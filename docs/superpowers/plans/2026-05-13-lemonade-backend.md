# Lemonade / AMD GAIA Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a model execution path that runs all 3 evaluation tiers against AMD GAIA's Lemonade Server (OpenAI-compatible HTTP), targeting `Phi-4-mini-reasoning-Hybrid`.

**Architecture:** Extract a one-method `ChatBackend` seam from the Ollama-specific agentic loop. Two implementations — `OllamaChatBackend` (wraps the existing `ollama.chat` call, qwen path unchanged) and `OpenAIChatBackend` (OpenAI-compatible HTTP, serves Lemonade). The agentic loop becomes backend-parametric; a small `OpenAIChatProvider` covers Tier 1 closed-book.

**Tech Stack:** Python 3, `requests`, `ollama` Python lib, `pytest`, Pydantic. Spec: `docs/superpowers/specs/2026-05-13-lemonade-backend-design.md`.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `backend/src/llm/chat_backend.py` | NEW — `ChatBackend` ABC, normalized message format, `OllamaChatBackend`, `OpenAIChatBackend` |
| `backend/src/llm/openai_chat_provider.py` | NEW — Tier 1 closed-book provider over an OpenAI-compatible endpoint |
| `backend/src/llm/agentic_provider.py` | MOD — loop becomes backend-parametric; `OllamaAgenticProvider` thin subclass; add `LemonadeAgenticProvider` |
| `backend/src/llm/__init__.py` | MOD — register `"lemonade"` + `"lemonade-agentic"` in `get_provider()` |
| `backend/src/api/models/evaluation.py` | MOD — add `tokens_per_sec` + `ttft_sec` to `RunMetadata` |
| `scripts/run_sanity_matrix.py` | MOD — add `--backend {ollama,lemonade}` flag |
| `backend/tests/test_llm/test_chat_backend.py` | NEW — tests for both backends |
| `backend/tests/test_llm/test_openai_chat_provider.py` | NEW — tests for Tier 1 provider |

### Normalized message format (used everywhere the loop touches messages)

```
system / user  -> {"role": "system"|"user", "content": str}
assistant      -> {"role": "assistant", "content": str,
                   "tool_calls": [{"id": str, "function": {"name": str, "arguments": dict}}]}
tool result    -> {"role": "tool", "tool_call_id": str, "content": str}
```

`tool_calls` is omitted or `[]` when the model made no calls. The assistant
`tool_calls` shape deliberately matches what the existing loop already reads
(`tool_call["function"]["name"]`, `tool_call["function"]["arguments"]`), so the
loop body barely changes — only the call site and the tool-result append.

---

## Task 1: `OllamaChatBackend` + the `ChatBackend` seam

