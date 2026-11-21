"""Function signatures Member 3 implements and Member 2's services call. OWNER: Member 3."""
from __future__ import annotations

from app.schemas.comparisons import (
    ComparisonResponse,
    ShortlistResponse,
    ShortlistRules,
    UnitResolution,
)
from app.schemas.common import CommercialTerm
from app.schemas.quotations import QuotationResponse
from app.schemas.requirements import CodeSuggestion, RequirementItem
from app.schemas.rfq import RfqResponse


def erp_candidates(item: RequirementItem, catalogue: list[dict], limit: int = 5) -> list[CodeSuggestion]:
    """Deterministic lexical shortlist of ERP codes (+ near-duplicate warnings). The LLM may only
    re-rank/explain these candidates; it must never invent a code outside `catalogue`."""
    raise NotImplementedError


def build_comparison(
    rfq: RfqResponse,
    quotations: list[QuotationResponse],
    standard_terms: list[CommercialTerm],
    resolutions: list[UnitResolution],
) -> ComparisonResponse:
    """Normalise, compute amounts in Decimal, flag deviations. `comparison_id`/`created_at` are
    assigned by the caller's persistence layer or here, but must be stable once stored."""
    raise NotImplementedError


def apply_shortlist_rules(comparison: ComparisonResponse, rules: ShortlistRules) -> ShortlistResponse:
    """Rule-based shortlist with reasons and evidence. No LLM, no hidden weighting."""
    raise NotImplementedError
