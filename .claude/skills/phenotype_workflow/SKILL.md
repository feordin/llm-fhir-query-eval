---
name: phenotype_workflow
description: End-to-end workflow for adding a deeply-evaluated PheKB phenotype — read PheKB raw docs (primary algorithm source), verify codes via UMLS get_source_atoms_for_cui (no guessing), build Synthea module with 3-path template (Path C tricky cross-indication test), create test cases, load to HAPI, validate. Use this BEFORE designing any phenotype module. Always check `docs/PHENOTYPE-AUDIT.md` first.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__nih-umls__search_umls, mcp__nih-umls__get_concept, mcp__nih-umls__get_source_atoms_for_cui, mcp__nih-umls__get_source_concept, mcp__nih-umls__lookup_code, mcp__nih-umls__crosswalk_codes, mcp__nih-umls__check_code_subsumption, mcp__nih-umls__search_value_sets, mcp__nih-umls__expand_value_set, mcp__nih-umls__validate_code_in_value_set, mcp__nih-umls__get_value_set, mcp__nih-umls__get_definitions, mcp__nih-umls__get_concept_relations
---

# Phenotype Workflow Skill

End-to-end workflow for adding a deeply-evaluated PheKB phenotype: read PheKB docs → verify codes → build Synthea module → create test cases → load + validate → update STATUS/memory.

For deep edge-case detail (FHIR query patterns, value-quantity encoding, multi-`_has` queries), see the archived reference at `.claude/skills/_archived_phenotype_test_case/REFERENCE-DO-NOT-LOAD.md`.

## Usage

```
/phenotype_workflow <command> <phenotype>
```

| Command | Description |
|---|---|
| `analyze <phenotype>` | Read PheKB docs + identify algorithm paths and codes |
| `create <phenotype>` | Build Synthea module + test cases from analysis |
| `validate <phenotype>` | Load to HAPI + run validator script |

## Core principles (READ THIS FIRST)

### 1. PheKB docs are the algorithm source — not your clinical knowledge

Real PheKB phenotypes are multi-criteria decision trees with thresholds, temporal logic, and exclusion criteria. Always read these files **before** writing the module:

```
data/phekb-raw/<phenotype-slug>/description.txt        # narrative algorithm
data/phekb-raw/<phenotype-slug>/document_analysis.json # extracted codes + clinical_criteria + algorithm_summary
data/phekb-raw/<phenotype-slug>/*.pdf | *.doc | *.docx # original algorithm documents
```

If `document_analysis.json` lists codes you weren't going to use (e.g., 10+ ICD-9 codes alongside the SNOMED you knew), that's a signal — your module is probably under-modeling the algorithm. Check the audit at `docs/PHENOTYPE-AUDIT.md` for tier classification.

If no PheKB raw dir exists for the phenotype, document this in the module remarks and clinical-knowledge-only design becomes acceptable. But always check first.

### 2. PheKB code lists > UMLS code lookups

UMLS gives "the right code." PheKB gives "the codes that actually appear in real EHR data" — including legacy ICD-9 codes, miscoded variants, and pre-coordinated SNOMED concepts that real institutions use. **Use PheKB extracted_codes as primary, UMLS for verification/crosswalk.**

For a T1-significant-gap phenotype:
- Pull the PheKB code list from `document_analysis.json`
- Crosswalk legacy codes to active equivalents via UMLS `crosswalk_codes`
- Include BOTH the active SNOMED AND any commonly-used ICD codes in module + test cases (real cohorts get coded under multiple systems)

For UMLS code resolution use this pattern (no guessing):
```
search_umls("<term>", "exact")  →  CUI
get_source_atoms_for_cui(cui, source="RXNORM", ttys="IN")  →  ingredient code
get_source_atoms_for_cui(cui, source="SNOMEDCT_US", ttys="PT")  →  SNOMED preferred term
```

Common ttys: `IN` (RxNorm ingredient), `SCD` (RxNorm clinical drug), `PT` (SNOMED/ICD preferred), `LC` (LOINC long common name).

### 3. The 3-path module template (with "tricky" Path C)

Standard structure for medication-treated phenotypes:

| Path | Distribution | What it tests |
|---|---|---|
| **Path A** | 60% | dx + medication — standard presentation |
| **Path B** | 30% | dx only — milder cases / no Rx documented |
| **Path C** | 10% (TRICKY) | medication only, no dx — cross-indication / undiagnosed |

