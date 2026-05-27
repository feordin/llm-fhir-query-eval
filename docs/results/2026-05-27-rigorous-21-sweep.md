# Sweep results: rigorous-21-sweep

_Aggregated 2026-05-27 14:55Z from 321 result files (filenames since 20260521T200000Z)._

Phenotypes in scope: **21**. Models compared: **3**.

## Headline: mean F1 by tier

| Model | T1 closed-book | T2 agentic+tools | T3 +methodology | Test cases | Cells | Empty % |
|---|---|---|---|---|---|---|
| `copilot:claude-sonnet-4.6` | **0.624** | **0.828** | **0.850** | 107 | 963 | 2.9% |
| `copilot:gpt-5.4` | **0.601** | **0.869** | **0.882** | 107 | 963 | 2.0% |
| `ollama:qwen3.5:9b` | **0.398** | **0.643** | **0.595** | 107 | 963 | 19.2% |

## Per-phenotype Tier 2 F1 (agentic+tools, mean over variants)

| Phenotype | `copilot:claude-sonnet-4.6` | `copilot:gpt-5.4` | `ollama:qwen3.5:9b` |
|---|---|---|---|
| `anxiety` | 0.633 | 0.640 | 0.203 |
| `asthma` | 0.712 | 0.729 | 0.465 |
| `atrial-fibrillation` | 0.658 | 0.705 | 0.580 |
| `bipolar-disorder` | 0.951 | 0.972 | 0.988 |
| `ckd` | 0.933 | 0.894 | 0.532 |
| `copd` | 0.827 | 0.992 | 0.846 |
| `coronary-heart-disease` | 0.805 | 0.939 | 0.598 |
| `crohns-disease` | 0.903 | 0.915 | 0.615 |
| `dementia` | 0.800 | 0.779 | 0.587 |
| `depression` | 0.643 | 0.698 | 0.909 |
| `epilepsy` | 0.795 | 0.754 | 0.750 |
| `gerd` | 0.980 | 0.995 | 0.670 |
| `heart-failure` | 0.773 | 0.834 | 0.700 |
| `hypertension` | 0.965 | 0.961 | 0.510 |
| `hyperthyroidism` | 0.949 | 0.999 | 0.753 |
| `hypothyroidism` | 0.808 | 0.857 | 0.497 |
| `migraine` | 0.785 | 0.880 | 0.579 |
| `rheumatoid-arthritis` | 0.969 | 0.899 | 0.573 |
| `stroke` | 0.822 | 0.938 | 0.596 |
| `type-1-diabetes` | 0.825 | 0.925 | 0.769 |
| `type-2-diabetes` | 0.820 | 0.923 | 0.865 |

## Per-variant breakdown (mean F1)

### `copilot:claude-sonnet-4.6`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.515 | 0.544 | 0.813 |
| T2 | 0.800 | 0.823 | 0.861 |
| T3 | 0.827 | 0.860 | 0.862 |

### `copilot:gpt-5.4`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.413 | 0.563 | 0.827 |
| T2 | 0.838 | 0.857 | 0.911 |
| T3 | 0.872 | 0.872 | 0.902 |

### `ollama:qwen3.5:9b`

| Tier | naive | broad | expert |
|---|---|---|---|
| T1 | 0.405 | 0.434 | 0.354 |
| T2 | 0.564 | 0.525 | 0.767 |
| T3 | 0.495 | 0.545 | 0.719 |

