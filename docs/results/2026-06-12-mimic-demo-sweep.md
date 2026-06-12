# MIMIC-IV demo sweep: does it hold on real data?

**Date:** 2026-06-12 · Opus (`copilot:claude-opus-4.7`), MIMIC-IV-on-FHIR **100-patient
demo**, loaded via `$import` onto 9 Azure FHIR servers, scored against
MIMIC-derived gold cohorts (`scripts/recompute_mimic_gold.py` + `run_mimic_eval.py`).
57 phenotypes with a MIMIC cohort × {dx, comprehensive} × naive/broad/expert × T1/T2/T3.

## Headline — synthetic vs real (Opus, mean F1 by tier)

| Tier | **MIMIC demo (real)** | Synthetic (full 388) |
|---|---|---|
| **T1 closed-book** | **0.090** | 0.679 |
| **T2 agentic+tools** | **0.688** | 0.862 |
| **T3 +methodology** | **0.662** | 0.867 |

**The result holds on real data — and the tools lever is *bigger*.** The closed-book→
agentic jump is **+0.60 on MIMIC** (0.09 → 0.69) versus **+0.18 on synthetic**. Tools
don't just recover *codes* on real data — they recover the *coding system itself*.

## Why T1 collapses on real data (the key finding)

Closed-book Opus queries clinical concepts in **SNOMED CT** — but **MIMIC carries only
ICD-9-CM / ICD-10-CM** (no SNOMED on any Condition). So a closed-book query matches
**nothing** (T1 dx = 0.029). Our *synthetic* data is multi-coded (SNOMED + ICD), which is
exactly why closed-book scores 0.68 there: the model's SNOMED guess hits. **Real EHR data
is single-system, and it isn't the system the model defaults to.**

Worked example — **hypertension**:
- **T1 (closed-book):** queries SNOMED `38341003` etc. → **0 patients, F1 0.0**.
- **T2 (agentic):** samples the server, discovers ICD-9 **and** ICD-10, enumerates the whole
  hypertension family (I10–I16, 401–405) → **55/55 recall, F1 0.89**.

## Granular ICD: enumeration, not category match

MIMIC uses fully-specified ICD codes (E11.9, E11.42, E11.21, E11.621…) and the server does
**exact** token matching with **no `code:below` hierarchy**. A category query (`E11`) matches
nothing; the agent must **sample the server and enumerate the present subcodes**. This is a
real test of introspection that synthetic data (coded at the category our gold uses) doesn't
exercise.

## Honest nuances

- **Recovery is incomplete & noisy.** ~**18–20%** of T2/T3 cells still score ~0 — the agentic
  loop doesn't always discover/enumerate the right granular ICD. Real-world recall is harder
  than the controlled synthetic case.
- **The expert prompt *underperforms* on MIMIC.** T2 by variant: **broad 0.76 > naive 0.70 >
  expert 0.60**. The "expert" prompt's code-aware hints assume SNOMED and actively mislead on
  ICD-only data; the looser naive/broad prompts let the agent discover the real coding freely.
  (On synthetic, expert was best — the opposite.)
- **T3 ≈ T2** here (0.662 vs 0.688), consistent with the synthetic frontier finding that the
  methodology is ~neutral for a strong model.

## Caveats

- **100-patient demo**, not full credentialed MIMIC-IV. Many cohorts are tiny (1–20 patients),
  so per-cell F1 is noisy; treat tier *means* as the signal, not individual cells.
- **Dx (+comprehensive) paths only.** MIMIC meds are **NDC** and procedures **ICD-10-PCS**;
  our RxNorm / CPT-SNOMED gold codes don't crosswalk, so those paths are excluded.
- **n=1**, in-process eval with no per-cell subprocess timeout; one server (`jaerwinllm5`) was
  excluded after its data store was corrupted by setup races.

## What's next: full MIMIC-IV

Download the full credentialed MIMIC-IV-on-FHIR and re-run the *same* pipeline
(`standardize_mimic_fhir.py` → blob → `$import` → `recompute_mimic_gold.py` →
`run_mimic_demo_sweep.sh`). Larger cohorts will sharpen the means and quench the demo's
small-n noise. Optional: add NDC→RxNorm / CPT-SNOMED→ICD-10-PCS crosswalks to unlock the
med/procedure paths, and n≥3 repeats to quench agentic variance.
