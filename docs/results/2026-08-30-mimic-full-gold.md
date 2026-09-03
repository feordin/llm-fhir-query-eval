# Full MIMIC-IV gold cohorts: 300k real patients, 105/108 phenotypes

**Date:** 2026-08-30 · Full credentialed MIMIC-IV-on-FHIR (**299,712 patients**),
standardized + gold-computed offline (no FHIR server). Follows the demo pipeline
from `2026-06-12-mimic-demo-sweep.md`; gold at `data/mimic-full-gold.json`
(patient-ID sets per phenotype × {dx, labs, comprehensive}).

## Pipeline (Phases 0–2 of the full-MIMIC plan)

1. **Unzip** (16 of 32 files kept): Patient, Encounter(+ED/ICU), Condition(+ED),
   Procedure(+ED/ICU), ObservationLabevents (118,171,367 rows / 151 GB),
   ObservationED, MedicationRequest (15.4M), Medication(+Mix), Org, Location.
   Skipped: Chartevents (16 GB gz ICU vitals), Datetime/Output/Micro/Specimen,
   MedicationAdministration/Dispense/StatementED.
2. **Standardize** (`standardize_mimic_fhir.py`, additive only): dotted
   ICD-10-CM/ICD-9-CM/ICD-10-PCS added beside MIMIC-local codings — 100% of
   Condition (5.66M) and hospital Procedure (669k); **+111.68M LOINC codings on
   labevents (94.5% coverage)** via the srdc itemid→LOINC map. ProcedureED is
   natively SNOMED and ObservationED natively LOINC (no transform needed — ED
   BP rows carry LOINC 8480-6/8462-4 as-is).
3. **Gold** (`recompute_mimic_gold.py`): hierarchical ICD prefix match for dx,
   LOINC+threshold for labs, union for comprehensive. 263,295 patients carry
   conditions/procedures; 246,724 carry criteria-relevant labs.

## Code-list fixes required for correct gold (this session)

The demo-era code lists had four defects that full-scale counts exposed:

- **Negation leakage**: `negation: true` test cases reference the *excluded*
  cohort's codes (T1D's insulin-without-dx subtracts E11) — T1D gold wrongly
  equaled T2D's 37k. Now skipped. T1D = **4,313** (11.6% of T2D — matches
  real-world type ratios).
- **URL-scrape junk**: `E11"]`, `E10.x`, `250.(0-9)0`, range notation
  (`A15-A19`), and 2-digit ICD-9 procedure codes (which would prefix-match dx
  categories) now rejected by `_valid_icd` shape validation.
- **`.x` templates in code_augmentations.json**: 10 entries (asthma 493.x, HF
  428.X, migraine 346.x/G43.x, T1D E10.x) normalized to category codes.
- **40 SNOMED-only phenotypes had zero ICD codes** → zero MIMIC patients for
  sepsis, COPD, stroke, anxiety, etc. New `scripts/backfill_icd_augmentations.py`
  crosswalked their Condition-context SNOMED codes via UMLS REST (**165 verified
  ICD entries**), + 8 manual UMLS-MCP lookups (down-syndrome Q90/758.0,
  glioblastoma C71/191, melanoma C43/172, renal-cancer C64/189.0).

Result: **105/108 phenotypes have a MIMIC cohort** (was 73 before fixes). The 3
without are structural: cardiac-conduction-qrs (ECG-based), multimodal-analgesia
(meds-only), neonatal-abstinence-syndrome (adults-only dataset).

## Headline cohorts (dx / labs / comprehensive)

| Phenotype | dx | labs | comp |
|---|---:|---:|---:|
| hypertension | 84,776 | – | 84,776 |
| resistant-hypertension | 83,947 | – | 83,947 |
| gerd | 39,230 | – | 39,230 |
| depression | 37,597 | – | 37,597 |
| type-2-diabetes | 37,142 | 20,908 | 42,069 |
| iron-deficiency-anemia | 33,684 | 127,055 | 128,252 |
| coronary-heart-disease | 33,315 | – | 33,315 |
| acute-kidney-injury | 31,926 | 38,987 | 44,960 |
| asthma | 30,237 | – | 30,237 |
| heart-failure | 24,234 | – | 24,234 |
| sepsis | 14,601 | – | 14,601 |
| … (full table: `mimic_phenotype_counts.py` output / gold JSON) | | | |
| tuberculosis | 94 | – | 94 |
| cystic-fibrosis | 37 | – | 37 |
| polycystic-kidney-disease | 16 | – | 16 |

Median dx cohort ≈ 2,400 — the demo's small-n noise (1–20 patient cohorts) is
gone; per-cell F1 will be meaningful.

## Caveats (carry into the sweep report)

- **Labs over-capture in the ICU population**: IDA's hemoglobin threshold
  catches 127k patients (~42% of the dataset); AKI creatinine 39k. The
  comprehensive union is dominated by labs for those phenotypes. This is a
  property of the phenotype definitions on sick populations, not a bug.
- **Category-level gold for histology cancers**: ICD can't express GBM or
  clear-cell RCC — their gold is C71 (all brain malignancy, 651) and C64
  (kidney, 984). Slight over-capture by design.
- **Pediatric phenotypes match adults**: severe-childhood-obesity (20,336) etc.
  match on codes only; `patient_filters` age guards aren't applied offline and
  MIMIC birthdates are century-shifted. Interpret those cells accordingly (or
  drop pediatric phenotypes from the MIMIC sweep list).
- **Meds (NDC) and procedures (ICD-10-PCS) paths remain unscored** — same as
  demo; proc_pts=0 because our procedure gold codes are CPT/SNOMED. NDC→RxNorm
  crosswalk deferred.
- **UMLS crosswalk quirk**: SNOMED "Bacterial sepsis" (10001005) maps to
  bacteremia (R78.81/790.7), slightly widening the sepsis dx net.

## Phases 3–4 complete (2026-08-31): jaerwinllm loaded + verified

- Labevents filtered to the 30 criteria LOINCs: 118M → **12,192,190 rows
  (10.3%)**; upload set = 35 NDJSON files / 44.6 GB (1.9 GB split chunks).
- MedicationRequest **included** (user decision): all 15.4M orders +
  Medication resources. Meds are `medicationReference` → NDC under a
  MIMIC-local CodeSystem — chained-query + coding-discovery realism, unscored.
- `$import` (IncrementalLoad, operation 85) loaded **42,279,201 resources in
  ~8.5 h with 0 errors**; per-type live counts equal file line counts exactly
  (Patient 299,712 · Condition 5,655,376 · Observation 16,596,671 ·
  MedicationRequest 15,416,901 · Procedure 3,354,975 · Encounter 929,499).
- Search verification: live token-search counts match offline JSON counts
  exactly for 5 spot codes (I10 72,970 · 401.9 124,177 · E11.9 25,422 ·
  LOINC 2160-0 3,283,280 · LOINC 4548-4 223,327). (An initial ±1,000 E11.9
  "discrepancy" was an unescaped regex dot in the offline grep, not the
  server.)

Remaining: server fan-out decision (1 vs more of jaerwinllm2..10), sweep prep
(`expected_patient_ids` from this gold, `run_mimic_sweep.sh --no-reload`).
