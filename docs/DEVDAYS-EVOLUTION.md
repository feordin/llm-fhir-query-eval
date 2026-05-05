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

## Tier 3 in practice: when context isn't engagement

Tier 2 teaches the agent what tools exist. Tier 3 was supposed to teach it what *strategies* exist by giving it a methodology skill — distilled phenotype-design heuristics:

- "For chronic diseases with subtypes, use VSAC + sample + multi-resource union"
- "For pediatric phenotypes, add `patient.birthdate` filter — pediatric is age, not a code"
- "For PGx phenotypes, MedicationRequest is the primary signal, not the Condition"
- "For procedural phenotypes, CPT often beats SNOMED for recall on US data"

We built it: `backend/src/llm/tier3_methodology.md`, 12 playbooks, ~5,000 words, prepended to the system prompt when `tier=3`.

### What we expected vs. what we measured

The first qwen3:8b matrix (9 cells: T1/T2/T3 × naive/broad/expert prompts) showed a depressing result: **Tier 3 didn't beat Tier 2.** Both got perfect F1 on the expert prompt; both failed on naive and broad. The 5,000 words of methodology made no measurable difference.

The hypothesis: small models *receive* long context but don't *engage* with it. They skim, jump to tool calls, and behave like Tier 2 with a longer prompt.

### Step 0: forced categorization

The fix was a 30-line addition at the top of the methodology document — **before** the playbooks themselves:

