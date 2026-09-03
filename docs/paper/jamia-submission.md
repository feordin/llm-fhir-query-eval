# JAMIA Research and Applications — submission draft

*(Source of truth for numbers: `manuscript.md` working draft +
`docs/results/`. This file is the journal-formatted version; convert to DOCX
with pandoc for the OUP portal.)*

---

## Title page

**Title:** Can a Large Language Model Find the Patients? Measuring FHIR Query
Accuracy for Clinical Cohort Identification Across Prompt Sophistication,
Agentic Tooling, and Real-World Data

**Authors:** Jared Erwin¹ *(co-authors, degrees, and affiliations to be
completed)*

¹ *(affiliation, city, country — TODO)*

**Corresponding author:** Jared Erwin — *(postal address, email, phone — TODO)*

**Keywords:** electronic phenotyping; Health Level Seven (FHIR); large
language models; cohort identification; clinical terminologies

**Word count:** ~2,400 *(recount after final edits; excludes title page,
abstract, references, figures, tables)*

---

## Abstract

**Objective:** To measure how accurately large language models (LLMs)
translate plain-English cohort descriptions into executable FHIR queries,
and to determine which intervention — prompt sophistication, agentic tool
access, or an expert methodology playbook — most improves them.

**Materials and Methods:** We built an execution-based benchmark of 108
phenotypes derived from PheKB algorithms, each with code-free prompts at
three sophistication levels (naive, broad, expert) and gold-standard
queries, evaluated over synthetic multi-path Synthea cohorts with
adversarial "mimicker" controls. Models were tested at three tiers:
closed-book (T1); agentic, with live FHIR-server introspection and UMLS/VSAC
terminology tools (T2); and agentic plus a phenotype-methodology playbook
(T3). Model and gold queries were executed against a live server and scored
as patient-set precision/recall/F1. Transfer was validated on
MIMIC-IV-on-FHIR (299,712 patients).

**Results:** Closed-book, frontier models reached mean F1 0.56–0.63 and were
highly prompt-sensitive. Agentic tooling added +0.23–0.30 F1, lifting
frontier models to 0.86–0.88 and collapsing the naive-versus-expert prompt
gap from up to 0.28 to ≤0.08. The playbook was neutral for frontier models
but added +0.23 for a small open-weight model. On real MIMIC-IV data,
closed-book performance collapsed (F1 0.036) while the agentic tier
recovered 0.493; recall declined with cohort size, and code-aware expert
prompts underperformed plain clinical language by 0.17 F1.

**Discussion:** Cohort identification is chiefly a clinical
concept-coverage problem; tools dominate because they let models discover
the terminologies actually present in the data.

**Conclusion:** An agentic loop over server introspection and terminology
services is the dominant, prompt-equalizing lever, and its value grows on
real EHR data.

---

## Introduction

Identifying a cohort of patients matching a clinical description is the
entry point to most retrospective clinical research, quality measurement,
and trial recruitment. In practice it requires a rare combination of
skills: fluency in the query interface (here, HL7 FHIR search [6]), command
of multiple clinical terminologies (SNOMED CT, ICD-10-CM, ICD-9-CM, LOINC,
RxNorm, CPT), and phenotyping judgment — knowing that real cohorts include
patients treated by outside providers (medication without diagnosis),
patients with abnormal laboratory results but no coded diagnosis, and
look-alike conditions that must be excluded [1,2]. Research networks such
as eMERGE have spent two decades curating executable phenotype definitions
(PheKB) precisely because this is hard for humans [3,4].

Large language models can write FHIR queries from natural language, but
"can write a query" is not "can find the cohort." A syntactically perfect
query with one missing subtype code silently drops patients; an over-broad
query silently admits look-alikes. Whether LLMs can be trusted for cohort
identification — and *what makes them trustworthy* — is an empirical
question that requires execution-based measurement against controlled
ground truth, not string similarity.

