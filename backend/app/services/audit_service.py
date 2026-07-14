"""Helper to append audit-log entries."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.audit import AuditLog

logger = get_logger("iaare.audit")


def log_event(
    db: Session,
    *,
    event_type: str,
    description: str,
    severity: str = "info",
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    meta: Optional[dict] = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        description=description,
        severity=severity,
        user_id=user_id,
        ip_address=ip_address,
        meta=meta or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info("[AUDIT:%s] %s", event_type, description)
    return entry
