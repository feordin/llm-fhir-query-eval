---
name: fhir-cohort-query
description: Build a FHIR query (or query set) that returns exactly the patient cohort described in plain English. Use whenever the user asks to find/count/list patients matching a clinical description against a FHIR server — e.g. "find all my type 2 diabetics", "patients on warfarin with INR over 3", "women over 65 with osteoporosis but no bisphosphonate".
---

# FHIR Cohort Query Builder

Turn a plain-English patient-population description into FHIR search queries
whose **returned patient set** matches the described cohort — high recall
(every path that finds these patients) *and* high precision (no look-alike
conditions).

**Server:** use `$FHIR_BASE_URL` if set, else ask the user for the endpoint.

## The iron rule: never answer from memory

Benchmarked closed-book, even frontier LLMs score F1 ≈ 0.6 on synthetic data
and **F1 ≈ 0.1 on real EHR data** — real servers carry code systems and
granularities you cannot predict. With the discovery loop below the same
models score 0.86–0.99. **Your first action is always a lookup, never a
query written from recall.**

## The discovery loop

### 1. Categorize the request (mandatory)

Load `references/methodology.md` and run its STEP 0: state which playbook(s)
the request matches (subtypes, threshold, negation, sex/age, iatrogenic,
cohort-OR vs case-AND, …) before writing anything. Most requests match more
than one — combine them.

### 2. Find the clinical concepts and codes (UMLS/VSAC via the nih-umls MCP)

- `search_umls("<concept>")` → CUI → `get_source_atoms_for_cui(cui, source)`
  for verified codes in a target vocabulary (SNOMED CT, ICD-10-CM, LOINC,
  RxNorm). Never invent a code.
- `crosswalk_codes` to map a known code between systems.
- For established phenotypes prefer a curated value set:
  `search_value_sets("<concept>")` → `expand_value_set(oid)` gives the full
  code family a committee already enumerated.
- **Enumerate the long tail.** Query the umbrella concept AND every subtype
  the cohort could be coded with (all diabetes-family codes, every cancer
  histology, each CKD stage). Under-enumeration is the #1 recall killer —
  a "pick the canonical code" instinct cut recall from 1.00 to 0.39 on
  heterogeneous phenotypes in our benchmark.

### 3. Sample the server — learn how THIS data is coded

Real servers are single-system and granular; assume nothing.

```
GET {base}/metadata                          # resources + search params + profiles
GET {base}/Condition?_count=10               # which code system(s)? dotted? granular?
GET {base}/Observation?category=laboratory&_count=10
GET {base}/MedicationRequest?_count=5        # inline codes or medicationReference?
```

Read the actual `coding.system` URIs from the samples. Findings that change
your query:

- **Data is ICD-only** (typical US claims/EHR): translate your SNOMED
  concepts to ICD-10-CM *and* ICD-9-CM (older records) via crosswalk.
- **Fully-granular codes + no hierarchy**: if samples show `E11.9`,
  `E11.42`… and the server lacks `:below`, a category query (`E11`) may
  match nothing — enumerate the granular codes present (sample more rows or
  probe with counts).
- **Meds behind `medicationReference`**: query needs `_include` /
  chained search into Medication, and the Medication codes may be NDC, not
  RxNorm.
- The `scripts/fhir_introspect.py` helper automates this census:
  `python scripts/fhir_introspect.py {base} --census Condition`.

### 4. Validate magnitude, then self-correct

Run every candidate with `&_summary=count` before finalizing:

- **0 results** → wrong system, wrong granularity, or too-narrow concepts.
  Re-sample, crosswalk, add subtypes.
- **Implausibly large** (approaching the whole population) → over-broad code
  family or a missing constraint; check against mimicker look-alikes.
- Iterate until counts are clinically plausible for the population.

### 5. Emit the final query set

- Always include the system URI: `code=http://hl7.org/fhir/sid/icd-10-cm|E11.9`,
  never a bare code. Comma-join codes within one param (OR).
- **Cohort ("all my patients with X")** = union across evidence paths — one
  query per resource type on its own line (Condition ∪ MedicationRequest ∪
  Observation ∪ Procedure); the caller unions patient sets.
- **Strict/validated case** = AND — chain with
  `Patient?_has:Condition:patient:code=…&_has:MedicationRequest:patient:code=…`.
- **Negation ("X without Y")** = two labeled queries: KEEP set and SUBTRACT
  set; the caller subtracts patient sets (FHIR has no NOT-EXISTS).
- State expected counts per query and any caveats (paths not queryable on
  this server, codes you could not verify).

## Why trust this workflow

Distilled from a 108-phenotype execution-based benchmark (PheKB algorithms,
patient-set P/R/F1 scoring) plus real-data validation on MIMIC-IV-on-FHIR
(299,712 patients). Key measured facts: tools are worth +0.23–0.30 F1 over
closed-book on synthetic and +0.6 on real data; with this loop a naive
plain-English prompt performs within ~0.05 of an expert code-aware prompt.
