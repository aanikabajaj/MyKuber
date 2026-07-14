"""Trusted device / browser fingerprint model."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    screen_resolution: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    last_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_country: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    is_trusted: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="devices")
