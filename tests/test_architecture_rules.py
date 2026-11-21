"""Enforces the separation: extraction / normalisation / deterministic evaluation / human decision."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "backend" / "app"
IMPORT = re.compile(r"^\s*(?:from|import)\s+app\.(\w+)", re.M)


def _imports(pkg: str) -> set[str]:
    found: set[str] = set()
    for f in (APP / pkg).rglob("*.py"):
        found |= set(IMPORT.findall(f.read_text(encoding="utf-8")))
    return found


def test_procurement_is_pure_deterministic():
    assert not _imports("procurement") & {"ai", "document", "services", "api", "database"}


def test_document_does_not_use_ai_or_logic_layers():
    assert not _imports("document") & {"ai", "procurement", "services", "api"}


def test_ai_does_not_depend_on_domain_logic():
    assert not _imports("ai") & {"procurement", "document", "services", "api", "database"}


def test_schemas_depend_on_nothing_else():
    assert not _imports("schemas") - {"schemas"}


def test_api_only_calls_services_or_contract_layers():
    # Skeleton handlers touch core/database only for /health. Business logic must go through services.
    assert not _imports("api") & {"ai", "procurement", "document"}
