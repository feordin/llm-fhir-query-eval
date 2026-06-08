# Results Reporting Frontend — Rethink

**Date:** 2026-06-07
**Status:** Approved design, pending implementation plan
**Task:** #1 (dev-days deliverable)

## Goal

Rethink the existing React frontend (`frontend/`) into a **static results-reporting
dashboard** whose front page is the **all-up F1 leaderboard** (high-level model
comparison: *does the model find the whole cohort?*), with drill-down from
leaderboard → phenotype → per-test-case 9-cell grid → individual cell detail.
Doubles as the dev-days presentation surface.

## Architecture decision: static precomputed JSON

The sweep is a fixed dataset, so the report is **static** — no live backend needed
to view it. A generator emits JSON artifacts under `frontend/public/data/`; the
frontend `fetch`es them. Deployable as a static site; decoupled from the FHIR
servers/DB. Refresh = regenerate + redeploy.

The existing live-API pages (Evaluate, TestCase live runs) are **kept behind a
secondary nav link** — not removed — for ad-hoc runs against the backend.

### Data generator — `scripts/build_frontend_data.py`

Reuses the trusted cell collection (`aggregate_sweep._collect_latest_cells`,
non-empty-wins) and the canonical-case logic (`build_grid_report.canonical_cases`).
Emits:

| File | Contents |
|---|---|
| `leaderboard.json` | per model × tier: mean all-up F1 (comprehensive/all-patients cell), coverage %, plus per-prompt means |
| `phenotypes.json` | 108 phenotypes × model: comprehensive-cell F1 per tier; canonical test-case id |
| `grids.json` | per (model, test_case): the 9-cell P/R/F1 grid + per-cell detail (see below) |
| `mimic.json` | per-phenotype MIMIC patient counts (dx/lab) from Task #3 |
| `meta.json` | cutoff, generation timestamp (passed in), models, coverage summary |

Per-cell detail captured in `grids.json` (from the result files — all already
present):
`prompt_text`, `primary_query_url` + `additional_query_urls`, `raw_response`,
`elapsed_sec`, `precision`/`recall`/`f1`/`passed`, `expected_count`/`actual_count`,
and for agentic tiers `run_metadata` (`output_tokens`, `tool_calls_count`,
`stop_reason`, `fallback_used`).

**Known gap:** the full step-by-step agentic tool transcript was NOT captured
(only `tool_calls_count`). Surfacing the per-call trace would require a re-run with
transcript capture — out of scope; the cell detail shows the count + token effort.

## Pages

1. **Leaderboard** (front page, `/`) — all-up F1 table (model × tier) + a recharts
   tier-progression chart (line/bar per model). Opus `+fhirskill` (Task #2) appears
   as its own column/series. The headline comparison.
2. **Phenotype matrix** (`/phenotypes`) — evolves the current Dashboard: 108
   phenotypes × models, comprehensive-cell F1, with a T1/T2/T3 toggle, search +
   filters. Row → phenotype detail.
3. **Phenotype detail** (`/phenotypes/:id`) — the per-test-case 9-cell P/R/F1 grids
   (one grid per test case of that phenotype, per model). Cell → cell detail.
4. **Cell detail** (modal or `/cell/...`) — prompt_text, generated query/queries,
   expected vs actual counts, P/R/F1, elapsed time, raw response, and (agentic)
   tool-call count + output tokens.
5. **Per-prompt breakdown** (`/prompts`) — naive vs broad vs expert across models
   (the "human side" axis): how much prompt sophistication matters.
6. **MIMIC real-data** (`/mimic`) — per-phenotype MIMIC counts + the
   synthetic-vs-real story (lab-only over-capture). Gated on Task #3 results (have
   the demo).
7. **Skill baseline** (could live on the Leaderboard) — Opus T1+skill vs Opus T2:
   best off-the-shelf vs our methodology.
8. **Live tooling** (`/live/*`) — existing Evaluate/TestCase pages, secondary nav.

## Components / reuse

- Keep recharts, react-router, react-query (react-query can wrap static fetches).
- A small `data/` client replacing the `/api` axios client for the static JSON
  (the live pages keep the axios client).
- Score-cell coloring + grid components shared between phenotype matrix and detail.

## Out of scope (v1)

- Full agentic tool transcript (not captured).
- Live regeneration from the UI (regen is a CLI step).
- Auth / multi-user.

## Open items for planning

1. Static hosting target (GitHub Pages vs the existing Vite preview vs bundled
   with the backend's static dir).
2. Whether cell detail is a modal or a routed page.
3. Exact `leaderboard.json` shape for the recharts series.
