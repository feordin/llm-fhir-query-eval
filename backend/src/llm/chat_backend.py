"""Chat backend abstraction for the agentic loop.

Defines a vendor-agnostic chat interface so the agent loop can run against
any LLM provider (Ollama, Foundry Local, Azure OpenAI, OpenAI direct,
Together, Fireworks, etc.) without caring about message-shape differences.

Canonical message and tool shapes are OpenAI-compatible. Each backend
translates to/from its vendor-native form at the wire.
"""
from __future__ import annotations

import json
import logging
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class NormalizedToolCall:
    """A tool call extracted from an assistant message, in canonical form."""
    id: str
    name: str
    arguments: dict


@dataclass
class AssistantMessage:
    """Normalized assistant turn: free-form text plus zero-or-more tool calls."""
    content: str
    tool_calls: list[NormalizedToolCall] = field(default_factory=list)


class ChatBackend(ABC):
    """Send messages + tools to an LLM and get a normalized reply.

    Inputs (`messages`, `tools`) MUST be in OpenAI-compatible shape — the
    canonical form used by the agent loop. The backend translates to its
    vendor-native shape internally.
    """

    backend_name: str  # set by subclass
    model: str         # set in __init__

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantMessage:
        """Send the conversation + tool definitions, return the assistant reply."""

    def assistant_to_history_dict(self, msg: AssistantMessage) -> dict:
        """Convert a normalized assistant message back to a canonical history dict
        the loop can append before issuing the next turn."""
        d: dict = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            d["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {
                        "name": c.name,
                        "arguments": json.dumps(c.arguments),
                    },
                }
                for c in msg.tool_calls
            ]
        return d

    @staticmethod
    def tool_result_message(tool_call_id: str, content: str) -> dict:
        """Build a canonical tool-result message for the next turn's history."""
        return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

class OllamaChatBackend(ChatBackend):
    """Backend for a local Ollama daemon using the `ollama` Python client."""

    backend_name = "ollama"

    def __init__(self, model: str):
        import ollama
        self._ollama = ollama
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantMessage:
        ollama_msgs = [_canonical_to_ollama(m) for m in messages]
        resp = self._ollama.chat(model=self.model, messages=ollama_msgs, tools=tools)
        return _ollama_msg_to_normalized(resp["message"])


def _canonical_to_ollama(m: dict) -> dict:
    """Strip tool_call_id (Ollama doesn't use it) and inflate JSON-string
    tool-call arguments back into dicts (Ollama uses dicts on the wire)."""
    out = {k: v for k, v in m.items() if k != "tool_call_id"}
    if "tool_calls" in out and out["tool_calls"]:
        new_calls = []
        for c in out["tool_calls"]:
            fn = c["function"]
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            new_calls.append({"function": {"name": fn["name"], "arguments": args}})
        out["tool_calls"] = new_calls
    return out


def _ollama_msg_to_normalized(msg: dict) -> AssistantMessage:
    content = msg.get("content", "") or ""
    calls: list[NormalizedToolCall] = []
    for i, c in enumerate(msg.get("tool_calls") or []):
        fn = c.get("function", {})
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        calls.append(NormalizedToolCall(
            id=c.get("id") or f"ollama-{i}-{secrets.token_hex(3)}",
            name=fn.get("name", ""),
            arguments=args or {},
        ))
    return AssistantMessage(content=content, tool_calls=calls)


# ---------------------------------------------------------------------------
# OpenAI-compatible (covers Foundry Local, Azure OpenAI, OpenAI direct, etc.)
# ---------------------------------------------------------------------------

class OpenAICompatChatBackend(ChatBackend):
    """Backend for any OpenAI-compatible /v1/chat/completions endpoint.

    Foundry Local, Azure OpenAI, OpenAI direct, Together, Fireworks, GitHub
    Models all share this protocol with different (base_url, api_key) pairs.
    """

    backend_name = "openai-compat"

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str = "not-used",
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ):
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantMessage:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return self._extract_assistant_message(resp.choices[0].message)

    def _extract_assistant_message(self, choice) -> AssistantMessage:
        """Hook: subclasses can override to apply vendor-specific recovery."""
        content = choice.content or ""
        calls: list[NormalizedToolCall] = []
        for c in (choice.tool_calls or []):
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(NormalizedToolCall(
                id=c.id, name=c.function.name, arguments=args,
            ))
        return AssistantMessage(content=content, tool_calls=calls)


