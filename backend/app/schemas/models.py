from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Literal, Optional
from decimal import Decimal

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Evidence(StrictModel):
    document: str
    page: int | None = None
    locator: str | None = None
    snippet: str | None = None

class Flag(StrictModel):
    code: str
    severity: Literal["info","warning","blocking"]
    message: str
    evidence: list[Evidence] = []

class AITrace(StrictModel):
    step: str
    provider: str
    model: str | None = None
    attempt: int = 1
    status: Literal["ok","repaired","fallback","cached","failed"]
    latency_ms: int | None = None
    error: str | None = None

class Quantity(StrictModel):
    value: Decimal
    unit: str

class RequirementItem(StrictModel):
    line_no: int
    description: str
    quantity: Quantity | None = None
    source: Evidence | None = None
    flags: list[Flag] = []

class IntakeResponse(StrictModel):
    requirement_id: str
    project_name: str | None = None
    scope_summary: str | None = None
    items: list[RequirementItem]
    note: dict | None = None
    warnings: list[str] = []
    ai_trace: list[AITrace] = []

class MatchRequest(StrictModel):
    requirement_id: str
    line_nos: list[int] | None = None

class MatchSuggestion(StrictModel):
    item_code: str
    description: str
    erp_unit: str | None = None
    confidence: float
    rationale: str
    near_duplicates: list[dict] = []

class MatchRow(StrictModel):
    line_no: int
    status: Literal["matched","ambiguous","unmatched"]
    suggestions: list[MatchSuggestion]
    confirmed_code: str | None = None
    flags: list[Flag] = []

class MatchResponse(StrictModel):
    requirement_id: str
    matches: list[MatchRow]
    ai_trace: list[AITrace] = []

class ConfirmMatchesRequest(StrictModel):
    requirement_id: str
    confirmed: list[dict]

class CommercialTerm(StrictModel):
    key: Literal["pf_esi_registration","tds","security_deposit","gst_extra","water_electricity_hutment","safety_ppe"]
    text: str = Field(min_length=1)

class ConfirmedItem(StrictModel):
    line_no: int = Field(gt=0)
    item_code: str = Field(min_length=1)

class RfqRequest(StrictModel):
    requirement_id: str
    confirmed_items: list[ConfirmedItem] = Field(min_length=1)
    response_due_date: str | None = None
    terms_override: list[CommercialTerm] | None = None

    @model_validator(mode="after")
    def validate_terms(self):
        if self.terms_override is not None:
            keys=[x.key for x in self.terms_override]
            expected={"pf_esi_registration","tds","security_deposit","gst_extra","water_electricity_hutment","safety_ppe"}
            if len(keys)!=6 or set(keys)!=expected:
                raise ValueError("terms_override must contain each of the six standard term keys exactly once")
        return self

class UnitResolution(StrictModel):
    quotation_id: str
    rfq_line_no: int = Field(gt=0)
    factor: Decimal = Field(gt=0)
    note: str = Field(min_length=3)
    resolved_by: str = Field(min_length=1)

class RfqResponse(StrictModel):
    rfq_id: str
    requirement_id: str
    subject: str
    body_text: str
    items: list[dict]
    terms: list[dict]
    response_due_date: str | None = None


class IntakeAIOutput(StrictModel):
    project_name: str
    scope_summary: str

class AIQuoteLine(StrictModel):
    description: str = Field(min_length=1)
    quantity: str | None = None
    unit: str | None = None
    rate: str | None = None
    amount_stated: str | None = None
    page: int | None = None
    evidence_snippet: str | None = None

class AIQuoteTerm(StrictModel):
    key: Literal["pf_esi_registration","tds","security_deposit","gst_extra","water_electricity_hutment","safety_ppe","other"]
    text: str = Field(min_length=1)
    page: int | None = None
    evidence_snippet: str | None = None

class AIQuoteExtraction(StrictModel):
    quote_date: str | None = None
    gst_basis: Literal["extra","inclusive","unstated"]
    gst_rate_percent: str | None = None
    gst_page: int | None = None
    gst_evidence_snippet: str | None = None
    lines: list[AIQuoteLine]
    terms: list[AIQuoteTerm] = []

class QuotationResponse(StrictModel):
    quotation_id: str
    rfq_id: str
    vendor_name: str
    source_file: str
    extraction_method: str
    quote_date: str | None = None
    validity_text: str | None = None
    gst: dict
    lines: list[dict]
    terms: list[dict]
    term_deviations: list[dict] = []
    extraction_confidence: float | None = None
    warnings: list[str] = []
    ai_trace: list[AITrace] = []

class ComparisonRequest(StrictModel):
    rfq_id: str
    quotation_ids: list[str] = Field(min_length=2, max_length=6)
    resolutions: list[UnitResolution] = []

class ComparisonResponse(StrictModel):
    comparison_id: str
    rfq_id: str
    created_at: str
    computed_by: Literal["deterministic"] = "deterministic"
    standard_terms: list[dict] = []
    rows: list[dict]
    vendors: list[dict]
    flags: list[Flag] = []

class ShortlistResponse(StrictModel):
    comparison_id: str
    rules_applied: dict = {}
    shortlist: list[dict]
    pending_review: list[dict]
    excluded: list[dict]
    decision_support_only: bool = True

class ApprovalRequest(StrictModel):
    decision: Literal["approve","override","reject_all"]
    selected_quotation_id: str | None = None
    approver_name: str = Field(min_length=1)
    note: str | None = None
    override_reason: str | None = None

class ApprovalResponse(StrictModel):
    approval_id: str
    comparison_id: str
    decision: str
    selected_quotation_id: str | None = None
    vendor_name: str | None = None
    is_override: bool
    approval_note: str
    approver_name: str
    decided_at: str


class ShortlistRules(StrictModel):
    max_vendors: int = Field(default=3, ge=1, le=4)
    exclude_on_blocking_flags: bool = True
    exclude_if_term_rejected: list[str] = []

class ShortlistRequest(StrictModel):
    rules: ShortlistRules = ShortlistRules()
