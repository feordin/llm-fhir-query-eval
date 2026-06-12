# Sweep results: opus-full-leaderboard

_Aggregated 2026-06-12 22:51Z from 3593 result files (filenames since 20260516T000000Z; cell-level non-empty-wins dedup)._

Phenotypes in scope: **108**. Models compared: **4**.

## Headline: mean F1 by tier

| Model | T1 closed-book | T2 agentic+tools | T3 +methodology | Test cases | Cells | Empty % |
|---|---|---|---|---|---|---|
| `copilot:claude-opus-4.7` | **0.679** | **0.862** | **0.867** | 388 | 3492 | 0.0% |
| `copilot:claude-sonnet-4.6` | **0.623** | **0.846** | **0.857** | 388 | 3492 | 1.4% |
| `copilot:gpt-5.4` | **0.656** | **0.878** | **0.884** | 388 | 3492 | 1.5% |
| `openai-compat:qwen-qwen3.5-9b` | **0.257** | **0.476** | **0.710** | 388 | 3492 | 1.1% |

## Per-phenotype Tier 2 F1 (agentic+tools, mean over variants)

| Phenotype | `copilot:claude-opus-4.7` | `copilot:claude-sonnet-4.6` | `copilot:gpt-5.4` | `openai-compat:qwen-qwen3.5-9b` |
|---|---|---|---|---|
| `abdominal-aortic-aneurysm` | 1.000 | 1.000 | 1.000 | 0.808 |
| `ace-inhibitor-cough` | 0.952 | 0.991 | 0.884 | 0.469 |
| `acute-kidney-injury` | 0.986 | 0.986 | 0.986 | 0.525 |
| `adhd` | 0.972 | 0.867 | 0.816 | 0.548 |
| `alcohol-use-disorder` | 0.992 | 0.881 | 0.992 | 0.727 |
| `anxiety` | 0.737 | 0.633 | 0.640 | 0.334 |
| `appendicitis` | 0.854 | 0.843 | 0.897 | 0.695 |
| `asthma` | 0.631 | 0.712 | 0.729 | 0.289 |
| `asthma-response-inhaled-steroids` | 0.495 | 0.486 | 0.625 | 0.333 |
| `atopic-dermatitis` | 0.957 | 0.920 | 0.876 | 0.381 |
| `atrial-fibrillation` | 0.539 | 0.658 | 0.705 | 0.432 |
| `autism` | 0.742 | 0.803 | 0.803 | 0.431 |
| `autoimmune-disease` | 0.500 | 0.349 | 0.710 | 0.167 |
| `bipolar-disorder` | 0.988 | 0.976 | 0.986 | 0.435 |
| `bladder-cancer` | 1.000 | 1.000 | 1.000 | 0.333 |
| `bone-scan-utilization` | 0.273 | 0.222 | 0.333 | 0.135 |
| `bph` | 0.952 | 0.992 | 0.972 | 0.533 |
| `breast-cancer` | 0.697 | 0.778 | 0.825 | 0.242 |
| `ca-mrsa` | 0.994 | 0.889 | 0.994 | 0.751 |
| `cardiac-conduction-qrs` | 0.500 | 0.667 | 1.000 | 0.167 |
| `cardiorespiratory-fitness` | 0.333 | 0.250 | 0.429 | 0.111 |
| `carotid-atherosclerosis` | 0.974 | 0.881 | 0.989 | 0.417 |
| `cataracts` | 0.812 | 0.866 | 0.889 | 0.495 |
| `cervical-cancer` | 0.998 | 0.997 | 0.997 | 0.624 |
| `chronic-rhinosinusitis` | 0.995 | 0.722 | 0.806 | 0.583 |
| `ckd` | 0.929 | 0.933 | 0.894 | 0.402 |
| `clopidogrel-poor-metabolizers` | 0.667 | 0.521 | 0.935 | 0.645 |
| `clostridium-difficile` | 0.746 | 0.662 | 0.740 | 0.478 |
| `colorectal-cancer` | 0.814 | 0.818 | 0.885 | 0.347 |
| `copd` | 0.955 | 0.827 | 0.992 | 0.881 |
| `coronary-heart-disease` | 0.912 | 0.805 | 0.939 | 0.368 |
| `crohns-disease` | 0.797 | 0.903 | 0.915 | 0.401 |
| `cystic-fibrosis` | 1.000 | 1.000 | 1.000 | 0.667 |
| `dementia` | 0.776 | 0.800 | 0.779 | 0.332 |
| `depression` | 0.821 | 0.643 | 0.698 | 0.402 |
| `developmental-language-disorder` | 0.254 | 0.253 | 0.253 | 0.167 |
| `diabetic-retinopathy` | 0.893 | 0.885 | 0.819 | 0.545 |
| `digital-rectal-exam` | 0.706 | 0.833 | 0.500 | 0.404 |
| `diverticulitis` | 1.000 | 1.000 | 1.000 | 0.819 |
| `down-syndrome` | 1.000 | 1.000 | 1.000 | 0.623 |
| `drug-induced-liver-injury` | 0.735 | 0.796 | 0.884 | 0.642 |
| `endometriosis` | 0.994 | 0.988 | 0.986 | 0.550 |
| `epilepsy` | 0.757 | 0.795 | 0.754 | 0.413 |
| `esophageal-cancer` | 1.000 | 1.000 | 1.000 | 0.333 |
| `familial-hypercholesterolemia` | 0.937 | 1.000 | 1.000 | 0.281 |
| `febrile-neutropenia-pediatric` | 0.726 | 0.683 | 0.658 | 0.461 |
| `fibromyalgia` | 0.739 | 0.647 | 0.739 | 0.469 |
| `functional-seizures` | 1.000 | 0.833 | 1.000 | 0.167 |
| `gerd` | 0.926 | 0.980 | 0.995 | 0.300 |
| `glaucoma` | 0.966 | 0.839 | 0.979 | 0.646 |
| `glioblastoma` | 1.000 | 0.667 | 1.000 | 0.333 |
| `gout` | 0.986 | 0.820 | 0.986 | 0.611 |
| `hearing-loss` | 0.970 | 0.812 | 0.775 | 0.537 |
| `heart-failure` | 0.815 | 0.773 | 0.834 | 0.448 |
| `hepatitis-c` | 0.868 | 0.978 | 0.932 | 0.455 |
| `herpes-zoster` | 1.000 | 1.000 | 0.917 | 0.497 |
| `hiv` | 0.983 | 1.000 | 1.000 | 0.444 |
| `hypertension` | 0.957 | 0.965 | 0.961 | 0.431 |
| `hyperthyroidism` | 0.999 | 0.949 | 0.999 | 0.626 |
| `hypothyroidism` | 0.770 | 0.808 | 0.857 | 0.460 |
| `influenza` | 1.000 | 1.000 | 1.000 | 0.667 |
| `intellectual-disability` | 1.000 | 0.962 | 0.975 | 0.500 |
| `iron-deficiency-anemia` | 0.987 | 0.771 | 0.900 | 0.638 |
| `leukemia` | 1.000 | 1.000 | 1.000 | 0.667 |
| `liver-cancer` | 0.985 | 0.984 | 0.957 | 0.396 |
| `liver-cancer-staging` | 1.000 | 0.838 | 0.558 | 0.400 |
| `lung-cancer` | 0.966 | 1.000 | 1.000 | 0.333 |
| `lyme-disease` | 1.000 | 1.000 | 1.000 | 0.803 |
| `lymphoma` | 1.000 | 1.000 | 1.000 | 0.579 |
| `melanoma` | 1.000 | 1.000 | 1.000 | 0.333 |
| `migraine` | 0.819 | 0.785 | 0.880 | 0.412 |
| `multimodal-analgesia` | 1.000 | 0.667 | 0.667 | 0.333 |
| `multiple-myeloma` | 1.000 | 1.000 | 1.000 | 1.000 |
| `multiple-sclerosis` | 0.921 | 0.993 | 0.995 | 0.388 |
| `nafld` | 0.865 | 0.962 | 0.962 | 0.368 |
| `neonatal-abstinence-syndrome` | 0.734 | 0.553 | 0.456 | 0.545 |
| `osteoporosis` | 0.874 | 0.874 | 0.917 | 0.643 |
| `ovarian-cancer` | 0.948 | 0.886 | 0.947 | 0.648 |
| `pancreatic-cancer` | 0.998 | 0.998 | 0.998 | 0.479 |
| `parkinsons-disease` | 0.992 | 0.992 | 0.992 | 0.534 |
| `peanut-allergy` | 0.747 | 0.664 | 0.750 | 0.432 |
| `peripheral-arterial-disease` | 0.844 | 0.937 | 0.919 | 0.262 |
| `pneumonia` | 0.874 | 0.939 | 0.780 | 0.461 |
| `polycystic-kidney-disease` | 1.000 | 1.000 | 1.000 | 0.584 |
| `post-event-pain` | 0.488 | 0.497 | 0.488 | 0.974 |
| `prostate-cancer` | 0.932 | 1.000 | 1.000 | 0.486 |
| `psoriasis` | 0.993 | 0.867 | 0.981 | 0.962 |
| `renal-cancer` | 1.000 | 1.000 | 1.000 | 0.333 |
| `resistant-hypertension` | 0.740 | 0.533 | 0.705 | 0.400 |
| `rheumatoid-arthritis` | 0.826 | 0.969 | 0.899 | 0.376 |
| `schizophrenia` | 0.989 | 0.960 | 0.942 | 0.854 |
| `sepsis` | 0.894 | 0.804 | 0.977 | 0.539 |
| `severe-childhood-obesity` | 0.783 | 0.930 | 0.966 | 0.303 |
| `sickle-cell-disease` | 0.907 | 0.974 | 0.982 | 0.643 |
| `sleep-apnea` | 0.845 | 0.840 | 0.866 | 0.333 |
| `statins-and-mace` | 0.983 | 0.964 | 0.964 | 0.745 |
| `steroid-induced-avn` | 0.994 | 0.994 | 0.883 | 0.742 |
| `stomach-cancer` | 1.000 | 1.000 | 1.000 | 0.667 |
| `stroke` | 0.989 | 0.822 | 0.938 | 0.545 |
| `systemic-lupus-erythematosus` | 0.891 | 0.926 | 0.806 | 0.360 |
| `thyroid-cancer` | 1.000 | 1.000 | 1.000 | 0.667 |
| `tuberculosis` | 0.986 | 0.875 | 0.986 | 0.764 |
| `type-1-diabetes` | 0.750 | 0.825 | 0.925 | 0.399 |
| `type-2-diabetes` | 0.947 | 0.820 | 0.923 | 0.358 |
| `ulcerative-colitis` | 0.995 | 0.773 | 0.995 | 0.624 |
| `urinary-incontinence` | 0.969 | 0.995 | 0.917 | 0.341 |
| `venous-thromboembolism` | 0.904 | 0.901 | 0.947 | 0.384 |
| `warfarin-dose-response` | 0.667 | 0.583 | 0.570 | 0.560 |

## Per-variant breakdown (mean F1)

### `copilot:claude-opus-4.7`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.533 | 0.644 | 0.859 |
| T2 | 0.816 | 0.868 | 0.903 |
| T3 | 0.830 | 0.869 | 0.901 |

### `copilot:claude-sonnet-4.6`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.492 | 0.554 | 0.825 |
| T2 | 0.846 | 0.870 | 0.820 |
| T3 | 0.861 | 0.871 | 0.838 |

### `copilot:gpt-5.4`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.481 | 0.634 | 0.854 |
| T2 | 0.842 | 0.873 | 0.919 |
| T3 | 0.859 | 0.883 | 0.908 |

### `openai-compat:qwen-qwen3.5-9b`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.072 | 0.150 | 0.551 |
| T2 | 0.283 | 0.363 | 0.778 |
| T3 | 0.637 | 0.683 | 0.809 |

