"""FastAPI entry point. OWNER: Member 2.

Run:  uvicorn app.main:app --reload --port 8000   (from backend/)
In Docker the built React app (frontend/dist) is served from the same process.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import APP_VERSION, load_settings
from app.core.errors import register_error_handlers
from app.database.db import init_db


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(title="Vinayak ProcureAI", version=APP_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    init_db(settings.database_path)
    app.include_router(router)

    dist = Path(settings.frontend_dist)
    if dist.is_dir():  # only present in the Docker image / after `npm run build`
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
