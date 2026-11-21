"""Guards the 'no real company data / secrets in the public repo' rule for tracked + staged files."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAME = re.compile(
    r"(vinayak-vch3-data|\.zip$|\.db$|\.sqlite3?$|(^|/)\.env$|Quotation_|ERP_item_codes|"
    r"Contractor_list|Procurement_SOP|BOQ_Specification|_email_)",
    re.I,
)
ALLOWED_BINARY = re.compile(r"\.(png|ico|svg)$", re.I)
SECRET_LIKE = re.compile(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|api[_-]?key\s*=\s*['\"][^'\"]{12,})", re.I)


def _files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    return [f for f in out if f and (ROOT / f).is_file()]


def test_no_data_pack_or_env_files():
    bad = [f for f in _files() if FORBIDDEN_NAME.search(f)]
    assert not bad, f"Forbidden files in repo: {bad}"


def test_fixtures_are_synthetic_and_text_only():
    for f in _files():
        if f.startswith("tests/fixtures/") and not f.endswith("README.md"):
            assert Path(f).name.startswith("synthetic_"), f"fixture must be named synthetic_*: {f}"
            assert not f.lower().endswith((".pdf", ".xlsx", ".xls", ".docx")), f"binary fixture needs review: {f}"


def test_no_obvious_secrets_in_text_files():
    for f in _files():
        if ALLOWED_BINARY.search(f) or f.endswith(("package-lock.json", "test_repo_hygiene.py")):
            continue
        try:
            text = (ROOT / f).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert not SECRET_LIKE.search(text), f"secret-looking string in {f}"