def _extract_foundry_assistant_message(choice) -> AssistantMessage:
    """Extract assistant message from an OpenAI-shape `choice`, applying the
    Foundry Local 0.8.x recovery parser when `tool_calls` is empty.

    Used by both the HTTP-path FoundryChatBackend and the in-process
    FoundryWinMLChatBackend — they share the same response shape and the
    same auto-mode tool-call bug.
    """
    content = choice.content or ""
    calls: list[NormalizedToolCall] = []
    for c in (choice.tool_calls or []):
        try:
            args = json.loads(c.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append(NormalizedToolCall(
            id=c.id, name=c.function.name, arguments=args,
        ))
    if calls:
        return AssistantMessage(content=content, tool_calls=calls)
    from .foundry_local_provider import FoundryLocalProvider
    recovered = FoundryLocalProvider.recover_tool_calls_from_content(content)
    if not recovered:
        return AssistantMessage(content=content, tool_calls=[])
    logger.info(
        "Foundry recovery: parsed %d tool call(s) from content (auto-mode bug)",
        len(recovered),
    )
    return AssistantMessage(
        content=content,
        tool_calls=[
            NormalizedToolCall(
                id=r["id"],
                name=r["function"]["name"],
                arguments=json.loads(r["function"]["arguments"]),
            )
            for r in recovered
        ],
    )


class FoundryChatBackend(OpenAICompatChatBackend):
    """OpenAI-compat backend + recovery hook for Foundry Local 0.8.x HTTP API.

    NOTE: this path is fragile under agentic load — the Inference.Service.Agent
    .NET process can crash on long contexts with tool definitions.
    Use FoundryWinMLChatBackend for Tier 2/3 work instead.
    """

    backend_name = "foundry-local"

    def _extract_assistant_message(self, choice) -> AssistantMessage:
        return _extract_foundry_assistant_message(choice)


class AzureOpenAIChatBackend(OpenAICompatChatBackend):
    """Backend for Azure OpenAI Service deployments.

    Different surface from a generic OpenAI-compatible endpoint:
    - URL: ``https://<resource>.openai.azure.com`` (NOT a /chat/completions URL)
    - Auth: ``api-key`` header instead of ``Authorization: Bearer``
    - Requires ``api_version`` (e.g. ``2024-08-01-preview``)
    - The ``model`` parameter is the Azure DEPLOYMENT NAME, not a base model name

    For Azure AI Foundry serverless endpoints (``*.services.ai.azure.com`` /
    ``*.inference.ai.azure.com``), use the generic OpenAICompatChatBackend
    instead -- those speak the standard OpenAI protocol over a base_url.

    Reuses chat() and translation logic from OpenAICompatChatBackend; only
    swaps the client construction.
    """

    backend_name = "azure-openai"

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        api_version: str = "2024-08-01-preview",
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ):
        from openai import AzureOpenAI
        # AzureOpenAI uses azure_endpoint=, NOT base_url=. azure_endpoint is the
        # resource root (e.g. https://<resource>.openai.azure.com), and the SDK
        # appends /openai/deployments/<model>/... internally.
        self.client = AzureOpenAI(
            azure_endpoint=base_url, api_key=api_key, api_version=api_version,
        )
        self.model = model  # = the Azure deployment name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.api_version = api_version


# ---------------------------------------------------------------------------
# Foundry Local in-process SDK (Windows ML / NPU). Bypasses the HTTP service
# entirely — same QNN execution provider, but inference happens inside the
# Python process, which empirically does not exhibit the agentic-load crash
# that takes down `Inference.Service.Agent`.
# ---------------------------------------------------------------------------

_foundry_winml_manager = None  # process-singleton SDK manager


