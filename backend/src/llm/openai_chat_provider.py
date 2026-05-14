"""Tier 1 (closed-book) provider over any OpenAI-compatible HTTP server.

The Ollama Tier-1 path shells out `ollama run <model>` (CommandProvider) and
Foundry Local uses FoundryLocalProvider. This is the equivalent closed-book
path for any OpenAI-compatible endpoint (AMD GAIA Lemonade, Azure OpenAI,
OpenAI direct): a single chat completion with no tools, reusing
OpenAICompatChatBackend.
"""
import sys
from pathlib import Path

from .provider import LLMProvider, FHIR_SYSTEM_PROMPT, build_generated_query
from .chat_backend import OpenAICompatChatBackend

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery


class OpenAIChatProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:13305/api/v1",
                 api_key: str = "not-used"):
        self.model = model
        self.backend = OpenAICompatChatBackend(model=model, base_url=base_url,
                                               api_key=api_key)

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        user_content = prompt if not context else f"{context}\n\n{prompt}"
        msg = self.backend.chat(
            messages=[
                {"role": "system", "content": FHIR_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            tools=[],
        )
        if not (msg.content or "").strip():
            raise RuntimeError("Model returned empty content")
        return build_generated_query(msg.content)
