# MIMIC full-sweep repeat-run variance (n=3, Opus T2/T3)

**Date:** 2026-09-02 (runs executed 2026-09-01; analyzed 2026-09-02)
**Runs:** r1 = full-sweep originals (2026-08-31/09-01), r2, r3 (both 2026-09-01)
**Model:** claude-opus-4.7 (copilot), full MIMIC-IV-on-FHIR dataset
**Scope:** 12 phenotypes × {dx, comprehensive} × {naive, broad, expert} × {T2, T3}
= 138 cells with ≥2 runs (120 with all 3). Repeated phenotypes:
abdominal-aortic-aneurysm, coronary-heart-disease, down-syndrome, epilepsy,
gout, heart-failure, hypertension, iron-deficiency-anemia, nafld, sepsis,
stroke, type-2-diabetes.

## Headline

Individual agentic cells are noisy; aggregate tier means are stable.

| Statistic | Value |
|---|---|
| Per-cell F1 SD — mean / median / max | 0.086 / 0.038 / 0.577 |
| Per-cell F1 range — mean / median | 0.153 / 0.072 |
| Cells with range ≤ 0.05 | 59/138 (43%) |
| Cells with range ≤ 0.10 | 79/138 (57%) |
| Cells with range > 0.50 | 9/138 (7%) |
| Mean F1 by run over the 120 common cells | r1 0.394, r2 0.426, r3 0.413 |
| Run-to-run spread of the aggregate mean | ~0.03 |
| SEM of a 138-cell tier mean (from per-cell SDs) | ~0.007 |

## Interpretation

- **Tail, not body:** the median cell moves only 0.07 F1 across runs; the mean
  is dragged by a 7% tail of high-swing cells. In 6 of the 9 cells with range
  > 0.5, one run scored exactly 0.0 — the agent emitted a query returning zero
  patients (wrong code system or over-narrow enumeration) on one attempt and
  succeeded on others. This is the same zero-result failure mode the sweep
  report documents, appearing stochastically per run.
- **Aggregate stability:** identical-cell tier means differ by ≤0.032 across
  the three runs, so sweep-level conclusions with deltas ≥ ~0.05 are outside
  run-to-run noise; the headline levers in the manuscript (+0.23 to +0.60)
  are an order of magnitude above it.
- **Consequence for single cells:** any per-phenotype or per-cell comparison
  (e.g., one phenotype's T2 vs T3) should not be interpreted at n=1;
  worst-case observed swing is 1.00 → 0.00 (down-syndrome dx, T2 broad, r3).

## Reproduction

Repeat artifacts: `results/*+mimic-r2-*.json`, `results/*+mimic-r3-*.json`
(r1 = the same test cases' `*+mimic-2026083*/2026090*` files; June `+mimic`
files are the 100-patient demo and must be excluded). Analysis pairs cells on
(test_case, tier, prompt_variant). Raw sweep logs: `logs/mimic-repeats/`.
