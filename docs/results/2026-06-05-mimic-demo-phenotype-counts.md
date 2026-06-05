# MIMIC-IV-on-FHIR Demo — Per-Phenotype Patient Counts

**Date:** 2026-06-05  **Dataset:** mimic-iv-clinical-database-demo-on-fhir-2.1.0 (100-patient demo)

Offline counts via `scripts/mimic_phenotype_counts.py` against the **standardized**
MIMIC data (`scripts/standardize_mimic_fhir.py`). The standardizer is **purely
additive normalization**: it keeps every original `mimic-*` coding and appends the
standard-system equivalent (dotted ICD / the lab item's LOINC). No values are altered,
no resources added or dropped — nothing is tuned to favor our tests.

Method: distinct Patient count via hierarchical ICD match (phenotype category code
matches MIMIC subcodes) for dx/procedure; LOINC + value-quantity threshold for labs.

**Confidence by path:**
- **dx** (Condition-anchored ICD) — HIGH. The headline number.
- **proc** (ICD-10-PCS) — 0 everywhere: our phenotype procedure codes are CPT/SNOMED,
  MIMIC procedures are ICD-10-PCS (no overlap). A code-system gap, not absence.
- **lab** (LOINC + threshold) — LOW, and OVER-CAPTURES. A single transient abnormal
  value during an ICU stay flags the phenotype. E.g. iron-deficiency-anemia=93/100
  because median MIMIC hemoglobin is 9.8 (< the 12 threshold) — ICU patients are
  overwhelmingly anemic. This is a REAL property of the sick ICU population, reported
  as-is, not a data defect.

```

phenotype                             dx_pts  proc_pts  lab_pts
----------------------------------------------------------------
iron-deficiency-anemia                     0         0       93
resistant-hypertension                    55         0        0
hypertension                              55         0        0
nafld                                      7         0       44
acute-kidney-injury                        0         0       38
coronary-heart-disease                    33         0        0
type-2-diabetes                           32         0       18
type-1-diabetes                           31         0       18
warfarin-dose-response                     0         0       26
gerd                                      25         0        0
heart-failure                             24         0        0
ckd                                       23         0        0
asthma                                    21         0        0
depression                                21         0        0
severe-childhood-obesity                  20         0        0
pneumonia                                 19         0        0
atrial-fibrillation                       18         0        0
familial-hypercholesterolemia             16         0        0
asthma-response-inhaled-steroids          15         0        0
drug-induced-liver-injury                 14         0       10
hypothyroidism                            14         0        8
epilepsy                                  12         0        0
atopic-dermatitis                         11         0        0
sleep-apnea                                9         0        0
dementia                                   9         0        0
clopidogrel-poor-metabolizers              8         0        0
venous-thromboembolism                     8         0        7
febrile-neutropenia-pediatric              2         0        8
migraine                                   7         0        0
breast-cancer                              6         0        0
functional-seizures                        6         0        0
clostridium-difficile                      5         0        0
peripheral-arterial-disease                5         0        0
statins-and-mace                           5         0        0
gout                                       0         0        5
urinary-incontinence                       4         0        0
autoimmune-disease                         3         0        0
bph                                        3         0        0
lung-cancer                                3         0        0
colorectal-cancer                          2         0        3
abdominal-aortic-aneurysm                  2         0        0
adhd                                       2         0        0
appendicitis                               2         0        0
ca-mrsa                                    2         0        0
chronic-rhinosinusitis                     2         0        0
developmental-language-disorder            2         0        0
hiv                                        2         0        1
fibromyalgia                               2         0        0
hyperthyroidism                            0         0        2
autism                                     1         0        0
carotid-atherosclerosis                    1         0        0
cataracts                                  1         0        0
diabetic-retinopathy                       1         0        0
crohns-disease                             1         0        0
multiple-sclerosis                         1         0        0
prostate-cancer                            0         0        1
rheumatoid-arthritis                       0         0        1

57/108 phenotypes have >=1 matching MIMIC patient (dx, procedure, or lab).
```
