# Can a Large Language Model Find the Patients? Measuring FHIR Query Accuracy for Clinical Cohort Identification Across Prompt Sophistication, Agentic Tooling, and Real-World Data

**Authors:** Jared Erwin¹ *(author list and affiliations to be completed)*

**Status:** DRAFT — full-MIMIC results pending (sweep in progress); figure slots
reference the Dev Days deck (`docs/presentation/devdays-outline.md`) and the
interactive leaderboard frontend.

---

## Abstract

**Objective:** Clinical cohort identification — turning a plain-English
description of a patient population into a query that returns exactly that
cohort — is a skilled, expensive bottleneck in clinical research. We measured
how accurately large language models (LLMs) perform this task against FHIR
servers, and which interventions (prompt sophistication, agentic tool access,
or an expert methodology playbook) actually improve them.

**Materials and Methods:** We built a benchmark of **108 phenotypes** derived
from expert-curated PheKB algorithms, each with code-free natural-language
prompts at three sophistication levels (naive, broad, expert) and executable
gold-standard FHIR queries. Synthetic patients were generated with custom
Synthea modules implementing a multi-path cohort design (diagnosis+medication,
diagnosis-only, medication-only "trick" paths, labs-only) plus curated
"mimicker" controls to punish over-broad queries. Models were evaluated at
three tiers: **T1** closed-book (single completion, no tools), **T2** agentic
(a tool loop with live FHIR server introspection and NIH UMLS/VSAC
terminology services), and **T3** (T2 plus a phenotype-methodology playbook).
Scoring is execution-based: the model query and gold query are run against a
live FHIR server and compared as **patient sets** (precision/recall/F1). We
then validated transfer to real-world data with **MIMIC-IV-on-FHIR**
(299,712 patients; 42.3 million resources per server), computing per-phenotype
gold cohorts offline from the data itself.

**Results:** Closed-book, even frontier models are mediocre (F1 0.56–0.63)
and highly prompt-sensitive. Agentic tooling is the dominant lever
(+0.23–0.30 F1), lifting frontier models to 0.86–0.88 and **collapsing the
prompt-sophistication gap**: with tools, a naive prompt performs within ~0.05
of an expert prompt. The methodology playbook is model-dependent: ~neutral
for frontier models but +0.23 for a small open-weight model. On real MIMIC-IV
data the tools lever is larger still: closed-book performance collapses
(full dataset T1 = 0.036; 87% of cells return zero patients) because real
EHR data is single-code-system and granularly coded, while agentic
introspection recovers much of it (T2 = 0.493; +0.46). Full scale also
exposes limits the 100-patient demo missed: recall stratifies by cohort
size (0.70 for 1k–10k-patient cohorts vs 0.28 above 10k — large phenotypes
span long tails of granular codes), and code-aware "expert" prompts
*invert*, underperforming plain clinical language by 0.17 F1.

**Conclusion:** Cohort recall is chiefly a *clinical concept coverage*
problem. Tools beat prompts and playbooks because they let the model discover
the concepts and code systems actually present in the data rather than recall
them. We package these findings as a reusable, server-agnostic FHIR
cohort-query agent (skill + methodology + terminology tooling).

---

## 1. Introduction

Identifying a cohort of patients matching a clinical description is the entry
point to most retrospective clinical research, quality measurement, and trial
recruitment. In practice it requires a rare combination of skills: fluency in
the query interface (here, HL7 FHIR search), command of multiple clinical
terminologies (SNOMED CT, ICD-10-CM, ICD-9-CM, LOINC, RxNorm, CPT), and
phenotyping judgment — knowing that real cohorts include patients treated by
outside providers (medication without diagnosis), patients with abnormal labs
but no coded diagnosis, and look-alike conditions that must be excluded.
Research networks such as eMERGE have spent two decades curating executable
phenotype definitions (PheKB) precisely because this is hard for humans.

