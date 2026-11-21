"""HTTP routes. OWNER: Member 2.

Every endpoint here already enforces the request contract (FastAPI + Pydantic). Business logic
is NOT implemented yet: handlers raise NotImplementedYet (HTTP 501, standard error envelope).
Replace each `raise` with a call into app.services.* — keep handlers thin.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.core.config import APP_VERSION, load_settings
from app.core.errors import NotImplementedYet
from app.database.db import connect
from app.schemas.comparisons import (
    ApprovalRequest,
    ApprovalResponse,
    ComparisonRequest,
    ComparisonResponse,
    ShortlistRequest,
    ShortlistResponse,
)
from app.schemas.quotations import QuotationResponse
from app.schemas.requirements import IntakeResponse, MatchRequest, MatchResponse
from app.schemas.rfq import RfqRequest, RfqResponse

router = APIRouter(prefix="/api")


class AIStatus(BaseModel):
    primary_configured: bool
    fallback_configured: bool
    cached_samples_enabled: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: Literal["ok", "error"]
    ai: AIStatus


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    s = load_settings()
    try:
        conn = connect(s.database_path)
        conn.execute("SELECT 1")
        conn.close()
        db = "ok"
    except sqlite3.Error:
        db = "error"
    return HealthResponse(
        status="ok" if db == "ok" else "degraded",
        version=APP_VERSION,
        database=db,  # type: ignore[arg-type]
        ai=AIStatus(
            primary_configured=bool(s.sarvam_api_key),
            fallback_configured=bool(s.fallback_provider and s.fallback_api_key),
            cached_samples_enabled=s.ai_use_cached_samples,
        ),
    )


@router.post("/requirements/intake", response_model=IntakeResponse)
def intake(
    email_text: Annotated[str, Form(min_length=1)],
    boq_file: Annotated[UploadFile | None, File()] = None,
    note_text: Annotated[str | None, Form()] = None,
    note_language: Annotated[Literal["en", "hi", "bn"] | None, Form()] = None,
) -> IntakeResponse:
    raise NotImplementedYet("requirements/intake")


@router.post("/requirements/match", response_model=MatchResponse)
def match(body: MatchRequest) -> MatchResponse:
    raise NotImplementedYet("requirements/match")


@router.post("/rfq/generate", response_model=RfqResponse)
def rfq_generate(body: RfqRequest) -> RfqResponse:
    raise NotImplementedYet("rfq/generate")


@router.post("/quotations/upload", response_model=QuotationResponse)
def quotation_upload(
    rfq_id: Annotated[str, Form(min_length=1)],
    vendor_name: Annotated[str, Form(min_length=1)],
    file: Annotated[UploadFile, File()],
) -> QuotationResponse:
    raise NotImplementedYet("quotations/upload")


@router.post("/comparisons/generate", response_model=ComparisonResponse)
def comparison_generate(body: ComparisonRequest) -> ComparisonResponse:
    raise NotImplementedYet("comparisons/generate")


@router.post("/comparisons/{comparison_id}/shortlist", response_model=ShortlistResponse)
def shortlist(comparison_id: str, body: ShortlistRequest | None = None) -> ShortlistResponse:
    raise NotImplementedYet("comparisons/shortlist")


@router.post("/approvals/{comparison_id}", response_model=ApprovalResponse)
def approve(comparison_id: str, body: ApprovalRequest) -> ApprovalResponse:
    raise NotImplementedYet("approvals")
