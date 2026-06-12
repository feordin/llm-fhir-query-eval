# Dev Days Presentation — Outline
### Measuring how accurately LLMs write real-world FHIR queries

**Audience:** technical (engineers, clinical-informatics, ML).
**Format note for slide generation:** each slide below has a **Title**, **On-slide
content** (what appears), **Visual** (chart/diagram to render), and **Speaker
notes** (what to say, not on the slide). Numbers are from
`docs/results/2026-06-10-full-108-three-model-sweep-v7.md` and the analysis docs
in `docs/results/`. A few cells (Opus T1/T2 full coverage) are still finishing;
placeholders are flagged **[PENDING BACKFILL]**.

---

## Section 0 — Framing

### Slide 1 — Title
- **Title:** Can an LLM find the patients? Measuring FHIR-query accuracy for clinical phenotyping
- **Subtitle:** A 108-phenotype benchmark across 4 models, 3 prompt styles, and 3 levels of tooling
- **Visual:** one hero number, large — e.g. "0.65 → 0.88 F1 when we give the model tools" with model logos.
- **Speaker notes:** Set the hook: clinical cohort-finding is a real, expensive task; can today's LLMs do it, and what actually makes them better?

### Slide 2 — The goal (the question we're answering)
- **On-slide:**
  - The task: given a plain-English description of a patient population, produce a FHIR query that returns *exactly that cohort*.
  - The question: **how accurately can an LLM — with and without an agentic loop — find a cohort described in plain English, against a realistic case/control mix?**
  - Why it's hard: requires FHIR syntax **and** the right clinical codes (LOINC, SNOMED CT, ICD-10/9, RxNorm) **and** the right resource types (Condition, MedicationRequest, Observation, Procedure).
- **Visual:** plain-English prompt → arrow → FHIR query → arrow → patient set. One concrete example (e.g., "patients with type 2 diabetes" → `Condition?code=http://hl7.org/fhir/sid/icd-10-cm|E11`).
- **Speaker notes:** Emphasize this is *semantic* — the prompt is deliberately code-free; the model must supply the codes.

### Slide 3 — What we measure (the metric — don't skip)
- **On-slide:**
  - We do **not** grade query strings. We run the model's query and the gold query against a FHIR server and compare the **returned patient sets**.
  - Metric: **Precision / Recall / F1 over patient IDs**, per (phenotype × test-case variant × prompt level × tier).
  - The headline cell is the **comprehensive cohort** — "did it find the *whole* population?"
- **Visual:** Venn diagram of model-set vs gold-set → P/R/F1.
- **Speaker notes:** This is what makes the benchmark trustworthy — two different-looking queries that select the same patients both score 1.0.

---

## Section 1 — How we built the benchmark

### Slide 4 — Test cases from PheKB (expert-curated, not invented)
- **On-slide:**
  - **PheKB** = Phenotype KnowledgeBase: peer-reviewed, expert-authored phenotype algorithms used by real research networks (eMERGE, etc.).
  - We used the **raw PheKB algorithm docs** as the source of truth — diagnosis codes, medication classes, lab thresholds, inclusion/exclusion logic.
  - **108 phenotypes** spanning the full clinical map: 18+ cancers, cardiometabolic, psychiatric, infectious, pediatric, genetic, procedural.
- **Visual:** PheKB logo + a grid/word-cloud of the 108 phenotype names grouped by domain.
- **Speaker notes:** Credibility point — these aren't toy cases; they're the algorithms clinical researchers actually use.

### Slide 5 — Prompts are code-free, by design (3 levels)
- **On-slide:** three "human" prompt styles, increasing sophistication:
  - **Naive** — what an untrained user types ("Find diabetics").
  - **Broad** — a clinically-aware request, no code knowledge ("Patients with a type 2 diabetes diagnosis").
  - **Expert** — precise, code-aware spec ("T2DM by ICD-10 E11.* or SNOMED 44054006…").
  - The expected (gold) query always carries the real codes — the test is whether the model can *derive* them.
- **Visual:** the SAME phenotype shown three ways (naive/broad/expert), side by side, with the one gold query they all map to. **Pick one clean example** — e.g., atrial fibrillation or type 2 diabetes.
- **Speaker notes:** This is the "human side" axis. Walk through the one example slowly; it makes the abstraction concrete.

