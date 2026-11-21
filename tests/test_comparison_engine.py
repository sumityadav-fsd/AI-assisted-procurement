from decimal import Decimal
from app.procurement.comparison import build_comparison

def fixture(unit="SQFT",qty="100",rate="2",amount="200",gst=None,terms=None):
    rfq={"rfq_id":"rfq_test","items":[{"line_no":1,"item_code":"SYN-1","description":"Synthetic item","quantity":"100","unit":"SQFT"}]}
    q={"quotation_id":"quo_test","rfq_id":"rfq_test","vendor_name":"Synthetic Vendor",
       "gst":gst or {"basis":"extra","rate_percent":"18"},
       "lines":[{"rfq_line_no":1,"description":"Synthetic item","quantity":qty,"unit":unit,"rate":rate,
                 "amount_stated":amount,"evidence":{"document":"synthetic_quote.pdf","page":1,"snippet":"synthetic row"}}],
       "term_deviations":terms or []}
    return rfq,q

def compare(rfq,q,resolutions=None):
    return build_comparison(rfq,[q],resolutions or [])

def test_matching_quantity_calculates_decimal_total():
    rfq,q=fixture()
    out=compare(rfq,q)
    vendor=out["vendors"][0]
    assert vendor["subtotal_comparable"]=="200.00"
    assert vendor["gst_amount"]=="36.00"
    assert vendor["total_incl_gst"]=="236.00"
    assert out["rows"][0]["cells"][0]["status"]=="comparable"

def test_unit_mismatch_requires_human_resolution():
    rfq,q=fixture(unit="SQM",qty="100",rate="2",amount="200")
    out=compare(rfq,q)
    assert out["rows"][0]["cells"][0]["status"]=="needs_review"
    assert out["rows"][0]["cells"][0]["amount_at_rfq_qty"] is None
    assert out["vendors"][0]["subtotal_comparable"] is None

def test_quantity_mismatch_requires_human_resolution():
    rfq,q=fixture(qty="90",amount="180")
    out=compare(rfq,q)
    assert out["rows"][0]["cells"][0]["status"]=="needs_review"
    assert out["vendors"][0]["total_incl_gst"] is None

def test_missing_gst_basis_means_unknown_total():
    rfq,q=fixture(gst={"basis":"unstated","rate_percent":None})
    out=compare(rfq,q)
    assert out["vendors"][0]["subtotal_comparable"]=="200.00"
    assert out["vendors"][0]["total_incl_gst"] is None
    assert any(f["code"]=="GST_UNSTATED" for f in out["vendors"][0]["flags"])

def test_arithmetic_mismatch_is_flagged():
    rfq,q=fixture(amount="199")
    out=compare(rfq,q)
    assert any(f["code"]=="ARITHMETIC_MISMATCH" for f in out["rows"][0]["cells"][0]["flags"])

def test_term_deviation_is_preserved_for_decision():
    deviation={"key":"security_deposit","status":"deviation","standard_text":"SAMPLE standard","vendor_text":"SAMPLE deviation","evidence":{"document":"synthetic_quote.pdf","page":2}}
    rfq,q=fixture(terms=[deviation])
    out=compare(rfq,q)
    assert out["vendors"][0]["term_deviations"][0]["status"]=="deviation"
    assert any(flag["code"]=="TERM_DEVIATION" for flag in out["vendors"][0]["flags"])

def test_human_unit_resolution_unlocks_comparison():
    rfq,q=fixture(unit="SQM",qty="100",rate="21.5278",amount="2152.78")
    resolution={"quotation_id":"quo_test","rfq_line_no":1,"factor":"10.7639","resolved_by":"Synthetic Reviewer","note":"Synthetic unit conversion checked"}
    out=compare(rfq,q,[resolution])
    assert out["rows"][0]["cells"][0]["status"]=="comparable"
    assert out["rows"][0]["cells"][0]["amount_at_rfq_qty"]=="200.00"
