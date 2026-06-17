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
- **Visual:** one hero statement, large — **"Plain English + tools ≈ an expert hand-writing codes"** with the supporting jump *0.66 → 0.88 F1* and model logos. (Alt hero for drama: the small open model goes **0.26 → 0.71** with tools+methodology.)
- **Speaker notes:** Set the hook: clinical cohort-finding is a real, expensive task; can today's LLMs do it, and what actually makes them better? The answer (tease): it's not a bigger model or a better prompt — it's tools, because the task is really about covering the code systems patients are coded in.

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
  - **Diagnoses and procedures carry multiple codings** — Conditions as **SNOMED + ICD-10-CM + ICD-9-CM**, Procedures as **SNOMED + CPT** (injected by a post-Synthea crosswalk of the phenotype-defining codes). (Medications use **RxNorm** and labs use **LOINC** — single standards, not crosswalked.)
  - **This is a deliberate *generosity* to the model:** because each diagnosed patient carries the concept in every system, **whichever code system the model queries, it still finds the patient.** So the benchmark does *not* test "did you pick the right code system" — it tests "did you enumerate the right clinical *concepts*." (Caveat / future work: a real single-EHR uses one system per site; a sharper design would give each patient *one* randomly-chosen system and test whether the model covers them all — see Slide 21.)
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
  | Claude Opus 4.7 | **0.679** |
  | GPT-5.4 | 0.656 |
  | Claude Sonnet 4.6 | 0.623 |
  | Qwen3.5-9B | 0.257 |
  - Within T1, **expert ≫ broad > naive** — code-aware phrasing helps a lot when the model has no tools. Opus is the sharpest example: **naive 0.53 → broad 0.64 → expert 0.86** (a +0.33 swing from phrasing alone).
- **Visual:** grouped bar chart, model × prompt-level, T1 only. Opus's naive→expert slope is the steepest — use it to make the "closed-book is prompt-sensitive" point.
- **Speaker notes:** Closed-book, even frontier models are mediocre (~0.62–0.68) and very prompt-sensitive; the small open model is poor (0.26). Opus tops the frontier T1 trio — strongest built-in FHIR/code recall — but still needs an expert prompt to do well without tools. Now the interesting part — what fixes it? (Opus T1 is now full-108 coverage from the decoupled backfill; earlier partial-subset reads of ~0.70 were on an easier 91-tc slice.)

---

## Section 3 — Giving the model help: tools & methodology

### Slide 11 — Tier 2: the agentic loop (what it actually does)
- **On-slide:**
  - **Tier 2** = an agentic loop with **10 tools** — FHIR (`server_metadata`, `search`, `resource_sample`) + UMLS (`search`, `crosswalk`) + VSAC (`search`/`expand`/`validate`/`lookup`/`subsumption`). The model is told **never answer from memory — the first action must be a tool call.** The actual workflow it's instructed to run:
    1. **Find the concept's codes** — `umls_search` (concept → CUI → codes across vocabularies), or a VSAC value set (`vsac_search_value_sets` → `vsac_expand_value_set`).
    2. **Sample the live server** (`fhir_resource_sample`) to see *which code systems the data actually uses*; `fhir_server_metadata` to confirm a search param exists.
    3. **Validate the magnitude** — run the query with `_summary=count` (`fhir_search`) and **self-correct: 0 results → codes too narrow (add subtypes/synonyms); implausibly large → a clinical filter is missing.**
    4. Emit the final FHIR query URL(s) — multi-resource cohorts as one URL per line (the evaluator unions the patient sets).
- **Visual:** loop diagram — find codes (UMLS/VSAC) → sample server (which systems?) → count & validate → **revise** (the 0/too-many self-correction arrow) → final query.
- **Speaker notes:** The key shift from T1 is *evidence-gathering, not recall* — it checks codes against UMLS/VSAC and probes the real server before answering. The count-and-revise step is what recovers the codes T1 missed. (Implementation: a system prompt with these rules + the 10 tools; the model runs the loop until it emits query URLs.)

