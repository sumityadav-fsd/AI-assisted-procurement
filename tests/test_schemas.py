import pytest
from pydantic import ValidationError

from app.schemas.common import CommercialTerm, Quantity, TermKey
from app.schemas.comparisons import ApprovalRequest
from app.schemas.rfq import RfqRequest


def test_decimal_serialises_as_string():
    q = Quantity(value="12.50", unit="sqm")
    assert q.model_dump(mode="json") == {"value": "12.50", "unit": "sqm"}


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        Quantity(value="1", unit="m", extra="x")


def test_terms_override_requires_all_six_once():
    five = [CommercialTerm(key=k, text="t") for k in list(TermKey)[:5]]
    with pytest.raises(ValidationError):
        RfqRequest(requirement_id="r", confirmed_items=[{"line_no": 1, "item_code": "X"}], terms_override=five)
    six = [CommercialTerm(key=k, text="t") for k in TermKey]
    RfqRequest(requirement_id="r", confirmed_items=[{"line_no": 1, "item_code": "X"}], terms_override=six)


def test_override_needs_reason():
    with pytest.raises(ValidationError):
        ApprovalRequest(decision="override", selected_quotation_id="q", approver_name="A")
    ApprovalRequest(decision="override", selected_quotation_id="q", approver_name="A", override_reason="why")
