import pytest
from pydantic import ValidationError
from app.schemas.models import RfqRequest, UnitResolution

TERMS=[
    {"key":"pf_esi_registration","text":"SYNTHETIC term A"},
    {"key":"tds","text":"SYNTHETIC term B"},
    {"key":"security_deposit","text":"SYNTHETIC term C"},
    {"key":"gst_extra","text":"SYNTHETIC term D"},
    {"key":"water_electricity_hutment","text":"SYNTHETIC term E"},
    {"key":"safety_ppe","text":"SYNTHETIC term F"},
]

def test_rfq_override_requires_all_six_unique_terms():
    RfqRequest(requirement_id="req_synthetic",confirmed_items=[{"line_no":1,"item_code":"SYN-1"}],terms_override=TERMS)
    with pytest.raises(ValidationError):
        RfqRequest(requirement_id="req_synthetic",confirmed_items=[{"line_no":1,"item_code":"SYN-1"}],terms_override=TERMS[:5])

def test_unit_resolution_requires_positive_factor_and_reason():
    UnitResolution(quotation_id="quo_synthetic",rfq_line_no=1,factor="1",note="Human checked",resolved_by="Reviewer")
    with pytest.raises(ValidationError):
        UnitResolution(quotation_id="quo_synthetic",rfq_line_no=1,factor="0",note="No factor",resolved_by="Reviewer")