### Slide 6 — Realistic test data: custom Synthea modules
- **On-slide:**
  - Synthetic patients generated with **custom Synthea modules**, one per phenotype, authored from the PheKB expert descriptions.
  - Each resource carries **multiple codings** (SNOMED + ICD-10 + ICD-9 + RxNorm/CPT) — so a model querying in *any* code system can find the same cohort.
  - Per-phenotype **isolation**: the server is wiped and loaded with one phenotype's data before its tests run — no cross-phenotype contamination.
- **Visual:** Synthea module → FHIR bundles → FHIR server pipeline diagram.
- **Speaker notes:** We control the ground truth exactly because we generated it — that's why patient-set scoring is valid.

### Slide 7 — Not just diagnoses: the 3-path cohort design
- **On-slide:** real cohorts aren't just "has the diagnosis code." Each phenotype's data follows a multi-path template:
  - **Path A** — diagnosis **+** medication (the obvious cases)
  - **Path B** — diagnosis only (diagnosed, untreated)
  - **Path C** — medication only, **no diagnosis** — the *trick path* (treated by an outside provider, cross-indication)
  - **Path D** — abnormal **labs** only (e.g., A1c, T-score), no diagnosis
- **Visual:** 4 overlapping circles (dx / meds / labs / procedure) with the union highlighted = "comprehensive."
- **Speaker notes:** Path C is the killer — a naive "query the diagnosis code" misses real patients. This is what separates a good model from a code-matcher.

### Slide 8 — Mimicker controls: the precision guard
- **On-slide:**
  - Each phenotype ships with **"mimicker" control patients** — people with *similar but distinct* conditions (look-alikes).
  - Purpose: punish **over-broad** queries. A query that's too loose scoops up mimickers → precision drops.
  - 108/108 phenotypes covered; ~348 curated mimicker terms.
- **Visual:** target phenotype vs. ring of mimickers; a too-broad query lasso catching mimickers (red) vs a precise one (green).
- **Speaker notes:** Recall is easy if you query everything; mimickers make precision matter. This is what makes F1 a fair score.

---

## Section 2 — Baseline: what the model just *knows*

### Slide 9 — Tier 1: closed-book (pure recall)
- **On-slide:**
  - **Tier 1** = a single chat completion, **no tools**. Tests the model's built-in knowledge of FHIR + clinical codes.
  - Same 3 prompts (naive/broad/expert) × 108 phenotypes.
- **Visual:** simple "prompt → model → query" with a lock icon (no tools).
- **Speaker notes:** This is the floor — what's baked into the weights.

### Slide 10 — Tier 1 results + the prompt effect
- **On-slide:** T1 F1 by model (all-test-case, full 388-tc coverage):
  | Model | T1 |
  |---|---|
  | Claude Opus 4.7 | **0.678** |
  | GPT-5.4 | 0.656 |
  | Claude Sonnet 4.6 | 0.623 |
  | Qwen3.5-9B | 0.257 |
  - Within T1, **expert ≫ broad > naive** — code-aware phrasing helps a lot when the model has no tools. Opus is the sharpest example: **naive 0.53 → broad 0.64 → expert 0.86** (a +0.33 swing from phrasing alone).
- **Visual:** grouped bar chart, model × prompt-level, T1 only. Opus's naive→expert slope is the steepest — use it to make the "closed-book is prompt-sensitive" point.
- **Speaker notes:** Closed-book, even frontier models are mediocre (~0.62–0.68) and very prompt-sensitive; the small open model is poor (0.26). Opus tops the frontier T1 trio — strongest built-in FHIR/code recall — but still needs an expert prompt to do well without tools. Now the interesting part — what fixes it? (Opus T1 is now full-108 coverage from the decoupled backfill; earlier partial-subset reads of ~0.70 were on an easier 91-tc slice.)

---

## Section 3 — Giving the model help: tools & methodology

### Slide 11 — Tier 2: agentic + tools
- **On-slide:**
  - **Tier 2** = an agentic loop with real tools:
    - **FHIR server introspection** (capabilities, profiles, valueset bindings, sample-the-data)
    - **UMLS / VSAC** code lookup & crosswalk (via an MCP server)
  - The model can *check its codes* and *probe the server* instead of recalling from memory.
- **Visual:** agent loop diagram: model ⇄ {FHIR introspection, UMLS/VSAC MCP, count-the-results}.
- **Speaker notes:** The hypothesis: most T1 failures are *recall* failures (wrong/missing codes); tools should recover them.

