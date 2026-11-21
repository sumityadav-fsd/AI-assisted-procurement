"""Function signatures Member 3 implements and Member 2's services call. OWNER: Member 3."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.schemas.common import StrictModel
from app.schemas.requirements import RequirementItem


class ExtractedPage(StrictModel):
    page: int
    text: str
    method: Literal["text", "ocr"]
    ocr_confidence: float | None = None


class ExtractedDocument(StrictModel):
    source_file: str
    pages: list[ExtractedPage]
    tables: list[list[list[str]]] = []  # tables -> rows -> cells, as raw strings


def parse_boq_excel(path: Path) -> list[RequirementItem]:
    """Deterministically read a site BOQ/quantity sheet into RequirementItems. No LLM."""
    raise NotImplementedError


def extract_document(path: Path) -> ExtractedDocument:
    """Text/tables from a PDF (text layer, else OCR) or Excel quotation. No LLM."""
    raise NotImplementedError
