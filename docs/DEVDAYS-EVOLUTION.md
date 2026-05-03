# DevDays — Evolution of an LLM-FHIR Evaluation Framework

A narrative of how the project evolved from "test if an LLM can write a FHIR query" to "test how well it can navigate the realities of clinical coding" — with the design decisions, surprises, and inflection points along the way.

---

## Where we started: a naïve setup that exposed the real problem

The original evaluation question was simple: **can an LLM translate "find patients with type 2 diabetes" into a working FHIR query?**

The first test case used a single SNOMED code:

```
Condition?code=http://snomed.info/sct|44054006
```

Synthea generated patients with that exact code, and qwen2.5:7b achieved 0.00 F1 — it hallucinated codes, used wrong code systems, and emitted malformed query strings. That was the easy result. The harder result came when we ran the same test against MIMIC-IV: a query with one SNOMED code missed 70% of the diabetes patients, because real EHR data has the same condition coded under multiple ICD-10 variants (E11.0 through E11.9), legacy ICD-9 (250.x), and SNOMED subtypes simultaneously.

**The first realization:** evaluating LLM FHIR-query generation is really evaluating its understanding of clinical coding plurality. A "correct" query depends entirely on what coding systems the data actually uses.

---

## Tier 1: closed-book evaluation — and the limits we found

We formalized this as **Tier 1 (Closed Book)**: just give the LLM the prompt, ask for a query. No tools, no introspection. The hypothesis was that small models would fail and large models would succeed via memorized clinical knowledge.

What actually happened:

| Failure mode | How often we saw it |
|---|---|
| Wrong code system (ICD-10 when data was SNOMED-only) | Almost universal in small models |
| Hallucinated codes (made-up LOINC, fake RxNorm SCDs) | Very common |
| Single code where a family was needed | Universal — even GPT-4o would use one cancer code instead of the C-chapter family |
| Wrong resource type (Condition for medications, etc.) | Common in small models |
| Missing patient-level filters (sex/age) | Universal — pediatric cohorts especially |

Even strong models had no way to discover what the server actually had. They were guessing.

---

## Tier 2: tool-assisted — the agentic loop, v1

We added an agentic loop with five tool families:

- **UMLS lookup / crosswalk** — search clinical concepts, map between code systems
- **VSAC value sets** — search for and expand quality-measure code lists
- **FHIR server metadata** — read the CapabilityStatement
- **FHIR sample data** — pull a few records of a resource type to inspect actual codings
- **FHIR search** — run candidate queries and see what comes back

The first version of the system prompt told the agent to use UMLS first, VSAC second, then sample. Performance improved substantially: wrong-code-system errors mostly disappeared because the agent could verify codes existed before constructing queries.

But systematic gaps remained:

- The agent would still pick a single code per concept even when value sets had 20+
- Provider-level requests ("find all diabetes patients including those on insulin without a documented diagnosis") got single-resource queries, missing 30-40% of the real cohort
- Subtype-rich diseases (cancer, dementia, diabetes) consistently under-recalled

We were teaching tools, but not strategy.

---

## The PheKB phenotype catalog — what reality actually looked like

In parallel, we built a 108-phenotype evaluation catalog from PheKB algorithm documents. We expected to write a few test cases per phenotype. The actual work surfaced patterns we hadn't expected:

### Pattern A: Real PheKB algorithms are multi-criteria decision trees

The eMERGE Drug-Induced Liver Injury algorithm doesn't just look for an ICD-10 code. It requires:

1. Hepatotoxicity dx (SNOMED + 3 ICD-10 codes — multi-system)
2. ALT ≥5× upper limit of normal (lab threshold)
3. A culprit drug prescription within 90 days (temporal ordering)

Encoding this as one Condition query loses 70% of cases. A real evaluation has to test multi-resource union, lab thresholds, and temporal logic.

### Pattern B: Code variation within a single phenotype

T2D's Synthea module distributes patients across 9 SNOMED variants. ADHD has 4. Asthma has 4. Heart failure has 5 (HFpEF, HFrEF, congestive, chronic, general). Each variant is clinically equivalent but coded differently.

A test case with one expected code "passes" only if the LLM happens to pick the right one. A test case with the full family rewards LLMs that know to query the family.

### Pattern C: The "tricky path C" cohort

Across phenotypes, ~30% of positive patients ended up in what we called Path C: **on the medication, but no diagnosis code**. Cross-indication — metformin prescribed for PCOS without a T2D dx, biologics prescribed for psoriatic arthritis without a Crohn's dx. Real EHRs have lots of these.

A naïve LLM that queries Condition only misses Path C entirely. A clinician using the same LLM as a chart-review assistant would think they had a complete cohort.

### Pattern D: The Synthea exporter's silent failure

We tried to make Conditions multi-coded by putting both SNOMED and ICD-10 in a Synthea module's `codes` array. Synthea silently exported only the first coding. The data on the server was still SNOMED-only despite the module saying otherwise.

This was a 4-hour debugging detour. The lesson: don't trust upstream tooling to carry your invariant; verify in the actual output.

---

## The code-augmentation pipeline — building realistic data

The fix for Pattern D became the most important infrastructure piece. We built:

