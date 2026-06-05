# Anthropic FHIR Skill — Off-the-Shelf Closed-Book Baseline

**Date:** 2026-06-05
**Status:** Approved design, pending implementation
**Task:** #2 (dev-days goals)

## Goal

Measure how well a strong **off-the-shelf** model (Opus 4.7), running **closed-book**
(no MCP server, no agentic loop — i.e. nothing from Tier 2 or Tier 3), augmented
only with Anthropic's official **`fhir-developer` skill**, can generate FHIR cohort
queries — and compare that against **our full in-house stack** (Opus 4.7 at Tier 3:
agentic loop + 10 tools + phenotype methodology playbook).

This answers: *does our hand-built phenotype methodology actually beat the best
generic FHIR artifact Anthropic ships?*

## Key finding about the skill (report this)

The vendored skill (`vendor/anthropic-fhir-skill/`, from `anthropics/healthcare`
repo, path `fhir-developer-skill/`) is a **FHIR-server-development** skill: HTTP
status codes, `OperationOutcome` errors, required-vs-optional field validation,
SMART-on-FHIR auth, Bundle transactions, Pydantic models. Only a slice bears on our
cohort-query task: coding-system URLs (LOINC/SNOMED/RxNorm/ICD-10), the
`GET /[ResourceType]?param=value` search format, value-set enums, and a few LOINC
vital codes. A null-or-small result is therefore an expected and *informative*
outcome — it argues for our custom skill (Thread B).

## The two columns being compared

| Spec label | Tier | Tools | System prompt | Measures |
|---|---|---|---|---|
| `copilot:claude-opus-4.7+fhirskill` | T1 closed-book | none | `FHIR_SYSTEM_PROMPT` + injected skill text | Best off-the-shelf, no agent |
| `copilot:claude-opus-4.7` | T3 | full 10-tool loop | `FHIR_SYSTEM_PROMPT` + `tier3_methodology.md` | Our full in-house stack |

### Injected skill text

Concatenation of, in order:
1. `vendor/anthropic-fhir-skill/SKILL.md` (~9.9 KB)
2. `vendor/anthropic-fhir-skill/references/resource-examples.md` (~5.4 KB)

The other three references (`smart-auth.md`, `bundles.md`, `pagination.md`) are
server-dev-only and are **excluded** as irrelevant noise. Reference files are
normally loaded on-demand by an agent loop; since this run has no loop, inlining
the one query-relevant reference is the faithful "skill alone" representation.

## Implementation (Approach 1 — new spec modifier)

Minimal change (~30 lines across 3 files), reusing all existing scoring/aggregation.

1. **`scripts/run_sanity_matrix.py`**
   - Add `--skill-file <path>` arg (repeatable or comma-separated; here two files).
   - Thread it into `make_provider(...)`. For `provider == "copilot"` and `tier == 1`,
     read + concatenate the skill files and pass the text as a new
     `system_prefix=` kwarg to `get_provider("copilot", ...)`.
   - Only T1 closed-book consumes the skill; T2/T3 ignore it (they have their own
     agentic prompt). This keeps the Opus-4.7 T3 column unmodified.

2. **`backend/src/llm/copilot_provider.py`** — closed-book `CopilotProvider`
   - Add `system_prefix: str = ""` to `__init__`.
   - In `generate_fhir_query`, build
     `system_message = _system_replace((system_prefix + "\n\n---\n\n" + FHIR_SYSTEM_PROMPT) if system_prefix else FHIR_SYSTEM_PROMPT)`.
   - No behavior change when `system_prefix` is empty (all existing runs unaffected).

3. **`backend/src/llm/__init__.py` factory** — pass `system_prefix` through to the
   `CopilotProvider` constructor for the `"copilot"` provider key.

4. **Spec label suffix** — when a skill file is injected, the result file's spec
   label is suffixed `+fhirskill` so `scripts/aggregate_sweep.py`'s per-spec dedup
   treats it as a distinct column from plain `copilot:claude-opus-4.7`.
   - Implementation: `run_isolated_suite.py` / `run_sanity_matrix.py` already derive
     a `_safe_name`; append `+fhirskill` to the model component for the output
     filename and the in-file `spec`/`model_version` label when `--skill-file` is set.

5. **Driver** — a small launcher (or reuse `run_isolated_suite.py` twice):
   - Run **A**: subset phenotypes, `--providers copilot:claude-opus-4.7`,
     `--tiers 1`, `--skill-file vendor/anthropic-fhir-skill/SKILL.md,vendor/anthropic-fhir-skill/references/resource-examples.md`.
   - Run **B**: same subset, `--providers copilot:claude-opus-4.7`, `--tiers 3`
     (no skill flag).
   - Aggregate both into one comparison table.

## Scope — representative subset

~8 phenotypes / ~25 test cases spanning the failure modes:

| Phenotype | Why included |
|---|---|
| `type-2-diabetes` | Canonical easy dx |
| `gerd` | 58% Path C (largest cross-indication) |
| `systemic-lupus-erythematosus` | Max cross-indication contamination |
| `osteoporosis` | DEXA labs + negative-value-quantity threshold |
| `coronary-heart-disease` | Procedure + comprehensive 4-resource union |
| `crohns-disease` (+ `biologic-without-dx`) | Negation / trick variant |
| `asthma` | Qwen's weakest phenotype in prior sweeps |
| `heart-failure` | Mixed dx/meds/labs |

If the subset shows a meaningful signal, expand to all 108 (still T1-only generation
for the skill column; FHIR servers needed only for scoring).

## Scoring & aggregation

No new scoring code. The skill column produces ordinary `run_sanity_matrix` result
files; `aggregate_sweep.py` (cell-level non-empty-wins dedup) folds the `+fhirskill`
column in alongside the existing T1/T2/T3 columns. Output: a P/R/F1 comparison of
Opus-4.7-skill-closed-book vs Opus-4.7-T3 across the subset, plus per-phenotype
deltas for the deck.

## Out of scope

- No MCP server, no tools, no agent loop in the skill column (by design).
- No changes to the existing sonnet/gpt-5.4/qwen sweep columns.
- The `setup_fhir_project.py` script and server-dev references are not used.

## Cost / risk

- Closed-book T1 is cheap (single completion per cell). T3 Opus on ~25 test cases ×
  3 prompt variants is the larger cost; bounded by the 20-iteration agent cap.
- Risk: Opus-4.7 T3 was not in the prior sweep, so this introduces a new model at
  T3 — acceptable, it is the intended comparator.
