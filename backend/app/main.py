from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
from uuid import uuid4
from app.api.routes import router
from app.core.errors import AppError, app_error_handler, validation_error_handler, http_error_handler, generic_error_handler

APP_DIR=Path(__file__).resolve().parent
app=FastAPI(title="Vinayak ProcureAI",version="1.0.0")
app.add_exception_handler(AppError,app_error_handler)
app.add_exception_handler(RequestValidationError,validation_error_handler)
app.add_exception_handler(StarletteHTTPException,http_error_handler)
app.add_exception_handler(Exception,generic_error_handler)

@app.middleware("http")
async def request_id(request: Request, call_next):
    request.state.request_id="req_"+uuid4().hex[:12]
    response=await call_next(request)
    response.headers["X-Request-ID"]=request.state.request_id
    return response

app.include_router(router)
app.mount("/static",StaticFiles(directory=APP_DIR/"static"),name="static")

@app.get("/",include_in_schema=False)
def index():
    return FileResponse(APP_DIR/"static"/"index.html")
