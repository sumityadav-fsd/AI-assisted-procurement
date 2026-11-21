"""LLM gateway: the ONLY place AI providers are called. OWNER: Member 2.

Policy implemented here (and tested in tests/test_ai_gateway.py with fake providers):
  1. If cached samples are enabled and a sample exists for `sample_key`, return it (trace: cached).
  2. For each provider in order (primary, then fallback):
       - call with a hard timeout (provider's job)
       - validate output against the Pydantic model
       - on invalid output: ONE repair attempt that shows the validation error to the model
       - on provider error/timeout: move to the next provider (trace: failed, then fallback)
  3. If everything fails: raise AIProviderUnavailable / AIOutputInvalid. Never fabricate output.

Callers receive (validated_model, traces). Traces must be forwarded to the API response.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.errors import AIOutputInvalid, AIProviderUnavailable
from app.schemas.common import AITrace

T = TypeVar("T", bound=BaseModel)


class ProviderError(Exception):
    """Network error, timeout, auth failure or non-2xx from a provider."""


class LLMProvider(Protocol):
    name: str
    model: str | None

    def complete(self, system: str, user: str, timeout_s: float) -> str:
        """Return the raw model text (expected to be JSON). Raise ProviderError on failure."""
        ...


class Gateway:
    def __init__(
        self,
        providers: list[LLMProvider],
        timeout_s: float = 30.0,
        samples_dir: str | None = None,
        use_cached_samples: bool = False,
    ):
        self.providers = providers
        self.timeout_s = timeout_s
        self.samples_dir = Path(samples_dir) if samples_dir else None
        self.use_cached_samples = use_cached_samples

    def run_structured(
        self, step: str, system: str, user: str, model_cls: type[T], sample_key: str | None = None
    ) -> tuple[T, list[AITrace]]:
        traces: list[AITrace] = []

        cached = self._load_sample(sample_key, model_cls)
        if cached is not None:
            traces.append(AITrace(step=step, provider="cache", status="cached"))
            return cached, traces

        last_invalid: str | None = None
        for idx, provider in enumerate(self.providers):
            ok_status = "ok" if idx == 0 else "fallback"
            prompt = user
            for attempt in (1, 2):
                started = time.monotonic()
                try:
                    raw = provider.complete(system, prompt, self.timeout_s)
                except ProviderError as exc:
                    traces.append(self._trace(step, provider, attempt, "failed", started, str(exc)))
                    break  # provider down -> next provider, no repair attempt
                try:
                    parsed = model_cls.model_validate(json.loads(_strip_fences(raw)))
                except (ValidationError, ValueError) as exc:
                    last_invalid = str(exc)[:500]
                    traces.append(self._trace(step, provider, attempt, "failed", started, last_invalid))
                    prompt = (
                        f"{user}\n\nYour previous output was invalid:\n{last_invalid}\n"
                        "Return corrected JSON only."
                    )
                    continue
                status = ok_status if attempt == 1 else "repaired"
                traces.append(self._trace(step, provider, attempt, status, started, None))
                return parsed, traces

        if last_invalid is not None:
            raise AIOutputInvalid(f"AI output failed validation for step '{step}': {last_invalid}")
        raise AIProviderUnavailable(f"No AI provider available for step '{step}'")

    def _load_sample(self, key: str | None, model_cls: type[T]) -> T | None:
        if not (self.use_cached_samples and key and self.samples_dir):
            return None
        path = self.samples_dir / f"{key}.json"
        if not path.is_file():
            return None
        return model_cls.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _trace(step: str, p: LLMProvider, attempt: int, status: str, started: float, error: str | None) -> AITrace:
        return AITrace(
            step=step,
            provider=p.name,
            model=p.model,
            attempt=attempt,
            status=status,  # type: ignore[arg-type]
            latency_ms=int((time.monotonic() - started) * 1000),
            error=error,
        )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()
