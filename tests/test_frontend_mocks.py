"""Frontend mock JSON must validate against the backend schemas, so mock-driven UI work cannot drift
from the real contract. Mocks are SYNTHETIC."""
import json
from pathlib import Path

import pytest

from app.schemas.common import ErrorResponse
from app.schemas.comparisons import ApprovalResponse, ComparisonResponse, ShortlistResponse
from app.schemas.quotations import QuotationResponse
from app.schemas.requirements import IntakeResponse, MatchResponse
from app.schemas.rfq import RfqResponse

MOCKS = Path(__file__).resolve().parents[1] / "frontend" / "src" / "mocks"
CASES = {
    "intake": IntakeResponse, "match": MatchResponse, "rfq": RfqResponse, "quotation": QuotationResponse,
    "comparison": ComparisonResponse, "shortlist": ShortlistResponse, "approval": ApprovalResponse,
    "error": ErrorResponse,
}


@pytest.mark.parametrize("name,model", CASES.items())
def test_mock_matches_schema(name, model):
    model.model_validate(json.loads((MOCKS / f"{name}.json").read_text()))
