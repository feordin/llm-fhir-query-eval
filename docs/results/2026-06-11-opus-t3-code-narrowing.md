# Opus T3 "regression": a per-case concept-enumeration failure mode (NOT a leaderboard effect)

**Date:** 2026-06-11, **resolved 2026-06-12 on full coverage** · follows the
2026-06-10 T3 lean refresh (`docs/results/2026-06-10-t3-lean-refresh.md`).

> ## UPDATE 2026-06-12 — RESOLVED on full Opus T2 coverage (read this first)
>
> The dramatic "Opus T3 < T2 by 0.06" below was a **48-test-case-subset artifact**.
> With the Opus T2 backfill now at **full 388-tc coverage**, the paired comparison
> (1164 cells) is:
>
> | | T2 | T3 | Δ |
> |---|---|---|---|
> | **F1** | 0.862 | 0.867 | **+0.004** |
> | distinct concepts/query | 6.96 | **8.17** | **+1.21** |
>
> **Opus T3 ≈ T2 on full coverage** (T3 is a hair *higher*), and under T3 Opus
> queries *more* concepts on average, not fewer — i.e. **the "concept-narrowing"
> does NOT hold model-wide.** It was concentrated in the cross-coded hard cases that
> dominated the unrepresentative 48-tc subset (the skill-baseline set).
>
> **What's still true and useful:** the *mechanism* — recall depends on concept
> coverage, and the methodology can make Opus under-enumerate subtype concepts on a
> *specific* hard phenotype (the CHD worked example: 32→7 concepts, recall 1.0→0.39).
> That is a **real per-case failure mode** worth knowing (it's why the plugin should
> say "enumerate all subtype concepts"), but it is **not** a leaderboard-level
> regression. Frame Slide 16B accordingly: a failure-mode example, not a headline.
>
> The original (pre-resolution) analysis is preserved below for the record; treat its
> "code-system narrowing" framing as the *initial, confounded* read.

## TL;DR (original, 2026-06-11 — superseded by the update above)

In the v7 leaderboard, **Opus is the only model whose T3 (+methodology) F1 sits
*below* its T2 (tools-only)** — 0.867 vs 0.904. We chased this down and it is
**not** a stale-methodology artifact and **not** purely a denominator artifact.
It is a real, mechanistic, **Opus-specific** effect:

> Under the prepended phenotype-methodology playbook, **Opus collapses the number
> of clinical code systems it queries** (SNOMED + ICD-10 + ICD-9 + CPT → mostly
> SNOMED-only). Because our Synthea **diagnoses and procedures are multi-coded** on
> purpose (Conditions: SNOMED + ICD-10 + ICD-9; Procedures: SNOMED + CPT), a
> SNOMED-only query systematically under-recalls. Sonnet and GPT do **not** narrow
> this way under the same playbook, so their recall — and F1 — holds or improves.