### Slide 11B — Tier 2 under the hood: how the agent actually talks to the data
- **On-slide:**
  - **The harness:** the model runs inside the **GitHub Copilot Agent SDK**, which runs the tool-calling loop internally — we hand it the system prompt + the 10 tools (registered as `@define_tool` wrappers); it iterates (model → tool call → result → model …) and returns the final query. A single T2 turn touches **three services**: the LLM, the FHIR server, and a clinical-terminology server.
  - **① The live FHIR server — direct FHIR REST (no MCP needed; FHIR *is* a REST API).** The FHIR tools issue plain HTTPS GETs against the real Microsoft FHIR server — exactly what an engineer would `curl`:
    - `GET /metadata` → CapabilityStatement (which resources & search params exist)
    - `GET /{ResourceType}?…&_summary=count` → cohort magnitude (the count-and-revise step)
    - `GET /{ResourceType}?_count=N` → sample real resources to see *which code systems the data uses*
  - **② The NIH UMLS MCP server (`nih-umls`) — the clinical-terminology backend.** The code-lookup tools call it: `umls_search` / `umls_crosswalk` → **NIH UTS** (UMLS Terminology Services) REST API; `vsac_*` → the **VSAC** (Value Set Authority Center) FHIR API. Authenticated with a **UMLS API key**. This is the *same engine* exposed as the `/umls` MCP server elsewhere in the project.
  - **So "the agent" = LLM (Copilot) ⇄ { FHIR REST on the live server, UMLS/VSAC via the NIH UMLS MCP server }.** Example trace for type-2-diabetes: `vsac_search_value_sets("type 2 diabetes")` → `vsac_expand_value_set(oid)` (full code family) → `fhir_resource_sample(Condition)` (see SNOMED vs ICD) → `fhir_search(Condition?code=…&_summary=count)` (validate) → emit query.
