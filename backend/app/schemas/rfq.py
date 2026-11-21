"""RFQ generation schemas. OWNER: Member 2."""
from __future__ import annotations

from datetime import date

from pydantic import Field, field_validator

from .common import CommercialTerm, Quantity, StrictModel, _check_six_terms


class ConfirmedItem(StrictModel):
    line_no: int = Field(ge=1)
    item_code: str = Field(min_length=1)


class RfqRequest(StrictModel):
    requirement_id: str
    confirmed_items: list[ConfirmedItem] = Field(min_length=1)
    response_due_date: date | None = None
    terms_override: list[CommercialTerm] | None = Field(
        default=None, description="Optional full replacement of the six terms' wording"
    )

    @field_validator("terms_override")
    @classmethod
    def _six(cls, v: list[CommercialTerm] | None) -> list[CommercialTerm] | None:
        return None if v is None else _check_six_terms(v)


class RfqItem(StrictModel):
    line_no: int
    item_code: str
    description: str
    quantity: Quantity


class RfqResponse(StrictModel):
    rfq_id: str
    requirement_id: str
    subject: str
    body_text: str
    items: list[RfqItem]
    terms: list[CommercialTerm]
    response_due_date: date | None = None
