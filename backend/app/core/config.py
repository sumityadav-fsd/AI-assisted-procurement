"""Environment-driven settings. OWNER: Member 2. No secrets are ever hard-coded."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_VERSION = "0.1.0-skeleton"


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_path: str
    upload_dir: str
    max_upload_mb: int
    cors_origins: list[str]
    frontend_dist: str
    ai_timeout_seconds: float
    ai_use_cached_samples: bool
    ai_samples_dir: str
    sarvam_api_key: str | None
    sarvam_base_url: str | None
    sarvam_model: str | None
    fallback_provider: str | None
    fallback_api_key: str | None
    fallback_base_url: str | None
    fallback_model: str | None


def load_settings() -> Settings:
    root = Path(__file__).resolve().parents[2]  # backend/
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_path=os.getenv("DATABASE_PATH", str(root / "data" / "procureai.db")),
        upload_dir=os.getenv("UPLOAD_DIR", str(root / "data" / "uploads")),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "15")),
        cors_origins=[o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o],
        frontend_dist=os.getenv("FRONTEND_DIST", str(root.parent / "frontend" / "dist")),
        ai_timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "30")),
        ai_use_cached_samples=_bool("AI_USE_CACHED_SAMPLES", False),
        ai_samples_dir=os.getenv("AI_SAMPLES_DIR", str(root / "app" / "ai" / "samples")),
        sarvam_api_key=os.getenv("SARVAM_API_KEY") or None,
        sarvam_base_url=os.getenv("SARVAM_BASE_URL") or None,
        sarvam_model=os.getenv("SARVAM_MODEL") or None,
        fallback_provider=os.getenv("FALLBACK_AI_PROVIDER") or None,
        fallback_api_key=os.getenv("FALLBACK_AI_API_KEY") or None,
        fallback_base_url=os.getenv("FALLBACK_AI_BASE_URL") or None,
        fallback_model=os.getenv("FALLBACK_AI_MODEL") or None,
    )
