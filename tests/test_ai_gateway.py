import asyncio

from app.ai.gateway import AIGateway


class RecordingProvider:
    name = "sarvam"
    model = "sarvam-105b"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def complete(self, messages, schema=None):
        self.calls += 1
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def test_gateway_retries_provider_once_then_validates():
    provider = RecordingProvider([TimeoutError("synthetic timeout"), '{"value":"recovered"}'])
    result, traces = asyncio.run(AIGateway(provider).structured(
        "synthetic_step", "synthetic prompt", {},
        lambda value: value if isinstance(value.get("value"), str) else (_ for _ in ()).throw(ValueError()),
        lambda: {"value": "deterministic"},
    ))
    assert result == {"value": "recovered"}
    assert provider.calls == 2
    assert traces[-1].status == "repaired"
    assert traces[-1].attempt == 2


def test_gateway_uses_deterministic_fallback_after_one_failed_retry():
    provider = RecordingProvider([TimeoutError("synthetic timeout"), TimeoutError("synthetic retry timeout")])
    result, traces = asyncio.run(AIGateway(provider).structured(
        "synthetic_step", "synthetic prompt", {}, lambda value: value,
        lambda: {"value": "synthetic deterministic result"},
    ))
    assert result["value"] == "synthetic deterministic result"
    assert provider.calls == 2
    assert traces[-1].provider == "deterministic-parser"
    assert traces[-1].status == "fallback"


def test_gateway_does_not_persist_or_replay_cached_model_outputs_by_default(tmp_path, monkeypatch):
    import app.ai.gateway as gateway_module

    monkeypatch.setattr(gateway_module, "AI_SAMPLES_DIR", tmp_path)
    monkeypatch.setattr(gateway_module, "AI_USE_CACHED_SAMPLES", False)
    provider = RecordingProvider(['{"value":"live model result"}'])
    first, first_trace = asyncio.run(AIGateway(provider).structured(
        "real_procurement_step", "real source-backed prompt", {}, lambda value: value,
        lambda: {"value": "deterministic fallback"},
    ))
    assert first["value"] == "live model result"
    assert first_trace[0].status == "ok"
    assert not list(tmp_path.glob("*.json"))

    offline = RecordingProvider([TimeoutError("offline"), TimeoutError("retry offline")])
    second, second_trace = asyncio.run(AIGateway(offline).structured(
        "real_procurement_step", "real source-backed prompt", {}, lambda value: value,
        lambda: {"value": "deterministic fallback"},
    ))
    assert second["value"] == "deterministic fallback"
    assert second_trace[-1].status == "fallback"
