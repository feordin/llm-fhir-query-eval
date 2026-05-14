from .provider import LLMProvider, parse_fhir_query_from_text, FHIR_SYSTEM_PROMPT, FHIR_SYSTEM_PROMPT_VERSION, build_generated_query
from .anthropic_provider import AnthropicProvider
from .cli_delegate_provider import CLIDelegateProvider
from .command_provider import CommandProvider
import os

from .agentic_provider import (
    AgenticProvider, OllamaAgenticProvider, FoundryAgenticProvider,
    OpenAICompatAgenticProvider,
)
from .foundry_local_provider import FoundryLocalProvider
from .openai_chat_provider import OpenAIChatProvider
from .chat_backend import (
    ChatBackend, OllamaChatBackend, OpenAICompatChatBackend,
    FoundryChatBackend, FoundryWinMLChatBackend,
)


def get_provider(name: str, model: str = None, **kwargs) -> LLMProvider:
    """Factory to create LLM provider by name.

    Args:
        name: Provider name - "anthropic", "claude-cli", "command",
              "ollama-agentic", "foundry-local", "foundry-agentic", or
              "openai-compat" (any OpenAI-compatible endpoint, incl. AMD GAIA
              Lemonade and Azure OpenAI)
        model: Model name (provider-specific)
        **kwargs: Additional provider-specific args
    """
    if name == "anthropic":
        return AnthropicProvider(model=model or "claude-sonnet-4-20250514", **kwargs)
    elif name == "claude-cli":
        return CLIDelegateProvider(model=model, **kwargs)
    elif name == "command":
        if "command" not in kwargs:
            raise ValueError("'command' provider requires a --command argument (e.g., 'ollama run llama3')")
        return CommandProvider(**kwargs)
    elif name == "ollama-agentic":
        fhir_url = kwargs.pop("fhir_url", "http://localhost:8080/fhir")
        max_iterations = kwargs.pop("max_iterations", 10)
        return OllamaAgenticProvider(
            model=model or "qwen2.5:7b",
            fhir_base_url=fhir_url,
            max_iterations=max_iterations,
            **kwargs,
        )
    elif name == "foundry-local":
        return FoundryLocalProvider(model=model or "qwen2.5-7b", **kwargs)
    elif name == "foundry-agentic":
        fhir_url = kwargs.pop("fhir_url", "http://localhost:8080/fhir")
        max_iterations = kwargs.pop("max_iterations", 10)
        return FoundryAgenticProvider(
            model=model or "qwen2.5-7b",
            fhir_base_url=fhir_url,
            max_iterations=max_iterations,
            **kwargs,
        )
    elif name == "openai-compat":
        # Any OpenAI-compatible endpoint. base_url via arg / OPENAI_COMPAT_BASE_URL
        # env / Lemonade's default. Tier 1 (closed-book) when no fhir_url is given,
        # otherwise the agentic loop.
        base_url = kwargs.pop("base_url", None) or os.environ.get(
            "OPENAI_COMPAT_BASE_URL", "http://localhost:13305/api/v1")
        if "fhir_url" in kwargs or "tier" in kwargs:
            fhir_url = kwargs.pop("fhir_url", "http://localhost:8080/fhir")
            max_iterations = kwargs.pop("max_iterations", 10)
            return OpenAICompatAgenticProvider(
                model=model, base_url=base_url, fhir_base_url=fhir_url,
                max_iterations=max_iterations, **kwargs,
            )
        return OpenAIChatProvider(model=model, base_url=base_url, **kwargs)
    else:
        raise ValueError(
            f"Unknown provider: '{name}'. Choose from: anthropic, claude-cli, command, "
            "ollama-agentic, foundry-local, foundry-agentic, openai-compat"
        )


__all__ = [
    "LLMProvider", "get_provider", "parse_fhir_query_from_text", "FHIR_SYSTEM_PROMPT",
    "FHIR_SYSTEM_PROMPT_VERSION", "build_generated_query",
    "AnthropicProvider", "CLIDelegateProvider", "CommandProvider",
    "AgenticProvider", "OllamaAgenticProvider", "FoundryAgenticProvider",
    "OpenAICompatAgenticProvider", "FoundryLocalProvider", "OpenAIChatProvider",
    "ChatBackend", "OllamaChatBackend", "OpenAICompatChatBackend",
    "FoundryChatBackend", "FoundryWinMLChatBackend",
]
