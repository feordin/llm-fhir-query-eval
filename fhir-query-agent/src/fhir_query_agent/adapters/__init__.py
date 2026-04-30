"""LLM adapter interfaces and implementations."""

from fhir_query_agent.adapters.base import AdapterResponse, LLMAdapter
from fhir_query_agent.adapters.ollama_adapter import OllamaAdapter
from fhir_query_agent.adapters.anthropic_adapter import AnthropicAdapter

__all__ = ["AdapterResponse", "LLMAdapter", "OllamaAdapter", "AnthropicAdapter"]
