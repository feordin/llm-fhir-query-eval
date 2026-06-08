# What moves the needle: prompt quality vs tooling (dev-days centerpiece)

**Date:** 2026-06-07. Comprehensive ("all-patients") cohort, mean F1 over each
phenotype's comprehensive cell. Source: `2026-06-07-per-testcase-grids.csv`.

## Prompt × Tier matrix (F1)
| model | naive·T1 | naive·T2 | naive·T3 | expert·T1 | expert·T2 | expert·T3 |
|---|---|---|---|---|---|---|
| sonnet | 0.738 | 0.925 | 0.920 | 0.887 | 0.982 | 0.952 |
| gpt-5.4 | 0.627 | 0.907 | 0.902 | 0.881 | 0.998 | 0.995 |
| qwen3.5-9b | 0.106 | 0.479 | 0.772 | 0.460 | 0.738 | 0.919 |

## Worst → best (dynamic range)
- Frontier: worst (naive+T1) 0.63–0.74 → best (expert+T2) 0.98–1.00.
- qwen: worst 0.106 (closed-book + naive ≈ useless) → best 0.919 (expert+T3). ~8×.

## Do you need the expert prompt? (with tools, no)
At T2: naive 0.91–0.93, **broad 0.95**, expert 0.98–1.00 for frontier. A broad
(clinically-aware, NO codes) prompt + tools already ≈ 95%; the code-aware expert
prompt adds only the last ~+0.05.

## Can T2/T3 rescue a naive prompt? (frontier: yes)
- naive+T2 = 0.925 (sonnet) / 0.907 (gpt) — agentic loop recovers an untrained-user
  prompt to near-best. The naive→expert gap collapses from ~0.15 (T1) to ~0.06 (T2).
- qwen: naive+T2 only 0.48, but naive+**T3** 0.77 — methodology is what lets the
  small model recover a naive prompt.

## Lever impact (Opus 8-pheno subset, FINAL — T1-plain run complete)
Baseline = Opus one-shot closed-book 0.885 (comprehensive). Prompt × lever:
| prompt | T1 plain | T1 +skill | T2 ours |
|---|---|---|---|
| naive | 0.888 | 0.882 | 0.987 |
| broad | 0.881 | 0.898 | 0.985 |
| expert | 0.885 | 0.880 | 0.993 |

- Better prompt (naive→expert): **−0.002** (≈ nothing)
- + Anthropic FHIR skill: **+0.002** (≈ nothing — Opus already knows FHIR)
- + our agentic tools (T2): **+0.104** (the only lever that moves)

(NB: earlier +0.077 skill / +0.179 tools were from a PARTIAL run with T1-plain
biased low; the complete run shows skill≈0 and tools≈+0.10. For a frontier model
only tools matter; for the weaker qwen, prompt AND methodology both matter a lot.)

## Headline
**Tools collapse the prompt gap.** Closed-book is brutally prompt-sensitive; the
agentic loop makes prompt sophistication nearly irrelevant for frontier models.
A layperson typing "find diabetics" + our agent ≈ an expert hand-writing codes
(0.93 vs 0.98). Tooling > skill > prompt — and the better the tooling, the less
the prompt matters. This is the practical case for the agentic approach.