**Files:**
- Create: `backend/src/llm/chat_backend.py`
- Test: `backend/tests/test_llm/test_chat_backend.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_llm/test_chat_backend.py
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.llm.chat_backend import OllamaChatBackend


def _fake_ollama_response(content="", tool_calls=None):
    msg = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "message": msg,
        "prompt_eval_count": 11,
        "eval_count": 7,
        "total_duration": 2_000_000_000,  # 2s in ns
    }


def test_ollama_backend_normalizes_plain_message():
    backend = OllamaChatBackend(model="qwen3.5:9b")
    with patch("src.llm.chat_backend.ollama.chat",
               return_value=_fake_ollama_response(content="Condition?code=x")):
        msg = backend.chat([{"role": "user", "content": "hi"}], tools=[])
    assert msg["role"] == "assistant"
    assert msg["content"] == "Condition?code=x"
    assert msg.get("tool_calls", []) == []


def test_ollama_backend_synthesizes_tool_call_ids():
    raw_calls = [{"function": {"name": "fhir_search", "arguments": {"query": "Patient"}}}]
    backend = OllamaChatBackend(model="qwen3.5:9b")
    with patch("src.llm.chat_backend.ollama.chat",
               return_value=_fake_ollama_response(tool_calls=raw_calls)):
        msg = backend.chat([{"role": "user", "content": "hi"}], tools=[])
    assert len(msg["tool_calls"]) == 1
    tc = msg["tool_calls"][0]
    assert tc["id"]  # synthesized, non-empty
    assert tc["function"]["name"] == "fhir_search"
    assert tc["function"]["arguments"] == {"query": "Patient"}


def test_ollama_backend_run_metrics():
    backend = OllamaChatBackend(model="qwen3.5:9b")
    with patch("src.llm.chat_backend.ollama.chat",
               return_value=_fake_ollama_response(content="x")):
        backend.chat([{"role": "user", "content": "hi"}], tools=[])
    m = backend.get_run_metrics()
    assert m["provider_backend"] == "ollama"
    assert m["input_tokens"] == 11
    assert m["output_tokens"] == 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_llm/test_chat_backend.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.llm.chat_backend'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/llm/chat_backend.py
"""Chat backend seam: isolates the agentic loop from a specific LLM transport.

The agentic loop in agentic_provider.py works in a normalized message format
and never sees wire-protocol differences. Each backend translates that format
to/from its native API.

Normalized formats:
  system / user -> {"role": ..., "content": str}
  assistant     -> {"role": "assistant", "content": str,
                    "tool_calls": [{"id": str, "function": {"name": str, "arguments": dict}}]}
  tool result   -> {"role": "tool", "tool_call_id": str, "content": str}
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import ollama
import requests

logger = logging.getLogger(__name__)

NormMsg = Dict[str, Any]


class ChatBackend(ABC):
    """One chat turn against an LLM, in the normalized message format."""

    @abstractmethod
    def chat(self, messages: List[NormMsg], tools: List[dict]) -> NormMsg:
        """Send messages + tool schemas, return a normalized assistant message."""

    @abstractmethod
    def get_run_metrics(self) -> Dict[str, Any]:
        """Return accumulated metrics for the run so far.

        Keys: provider_backend, input_tokens, output_tokens,
        tokens_per_sec (float|None), ttft_sec (float|None).
        """


class OllamaChatBackend(ChatBackend):
    """Wraps ollama.chat() — the existing qwen path, behavior unchanged."""

    def __init__(self, model: str):
        self.model = model
        self._input_tokens = 0
        self._output_tokens = 0

    def chat(self, messages: List[NormMsg], tools: List[dict]) -> NormMsg:
        response = ollama.chat(model=self.model, messages=messages, tools=tools)
        raw = response["message"]
        self._input_tokens += response.get("prompt_eval_count", 0) or 0
        self._output_tokens += response.get("eval_count", 0) or 0

        norm: NormMsg = {"role": "assistant", "content": raw.get("content", "") or ""}
        raw_calls = raw.get("tool_calls") or []
        if raw_calls:
            calls = []
            for i, tc in enumerate(raw_calls):
                fn = tc["function"]
                calls.append({
                    "id": tc.get("id") or f"call_{i}",
                    "function": {"name": fn["name"], "arguments": fn.get("arguments", {}) or {}},
                })
            norm["tool_calls"] = calls
        return norm

    def get_run_metrics(self) -> Dict[str, Any]:
        return {
            "provider_backend": "ollama",
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "tokens_per_sec": None,
            "ttft_sec": None,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_llm/test_chat_backend.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/llm/chat_backend.py backend/tests/test_llm/test_chat_backend.py
git commit -m "feat: add ChatBackend seam with OllamaChatBackend"
```

---

## Task 2: `OpenAIChatBackend`

**Files:**
- Modify: `backend/src/llm/chat_backend.py` (append `OpenAIChatBackend`)
- Test: `backend/tests/test_llm/test_chat_backend.py` (append tests)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_llm/test_chat_backend.py`:

```python
from src.llm.chat_backend import OpenAIChatBackend


def _fake_openai_response(content="", tool_calls=None):
    msg = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "choices": [{"message": msg, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 9},
        "decoding_speed_tps": 30.0,
        "prefill_duration_ttft": 0.47,
    }


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_openai_backend_normalizes_plain_message():
    backend = OpenAIChatBackend(model="Phi-4-mini-reasoning-Hybrid",
                                base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_FakeResp(_fake_openai_response(content="Patient?_id=1"))):
        msg = backend.chat([{"role": "user", "content": "hi"}], tools=[])
    assert msg["role"] == "assistant"
    assert msg["content"] == "Patient?_id=1"
    assert msg.get("tool_calls", []) == []


