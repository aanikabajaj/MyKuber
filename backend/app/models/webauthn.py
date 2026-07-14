"""WebAuthn passkey credentials + transient challenge storage."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    credential_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)  # base64url
    public_key: Mapped[str] = mapped_column(String(1024))  # base64url
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="credentials")


class PendingChallenge(Base):
    """Short-lived WebAuthn challenge, keyed by a client-held handle."""

    __tablename__ = "pending_challenges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # handle (uuid hex)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(30))  # 'register' | 'authenticate'
    challenge: Mapped[str] = mapped_column(String(512))  # base64url
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
