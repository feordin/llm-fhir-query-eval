import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.llm.openai_chat_provider import OpenAIChatProvider


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _resp(content):
    return _FakeResp({
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 4},
    })


def test_tier1_provider_parses_query_from_content():
    provider = OpenAIChatProvider(model="Phi-4-mini-reasoning-Hybrid",
                                  base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_resp("Condition?code=http://snomed.info/sct|44054006")):
        result = provider.generate_fhir_query("Find diabetics")
    assert result.parsed_query.resource_type == "Condition"
    assert "44054006" in result.raw_response


def test_tier1_provider_raises_on_unparseable_content():
    provider = OpenAIChatProvider(model="Phi-4-mini-reasoning-Hybrid",
                                  base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_resp("I cannot help with that.")):
        try:
            provider.generate_fhir_query("Find diabetics")
            assert False, "expected a parse error"
        except (ValueError, RuntimeError):
            pass


def test_factory_builds_lemonade_tier1():
    from src.llm import get_provider
    p = get_provider("lemonade", model="Phi-4-mini-reasoning-Hybrid")
    assert isinstance(p, OpenAIChatProvider)
    assert p.model == "Phi-4-mini-reasoning-Hybrid"


def test_factory_builds_lemonade_agentic_with_default_base_url():
    from src.llm import get_provider
    from src.llm.agentic_provider import LemonadeAgenticProvider
    p = get_provider("lemonade-agentic", model="Phi-4-mini-reasoning-Hybrid",
                     fhir_url="https://localhost:8443", tier=2)
    assert isinstance(p, LemonadeAgenticProvider)
    assert p.tier == 2
    assert p.backend.base_url == "http://localhost:13305/api/v1"
