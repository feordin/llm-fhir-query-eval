# Full MIMIC-IV sweep: real data at scale is harder than the demo said

**Date:** 2026-09-01 · Opus (`copilot:claude-opus-4.7`), **full MIMIC-IV-on-FHIR
(299,712 patients, 42.3M resources × 10 servers)**, 105 phenotypes ×
{dx, comprehensive} × naive/broad/expert × T1/T2/T3, lean methodology.
Gold: `data/mimic-full-gold.json` (offline-recomputed patient sets). 1,592
scored cells (1 parse-failure cell). Cells: `data/mimic-full-sweep-cells.json`.

## Headline — demo vs full vs synthetic (Opus, mean F1 by tier)

| Tier | **MIMIC full (this run)** | MIMIC demo (100 pts) | Synthetic (388 tc) |
|---|---|---|---|
| **T1 closed-book** | **0.036** | 0.090 | 0.632 |
| **T2 agentic** | **0.493** | 0.688 | 0.859 |
| **T3 +methodology** | **0.462** | 0.662 | 0.860 |

Three findings, in order of importance:

1. **The tools lever survives and is still the story**: +0.46 T1→T2 (87% of
   T1 cells are exact zeros; only 11% of T2 cells are). But
2. **the demo overstated agentic recovery** (0.69 → 0.49 at full scale), and
3. **the expert prompt actively hurts on real data** — T2: broad **0.556** >
   naive 0.539 ≫ expert **0.384**. The demo showed the same ordering mildly
   (0.76/0.70/0.60); at scale the expert penalty is decisive (−0.17 vs broad).

## Why full-scale is harder: recall is capped by code-tail coverage

T2 precision stays decent (0.71); **recall (0.48) is the bottleneck**. By
gold cohort size (T2-broad):

| Gold size | n | Recall | F1 |
|---|---|---|---|
| 1–100 | 4 | 0.41 | 0.36 |
| 100–1,000 | 33 | 0.64 | 0.55 |
| 1,000–10,000 | 85 | **0.70** | **0.68** |
| 10,000+ | 55 | **0.28** | 0.39 |

At demo scale, a cohort's patients span a handful of granular ICD codes; the
agent samples, enumerates them, and recall ≈ 1. At 300k patients a large
phenotype spans a *long tail* of granular codes (E11.x alone has dozens of
populated subcodes), the sample shows only the head of the distribution, and
partial enumeration caps recall. Concept/code-tail coverage — the synthetic
benchmark's central axis — becomes brutally binding on real data.

Clean successes exist at every size below ~10k: AAA (gold 2,233), ACE-cough
(6,735), bladder cancer, melanoma, Down syndrome, multiple myeloma all hit
F1 = 1.00 at T2-broad.

## Honest accounting: some giant-cohort zeros are gold artifacts

The worst cells mix two causes that must not be conflated:

