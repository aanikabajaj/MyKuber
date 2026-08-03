"""Structured logging for the AI Gateway — uses structlog JSON renderer."""
from __future__ import annotations
import hashlib
import structlog


def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )


def hash_user_id(user_id: int) -> str:
    return hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()


def log_request_complete(
    request_id: str,
    user_id_hash: str,
    endpoint: str,
    http_status: int,
    total_latency_ms: int,
    intents_detected: list[str],
    services_invoked: list[str],
    llm_tokens_used: int,
    session_id: str,
) -> None:
    """Emit a single structured JSON log event for every completed AI request."""
    logger = structlog.get_logger()
    logger.info(
        "ai_request_complete",
        request_id=request_id,
        user_id=user_id_hash,  # SHA-256 hash, never raw user_id
        endpoint=endpoint,
        http_status=http_status,
        total_latency_ms=total_latency_ms,
        intents_detected=intents_detected,
        services_invoked=services_invoked,
        llm_tokens_used=llm_tokens_used,
        session_id=session_id,
    )


async def persist_execution_trace(
    request_id: str,
    user_id: int,
    session_id: str,
    endpoint: str,
    intent: str,
    services_invoked: list,
    node_traces: list,
    total_latency_ms: int,
    llm_tokens_used: int,
    http_status: int,
    db,  # AsyncSession
) -> None:
    """Persist an AIExecutionTrace row for every request."""
    from ai.models.ai_tables import AIExecutionTrace

    trace = AIExecutionTrace(
        request_id=request_id,
        user_id_hash=hash_user_id(user_id),
        session_id=session_id or "",
        endpoint=endpoint,
        intent=intent,
        services_invoked=services_invoked,
        node_traces=node_traces,
        total_latency_ms=total_latency_ms,
        llm_tokens_used=llm_tokens_used,
        http_status=http_status,
    )
    db.add(trace)
    await db.commit()
