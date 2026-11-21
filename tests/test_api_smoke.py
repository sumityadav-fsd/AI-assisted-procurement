from fastapi.testclient import TestClient
from app.main import app

def test_health():
    client=TestClient(app)
    response=client.get("/api/health")
    assert response.status_code==200
    assert response.json()["status"]=="ok"

def test_root_serves_single_page_ui():
    client=TestClient(app)
    response=client.get("/")
    assert response.status_code==200
    assert "Vinayak ProcureAI" in response.text

def test_demo_load_runs_without_external_key():
    client=TestClient(app)
    response=client.post("/api/demo/load")
    assert response.status_code==200
    data=response.json()
    assert data["requirement"]["project_name"]=="Synthetic Residential Project"
    assert len(data["quotations"])==4
    assert data["quotations"][3]["extraction_method"]=="synthetic_scanned_ocr"
    assert any(flag["code"]=="LOW_OCR_CONFIDENCE" for flag in data["comparison"]["vendors"][3]["flags"])
    assert data["comparison"]["computed_by"]=="deterministic"

def test_demo_shortlist_and_human_approval():
    client=TestClient(app)
    demo=client.post("/api/demo/load").json()
    comparison_id=demo["comparison"]["comparison_id"]
    shortlist=client.post(f"/api/comparisons/{comparison_id}/shortlist",json={})
    assert shortlist.status_code==200
    selected=shortlist.json()["shortlist"][0]["quotation_id"]
    approval=client.post(f"/api/approvals/{comparison_id}",json={
        "decision":"approve","selected_quotation_id":selected,"approver_name":"Synthetic Approver"
    })
    assert approval.status_code==200
    assert approval.json()["decision"]=="approve"


def test_errors_use_standard_envelope():
    client=TestClient(app)
    missing=client.get("/not-a-route")
    assert missing.status_code==404
    assert set(missing.json()["error"])=={"code","message","details","request_id"}
    invalid=client.post("/api/comparisons/generate",json={"rfq_id":"rfq_x","quotation_ids":["only-one"]})
    assert invalid.status_code==422
    assert invalid.json()["error"]["code"]=="VALIDATION_ERROR"


def test_complete_synthetic_upload_flow(monkeypatch, tmp_path):
    import io
    import openpyxl

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "flow.sqlite3"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    catalogue = tmp_path / "synthetic_catalogue.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Item Code", "Description", "Unit"])
    ws.append(["SYN-ITEM-1", "Synthetic waterproofing floor", "SQFT"])
    wb.save(catalogue)
    monkeypatch.setenv("ERP_CATALOGUE_PATH", str(catalogue))

    def workbook(rows):
        output = io.BytesIO()
        book = openpyxl.Workbook()
        sheet = book.active
        for row in rows:
            sheet.append(row)
        book.save(output)
        return output.getvalue()

    boq = workbook([
        ["Description", "Quantity", "Unit"],
        ["Synthetic waterproofing floor", 5, "SQFT"],
    ])
    quote_a = workbook([
        ["Item Description", "Quantity", "Unit", "Rate", "Amount"],
        ["Synthetic waterproofing floor", 5, "SQFT", 10, 50],
        ["GST extra @ 18%"],
    ])
    quote_b = workbook([
        ["Item Description", "Quantity", "Unit", "Rate", "Amount"],
        ["Synthetic waterproofing floor", 5, "SQFT", 11, 55],
        ["GST extra @ 18%"],
    ])

    client = TestClient(app)
    intake = client.post("/api/requirements/intake", data={"email_text": "Synthetic site requirement"},
                         files={"boq_file": ("synthetic_boq.xlsx", boq, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert intake.status_code == 200, intake.text
    req = intake.json()
    assert req["items"][0]["quantity"] == {"value": "5", "unit": "SQFT"}

    match = client.post("/api/requirements/match", json={"requirement_id": req["requirement_id"]})
    assert match.status_code == 200
    code = match.json()["matches"][0]["suggestions"][0]["item_code"]

    rfq = client.post("/api/rfq/generate", json={"requirement_id": req["requirement_id"],
                     "confirmed_items": [{"line_no": 1, "item_code": code}]})
    assert rfq.status_code == 200
    rfq_id = rfq.json()["rfq_id"]

    uploaded = []
    for vendor, content in [("Synthetic Vendor A", quote_a), ("Synthetic Vendor B", quote_b)]:
        response = client.post("/api/quotations/upload", data={"rfq_id": rfq_id, "vendor_name": vendor},
            files={"file": ("synthetic_quote.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert response.status_code == 200, response.text
        uploaded.append(response.json())
    assert uploaded[0]["lines"][0]["rate"] == "10"
    assert uploaded[0]["lines"][0]["amount_stated"] == "50"

    comparison = client.post("/api/comparisons/generate", json={"rfq_id": rfq_id,
        "quotation_ids": [q["quotation_id"] for q in uploaded]})
    assert comparison.status_code == 200, comparison.text
    cmp = comparison.json()
    assert cmp["computed_by"] == "deterministic"
    assert cmp["vendors"][0]["total_incl_gst"] == "59.00"

    shortlist = client.post(f"/api/comparisons/{cmp['comparison_id']}/shortlist", json={})
    assert shortlist.status_code == 200
    selected = shortlist.json()["shortlist"][0]["quotation_id"]
    approval = client.post(f"/api/approvals/{cmp['comparison_id']}", json={
        "decision": "approve", "selected_quotation_id": selected, "approver_name": "Synthetic Reviewer"
    })
    assert approval.status_code == 200
    assert approval.json()["decision"] == "approve"
