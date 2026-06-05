# Sweep results: full-108-three-model-sweep-v3

_Aggregated 2026-06-05 07:34Z from 1421 result files (filenames since 20260527T000000Z; cell-level non-empty-wins dedup)._

Phenotypes in scope: **108**. Models compared: **4**.

## Headline: mean F1 by tier

| Model | T1 closed-book | T2 agentic+tools | T3 +methodology | Test cases | Cells | Empty % |
|---|---|---|---|---|---|---|
| `copilot:claude-sonnet-4.6` | **0.627** | **0.854** | **0.852** | 292 | 2628 | 1.8% |
| `copilot:gpt-5.4` | **0.674** | **0.883** | **0.868** | 291 | 2619 | 2.6% |
| `ollama:qwen3.5-9b` | **0.409** | **0.715** | **0.662** | 146 | 1083 | 19.3% |
| `openai-compat:qwen-qwen3.5-9b` | **0.281** | **0.487** | **0.710** | 388 | 3492 | 16.6% |

## Per-phenotype Tier 2 F1 (agentic+tools, mean over variants)

| Phenotype | `copilot:claude-sonnet-4.6` | `copilot:gpt-5.4` | `ollama:qwen3.5-9b` | `openai-compat:qwen-qwen3.5-9b` |
|---|---|---|---|---|
| `abdominal-aortic-aneurysm` | 1.000 | 1.000 | — | 0.808 |
| `ace-inhibitor-cough` | 0.991 | 0.884 | — | 0.469 |
| `acute-kidney-injury` | 0.986 | 0.986 | 0.972 | 0.525 |
| `adhd` | 0.867 | 0.816 | — | 0.653 |
| `alcohol-use-disorder` | 0.881 | 0.992 | — | 0.727 |
| `anxiety` | — | — | — | 0.220 |
| `appendicitis` | 0.843 | 0.897 | — | 0.695 |
| `asthma` | — | — | 0.500 | 0.287 |
| `asthma-response-inhaled-steroids` | 0.486 | 0.625 | — | 0.375 |
| `atopic-dermatitis` | 0.920 | 0.876 | 1.000 | 0.388 |
| `atrial-fibrillation` | — | — | 0.814 | 0.095 |
| `autism` | 0.803 | 0.803 | — | 0.431 |
| `autoimmune-disease` | 0.349 | 0.710 | — | 0.167 |
| `bipolar-disorder` | — | — | — | 0.514 |
| `bladder-cancer` | 1.000 | 1.000 | — | 0.333 |
| `bone-scan-utilization` | 0.222 | 0.333 | — | 0.135 |
| `bph` | 0.992 | 0.972 | — | 0.533 |
| `breast-cancer` | 0.778 | 0.825 | — | 0.214 |
| `ca-mrsa` | 0.889 | 0.994 | — | 0.707 |
| `cardiac-conduction-qrs` | 0.667 | 1.000 | — | 0.167 |
| `cardiorespiratory-fitness` | 0.250 | 0.429 | — | 0.125 |
| `carotid-atherosclerosis` | 0.881 | 0.989 | — | 0.417 |
| `cataracts` | 0.866 | 0.889 | — | 0.361 |
| `cervical-cancer` | 0.997 | 0.997 | — | 0.624 |
| `chronic-rhinosinusitis` | 0.722 | 0.806 | — | 0.583 |
| `ckd` | — | — | 0.725 | 0.453 |
| `clopidogrel-poor-metabolizers` | 0.521 | 0.935 | — | 0.645 |
| `clostridium-difficile` | 0.662 | 0.740 | — | 0.478 |
| `colorectal-cancer` | 0.818 | 0.885 | — | 0.446 |
| `copd` | — | — | 0.990 | 0.779 |
| `coronary-heart-disease` | — | — | 0.493 | 0.456 |
| `crohns-disease` | 0.875 | 0.882 | 0.560 | 0.432 |
| `cystic-fibrosis` | 1.000 | 1.000 | — | 0.667 |
| `dementia` | — | — | 0.706 | 0.497 |
| `depression` | — | — | 0.750 | 0.525 |
| `developmental-language-disorder` | 0.253 | 0.253 | — | 0.334 |
| `diabetic-retinopathy` | 0.885 | 0.819 | — | 0.545 |
| `digital-rectal-exam` | 0.833 | 0.500 | — | 0.404 |
| `diverticulitis` | 1.000 | 1.000 | — | 0.819 |
| `down-syndrome` | 1.000 | 1.000 | — | 0.623 |
| `drug-induced-liver-injury` | 0.796 | 0.884 | — | 0.536 |
| `endometriosis` | 0.988 | 0.986 | — | 0.550 |
| `epilepsy` | — | — | 0.656 | 0.275 |
| `esophageal-cancer` | 1.000 | 1.000 | — | 0.333 |
| `familial-hypercholesterolemia` | 1.000 | 1.000 | — | 0.362 |
| `febrile-neutropenia-pediatric` | 0.683 | 0.658 | — | 0.733 |
| `fibromyalgia` | 0.647 | 0.739 | 0.429 | 0.469 |
| `functional-seizures` | 0.833 | 1.000 | — | 0.167 |
| `gerd` | 0.980 | 0.995 | 0.670 | 0.442 |
| `glaucoma` | 0.839 | 0.979 | — | 0.646 |
| `glioblastoma` | 0.667 | 1.000 | — | 0.333 |
| `gout` | 0.820 | 0.986 | 0.872 | 0.561 |
| `hearing-loss` | 0.812 | 0.775 | — | 0.400 |
| `heart-failure` | — | — | 0.453 | 0.287 |
| `hepatitis-c` | 0.978 | 0.932 | — | 0.416 |
| `herpes-zoster` | 1.000 | 0.917 | — | 0.750 |
| `hiv` | 1.000 | 1.000 | — | 0.421 |
| `hypertension` | — | — | 0.383 | 0.446 |
| `hyperthyroidism` | — | — | 0.915 | 0.647 |
| `hypothyroidism` | — | — | 0.616 | 0.413 |
| `influenza` | 1.000 | 1.000 | — | 0.667 |
| `intellectual-disability` | 0.962 | 0.975 | — | 0.373 |
| `iron-deficiency-anemia` | 0.771 | 0.900 | 0.862 | 0.638 |
| `leukemia` | 1.000 | 1.000 | — | 0.333 |
| `liver-cancer` | 0.984 | 0.957 | — | 0.634 |
| `liver-cancer-staging` | 0.838 | 0.558 | — | 0.694 |
| `lung-cancer` | 1.000 | 1.000 | — | 0.333 |
| `lyme-disease` | 1.000 | 1.000 | — | 0.803 |
| `lymphoma` | 1.000 | 1.000 | — | 0.579 |
| `melanoma` | 1.000 | 1.000 | — | 0.333 |
| `migraine` | — | — | 0.634 | 0.312 |
| `multimodal-analgesia` | 0.667 | 0.667 | — | 0.333 |
| `multiple-myeloma` | 1.000 | 1.000 | — | 1.000 |
| `multiple-sclerosis` | 0.993 | 0.995 | 0.996 | 0.481 |
| `nafld` | 0.962 | 0.962 | — | 0.260 |
| `neonatal-abstinence-syndrome` | 0.553 | 0.456 | — | 0.545 |
| `osteoporosis` | 0.874 | 0.917 | 0.866 | 0.643 |
| `ovarian-cancer` | 0.886 | 0.947 | — | 0.563 |
| `pancreatic-cancer` | 0.998 | 0.998 | — | 0.445 |
| `parkinsons-disease` | 0.992 | 0.992 | 0.990 | 0.534 |
| `peanut-allergy` | 0.664 | 0.750 | — | 0.432 |
| `peripheral-arterial-disease` | 0.937 | 0.919 | — | 0.416 |
| `pneumonia` | 0.939 | 0.780 | 0.775 | 0.544 |
| `polycystic-kidney-disease` | 1.000 | 1.000 | — | 0.584 |
| `post-event-pain` | 0.497 | 0.488 | — | 0.974 |
| `prostate-cancer` | 1.000 | 1.000 | — | 0.494 |
| `psoriasis` | 0.867 | 0.981 | 0.990 | 0.691 |
| `renal-cancer` | 1.000 | 1.000 | — | 0.333 |
| `resistant-hypertension` | 0.533 | 0.705 | — | 0.604 |
| `rheumatoid-arthritis` | — | — | — | 0.372 |
| `schizophrenia` | 0.960 | 0.942 | 1.000 | 0.854 |
| `sepsis` | 0.804 | 0.981 | — | 0.539 |
| `severe-childhood-obesity` | 0.930 | 0.966 | — | 0.330 |
| `sickle-cell-disease` | 0.974 | 0.982 | — | 0.484 |
| `sleep-apnea` | 0.840 | 0.866 | — | 0.333 |
| `statins-and-mace` | 0.964 | 0.964 | — | 0.718 |
| `steroid-induced-avn` | 0.994 | 0.883 | — | 0.883 |
| `stomach-cancer` | 1.000 | 1.000 | — | 0.667 |
| `stroke` | — | — | 0.497 | 0.540 |
| `systemic-lupus-erythematosus` | 0.926 | 0.806 | 0.921 | 0.360 |
| `thyroid-cancer` | 1.000 | 1.000 | — | 0.667 |
| `tuberculosis` | 0.875 | 0.986 | — | 0.764 |
| `type-1-diabetes` | — | — | 0.804 | 0.337 |
| `type-2-diabetes` | — | — | 0.803 | 0.358 |
| `ulcerative-colitis` | 0.773 | 0.995 | 0.989 | 0.851 |
| `urinary-incontinence` | 0.995 | 0.917 | — | 0.353 |
| `venous-thromboembolism` | 0.901 | 0.947 | 0.657 | 0.540 |
| `warfarin-dose-response` | 0.583 | 0.570 | — | 0.560 |

## Per-variant breakdown (mean F1)

### `copilot:claude-sonnet-4.6`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.489 | 0.560 | 0.833 |
| T2 | 0.866 | 0.888 | 0.809 |
| T3 | 0.854 | 0.885 | 0.818 |

### `copilot:gpt-5.4`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.504 | 0.658 | 0.860 |
| T2 | 0.844 | 0.881 | 0.922 |
| T3 | 0.823 | 0.874 | 0.909 |

### `ollama:qwen3.5-9b`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.442 | 0.400 | 0.385 |
| T2 | 0.615 | 0.640 | 0.851 |
| T3 | 0.635 | 0.523 | 0.803 |

### `openai-compat:qwen-qwen3.5-9b`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.088 | 0.148 | 0.604 |
| T2 | 0.325 | 0.341 | 0.786 |
| T3 | 0.637 | 0.658 | 0.833 |

