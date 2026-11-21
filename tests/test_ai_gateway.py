"""Gateway policy tests using FAKE providers (no network, no real AI)."""
import json

import pytest
from pydantic import BaseModel

from app.ai.gateway import Gateway, ProviderError
from app.core.errors import AIOutputInvalid, AIProviderUnavailable


class Out(BaseModel):
    n: int


class Fake:
    def __init__(self, name, responses):
        self.name, self.model, self._r, self.calls = name, "m", list(responses), 0

    def complete(self, system, user, timeout_s):
        self.calls += 1
        r = self._r.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_happy_path():
    p = Fake("primary", ['{"n": 1}'])
    out, tr = Gateway([p]).run_structured("s", "sys", "u", Out)
    assert out.n == 1 and [t.status for t in tr] == ["ok"]


def test_one_repair_then_success():
    p = Fake("primary", ['{"n": "x"}', '```json\n{"n": 2}\n```'])
    out, tr = Gateway([p]).run_structured("s", "sys", "u", Out)
    assert out.n == 2 and [t.status for t in tr] == ["failed", "repaired"] and p.calls == 2


def test_only_one_repair_attempt():
    p = Fake("primary", ["bad", "bad", "never-called"])
    with pytest.raises(AIOutputInvalid):
        Gateway([p]).run_structured("s", "sys", "u", Out)
    assert p.calls == 2


def test_provider_error_falls_back():
    a = Fake("primary", [ProviderError("timeout")])
    b = Fake("fallback", ['{"n": 3}'])
    out, tr = Gateway([a, b]).run_structured("s", "sys", "u", Out)
    assert out.n == 3 and [t.status for t in tr] == ["failed", "fallback"]


def test_no_providers_raises_unavailable():
    with pytest.raises(AIProviderUnavailable):
        Gateway([]).run_structured("s", "sys", "u", Out)


def test_cached_sample_used_without_calling_provider(tmp_path):
    (tmp_path / "k.json").write_text(json.dumps({"n": 9}))
    p = Fake("primary", [])
    out, tr = Gateway([p], samples_dir=str(tmp_path), use_cached_samples=True).run_structured(
        "s", "sys", "u", Out, sample_key="k"
    )
    assert out.n == 9 and tr[0].status == "cached" and p.calls == 0