1. **`scripts/build_code_augmentations.py`** — auto-populate a SNOMED→ICD-10/ICD-9/CPT crosswalk map by reading PheKB document analyses, with disambiguating-modifier guards (so "ruptured AAA" doesn't false-match "AAA without rupture").
2. **`data/code_augmentations.json`** — 314 SNOMED-keyed entries covering 48 phenotypes' worth of crosswalks.
3. **`scripts/augment_fhir_codes.py`** — post-process Synthea bundles in-place, attaching ICD-10/ICD-9/CPT codings alongside SNOMED on every matching resource.

The same patient now appears via SNOMED 233985008 OR ICD-10 I71.4 OR ICD-9 441.4 OR CPT 35081 — exactly like real EHR data.

This unlocked a new evaluation dimension: **does the LLM know that any of those code systems would retrieve the same cohort**, or does it fixate on one and confidently get the wrong number of patients?

---

## The migration: HAPI → Microsoft Health FHIR Server

Mid-sweep we hit HAPI FHIR's stability ceiling. After ~1 hour of sequential transaction-bundle loads, HAPI would go unhealthy and start dropping connections. We migrated to Microsoft's Health FHIR Server (SQL-backed). Key learnings:

- **Stability beat speed.** Microsoft FHIR was 5-10x slower per bundle (SQL serialization on inserts), but rock-solid through 30+ sequential phenotype loads. For a one-time full reload, the right trade.
- **The IG layer is real.** Microsoft FHIR exposes `implementationGuide` and `supportedProfile` in its CapabilityStatement, which our `fhir_server_metadata` tool now surfaces — Tier 2 agents can detect "this is a US Core server" and adjust strategy.
- **Authentication is non-trivial.** First boot demanded Bearer auth and a non-null Authority — even with `Security__Enabled=false`. We had to also disable `TestAuthEnvironment__FilePath` and provide a placeholder Authority. Documented in compose file comments now.

---

## Tier 2 v2: the agentic loop after PheKB lessons

Today's system prompt (`backend/src/llm/agentic_provider.py`) is built around five core principles distilled from those phenotype patterns:

1. **Real EHR data is multi-coded** — Conditions/Procedures/Observations carry SNOMED + ICD-10 + ICD-9 + CPT simultaneously.
2. **Diseases-with-subtypes need code families** — use VSAC value-set expansion, not single codes.
3. **Provider-level cohorts span resource types** — Condition OR MedicationRequest OR Observation, often unioned.
4. **Plan before you query** — decompose into dx / meds / labs / procedures / patient filters.
5. **Iterate: query → count → refine** — verify magnitude, sample codings.

The recommended workflow is now `vsac_search_value_sets` → `fhir_server_metadata` → `fhir_resource_sample` → construct → `fhir_search`. UMLS only as a fallback for rare phenotypes. This inversion (VSAC first, UMLS last) eliminates 60-80% of tool calls for well-known concepts.

The system prompt also includes worked examples for:

- Multi-code single-resource queries
- Lab thresholds with `value-quantity`
- Patient-level filters via `patient.gender` / `patient.birthdate`
- Cross-resource via `_has`
- Multi-query union (provider-level cohorts)
- Negation via two-query subtraction

---

## Where Tier 3 will go

Tier 2 teaches the agent what tools exist. Tier 3 will teach it what *strategies* exist by giving it a methodology skill that distills the phenotype-design heuristics:

- "For chronic diseases with subtypes, use VSAC + sample + multi-resource union"
- "For pediatric phenotypes, add `patient.birthdate` filter — pediatric is age, not a code"
- "For PGx phenotypes, MedicationRequest is the primary signal, not the Condition"
- "For procedural phenotypes, CPT often beats SNOMED for recall on US data"

This is the same knowledge the `phenotype_workflow` skill encodes for human authors. Surfacing it as a Tier 3 skill should let the agent operate at the level of an experienced clinical informaticist rather than just a careful FHIR developer.

---

## The numbers (so far)

| Metric | Value |
|---|---|
| PheKB phenotypes covered | 108 / 108 |
| Synthea modules built | 216 (positive + control per phenotype) |
| PheKB documents analyzed | 75 (state A) — was 63 before re-running extraction with streaming + 32K tokens |
| Code-augmentation entries | 314 SNOMED-keyed crosswalks → ICD-10/ICD-9/CPT |
| Test cases | ~419 across the catalog |
| Patients on Microsoft FHIR | 25,729 |
| FHIR resources loaded | 0 errors across the full catalog reload |

---

## What we'd do differently next time

1. **Augment-as-you-generate, not as-you-fix.** The augmentation pipeline should be part of the Synthea workflow from day one, not a retrofit. Synthea's first-coding-only export is a real constraint, not a quirk.
2. **Pick a SQL-backed FHIR server from the start.** HAPI in-memory was great for early iteration but doesn't survive sustained load. Migrating mid-project cost ~6 hours and forced a client refactor.
3. **VSAC-first, always.** UMLS crosswalking is fine but value sets are the primitive that matches how phenotype algorithms are actually authored.
4. **Test the negation cases before you assume queries handle them.** FHIR has no `NOT EXISTS`; getting that wrong silently produces over-counts in 30%+ of provider-level cohort queries.
5. **The agentic loop's system prompt is the most leveraged surface in the codebase.** Three lines of guidance ("sample server data first", "use code families not single codes", "decompose by resource type") are worth more than ten more tools.