Add **Path D** (labs-only, no dx) when the phenotype has a defining lab threshold. Add multi-SNOMED variation within Path A/B when PheKB lists multiple subtype codes.

Path C is intentionally tricky — it tests whether the LLM knows that querying just for the medication overshoots into other indications (e.g., methotrexate query catches RA + psoriasis; vancomycin query catches C. diff + MRSA; mesalamine catches UC + Crohn's).

### 4. Test case set per phenotype

| Test case | Resource targeted | What it tests |
|---|---|---|
| `<phenotype>-dx` | Condition | LLM picks correct dx code system + value (ALL subtype codes if multi-SNOMED) |
| `<phenotype>-meds` | MedicationRequest | LLM picks correct RxNorm code(s) |
| `<phenotype>-labs` | Observation | LLM uses LOINC + value-quantity filter for threshold |
| `<phenotype>-comprehensive` | multi_query | LLM runs multiple queries and unions patient sets |

For comprehensive case set `metadata.multi_query: true` and list URLs in `expected_queries`. The validator unions patient IDs across queries.

For sex/age-restricted phenotypes use `metadata.patient_filters: {"sex": "female", "min_age_years": 18, "max_age_years": 50}` AND include `patient.gender=female` chained search in the test query URL.

### 5. Prompts are code-free

Each test case has a `prompts` block with three difficulty levels:
```json
"prompts": {
  "naive": "Find patients with X.",
  "broad": "Find patients diagnosed with X — clinical context, subtypes, etc.",
  "expert": "Search Condition for SNOMED <code> ... Query: <full URL>"
}
```

Prompts mention clinical concepts only (no codes). Codes appear in `expected_query` and `metadata.required_codes`.

## The workflow

### `analyze <phenotype>`

1. Check `docs/PHENOTYPE-AUDIT.md` for the phenotype's tier
2. Read `data/phekb-raw/<phenotype>/description.txt` + `document_analysis.json` + any PDFs/.docs
3. Identify all algorithm paths, code lists, lab thresholds, exclusion criteria, temporal logic
4. For unverified codes, run `search_umls` → `get_source_atoms_for_cui`
5. For ICD-9-only PheKB codes, crosswalk to SNOMED/ICD-10 via `crosswalk_codes`
6. Output a structured summary (paths, codes, criteria) — does NOT write files yet

### `create <phenotype>`

1. Use the analysis to write `synthea/modules/custom/phekb_<phenotype>.json` and `phekb_<phenotype>_control.json`
2. Module structure:
   - Age/sex guards from PheKB inclusion criteria
   - `Choose_Patient_Path` distributed_transition for paths A/B/C/D
   - `ConditionOnset` for dx (use ALL relevant codes — SNOMED + ICD-9/10 if PheKB lists both)
   - `MedicationOrder` with verified RxNorm codes
   - `Observation` with LOINC code + value range when applicable
3. Write test cases under `test-cases/phekb/phekb-<phenotype>-{dx,meds,labs,comprehensive}.json`
4. Use the JSON skeleton template (next section)

### `validate <phenotype>`

1. Generate: `python synthea/generate_test_data.py --phenotype <slug> --patients N --controls M`
2. **Augment** (optional but recommended): `python scripts/build_code_augmentations.py --phenotype <slug>` then `python scripts/augment_fhir_codes.py --phenotype <slug>` — post-processes Synthea bundles to attach ICD-9/ICD-10/CPT codings alongside SNOMED, mirroring real EHR multi-coded data. **Synthea's FHIR exporter only emits the FIRST coding per resource** — so multi-system codes added directly to Synthea module `codes` arrays are silently dropped. The augmentor is the workaround.
3. Load: `fhir-eval load synthea -p <slug> --fhir-url http://localhost:8080`
4. Validate: `python scripts/validate_phenotype_test_cases.py <slug>` — populates `expected_patient_ids` from query results
5. Verify counts in HAPI via direct curl (catch silent load failures)

## Test case JSON skeleton

```json
{
  "id": "phekb-<phenotype>-<dx|meds|labs|comprehensive>",
  "source": "phekb",
  "source_id": "<phenotype>",
  "name": "<Human-readable>",
  "description": "What this test evaluates and which path it covers.",
  "prompt": "<natural-language clinical prompt — NO CODES>",
  "prompts": { "naive": "...", "broad": "...", "expert": "..." },
  "metadata": {
    "implementation_guide": "US Core 5.0.0",
    "algorithm_path": "<which PheKB path, e.g. 'Path A: dx+meds'>",
    "code_systems": ["SNOMED CT", "ICD-10-CM", "RxNorm", "LOINC"],
    "required_codes": [
      { "system": "http://snomed.info/sct", "code": "...", "display": "...", "source": "PheKB doc + UMLS verified" }
    ],
    "complexity": "easy|medium|hard|expert",
    "tags": [...],
    "multi_query": true,                          // for comprehensive
    "expected_queries": [...],                    // for comprehensive
    "patient_filters": {"sex":"female","min_age_years":18}  // when applicable
  },
  "expected_query": {
    "resource_type": "Condition|MedicationRequest|Observation|Patient|multi",
    "parameters": {"code": "..."},
    "url": "Condition?code=..."
  },
  "test_data": {
    "resources": ["synthea/output/<phenotype>/positive/fhir/", "synthea/output/<phenotype>/control/fhir/"],
    "expected_result_count": null,
    "expected_resource_ids": [],
    "expected_patient_ids": []
  },
  "created_at": "<ISO>",
  "updated_at": "<ISO>"
}
```

## Common FHIR query patterns

| Need | URL |
|---|---|
| Multi-code Condition | `Condition?code=http://snomed.info/sct\|<a>,http://snomed.info/sct\|<b>` |
| Multi-system Condition (PheKB scenario) | `Condition?code=http://snomed.info/sct\|<a>,http://hl7.org/fhir/sid/icd-10-cm\|<b>` |
| Multi-RxNorm meds | `MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm\|<a>,http://www.nlm.nih.gov/research/umls/rxnorm\|<b>` |
| Lab with threshold | `Observation?code=http://loinc.org\|<code>&value-quantity=ge<n>\|\|<unit-encoded>` |
| Sex-restricted | append `&patient.gender=female` |
| Age-restricted | use `patient.birthdate=ge<date>&patient.birthdate=le<date>` chained |

Value-quantity encoding gotchas:
- Percent: `ge6.5||%25` (URL-encoded `%`)
- Negative T-score: `le-2.5||{T-score}`
- mg/dL: `gt200||mg/dL`

## Audit + tiering reference

`docs/PHENOTYPE-AUDIT.md` (regenerate with `python scripts/audit_phenotypes_vs_phekb.py`) shows current state of all phenotypes:

- **T1-significant-gap**: PheKB doc has ≥8 codes OR thresholds OR temporal logic. Module needs revision.
- **T2-minor-gap**: PheKB doc has 3–7 codes. Probably acceptable, doc the gap.
- **T3-aligned**: PheKB doc has 0–2 codes (matches module).
- **T3-no-phekb**: No PheKB doc — clinical-knowledge module is the only option.

When working on T1 phenotypes, expand the module to include all PheKB codes and lab thresholds. Track revisions in memory notes.

## STATUS + memory updates after each phenotype

1. Add a row to `STATUS.md` under the deep-evaluation table
2. Increment the deep-phenotype count in the header
3. Write `~/.claude/projects/.../memory/project_phenotype_<name>_<date>.md` with: codes, paths, key learnings, gap vs PheKB
4. Add one-line entry to `MEMORY.md` index with summary

## Common pitfalls

- **Guessing RxNorm codes**: don't. Use `get_source_atoms_for_cui`. Wrong-numbered guesses return real but unrelated drugs (oxybutynin guesses returned oxyfedrine, oxyphenonium, orphenadrine — all valid antimuscarinics, all wrong drug).
- **VSAC `lookup_code` 404s**: VSAC FHIR mirror has incomplete RxNorm coverage. Use `get_source_atoms_for_cui` instead, which hits the full UMLS REST API.
- **HAPI silent failures**: After Docker restart or extended uptime, HAPI can become "unhealthy" — loads fail with `RemoteDisconnected` errors but exit code 0. Verify load by direct curl `_summary=count` query.
- **Synthea SCD vs ingredient choice**: Use SCD for drugs in Synthea's medications.csv (round-trips cleanly) and ingredient otherwise. Trade-off: SCD is narrower, ingredient is broader.
- **Forgetting PheKB ICD-9 codes**: When the PheKB doc lists ICD-9, real cohorts include those codes. Don't drop them just because they're "legacy" — include both.
