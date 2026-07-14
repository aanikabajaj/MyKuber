"""Adaptive authentication session — tracks the multi-step login journey."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthSession(Base):
    """A server-side record of an in-progress adaptive login.

    Created after password verification. Holds the ordered list of factors
    the risk engine demands, and tracks which have been satisfied.
    """

    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # uuid4 hex
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_band: Mapped[str] = mapped_column(String(20), default="SAFE")

    required_steps: Mapped[list] = mapped_column(JSON, default=list)
    completed_steps: Mapped[list] = mapped_column(JSON, default=list)

    # 'pending' | 'approved' | 'blocked' | 'expired'
    status: Mapped[str] = mapped_column(String(20), default="pending")

    context: Mapped[dict] = mapped_column(JSON, default=dict)
    device_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @property
    def next_step(self) -> Optional[str]:
        for step in self.required_steps:
            if step not in (self.completed_steps or []):
                return step
        return None

    @property
    def is_complete(self) -> bool:
        return self.next_step is None
