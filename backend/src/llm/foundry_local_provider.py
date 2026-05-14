"""Closed-book FHIR query provider backed by Foundry Local on the NPU.

Uses the in-process foundry-local-sdk-winml SDK so inference runs directly
on the Snapdragon NPU via QNN. Avoids the HTTP-service-based path because
that service crashes under agentic load (long context + tool definitions).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from .provider import LLMProvider, FHIR_SYSTEM_PROMPT, build_generated_query

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery

logger = logging.getLogger(__name__)


class FoundryLocalProvider(LLMProvider):
    """Closed-book FHIR query generation via Foundry Local in-process SDK.

    The SDK loads the model into the current Python process and runs inference
    on the NPU directly. Note that each subprocess pays a ~10s cold-load cost
    (the model is reused only within one process).
    """

    def __init__(
        self,
        model: str = "qwen2.5-7b",
        max_tokens: int = 1024,  # see FoundryWinMLChatBackend re: 300s streaming cap
        temperature: float = 0.0,
        # base_url accepted but ignored — kept so existing CLI plumbing
        # (which passes --base-url for the legacy HTTP path) doesn't break.
        base_url: Optional[str] = None,
        **_legacy_kwargs,
    ):
        from .chat_backend import FoundryWinMLChatBackend
        self._backend = FoundryWinMLChatBackend(
            model=model, max_tokens=max_tokens, temperature=temperature,
        )
        self.alias = model
        self.model_id = self._backend.model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        user_message = f"{context}\n\n{prompt}" if context else prompt
        msg = self._backend.chat(
            messages=[
                {"role": "system", "content": FHIR_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            tools=[],
        )
        return build_generated_query(msg.content)

    @staticmethod
    def recover_tool_calls_from_content(content: str) -> list[dict]:
        """Extract tool calls from the assistant message's content field.

        Workaround for Foundry Local 0.8.119, where `tool_choice="auto"` returns
        an empty `tool_calls` array even when the model emits a well-formed
        call. The intended call appears in `content` in unpredictable forms
        because the chat template's special tokens decode inconsistently:

          1. Native Qwen:    <tool_call>{...}</tool_call>            (clean)
          2. Mangled parens: )(((({...}))))                          (auto-mode bug)
          3. Mangled tags:   <translation>{...}<translation>         (also seen)
          4. Other tags:     <[any-tag]>{...}<[any-tag-or-/]>        (defensive)
          5. Bare JSON:      a {"name": ..., "arguments": ...} object embedded
                             anywhere in the response, no tag wrapping.

        Strategy: try 1 -> 2 -> 3 (any tag-like wrapper) -> 5 (bare JSON
        scan for objects containing both "name" and "arguments"|"parameters").

        Returns OpenAI-shaped tool_call dicts, or [] if nothing parseable.
        """
        out: list[dict] = []

        # Layer 1: clean <tool_call>...</tool_call>
        for m in re.finditer(r"<tool_call>\s*(.+?)\s*</tool_call>", content, re.DOTALL):
            out.extend(_parse_payload(m.group(1)))
        if out:
            return out

        # Layer 2: )((((...))))
        for m in re.finditer(r"\)\({3,}\s*(\{.+?\})\s*\){3,}", content, re.DOTALL):
            out.extend(_parse_payload(m.group(1)))
        if out:
            return out

        # Layer 3: any <tagname>JSON<tagname-or-/tagname> wrapper
        for m in re.finditer(
            r"<([A-Za-z_][\w-]*)>\s*(\{.+?\})\s*</?\1>", content, re.DOTALL,
        ):
            out.extend(_parse_payload(m.group(2)))
        if out:
            return out

        # Layer 5: bare JSON object containing both "name" and arguments-like key
        for raw in _iter_balanced_json_objects(content):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "name" in obj and (
                "arguments" in obj or "parameters" in obj
            ):
                out.extend(_parse_payload(raw))
        return out


def _iter_balanced_json_objects(text: str):
    """Yield balanced top-level {...} substrings from text.

    Naive but effective: track brace depth, ignore braces inside string
    literals (recognising backslash escapes). Misses pathological cases
    but handles every shape we've seen Foundry emit.
    """
    i, n = 0, len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth, j, in_str, esc = 0, i, False, False
        while j < n:
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        yield text[i:j + 1]
                        i = j + 1
                        break
            j += 1
        else:
            return  # ran off the end without closing


def _parse_payload(text: str) -> list[dict]:
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = data if isinstance(data, list) else [data]
    out: list[dict] = []
    for i, call in enumerate(items):
        if not isinstance(call, dict) or "name" not in call:
            continue
        args = call.get("arguments", call.get("parameters", {}))
        if not isinstance(args, str):
            args = json.dumps(args)
        out.append({
            "id": f"foundry-recovered-{i}",
            "type": "function",
            "function": {"name": call["name"], "arguments": args},
        })
    return out
