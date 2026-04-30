"""Adapter for Anthropic API with tool use (stub)."""

from fhir_query_agent.adapters.base import AdapterResponse, LLMAdapter


class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic API with tool use.

    This is a stub implementation. Anthropic's tool use API requires
    converting between the OpenAI-style function format used internally
    and Anthropic's native tool_use format.

    To implement:
        1. Convert tool definitions to Anthropic format (input_schema)
        2. Convert messages to Anthropic format (system vs user/assistant)
        3. Parse tool_use content blocks from responses
        4. Return ToolCall objects for each tool_use block
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str = None):
        """Initialize the Anthropic adapter.

        Args:
            model: Anthropic model name.
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        """
        self.model = model
        self.api_key = api_key

    def chat(self, messages: list[dict], tools: list[dict]) -> AdapterResponse:
        """Send a chat request with tools to Anthropic.

        Not yet implemented. Raises NotImplementedError.
        """
        raise NotImplementedError(
            "Anthropic adapter not yet implemented. "
            "Use OllamaAdapter for local models or contribute this adapter."
        )