**Objective.** This study asks three questions: (1) How accurate are LLMs
at cohort identification from plain English, measured as patient-set
overlap against expert-defined gold cohorts? (2) Which intervention moves
the needle — a more sophisticated prompt, an agentic tool loop (server
introspection plus terminology services), or an expert methodology
playbook? (3) Do the answers transfer from synthetic to real EHR data
(MIMIC-IV)?

## Background and Significance

Computational phenotyping in the PheKB/eMERGE tradition established
expert-curated, multi-modality phenotype definitions as the standard for
EHR cohort identification [1–5], and desiderata for *computable* phenotype
representations motivated executable, portable definitions [5]. FHIR has
become the dominant standards-based interface to EHR data [6,7], making
FHIR search the natural query target for automated cohort tools, with the
UMLS providing the terminology backbone that phenotype queries draw on [8].

Prior LLM work has addressed text-to-SQL over EHR schemas (EHRSQL [12]),
clinical code assignment [13], and trial-eligibility screening from
unstructured notes [14], but generally scores query text or single-code
accuracy rather than executing queries against a server and comparing
returned patient sets. Execution-based scoring matters because distinct
queries can be semantically equivalent, and because patient-level effects
of missing subtypes or over-broad codes are invisible at the string level.
Synthea provides reproducible synthetic patients [9]; MIMIC-IV [10] in its
FHIR form [11] provides de-identified real hospital data under the same
query interface, enabling a synthetic-to-real transfer test under identical
harnesses. To our knowledge this is the first execution-based,
patient-set-scored benchmark of LLM cohort identification spanning both
regimes.

## Materials and Methods

### Benchmark construction: 108 PheKB phenotypes

We derived test cases from the raw PheKB algorithm documents
(descriptions, flowcharts, code lists) for 108 phenotypes spanning the
clinical map: cardiometabolic, psychiatric, infectious, 18 cancers,
pediatric, genetic, procedural, pharmacogenomic, and care-pattern
phenotypes [3]. Each phenotype yields multiple test-case variants targeting
different evidence paths: `-dx` (diagnosis codes; Condition), `-meds`
(MedicationRequest), `-labs` (Observation with value thresholds),
`-procedures` (Procedure), trick variants (e.g., medication *without*
diagnosis; negation via two-query set subtraction), and `-comprehensive` —
the union cohort ("all my patients with X"), the variant closest to real
phenotyping practice.

