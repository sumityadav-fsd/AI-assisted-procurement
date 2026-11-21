from pathlib import Path
import os

APP_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = APP_ROOT.parent
REPO_ROOT = BACKEND_ROOT.parent
APP_VERSION = "1.0.0-mvp"

# Minimal .env reader using only the standard library; process environment wins.
_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip().strip("\\\"'"))

def setting(name: str, default: str) -> str:
    return os.getenv(name, default)

def data_pack_dir() -> Path:
    # Real pack is expected under the gitignored data_private folder.
    return Path(setting("DATA_PACK_DIR", str(REPO_ROOT / "data_private" / "vinayak-vch3-data")))

def erp_catalogue_path() -> Path:
    return Path(setting(
        "ERP_CATALOGUE_PATH",
        str(data_pack_dir() / "04_item_codes" / "ERP_item_codes_waterproofing.xlsx"),
    ))

def upload_dir() -> Path:
    p = Path(setting("UPLOAD_DIR", str(BACKEND_ROOT / "data" / "uploads")))
    p.mkdir(parents=True, exist_ok=True)
    return p

def db_path() -> Path:
    p = Path(setting("DATABASE_PATH", str(BACKEND_ROOT / "data" / "procureai.sqlite3")))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

SARVAM_API_KEY = setting("SARVAM_API_KEY", "")
SARVAM_CHAT_URL = "https://api.sarvam.ai/v2/chat/completions"
SARVAM_MODEL = "sarvam-105b"
AI_TIMEOUT_SECONDS = float(setting("AI_TIMEOUT_SECONDS", "30"))
AI_USE_CACHED_SAMPLES = setting("AI_USE_CACHED_SAMPLES", "true").lower() in {"1","true","yes"}
AI_SAMPLES_DIR = Path(setting("AI_SAMPLES_DIR", str(REPO_ROOT / "data_private" / "ai_samples")))
MAX_UPLOAD_MB = int(setting("MAX_UPLOAD_MB", "20"))