def _get_foundry_winml_manager(app_name: str = "fhir-eval-winml"):
    """Lazily initialize the foundry-local-sdk-winml manager (singleton).

    Calling this multiple times within a process is cheap: it inits the SDK
    once, registers QNN once, and returns the same manager instance.
    """
    global _foundry_winml_manager
    if _foundry_winml_manager is not None:
        return _foundry_winml_manager
    from foundry_local_sdk import FoundryLocalManager, Configuration
    FoundryLocalManager.initialize(Configuration(app_name=app_name))
    mgr = FoundryLocalManager.instance
    mgr.download_and_register_eps()
    _foundry_winml_manager = mgr
    return mgr


class FoundryWinMLChatBackend(ChatBackend):
    """In-process Foundry Local chat backend using foundry-local-sdk-winml.

    Loads the model into the current Python process and runs inference on the
    NPU directly via QNN. Survives the agentic-load patterns that crash the
    HTTP service.

    NOTE on timeouts: the SDK's native layer has TWO hard wall-clock caps per
    chat completion:
      - non-streaming complete_chat: ~120s
      - streaming complete_streaming_chat: ~300s
    At ~4-5 tok/s on the Snapdragon NPU, that's ~500 tokens for non-streaming
    or ~1200 tokens for streaming. We use streaming under the hood and
    accumulate chunks into a single response — strictly more headroom, and
    finish_reason=length fires before the wall clock if max_tokens hits first.

    Default max_tokens=1024 keeps total generation inside the 300s streaming
    budget with headroom. Each call's input prefill also counts against this
    budget, so very long inputs (e.g. Tier 3 methodology + 10 tool defs) leave
    less room for output — keep system prompts tight.
    """

    backend_name = "foundry-local"

    def __init__(self, model: str, max_tokens: int = 1024, temperature: float = 0.0):
        mgr = _get_foundry_winml_manager()
        self._model_obj = mgr.catalog.get_model(model)
        if not self._model_obj.is_cached:
            logger.info("Foundry model %s not cached; downloading...", model)
            self._model_obj.download(progress_callback=lambda _p: None)
        if not self._model_obj.is_loaded:
            logger.info("Loading Foundry model %s on NPU...", self._model_obj.id)
            self._model_obj.load()
        self._client = self._model_obj.get_chat_client()
        self._client.settings.max_tokens = max_tokens
        self._client.settings.temperature = temperature
        self.model = self._model_obj.id
        self.max_tokens = max_tokens
        self.temperature = temperature

    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantMessage:
        """Run a chat completion via the SDK's streaming API and accumulate.

        Streaming gives us the longer 300s native budget. We rebuild a
        single OpenAI-shape choice from the deltas and feed it through the
        Foundry recovery parser as before.
        """
        content_parts: list[str] = []
        # tool_calls accumulator: index -> {id, name, arguments(str)}
        tc_buf: dict[int, dict] = {}
        for chunk in self._client.complete_streaming_chat(messages, tools=tools or None):
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            if getattr(delta, "content", None):
                content_parts.append(delta.content)
            for tc in (getattr(delta, "tool_calls", None) or []):
                idx = getattr(tc, "index", 0) or 0
                slot = tc_buf.setdefault(idx, {"id": None, "name": None, "arguments": ""})
                if getattr(tc, "id", None):
                    slot["id"] = tc.id
                fn = getattr(tc, "function", None)
                if fn is not None:
                    if getattr(fn, "name", None):
                        slot["name"] = fn.name
                    if getattr(fn, "arguments", None):
                        slot["arguments"] += fn.arguments

        # Materialize an OpenAI-shape "choice.message" so the existing
        # recovery parser path can run unchanged.
        from types import SimpleNamespace

        def _ns_tc(slot):
            return SimpleNamespace(
                id=slot["id"] or "",
                function=SimpleNamespace(
                    name=slot["name"] or "",
                    arguments=slot["arguments"] or "",
                ),
            )

        fake_choice = SimpleNamespace(
            content="".join(content_parts),
            tool_calls=[_ns_tc(s) for s in tc_buf.values()] or None,
        )
        return _extract_foundry_assistant_message(fake_choice)