The cost is concentrated in **cross-coded / cross-resource phenotypes** (coronary
heart disease, Crohn's cross-resource includes, diabetes labs), exactly the cases
where multi-system coding matters most.

## What we ruled out

**1. "Opus T3 is still the old, pre-fix methodology."** *Ruled out.* The canonical
`copilot:claude-opus-4.7` Tier-3 cells are **byte-identical** to the `+T3fix`
lean-refresh cells — all 1164 (tc × variant) cells match exactly, all stamped
2026-06-09/10. Promotion worked; Opus T3 **is** the lean + age-guard methodology.
A rerun would not change the methodology it ran under.

**2. "It's just the denominator (Opus T3 is full-388, Opus T2 is 48 tc)."**
*Insufficient on its own.* The 48-tc gap is real *within the subset*: a paired
comparison on the 48 test cases where Opus has **both** T2 and T3 shows
**T2 0.904 vs T3 0.841 (−0.063)**, with T3 **losing 22, winning 9, tied 17**.
So even apples-to-apples on identical cases, T3 < T2 for Opus. (The full-388 vs
48-tc mismatch *does* explain why the leaderboard's headline 0.867-vs-0.904 looks
worse than it is, but it is not the whole story — see caveats.)

## The mechanism — code-system narrowing (the evidence)

Paired cells (same test-case + variant, where the model has both T2 and T3).
"sys" = mean distinct clinical code systems referenced per query (counting the
`system|code` URIs in `code=`/`combo-code=`); "q" = mean queries per cell.

| Model | n cells | sys T2 | sys T3 | Δsys | F1 T2 | F1 T3 | ΔF1 |
|---|---|---|---|---|---|---|---|
| **claude-opus-4.7** | 144 | 2.46 | **1.83** | **−0.63** | 0.904 | 0.841 | **−0.063** |
| claude-sonnet-4.6 | 1132 | 2.31 | 2.13 | −0.18 | 0.846 | 0.864 | +0.018 |
| gpt-5.4 | 1114 | 2.11 | 2.11 | −0.00 | 0.878 | 0.899 | +0.021 |

All three models issue **fewer queries** under T3 (the playbook rightly discourages
shotgunning) — but only **Opus also strips code systems from *within* each query**.
GPT cuts query count the most (−0.54) yet keeps full code-system breadth, so its
recall is untouched. Opus keeps roughly the same query count but drops 0.63 code
systems per query, and that is precisely what bleeds recall.

The F1 column tracks the sys column one-for-one: the only model that narrows code
systems is the only model that regresses.

### Per-phenotype contrast (Tier-3 F1, the Opus-specific collapses)

| Phenotype (T3) | **Opus** | Sonnet | GPT |
|---|---|---|---|
| coronary-heart-disease | **0.467** | 0.878 | 0.878 |
| crohns-disease-include-patient | **0.641** | 1.000 | 1.000 |
| type-2-diabetes-labs | **0.667** | 1.000 | 1.000 |

Sonnet and GPT nail these under T3; Opus alone collapses. The collapse always
coincides with a single-code-system query — and that coupling is deterministic
(next section), even though *which* cells collapse on any given run shuffles with
agentic variance.

### The deterministic core: code-system count drives F1

Pooling all Opus T3 cells across the canonical run and the confirmatory rerun
(CHD + Crohn's), F1 is a clean monotone function of how many code systems the
query references:

| code systems in query | mean F1 | n cells |
|---|---|---|
| 1 (e.g. SNOMED-only) | **0.816** | 38 |
| 2 | 0.862 | 26 |
| 3 (SNOMED + ICD + CPT/RxNorm) | **0.961** | 14 |

This is the deterministic mechanism: a one-system query against multi-coded data
loses ~0.15 F1 versus a three-system query. The only question is how often Opus
lands on one system — and under T3 it does so on **~half** of these cross-coded
cells.

### Smoking gun — coronary heart disease, naive prompt

| | F1 | Recall | Codes queried |
|---|---|---|---|
| **Opus T2** (tools only) | 0.878 | **1.00** | 21 Condition codes across **SNOMED + ICD-10-CM + ICD-9-CM**; Procedures across **SNOMED + CPT** |
| **Opus T3** (+methodology) | 0.467 | **0.389** | **3 SNOMED** Condition codes + **4 SNOMED** Procedure codes — no ICD, no CPT |

Same model, same data, same prompt — the only thing added is the methodology
playbook, and it cut Opus from a 21-code multi-system union (recall 1.00) down to a
7-code SNOMED-only query (recall 0.39).

## The theory — why Opus, specifically

The lean methodology playbook is, in effect, a set of *expert-phenotyper habits*:
identify the canonical concept, validate codes, don't over-constrain, reason before
querying. It nudges toward **principled, canonical code selection**.

Opus is the most **instruction-adherent / literal** of the three frontier models.
We think it applies the playbook's "be principled, pick the right canonical code"
guidance **too faithfully**, collapsing it into "pick *the* canonical code
*system*." It validates a small set of high-confidence SNOMED codes via UMLS,
judges the concept correctly captured, and stops — treating breadth as
sloppiness. Sonnet and GPT read the same playbook as *softer* guidance and retain
the T2-style exploratory behavior (sample the server, see multiple code systems
present, union them), so they keep recall.

In one line: **the methodology over-steers the most obedient model toward
code-system parsimony, and parsimony is exactly wrong against deliberately
multi-coded data.** It is the strong-model version of the same lever that *helps*
weak models — Qwen lacks phenotyping competence and the playbook supplies it; Opus
already has the competence and the playbook displaces a better default.

This is consistent with our broader narrative (methodology is a big lever for weak
models, ~neutral-to-slightly-negative for frontier) — Opus is simply the sharpest
instance of the negative tail, and now we know the *channel*: code-system breadth.

## Confirmation status & honest caveats

- **Determinism (confirmed, with nuance):** a focused **Opus-T3 rerun on CHD +
  Crohn's** (tagged `+T3confirm`, 39 cells) settled this. The *propensity* to narrow
  reproduces at the aggregate: mean code-systems/query 1.64 (canonical) vs 1.74
  (rerun), with ~46–51% of cells collapsing to a single system in **both** runs. The
  *mechanism* is deterministic (the sys→F1 table above). What is **stochastic** is
  *which* cells narrow on a given run — e.g. CHD-naive reproduced 0.467/1-system
  exactly, but CHD-broad/expert recovered to 0.878 with 2–3 systems. So the honest
  framing is **"Opus has a stable, model-specific propensity under T3 to drop to one
  code system on roughly half of cross-coded cells, and that drop deterministically
  costs recall"** — not "Opus deterministically fails cell X." (Aside: the rerun's
  mean F1 on this subset, 0.870, was actually a touch *above* canonical 0.845 — well
  within agentic noise — which is itself the point: the per-cell outcome is noisy, the
  aggregate narrowing propensity is what's stable and Opus-specific.)
- **Denominator:** the −0.63 sys / −0.063 F1 numbers are computed on the **48-tc
  skill-baseline subset** (n=144 cells) because Opus T2 is only partial. The
  mechanism is crisp on that subset and the per-phenotype contrast uses
  full-coverage T3, but a **full-388 Opus T2 backfill** is required before we
  publish "Opus T3 < T2" as a headline leaderboard claim. Until then we frame it
  as *"on the cases measured, the methodology narrows Opus's code systems and costs
  recall."*
- **Not a data bug:** the Synthea dx/procedure multi-coding (SNOMED↔ICD-9/ICD-10 via
  `augment_fhir_codes.py`, 189 curated crosswalk entries; +CPT for procedures) is
  intentional and correct; T2 Opus exploits it fully. The playbook, not the data,
  suppresses it. (Meds are RxNorm-only and labs LOINC-only — single-system — so this
  finding is specific to the diagnosis/procedure-coded cohorts.)

## Implications

- **Presentation:** this is a *nuance-sells-credibility* slide — "methodology can
  backfire on the most instruction-following frontier model, via code-system
  narrowing." It sharpens Slide 16 ("methodology helps weak models a lot, strong
  models a little — and can mildly hurt the most literal one").
- **Plugin:** the shareable methodology should add an explicit instruction to
  **enumerate all code systems present on the server (SNOMED *and* ICD *and*
  CPT/RxNorm), not just the canonical one** — i.e., bake the T2 exploratory habit
  into the playbook so the strong-model parsimony failure can't happen.
- **Next:** backfill Opus T2 to full 388 (fair leaderboard), and re-aggregate.