def test_openai_backend_parses_json_string_arguments():
    raw_calls = [{
        "id": "call_abc",
        "type": "function",
        "function": {"name": "fhir_search", "arguments": '{"query": "Patient"}'},
    }]
    backend = OpenAIChatBackend(model="Phi-4-mini-reasoning-Hybrid",
                                base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_FakeResp(_fake_openai_response(tool_calls=raw_calls))):
        msg = backend.chat([{"role": "user", "content": "hi"}], tools=[])
    tc = msg["tool_calls"][0]
    assert tc["id"] == "call_abc"
    assert tc["function"]["name"] == "fhir_search"
    assert tc["function"]["arguments"] == {"query": "Patient"}  # parsed from JSON string


def test_openai_backend_translates_tool_result_and_assistant_messages():
    """Outbound translation: tool messages keep tool_call_id, assistant tool_calls
    are emitted with arguments serialized back to a JSON string."""
    captured = {}

    def _capture(url, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResp(_fake_openai_response(content="done"))

    backend = OpenAIChatBackend(model="Phi-4-mini-reasoning-Hybrid",
                                base_url="http://localhost:13305/api/v1")
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "call_1", "function": {"name": "fhir_search",
                                                      "arguments": {"query": "Patient"}}}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "{\"total\": 3}"},
    ]
    with patch("src.llm.chat_backend.requests.post", side_effect=_capture):
        backend.chat(messages, tools=[])

    sent = captured["payload"]["messages"]
    assert sent[2]["role"] == "tool"
    assert sent[2]["tool_call_id"] == "call_1"
    assistant_tc = sent[1]["tool_calls"][0]
    assert assistant_tc["type"] == "function"
    assert assistant_tc["function"]["arguments"] == '{"query": "Patient"}'  # serialized


