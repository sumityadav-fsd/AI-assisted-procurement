"""Public-repository hygiene checks; private data directories are excluded."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAME = re.compile(
    r"(vinayak-vch3-data|\.zip$|\.db$|\.sqlite3?$|Quotation_|ERP_item_codes|"
    r"Contractor_list|Procurement_SOP|BOQ_Specification|_email_)", re.I
)
SECRET_LIKE = re.compile(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|api[_-]?key\s*=\s*['\"][^'\"]{12,})", re.I)
EXCLUDED_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "data_private", "uploads"}


def repo_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name.endswith((".pyc", ".sqlite", ".sqlite3", ".db")):
            continue
        yield path


def test_no_data_pack_or_env_files():
    bad = [str(path.relative_to(ROOT)) for path in repo_files() if FORBIDDEN_NAME.search(str(path.relative_to(ROOT)))]
    assert not bad, f"Forbidden files in repo: {bad}"


def test_fixtures_are_synthetic_and_text_only():
    fixtures = ROOT / "tests" / "fixtures"
    if not fixtures.exists():
        return
    for path in fixtures.rglob("*"):
        if path.is_file() and path.name != "README.md":
            assert path.name.startswith("synthetic_"), f"fixture must be named synthetic_*: {path.name}"
            assert not path.suffix.lower() in {".pdf", ".xlsx", ".xls", ".docx"}, "binary fixture needs review"


def test_no_obvious_secrets_in_text_files():
    for path in repo_files():
        if path.suffix.lower() in {".png", ".ico", ".svg"} or path.name in {"package-lock.json", "test_repo_hygiene.py"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert not SECRET_LIKE.search(content), f"secret-looking string in {path.relative_to(ROOT)}"
