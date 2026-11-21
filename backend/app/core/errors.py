"""Uniform error envelope and exception handlers. OWNER: Member 2.

Every non-2xx response has the shape {"error": {"code", "message", "details", "request_id"}}.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorBody, ErrorDetail, ErrorResponse

log = logging.getLogger("procureai")


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: list[ErrorDetail] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    status_code, code = 404, "NOT_FOUND"


class ConflictError(AppError):
    status_code, code = 409, "CONFLICT_STATE"


class UnsupportedFileError(AppError):
    status_code, code = 415, "UNSUPPORTED_FILE_TYPE"


class FileTooLargeError(AppError):
    status_code, code = 413, "FILE_TOO_LARGE"


class ExtractionError(AppError):
    status_code, code = 422, "EXTRACTION_FAILED"


class AIProviderUnavailable(AppError):
    status_code, code = 502, "AI_PROVIDER_UNAVAILABLE"


class AIOutputInvalid(AppError):
    status_code, code = 502, "AI_OUTPUT_INVALID"


class NotImplementedYet(AppError):
    status_code, code = 501, "NOT_IMPLEMENTED"


def _response(status: int, code: str, message: str, details: list[ErrorDetail], rid: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details, request_id=rid))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _response(exc.status_code, exc.code, exc.message, exc.details, uuid.uuid4().hex[:12])

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(loc=".".join(str(p) for p in e["loc"]), msg=str(e["msg"])) for e in exc.errors()
        ]
        return _response(422, "VALIDATION_ERROR", "Request validation failed", details, uuid.uuid4().hex[:12])

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return _response(exc.status_code, code, str(exc.detail), [], uuid.uuid4().hex[:12])

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        rid = uuid.uuid4().hex[:12]
        log.exception("unhandled error request_id=%s", rid)
        return _response(500, "INTERNAL_ERROR", "Unexpected server error", [], rid)
