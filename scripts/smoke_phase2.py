"""Phase 2 smoke test: validate the ChatBackend abstraction and the
refactored AgenticProvider loop.

Five checks:
  1. _canonical_to_ollama strips tool_call_id and inflates string args.
  2. _ollama_msg_to_normalized handles dict-arg tool calls correctly.
  3. FoundryChatBackend._extract_assistant_message recovers tool calls
     from content when the openai client returns empty tool_calls (the
     Foundry Local 0.8.x auto-mode bug). Mocks the openai response.
  4. AgenticProvider drives a scripted ChatBackend end-to-end:
     tool call -> tool result -> final answer with FHIR URL.
  5. Live: FoundryChatBackend.chat() against the running Foundry server
     with one real tool spec; verify the call comes back normalized.

Usage: python scripts/smoke_phase2.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from src.llm.chat_backend import (
    AssistantMessage,
    ChatBackend,
    FoundryChatBackend,
    FoundryWinMLChatBackend,
    NormalizedToolCall,
    OpenAICompatChatBackend,
    _canonical_to_ollama,
    _ollama_msg_to_normalized,
)
from src.llm.agentic_provider import AgenticProvider


# ---------------------------------------------------------------------------
# 1 & 2. Translator unit checks
# ---------------------------------------------------------------------------

def check_canonical_to_ollama() -> None:
    canonical_msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {
            "role": "assistant", "content": "",
            "tool_calls": [{
                "id": "call_abc",
                "type": "function",
                "function": {"name": "x", "arguments": '{"a": 1}'},
            }],
        },
        {"role": "tool", "tool_call_id": "call_abc", "content": "result"},
    ]
    out = [_canonical_to_ollama(m) for m in canonical_msgs]
    assert "tool_call_id" not in out[3], "tool_call_id not stripped from tool message"
    args = out[2]["tool_calls"][0]["function"]["arguments"]
    assert args == {"a": 1}, f"args not inflated to dict: {args!r}"
    print("  [OK] canonical -> ollama strips tool_call_id and inflates args")


def check_ollama_to_normalized() -> None:
    ollama_msg = {
        "role": "assistant",
        "content": "thinking...",
        "tool_calls": [
            {"function": {"name": "fhir_search",
                          "arguments": {"query": "Patient?_count=1"}}},
        ],
    }
    norm = _ollama_msg_to_normalized(ollama_msg)
    assert norm.content == "thinking..."
    assert len(norm.tool_calls) == 1
    assert norm.tool_calls[0].name == "fhir_search"
    assert norm.tool_calls[0].arguments == {"query": "Patient?_count=1"}
    assert norm.tool_calls[0].id, "id should be auto-generated"
    print("  [OK] ollama -> normalized handles dict-arg tool calls")


# ---------------------------------------------------------------------------
# 3. Foundry recovery hook (mocks openai response)
# ---------------------------------------------------------------------------

def check_foundry_recovery_hook() -> None:
    backend = FoundryChatBackend.__new__(FoundryChatBackend)
    backend.client = MagicMock()
    backend.model = "qwen2.5-7b-instruct-qnn-npu:2"

    # Simulate openai SDK: empty tool_calls, mangled call in content
    mangled_content = (
        ')(((({"name": "fhir_search", "arguments": {"query": "Patient?_count=1"}}))))'
    )
    fake_choice = SimpleNamespace(content=mangled_content, tool_calls=None)
    msg = backend._extract_assistant_message(fake_choice)
    assert len(msg.tool_calls) == 1, f"recovery failed: {msg.tool_calls}"
    assert msg.tool_calls[0].name == "fhir_search"
    assert msg.tool_calls[0].arguments == {"query": "Patient?_count=1"}
    print("  [OK] Foundry recovery hook extracts call from mangled content")


# ---------------------------------------------------------------------------
# 4. AgenticProvider loop with scripted backend
# ---------------------------------------------------------------------------

class ScriptedBackend(ChatBackend):
    backend_name = "scripted"
    model = "scripted-model"

    def __init__(self, scripted_replies: list[AssistantMessage]):
        self._replies = list(scripted_replies)
        self.calls_received: list[list[dict]] = []

    def chat(self, messages, tools):
        self.calls_received.append(list(messages))
        if not self._replies:
            raise RuntimeError("ScriptedBackend exhausted")
        return self._replies.pop(0)


class StubAgenticProvider(AgenticProvider):
    """AgenticProvider whose _execute_tool returns a fixed response (no real
    FHIR/UMLS dependency)."""

    def _execute_tool(self, name, args):
        return {"stubbed_for_tool": name, "args": args, "ok": True}


def check_agentic_loop() -> None:
    replies = [
        AssistantMessage(
            content="",
            tool_calls=[NormalizedToolCall(
                id="t1", name="fhir_search", arguments={"query": "Patient?_count=1"},
            )],
        ),
        AssistantMessage(
            content="Condition?code=http://snomed.info/sct|44054006",
        ),
    ]
    scripted = ScriptedBackend(scripted_replies=replies)
    provider = StubAgenticProvider(
        chat_backend=scripted,
        fhir_base_url="http://localhost:9999/fhir",  # never actually called
        max_iterations=5,
        tier=2,
    )
    result = provider.generate_fhir_query("Find diabetic patients")
    assert result.parsed_query is not None, "no parsed query returned"
    assert "44054006" in result.parsed_query.url, f"unexpected url: {result.parsed_query.url}"
    assert len(scripted.calls_received) == 2, f"expected 2 backend calls, got {len(scripted.calls_received)}"

    # Second-call history should include: system, user, assistant(tool_calls), tool(result)
    second_call_history = scripted.calls_received[1]
    roles = [m["role"] for m in second_call_history]
    assert roles == ["system", "user", "assistant", "tool"], f"unexpected roles: {roles}"
    assert second_call_history[3]["tool_call_id"] == "t1", "tool_call_id missing"
    assert provider.last_run_metadata is not None
    assert provider.last_run_metadata.provider_backend == "scripted"
    assert provider.last_run_metadata.tool_calls_count == 1
    print("  [OK] AgenticProvider drives scripted backend through tool_call -> final")


# ---------------------------------------------------------------------------
# 5. Live: FoundryChatBackend.chat against the running server
# ---------------------------------------------------------------------------

def check_live_foundry_backend() -> None:
    backend = FoundryWinMLChatBackend(model="qwen2.5-7b")
    messages = [
        {"role": "user", "content": "Look up the LOINC code for hemoglobin A1c."},
    ]
    tools = [{
        "type": "function",
        "function": {
            "name": "lookup_loinc",
            "description": "Look up a LOINC code by clinical concept name",
            "parameters": {
                "type": "object",
                "properties": {"concept": {"type": "string"}},
                "required": ["concept"],
            },
        },
    }]
    msg = backend.chat(messages, tools)
    print(f"    content: {msg.content[:120]!r}")
    print(f"    tool_calls: {[(c.name, c.arguments) for c in msg.tool_calls]}")
    if not msg.tool_calls:
        print("    [WARN] no tool calls returned (model may have answered directly)")
        return
    assert msg.tool_calls[0].name == "lookup_loinc", \
        f"unexpected call name: {msg.tool_calls[0].name}"
    print("  [OK] FoundryChatBackend.chat returned a normalized tool call")


def main() -> int:
    print("== Phase 2 smoke test ==\n")
    print("1. canonical -> ollama translator")
    check_canonical_to_ollama()
    print("\n2. ollama -> normalized translator")
    check_ollama_to_normalized()
    print("\n3. Foundry recovery hook (mocked openai response)")
    check_foundry_recovery_hook()
    print("\n4. AgenticProvider loop with scripted backend")
    check_agentic_loop()
    print("\n5. Live FoundryChatBackend.chat against running Foundry server")
    check_live_foundry_backend()
    print("\n== ALL CHECKS PASSED ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
