import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.llm.chat_backend import OllamaChatBackend, OpenAIChatBackend


# ---------------------------------------------------------------------------
# OllamaChatBackend
# ---------------------------------------------------------------------------

def _fake_ollama_response(content="", tool_calls=None):
    msg = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "message": msg,
        "prompt_eval_count": 11,
        "eval_count": 7,
        "total_duration": 2_000_000_000,  # 2s in ns
    }


def test_ollama_backend_normalizes_plain_message():
    backend = OllamaChatBackend(model="qwen3.5:9b")
    with patch("src.llm.chat_backend.ollama.chat",
               return_value=_fake_ollama_response(content="Condition?code=x")):
        msg = backend.chat([{"role": "user", "content": "hi"}], tools=[])
    assert msg["role"] == "assistant"
    assert msg["content"] == "Condition?code=x"
    assert msg.get("tool_calls", []) == []


def test_ollama_backend_synthesizes_tool_call_ids():
    raw_calls = [{"function": {"name": "fhir_search", "arguments": {"query": "Patient"}}}]
    backend = OllamaChatBackend(model="qwen3.5:9b")
    with patch("src.llm.chat_backend.ollama.chat",
               return_value=_fake_ollama_response(tool_calls=raw_calls)):
        msg = backend.chat([{"role": "user", "content": "hi"}], tools=[])
    assert len(msg["tool_calls"]) == 1
    tc = msg["tool_calls"][0]
    assert tc["id"]  # synthesized, non-empty
    assert tc["function"]["name"] == "fhir_search"
    assert tc["function"]["arguments"] == {"query": "Patient"}


def test_ollama_backend_run_metrics():
    backend = OllamaChatBackend(model="qwen3.5:9b")
    with patch("src.llm.chat_backend.ollama.chat",
               return_value=_fake_ollama_response(content="x")):
        backend.chat([{"role": "user", "content": "hi"}], tools=[])
    m = backend.get_run_metrics()
    assert m["provider_backend"] == "ollama"
    assert m["input_tokens"] == 11
    assert m["output_tokens"] == 7


# ---------------------------------------------------------------------------
# OpenAIChatBackend
# ---------------------------------------------------------------------------

def _fake_openai_response(content="", tool_calls=None):
    msg = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "choices": [{"message": msg, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 9},
        "decoding_speed_tps": 30.0,
        "prefill_duration_ttft": 0.47,
    }


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_openai_backend_normalizes_plain_message():
    backend = OpenAIChatBackend(model="Phi-4-mini-reasoning-Hybrid",
                                base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_FakeResp(_fake_openai_response(content="Patient?_id=1"))):
        msg = backend.chat([{"role": "user", "content": "hi"}], tools=[])
    assert msg["role"] == "assistant"
    assert msg["content"] == "Patient?_id=1"
    assert msg.get("tool_calls", []) == []


def test_openai_backend_parses_json_string_arguments():
    raw_calls = [{
        "id": "call_abc",
        "type": "function",
        "function": {"name": "fhir_search", "arguments": '{"query": "Patient"}'},
    }]
    backend = OpenAIChatBackend(model="Phi-4-mini-reasoning-Hybrid",
                                base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_FakeResp(_fake_openai_response(tool_calls=raw_calls))):
        msg = backend.chat([{"role": "user", "content": "hi"}], tools=[])
    tc = msg["tool_calls"][0]
    assert tc["id"] == "call_abc"
    assert tc["function"]["name"] == "fhir_search"
    assert tc["function"]["arguments"] == {"query": "Patient"}  # parsed from JSON string


def test_openai_backend_translates_tool_result_and_assistant_messages():
    """Outbound translation: tool messages keep tool_call_id, assistant tool_calls
    are emitted with arguments serialized back to a JSON string."""
    captured = {}

    def _capture(url, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResp(_fake_openai_response(content="done"))

    backend = OpenAIChatBackend(model="Phi-4-mini-reasoning-Hybrid",
                                base_url="http://localhost:13305/api/v1")
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "call_1", "function": {"name": "fhir_search",
                                                      "arguments": {"query": "Patient"}}}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "{\"total\": 3}"},
    ]
    with patch("src.llm.chat_backend.requests.post", side_effect=_capture):
        backend.chat(messages, tools=[])

    sent = captured["payload"]["messages"]
    assert sent[2]["role"] == "tool"
    assert sent[2]["tool_call_id"] == "call_1"
    assistant_tc = sent[1]["tool_calls"][0]
    assert assistant_tc["type"] == "function"
    assert assistant_tc["function"]["arguments"] == '{"query": "Patient"}'  # serialized


def test_openai_backend_run_metrics():
    backend = OpenAIChatBackend(model="Phi-4-mini-reasoning-Hybrid",
                                base_url="http://localhost:13305/api/v1")
    with patch("src.llm.chat_backend.requests.post",
               return_value=_FakeResp(_fake_openai_response(content="x"))):
        backend.chat([{"role": "user", "content": "hi"}], tools=[])
    m = backend.get_run_metrics()
    assert m["provider_backend"] == "lemonade"
    assert m["input_tokens"] == 20
    assert m["output_tokens"] == 9
    assert m["tokens_per_sec"] == 30.0
    assert m["ttft_sec"] == 0.47


def test_run_metadata_accepts_speed_fields():
    from src.api.models.evaluation import RunMetadata
    m = RunMetadata(provider_backend="lemonade", tokens_per_sec=29.6, ttft_sec=0.47)
    assert m.tokens_per_sec == 29.6
    assert m.ttft_sec == 0.47
    # Backward compatible: omitting them leaves them None
    assert RunMetadata().tokens_per_sec is None
