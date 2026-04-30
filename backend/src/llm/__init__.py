from .provider import LLMProvider, parse_fhir_query_from_text, FHIR_SYSTEM_PROMPT
from .anthropic_provider import AnthropicProvider
from .cli_delegate_provider import CLIDelegateProvider
from .command_provider import CommandProvider
from .agentic_provider import OllamaAgenticProvider


def get_provider(name: str, model: str = None, **kwargs) -> LLMProvider:
    """Factory to create LLM provider by name.

    Args:
        name: Provider name - "anthropic", "claude-cli", "command", or "ollama-agentic"
        model: Model name (provider-specific)
        **kwargs: Additional provider-specific args (e.g., command="ollama run llama3")
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
        # Extract agentic-specific kwargs, pass the rest through
        fhir_url = kwargs.pop("fhir_url", "http://localhost:8080/fhir")
        max_iterations = kwargs.pop("max_iterations", 10)
        return OllamaAgenticProvider(
            model=model or "qwen2.5:7b",
            fhir_base_url=fhir_url,
            max_iterations=max_iterations,
            **kwargs,
        )
    else:
        raise ValueError(
            f"Unknown provider: '{name}'. "
            "Choose from: anthropic, claude-cli, command, ollama-agentic"
        )


__all__ = [
    "LLMProvider", "get_provider", "parse_fhir_query_from_text", "FHIR_SYSTEM_PROMPT",
    "AnthropicProvider", "CLIDelegateProvider", "CommandProvider", "OllamaAgenticProvider",
]
