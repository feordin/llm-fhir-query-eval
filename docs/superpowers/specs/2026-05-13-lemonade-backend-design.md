# Lemonade / AMD GAIA Model Execution Path — Design

**Date:** 2026-05-13
**Status:** Approved for implementation

## Goal

Add a new model execution path that runs FHIR-query evaluation against AMD GAIA's
**Lemonade Server** (OpenAI-compatible HTTP), targeting the
`Phi-4-mini-reasoning-Hybrid` model. Two motivations:

1. **Speed comparison** — see whether Lemonade (NPU/GPU-accelerated, ONNX hybrid)
   runs faster than the current Ollama path.
2. **Coverage** — use the Lemonade model to run the phenotype test cases that were
   skipped in the qwen3.5:9b execution.

The path must support **all 3 evaluation tiers** (Tier 1 closed-book, Tiers 2/3
agentic tool-calling), at parity with the existing Ollama path, so the skipped
phenotypes can run through the same `run_sanity_matrix.py` harness.

## Environment (confirmed)

- Lemonade Server running at **`http://localhost:13305/api/v1`** (OpenAI-compatible).
- `/chat/completions` works, accepts a `tools` param, returns per-response timing
  metrics: `decoding_speed_tps`, `prefill_duration_ttft`, `prompt_tokens`,
  `completion_tokens`, `completion_time_ms`.
- Model id: `Phi-4-mini-reasoning-Hybrid`. It is a **reasoning model** — responses
  carry a separate `reasoning_content` field; the FHIR answer is in `content`.
- Port `13305` is non-standard (likely GAIA-assigned), so the base URL must be
  configurable, not hardcoded.

## Approach

**Chosen: extract a `ChatBackend` seam** (brainstorming Approach B).

The agentic loop in `OllamaAgenticProvider.generate_fhir_query()` is already
backend-agnostic except for three touchpoints:

1. The `ollama.chat(model, messages, tools)` call and its response shape
   (`response["message"]`).
2. The `tool_calls` shape — Ollama returns `arguments` as a dict; OpenAI-compatible
   APIs return it as a JSON string.
3. Tool-result messages — OpenAI-compatible APIs require `tool_call_id` on
   `role: "tool"` messages; Ollama does not.

Extracting that single seam (rather than duplicating the ~200-line loop) avoids
drift and directly delivers the backend-adapter abstraction that
`docs/PLAN-CLOUD-MODEL-EVALUATION.md` already calls for.

Rejected alternatives:
- **Approach A** (two parallel Lemonade provider classes) — duplicates the agentic
  loop; every future prompt/loop fix would have to be applied twice.
- **Approach C** (reuse existing code via shims) — not viable; the `ollama` lib
  cannot speak Lemonade's OpenAI protocol.

## Module layout

```
backend/src/llm/
  chat_backend.py          NEW — ChatBackend interface + OllamaChatBackend + OpenAIChatBackend
  openai_chat_provider.py  NEW — Tier 1 closed-book provider over OpenAI-compatible HTTP
  agentic_provider.py      MOD — loop becomes backend-parametric; OllamaAgenticProvider
                                 becomes a thin subclass; add LemonadeAgenticProvider
  __init__.py              MOD — register "lemonade" + "lemonade-agentic" in get_provider()
```

## The `ChatBackend` seam

A minimal interface — one method — with the agentic loop operating on a
**normalized message format** so it never sees wire-protocol differences.

```python
class ChatBackend(Protocol):
    def chat(self, messages: list[NormMsg], tools: list[dict]) -> NormAssistantMsg: ...
```

Normalized message formats the loop works in:

```
assistant -> {"role": "assistant",
              "content": str,
              "tool_calls": [{"id": str, "name": str, "arguments": dict}]}
tool      -> {"role": "tool", "tool_call_id": str, "content": str}
system / user -> {"role": ..., "content": str}
```

Each backend owns wire translation in both directions: it accepts the normalized
message list, translates to its native format for the request, and translates the
native response back to a normalized assistant message.

### `OllamaChatBackend`

- Wraps the current `ollama.chat(model, messages, tools)` call verbatim.
- Translates Ollama's response message into the normalized shape (`arguments`
  already a dict; synthesize a `tool_call_id` if Ollama omits one).
- The qwen path runs through this and **must behave identically** to today.

### `OpenAIChatBackend`