Prompts are code-free by design at three levels: **naive** ("Find
diabetics"), **broad** ("Patients with a type 2 diabetes diagnosis"), and
**expert** (a precise, code-aware specification *without* embedded
queries). The gold query carries the actual codes; the test is whether the
model can derive them. The benchmark comprises 388 test cases; the
all-test-case mean F1 is the primary endpoint, with the comprehensive cell
reported separately as the whole-cohort endpoint.

> **[FIGURE 1]** Benchmark pipeline: plain-English prompt → LLM (per tier)
> → FHIR query → live server execution → patient-set P/R/F1 versus gold.

### Synthetic patients: multi-path cohorts with adversarial controls

Each phenotype has a custom Synthea [9] module implementing a multi-path
template: Path A (diagnosis + medication), Path B (diagnosis only,
untreated), Path C (medication only, no diagnosis — the cross-indication
"trick" path), and where applicable Path D (abnormal laboratory results
only). Each phenotype additionally ships mimicker controls — patients with
similar but distinct conditions (~348 curated terms across 108 phenotypes,
resolved to SNOMED CT via UMLS [8]) — so over-broad queries lose precision.

Conditions and procedures carry multiple codings (SNOMED CT + ICD-10-CM +
ICD-9-CM; CPT for procedures) injected by a post-Synthea crosswalk
pipeline. This is a deliberate *generosity*: whichever code system the
model queries, it finds the multi-coded patient — so the synthetic
benchmark tests clinical concept enumeration, not code-system choice.
(Real data reverses this generosity; see below.) At evaluation time the
FHIR server is wiped and loaded with a single phenotype's bundle
(per-phenotype isolation), so gold patient sets are exact.

> **[FIGURE 2]** Multi-path cohort design: overlapping dx/meds/labs/
> procedure sets; the union is the comprehensive cohort; Path C highlighted
> as the trick path; mimicker ring outside.

### Three evaluation tiers

**T1 (closed-book)** is a single completion with no tools, testing pure
parametric recall. **T2 (agentic)** provides ten tools across two channels:
direct FHIR REST against the live server (`server_metadata`, `search` with
`_summary=count`, `resource_sample`) and clinical terminology via the NIH
UMLS API [8] (concept search, code crosswalk, and VSAC value-set
search/expand/validate/lookup/subsumption). The system prompt mandates
evidence-gathering: find codes via UMLS/VSAC, sample the server to learn
which code systems the data uses, validate cohort magnitude with
`_summary=count`, and self-correct (zero results → codes too narrow;
implausibly large → missing constraint). **T3** prepends a
phenotype-methodology playbook: a mandatory categorize-then-query step
routing the request to ~12 named playbooks (negation, thresholds, subtype
enumeration, sex/age guards, cross-resource `_has`, cohort-OR versus
case-AND, and others), plus universal tactics. Two empirically derived
fixes are baked in: a lean variant (the full 16 KB playbook
over-constrained strong models) and an age-filter guard.

> **[FIGURE 3]** T2 agentic loop: UMLS/VSAC code discovery → server
> sampling → count-validate → revise → emit query; FHIR REST and
> terminology channels labeled.

### Scoring

We never grade query strings. Model and gold queries are executed against
the live server; returned patient-ID sets are compared: precision =
|G∩M|/|M|, recall = |G∩M|/|G|, F1 harmonic. Multi-query cases union
patient sets; negation cases subtract them. Cells are scored per
(phenotype × variant × prompt level × tier × model).

### Real-data validation: MIMIC-IV-on-FHIR

To test transfer, we evaluated against MIMIC-IV-on-FHIR [10,11]: first the
100-patient demo, then the full credentialed dataset (299,712 patients;
118.2 million laboratory observations). Real data breaks two synthetic
conveniences: (i) MIMIC Conditions carry only ICD-9-CM/ICD-10-CM — no
SNOMED CT — under MIMIC-local CodeSystem URIs with undotted codes; and
(ii) codes are fully granular (E11.9, E11.42, …) on a server with exact
token matching and no `code:below` hierarchy, so category queries match
nothing.

We standardized additively (never replacing): dotted
ICD-10-CM/ICD-9-CM/ICD-10-PCS codings added beside the originals, and
LOINC added to laboratory observations via an itemid→LOINC map (94.5%
coverage). This corrects conversion artifacts — real US-Core-conformant
endpoints expose standard system URIs — while preserving what makes real
data hard: no SNOMED CT anywhere, granular codes, NDC-only medications
behind `medicationReference` indirection. For the medication path, we
resolved MIMIC's 5,732 distinct NDCs to RxNorm products and ingredients
(99.8% mapped) and additively coded the Medication resources.

Gold cohorts were recomputed from the data itself: hierarchical ICD prefix
matching for diagnosis cohorts, LOINC+threshold evaluation for laboratory
cohorts, and ingredient-level matching for medication cohorts, yielding
patient-ID sets per phenotype. 105/108 phenotypes have a non-empty MIMIC
cohort (median diagnosis cohort ≈ 2,400 patients; hypertension 84,776; the
three empty phenotypes are structurally out of scope — ECG-based,
medication-only, and neonatal in an adult dataset). The full 42.3
million-resource dataset was loaded to ten FHIR server instances via bulk
`$import` with exact count verification.

### Models

Frontier: GPT-5.4, Claude Opus 4.7, Claude Sonnet 4.6. Small open-weight:
Qwen3.5-9B. Most cells were run once; a repeat study (n=3) characterized
run-to-run variance (see Limitations). Tier means over 388 cells are the
primary endpoints.

## Results

### Synthetic benchmark: tiers and models

**Table 1.** All-test-case mean F1, full 108 phenotypes / 388 test cases.

| Model | T1 | T2 | T3 |
|---|---|---|---|
| GPT-5.4 | 0.624 | 0.871 | **0.879** |
| Claude Sonnet 4.6 | 0.563 | 0.859 | 0.862 |
| Claude Opus 4.7 | 0.632 | 0.859 | 0.860 |
| Qwen3.5-9B | 0.257 | 0.476 | 0.710 |

Closed-book, frontier models cluster at F1 0.56–0.63. Tools are the
dominant lever: every model gains +0.23–0.30 from T1→T2. The methodology
playbook (T3) is approximately neutral for frontier models (−0.02 to
+0.02) but transformative for the small model (+0.234).

> **[FIGURE 4]** Model × tier (T1/T2/T3) grouped bar chart.

### Tools collapse the prompt-sophistication gap

**Table 2.** Mean F1 by prompt level and tier; "gap" is expert−naive.

| Model | T1 naive | T1 broad | T1 expert | T2 naive | T2 broad | T2 expert | gap T1→T2 |
|---|---|---|---|---|---|---|---|
| GPT-5.4 | 0.481 | 0.634 | 0.758 | 0.842 | 0.873 | 0.897 | 0.28 → 0.06 |
| Claude Opus 4.7 | 0.533 | 0.644 | 0.718 | 0.816 | 0.868 | 0.894 | 0.19 → 0.08 |
| Claude Sonnet 4.6 | 0.492 | 0.554 | 0.643 | 0.846 | 0.870 | 0.861 | 0.15 → 0.02 |
| Qwen3.5-9B | 0.072 | 0.150 | 0.551 | 0.283 | 0.363 | 0.778 | 0.48 → 0.50 |

Closed-book, prompt phrasing is worth up to +0.28 F1 (expert versus
naive). With tools, the gap collapses to ~0.02–0.08 for frontier models —
a naive prompt plus tools approaches an expert prompt plus tools. The
collapse is a frontier-model result: the small model still needs both
tools *and* a code-aware prompt (gap ~0.50 persists at T2).

> **[FIGURE 5]** Prompt-collapse lines (centerpiece): x = prompt level,
> y = F1; Opus exemplar: T1 line slopes 0.53→0.72, T2 line flat 0.82→0.89.

### The achievable ceiling: comprehensive cohorts

**Table 3.** Best tier×prompt configuration on the comprehensive
("find all my patients") cell — 80 phenotypes with a comprehensive case.

| Model | Best config | Best F1 (comprehensive) |
|---|---|---|
| GPT-5.4 | T2 + expert | 0.990 |
| Claude Sonnet 4.6 | T2 + expert | 0.986 |
| Claude Opus 4.7 | T3 + expert | 0.967 |
| Qwen3.5-9B | T3 + expert | 0.919 |

With the right configuration, frontier models essentially solve
whole-cohort retrieval on synthetic data (0.97–0.99). The headroom in
Table 1 lives in the harder per-path and trick variants.

### Methodology is a model-dependent lever — with a failure mode

The playbook's benefit concentrates where competence is missing: Qwen
gains +0.23 (T2 0.476 → T3 0.710); frontier models are flat. On
heterogeneous cross-coded phenotypes we identified a reproducible failure
mode: the playbook's "canonical code" framing led Opus to under-enumerate
subtype concepts (coronary heart disease: 32 concepts enumerated at T2 →
recall 1.00; 7 at T3 → recall 0.39). Averaged over all 388 cases this
washes out (Opus T2→T3 −0.02, within agentic noise), but it dictates
playbook design: instruct enumeration of the full subtype tail, not the
canonical code. A published generic FHIR-developer skill (prepended text,
no tools) added only +0.018 over plain closed-book for Opus — a generic
skill supplies what a frontier model already knows; the +0.21 gap to the
agentic stack comes from tools.

### Real-world data: MIMIC-IV

**Table 4.** Mean F1 by tier (Claude Opus 4.7) across the three data
regimes. The MIMIC full sweep is 1,592 cells (105 phenotypes ×
dx+comprehensive × 3 prompts × 3 tiers).

| Tier | Synthetic | MIMIC demo (100 pts) | MIMIC full (299,712 pts) |
|---|---|---|---|
| T1 closed-book | 0.632 | 0.090 | **0.036** |
| T2 agentic | 0.859 | 0.688 | **0.493** |
| T3 + methodology | 0.860 | 0.662 | **0.462** |

Three results. First, the tools lever survives and dominates: +0.46 T1→T2
(87% of closed-book cells return zero patients; only 11% of agentic cells
do). Closed-book queries default to SNOMED CT, which the real data does
not carry at all; agentic sampling discovers ICD-9/ICD-10 and enumerates
the granular codes present. Second, the 100-patient demo overstated
agentic recovery (0.69 → 0.49): T2 precision remains 0.71 but recall falls
to 0.48, and recall stratifies by cohort size — 0.70 for gold cohorts of
1,000–10,000 patients, 0.28 above 10,000. At scale, a large phenotype's
patients span a long tail of granular ICD codes; server samples reveal
only the head of the distribution, and partial enumeration caps recall.
Third, the expert-prompt inversion strengthens: T2 broad 0.556 > naive
0.539 ≫ expert 0.384 — code-aware hints anchor the model on absent
vocabularies and suppress the server-sampling behavior looser prompts
trigger.

On the medication path — the strictest discovery test, since medications
sit behind `medicationReference` with NDC-only local coding — closed-book
scored exactly zero in 197/198 cells, while the agentic loop recovered F1
0.429 (precision 0.774), with successful cells independently discovering
the chained ingredient-level search pattern
(`MedicationRequest?medication.code=<rxnorm>|<ingredient>`). The broad >
expert inversion replicated (0.469 versus 0.401). The recomputed
medication cohorts also confirm the cross-indication phenomenon the
synthetic trick paths model, at real-world magnitude: peripheral arterial
disease has 67,288 patients on its medication classes against 6,748
diagnosed.

A subset of the worst large-cohort cells are benchmark artifacts rather
than model failures (a resistant-hypertension gold that prefix-matches the
whole hypertension family; pediatric phenotypes whose age guards cannot
apply to offline gold on an adult dataset; allergy phenotypes whose
natural resource, AllergyIntolerance, MIMIC-on-FHIR does not populate).
Excluding these three phenotypes (45 cells) moves tier means by ~+0.01 and
leaves every conclusion unchanged; they are retained in the primary
analysis.

> **[FIGURE 6]** (a) Tier means across the three data regimes (synthetic /
> MIMIC demo / MIMIC full), annotating the T1 collapse and demo→full
> recall gap; (b) T2-broad recall by gold-cohort-size bucket
> (0.41 / 0.64 / 0.70 / 0.28) — the code-tail coverage story.

## Discussion

**Cohort recall is concept coverage.** The through-line across every
intervention is whether the final query enumerates all clinical
concepts/subtypes the cohort is coded with. Expert prompts hand the model
concepts; tools let it *discover* them (sample the server, expand value
sets, crosswalk); over-tight methodology prunes them. On synthetic data
(generous multi-system coding) concept coverage is the whole game; on real
data the model must additionally discover *which system and at what
granularity* — which is why closed-book collapses and tools grow more
valuable.

**Tools democratize cohort identification.** The prompt-gap collapse is
the practically important finding: with a proper agentic loop, a
clinician's plain-English request approaches an informaticist's code-aware
specification. Institutionally, investment in tooling (terminology
services, server introspection) dominates investment in prompt
engineering.

**Match strategy to model.** Methodology playbooks are scaffolding for
models that lack phenotyping competence; for frontier models they are at
best neutral and can induce under-enumeration if phrased canonically.

**Real EHR data is an adversarial distribution shift** for parametric
recall: single code system, granular codes, exact-match servers,
NDC-behind-reference medications. Benchmarks built only on multi-coded
synthetic data overstate closed-book competence; our synthetic/real
pairing quantifies the gap under an identical harness.

**Scale is part of the distribution shift.** The demo→full gap (T2 0.69 →
0.49) shows that real-data difficulty grows with cohort code-diversity:
small samples of real data flatter agentic models because small cohorts
have short code tails. Benchmarks should report performance stratified by
cohort size, and agentic methodologies should mandate count-guided,
iterative code-tail expansion rather than one-shot enumeration.

**Describe the population; don't prompt with codes.** The expert-prompt
inversion at scale (−0.17 versus broad at T2) turns a synthetic-data
nicety into deployment guidance: on unfamiliar servers, embedding codes in
the request anchors the agent on possibly-absent vocabularies and
suppresses discovery. The best human interface to a cohort agent is
precise *clinical* language, not precise *coding* language.

### Limitations

Agentic run-to-run variance: most cells are n=1; a repeat study (n=3,
Opus, 138 T2/T3 cells over 12 MIMIC phenotypes) measured median per-cell
F1 range 0.07 but a heavy tail (7% of cells swing >0.5, usually one
attempt emitting a zero-result query). Aggregate tier means over identical
cells are stable to ~±0.03, so tier-level deltas below ~0.05 are within
noise while the headline levers (+0.23–0.60) are an order of magnitude
above it; single-cell comparisons should not be read at n=1. Synthetic
generosity: multi-coded patients mean the synthetic benchmark does not
test code-system selection (the MIMIC arm does). MIMIC scoring paths:
diagnosis, laboratory, their union, and (via the NDC→RxNorm ingredient
crosswalk) medications are scored; procedures remain future work, and
medication gold matches at ingredient level. MIMIC caveats: laboratory
thresholds over-capture in an ICU population; two histology phenotypes
score at ICD category level; pediatric phenotypes match on codes only in
an adult dataset. Expert prompts were rewritten to remove embedded queries
(de-leak); residual phrasing effects are possible. One FHIR server
implementation per arm; server search-feature differences (e.g.,
`code:below`) matter and are part of what tools must discover.

## Conclusion

Even frontier LLMs are mediocre closed-book cohort finders and heavily
prompt-dependent; a modest agentic loop over server introspection and
terminology services is the dominant, prompt-equalizing lever, and its
value grows on real EHR data where parametric recall fails structurally.
The practical product of the benchmark is a reusable cohort-query agent:
lean methodology, long-tail concept enumeration, server-first discovery,
and UMLS/VSAC integration, pointable at any FHIR endpoint.

---

## Funding

*(TODO: state funding sources, or "This research received no specific
grant from any funding agency in the public, commercial, or not-for-profit
sectors.")*

## Competing Interests

*(TODO — must declare: author employment at Microsoft; the evaluation used
Microsoft Copilot model endpoints and Azure infrastructure, and Claude/GPT
models from Anthropic/OpenAI.)*

## Author Contributions

*(TODO: CRediT taxonomy — e.g., JE: Conceptualization, Methodology,
Software, Investigation, Data curation, Formal analysis, Writing –
original draft.)*

## Data Availability

Benchmark test cases, Synthea modules, augmentation and evaluation
pipelines, and the cohort-query agent are available in the project
repository *(TODO: archive a release with a DOI, e.g., Zenodo)*. MIMIC-IV
is available to credentialed users via PhysioNet; per the PhysioNet Data
Use Agreement, no MIMIC-derived artifacts (gold patient cohorts,
itemid→LOINC maps, NDC lists) are redistributed. Credentialed users can
regenerate them with the included scripts.

## Acknowledgements and AI Use Disclosure

Large language models are the subject of this study; the models and
versions evaluated are enumerated in Materials and Methods. In addition,
LLM-based tooling (Claude, Anthropic) was used to assist with evaluation
harness development and manuscript drafting; all analyses, results, and
claims were verified by the authors. *(JAMIA requires this disclosure in
the cover letter as well.)*

## References

1. Hripcsak G, Albers DJ. Next-generation phenotyping of electronic health
   records. J Am Med Inform Assoc. 2013;20(1):117–121.
   doi:10.1136/amiajnl-2012-001145
2. Banda JM, Seneviratne M, Hernandez-Boussard T, et al. Advances in
   electronic phenotyping: from rule-based definitions to machine learning
   models. Annu Rev Biomed Data Sci. 2018;1:53–68.
   doi:10.1146/annurev-biodatasci-080917-013315
3. Kirby JC, Speltz P, Rasmussen LV, et al. PheKB: a catalog and workflow
   for creating electronic phenotype algorithms for transportability.
   J Am Med Inform Assoc. 2016;23(6):1046–1052. doi:10.1093/jamia/ocv202
4. Gottesman O, Kuivaniemi H, Tromp G, et al. The Electronic Medical
   Records and Genomics (eMERGE) Network: past, present, and future.
   Genet Med. 2013;15(10):761–771. doi:10.1038/gim.2013.72
5. Mo H, Thompson WK, Rasmussen LV, et al. Desiderata for computable
   representations of electronic health records-driven phenotype
   algorithms. J Am Med Inform Assoc. 2015;22(6):1220–1230.
   doi:10.1093/jamia/ocv112
6. HL7 International. HL7 FHIR Release 4 (R4) specification.
   https://hl7.org/fhir/R4/. Accessed September 2, 2026.
7. Mandel JC, Kreda DA, Mandl KD, et al. SMART on FHIR: a standards-based,
   interoperable apps platform for electronic health records. J Am Med
   Inform Assoc. 2016;23(5):899–908. doi:10.1093/jamia/ocv189
8. Bodenreider O. The Unified Medical Language System (UMLS): integrating
   biomedical terminology. Nucleic Acids Res. 2004;32(Database
   issue):D267–D270. doi:10.1093/nar/gkh061
9. Walonoski J, Kramer M, Nichols J, et al. Synthea: an approach, method,
   and software mechanism for generating synthetic patients and the
   synthetic electronic health care record. J Am Med Inform Assoc.
   2018;25(3):230–238. doi:10.1093/jamia/ocx079
10. Johnson AEW, Bulgarelli L, Shen L, et al. MIMIC-IV, a freely
    accessible electronic health record dataset. Sci Data. 2023;10(1):1.
    doi:10.1038/s41597-022-01899-x
11. Bennett AM, Ulrich H, van Damme P, et al. MIMIC-IV on FHIR: converting
    a decade of in-patient data into an exchangeable, interoperable
    format. J Am Med Inform Assoc. 2023;30(4):718–725.
    doi:10.1093/jamia/ocad002
12. Lee G, Hwang H, Bae S, et al. EHRSQL: a practical text-to-SQL
    benchmark for electronic health records. Adv Neural Inf Process Syst.
    2022;35:15589–15601.
13. Klang E, Tessler I, Apakama DU, et al. Assessing retrieval-augmented
    large language model performance in emergency department ICD-10-CM
    coding compared to human coders. medRxiv [preprint]. 2024.
    doi:10.1101/2024.10.15.24315526
14. Syed M, Hamidi M, Bikkanuri M, et al. Translating evidence into
    practice: adapting TrialGPT for real-world clinical trial eligibility
    screening. J Am Med Inform Assoc. 2026;33(4):909–913.
    doi:10.1093/jamia/ocag006