def test_openai_backend_run_metrics():
    backend = OpenAIChatBackend(model="Phi-4-mini-reasoning-Hybrid",
                                base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_FakeResp(_fake_openai_response(content="x"))):
        backend.chat([{"role": "user", "content": "hi"}], tools=[])
    m = backend.get_run_metrics()
    assert m["provider_backend"] == "lemonade"
    assert m["input_tokens"] == 20
    assert m["output_tokens"] == 9
    assert m["tokens_per_sec"] == 30.0
    assert m["ttft_sec"] == 0.47
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_llm/test_chat_backend.py -v`
Expected: FAIL — `ImportError: cannot import name 'OpenAIChatBackend'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/src/llm/chat_backend.py`:

```python
class OpenAIChatBackend(ChatBackend):
    """OpenAI-compatible HTTP backend. Serves AMD GAIA's Lemonade Server.

    provider_backend is reported as "lemonade" since that is the only
    OpenAI-compatible target wired in today.
    """

    def __init__(self, model: str, base_url: str, request_timeout: int = 300):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self._input_tokens = 0
        self._output_tokens = 0
        self._tokens_per_sec = None
        self._ttft_sec = None

    def chat(self, messages: List[NormMsg], tools: List[dict]) -> NormMsg:
        wire_messages = [self._to_wire(m) for m in messages]
        payload: Dict[str, Any] = {"model": self.model, "messages": wire_messages}
        if tools:
            payload["tools"] = tools
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        usage = data.get("usage", {}) or {}
        self._input_tokens += usage.get("prompt_tokens", 0) or 0
        self._output_tokens += usage.get("completion_tokens", 0) or 0
        if data.get("decoding_speed_tps") is not None:
            self._tokens_per_sec = data["decoding_speed_tps"]
        if data.get("prefill_duration_ttft") is not None:
            self._ttft_sec = data["prefill_duration_ttft"]

        raw = data["choices"][0]["message"]
        # Reasoning models emit reasoning_content separately; we only want content.
        norm: NormMsg = {"role": "assistant", "content": raw.get("content", "") or ""}
        raw_calls = raw.get("tool_calls") or []
        if raw_calls:
            calls = []
            for tc in raw_calls:
                fn = tc["function"]
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args) if args.strip() else {}
                    except json.JSONDecodeError:
                        logger.warning("Tool-call arguments not valid JSON: %.200s", args)
                        args = {}
                calls.append({
                    "id": tc.get("id") or "call_0",
                    "function": {"name": fn["name"], "arguments": args},
                })
            norm["tool_calls"] = calls
        return norm

    @staticmethod
    def _to_wire(m: NormMsg) -> Dict[str, Any]:
        """Translate one normalized message to OpenAI wire format."""
        role = m["role"]
        if role == "tool":
            return {"role": "tool", "tool_call_id": m["tool_call_id"],
                    "content": m.get("content", "")}
        if role == "assistant" and m.get("tool_calls"):
            return {
                "role": "assistant",
                "content": m.get("content", "") or "",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": json.dumps(tc["function"]["arguments"]),
                        },
                    }
                    for tc in m["tool_calls"]
                ],
            }
        return {"role": role, "content": m.get("content", "") or ""}

    def get_run_metrics(self) -> Dict[str, Any]:
        return {
            "provider_backend": "lemonade",
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "tokens_per_sec": self._tokens_per_sec,
            "ttft_sec": self._ttft_sec,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_llm/test_chat_backend.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/llm/chat_backend.py backend/tests/test_llm/test_chat_backend.py
git commit -m "feat: add OpenAIChatBackend for Lemonade/OpenAI-compatible servers"
```

---

## Task 3: Add speed fields to `RunMetadata`

**Files:**
- Modify: `backend/src/api/models/evaluation.py:44-51`
- Test: `backend/tests/test_llm/test_chat_backend.py` (append one test)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_llm/test_chat_backend.py`:

```python
def test_run_metadata_accepts_speed_fields():
    from src.api.models.evaluation import RunMetadata
    m = RunMetadata(provider_backend="lemonade", tokens_per_sec=29.6, ttft_sec=0.47)
    assert m.tokens_per_sec == 29.6
    assert m.ttft_sec == 0.47
    # Backward compatible: omitting them leaves them None
    assert RunMetadata().tokens_per_sec is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_llm/test_chat_backend.py::test_run_metadata_accepts_speed_fields -v`
Expected: FAIL — Pydantic rejects unknown field `tokens_per_sec` (or `AttributeError`)

- [ ] **Step 3: Write minimal implementation**

In `backend/src/api/models/evaluation.py`, inside `class RunMetadata`, add two fields immediately after the `host` field (line 50):

```python
    host: Optional[str] = None                   # machine hostname
    benchmark_track: Optional[str] = None        # "standardized", "optimized", "copilot"
    tokens_per_sec: Optional[float] = None       # decode throughput (OpenAI-compatible backends)
    ttft_sec: Optional[float] = None             # time to first token (OpenAI-compatible backends)
```

(The `benchmark_track` line already exists — keep it; only the two new lines are added.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_llm/test_chat_backend.py::test_run_metadata_accepts_speed_fields -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/models/evaluation.py backend/tests/test_llm/test_chat_backend.py
git commit -m "feat: add tokens_per_sec and ttft_sec to RunMetadata"
```

---

## Task 4: Make the agentic loop backend-parametric

This refactors `agentic_provider.py` so the loop drives a `ChatBackend` instead of calling `ollama.chat` directly. `OllamaAgenticProvider` keeps its public name and constructor signature (so `get_provider("ollama-agentic", ...)` is unaffected) but delegates to a backend internally. A new `LemonadeAgenticProvider` is added.

**Files:**
- Modify: `backend/src/llm/agentic_provider.py` (lines ~19, ~426-438, ~447, ~463-478, ~508-520, ~554-574)

- [ ] **Step 1: Replace the direct ollama import with the backend import**

In `backend/src/llm/agentic_provider.py`, change line 19 from:

```python
import ollama
```

to:

```python
from .chat_backend import ChatBackend, OllamaChatBackend, OpenAIChatBackend
```

- [ ] **Step 2: Rename the class and make `__init__` take a backend**

Find the class declaration `class OllamaAgenticProvider` (around line 380-426) and rename it to `class AgenticProvider`. Replace its `__init__` (lines ~426-445) with:

```python
    def __init__(
        self,
        backend: ChatBackend,
        model: str,
        fhir_base_url: str = "http://localhost:8080/fhir",
        max_iterations: int = 20,
        request_timeout: int = 30,
        tier: int = 2,
    ):
        self.backend = backend
        self.model = model
        self.fhir_base_url = fhir_base_url.rstrip("/")
        self.max_iterations = max_iterations
        self.request_timeout = request_timeout
        self.tier = tier
        self.verify_ssl = not self.fhir_base_url.lower().startswith("https://")
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.tool_trace: List[Dict[str, Any]] = []
        self.last_run_metadata: Optional[RunMetadata] = None
        self._system_prompt = self._build_system_prompt()
```

- [ ] **Step 3: Wire backend metrics into `_build_run_metadata`**

Replace the body of `_build_run_metadata` (lines ~463-478) with:

```python
    def _build_run_metadata(self, iterations_used: int, stop_reason: str, elapsed_sec: float) -> RunMetadata:
        """Build audit metadata for the just-completed agentic run."""
        m = self.backend.get_run_metrics()
        return RunMetadata(
            provider_backend=m["provider_backend"],
            model_version=self.model,
            tool_transport="http",
            tier=self.tier,
            system_prompt_version=AGENTIC_SYSTEM_PROMPT_VERSION,
            tool_schema_version=TOOL_SCHEMA_VERSION,
            iterations_used=iterations_used,
            max_iterations=self.max_iterations,
            elapsed_sec=round(elapsed_sec, 2),
            stop_reason=stop_reason,
            fallback_used=stop_reason.startswith("fallback"),
            tool_calls_count=len(self.tool_trace),
            input_tokens=m["input_tokens"] or None,
            output_tokens=m["output_tokens"] or None,
            tokens_per_sec=m["tokens_per_sec"],
            ttft_sec=m["ttft_sec"],
        )
```

- [ ] **Step 4: Replace the `ollama.chat` call site**

In `generate_fhir_query`, replace the try/except block that calls `ollama.chat` (lines ~508-520) — from `try:` through `messages.append(msg)` — with:

```python
            try:
                msg = self.backend.chat(messages, tools)
            except Exception as e:
                raise RuntimeError(
                    f"Chat backend failed (model={self.model}): {e}"
                ) from e

            messages.append(msg)
```

- [ ] **Step 5: Add `tool_call_id` to tool-result messages**

In the tool-execution loop (lines ~554-574), find the `messages.append` for the tool result and replace it with:

```python
                result_str = json.dumps(result) if not isinstance(result, str) else result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result_str,
                })
