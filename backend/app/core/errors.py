from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from uuid import uuid4

class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details=None):
        self.code, self.message, self.status, self.details = code, message, status, details or []

def _request_id(request):
    return getattr(request.state,"request_id",str(uuid4()))

async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status, content={"error":{
        "code":exc.code,"message":exc.message,"details":exc.details,"request_id":_request_id(request)
    }})

async def validation_error_handler(request: Request, exc):
    return JSONResponse(status_code=422, content={"error":{
        "code":"VALIDATION_ERROR","message":"Request validation failed",
        "details":[{"loc":".".join(map(str,e["loc"])),"msg":e["msg"]} for e in exc.errors()],
        "request_id":_request_id(request)
    }})

async def http_error_handler(request: Request, exc: StarletteHTTPException):
    code="NOT_FOUND" if exc.status_code==404 else ("METHOD_NOT_ALLOWED" if exc.status_code==405 else "HTTP_ERROR")
    return JSONResponse(status_code=exc.status_code,content={"error":{
        "code":code,"message":str(exc.detail),"details":[],"request_id":_request_id(request)
    }})

async def generic_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error":{
        "code":"INTERNAL_ERROR","message":"Unexpected server error","details":[],"request_id":_request_id(request)
    }})
