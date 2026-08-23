"""API FastAPI — analyse des exports CTO Boursorama.

Lancer en local :
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations


import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.session_store import SESSIONS

app = FastAPI(title=settings.PROJECT_NAME, version=settings.API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, tags=["api-v1"])

@app.get("/api/health")
def health():
    return {"status": "ok", "nb_sessions_actives": len(SESSIONS)}
