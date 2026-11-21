"""Skeleton-level contract tests. These prove ONLY that the contract layer works
(routing, validation, error envelope). They do not test any business logic: none exists yet."""
import pytest


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["ai"] == {
        "primary_configured": False,
        "fallback_configured": False,
        "cached_samples_enabled": False,
    }


def test_unknown_route_uses_error_envelope(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/requirements/match", {}),
        ("/api/rfq/generate", {"requirement_id": "r1", "confirmed_items": []}),
        ("/api/comparisons/generate", {"rfq_id": "x", "quotation_ids": ["only-one"]}),
        ("/api/approvals/c1", {"decision": "override", "selected_quotation_id": "q1", "approver_name": "A"}),
        ("/api/approvals/c1", {"decision": "approve", "approver_name": "A"}),
    ],
)
def test_invalid_json_requests_are_422_with_envelope(client, path, body):
    r = client.post(path, json=body)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["details"]


def test_multipart_endpoints_validate_required_fields(client):
    assert client.post("/api/requirements/intake", data={}).status_code == 422
    assert client.post("/api/quotations/upload", data={"rfq_id": "r"}).status_code == 422


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/requirements/match", {"requirement_id": "r1"}),
        ("/api/rfq/generate", {"requirement_id": "r1", "confirmed_items": [{"line_no": 1, "item_code": "X"}]}),
        ("/api/comparisons/generate", {"rfq_id": "r", "quotation_ids": ["a", "b"]}),
        ("/api/comparisons/c1/shortlist", {}),
        ("/api/approvals/c1", {"decision": "reject_all", "approver_name": "A"}),
    ],
)
def test_valid_requests_reach_unimplemented_handlers(client, path, body):
    r = client.post(path, json=body)
    assert r.status_code == 501
    assert r.json()["error"]["code"] == "NOT_IMPLEMENTED"
