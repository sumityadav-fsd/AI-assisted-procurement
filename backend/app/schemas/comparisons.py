"""Comparative statement, shortlist and approval schemas. OWNER: Member 2.

All numbers in these objects are produced by deterministic Decimal code in
backend/app/procurement/ (Member 3). No LLM output reaches these fields.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from .common import CommercialTerm, Flag, Quantity, SourceEvidence, StrictModel, TermKey


class UnitResolution(StrictModel):
    """Human-supplied resolution of a quantity/unit mismatch. The ONLY way a mismatch is resolved."""

    quotation_id: str
    rfq_line_no: int
    factor: Decimal = Field(gt=0, description="quoted_quantity * factor = RFQ-unit quantity")
    note: str = Field(min_length=1)
    resolved_by: str = Field(min_length=1)


class ComparisonRequest(StrictModel):
    rfq_id: str
    quotation_ids: list[str] = Field(min_length=2, max_length=6)
    resolutions: list[UnitResolution] = Field(default_factory=list)


class VendorCell(StrictModel):
    quotation_id: str
    vendor_name: str
    status: Literal["comparable", "needs_review", "not_quoted"]
    quoted_quantity: Quantity | None = None
    rate: Decimal | None = None
    amount_at_rfq_qty: Decimal | None = Field(
        default=None, description="rfq_quantity x rate. Null unless status == comparable"
    )
    amount_stated_by_vendor: Decimal | None = None
    flags: list[Flag] = Field(default_factory=list)
    evidence: list[SourceEvidence] = Field(default_factory=list)


class ComparisonRow(StrictModel):
    rfq_line_no: int
    item_code: str
    description: str
    rfq_quantity: Quantity
    cells: list[VendorCell]


class TermDeviation(StrictModel):
    key: TermKey
    status: Literal["accepted", "deviation", "not_stated"]
    standard_text: str
    vendor_text: str | None = None
    evidence: SourceEvidence | None = None


class VendorSummary(StrictModel):
    quotation_id: str
    vendor_name: str
    subtotal_comparable: Decimal | None = None
    gst_basis: Literal["extra", "inclusive", "unstated"]
    gst_rate_percent: Decimal | None = None
    gst_amount: Decimal | None = None
    total_incl_gst: Decimal | None = Field(
        default=None, description="Null when GST is unstated: UNKNOWN is never guessed"
    )
    lines_comparable: int
    lines_needs_review: int
    lines_not_quoted: int
    term_deviations: list[TermDeviation]
    flags: list[Flag] = Field(default_factory=list)


class ComparisonResponse(StrictModel):
    comparison_id: str
    rfq_id: str
    created_at: datetime
    computed_by: Literal["deterministic"] = "deterministic"
    standard_terms: list[CommercialTerm]
    rows: list[ComparisonRow]
    vendors: list[VendorSummary]
    flags: list[Flag] = Field(default_factory=list)


class ShortlistRules(StrictModel):
    max_vendors: int = Field(default=3, ge=1, le=4)
    exclude_on_blocking_flags: bool = True
    exclude_if_term_rejected: list[TermKey] = Field(default_factory=list)


class ShortlistRequest(StrictModel):
    rules: ShortlistRules = Field(default_factory=ShortlistRules)


class Reason(StrictModel):
    text: str
    evidence: list[SourceEvidence] = Field(default_factory=list)


class ShortlistEntry(StrictModel):
    rank: int = Field(ge=1)
    quotation_id: str
    vendor_name: str
    total_incl_gst: Decimal
    reasons: list[Reason]
    caveats: list[Flag] = Field(default_factory=list)


class VendorNote(StrictModel):
    quotation_id: str
    vendor_name: str
    reasons: list[Reason]


class ShortlistResponse(StrictModel):
    comparison_id: str
    rules_applied: ShortlistRules
    shortlist: list[ShortlistEntry]
    pending_review: list[VendorNote] = Field(
        default_factory=list, description="Vendors with unresolved lines or unstated GST: not ranked"
    )
    excluded: list[VendorNote] = Field(default_factory=list)
    decision_support_only: Literal[True] = True


class ApprovalRequest(StrictModel):
    decision: Literal["approve", "override", "reject_all"]
    selected_quotation_id: str | None = None
    approver_name: str = Field(min_length=1, description="Free text; no authentication in MVP")
    note: str | None = None
    override_reason: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> "ApprovalRequest":
        if self.decision == "reject_all":
            if self.selected_quotation_id is not None:
                raise ValueError("selected_quotation_id must be null for reject_all")
        elif not self.selected_quotation_id:
            raise ValueError("selected_quotation_id is required for approve/override")
        if self.decision == "override" and not (self.override_reason or "").strip():
            raise ValueError("override_reason is required for override")
        return self


class ApprovalResponse(StrictModel):
    approval_id: str
    comparison_id: str
    decision: Literal["approve", "override", "reject_all"]
    selected_quotation_id: str | None = None
    vendor_name: str | None = None
    is_override: bool
    approval_note: str = Field(description="Template-generated from stored facts; not LLM text")
    approver_name: str
    decided_at: datetime
