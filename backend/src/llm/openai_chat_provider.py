"""Tier 1 (closed-book) provider over an OpenAI-compatible HTTP server.

The Ollama Tier-1 path shells out `ollama run <model>` (CommandProvider).
Lemonade has no equivalent CLI, so its closed-book path is a single
/chat/completions call with no tools, reusing OpenAIChatBackend.
"""
import sys
from pathlib import Path

from .provider import (
    LLMProvider, FHIR_SYSTEM_PROMPT,
    parse_fhir_query_from_text, parse_fhir_queries_from_text,
)
from .chat_backend import OpenAIChatBackend

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery


class OpenAIChatProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:13305/api/v1",
                 request_timeout: int = 300):
        self.model = model
        self.backend = OpenAIChatBackend(model, base_url=base_url,
                                         request_timeout=request_timeout)

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        user_content = prompt if not context else f"{context}\n\n{prompt}"
        messages = [
            {"role": "system", "content": FHIR_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        msg = self.backend.chat(messages, tools=[])
        raw_text = (msg.get("content") or "").strip()
        if not raw_text:
            raise RuntimeError("Model returned empty content")

        all_parsed = parse_fhir_queries_from_text(raw_text)
        if all_parsed:
            parsed, additional = all_parsed[0], all_parsed[1:]
        else:
            parsed, additional = parse_fhir_query_from_text(raw_text), []
        return GeneratedQuery(raw_response=raw_text, parsed_query=parsed,
                              additional_queries=additional)
