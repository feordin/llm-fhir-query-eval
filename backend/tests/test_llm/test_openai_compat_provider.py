"""Reconciliation coverage: the openai-compat provider wiring and the
lean-prompt port onto the (Foundry-based) AgenticProvider.

Construction only -- no live endpoint. The OpenAI SDK client is lazy, so
building these providers issues no network calls.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.llm import get_provider
from src.llm.agentic_provider import (
    AGENTIC_SYSTEM_PROMPT, LEAN_AGENTIC_SYSTEM_PROMPT,
    OpenAICompatAgenticProvider,
)
from src.llm.openai_chat_provider import OpenAIChatProvider


def test_factory_openai_compat_tier1_is_closed_book():
    p = get_provider("openai-compat", model="Qwen3-8B-Hybrid",
                     base_url="http://localhost:13305/api/v1")
    assert isinstance(p, OpenAIChatProvider)
    assert p.model == "Qwen3-8B-Hybrid"


def test_factory_openai_compat_agentic_defaults_to_full_prompt():
    """A frontier model on an OpenAI-compatible endpoint (e.g. Azure OpenAI)
    keeps the full prompt unless lean is explicitly requested."""
    p = get_provider("openai-compat", model="gpt-4", base_url="http://x",
                     fhir_url="https://x", tier=2)
    assert isinstance(p, OpenAICompatAgenticProvider)
    assert p._agentic_prompt == AGENTIC_SYSTEM_PROMPT
    assert p.tier == 2


def test_factory_openai_compat_agentic_lean_prompt_opt_in():
    """Small local models (Lemonade Qwen3-8B) opt into the lean prompt."""
    p = get_provider("openai-compat", model="Qwen3-8B-Hybrid", base_url="http://x",
                     fhir_url="https://x", tier=2, lean_prompt=True)
    assert isinstance(p, OpenAICompatAgenticProvider)
    assert p._agentic_prompt == LEAN_AGENTIC_SYSTEM_PROMPT
    assert p._agentic_prompt_version == "0.1.0"


def test_ollama_agentic_still_uses_full_prompt():
    """Regression: the Ollama path is untouched by the lean-prompt port."""
    p = get_provider("ollama-agentic", model="qwen3.5:9b", fhir_url="https://x", tier=2)
    assert p._agentic_prompt == AGENTIC_SYSTEM_PROMPT
