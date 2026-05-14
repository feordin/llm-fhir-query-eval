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
    """Wraps ollama.chat() -- the existing qwen path, behavior unchanged."""

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


class OpenAIChatBackend(ChatBackend):
    """OpenAI-compatible HTTP backend. Serves AMD GAIA's Lemonade Server.

    provider_backend is reported as "lemonade" since that is the only
    OpenAI-compatible target wired in today.
    """

    # Some OpenAI-compatible servers (observed with Lemonade) intermittently
    # return an HTTP 200 whose body has no "choices" -- retry a few times
    # before giving up so a single blip doesn't kill a long agentic run.
    MAX_ATTEMPTS = 3

    def __init__(self, model: str, base_url: str, request_timeout: int = 300):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self._input_tokens = 0
        self._output_tokens = 0
        self._tokens_per_sec = None
        self._ttft_sec = None

    def _post_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST to /chat/completions, retrying on responses that lack 'choices'."""
        last_problem = None
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("choices"):
                return data
            last_problem = json.dumps(data)[:300]
            logger.warning(
                "OpenAI-compatible response missing 'choices' (attempt %d/%d): %s",
                attempt, self.MAX_ATTEMPTS, last_problem,
            )
        raise RuntimeError(
            f"OpenAI-compatible server returned no 'choices' after "
            f"{self.MAX_ATTEMPTS} attempts. Last body: {last_problem}"
        )

    def chat(self, messages: List[NormMsg], tools: List[dict]) -> NormMsg:
        wire_messages = [self._to_wire(m) for m in messages]
        payload: Dict[str, Any] = {"model": self.model, "messages": wire_messages}
        if tools:
            payload["tools"] = tools
        data = self._post_chat(payload)

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
