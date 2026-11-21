"""Requirement intake and ERP matching schemas. OWNER: Member 2."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import AITrace, Flag, Quantity, SourceEvidence, StrictModel


class RequirementItem(StrictModel):
    line_no: int = Field(ge=1)
    description: str
    quantity: Quantity | None = Field(
        default=None, description="Taken deterministically from the BOQ; null if UNKNOWN"
    )
    source: SourceEvidence
    flags: list[Flag] = Field(default_factory=list)


class NoteSummary(StrictModel):
    language: Literal["en", "hi", "bn"] | None = None
    original_text: str
    english_summary: str | None = None
    ai_generated: bool = True


class IntakeResponse(StrictModel):
    requirement_id: str
    project_name: str | None = None
    scope_summary: str | None = None
    items: list[RequirementItem]
    note: NoteSummary | None = None
    warnings: list[Flag] = Field(default_factory=list)
    ai_trace: list[AITrace] = Field(default_factory=list)


class MatchRequest(StrictModel):
    requirement_id: str
    line_nos: list[int] | None = Field(default=None, description="Null = all lines")


class NearDuplicate(StrictModel):
    item_code: str
    description: str
    similarity: float = Field(ge=0, le=1)


class CodeSuggestion(StrictModel):
    item_code: str
    description: str
    erp_unit: str | None = None
    confidence: float = Field(ge=0, le=1)
    rationale: str
    near_duplicates: list[NearDuplicate] = Field(default_factory=list)


class ItemMatch(StrictModel):
    line_no: int
    status: Literal["matched", "ambiguous", "unmatched"]
    suggestions: list[CodeSuggestion] = Field(default_factory=list, max_length=5)
    flags: list[Flag] = Field(default_factory=list)


class MatchResponse(StrictModel):
    requirement_id: str
    matches: list[ItemMatch]
    ai_trace: list[AITrace] = Field(default_factory=list)