```

(The `tool_call` dict now always carries an `id` — both backends guarantee it.)

- [ ] **Step 6: Add thin subclasses at the end of the file**

At the end of `backend/src/llm/agentic_provider.py`, add:

```python
class OllamaAgenticProvider(AgenticProvider):
    """Agentic provider backed by a local Ollama server (unchanged qwen path)."""

    def __init__(self, model: str = "qwen3.5:9b", **kwargs):
        super().__init__(backend=OllamaChatBackend(model), model=model, **kwargs)


class LemonadeAgenticProvider(AgenticProvider):
    """Agentic provider backed by an OpenAI-compatible server (AMD GAIA Lemonade)."""

    def __init__(self, model: str, base_url: str = "http://localhost:13305/api/v1",
                 request_timeout: int = 300, **kwargs):
        backend = OpenAIChatBackend(model, base_url=base_url, request_timeout=request_timeout)
        super().__init__(backend=backend, model=model, **kwargs)
```

- [ ] **Step 7: Run the existing test suite to confirm nothing broke**

Run: `cd backend && poetry run pytest tests/test_llm/ -v`
Expected: PASS — all tests from Tasks 1-3 still green, no import errors.

- [ ] **Step 8: Commit**

```bash
git add backend/src/llm/agentic_provider.py
git commit -m "refactor: make agentic loop backend-parametric via ChatBackend"
```

---

## Task 5: `OpenAIChatProvider` — Tier 1 closed-book

**Files:**
- Create: `backend/src/llm/openai_chat_provider.py`
- Test: `backend/tests/test_llm/test_openai_chat_provider.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_llm/test_openai_chat_provider.py
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.llm.openai_chat_provider import OpenAIChatProvider


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _resp(content):
    return _FakeResp({
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 4},
    })


def test_tier1_provider_parses_query_from_content():
    provider = OpenAIChatProvider(model="Phi-4-mini-reasoning-Hybrid",
                                  base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_resp("Condition?code=http://snomed.info/sct|44054006")):
        result = provider.generate_fhir_query("Find diabetics")
    assert result.parsed_query.resource_type == "Condition"
    assert "44054006" in result.raw_response


def test_tier1_provider_raises_on_unparseable_content():
    provider = OpenAIChatProvider(model="Phi-4-mini-reasoning-Hybrid",
                                  base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_resp("I cannot help with that.")):
        try:
            provider.generate_fhir_query("Find diabetics")
            assert False, "expected a parse error"
        except (ValueError, RuntimeError):
            pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_llm/test_openai_chat_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.llm.openai_chat_provider'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/llm/openai_chat_provider.py
