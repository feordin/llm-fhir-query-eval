from .provider import LLMProvider, FHIR_SYSTEM_PROMPT, parse_fhir_query_from_text

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery
from src.utils.config import settings


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str = None):
        import anthropic
        self.model = model
        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key.")
        self.client = anthropic.Anthropic(api_key=key)

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        user_message = prompt
        if context:
            user_message = f"{context}\n\n{prompt}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=FHIR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )

        raw_text = response.content[0].text
        parsed = parse_fhir_query_from_text(raw_text)
        return GeneratedQuery(raw_response=raw_text, parsed_query=parsed)
