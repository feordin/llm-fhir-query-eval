# T3 lean-for-all + age-filter guard: full refresh (108 × 3 models)

**Date:** 2026-06-10 · follows the 2026-06-07 T3 regression verdict
(`docs/results/2026-06-07-t3-regression-analysis.md`).
Data promoted to canonical; published views regenerated
(`docs/results/2026-06-10-full-108-three-model-sweep-v7.md`, `frontend/public/data/`).

## What changed

The 06-07 verdict found T3 (prepended phenotype methodology) was *helping qwen
but mildly hurting frontier models*, and traced it to two causes: (a) frontier
models got the **full ~16 KB** methodology while small models got a **lean**
variant — an unfair asymmetry; (b) a handful of **catastrophic single-cell
collapses** (over-constrained queries returning ~0 patients), amplified by n=1
agentic variance. Commit `b35ae9cc` shipped the fix:

1. **Lean methodology is now the default for ALL models** (drop the
   small-model-only gate in `run_isolated_suite.py:decide_lean`). `--full-prompt`
   opts back into the full playbook for A/B controls.
2. **Age-filter guard** (both `tier3_methodology.md` and `…_lean.md`): never add a
   `patient.birthdate` filter merely because a disease *name* contains an age word
   (neonatal/juvenile/congenital). The condition code already encodes the age
   group; the filter silently drops valid patients. This was the root cause of the
   systematic neonatal-abstinence-syndrome (NAS) collapse.

This refresh reran **all 108 phenotypes × {sonnet-4.6, gpt-5.4, opus-4.7} × T3 ×
naive/broad/expert** on the 10-server Azure FHIR fan-out (`run_t3_lean_refresh.sh`,
tagged `+T3fix`), then **promoted the `+T3fix` cells to canonical** (per-cell
latest-non-empty dedup; tier-1/2 cells untouched).

## Smoke test first — gains hold

Before spending the full sweep, the 5 phenotypes that collapsed under full
methodology were rerun under lean+guard. Comprehensive-cell F1 (mean over the 3
prompts), vs the 06-07 verdict's documented numbers:

| Phenotype | sonnet +T3fix | gpt +T3fix |
|---|---|---|
| glaucoma | 0.976 | 0.976 |
| neonatal-abstinence-syndrome | 0.983 | 0.673 |
| tuberculosis | 1.000 | 0.958 |
| iron-deficiency-anemia | 0.931 | 0.926 |
| febrile-neutropenia-pediatric | 0.516 | 0.516 |
| **5-pheno mean** | **0.881** | **0.810** |

vs original full-T3 (sonnet 0.603 / gpt 0.684) and the lean target
(0.807 / 0.752): the refresh **beats the lean target on both models**. NAS sonnet
broad/expert recovered to 1.000 (was R=0.011) with the model explicitly logging
*"Age filter NOT applied — 'neonatal' is encoded in the condition itself."*

## Full refresh — comprehensive cell (the headline cohort)

Paired comparison on the 79–80 phenotypes that have a `-comprehensive` case,
canonical full-methodology vs promoted lean+guard:

| Model | full-methodology | lean+guard | Δ |
|---|---|---|---|
| sonnet-4.6 | 0.942 | **0.950** | +0.008 |
| gpt-5.4 | 0.944 | **0.960** | +0.016 |
| opus-4.7 | — | **0.939** | (no prior T3) |

The small mean delta hides the real effect — most cells were already ~1.0. The
fix **converts the catastrophic collapses into wins**:

- **sonnet:** tuberculosis +0.37, glaucoma +0.34, NAS +0.33, iron-deficiency-anemia +0.28
- **gpt:** NAS +0.64, febrile-neutropenia +0.24, warfarin +0.14

### No guard-induced harm

The only sonnet "regressions" (post-event-pain −0.21, liver-cancer-staging −0.21,
liver-cancer −0.19) were investigated and are **not** caused by the age guard:

- **post-event-pain** dips via *under*-recall (R=0.13 on naive/broad) — wrong/thin
  codes on the lay prompt. Suppressing an age filter would lower *precision*, not
  recall, so the guard is not implicated.
- **liver-cancer** lean+guard queries are excellent (naive R=0.99, expert R=1.00)
  with **no birthdate filter present** — the guard behaved correctly; the dip is
  broad-prompt code coverage (R=0.78).

Residual sub-0.5 cells (febrile-neutropenia, post-event-pain, warfarin,
liver-cancer-staging) are **identical across all three models** and only on
*naive/broad* (never expert) — i.e. genuine prompt-difficulty floors where lay
phrasing under-specifies a hard phenotype, not a methodology or model artifact.

## Full refresh — all 388 test cases (v7 leaderboard)

| Model | T1 closed-book | T2 agentic+tools | T3 +methodology | vs v6 T3 |
|---|---|---|---|---|
| `copilot:claude-opus-4.7` | 0.703 ⚠ | 0.904 ⚠ | **0.867** | *new* |
| `copilot:claude-sonnet-4.6` | 0.623 | 0.846 | **0.857** | 0.851 (+0.006) |
| `copilot:gpt-5.4` | 0.656 | 0.878 | **0.884** | 0.871 (+0.013) |
| `openai-compat:qwen-qwen3.5-9b` | 0.257 | 0.476 | 0.710 | unchanged |

The all-test-case T3 gain is modest because dx/meds/labs cells were already strong;
the fix's leverage is concentrated in the comprehensive collapses above. qwen is
unchanged — it was already on the lean methodology, which is exactly why the
"lean for all" change is a no-op for it and a net win for the frontier models.

> ⚠ **opus coverage caveat:** opus T3 is full coverage (388 test cases, this
> refresh). opus **T1/T2 are partial** — only 48 test cases each, carried over from
> the earlier skill-baseline experiment. Treat opus T3=0.867 as the trustworthy
> number; opus T1/T2 are not comparable to sonnet/gpt full coverage and should be
> backfilled before being quoted.

## Variance caveat (unchanged from 06-07)

Each cell is still **one** non-deterministic agentic run. The verdict's guidance
holds: **use n≥3 (median) before trusting any sub-0.05 tier delta.** The
comprehensive collapse-recoveries here (+0.3 to +0.6) are far above that noise
floor; the all-test-case +0.006/+0.013 frontier deltas are within it (directionally
positive, with the collapses provably fixed).

## Reproduce

```bash
# the refresh (free copilot models are wall-clock-only; opus is PREMIUM quota)
bash scripts/run_t3_lean_refresh.sh                 # 108 × 3 models × T3, tagged +T3fix

# promote +T3fix tier-3 cells to canonical (copy with suffix stripped), then rebuild
#   views excluding all experiment-suffix specs:
python scripts/build_frontend_data.py --since 20260516T000000Z \
    --exclude-models ollama +T3fix +T3lean +T3rerun +fhirskill --stamp <now>
python scripts/aggregate_sweep.py --since 20260516T000000Z \
    --label full-108-three-model-sweep-v7 \
    --exclude-models ollama +T3fix +T3lean +T3rerun +fhirskill --phenotypes <all 108>
```

## Next

- Backfill opus T1/T2 to full 388-test-case coverage so its row is comparable.
- n≥3 repeat runs on the residual sub-0.5 naive/broad cells to separate
  prompt-difficulty floor from single-run variance.
- Ship the lean playbook + age-filter guard as the methodology core of the
  shareable fhir-phenotyping plugin (already specced).
