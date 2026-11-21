"""Quotation extraction schemas. OWNER: Member 2.

Values here are EXTRACTED, not evaluated. Totals are never computed on this object.
`amount_stated` is what the vendor wrote; the comparison step recomputes independently.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .common import AITrace, Flag, Quantity, SourceEvidence, StrictModel, TermKey


class QuotationLine(StrictModel):
    line_no: int | None = Field(default=None, description="Vendor's own line number if any")
    description: str
    quantity: Quantity | None = None
    rate: Decimal | None = None
    rate_unit: str | None = Field(default=None, description="Unit the rate is per, as written")
    amount_stated: Decimal | None = None
    evidence: SourceEvidence


class QuotationTerm(StrictModel):
    key: TermKey | Literal["other"]
    text: str
    evidence: SourceEvidence


class GstInfo(StrictModel):
    basis: Literal["extra", "inclusive", "unstated"]
    rate_percent: Decimal | None = None
    evidence: SourceEvidence | None = None


class QuotationResponse(StrictModel):
    quotation_id: str
    rfq_id: str
    vendor_name: str = Field(description="As typed by the user at upload; never inferred silently")
    source_file: str
    extraction_method: Literal["excel", "text_pdf", "scanned_pdf_ocr", "image_ocr", "cached_sample"]
    quote_date: date | None = None
    validity_text: str | None = None
    gst: GstInfo
    lines: list[QuotationLine]
    terms: list[QuotationTerm] = Field(default_factory=list)
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[Flag] = Field(default_factory=list)
    ai_trace: list[AITrace] = Field(default_factory=list)
