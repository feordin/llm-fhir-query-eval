"""Base adapter interface for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """A single tool call from the LLM."""

    name: str
    arguments: dict


@dataclass
class AdapterResponse:
    """Standardized response from any LLM adapter.

    Attributes:
        content: Text content from the LLM (may be empty if tool calls present).
        tool_calls: List of tool calls the LLM wants to make.
        is_final: True if the LLM is done (no more tool calls needed).
    """

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    is_final: bool = True


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters.

    Each adapter translates between the agent's generic interface and a
    specific LLM provider's API (Ollama, Anthropic, OpenAI, etc.).
    """

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict]) -> AdapterResponse:
        """Send a chat completion request with tool definitions.

        Args:
            messages: Conversation history in OpenAI-style format:
                [{"role": "system"|"user"|"assistant"|"tool", "content": "..."}]
            tools: Tool definitions in the provider's expected format.

        Returns:
            AdapterResponse with content and/or tool calls.
        """
        ...
