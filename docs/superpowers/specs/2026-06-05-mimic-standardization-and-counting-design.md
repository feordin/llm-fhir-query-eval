# MIMIC-IV-on-FHIR — Code Standardization + Per-Phenotype Counting

**Date:** 2026-06-05
**Status:** Approved design, pending implementation plan
**Task:** #3 (dev-days goals)
**Dataset:** `mimic-iv-clinical-database-demo-on-fhir-2.1.0` (100-patient demo)

## Background — coding-system profile (verified 2026-06-05)

MIMIC-on-FHIR uses **MIMIC-local CodeSystem URIs**, not the standards our queries
target. Codes are ICD/NDC/local *values* under `mimic-*` namespaces:

| Resource | MIMIC system | Code form | Standard equivalent |
|---|---|---|---|
| Condition | `mimic-diagnosis-icd10` / `-icd9` | undotted (`E119`, `5715`, `V462`) | `hl7.org/fhir/sid/icd-10-cm` / `icd-9-cm` |
| Procedure | `mimic-procedure-icd9` / `-icd10` | undotted (`5491`; PCS `3E0G76Z`) | `icd-9-cm` / `icd-10-pcs` |
| Medication | `mimic-medication-ndc` + `-name` | NDC + local names | RxNorm (no map shipped) |
| Lab Obs | `mimic-d-labitems` | local item IDs (`50885`) | LOINC (no map shipped) |
| Chart Obs | `mimic-chartevents-d-items` | local item IDs | LOINC (rarely needed) |

The bundle ships **only** resource NDJSONs — no ConceptMaps/crosswalks.
Demo resource counts: 100 Patient, 4506 Condition, 722 Procedure,
17552 MedicationRequest, 1480 Medication.

## Goal

While processing MIMIC for per-phenotype counts, **standardize the codes
additively** and save a new version, so the same data serves (a) reliable offline
cohort counts and (b) a future `$import` eval-rerun where our existing
standard-system queries work unchanged.

## Decisions (approved)

1. **Additive transform** — keep each original `mimic-*` coding AND append a
   standard coding on the same `code.coding[]`. Nothing lost; provenance kept;
   mirrors `scripts/augment_fhir_codes.py`.
2. **Include LOINC labs now** — add LOINC codings to lab Observations using
   MIMIC's published `d_labitems`→LOINC map (partial coverage; additive).
3. **Meds untouched** — no NDC→RxNorm transform. Instead enhance the phenotyping
   skill to be **server-aware** about med coding systems (separate work, below).

## Component 1 — `scripts/standardize_mimic_fhir.py`

Streams each input NDJSON → emits a standardized copy under `mimic-standardized/`.
Pure transform, no FHIR server. Idempotent.

### ICD re-dotting (Condition + Procedure)

Rule selected by the source `mimic-*` system label:

| Source system | Dot rule | Example | Added coding system |
|---|---|---|---|
| `mimic-diagnosis-icd10` | dot after 3rd char if len>3 | `E119`→`E11.9` | `http://hl7.org/fhir/sid/icd-10-cm` |
| `mimic-diagnosis-icd9` | numeric/V: dot after 3rd; E: after 4th | `5715`→`571.5`, `V462`→`V46.2` | `http://hl7.org/fhir/sid/icd-9-cm` |
| `mimic-procedure-icd9` | dot after **2nd** char | `5491`→`54.91` | `http://hl7.org/fhir/sid/icd-9-cm` |
| `mimic-procedure-icd10` (PCS) | **no dot** (7-char) | `3E0G76Z` | `http://hl7.org/fhir/sid/icd-10-pcs` |

- The added coding reuses the original `display`.
- **Validation gate:** sample-validate a random subset of re-dotted codes via the
  UMLS MCP (`lookup_code` in ICD10CM / ICD9CM). Report match rate; fail loudly if
  below a threshold (e.g. <95%) so a bad dotting rule can't ship silently.

### LOINC labs (Observation labevents)

- Source MIMIC's official `d_labitems`→LOINC mapping (MIT-LCP `mimic-code` /
  PhysioNet derived table). Build an `itemid -> LOINC` dict.
- For each lab Observation whose `mimic-d-labitems` code is in the map, append a
  `{system: http://loinc.org, code: <loinc>, display: ...}` coding.
- Items with no LOINC mapping keep only the local coding (logged with a coverage
  %). Fallback if the map is unavailable: skip LOINC enrichment (degrade to local
  only) — labs counts then rely on display-name matching, flagged as lower
  confidence.

### Scope of files transformed

Condition(+ED), Procedure(+ED/ICU), ObservationLabevents (+ ED labs). Leave
Medication*, Chartevents, Datetimeevents, Micro*, Specimen* untouched in v1
(Chartevents is 534 MB ICU vitals, rarely needed by our algorithms).

## Component 2 — `scripts/mimic_phenotype_counts.py`

Offline per-phenotype patient counts against the **standardized** data (no server).

1. For each of our 108 phenotypes, load its standard code sets from the existing
   definitions (`test-cases/phekb/*`, `data/code_augmentations.json`):
   ICD-10-CM + ICD-9-CM (dx), ICD-10-PCS/ICD-9 proc, LOINC (labs).
2. Match against standardized MIMIC resources (normalize: strip dots both sides,
   uppercase; allow ICD **prefix** match, e.g. `E11` matches `E11.9`).
3. Resolve to distinct `subject`/`patient` references and count.
4. Emit a table: phenotype × {dx-count, procedure-count, lab-count,
   any-path-union-count} with a confidence tag per path
   (dx/procedure = high, labs = medium, meds = excluded in v1).

**Headline number per phenotype = the dx (ICD) cohort** (most reliable, covers the
primary identifier for most phenotypes). Procedure/lab counts enrich it.

## Component 3 — phenotyping skill: med-coding-system awareness (separate)

Not a data transform. Enhance the `fhir-phenotyping` / `fhir-server-introspection`
skill (Thread B) so that, given a server, it detects which medication coding
system is in use (sample `Medication`/`MedicationRequest`, observe `system` URIs:
NDC vs RxNorm vs local-name) and constructs med-path queries accordingly. This is
the realistic Tier-2 introspection behavior and makes the plugin robust to real
servers like MIMIC. Tracked under Thread B, informed by this finding.

## Loading to a FHIR server ($import vs POST) — deferred until after current run

- **Counting needs no server** (Component 2 is offline) — do that first.
- For the eventual eval-rerun: **`$import` (bulk NDJSON)** is the clear choice —
  MIMIC ships NDJSON specifically for it; per-resource POST would be hundreds of
  thousands of requests. Load the **standardized** version so our queries work.
- Skip Chartevents unless a phenotype needs ICU vitals. Confirm the Microsoft FHIR
  server's `$import` supports the volume (143 MB Labevents is the big one kept).

## Out of scope (v1)

- NDC→RxNorm med transform (handled via skill awareness instead).
- Chartevents/Datetimeevents/Micro/Specimen standardization.
- The full credentialed MIMIC-IV (this is the 100-patient demo; pipeline should
  scale to it unchanged).

## Open items for planning

1. Exact source + URL for the `d_labitems`→LOINC map; measure coverage %.
2. ICD-9 E-code dotting edge cases (rare in dx) — confirm rule against samples.
3. Whether counts should also be produced for the **original** (un-standardized)
   data as a sanity cross-check (expect identical for dx once dotting is correct).
