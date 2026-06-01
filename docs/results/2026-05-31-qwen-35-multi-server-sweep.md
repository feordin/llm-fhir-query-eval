# Sweep results: qwen-35-multi-server-sweep

_Aggregated 2026-05-31 08:20Z from 164 result files (filenames since 20260531T030000Z)._

Phenotypes in scope: **35**. Models compared: **1**.

## Headline: mean F1 by tier

| Model | T1 closed-book | T2 agentic+tools | T3 +methodology | Test cases | Cells | Empty % |
|---|---|---|---|---|---|---|
| `openai-compat:qwen/qwen3.5-9b` | — | **0.460** | **0.685** | 164 | 984 | 6.5% |

## Per-phenotype Tier 2 F1 (agentic+tools, mean over variants)

| Phenotype | `openai-compat:qwen/qwen3.5-9b` |
|---|---|
| `acute-kidney-injury` | 0.525 |
| `anxiety` | 0.224 |
| `asthma` | 0.082 |
| `atopic-dermatitis` | 0.218 |
| `atrial-fibrillation` | 0.134 |
| `bipolar-disorder` | 0.421 |
| `ckd` | 0.529 |
| `copd` | 0.936 |
| `coronary-heart-disease` | 0.504 |
| `crohns-disease` | 0.521 |
| `dementia` | 0.340 |
| `depression` | 0.509 |
| `epilepsy` | 0.217 |
| `fibromyalgia` | 0.469 |
| `gerd` | 0.342 |
| `gout` | 0.561 |
| `heart-failure` | 0.287 |
| `hypertension` | 0.448 |
| `hyperthyroidism` | 0.647 |
| `hypothyroidism` | 0.506 |
| `iron-deficiency-anemia` | 0.638 |
| `migraine` | 0.312 |
| `multiple-sclerosis` | 0.481 |
| `osteoporosis` | 0.701 |
| `parkinsons-disease` | 0.601 |
| `pneumonia` | 0.544 |
| `psoriasis` | 0.691 |
| `rheumatoid-arthritis` | 0.396 |
| `schizophrenia` | 0.854 |
| `stroke` | 0.540 |
| `systemic-lupus-erythematosus` | 0.360 |
| `type-1-diabetes` | 0.337 |
| `type-2-diabetes` | 0.418 |
| `ulcerative-colitis` | 0.851 |
| `venous-thromboembolism` | 0.489 |

## Per-variant breakdown (mean F1)

### `openai-compat:qwen/qwen3.5-9b`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | — | — | — |
| T2 | 0.290 | 0.346 | 0.736 |
| T3 | 0.586 | 0.632 | 0.830 |

