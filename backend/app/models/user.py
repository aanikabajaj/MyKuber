"""User account model."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- Personal details ---
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    dob: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    mobile: Mapped[str] = mapped_column(String(20), index=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    pin_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # --- Credentials ---
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    mpin_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # --- Second factors ---
    totp_secret_enc: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    face_embedding_enc: Mapped[Optional[str]] = mapped_column(String(8192), nullable=True)
    face_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # 'face' or 'passkey' — the strong factor the user chose at registration
    second_factor: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # --- Verification flags ---
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mobile_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Status ---
    # registration_stage: details -> mobile -> email -> authenticator -> mpin -> second_factor -> complete
    registration_stage: Mapped[str] = mapped_column(String(30), default="details")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Seeded demo accounts: in DEMO_MODE their biometric step is auto-passed so
    # they can be logged in during a presentation without the enrolled face.
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship(
        "WebAuthnCredential", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def registration_complete(self) -> bool:
        return self.registration_stage == "complete"