1. A 4-step procedural instruction ("read the request → run the decision tree → state the playbook number(s) explicitly → only then construct queries"). The word "mandatory" matters less than "State explicitly in your reasoning" — that's what turns it from passive context into a forced output.
2. An 8-row keyword→playbook lookup table: `"without"` → Playbook 10 (negation, two-query subtraction), `"≥"` → Playbook 7 (threshold via `value-quantity`), `"female"` → Playbook 4 (chain `patient.gender`), `"all my patients"` → Playbook 12 (cohort = OR multi-resource union), and so on.
3. A closing exhortation about the cost of skipping (folklore, but it doesn't hurt).

### What it bought us

Re-running the matrix on 5 more test cases yielded:

| Phenotype | T2 broad F1 | T3 broad F1 |
|---|---|---|
| Ovarian-cancer-dx (sex-specific) | 0.3 | **1.0** |
| T2D-comprehensive (multi-resource) | timeout | **1.0** |
| AKI-labs (threshold) | 1.0 (already at ceiling) | 1.0 |
| Crohn's-dx (subtypes) | 0.0 | 0.0 |

Two phenotypes flipped from poor/timeout to perfect. AKI-labs was already at ceiling. Crohn's-dx didn't lift — qwen3:8b's classification might've still been off there. Small N, but directionally consistent: where there was room to lift, the lift happened.

### The honest assessment

The lift is plausibly driven by the **table** more than the procedural framing. The keyword index lets a small model *match* against a short lookup rather than *recall* from a long methodology doc. Strip out the "mandatory" wording and most of the lift would probably remain. Unverified — would take a control matrix to confirm.

### The generalizable principle

This is the cleanest illustration we got of a broader truth in agentic LLM design: **handing a model a lot of knowledge isn't the same as making it use that knowledge.** A small explicit "categorize first, act second" instruction extracts an order of magnitude more value out of the same content. Same idea as putting your hot path at the top of a CLAUDE.md, or like an index card on a doctor's desk vs. a textbook on the shelf.

For DevDays: the audience doesn't have to care about FHIR to take this home. They have to design agents that consume context they put together themselves. "Make the most-likely-needed knowledge a reflex, not a recall" is portable.

---

## Open problem: the multi-resource union ceiling

The Crohn's-comprehensive test case is the one we couldn't beat. It defines a 152-patient provider-level cohort that requires three queries unioned:

1. `Condition?code=<crohn's SNOMED + ICD-10 + ICD-9>` — patients with a documented diagnosis
2. `MedicationRequest?code=<biologic + 5-ASA + steroid RxNorm codes>` — treated patients (some without dx)
3. `Observation?code=<inflammatory markers>` — lab-evidenced patients

The runner unions the patient IDs. Best F1 we hit across all 9 cells (T1/T2/T3 × naive/broad/expert) was **0.31** — the agent never produced all three queries cleanly enough to reach the 152-patient cohort.

### Why this matters: it's not just Crohn's

The same shape recurs across most provider-level cohort definitions:

- **T2D comprehensive** (74 patients): dx + meds + HbA1c labs. T1 baseline got lucky here (qwen3:8b had T2D knowledge baked in), but on phenotypes the model doesn't already know, the same shape would fail.
- **DILI** (drug-induced liver injury): culprit drug exposure + ALT lab threshold + hepatotoxicity dx — three resources with a temporal twist.
- **AAA** (3 case types: repair procedure, ruptured dx, ≥2 vascular visits with unruptured dx): three queries, three failure paths.
- **Heart failure** (HFpEF vs HFrEF, multiple meds, BNP labs)
- **Sepsis** (SIRS Conditions + qSOFA Observations + lactate threshold + abx Rx)
- Generally: **any phenotype where "find all my X patients" is the question**, which is most of clinical practice.

PheKB's algorithms are mostly written this way because real EHR documentation is mostly written this way: a patient is sometimes diagnosed, sometimes treated, sometimes lab-evidenced, often two of three, occasionally all three.

### Failure modes we observed

- **Single concatenated query.** The agent emits one giant URL that smashes multiple `?code=` strings together (`MedicationRequest?code=...MedicationRequest?code=...`). The server returns 400; the runner records a 0.
- **Multiple queries, wrong resource types.** Agent emits two `Condition?` queries with different codes instead of `Condition?` + `MedicationRequest?`. Result is duplication within one resource type, not union across types.
- **Multiple queries, one resource type missing.** Agent recognized "dx + meds" but not "dx + meds + labs". 30-60% under-recall.
- **Over-querying spam.** Especially on T1 broad, the model dumps a wall of queries that catch the cohort but also catch thousands of unrelated patients (precision = 0.04, recall = 0.99).

### Possible solutions — captured here as gaps, not yet implemented

We're treating this as a known frontier and not patching it before the talk. Candidates for future work, roughly ranked by leverage:

1. **Output-schema enforcement.** Require the agent's final answer to follow a template:
   ```
   # Query 1 (Condition): <url>
   # Query 2 (MedicationRequest): <url>
   # Query 3 (Observation): <url>
   ```
   Force the agent to address each resource type explicitly. Even if it leaves a query empty, the structural prompt makes it harder to skip a resource type unconsciously.

2. **A pre-flight `decompose_cohort(prompt)` tool** that returns suggested per-resource queries for the agent to verify and refine. Trades flexibility for structure — useful for cohort prompts, less so for case-validation prompts.

3. **Iterative validation in-loop.** Agent emits one query, runner returns count + sample, agent asks "is this the cohort or do I need to broaden?". Slow but pedagogically interesting — and more like how a clinician actually works.

4. **Two-stage agent: planner + executor.** The planner outputs a JSON resource decomposition (`{Condition: [codes], MedicationRequest: [codes], Observation: [codes + threshold]}`), and a deterministic executor builds the queries. Removes one degree of freedom (URL syntax) from the LLM's job.

5. **Fine-tune on synthetic union examples.** A few hundred (prompt → 3-query union) pairs would teach the format. Practical but not as portable a story.

6. **Stronger STEP 0 framing for cohort cases.** A keyword like "all my patients" or "comprehensive" already maps to Playbook 12 today, but the lookup row could be more aggressive: *"You MUST emit one query per resource type. Skipping a resource type drops the cohort by 30-60%."* — more behavioral nudging.

### What we'll say at DevDays

This is the open question we end on. The takeaway: **context-only methods plateau when the answer is structurally multi-step.** Single-prompt agents — even with tools, even with methodology — hit a ceiling on tasks that require coordinated outputs across multiple structural slots. The next research lever isn't more knowledge; it's tighter output structure or workflow decomposition.

It's a satisfying open question because it's the same shape as a lot of real-world agentic problems: deal-flow agents that need to query 3 systems, support agents that need to consult 4 references, planning agents that need to fill N slots in a coordinated plan. Small models (and even mid-tier models) under-fill. Big models over-spam. Structure beats both.

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
