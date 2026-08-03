"""IAARE FastAPI application entry point."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.logging_config import get_logger
from app.api.routes import admin, auth, captcha, login, registration, transaction, user

logger = get_logger("iaare.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(captcha.router)
app.include_router(registration.router)
app.include_router(login.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(transaction.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    try:
        from app.seed import seed_all
        seed_all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Seeding skipped/failed: %s", exc)
    from app.services.notification_service import active_providers
    prov = active_providers()
    logger.info("IAARE backend ready (demo_mode=%s)", settings.DEMO_MODE)
    logger.info("OTP delivery -> SMS: %s | Email: %s", prov["sms"], prov["email"])


@app.get("/api/health", tags=["health"])
def health() -> dict:
    from app.services.notification_service import active_providers
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION,
            "demo_mode": settings.DEMO_MODE, "otp": active_providers()}


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "name": settings.PROJECT_NAME,
        "description": settings.PROJECT_DESCRIPTION,
        "docs": "/docs",
        "health": "/api/health",
    }


# ---------------------------------------------------------------------------
# Serve the built React frontend (if dist/ exists next to the backend folder)
# This lets a single ngrok tunnel serve both frontend and backend.
# ---------------------------------------------------------------------------
_FRONTEND_DIST = os.path.join(
    os.path.dirname(__file__), "..", "..", "frontend", "dist"
)

if os.path.isdir(_FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        """Catch-all: serve index.html for all non-API routes (SPA routing)."""
        index = os.path.join(_FRONTEND_DIST, "index.html")
        return FileResponse(index)
