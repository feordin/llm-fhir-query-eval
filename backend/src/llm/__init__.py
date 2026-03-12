from .provider import LLMProvider, parse_fhir_query_from_text, FHIR_SYSTEM_PROMPT
from .anthropic_provider import AnthropicProvider
from .cli_delegate_provider import CLIDelegateProvider
from .command_provider import CommandProvider


def get_provider(name: str, model: str = None, **kwargs) -> LLMProvider:
    """Factory to create LLM provider by name.

    Args:
        name: Provider name - "anthropic", "claude-cli", or "command"
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
    else:
        raise ValueError(f"Unknown provider: '{name}'. Choose from: anthropic, claude-cli, command")


__all__ = [
    "LLMProvider", "get_provider", "parse_fhir_query_from_text", "FHIR_SYSTEM_PROMPT",
    "AnthropicProvider", "CLIDelegateProvider", "CommandProvider",
]
