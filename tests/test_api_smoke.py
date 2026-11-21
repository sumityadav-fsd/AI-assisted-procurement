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

def test_real_amara_source_import_uses_company_documents():
    client=TestClient(app)
    response=client.post("/api/procurement/import/amara-tower-2")
    assert response.status_code==200, response.text
    data=response.json()
    assert "Amara" in data["requirement"]["project_name"]
    assert len(data["requirement"]["items"])==8
    assert data["matches"]["matches"]
    assert all(x["provider"] in {"sarvam", "deterministic-parser"} for x in data["matches"]["ai_trace"])


def test_synthetic_demo_endpoint_is_not_exposed():
    client=TestClient(app)
    assert client.post("/api/demo/load").status_code==404

