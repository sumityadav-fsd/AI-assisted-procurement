"""Shared schema primitives. OWNER: Member 2.

Conventions (see API_CONTRACT.md):
- Money and quantities are Decimal, serialised as JSON *strings* (never floats).
- Every model forbids unknown fields so AI/LLM output drift fails loudly.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TermKey(str, Enum):
    """The six standard commercial terms Vinayak attaches to every RFQ."""

    PF_ESI_REGISTRATION = "pf_esi_registration"
    TDS = "tds"
    SECURITY_DEPOSIT = "security_deposit"
    GST_EXTRA = "gst_extra"
    WATER_ELECTRICITY_HUTMENT = "water_electricity_hutment"
    SAFETY_PPE = "safety_ppe"


class FlagCode(str, Enum):
    QTY_MISMATCH = "QTY_MISMATCH"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    UNIT_UNKNOWN = "UNIT_UNKNOWN"
    MISSING_RATE = "MISSING_RATE"
    ITEM_NOT_QUOTED = "ITEM_NOT_QUOTED"
    EXTRA_ITEM_QUOTED = "EXTRA_ITEM_QUOTED"
    GST_UNSTATED = "GST_UNSTATED"
    TERM_DEVIATION = "TERM_DEVIATION"
    TERM_NOT_STATED = "TERM_NOT_STATED"
    ARITHMETIC_MISMATCH = "ARITHMETIC_MISMATCH"
    LOW_OCR_CONFIDENCE = "LOW_OCR_CONFIDENCE"
    LOW_MATCH_CONFIDENCE = "LOW_MATCH_CONFIDENCE"
    NEAR_DUPLICATE_CODE = "NEAR_DUPLICATE_CODE"
    UNRESOLVED_REVIEW = "UNRESOLVED_REVIEW"


class Quantity(StrictModel):
    value: Decimal
    unit: str = Field(min_length=1, description="Unit exactly as written in the source")


class SourceEvidence(StrictModel):
    """Pointer back to where a value came from. Required for every extracted value."""

    document: str = Field(description="Uploaded file name or logical source, e.g. 'email'")
    page: int | None = None
    locator: str | None = Field(default=None, description="e.g. 'Sheet1!C12' or 'line 14'")
    snippet: str | None = Field(default=None, max_length=500)


class Flag(StrictModel):
    code: FlagCode
    severity: Literal["info", "warning", "blocking"]
    message: str
    evidence: list[SourceEvidence] = Field(default_factory=list)


class AITrace(StrictModel):
    """One entry per AI call attempt. Always returned to the UI (Principle: visible traces)."""

    step: str
    provider: str
    model: str | None = None
    attempt: int = 1
    status: Literal["ok", "repaired", "fallback", "cached", "failed"]
    latency_ms: int | None = None
    error: str | None = None


class ErrorDetail(StrictModel):
    loc: str
    msg: str


class ErrorBody(StrictModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str | None = None


class ErrorResponse(StrictModel):
    error: ErrorBody


class CommercialTerm(StrictModel):
    key: TermKey
    text: str = Field(min_length=1)


def _check_six_terms(terms: list[CommercialTerm]) -> list[CommercialTerm]:
    keys = [t.key for t in terms]
    if len(keys) != len(set(keys)) or set(keys) != set(TermKey):
        raise ValueError("terms must contain each of the six standard TermKey values exactly once")
    return terms
