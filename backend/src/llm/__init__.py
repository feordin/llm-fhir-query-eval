from .provider import LLMProvider, parse_fhir_query_from_text, FHIR_SYSTEM_PROMPT, FHIR_SYSTEM_PROMPT_VERSION, build_generated_query
from .anthropic_provider import AnthropicProvider
from .cli_delegate_provider import CLIDelegateProvider
from .command_provider import CommandProvider
from .agentic_provider import AgenticProvider, OllamaAgenticProvider, FoundryAgenticProvider
from .foundry_local_provider import FoundryLocalProvider
from .chat_backend import (
    ChatBackend, OllamaChatBackend, OpenAICompatChatBackend,
    FoundryChatBackend, FoundryWinMLChatBackend,
)


def get_provider(name: str, model: str = None, **kwargs) -> LLMProvider:
    """Factory to create LLM provider by name.

    Args:
        name: Provider name - "anthropic", "claude-cli", "command",
              "ollama-agentic", "foundry-local", or "foundry-agentic"
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
    else:
        raise ValueError(
            f"Unknown provider: '{name}'. Choose from: anthropic, claude-cli, command, "
            "ollama-agentic, foundry-local, foundry-agentic"
        )


__all__ = [
    "LLMProvider", "get_provider", "parse_fhir_query_from_text", "FHIR_SYSTEM_PROMPT",
    "FHIR_SYSTEM_PROMPT_VERSION", "build_generated_query",
    "AnthropicProvider", "CLIDelegateProvider", "CommandProvider",
    "AgenticProvider", "OllamaAgenticProvider", "FoundryAgenticProvider",
    "FoundryLocalProvider",
    "ChatBackend", "OllamaChatBackend", "OpenAICompatChatBackend",
    "FoundryChatBackend", "FoundryWinMLChatBackend",
]
