# MIMIC-IV-on-FHIR Demo — Per-Phenotype Patient Counts

**Date:** 2026-06-05  **Dataset:** mimic-iv-clinical-database-demo-on-fhir-2.1.0 (100-patient demo)

Offline counts via `scripts/mimic_phenotype_counts.py` against the **standardized**
MIMIC data (`scripts/standardize_mimic_fhir.py`: additive dotted ICD + LOINC codings).
Method: hierarchical ICD match (phenotype category code matches MIMIC subcodes),
distinct Patient count. dx = Condition-anchored (high confidence, the headline);
proc = ICD-10-PCS (0 because our phenotype procedure codes are CPT/SNOMED, not PCS).
Labs (LOINC) not yet counted — phase 2.

```

phenotype                             dx_pts  proc_pts  #codes
----------------------------------------------------------------
resistant-hypertension                    55         0       2
hypertension                              55         0       4
coronary-heart-disease                    33         0      10
type-2-diabetes                           32         0       9
type-1-diabetes                           31         0      10
gerd                                      25         0       6
heart-failure                             24         0      38
ckd                                       23         0       9
asthma                                    21         0      24
depression                                21         0      16
severe-childhood-obesity                  20         0       7
pneumonia                                 19         0       8
atrial-fibrillation                       18         0       1
familial-hypercholesterolemia             16         0       3
asthma-response-inhaled-steroids          15         0       9
drug-induced-liver-injury                 14         0      17
hypothyroidism                            14         0       5
epilepsy                                  12         0      13
atopic-dermatitis                         11         0      12
sleep-apnea                                9         0       4
dementia                                   9         0      30
clopidogrel-poor-metabolizers              8         0       7
venous-thromboembolism                     8         0      22
nafld                                      7         0       6
migraine                                   7         0      22
breast-cancer                              6         0       7
functional-seizures                        6         0       4
clostridium-difficile                      5         0       1
peripheral-arterial-disease                5         0       4
statins-and-mace                           5         0       7
urinary-incontinence                       4         0       4
autoimmune-disease                         3         0       9
bph                                        3         0       2
lung-cancer                                3         0       4
abdominal-aortic-aneurysm                  2         0       6
adhd                                       2         0      11
appendicitis                               2         0       9
ca-mrsa                                    2         0       3
chronic-rhinosinusitis                     2         0       5
colorectal-cancer                          2         0      19
developmental-language-disorder            2         0      18
febrile-neutropenia-pediatric              2         0       7
hiv                                        2         0       4
fibromyalgia                               2         0       4
autism                                     1         0       8
carotid-atherosclerosis                    1         0       2
cataracts                                  1         0       6
diabetic-retinopathy                       1         0       8
crohns-disease                             1         0      10
multiple-sclerosis                         1         0       2

50/108 phenotypes have >=1 matching MIMIC patient (dx or procedure).
```
