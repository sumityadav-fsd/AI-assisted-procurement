"""Concrete providers. OWNER: Member 2.

STATUS: NOT IMPLEMENTED. No provider call has been made or verified.
UNKNOWN: Sarvam's exact HTTP API (endpoint, auth header, JSON-mode support) and which
fallback provider the team will use. Implement with httpx against the real docs, then
add a recorded-response test. Until then the gateway has no providers and the UI will
show AI_PROVIDER_UNAVAILABLE unless AI_USE_CACHED_SAMPLES=true.
"""
from __future__ import annotations

from app.core.config import Settings

from .gateway import LLMProvider, ProviderError


class _Unimplemented:
    def __init__(self, name: str, model: str | None):
        self.name = name
        self.model = model

    def complete(self, system: str, user: str, timeout_s: float) -> str:
        raise ProviderError(f"{self.name} provider is not implemented yet")


def build_providers(settings: Settings) -> list[LLMProvider]:
    providers: list[LLMProvider] = []
    if settings.sarvam_api_key:
        providers.append(_Unimplemented("sarvam", settings.sarvam_model))  # TODO(Member 2)
    if settings.fallback_provider and settings.fallback_api_key:
        providers.append(_Unimplemented(settings.fallback_provider, settings.fallback_model))  # TODO(Member 2)
    return providers