Large language models can write FHIR queries from natural language, but
"can write a query" is not "can find the cohort." A syntactically perfect
query with one missing subtype code silently drops patients; an over-broad
query silently admits look-alikes. Whether LLMs can be trusted for cohort
identification — and *what makes them trustworthy* — is an empirical
question that requires execution-based measurement against controlled ground
truth, not string similarity.

This paper asks three questions:

1. **How accurate are LLMs at cohort identification from plain English**,
   measured as patient-set overlap against expert-defined gold cohorts?
2. **Which intervention moves the needle** — a more sophisticated prompt, an
   agentic tool loop (server introspection + terminology services), or an
   expert methodology playbook?
3. **Do the answers transfer from synthetic to real EHR data** (MIMIC-IV)?

### Contributions

- A **108-phenotype execution-based benchmark** built from PheKB expert
  algorithms, with three prompt-sophistication levels, adversarial cohort
  paths, mimicker controls, and patient-set P/R/F1 scoring.
- A three-tier evaluation isolating the contributions of **recall (T1)**,
  **tools (T2)**, and **methodology (T3)**.
- Evidence that **agentic tooling is the dominant lever** and that it
  **collapses the prompt-sophistication gap** — with tools, plain English
  approaches expert code-aware prompting.
- A **real-data replication on MIMIC-IV-on-FHIR** (299,712 patients) showing
  the tools lever *grows* on real data, because real EHR coding practices
  (single system, fully granular ICD) defeat closed-book recall entirely.
- A reusable, shareable **FHIR cohort-query agent** distilling the winning
  configuration.

---

## 2. Background and Related Work

*(To be expanded with formal citations.)* Computational phenotyping and the
PheKB/eMERGE tradition established expert-curated, multi-modality phenotype
definitions as the standard for EHR cohort identification. Prior LLM work has
addressed text-to-SQL over EHR schemas (e.g., EHRSQL), FHIR API usage, and
clinical code prediction, but generally scores query text or single-code
accuracy rather than executing queries against a server and comparing
returned patient sets. Execution-based scoring matters because distinct
queries can be semantically equivalent, and because patient-level effects of
missing subtypes or over-broad codes are invisible at the string level.
Synthea provides reproducible synthetic patients; MIMIC-IV-on-FHIR provides
de-identified real ICU/hospital data in FHIR form, enabling a
synthetic-to-real transfer test under identical harnesses.

---

## 3. Materials and Methods

### 3.1 Benchmark construction: 108 PheKB phenotypes

We derived test cases from the raw PheKB algorithm documents (descriptions,
flowcharts, code lists) for **108 phenotypes** spanning the clinical map:
cardiometabolic, psychiatric, infectious, 18 cancers, pediatric, genetic,
procedural, pharmacogenomic, and care-pattern phenotypes. Each phenotype
yields multiple **test-case variants** targeting different evidence paths:

- `-dx` — diagnosis-code cohort (Condition)
- `-meds` — medication cohort (MedicationRequest)
- `-labs` — laboratory threshold cohort (Observation + value-quantity)
- `-procedures` — procedure cohort (Procedure)
- **trick variants** — e.g., `-meds-only` (medication *without* diagnosis),
  `biologic-without-dx` (negation via two-query set subtraction)
- `-comprehensive` — the union cohort ("all my patients with X"), the
  variant closest to real phenotyping practice.

