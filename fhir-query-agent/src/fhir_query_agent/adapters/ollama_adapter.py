"""Adapter for Ollama's native tool calling API."""

from fhir_query_agent.adapters.base import AdapterResponse, LLMAdapter, ToolCall


class OllamaAdapter(LLMAdapter):
    """Adapter for local Ollama models with native tool calling.

    Requires `ollama` Python package and a running Ollama server.
    Models with good tool calling support: qwen2.5:7b, llama3.1:8b,
    mistral-nemo, command-r.
    """

    def __init__(self, model: str = "qwen2.5:7b", host: str = None):
        """Initialize the Ollama adapter.

        Args:
            model: Ollama model name (e.g., "qwen2.5:7b").
            host: Ollama server URL. Defaults to http://localhost:11434.
        """
        self.model = model
        self.host = host

    def chat(self, messages: list[dict], tools: list[dict]) -> AdapterResponse:
        """Send a chat request with tools to Ollama.

        Args:
            messages: Conversation messages.
            tools: Tool definitions in Ollama/OpenAI function format.

        Returns:
            AdapterResponse with content and/or tool calls.
        """
        try:
            import ollama
        except ImportError:
            raise ImportError(
                "ollama package is required. Install with: pip install ollama"
            )

        kwargs = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        if self.host:
            client = ollama.Client(host=self.host)
            response = client.chat(**kwargs)
        else:
            response = ollama.chat(**kwargs)

        msg = response["message"]
        content = msg.get("content", "") or ""
        raw_tool_calls = msg.get("tool_calls") or []

        tool_calls = []
        for tc in raw_tool_calls:
            func = tc.get("function", {})
            tool_calls.append(
                ToolCall(
                    name=func.get("name", ""),
                    arguments=func.get("arguments", {}),
                )
            )

        return AdapterResponse(
            content=content,
            tool_calls=tool_calls,
            is_final=len(tool_calls) == 0,
        )
