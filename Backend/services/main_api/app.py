"""
services/main_api/app.py
=========================
Main API — FastAPI app that wires together all routers.
Run with:  uvicorn services.main_api.app:app --port 8000 --reload
"""
from __future__ import annotations
import sys, os

# Ensure Backend/ is on the path so `core.*` imports resolve
_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.runtime_schema import ensure_runtime_schema

from services.main_api.routers import (
    ai_tools,
    applications,
    auth,
    evidence,
    jobs,
    linkedin,
    offer_letter,
    proctoring_enhanced,
    resume,
    verification,
    workflow,
)


def _include_service_routes(service_app: FastAPI, prefixes: tuple[str, ...]) -> None:
    """Expose selected microservice routes from the monolith-style Render service."""
    for route in service_app.router.routes:
        path = getattr(route, "path", "")
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes):
            app.router.routes.append(route)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_runtime_schema()
    yield


app = FastAPI(
    title="Hiresy Main API",
    version="2.0",
    description="Core API: auth, jobs, applications, LinkedIn OAuth, resume parsing, enhanced proctoring",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        dict.fromkeys(
            [
                settings.public_frontend_url,
                settings.FRONTEND_URL.rstrip("/"),
                "http://localhost:5173",
                "http://localhost:3000",
            ]
        )
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(linkedin.router)
app.include_router(resume.router)
app.include_router(ai_tools.router)
app.include_router(verification.router)
app.include_router(evidence.router)
app.include_router(proctoring_enhanced.router)
app.include_router(workflow.router)
app.include_router(offer_letter.router)

# The Render quick deploy runs only this main API container. Include the candidate
# round routes here so frontend links work even without separate microservices.
try:
    from services.shortlisting_test.app import app as shortlisting_app
    from services.coding_test.app import app as coding_app
    from services.live_hr.app import app as live_hr_app

    _include_service_routes(shortlisting_app, ("/test", "/tests"))
    _include_service_routes(coding_app, ("/coding", "/session"))
    _include_service_routes(live_hr_app, ("/livehr", "/hr"))
except Exception as exc:  # pragma: no cover - startup should continue with core API
    import logging

    logging.getLogger(__name__).warning("Could not include assessment service routes: %s", exc)


@app.get("/", tags=["health"])
def root():
    return {"message": "Hiresy Main API running", "version": "2.0"}


@app.get("/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "db_mode": settings.DATABASE_MODE,
        "db": settings.db_url.split("@")[-1] if "@" in settings.db_url else settings.db_url,
        "brevo": bool(settings.BREVO_API and settings.brevo_sender_email),
        "email_provider": "brevo",
        "groq": bool(settings.GROQ_API_KEY),
    }
