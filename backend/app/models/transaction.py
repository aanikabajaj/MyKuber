"""Fund-transfer transaction model (prototype banking)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    beneficiary_name: Mapped[str] = mapped_column(String(120))
    beneficiary_account: Mapped[str] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Float)
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # 'pending' -> 'completed' | 'failed' | 'blocked'
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # Whether Face ID step-up was demanded and how it went.
    step_up_required: Mapped[bool] = mapped_column(default=False)
    step_up_factor: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    balance_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