**Prompts are code-free by design** at three levels: **naive** ("Find
diabetics"), **broad** ("Patients with a type 2 diabetes diagnosis"), and
**expert** (a precise, code-aware specification *without* embedded queries).
The gold query carries the actual codes; the test is whether the model can
derive them. In total the benchmark comprises **388 test cases**; the
all-test-case mean F1 is the primary endpoint, with the comprehensive cell
reported separately as the "whole-cohort" endpoint.

> **[FIGURE 1 — Benchmark pipeline]** *Plain-English prompt → LLM (per tier)
> → FHIR query → live server execution → patient-set P/R/F1 vs gold.*
> (Source: deck Slides 2–3 visuals.)

### 3.2 Synthetic patients: multi-path cohorts with adversarial controls

Each phenotype has a custom **Synthea module** implementing a multi-path
template: **Path A** (diagnosis + medication), **Path B** (diagnosis only,
untreated), **Path C** (medication only, no diagnosis — the cross-indication
"trick" path), and where applicable **Path D** (abnormal labs only). Each
phenotype additionally ships **mimicker controls** — patients with similar
but distinct conditions (~348 curated terms across 108 phenotypes, resolved
to SNOMED via UMLS) — so over-broad queries lose precision.

Conditions and procedures carry **multiple codings** (SNOMED + ICD-10-CM +
ICD-9-CM; CPT for procedures) injected by a post-Synthea crosswalk pipeline.
This is a deliberate *generosity*: whichever code system the model queries,
it finds the multi-coded patient — so the synthetic benchmark tests
**clinical concept enumeration**, not code-system choice. (Real data reverses
this generosity; §3.5.) At evaluation time the FHIR server is wiped and
loaded with a single phenotype's bundle (per-phenotype isolation), so gold
patient sets are exact.

> **[FIGURE 2 — Multi-path cohort design]** *Overlapping dx/meds/labs/
> procedure sets; the union is the comprehensive cohort; Path C highlighted
> as the trick path; mimicker ring outside.* (Source: deck Slides 7–8
> visuals.)

### 3.3 Three evaluation tiers

| Tier | Tools | Methodology | Tests |
|---|---|---|---|
| **T1** closed-book | none | none | pure parametric recall |
| **T2** agentic | 10 tools | none | can tools recover what recall misses? |
| **T3** agentic + playbook | 10 tools | lean playbook | does expert strategy add anything? |

The **T2 agentic loop** provides ten tools across two channels: direct FHIR
REST against the live server (`server_metadata`, `search` with
`_summary=count`, `resource_sample`) and clinical terminology via the NIH
UMLS MCP server (`umls_search`, `umls_crosswalk`, and VSAC value-set
search/expand/validate/lookup/subsumption, authenticated with a UMLS API
key). The system prompt mandates evidence-gathering: find codes via
UMLS/VSAC, sample the server to learn which code systems the data uses,
validate cohort magnitude with `_summary=count`, and self-correct (zero
results → codes too narrow; implausibly large → missing constraint).

**T3** prepends a phenotype-methodology playbook: a mandatory
categorize-then-query step routing the request to ~12 named playbooks
(negation, thresholds, subtypes enumeration, sex/age guards,
iatrogenic-med-primary, cross-resource `_has`, cohort-OR vs case-AND …),
plus universal tactics. Two empirically-derived fixes are baked in: a **lean**
variant (the full 16 KB playbook over-constrained strong models) and an
**age-filter guard** (never add a birthdate filter because a disease *name*
contains an age word).

> **[FIGURE 3 — T2 agentic loop]** *Loop diagram: UMLS/VSAC code discovery →
> server sampling → count-validate → revise → emit query; FHIR REST and MCP
> channels labeled.* (Source: deck Slides 11/11B visuals.)

### 3.4 Scoring

We never grade query strings. Model and gold queries are executed against
the live server; returned **patient-ID sets** are compared:
precision = |G∩M|/|M|, recall = |G∩M|/|G|, F1 harmonic. Multi-query cases
union patient sets (line-separated queries); negation cases subtract them.
Cells are scored per (phenotype × variant × prompt level × tier × model).

### 3.5 Real-data validation: MIMIC-IV-on-FHIR

To test transfer, we evaluated against **MIMIC-IV-on-FHIR**: first the
100-patient demo, then the full credentialed dataset (**299,712 patients**;
118.2 M laboratory observations). Real data breaks two synthetic
conveniences: (i) MIMIC Conditions carry **only ICD-9-CM/ICD-10-CM** — no
SNOMED — under MIMIC-local CodeSystem URIs with undotted codes; and (ii)
codes are **fully granular** (E11.9, E11.42, …) on a server with exact token
matching and no `code:below` hierarchy, so category queries match nothing.

We standardized **additively** (never replacing): dotted
ICD-10-CM/ICD-9-CM/ICD-10-PCS codings added beside the originals, and LOINC
added to laboratory observations via an itemid→LOINC map (94.5% coverage).
This corrects conversion artifacts — real US-Core-conformant endpoints
expose standard system URIs — while preserving what makes real data hard: no
SNOMED anywhere, granular codes, NDC-only medications behind
`medicationReference` indirection.

Gold cohorts were recomputed **from the data itself**: hierarchical ICD
prefix matching for diagnosis cohorts and LOINC+threshold evaluation for lab
cohorts, yielding patient-ID sets per phenotype for dx, labs, and
comprehensive paths. **105/108 phenotypes** have a non-empty MIMIC cohort
(median dx cohort ≈ 2,400 patients; hypertension 84,776; the three empty
phenotypes are structurally out of scope — ECG-based, meds-only, and
neonatal in an adult dataset). The full 42.3 M-resource dataset was loaded
to ten FHIR server instances via bulk `$import` with exact count
verification (per-type and per-code spot checks matched offline counts
exactly).

### 3.6 Models

Frontier: GPT-5.4, Claude Opus 4.7, Claude Sonnet 4.6. Small open-weight:
Qwen3.5-9B. All runs n=1 per cell (agentic variance addressed in
Limitations); tier means over 388 cells are the primary endpoints.

---

## 4. Results

### 4.1 Synthetic benchmark: tiers and models

| Model | T1 | T2 | T3 |
|---|---|---|---|
| GPT-5.4 | 0.624 | 0.871 | **0.879** |
| Claude Sonnet 4.6 | 0.563 | 0.859 | 0.862 |
| Claude Opus 4.7 | 0.632 | 0.859 | 0.860 |
| Qwen3.5-9B | 0.257 | 0.476 | 0.710 |

*All-test-case mean F1, full 108 phenotypes / 388 test cases.*

Closed-book, frontier models cluster at F1 0.56–0.63. **Tools are the
dominant lever**: every model gains +0.23–0.30 from T1→T2. The methodology
playbook (T3) is approximately neutral for frontier models (−0.02 to +0.02)
but transformative for the small model (+0.234).

> **[FIGURE 4 — Headline grouped bars]** *Model × tier (T1/T2/T3) grouped
> bar chart.* (Source: deck Slide 14 visual; frontend leaderboard export.)

### 4.2 Tools collapse the prompt-sophistication gap

| Model | T1 naive | T1 broad | T1 expert | T2 naive | T2 broad | T2 expert | gap T1→T2 |
|---|---|---|---|---|---|---|---|
| GPT-5.4 | 0.481 | 0.634 | 0.758 | 0.842 | 0.873 | 0.897 | 0.28 → 0.06 |
| Claude Opus 4.7 | 0.533 | 0.644 | 0.718 | 0.816 | 0.868 | 0.894 | 0.19 → 0.08 |
| Claude Sonnet 4.6 | 0.492 | 0.554 | 0.643 | 0.846 | 0.870 | 0.861 | 0.15 → 0.02 |
| Qwen3.5-9B | 0.072 | 0.150 | 0.551 | 0.283 | 0.363 | 0.778 | 0.48 → 0.50 |

Closed-book, prompt phrasing is worth up to +0.28 F1 (expert vs naive). With
tools, the gap collapses to ~0.02–0.08 for frontier models — **a naive
prompt plus tools approaches an expert prompt plus tools**. The collapse is
a frontier-model result: the small model still needs both tools *and* a
code-aware prompt (gap ~0.50 persists at T2).

> **[FIGURE 5 — Prompt-collapse lines (centerpiece)]** *X = prompt level,
> Y = F1; Opus exemplar: T1 line slopes 0.53→0.72, T2 line flat
> 0.82→0.89.* (Source: deck Slide 15 chart; all-test-case basis only.)

### 4.3 The achievable ceiling: comprehensive cohorts

On the comprehensive ("find all my patients") cell — 80 phenotypes with a
comprehensive case — each model's best tier×prompt configuration:

| Model | Best config | Best F1 (comprehensive) |
|---|---|---|
| GPT-5.4 | T2 + expert | 0.990 |
| Claude Sonnet 4.6 | T2 + expert | 0.986 |
| Claude Opus 4.7 | T3 + expert | 0.967 |
| Qwen3.5-9B | T3 + expert | 0.919 |

With the right configuration, frontier models **essentially solve
whole-cohort retrieval** on synthetic data (0.97–0.99). The headroom in the
headline table lives in the harder per-path and trick variants.

### 4.4 Methodology is a model-dependent lever — with a failure mode

The playbook's benefit concentrates where competence is missing: Qwen gains
+0.23 (T2 0.476 → T3 0.710); frontier models are flat. On heterogeneous
cross-coded phenotypes we identified a reproducible failure mode: the
playbook's "canonical code" framing led Opus to **under-enumerate subtype
concepts** (coronary heart disease: 32 concepts enumerated at T2 → recall
1.00; 7 at T3 → recall 0.39). Averaged over all 388 cases this washes out
(Opus T2→T3 −0.02, within agentic noise), but it dictates playbook design:
*instruct enumeration of the full subtype tail, not the canonical code.*

### 4.5 Off-the-shelf generic skill: marginal

Opus with a published generic FHIR-developer skill (prepended text, no
tools) scores 0.650 vs plain closed-book 0.632 (+0.018) — near-noise on the
expert prompt (+0.014). A generic skill supplies what a frontier model
already knows; the +0.21 gap to the agentic stack comes from tools.

### 4.6 Real-world data: MIMIC-IV

**Demo (100 patients, prior work in this project):** the synthetic ordering
holds but the tools lever *triples*: Opus T1 0.090 / T2 0.688 / T3 0.662.
Closed-book queries default to SNOMED, which real data does not carry at
all; agentic sampling discovers ICD-9/ICD-10 and enumerates the granular
codes present. The expert prompt — best on synthetic — **underperforms broad
on MIMIC** (T2: broad 0.76 > naive 0.70 > expert 0.60): its code-aware hints
assume the wrong vocabulary and mislead, while looser prompts let the agent
discover the truth.

**Full dataset (299,712 patients):** gold cohorts span 105 phenotypes at
realistic scale (median dx cohort ≈ 2,400; hypertension 84,776; T2D
comprehensive 42,069). All ten server instances hold the identical verified
42.3 M-resource load. The full sweep (1,592 cells: 105 phenotypes ×
dx+comprehensive × 3 prompts × 3 tiers, Opus):

| Tier | MIMIC full | MIMIC demo | Synthetic |
|---|---|---|---|
| T1 closed-book | **0.036** | 0.090 | 0.632 |
| T2 agentic | **0.493** | 0.688 | 0.859 |
| T3 + methodology | **0.462** | 0.662 | 0.860 |

Three results. First, **the tools lever survives and dominates**: +0.46
T1→T2 (87% of closed-book cells return zero patients; only 11% of agentic
cells do). Second, **the 100-patient demo overstated agentic recovery**
(0.69 → 0.49): T2 precision remains 0.71 but recall falls to 0.48, and
recall stratifies by cohort size — 0.70 for gold cohorts of 1,000–10,000
patients, 0.28 above 10,000. At scale, a large phenotype's patients span a
long tail of granular ICD codes; server samples reveal only the head of the
distribution, and partial enumeration caps recall. Third, the
**expert-prompt inversion strengthens**: T2 broad 0.556 > naive 0.539 ≫
expert 0.384 — code-aware hints anchor the model on absent vocabularies and
suppress the server-sampling behavior looser prompts trigger.

**Medication path (NDC→RxNorm crosswalk).** Resolving MIMIC's 5,732
distinct NDCs to RxNorm products and ingredients (RxNav; 99.8% mapped),
additively coding the Medication resources, and recomputing gold at
ingredient level unlocked the medication path for 66 phenotypes — the
strictest discovery test in the study, since scoring requires the model to
find that medications sit behind `medicationReference` with NDC-only local
coding and to issue a chained ingredient-level search. Closed-book scores
**exactly zero** (197/198 cells); the agentic loop recovers F1 0.429
(precision 0.774), with successful cells independently discovering the
chained `MedicationRequest?medication.code=rxnorm|<ingredient>` pattern.
The broad > expert prompt inversion replicates on this third path (0.469 vs
0.401). The recomputed medication cohorts also confirm the cross-indication
phenomenon that the synthetic benchmark's "trick paths" model, at real-world
magnitude: peripheral arterial disease has 67,288 patients on its medication
classes against 6,748 diagnosed.

A subset of the worst large-cohort cells are benchmark artifacts rather than
model failures (a resistant-hypertension gold that prefix-matches the whole
hypertension family; pediatric phenotypes whose age guards cannot apply to
offline gold on an adult dataset; allergy phenotypes whose natural resource,
AllergyIntolerance, MIMIC-on-FHIR does not populate). Excluding these three
phenotypes (45 cells) moves tier means by ~+0.01 (T2 0.493 → 0.503,
T3 0.462 → 0.474) and leaves every conclusion unchanged; the exclusions are
retained as the primary analysis for correctness (§6).

> **[FIGURE 6 — Synthetic vs demo vs full-MIMIC tier bars]** *Grouped bars
> per tier across the three data regimes; annotate the T1 collapse and the
> demo→full recall gap.* (Data: table above; source doc
> `docs/results/2026-09-01-mimic-full-sweep.md`.)
>
> **[FIGURE 7 — Recall vs gold-cohort size]** *T2-broad recall by gold-size
> bucket (0.41 / 0.64 / 0.70 / 0.28); the code-tail coverage story.*

> **[FIGURE 7 — Synthetic vs real bar pairs]** *T1/T2/T3 bars side-by-side,
> synthetic vs MIMIC; the T1 collapse and enlarged T1→T2 delta are the
> visual story.* (Source: deck Slide 21 roadmap slot; data from §4.6.)

---

## 5. Discussion

**Cohort recall is concept coverage.** The through-line across every
intervention is whether the final query enumerates all clinical
concepts/subtypes the cohort is coded with. Expert prompts hand the model
concepts; tools let it *discover* them (sample the server, expand value
sets, crosswalk); over-tight methodology prunes them. On synthetic data
(generous multi-system coding) concept coverage is the whole game; on real
data the model must additionally discover *which system and at what
granularity* — which is why closed-book collapses and tools grow more
valuable.

**Tools democratize cohort identification.** The prompt-gap collapse is the
practically important finding: with a proper agentic loop, a clinician's
plain-English request approaches an informaticist's code-aware
specification. Institutionally, investment in tooling (terminology services,
server introspection) dominates investment in prompt engineering.

**Match strategy to model.** Methodology playbooks are scaffolding for
models that lack phenotyping competence; for frontier models they are at
best neutral and can induce under-enumeration if phrased canonically.

**Real EHR data is an adversarial distribution shift** for parametric
recall: single code system, granular codes, exact-match servers, NDC-behind-
reference medications. Benchmarks built only on multi-coded synthetic data
overstate closed-book competence; our synthetic/real pairing quantifies the
gap under an identical harness.

**Scale is part of the distribution shift.** The demo→full gap (T2 0.69 →
0.49) shows that real-data difficulty grows with cohort code-diversity:
small samples of real data flatter agentic models because small cohorts
have short code tails. Benchmarks should report performance *stratified by
cohort size*, and agentic methodologies should mandate count-guided,
iterative code-tail expansion rather than one-shot enumeration — the
current playbook's "enumerate all subtypes" is necessary but not
sufficient when the tail is only visible through aggressive sampling.

**Describe the population; don't prompt with codes.** The expert-prompt
inversion at scale (−0.17 vs broad at T2) turns a synthetic-data nicety
into deployment guidance: on unfamiliar servers, embedding codes in the
request anchors the agent on possibly-absent vocabularies and suppresses
discovery. The best human interface to a cohort agent is precise *clinical*
language, not precise *coding* language.

## 6. Limitations

- **n=1 agentic runs** per cell; sub-0.05 deltas are within variance. The
  headline levers (+0.23–0.60) are far above it. Repeat runs (n≥3) planned.
- **Synthetic generosity**: multi-coded patients mean the synthetic
  benchmark does not test code-system selection (the MIMIC arm does). A
  sharper synthetic design would assign each patient one randomly chosen
  system.
- **MIMIC scoring paths**: dx, labs, their union, and (via the NDC→RxNorm
  ingredient crosswalk) medications are scored; procedures (ICD-10-PCS vs
  our CPT/SNOMED gold) remain future work. Medication gold matches at
  ingredient level, which treats any product of a listed drug as a match;
  dose- or formulation-specific phenotype criteria are not enforced.
- **MIMIC caveats**: lab thresholds over-capture in an ICU population
  (IDA hemoglobin criterion captures 42% of patients); two histology
  phenotypes (GBM, RCC) score at ICD category level; pediatric phenotypes
  match on codes only in an adult dataset.
- **Prompt provenance**: expert prompts were rewritten to remove embedded
  queries (de-leak); residual phrasing effects are possible.
- Single FHIR server implementation per arm (fhir-candle/Microsoft FHIR);
  server search-feature differences (e.g., `code:below`) matter and are part
  of what tools must discover.

## 7. Conclusion

Even frontier LLMs are mediocre closed-book cohort finders and heavily
prompt-dependent; a modest agentic loop over server introspection and
terminology services is the dominant, prompt-equalizing lever, and its value
*grows* on real EHR data where parametric recall fails structurally. The
practical product of the benchmark is a reusable cohort-query agent: lean
methodology, long-tail concept enumeration, server-first discovery, and
UMLS/VSAC integration, pointable at any FHIR endpoint.

## Data and Code Availability

Benchmark test cases, Synthea modules, augmentation and evaluation
pipelines, and the cohort-query agent are available in the project
repository. MIMIC-IV is available to credentialed users via PhysioNet;
derived gold cohorts are reproducible with the included scripts
(`recompute_mimic_gold.py`).

## Figure/Table inventory (deck mapping)

| Slot | Content | Deck source |
|---|---|---|
| Fig 1 | Benchmark pipeline diagram | Slides 2–3 |
| Fig 2 | Multi-path cohort + mimickers | Slides 7–8 |
| Fig 3 | T2 agentic loop / two channels | Slides 11, 11B |
| Fig 4 | Model × tier grouped bars | Slide 14 |
| Fig 5 | Prompt-collapse lines (Opus) | Slide 15 |
| Tab 1 | Headline tier table | Slide 14 |
| Tab 2 | Prompt × tier table | Slide 15 |
| Tab 3 | Comprehensive ceiling | Slide 14B |
| Fig 6 | Synthetic vs demo vs full-MIMIC tier bars | `2026-09-01-mimic-full-sweep.md` |
| Fig 7 | T2 recall vs gold-cohort size | `2026-09-01-mimic-full-sweep.md` |
