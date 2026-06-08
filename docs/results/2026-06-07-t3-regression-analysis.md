# Why did T3 (methodology) hurt the frontier models but help qwen?

**Date:** 2026-06-07  ·  **Task #5** (dev-days analysis)
Data: `docs/results/2026-06-07-per-testcase-grids.csv` (cutoff 0516, non-empty-wins).

## The headline
| Model | T2 | T3 | Δ |
|---|---|---|---|
| claude-sonnet-4.6 | 0.917 | 0.896 | **−0.021** |
| gpt-5.4 | 0.914 | 0.906 | **−0.008** |
| qwen3.5-9b | 0.529 | 0.779 | **+0.250** |

## Finding 1 — the frontier "regression" is NOT broad; it's a few catastrophic cells
On comprehensive cases, sonnet T3 **regressed on 12, improved on 11, ~tied on 57**
(gpt: 11 / 5 / 64). So T3 is roughly neutral on most cases — the negative mean is
dragged down by a small number of **single-cell collapses** where the query matched
almost nothing:

- `neonatal-abstinence-syndrome` sonnet **T3/broad**: R=**0.011** (68 / 6250) vs T2/broad R=0.91
- `glaucoma` sonnet **T3/expert**: R=**0.0** (0 / 218) vs T2/expert R=1.0 (perfect)
- worst sonnet comp regressions: glaucoma −0.33, tuberculosis −0.33, NAS −0.31, iron-deficiency-anemia −0.28
- worst gpt: NAS −0.33, febrile-neutropenia −0.24

These are recall collapses (precision usually stays 1.0) — the model emitted an
**over-constrained or wrong query that found ~0 patients**, where the simpler T2
agentic run succeeded.

## Finding 2 — qwen and frontier got DIFFERENT methodology (the key asymmetry)
Auto-lean fires for small models (`qwen3.5-9b` ∈ `SMALL_MODEL_PATTERNS`): **qwen got
the LEAN methodology**, **frontier got the FULL ~16 KB `tier3_methodology.md`**.
So the comparison isn't apples-to-apples. Qwen lacks baseline FHIR/phenotyping
competence, so even the lean playbook is a big lift (+0.25). The frontier models
already know the methodology, so the full playbook adds length/constraints that are
net-neutral and **occasionally backfire** into a catastrophic query.

## Finding 3 — confounded by single-run agentic variance (n=1 per cell)
Each cell is **one** non-deterministic agentic run. A few unlucky T3 runs (the
collapses above) are enough to swing a per-phenotype mean by 0.3. The −0.02 frontier
gap is within what single-run variance can produce — we cannot currently distinguish
"methodology systematically hurts" from "two agentic runs diverged by chance,"
because we don't have repeated runs per cell.

## Answers to the questions
- **Why help qwen, hurt frontier?** Qwen lacks competence → (lean) methodology fills
  the gap. Frontier already competent → full methodology is net-neutral with rare
  backfires; n=1 variance amplifies those into the headline −0.02.
- **Should we have run lean for everyone?** Likely worth testing — the lean prompt
  is shorter and less likely to over-direct. This is the cleanest next experiment.
- **Was there another problem?** Yes, two: (a) the **asymmetric prompt** (lean vs
  full) makes the qwen-vs-frontier T3 comparison unfair; (b) **n=1** makes the small
  frontier gap statistically fragile.
- **How to improve?**
  1. **Run frontier T3 with `--lean-prompt`** on the regressed phenotypes and compare
     (cheap via Copilot) — tests whether the full playbook is the cause.
  2. **Repeat runs per cell** (e.g., 3×, take median/mean) to quench agentic variance
     before trusting any sub-0.05 tier delta.
  3. **Inspect the catastrophic queries** (glaucoma/NAS/TB) to see which methodology
     instruction triggers the over-constrained/0-result query, and tighten it.
  4. Consider a **shorter, targeted methodology** for capable models (or drop T3 for
     frontier and report T2 as their ceiling, which the leaderboard already does).

## For the deck
Lead with: *"methodology is a big lever for a small open model (+25 pts) and roughly
neutral for frontier models, where its only effect is a handful of variance-driven
query collapses."* That's the honest, defensible story — and it motivates the
follow-up experiments above rather than over-claiming "methodology hurts."

## Experiment C — inspecting the catastrophic queries (2026-06-07)
The collapses are NOT one failure mode:

- **neonatal-abstinence-syndrome, sonnet T3/broad (68 / 6250):** codes correct, but
  the methodology/reasoning injected a spurious filter
  `&patient.birthdate=ge2025-06-02` ("NAS is neonatal → recent birth"). The synthetic
  cohort spans many birth years, so this over-constraint killed recall. T2 didn't add
  it and found all 6250. **→ real methodology-induced over-constraint.**
- **glaucoma, sonnet T3/expert (0 / 218):** the emitted SNOMED codes are *exactly*
  the gold codes (84494001/23986001/392288006), yet 0 results. The raw response shows
  the agent's tool calls hit `null` server totals during exploration ("No server
  totals… paged beyond the first 10"). **→ looks like an agentic/server-state variance
  fluke, not a methodology error.**

So "why isn't T3 better" is multi-causal: partly methodology over-constraint, partly
single-run agentic/server variance. Experiments A (full-T3 rerun = variance test) and
B (lean-T3 = "lean for all?") are running to quantify which dominates per phenotype.

## VERDICT — Experiments A (full-T3 rerun) + B (lean-T3), 2026-06-07
Three-way mean F1 on the 5 regressed phenotypes (comprehensive T3):

| model | original | full-T3 rerun | lean-T3 |
|---|---|---|---|
| sonnet | 0.603 | 0.727 | **0.807** |
| gpt-5.4 | 0.684 | 0.595 | **0.752** |

1. **Variance is large.** glaucoma swings 0.60→0.93 (sonnet rerun) and 0.94→0.80→1.00
   (gpt); NAS-gpt 0.35→0.02. Several "regressions" were unlucky single runs — n=1
   inflated the apparent T3<T2 gap. **Use n≥3 before trusting sub-0.05 tier deltas.**
2. **Lean for all = YES.** Lean matches or beats both original and a fresh full run in
   every cell, and fixes the full-methodology over-constraints (IDA-sonnet 0.65→0.93,
   febrile-neutropenia-gpt 0.27→0.52). It never meaningfully hurts. **Recommend lean
   methodology as the default for ALL models, not just small ones.**
3. **Some failures are systematic.** NAS is deterministic (sonnet 0.657 across all
   three) — the `patient.birthdate` over-constraint persists under lean. **Targeted
   fix:** the methodology should not induce age/birthdate filters from "neonatal/
   pediatric" reasoning when the data spans many birth years.

### Actions
- Make lean the default T3 methodology for all models (drop the small-model-only auto-lean gate).
- Patch the methodology to suppress spurious patient.birthdate/age constraints.
- Adopt n≥3 repeat runs (median) for the headline tier comparison.