"""Tier 1 (closed-book) provider over an OpenAI-compatible HTTP server.

The Ollama Tier-1 path shells out `ollama run <model>` (CommandProvider).
Lemonade has no equivalent CLI, so its closed-book path is a single
/chat/completions call with no tools, reusing OpenAIChatBackend.
"""
import sys
from pathlib import Path

from .provider import (
    LLMProvider, FHIR_SYSTEM_PROMPT,
    parse_fhir_query_from_text, parse_fhir_queries_from_text,
)
from .chat_backend import OpenAIChatBackend

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery


class OpenAIChatProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:13305/api/v1",
                 request_timeout: int = 300):
        self.model = model
        self.backend = OpenAIChatBackend(model, base_url=base_url,
                                         request_timeout=request_timeout)

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        user_content = prompt if not context else f"{context}\n\n{prompt}"
        messages = [
            {"role": "system", "content": FHIR_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        msg = self.backend.chat(messages, tools=[])
        raw_text = (msg.get("content") or "").strip()
        if not raw_text:
            raise RuntimeError("Model returned empty content")

        all_parsed = parse_fhir_queries_from_text(raw_text)
        if all_parsed:
            parsed, additional = all_parsed[0], all_parsed[1:]
        else:
            parsed, additional = parse_fhir_query_from_text(raw_text), []
        return GeneratedQuery(raw_response=raw_text, parsed_query=parsed,
                              additional_queries=additional)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_llm/test_openai_chat_provider.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/llm/openai_chat_provider.py backend/tests/test_llm/test_openai_chat_provider.py
git commit -m "feat: add OpenAIChatProvider for Tier 1 closed-book on Lemonade"
```

---

## Task 6: Wire `lemonade` + `lemonade-agentic` into `get_provider()`

**Files:**
- Modify: `backend/src/llm/__init__.py`
- Test: `backend/tests/test_llm/test_openai_chat_provider.py` (append two tests)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_llm/test_openai_chat_provider.py`:

```python
def test_factory_builds_lemonade_tier1():
    from src.llm import get_provider
    from src.llm.openai_chat_provider import OpenAIChatProvider
    p = get_provider("lemonade", model="Phi-4-mini-reasoning-Hybrid")
    assert isinstance(p, OpenAIChatProvider)
    assert p.model == "Phi-4-mini-reasoning-Hybrid"


def test_factory_builds_lemonade_agentic_with_default_base_url():
    from src.llm import get_provider
    from src.llm.agentic_provider import LemonadeAgenticProvider
    p = get_provider("lemonade-agentic", model="Phi-4-mini-reasoning-Hybrid",
                     fhir_url="https://localhost:8443", tier=2)
    assert isinstance(p, LemonadeAgenticProvider)
    assert p.tier == 2
    assert p.backend.base_url == "http://localhost:13305/api/v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_llm/test_openai_chat_provider.py -k factory -v`
Expected: FAIL — `ValueError: Unknown provider: 'lemonade'`

- [ ] **Step 3: Write minimal implementation**

In `backend/src/llm/__init__.py`:

Add imports after line 5 (`from .agentic_provider import OllamaAgenticProvider`):

```python
from .agentic_provider import OllamaAgenticProvider, LemonadeAgenticProvider
from .openai_chat_provider import OpenAIChatProvider
```

(Replace the existing line 5 with the first line above; add the second.)

Add `import os` at the top of the file (line 1, before the other imports).

Add two `elif` branches in `get_provider()`, immediately before the final `else` (line 34):

```python
    elif name == "lemonade":
        base_url = kwargs.pop("base_url", None) or os.environ.get(
            "LEMONADE_BASE_URL", "http://localhost:13305/api/v1")
        # Tier 1 closed-book — drop agentic-only kwargs if a caller passed them
        kwargs.pop("fhir_url", None)
        kwargs.pop("max_iterations", None)
        kwargs.pop("tier", None)
        return OpenAIChatProvider(model=model or "Phi-4-mini-reasoning-Hybrid",
                                  base_url=base_url, **kwargs)
    elif name == "lemonade-agentic":
        base_url = kwargs.pop("base_url", None) or os.environ.get(
            "LEMONADE_BASE_URL", "http://localhost:13305/api/v1")
        fhir_url = kwargs.pop("fhir_url", "http://localhost:8080/fhir")
        max_iterations = kwargs.pop("max_iterations", 10)
        return LemonadeAgenticProvider(
            model=model or "Phi-4-mini-reasoning-Hybrid",
            base_url=base_url,
            fhir_base_url=fhir_url,
            max_iterations=max_iterations,
            **kwargs,
        )
```

Update the final `else` error message and the docstring to include the new names:

```python
    else:
        raise ValueError(
            f"Unknown provider: '{name}'. "
            "Choose from: anthropic, claude-cli, command, ollama-agentic, "
            "lemonade, lemonade-agentic"
        )
```

Add `"LemonadeAgenticProvider", "OpenAIChatProvider"` to the `__all__` list.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_llm/ -v`
Expected: PASS — all test_llm tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/src/llm/__init__.py backend/tests/test_llm/test_openai_chat_provider.py
git commit -m "feat: wire lemonade + lemonade-agentic into get_provider factory"
```

---

## Task 7: Add `--backend` flag to `run_sanity_matrix.py`

**Files:**
- Modify: `scripts/run_sanity_matrix.py` (lines ~63-82, ~114, ~138-154, ~177-198)

- [ ] **Step 1: Add the `--backend` argument**

In `main()`, in the argparse block (after the `--model` line ~180), add:

```python
    p.add_argument("--backend", choices=["ollama", "lemonade"], default="ollama",
                   help="Model serving backend (default: ollama)")
```

- [ ] **Step 2: Thread `backend` through `make_provider`**

Replace `make_provider` (lines ~63-82) with:

```python
def make_provider(tier: int, model: str, fhir_url: str, backend: str = "ollama",
                  cell_timeout_sec: int = 300):
    if tier == 1:
        inner_timeout = max(30, cell_timeout_sec - 30)
        if backend == "lemonade":
            return get_provider("lemonade", model=model)
        return get_provider(
            "command",
            command=f"ollama run {model}",
            timeout_sec=inner_timeout,
        )
    base = fhir_url.rstrip("/")
    is_root_mounted = base.lower().startswith("https://") or ":8443" in base
    agentic_fhir = base if (is_root_mounted or base.endswith("/fhir")) else base + "/fhir"
    provider_name = "lemonade-agentic" if backend == "lemonade" else "ollama-agentic"
    return get_provider(
        provider_name,
        model=model,
        fhir_url=agentic_fhir,
        tier=tier,
        max_iterations=AGENT_MAX_ITERATIONS,
    )
```

- [ ] **Step 3: Thread `backend` through `run_one_cell` and the subprocess path**

In `run_one_cell` (line ~95), add `backend: str = "ollama"` to the signature (after `fhir_url`). Update its `make_provider` call (line ~107) to pass `backend`:

```python
        provider = make_provider(tier, model, fhir_url, backend, cell_timeout_sec)
```

Replace the hardcoded provider name (line ~114) with:

```python
        provider_name = backend
```

In `run_cell_subprocess` (line ~138), add `backend: str` to the signature and add to the `cmd` list (after the `--model` pair):

```python
        "--backend", backend,
```

- [ ] **Step 4: Pass `--backend` through the single-cell argparse path**

In `main()`, in the single-cell branch (line ~193-198), update the `run_one_cell` call to pass `args.backend`:

```python
    if args.single_cell:
        cell = run_one_cell(args.test_case, args.cell_tier, args.cell_variant,
                            args.model, args.fhir_url, args.backend, args.cell_timeout_sec)
```

In the matrix loop (line ~220), update the `run_cell_subprocess` call:

```python
            cell = run_cell_subprocess(tc.id, tier, variant, args.model,
                                       args.fhir_url, args.backend, args.cell_timeout_sec)
```

Add `"backend": args.backend,` to the JSON report dict (after the `"model"` key, line ~248).

- [ ] **Step 5: Smoke-test the argument parsing**

Run: `python scripts/run_sanity_matrix.py --help`
Expected: help text shows `--backend {ollama,lemonade}`; no errors.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_sanity_matrix.py
git commit -m "feat: add --backend flag to run_sanity_matrix"
```

---

## Task 8: End-to-end verification

No new code — this task proves the spec's verification gate. Record actual output; if a step fails, stop and report rather than papering over it.

- [ ] **Step 1: Full unit suite green**

Run: `cd backend && poetry run pytest`
Expected: PASS — all pre-existing tests plus the new `test_llm` tests.

- [ ] **Step 2: Qwen path unchanged (regression check)**

Confirm Ollama is running with `qwen3.5:9b` available, then:

Run: `python scripts/run_sanity_matrix.py -t phekb-asthma-dx --model qwen3.5:9b --backend ollama --tiers 2 --prompt-variants naive --fhir-url https://localhost:8443`
Expected: the T2/naive cell completes with a non-error result (a P/R/F1 line, not `ERROR`). This proves the `OllamaChatBackend` seam preserves the qwen path.

- [ ] **Step 3: Lemonade smoke matrix (all 3 tiers)**

Confirm the Lemonade server responds: `curl -s http://localhost:13305/api/v1/models | head -c 200`

Run: `python scripts/run_sanity_matrix.py -t phekb-asthma-dx --model Phi-4-mini-reasoning-Hybrid --backend lemonade --fhir-url https://localhost:8443`
Expected: a 3×3 matrix runs to completion. Tier 1 cells should produce queries; Tier 2/3 may or may not score well, but should not crash on transport errors.

- [ ] **Step 4: Confirm speed fields landed in the result JSON**

Run: `python -c "import json,glob; f=sorted(glob.glob('results/sanity-matrix-phekb-asthma-dx-Phi-4-mini-reasoning-Hybrid-*.json'))[-1]; d=json.load(open(f)); print(f); [print(c['tier'], c['prompt_variant'], c.get('run_metadata',{}).get('tokens_per_sec'), c.get('run_metadata',{}).get('provider_backend')) for c in d['results']]"`
Expected: rows print with `provider_backend` = `lemonade` and a non-`None` `tokens_per_sec` for the agentic (T2/T3) cells.

- [ ] **Step 5: Tool-calling spot-check (finding, not a bug)**

Inspect a Tier 2 cell from the Lemonade run for whether the model emitted tool calls:

Run: `python -c "import json,glob; f=sorted(glob.glob('results/sanity-matrix-phekb-asthma-dx-Phi-4-mini-reasoning-Hybrid-*.json'))[-1]; d=json.load(open(f)); [print(c['tier'], c['prompt_variant'], c.get('run_metadata',{}).get('tool_calls_count'), c.get('run_metadata',{}).get('stop_reason')) for c in d['results'] if c['tier']==2]"`
Expected: record the `tool_calls_count`. If it is consistently 0, that is a real finding about `Phi-4-mini-reasoning-Hybrid`'s tool-calling reliability — report it, do not hide it.

- [ ] **Step 6: Commit the verification results**

Append a short results note to the spec file (`docs/superpowers/specs/2026-05-13-lemonade-backend-design.md`) under a new `## Verification Results` heading: paste the qwen regression line, the Lemonade matrix summary, observed `tokens_per_sec`, and the tool-calling finding.

```bash
git add docs/superpowers/specs/2026-05-13-lemonade-backend-design.md
git commit -m "docs: record Lemonade backend verification results"
```

---

## Self-Review Notes

- **Spec coverage:** ChatBackend seam (T1-T2), normalized format (T1-T2), OllamaChatBackend qwen-parity (T1, verified T8.2), OpenAIChatBackend incl. reasoning_content/`tool_call_id`/JSON-string args (T2), Tier-1 `OpenAIChatProvider` (T5), factory wiring (T6), `--backend` flag (T7), speed metrics into RunMetadata (T3 + T4 wiring + T8.4), verification gate incl. tool-call spot-check (T8). All spec sections mapped.
- **Spec deviation (intentional):** spec listed `prompt_tokens`/`completion_tokens` as new RunMetadata fields; `RunMetadata` already has `input_tokens`/`output_tokens`, so those are reused and only `tokens_per_sec`/`ttft_sec` are added.
- **Type consistency:** `get_run_metrics()` returns the same 5 keys (`provider_backend`, `input_tokens`, `output_tokens`, `tokens_per_sec`, `ttft_sec`) in both backends and Task 4 consumes exactly those. Normalized tool-call shape `{"id", "function": {"name", "arguments"}}` is produced by both backends and consumed unchanged by the existing loop body.
- **Out of scope:** running the skipped phenotypes — separate follow-up task per the spec.