- **Visual:** center node = **model (Copilot Agent SDK loop)**; arrow right to **FHIR server** labeled with the 3 REST calls (`/metadata`, `?_summary=count`, `?_count=N`); arrow left to **NIH UMLS MCP server** labeled UMLS UTS + VSAC FHIR. A small key: "FHIR = direct REST · terminology = MCP server."
- **Speaker notes:** This is the slide that answers "what's the MCP server and how does it hit FHIR." Two distinct channels: **clinical terminology** (concepts → codes, code families, crosswalks) comes from the **NIH UMLS MCP server** (UMLS + VSAC, API-key'd); the **FHIR data access** is plain **FHIR REST** straight to the live server (FHIR is already a RESTful HTTP API, so no MCP layer is needed — the tool just does authenticated GETs). The agent is doing exactly what a clinical-informatics engineer does by hand — discover codes from UMLS/VSAC, sample the server to learn its coding, count to sanity-check — just in an automated loop.

### Slide 12 — Tier 3: + a phenotyping playbook (what it adds)
- **On-slide:**
  - **Tier 3** = the same T2 loop **plus a prepended methodology playbook**. Its core is a mandatory **STEP 0 — categorize the request** into one or more of **~12 named playbooks** via a keyword cheat-sheet, *then* build the query:
    - "without / but not" → **Negation** (two queries; subtract patient sets)
    - "≥ / above / threshold" → **Threshold** (`value-quantity=ge…`)
    - "men / women" → **Sex** (`patient.gender`); "all my patients" → **Cohort = OR** (multi-resource union); "validated case" → **AND** via `_has`
    - subtypes (cancers, diabetes families) → query the **umbrella code + every subtype**, not just one
  - Plus universal tactics: **sample the server first, crosswalk unknown codes via UMLS, always include the system URI, don't over-constrain.**
  - Two hard-won fixes baked in: a **lean** playbook (the long one over-constrained strong models) and an **age-filter guard** (don't add a `patient.birthdate` filter just because a disease *name* contains an age word — the code already encodes it).
- **Visual:** the STEP-0 keyword→playbook cheat-sheet (a few rows) feeding into the T2 loop from Slide 11.
- **Speaker notes:** T1→T2 adds *capability* (tools); T2→T3 adds *strategy* (which playbook + tactics). The playbook is real expert-phenotyper structure condensed to a decision tree — most requests match more than one playbook and combine them. Keep the capability-vs-strategy distinction crisp; it's the spine of the analysis.

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
  | Claude Opus 4.7 | 0.679 | 0.862 | 0.867 |
  | Qwen3.5-9B | 0.257 | 0.476 | 0.710 |
  - All four models are now **full-108 (388 test cases)** on every tier. *(All numbers in this deck are this all-test-case mean — except Slide 14B, the comprehensive-cohort "best case.")*
- **Visual:** grouped bar chart, model × tier (T1/T2/T3).
- **Speaker notes:** The big jump is T1→T2 (every model gains ~0.20). Land that, then unpack *why* next. For Opus on full coverage, **T3 (0.867) ≈ T2 (0.862)** — the methodology is ~neutral for a strong model (the earlier "T3 < T2" was a 48-tc-subset artifact; see Slide 16B for the per-case concept-enumeration failure mode that's real but averages out).

### Slide 14B — Best achievable per model (the ceiling) · ⚠ COMPREHENSIVE COHORT
- **On-slide:** **The one slide on the comprehensive ("all-patients") cohort** — distinct from the all-test-case basis used everywhere else in this deck. Each model's **best possible** score: the single best **tier × prompt** combination, on the comprehensive cell (80 phenotypes that have one):
  | Model | Best config | Best F1 *(comprehensive)* |
  |---|---|---|
  | GPT-5.4 | T2 + expert | **0.998** |
  | Claude Opus 4.7 | T3 + expert | **0.985** |
  | Claude Sonnet 4.6 | T2 + expert | **0.982** |
  | Qwen3.5-9B | T3 + expert | **0.919** |
  - On the cohort that matters most — *did you find the whole population?* — frontier models with the right config **essentially solve it (~0.98–1.00)**. The agentic union query finds nearly everyone.
  - **Even the small open model reaches 0.92** — but only by stacking the full stack (T3 + expert: methodology *and* a code-aware prompt).
  - All four peak with an **expert** prompt; frontier needs only tools (T2), the others lean on methodology (T3).
- **Visual:** bar chart near the top of the scale (0.8–1.0), best-F1 per model, each bar annotated with its winning config (e.g., "T2·expert"). Put a clear "comprehensive cohort" tag on the slide.
- **Speaker notes:** **Call this out explicitly as the comprehensive-cohort slide** — every other slide is the all-test-case average (which includes the harder dx/meds/labs/trick variants and so runs lower, ~0.86–0.92). This slide answers "what's the best each model can do at finding the *whole cohort*," and the answer for frontier is ~1.0 with tools + a precise prompt. The contrast with the all-test-case spine is the point: the comprehensive *union* is near-solved; the per-variant difficulty (Slide 14) is where the real headroom is.

---

## Section 4 — Analysis: why did it help?

### Slide 15 — Why T2 helped: tools collapse the prompt gap (centerpiece)
- **On-slide:** *(all-test-case basis — same as Slides 10/14)*
  - In T1, prompt quality mattered a lot: naive ≈ **0.48–0.53** vs expert ≈ **0.83–0.86** — a **~0.33** gap.
  - In T2, **a naive prompt + tools ≈ an expert prompt + tools**: naive ≈ **0.82–0.85** vs expert ≈ **0.82–0.92** — the gap collapses to **~0.05** (and for Sonnet, naive actually edges out expert).
  - Interpretation: **tools recover what phrasing used to**. The model doesn't need you to know the codes — it can look them up.
- **Visual:** the killer chart — prompt-level on X, F1 on Y, two lines (T1 vs T2). T1 line slopes up steeply (~0.33 rise; prompt matters); T2 line is high and **flat** (~0.05; prompt barely matters).
- **Speaker notes:** This is the most quotable finding: *tools democratize the query* — a clinician can ask in plain English and still get an expert-quality cohort. **Basis note:** these are all-test-case means (consistent with Slides 10/14). If you'd rather use the **comprehensive ("all-patients") cohort** — the headline cell — the same convergence reads naive+T2 ≈ **0.91–0.93** vs expert+T2 ≈ **0.98** (from `2026-06-07-prompt-vs-tools-impact.md`); higher absolute numbers, identical story. Pick ONE basis for the whole deck and say which — don't mix (this slide previously used the comprehensive numbers while 10/14 use all-test-case).

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

### Slide 16B — A methodology failure mode: concept under-enumeration (deep-dive, optional)
- **On-slide:**
  - Because the benchmark is **generous on code systems** (any system finds the multi-coded patients), the *only* way to under-recall is to **enumerate too few clinical concepts** (subtype codes).
  - On **heterogeneous, cross-coded phenotypes**, the T3 playbook makes **Opus do exactly that.** Coronary heart disease, same prompt: **T2 enumerated 32 distinct concepts → recall 1.00; T3 enumerated 7 → recall 0.39.** Opus reads "pick the principled, canonical code" as "pick the *few* canonical concepts" and drops the long tail of subtypes.
  - **Scope it honestly:** averaged over all 388 test cases (most are simple single-concept phenotypes scoring ~1.0 regardless), this **washes out** — full-coverage Opus T2→T3 ≈ **−0.02, within agentic noise.** Opus is simply the one frontier model that doesn't *gain* from T3 (sonnet/gpt ≈ +0.02). It's a **per-phenotype failure mode on hard cases, not a leaderboard regression.**
  - **Theory + plugin fix:** the methodology should say "enumerate *all* subtype concepts, not just the canonical one."
- **Visual:** CHD before/after — T2 (32 concepts, recall 1.00) vs T3 (7 concepts, recall 0.39), with an inset noting it averages out across all phenotypes.
- **Speaker notes:** Treat this as an honest *failure-mode* example, **not** a headline number. The dramatic early read ("Opus T3 < T2 by 0.06") was an artifact of an unrepresentative 48-test-case subset plus n=1 agentic variance; on full coverage it's ~neutral. What's real and reproducible is the *mechanism* on hard cross-coded phenotypes (CHD / Crohn's / SLE): the playbook makes Opus under-enumerate subtype concepts. It's worth a slide because it tells you what to put in the playbook (enumerate the long tail), not because Opus is "worse." If the talk is tight, this is the first cut. Full write-up: `docs/results/2026-06-11-opus-t3-code-narrowing.md`.

### Slide 17 — What moves the needle (the lever summary)
- **On-slide:** for a frontier model, ranked impact (**all-test-case** T1→T2):
  - **Tools: +0.18–0.22** (the dominant lever) — GPT 0.66→0.88, Sonnet 0.62→0.85, Opus 0.68→0.86. *(On the already-high comprehensive cohort the lift is smaller, ~+0.10, because those cells start near 0.9.)*
  - Prompt quality: large at T1 (~+0.33), **~0 once tools are on**
  - Methodology: small for frontier (~+0.005), large for small models (Qwen +0.23)
  - Off-the-shelf generic skill: ~0 (+0.014) for a model that already knows FHIR
- **Visual:** tornado/lever chart ranking the interventions by F1 impact.
- **Speaker notes:** The one-slide takeaway if they remember nothing else: **give the model tools.**

### Slide 17B — What recall actually depends on: concept coverage
- **On-slide:**
  - We deliberately made the benchmark **generous on code systems** (diagnoses multi-coded across SNOMED/ICD-9/ICD-10), so a model is never penalized for *which* system it picks — only for **how many of the cohort's clinical concepts it enumerates.**
  - So the through-line is **concept coverage:** the expert prompt hands the model the concepts; **tools win because they let the model *discover* the concepts present** (sample the server, see which codes exist, crosswalk via UMLS) instead of recalling them; a generic skill stalls when it can't; over-tight methodology can prune the long tail.
  - Net: cohort recall is mostly **"did you enumerate every clinical concept/subtype the population is coded with?"** — and tools are what make that possible from a plain-English prompt.
- **Visual:** the plain-English prompt → (tools discover concepts on the server) → enumerated concept list → patient set. Contrast a 7-concept query vs a 32-concept query for the same phenotype.
- **Speaker notes:** Keep this modest and accurate: the clean "coverage→recall" story holds *within a heterogeneous phenotype* (more of its concepts → higher recall), but concept counts aren't comparable *across* phenotypes (a simple phenotype needs one concept and scores ~1.0). So don't show a single universal curve — show it as "tools let the model discover the concepts the cohort is coded with." This is the honest version of "give the model tools."

---

## Section 5 — Off-the-shelf comparison

### Slide 18 — Best off-the-shelf agent: Opus + the Anthropic FHIR skill
- **On-slide:**
  - We ran **Opus with Anthropic's published FHIR-developer skill** (closed-book — the skill is prepended text, no tools) as a "strong generic" baseline, across **all 108 phenotypes × 3 prompts**.
  - **Headline (all 388 test cases): off-the-shelf Opus+skill 0.69 vs our agentic stack 0.86** (T2; T3 0.87). A strong generic skill, closed-book, lands at the model's plain-recall level; the agentic tools are what add ~0.17.
  - The gap is concentrated in the **hard cross-indication phenotypes** (e.g., Crohn's, asthma) — exactly the Path-C trick cases where you must discover/crosswalk codes.
  - **The skill's *marginal* lift is ~0:** Opus closed-book **plain 0.679 vs +skill 0.693 (+0.014)** over all 108. A generic skill barely helps a model that already knows FHIR — the win is the **tools**, not the prompt/skill text.
  - **By prompt (all-tc, T1) — where the tiny lift lands:**
    | prompt | plain | + skill | Δ |
    |---|---|---|---|
    | naive | 0.533 | 0.552 | +0.019 |
    | broad | 0.644 | 0.666 | +0.022 |
    | expert | 0.859 | 0.862 | +0.003 |

    The skill helps the **naive/broad** prompts (+0.02) but is **noise on expert** (+0.003) — it supplies FHIR guidance an expert prompt already encodes.
- **Visual:** two bars — off-the-shelf Opus+skill (**0.69**) vs our agentic (**0.86**), all-test-case — with a callout on the cross-indication phenotypes driving the gap.
- **Speaker notes:** A generic skill gets you to plain closed-book level (~0.69); the lift to 0.86 is domain-specific tooling + the trick-path handling we built. All-test-case basis, consistent with the rest of the deck. (For reference, on the comprehensive cohort the same comparison is ~0.84 vs ~0.95 — the basis used on Slide 14B; don't mix the two on one chart.) Source: `docs/results/2026-06-12-opus-full-leaderboard.md` + the +fhirskill cells.

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
  - **n=1 agentic runs** — single non-deterministic runs per cell; sub-0.05 tier deltas are within variance (we use the comprehensive recoveries and the code-system *mechanism*, both far above noise). The Opus code-narrowing finding (16B) is framed as a *propensity*, confirmed by rerun, not a per-cell certainty.
  - **Coverage:** all four models are now full-108 on T1 and T3; Opus T2 backfilled to full coverage (was a 48-tc subset).
- **Visual:** simple list, no chart.
- **Speaker notes:** Pre-empt the obvious questions; it builds trust. The synthetic-data point is the big one — lead with it, and note MIMIC (Slide 21) is the answer.

### Slide 21 — What's next
- **On-slide:**
  - **MIMIC-IV-on-FHIR** — rerun the benchmark on **real, de-identified ICU data** (standardizer + per-phenotype counting already built).
  - Repeat runs (n≥3) to quench agentic variance.
  - Broaden the off-the-shelf comparison.
- **Visual:** roadmap arrow: synthetic ✓ → real-data (MIMIC) → repeated runs.
- **Speaker notes:** The natural next question is "does this hold on real data?" — that's the next experiment.

### Slide 22 — Takeaways
- **On-slide:** five lines (the ones worth remembering):
  1. **Closed-book, even the best frontier LLM is mediocre** (~0.68 F1) and very prompt-sensitive (Opus naive 0.53 → expert 0.86). Clinical FHIR phenotyping is **not "solved" by scale alone.**
  2. **Tools are the dominant lever** (+0.18–0.22 all-test-case) and they **erase the prompt gap** — plain English + tools ≈ an expert hand-writing codes. **Tooling > skill > prompt.**
  3. **Recall is really about concept coverage** — did the query enumerate every clinical concept/subtype the cohort is coded with? Tools win because they let the model **discover** those concepts on the server instead of recalling them. (We make the benchmark *generous on code systems* — any system finds the patient — so concepts, not systems, are the axis.)
  4. **Methodology is a model-dependent lever** — huge for a weak model (Qwen T2→T3 **+0.23**), ~0 for the frontier (sonnet/gpt +0.02, Opus ~−0.02). On hard cross-coded phenotypes the playbook can make Opus **under-enumerate subtype concepts** (a real failure mode, though it averages out). **Match the strategy to the model; "more guidance" isn't universally better.**
  5. **We shipped the win as a reusable plugin** (lean playbook + age-guard + server-introspection + UMLS/VSAC) — point it at any FHIR server and a clinician's plain-English ask becomes a research-grade cohort.
- **Visual:** five one-liners with icons (lock / toolbox / code-systems funnel / playbook-with-caution / plugin). Bold lines 2 and 3 as the headline.
- **Speaker notes:** Close on the democratization message: the right tooling lets a clinician ask in plain English and get a research-grade cohort. If they remember two things: **(1) give the model tools, (2) because cohort recall is a code-system-coverage problem.** Lines 1, 4 are the credibility/nuance; line 5 is the deliverable.

---

## Appendix (optional backup slides)
- Full 108-phenotype × model T2 table (from v7 report).
- The FHIR query format + code-system primer (LOINC/SNOMED/ICD/RxNorm, `system|code`).
- Per-phenotype deep-dive on one trick case (e.g., NAS age-filter collapse → fix).
- Infrastructure: per-phenotype isolation, multi-coding augmentation pipeline, 10-server eval fan-out.

---

### Number bases & consistency (read before presenting)

**The deck has a single spine: the all-test-case mean** (F1 averaged over all 388
test cases / all variants). **Source of truth: `docs/results/2026-06-12-opus-full-leaderboard.md`.**
Every slide uses this **except Slide 14B**, the deliberate **comprehensive-cohort**
"best case" exception (the per-phenotype "all-patients" cell only — scores higher
because it's a broad union query, not an average over the harder variants). 14B is
labeled as such on the slide; nothing else mixes the two bases.

**Verified full-108 all-test-case numbers:** Opus 0.679/0.862/0.867,
GPT 0.656/0.878/0.884, Sonnet 0.623/0.846/0.857, Qwen 0.257/0.476/0.710.
Frontier T1→T2 lift +0.18–0.22 (the dominant lever). Skill marginal lift: plain 0.679
→ +fhirskill 0.693 (+0.014).

**Slide 14B (comprehensive cohort, 80 phenotypes with a `-comprehensive` case),
best tier×prompt:** GPT T2·expert 0.998, Opus T3·expert 0.985, Sonnet T2·expert 0.982,
Qwen T3·expert 0.919.

**Frontend** is checked in and clone-ready (`npm install && npm run dev`). Note its
main leaderboard uses the comprehensive **canonical-cell** basis over all 108 (Opus
T2 0.904, T3 0.895) — a *different* comprehensive denominator than Slide 14B's 80-pheno
cut — so the website's comprehensive numbers (~0.90) won't equal the deck's 14B
(~0.94–1.0). The "Best achievable" panel matches 14B (comprehensive best tier×prompt).
