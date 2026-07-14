"""IAARE FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging_config import get_logger
from app.api.routes import admin, auth, captcha, login, registration, user

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
app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    try:
        from app.seed import seed_all
        seed_all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Seeding skipped/failed: %s", exc)
    logger.info("IAARE backend ready (demo_mode=%s)", settings.DEMO_MODE)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION,
            "demo_mode": settings.DEMO_MODE}


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "name": settings.PROJECT_NAME,
        "description": settings.PROJECT_DESCRIPTION,
        "docs": "/docs",
        "health": "/api/health",
    }