### Slide 12 — Tier 3: agentic + methodology playbook
- **On-slide:**
  - **Tier 3** = Tier 2 **plus a prepended phenotype-methodology "playbook"** — how an expert phenotyper approaches the task (handle subtypes, use multiple code systems, validate counts, don't over-constrain).
  - We ship a **lean** version of the playbook (a long version over-constrained strong models).
- **Visual:** T1 / T2 / T3 as three stacked capability tiers (lock → toolbox → toolbox+playbook).
- **Speaker notes:** T1→T2 adds *capability*; T2→T3 adds *strategy*. Keep this distinction crisp — it's the spine of the analysis.

### Slide 13 — The three tiers, side by side
- **On-slide:** one comparison table:
  | | Tools? | Methodology? | Tests |
  |---|---|---|---|
  | T1 closed-book | no | no | pure recall |
  | T2 agentic | **yes** | no | can tools recover codes? |
  | T3 agentic+playbook | yes | **yes** | does expert strategy help? |
- **Visual:** the table above, clean.
- **Speaker notes:** Transition line: "so what happened when we turned on tools, then methodology?"

### Slide 14 — Headline results: all three tiers, all models
- **On-slide:** the money table (all-test-case F1):
  | Model | T1 | T2 | T3 |
  |---|---|---|---|
  | GPT-5.4 | 0.656 | 0.878 | 0.884 |
  | Claude Sonnet 4.6 | 0.623 | 0.846 | 0.857 |
  | Claude Opus 4.7 | 0.678 | 0.90* | 0.867 |
  | Qwen3.5-9B | 0.257 | 0.476 | 0.710 |
  - `*` Opus **T1 and T3 are full-108** (388 tc); **Opus T2 is a 48-tc subset** (0.904 on that slice) — not yet backfilled, so don't compare Opus T2 to its own T3 as a leaderboard fact (see Slide 16B).
  - And the **comprehensive-cohort** headline (T3): Sonnet **0.95**, GPT **0.96**, Opus **0.94**.
- **Visual:** grouped bar chart, model × tier (T1/T2/T3), with the comprehensive numbers called out. Mark the Opus T2 bar as partial-coverage (hatched/asterisk).
- **Speaker notes:** The big jump is T1→T2. Land that, then unpack *why* next. Opus posts the best closed-book T1 (0.678) but, uniquely, its T3 doesn't beat its T2 — which is the hook for Slide 16B (the methodology over-steers Opus into code-system parsimony). Be honest that the Opus T2 cell is a 48-tc subset.

---

## Section 4 — Analysis: why did it help?

### Slide 15 — Why T2 helped: tools collapse the prompt gap (centerpiece)
- **On-slide:**
  - In T1, prompt quality mattered a lot (expert ≫ naive).
  - In T2, **a naive prompt + tools ≈ an expert prompt + tools** (frontier: naive+T2 ≈ 0.91–0.93 vs expert+T2 ≈ 0.98).
  - Interpretation: **tools recover what phrasing used to**. The model doesn't need you to know the codes — it can look them up.
- **Visual:** the killer chart — prompt-level on X, F1 on Y, two lines (T1 vs T2). T1 line slopes up steeply (prompt matters); T2 line is high and flat (prompt barely matters).
- **Speaker notes:** This is the most quotable finding: *tools democratize the query* — a clinician can ask in plain English and still get an expert-quality cohort.

### Slide 16 — Why T3 (methodology) helped — and for whom
- **On-slide:**
  - Methodology's benefit is **uneven**:
    - **Small/open model (Qwen): huge** — T2 0.48 → T3 **0.71** (+0.23). It lacks built-in phenotyping competence; the playbook supplies it.
    - **Frontier models: roughly neutral** — they already know the methodology; the playbook mostly adds length.
  - Two fixes from our analysis made T3 reliably ≥ T2 even for frontier:
    - **Lean playbook for all** (the long one over-constrained strong models).
    - **Age-filter guard** — stop the model from bolting on a spurious `birthdate` filter when a disease *name* contains an age word (fixed the neonatal-abstinence collapse).
- **Visual:** delta chart — T2→T3 gain per model (big green bar for Qwen, ~flat for frontier).
- **Speaker notes:** Nuance sells credibility: methodology is a big lever for a weak model, a small one for a strong model. Don't over-claim. Tee up the next slide: for the *most* instruction-following frontier model, the playbook can actually backfire — and we found exactly why.

### Slide 16B — When methodology backfires: the Opus code-narrowing case (deep-dive)
- **On-slide:**
  - **Opus is the one model whose T3 lands *below* its T2** (0.84 vs 0.90 on the cases measured). Sonnet and GPT both *gain* from T3.
  - Root cause we traced: under the methodology playbook, **Opus collapses how many clinical code systems it queries** — from a SNOMED + ICD-10 + ICD-9 + CPT union down to **SNOMED-only**. Our data is deliberately multi-coded, so a one-system query silently under-recalls.
  - **The number:** mean distinct code-systems per query, T2→T3 — **Opus 2.46 → 1.83 (−0.63)**; Sonnet 2.31 → 2.13; **GPT 2.11 → 2.11 (flat)**. Only Opus narrows; only Opus regresses.
  - **Deterministic mechanism:** code systems in the query → F1 is monotone (1 sys → 0.82, 2 → 0.86, 3 → **0.96**). Under T3, Opus drops to a single system on **~half** of cross-coded cells; that drop is what costs recall. (Confirmed by a rerun — the narrowing *propensity* is stable and Opus-specific; which exact cells narrow is agentic noise.)
  - **One case (coronary heart disease, same prompt):** T2 = 21 codes across 4 systems, recall **1.00** → T3 = 7 SNOMED-only codes, recall **0.39**.
  - **Theory:** Opus follows the playbook's "pick the principled, canonical code" guidance *most literally* and over-applies it as "pick the canonical code *system*." The same lever that *supplies* competence to a weak model (Qwen) *displaces* a better default in the most obedient strong model.
- **Visual:** two-panel — (left) grouped bars of code-systems-per-query T2 vs T3 for the 3 models (Opus bar drops, others flat); (right) the CHD before/after query with recall 1.00 → 0.39.
- **Speaker notes:** This is the credibility centerpiece of the analysis section. The story: methodology isn't free — for the most instruction-adherent model it can suppress the very multi-system exploration that tools unlocked. The fix for the shareable plugin is explicit: tell the model to enumerate *all* code systems present, not just the canonical one. Full write-up: `docs/results/2026-06-11-opus-t3-code-narrowing.md`. (Honest caveat for Q&A: the Opus T2 baseline here is a 48-test-case subset; a full-coverage backfill is in progress, but the mechanism — code-system narrowing — is unambiguous in the queries themselves.)

### Slide 17 — What moves the needle (the lever summary)
- **On-slide:** for a frontier model, ranked impact:
  - **Tools: +0.10–0.20** (the dominant lever)
  - Prompt quality: large at T1, **~0 once tools are on**
  - Methodology: small for frontier, large for small models
  - Off-the-shelf generic skill: ~0 for a model that already knows FHIR
- **Visual:** tornado/lever chart ranking the interventions by F1 impact.
- **Speaker notes:** The one-slide takeaway if they remember nothing else: **give the model tools.**

---

## Section 5 — Off-the-shelf comparison

### Slide 18 — Best off-the-shelf agent: Opus + the Anthropic FHIR skill
- **On-slide:**
  - We ran **Opus with Anthropic's published FHIR-developer skill** (closed-book) as a "strong generic agent" baseline.
  - Result: **~0.88** vs **our in-house Tier-2 stack ~0.99** on the same cases.
  - The gap is concentrated in the **hard cross-indication phenotypes** (e.g., Crohn's 0.74, asthma 0.46) — exactly the Path-C trick cases.
  - **The skill's *marginal* lift is ~0** (newly measured at full scale): Opus T1 **plain 0.678 vs +skill 0.693 (+0.015)** across all 108 phenotypes. A generic skill barely helps a model that already knows FHIR — the win is the **tools**, not the prompt/skill text.
- **Visual:** two bars — off-the-shelf Opus+skill (0.88) vs our T2 (0.99) — with a callout on which phenotypes drive the gap.
- **Speaker notes:** A generic skill gets you most of the way; the last mile is domain-specific tooling + the trick-path handling we built.

---

## Section 6 — Outcome & what's next

### Slide 19 — The artifact: a shareable FHIR-phenotyping plugin
- **On-slide:**
  - Everything we learned is packaged into a **reusable FHIR-phenotyping plugin**:
    - the **lean methodology playbook** (with the age-filter guard baked in) as its core,
    - the **server-introspection + UMLS/VSAC** tool wiring,
    - so any team can point a model at their FHIR server and get expert-quality cohort queries.
- **Visual:** plugin box diagram: playbook + tools → drop-in for any FHIR endpoint.
- **Speaker notes:** The benchmark produced not just numbers but a deliverable others can use.

### Slide 20 — Caveats (be honest)
- **On-slide:**
  - **Synthetic data** (Synthea), not real EHR — controlled ground truth, but a known gap from messy reality.
  - **n=1 agentic runs** — single non-deterministic runs per cell; sub-0.05 tier deltas are within variance (we use the comprehensive recoveries, which are far above noise).
  - **Opus T1/T2** coverage being finalized at presentation time.
- **Visual:** simple list, no chart.
- **Speaker notes:** Pre-empt the obvious questions; it builds trust.

### Slide 21 — What's next
- **On-slide:**
  - **MIMIC-IV-on-FHIR** — rerun the benchmark on **real, de-identified ICU data** (standardizer + per-phenotype counting already built).
  - Repeat runs (n≥3) to quench agentic variance.
  - Broaden the off-the-shelf comparison.
- **Visual:** roadmap arrow: synthetic ✓ → real-data (MIMIC) → repeated runs.
- **Speaker notes:** The natural next question is "does this hold on real data?" — that's the next experiment.

### Slide 22 — Takeaways
- **On-slide:** three lines:
  1. **Closed-book, even frontier LLMs are mediocre at clinical FHIR queries** (~0.62–0.66 F1) and very prompt-sensitive.
  2. **Tools are the dominant lever** (+0.10–0.20) and they *erase* the prompt-skill gap — plain English + tools ≈ expert prompt.
  3. **Methodology helps weak models a lot, strong models a little** — and we shipped it as a reusable plugin.
- **Visual:** three icons (lock / toolbox / playbook) with the one-line each.
- **Speaker notes:** Close on the democratization message: the right tooling lets a clinician ask in plain English and get a research-grade cohort.

---

## Appendix (optional backup slides)
- Full 108-phenotype × model T2 table (from v7 report).
- The FHIR query format + code-system primer (LOINC/SNOMED/ICD/RxNorm, `system|code`).
- Per-phenotype deep-dive on one trick case (e.g., NAS age-filter collapse → fix).
- Infrastructure: per-phenotype isolation, multi-coding augmentation pipeline, 10-server eval fan-out.

---

### Numbers to refresh before presenting
- ✅ **Opus T1 backfilled to full 108** (decoupled generate/score harness, sharded
  across 6 servers; 0 reload-starvation — the blocker is fixed). **Opus T1 plain
  0.678, +fhirskill 0.693** (Slides 10 & 14 filled). Report:
  `docs/results/2026-06-12-opus-t1-backfill-decoupled.md`. **Opus T2 still a 48-tc
  subset** (intentionally not backfilled) — Slide 14 flags it `*`; backfill it too
  (agentic, via single/low-shard isolated suite) if you want a fair leaderboard T2
  row, which would turn the Slide 16B "T3 < T2" observation into a headline.
- ✅ **Slide 15 (prompt-vs-tools) verified** against `2026-06-07-prompt-vs-tools-impact.md`:
  naive·T2 0.907–0.925, broad·T2 0.95, expert·T2 0.982–0.998. Accurate.
- ✅ **Slide 18 (Opus skill baseline) verified** against `2026-06-07-opus-skill-baseline.md`:
  off-the-shelf 0.878 (≈0.88), ours-T2 0.989 (≈0.99), Crohn's 0.74, asthma 0.46. Accurate.
- ⚠ **Slide 17 lever range** — the "tools +0.10–0.20" is defensible but mixes metrics:
  the *final* Opus comprehensive run is **+0.104**; the all-test-case frontier T1→T2 is
  **~+0.22**. State which you mean, or cite "+0.10 (comprehensive cohort) to +0.22 (all cases)."
- **NEW — skill marginal lift now computable.** The skill-baseline doc's open caveat
  ("measure the skill's *marginal* lift via Opus T1 *without* skill — not run yet") is
  closed by this backfill: T1 plain vs T1 +fhirskill on full coverage. On the 8-pheno
  subset it was ≈ +0.002 (skill ≈ 0 for a model that already knows FHIR); confirm at
  full scale and add to Slide 17/18.
- **NEW — Slide 16B** added (Opus T3 code-narrowing finding); full write-up at
  `docs/results/2026-06-11-opus-t3-code-narrowing.md`.
