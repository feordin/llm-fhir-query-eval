# LLM FHIR Query Evaluation

**A 108-phenotype benchmark measuring how accurately LLMs translate plain-English
patient-cohort descriptions into FHIR queries — and what actually makes them better.**

Given a code-free, plain-English description of a patient population (e.g. *"find
patients with type 2 diabetes"*), can a model produce a FHIR query that returns
*exactly that cohort*? We score the returned **patient sets** (not the query strings)
against expert-curated gold queries, across 4 models, 3 prompt styles, and 3 levels
of tooling.

## Headline result (all-test-case mean F1, full 108 phenotypes)

| Model | T1 closed-book | T2 agentic + tools | T3 + methodology |
|---|---|---|---|
| GPT-5.4 | 0.656 | 0.878 | 0.884 |
| Claude Opus 4.7 | 0.679 | 0.862 | 0.867 |
| Claude Sonnet 4.6 | 0.623 | 0.846 | 0.857 |
| Qwen3.5-9B | 0.257 | 0.476 | 0.710 |

**Tools are the dominant lever (+0.18–0.22)** and they *erase the prompt-skill gap*:
closed-book, prompt quality matters enormously; with tools, a plain-English prompt ≈
an expert one. Off-the-shelf prompt "skills" add ~0 for a model that already knows
FHIR. See `docs/presentation/devdays-outline.md` and `docs/results/` for the full story.

## The three axes

- **3 prompt levels** (the human side): **naive** (untrained user) · **broad**
  (clinically aware, no codes) · **expert** (precise, code-aware).
- **3 tiers** (the model side): **T1** closed-book (single completion, no tools) ·
  **T2** agentic loop with 10 FHIR + UMLS/VSAC tools (introspect the server, look up
  codes) · **T3** T2 plus a prepended phenotyping-methodology playbook.
- **Realistic data**: custom Synthea modules per phenotype with a 3-path cohort
  design (dx / meds-only / labs-only — the trick paths) plus mimicker controls, so
  precision is real and trivial code-matching fails.

## See the results

**Interactive leaderboard** (the data snapshot is checked in — no extra setup):
```bash
cd frontend && npm install && npm run dev   # open the printed localhost URL
```
It shows the per-model × tier leaderboard, the prompt × tier heatmaps, each model's
best-achievable score, the off-the-shelf-skill comparison, and per-phenotype drill-downs.

**Key writeups** (`docs/results/`):
- `2026-06-12-opus-full-leaderboard.md` — the full-108 source-of-truth numbers
- `2026-06-07-prompt-vs-tools-impact.md` — "what moves the needle" (tools vs prompt)
- `2026-06-07-opus-skill-baseline.md` — off-the-shelf Anthropic FHIR skill vs our stack
- `2026-06-11-opus-t3-code-narrowing.md` — a methodology failure mode (concept enumeration)
- `2026-06-12-mimic-demo-sweep.md` — first real-data run on MIMIC-IV-on-FHIR

## Architecture

```
Web UI (React/TS)  ──REST──►  Backend API (FastAPI)  ──►  { Test cases (JSON),
                                  eval engines              LLM providers,
                                  (execution/semantic)      FHIR server (fhir-candle / MS FHIR) }
```

- `backend/src/evaluation/` — execution-based + semantic evaluators
- `backend/src/llm/` — provider abstractions; `agentic_provider.py` (the T2/T3 loop + 10 tools),
  `tier3_methodology_lean.md` (the playbook)
- `test-cases/phekb/` — the benchmark (JSON, one file per phenotype × variant)
- `scripts/` — the eval harness, Synthea data pipeline, sweep runners, and the
  MIMIC-IV `$import` automation
- `frontend/` — the static results site

## Quick start

```bash
# 1. Config
cp .env.example .env          # add ANTHROPIC_API_KEY, UMLS_API_KEY (for T2/T3), etc.

# 2. Backend
cd backend && poetry install
poetry run pytest             # tests
poetry run uvicorn src.api.main:app --reload --port 8000

# 3. Frontend (results site)
cd frontend && npm install && npm run dev

# 4. FHIR server (test-data target)
docker-compose up -d fhir-candle   # R4 at http://localhost:5826/r4
```

Generating test data and running sweeps is driven by the `scripts/` harness and the
custom Claude Code skills (`/synthea`, `/phenotype_workflow`, `/umls`) — see
`CLAUDE.md` for the project conventions and skill reference.

## FHIR query format

```
GET /[ResourceType]?[param]=[system]|[code]
# e.g.  Condition?code=http://hl7.org/fhir/sid/icd-10-cm|E11.9
```
Code systems: LOINC `http://loinc.org` · SNOMED CT `http://snomed.info/sct` ·
ICD-10-CM `http://hl7.org/fhir/sid/icd-10-cm` · RxNorm
`http://www.nlm.nih.gov/research/umls/rxnorm`.

## Acknowledgments

Phenotype algorithms from **[PheKB](https://phekb.org)**. Synthetic data via
**[Synthea](https://github.com/synthetichealth/synthea)**. Terminology via the
**NIH UMLS / VSAC** APIs. Real-data evaluation uses **MIMIC-IV-on-FHIR** (PhysioNet,
credentialed).
