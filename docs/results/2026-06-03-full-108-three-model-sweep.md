# Sweep results: full-108-three-model-sweep

_Aggregated 2026-06-03 07:07Z from 835 result files (filenames since 20260602T000000Z)._

Phenotypes in scope: **108**. Models compared: **3**.

## Headline: mean F1 by tier

| Model | T1 closed-book | T2 agentic+tools | T3 +methodology | Test cases | Cells | Empty % |
|---|---|---|---|---|---|---|
| `copilot:claude-sonnet-4.6` | **0.603** | **0.843** | **0.846** | 224 | 2016 | 1.9% |
| `copilot:gpt-5.4` | **0.664** | **0.872** | **0.850** | 223 | 2007 | 2.6% |
| `openai-compat:qwen/qwen3.5-9b` | **0.263** | **0.549** | **0.737** | 388 | 2508 | 54.8% |

## Per-phenotype Tier 2 F1 (agentic+tools, mean over variants)

| Phenotype | `copilot:claude-sonnet-4.6` | `copilot:gpt-5.4` | `openai-compat:qwen/qwen3.5-9b` |
|---|---|---|---|
| `abdominal-aortic-aneurysm` | 1.000 | 1.000 | 0.773 |
| `ace-inhibitor-cough` | 0.991 | 0.884 | 0.560 |
| `adhd` | 0.867 | 0.816 | 0.500 |
| `alcohol-use-disorder` | 0.881 | 0.992 | 0.539 |
| `appendicitis` | 0.843 | 0.897 | 0.530 |
| `asthma-response-inhaled-steroids` | 0.486 | 0.625 | 0.400 |
| `autism` | 0.803 | 0.803 | 0.375 |
| `autoimmune-disease` | 0.349 | 0.710 | 0.200 |
| `bladder-cancer` | 1.000 | 1.000 | 0.333 |
| `bone-scan-utilization` | 0.222 | 0.333 | 0.125 |
| `bph` | 0.992 | 0.972 | 0.740 |
| `breast-cancer` | 0.778 | 0.825 | 0.351 |
| `ca-mrsa` | 0.889 | 0.994 | 0.823 |
| `cardiac-conduction-qrs` | 0.667 | 1.000 | 0.500 |
| `cardiorespiratory-fitness` | 0.250 | 0.429 | 0.250 |
| `carotid-atherosclerosis` | 0.881 | 0.989 | 0.617 |
| `cataracts` | 0.866 | 0.889 | 0.521 |
| `cervical-cancer` | 0.997 | 0.997 | 0.500 |
| `chronic-rhinosinusitis` | 0.722 | 0.806 | 0.535 |
| `clopidogrel-poor-metabolizers` | 0.521 | 0.935 | 0.507 |
| `clostridium-difficile` | 0.662 | 0.740 | 0.500 |
| `colorectal-cancer` | 0.818 | 0.885 | 0.428 |
| `cystic-fibrosis` | 1.000 | 1.000 | 0.957 |
| `developmental-language-disorder` | 0.253 | 0.253 | 0.582 |
| `diabetic-retinopathy` | 0.885 | 0.819 | 0.693 |
| `digital-rectal-exam` | 0.833 | 0.500 | 0.268 |
| `diverticulitis` | 1.000 | 1.000 | 0.875 |
| `down-syndrome` | 1.000 | 1.000 | 0.935 |
| `drug-induced-liver-injury` | 0.796 | 0.884 | 0.667 |
| `endometriosis` | 0.988 | 0.986 | 0.658 |
| `esophageal-cancer` | 1.000 | 1.000 | 0.667 |
| `familial-hypercholesterolemia` | 1.000 | 1.000 | — |
| `febrile-neutropenia-pediatric` | 0.683 | 0.658 | 0.628 |
| `functional-seizures` | 0.833 | 1.000 | 0.500 |
| `glaucoma` | 0.839 | 0.979 | — |
| `glioblastoma` | 0.667 | 1.000 | 0.538 |
| `hearing-loss` | 0.812 | 0.775 | 0.500 |
| `hepatitis-c` | 0.978 | 0.932 | 0.547 |
| `herpes-zoster` | 1.000 | 0.917 | 0.554 |
| `hiv` | 1.000 | 1.000 | 0.594 |
| `influenza` | 1.000 | 1.000 | 0.800 |
| `intellectual-disability` | 0.962 | 0.975 | — |
| `leukemia` | 1.000 | 1.000 | — |
| `liver-cancer` | 0.984 | 0.957 | 0.333 |
| `liver-cancer-staging` | 0.838 | 0.558 | — |
| `lung-cancer` | 1.000 | 1.000 | — |
| `lyme-disease` | 1.000 | 1.000 | 0.898 |
| `lymphoma` | 1.000 | 1.000 | 0.333 |
| `melanoma` | 1.000 | 1.000 | — |
| `multimodal-analgesia` | 0.667 | 0.667 | 0.500 |
| `multiple-myeloma` | 1.000 | 1.000 | 0.836 |
| `nafld` | 0.962 | 0.962 | — |
| `neonatal-abstinence-syndrome` | 0.553 | 0.456 | — |
| `ovarian-cancer` | 0.886 | 0.947 | 0.481 |
| `pancreatic-cancer` | 0.998 | 0.998 | — |
| `peanut-allergy` | 0.664 | 0.750 | 0.500 |
| `peripheral-arterial-disease` | 0.937 | 0.919 | 0.460 |
| `polycystic-kidney-disease` | 1.000 | 1.000 | 1.000 |
| `post-event-pain` | 0.497 | 0.488 | — |
| `prostate-cancer` | 1.000 | 1.000 | 0.000 |
| `renal-cancer` | 1.000 | 1.000 | 0.333 |
| `resistant-hypertension` | 0.533 | 0.705 | — |
| `sepsis` | 0.804 | 0.981 | — |
| `severe-childhood-obesity` | 0.930 | 0.966 | — |
| `sickle-cell-disease` | 0.974 | 0.982 | — |
| `sleep-apnea` | 0.840 | 0.866 | 0.512 |
| `statins-and-mace` | 0.964 | 0.964 | — |
| `steroid-induced-avn` | 0.994 | 0.883 | — |
| `stomach-cancer` | 1.000 | 1.000 | — |
| `thyroid-cancer` | 1.000 | 1.000 | — |
| `tuberculosis` | 0.875 | 0.986 | 0.813 |
| `urinary-incontinence` | 0.995 | 0.917 | — |
| `warfarin-dose-response` | 0.583 | 0.570 | — |

## Per-variant breakdown (mean F1)

### `copilot:claude-sonnet-4.6`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.458 | 0.533 | 0.819 |
| T2 | 0.853 | 0.875 | 0.802 |
| T3 | 0.844 | 0.870 | 0.823 |

### `copilot:gpt-5.4`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.499 | 0.636 | 0.855 |
| T2 | 0.837 | 0.860 | 0.917 |
| T3 | 0.798 | 0.851 | 0.902 |

### `openai-compat:qwen/qwen3.5-9b`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.081 | 0.139 | 0.568 |
| T2 | 0.371 | 0.418 | 0.829 |
| T3 | 0.724 | 0.673 | 0.807 |

