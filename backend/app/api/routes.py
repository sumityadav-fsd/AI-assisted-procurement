from fastapi import APIRouter, UploadFile, File, Form
import os
from app.core.config import MAX_UPLOAD_MB
from app.core.errors import AppError
from app.schemas.models import (
    IntakeResponse, MatchRequest, MatchResponse, RfqRequest, RfqResponse,
    QuotationResponse, ComparisonRequest, ComparisonResponse, ShortlistRequest,
    ShortlistResponse, ApprovalRequest, ApprovalResponse,
)
from app.services import pipeline

router=APIRouter(prefix="/api")

@router.get("/health")
def health():
    return pipeline.health_status()

@router.post("/requirements/intake", response_model=IntakeResponse)
async def requirement_intake(email_text: str=Form(...), boq_file: UploadFile|None=File(None),
                             note_text: str|None=Form(None), note_language: str|None=Form(None)):
    path=None
    if boq_file:
        if not (boq_file.filename or "").lower().endswith(".xlsx"):
            raise AppError("UNSUPPORTED_FILE_TYPE","BOQ must be .xlsx",415)
        content=await boq_file.read()
        if len(content)>MAX_UPLOAD_MB*1024*1024:
            raise AppError("FILE_TOO_LARGE","Upload exceeds configured limit",413)
        path=pipeline.store_boq_upload(content)
    return await pipeline.intake(email_text,path,note_text,note_language)

@router.post("/requirements/match", response_model=MatchResponse)
async def requirement_match(body: MatchRequest):
    result=await pipeline.match_requirement(body.requirement_id,body.line_nos)
    if not result:
        raise AppError("NOT_FOUND","Requirement not found",404)
    return result

@router.post("/rfq/generate", response_model=RfqResponse)
async def rfq_generate(body: RfqRequest):
    result=await pipeline.generate_rfq(body)
    if not result:
        raise AppError("NOT_FOUND","Requirement not found",404)
    if result.get("error"):
        raise AppError("MATCH_CONFIRMATION_REQUIRED",result["error"],422)
    return result

@router.post("/quotations/upload", response_model=QuotationResponse)
async def quotations_upload(rfq_id: str=Form(...), vendor_name: str=Form(...), file: UploadFile=File(...)):
    content=await file.read()
    if len(content)>MAX_UPLOAD_MB*1024*1024:
        raise AppError("FILE_TOO_LARGE","Upload exceeds configured limit",413)
    result=await pipeline.upload_quotation(rfq_id,vendor_name,file.filename or "quotation",content)
    if not result:
        raise AppError("NOT_FOUND","RFQ not found",404)
    if result.get("error"):
        raise AppError("UNSUPPORTED_FILE_TYPE",result["error"],415)
    return result

@router.post("/comparisons/generate", response_model=ComparisonResponse)
def comparisons_generate(body: ComparisonRequest):
    return pipeline.generate_comparison_for_ids(body.rfq_id,body.quotation_ids,body.resolutions)

@router.post("/comparisons/{comparison_id}/shortlist", response_model=ShortlistResponse)
async def comparisons_shortlist(comparison_id: str, body: ShortlistRequest|None=None):
    result=await pipeline.shortlist(comparison_id,body.rules.model_dump() if body else None)
    if not result:
        raise AppError("NOT_FOUND","Comparison not found",404)
    return result

@router.post("/approvals/{comparison_id}", response_model=ApprovalResponse)
def approvals(comparison_id: str, body: ApprovalRequest):
    return pipeline.create_approval(comparison_id,body)

@router.post("/procurement/import/amara-tower-2")
async def import_amara_requirement():
    try:
        return await pipeline.load_real_sample()
    except FileNotFoundError as exc:
        raise AppError("DATA_PACK_MISSING", str(exc), 500)
