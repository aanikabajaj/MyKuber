"""AI Gateway — FastAPI application entry point."""
from __future__ import annotations
import uuid
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from ai.core.config import settings
from ai.models.ai_tables import create_ai_tables


def configure_logging():
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await create_ai_tables()
    # Ensure Qdrant collections exist (if Qdrant is reachable)
    try:
        from qdrant_client import QdrantClient
        from ai.rag.collections import ensure_collections
        qc = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        ensure_collections(qc)
    except Exception:
        pass  # non-fatal on startup
    # Warm both embedding models so the first chat request isn't stuck
    # downloading/loading them and risking a client-side timeout:
    #  - BGE-M3 (RAG document retrieval)
    #  - all-MiniLM-L6-v2 (intent_router's semantic classifier — loaded and
    #    its centroids built as a side effect of importing the module)
    import asyncio

    loop = asyncio.get_running_loop()
    try:
        from ai.rag.embeddings import warmup as warmup_embeddings
        await warmup_embeddings()
    except Exception:
        pass  # non-fatal on startup — falls back to lazy load on first use
    try:
        await loop.run_in_executor(None, lambda: __import__("ai.agents.intent_router"))
    except Exception:
        pass  # non-fatal on startup — falls back to lazy load on first use
    yield


app = FastAPI(title="Wealth Intelligence AI Gateway", lifespan=lifespan)

# CORS — allow mobile/web clients (tighten allow_origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics at /ai/metrics
metrics_app = make_asgi_app()
app.mount("/ai/metrics", metrics_app)

# Include routers
from ai.api import chat, portfolio, transactions, knowledge, profile, health
app.include_router(chat.router, prefix="/ai")
app.include_router(portfolio.router, prefix="/ai")
app.include_router(transactions.router, prefix="/ai")
app.include_router(knowledge.router, prefix="/ai")
app.include_router(profile.router, prefix="/ai")
app.include_router(health.router, prefix="/ai")