- **Genuine enumeration failure** (model's fault): e.g. large heterogeneous
  dx families where the agent enumerates the head codes only.
- **Gold-breadth artifacts** (benchmark's fault): *resistant-hypertension*
  gold prefix-matches essentially the whole hypertension family (83,947
  patients) because its test-case code list overlaps plain HTN — a model
  that correctly queries the specific I1A.0 resistant-HTN code scores ~0.
  *Severe-childhood-obesity* gold is 20,336 code-matched **adults** (age
  guards don't apply offline; MIMIC is adults-only) — a model that correctly
  adds a pediatric age filter scores ~0. *Peanut-allergy* models query
  AllergyIntolerance, a resource MIMIC-on-FHIR doesn't populate.

**Hygiene-excluded means (2026-09-01, now the primary numbers):** dropping
the three artifact phenotypes (resistant-hypertension — gold ≈ the whole HTN
family via overlapping test-case codes and a med-count criterion offline
gold can't express; severe-childhood-obesity — pediatric criterion
inapplicable to an adult dataset; peanut-allergy — AllergyIntolerance not
populated in MIMIC-on-FHIR) removes 45 cells and moves the means ~+0.01:

| Tier | All 105 | Hygiene (102) |
|---|---|---|
| T1 | 0.036 | 0.037 |
| T2 | 0.493 | **0.503** |
| T3 | 0.462 | **0.474** |

T2 by variant (hygiene): naive 0.549 / broad **0.570** / expert 0.392 — the
expert inversion is unchanged. Conclusions are insensitive to the artifacts;
they are excluded going forward for correctness, not because they moved the
story.

## Expert-prompt inversion, confirmed at scale

| Variant | T1 | T2 | T3 |
|---|---|---|---|
| naive | 0.023 | 0.539 | 0.505 |
| broad | 0.047 | **0.556** | **0.509** |
| expert | 0.037 | 0.384 | 0.372 |

On synthetic data the expert prompt is worth +0.08 over broad at T2; on real
data it costs −0.17. The expert prompt's SNOMED-centric code hints anchor
the model on a vocabulary the data doesn't carry, and (new at scale) its
precise code lists suppress the server-sampling behavior that the looser
prompts trigger. **Prompting with codes is an anti-pattern on unfamiliar
servers — describe the population, let the agent discover the coding.**

## T3 ≈ T2 minus a little (0.462 vs 0.493)

Consistent with synthetic (frontier ≈ neutral) and the demo (−0.03). The
lean playbook doesn't rescue the long-tail enumeration problem — its
"enumerate all subtypes" line isn't enough when the tail is only visible
through aggressive sampling. Playbook v2 should mandate *iterative
count-guided tail expansion* (sample → query → compare count to a
plausibility estimate → expand codes → repeat).

## Path split

| Tier | dx | comprehensive |
|---|---|---|
| T1 | 0.012 | 0.065 |
| T2 | 0.520 | 0.460 |
| T3 | 0.490 | 0.427 |

Comprehensive trails dx at T2/T3 — the union cells inherit the lab-side
over-capture (IDA 128k, NAFLD 58k lab-dominated golds) plus the code-tail
problem on the dx side.

## Meds path (added 2026-09-01, gold v2): the hardest discovery test

NDC→RxNorm crosswalk (RxNav, 5,720/5,732 NDCs) + ingredient-level
augmentation of Medication resources (re-imported to all 10 servers) unlocked
the medication path: 66 phenotypes, gold = ingredient-level RxNorm match
(`data/mimic-full-gold-v2.json`; real-scale cross-indication confirmed — PAD
meds=67,288 vs dx=6,748). To score, a model must discover that MIMIC meds
are NDC behind `medicationReference`, use a chained
`MedicationRequest?medication.code=` search, and query at ingredient level.
593 cells (66 × 3 prompts × 3 tiers):

| Tier | F1 | P | R | zero cells |
|---|---|---|---|---|
| T1 | **0.000** | 0.000 | 0.000 | 197/198 |
| T2 | **0.429** | 0.774 | 0.395 | 21/197 |
| T3 | 0.375 | 0.700 | 0.348 | 32/198 |

T2 by variant: naive 0.418 / broad **0.469** / expert 0.401 — the broad >
expert inversion holds on a third path. T1's *literal zero* is the starkest
tools result in the project: no amount of parametric knowledge finds
medications behind a reference indirection with local NDC coding. Successful
cells (ADHD, breast-cancer meds F1 = 1.00) all discovered the chained
RxNorm-ingredient query; failure modes include falling back to unsupported
`:text` searches (epilepsy, hepatitis-C) and querying the MIMIC-local NDC
system without enumeration (colorectal).

## Takeaways for the paper

1. Real data at scale **strengthens the qualitative claims** (tools are the
   lever; closed-book is near-zero; expert prompting inverts) and **tempers
   the quantitative ones** (agentic F1 ≈ 0.49–0.56 on real data, not ~0.7).
2. The demo→full drop is itself a finding: **benchmark difficulty scales
   with cohort code-diversity**, and small real-data samples overstate
   agentic competence.
3. Next levers, in order: gold hygiene for the artifact phenotypes;
   count-guided tail-expansion in the methodology; n≥3 repeats; NDC→RxNorm
   to unlock the meds path.

## Caveats

- n=1 agentic runs per cell; single model (Opus).
- dx + comprehensive paths only (meds/procedures unscored, as before).
- 1 unparsed cell (urinary-incontinence T3-naive asked a clarifying question).
- Gold-artifact phenotypes enumerated above remain in the tier means.