- POSTs to `{base_url}/chat/completions` via `requests`.
- Translation rules:
  - `arguments` arrives as a JSON string → `json.loads` into a dict.
  - Tool-result messages get their `tool_call_id` carried through to the request.
  - Assistant messages with tool calls are emitted in OpenAI `tool_calls` array
    format.
  - Read `content`; ignore `reasoning_content`.
  - Capture timing fields (`decoding_speed_tps`, `prefill_duration_ttft`,
    `prompt_tokens`, `completion_tokens`) and accumulate across loop iterations.
- Base URL configurable; default `http://localhost:13305/api/v1`.

### Agentic loop changes

`AgenticProvider.generate_fhir_query()` keeps its entire loop, final-answer retry,
fallback logic, and tool dispatch **unchanged**. The only edits:

- `response = ollama.chat(...)` / `msg = response["message"]`
  → `msg = self.backend.chat(messages, tools)`.
- `messages` now holds normalized dicts; tool-result messages include
  `tool_call_id` (sourced from `tool_call["id"]`).
- `OllamaAgenticProvider` becomes `AgenticProvider(backend=OllamaChatBackend(model))`.
- `LemonadeAgenticProvider` is `AgenticProvider(backend=OpenAIChatBackend(model, base_url))`.

## Tier 1 path — `OpenAIChatProvider`

The Ollama Tier-1 path shells out `ollama run <model>` via `CommandProvider`.
Lemonade has no equivalent CLI, so Tier 1 gets a small new provider:

- Single `/chat/completions` call, no tools, reusing `OpenAIChatBackend`.
- Feeds `FHIR_SYSTEM_PROMPT` + context + prompt.
- Parses the response `content` with the existing `parse_fhir_queries_from_text`
  (falls back to `parse_fhir_query_from_text`), exactly as `CommandProvider` does.
- ~40 lines, mirrors `CommandProvider`'s structure and error handling.

## Factory wiring — `get_provider()`

Two new provider names:

| Name                | Provider                | Tiers |
|---------------------|-------------------------|-------|
| `"lemonade"`        | `OpenAIChatProvider`    | 1     |
| `"lemonade-agentic"`| `LemonadeAgenticProvider` | 2/3 |

Base URL resolution order: explicit `kwargs` arg → `LEMONADE_BASE_URL` env var →
default `http://localhost:13305/api/v1`.

## Matrix runner — `run_sanity_matrix.py`

Resolves the existing `# TODO: derive from --provider flag when multi-backend lands`:

- Add `--backend {ollama,lemonade}`, default `ollama` — existing usage unchanged.
- `make_provider()` selects `command` / `ollama-agentic` vs `lemonade` /
  `lemonade-agentic` based on `--backend`.
- `provider_name` passed to `EvaluationRunner.run_single()` becomes the actual
  backend string (not the hardcoded `"ollama"`).
- Output filename already embeds the model; `Phi-4-mini-reasoning-Hybrid` is
  sanitized the same way (`:` and `/` → `-`).

## Speed metrics — `RunMetadata`

- Add optional fields to `RunMetadata`: `tokens_per_sec`, `prompt_tokens`,
  `completion_tokens`, `ttft_sec`. Optional so the Ollama path leaves them null.
- `OpenAIChatBackend` accumulates Lemonade's per-response timing across loop
  iterations and exposes it; the agentic provider folds it into
  `_build_run_metadata()`.
- Every sanity-matrix cell then records speed. Comparison = reading result JSONs.
  `elapsed_sec` is already captured for both backends.

## Verification (required before any "done" claim)

1. `pytest` — existing suite still green.
2. **Qwen unchanged:** re-run one existing qwen3.5 sanity-matrix cell
   (e.g. `phekb-asthma-dx`, tier 2) and confirm it still produces a valid query
   through the new `OllamaChatBackend` seam.
3. **Lemonade smoke:** one full 3×3 sanity matrix on `Phi-4-mini-reasoning-Hybrid`
   against a known phenotype — confirm all 3 tiers execute and the result JSON
   carries the new speed fields.
4. **Tool-calling spot-check:** confirm Tier 2 actually emits `tool_calls` with
   this reasoning model. Its tool-call reliability is unverified; if it won't emit
   tool calls, that is a finding to report, not a bug to hide.

## Out of scope / follow-up

Actually running the skipped phenotypes is a separate task after this lands. The
`test-cases/phekb/` vs `results/` diff is messy — old abbreviated names
(`phekb-aaa-*`) vs current (`phekb-abdominal-aortic-aneurysm-*`), plus
non-phenotype entries (`phekb-hba1c`, `phekb-blood-pressure`). The first step of
that follow-up is producing a clean "no qwen3.5 result" list; it is not guessed
here.
