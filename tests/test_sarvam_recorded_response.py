from app.ai.providers import SarvamProvider

def test_parses_recorded_sarvam_chat_response():
    recorded={"id":"synthetic-response-id","choices":[{"message":{"role":"assistant","content":"{\"project_name\":\"Synthetic Site\",\"scope_summary\":\"Synthetic waterproofing\"}"}}]}
    assert SarvamProvider.extract_content(recorded) == "{\"project_name\":\"Synthetic Site\",\"scope_summary\":\"Synthetic waterproofing\"}"


def test_recorded_structured_quote_response_passes_pydantic():
    from app.schemas.models import AIQuoteExtraction
    recorded={
        "quote_date":"2026-11-20",
        "gst_basis":"extra",
        "gst_rate_percent":"18",
        "gst_page":2,
        "gst_evidence_snippet":"SYNTHETIC GST wording",
        "lines":[{
            "description":"Synthetic waterproofing item",
            "quantity":"100",
            "unit":"SQFT",
            "rate":"2.50",
            "amount_stated":"250.00",
            "page":1,
            "evidence_snippet":"SYNTHETIC quote row"
        }],
        "terms":[{
            "key":"tds",
            "text":"SYNTHETIC tax term",
            "page":2,
            "evidence_snippet":"SYNTHETIC term evidence"
        }]
    }
    parsed=AIQuoteExtraction.model_validate(recorded)
    assert parsed.lines[0].rate=="2.50"
    assert parsed.gst_basis=="extra"


def test_sarvam_document_ai_recorded_job_flow(monkeypatch):
    import asyncio
    import io
    import json
    import zipfile
    import httpx
    import app.ai.providers as providers

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("synthetic_document/metadata/page_001.json", json.dumps({
            "blocks": [{"text": "Synthetic quotation line"}]
        }))

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.calls = []
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, url, **kwargs):
            self.calls.append(("POST", url, kwargs))
            return httpx.Response(201, json={"job_id": "synthetic-job", "status": "pending"}, request=httpx.Request("POST", url))
        async def get(self, url, **kwargs):
            self.calls.append(("GET", url, kwargs))
            if url.endswith("/status"):
                return httpx.Response(200, json={"job_id": "synthetic-job", "status": "completed"}, request=httpx.Request("GET", url))
            if url.endswith("download-url"):
                return httpx.Response(200, json={"method": "GET", "url": "https://synthetic-download.invalid/file.zip"}, request=httpx.Request("GET", url))
            return httpx.Response(200, content=output.getvalue(), request=httpx.Request("GET", url))

    monkeypatch.setattr(providers, "SARVAM_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeAsyncClient)
    parsed = asyncio.run(providers.SarvamProvider().parse_document(b"synthetic pdf bytes", "synthetic_quote.pdf"))
    assert "[PAGE 1]" in parsed
    assert "Synthetic quotation line" in parsed
