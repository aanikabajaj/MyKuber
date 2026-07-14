"""Issue and verify Email / SMS OTP codes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_numeric_otp, hash_otp, verify_otp
from app.models.otp import OTPCode
from app.services import notification_service
from app.services.notification_service import DeliveryResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def issue_otp(
    db: Session,
    *,
    channel: str,
    purpose: str,
    destination: str,
    user_id: Optional[int] = None,
) -> DeliveryResult:
    """Generate, persist and deliver an OTP. Prior unconsumed codes are voided."""
    db.execute(
        update(OTPCode)
        .where(
            OTPCode.user_id == user_id,
            OTPCode.channel == channel,
            OTPCode.purpose == purpose,
            OTPCode.consumed.is_(False),
        )
        .values(consumed=True)
    )
    code = generate_numeric_otp(settings.OTP_LENGTH)
    record = OTPCode(
        user_id=user_id,
        channel=channel,
        purpose=purpose,
        destination=destination,
        code_hash=hash_otp(code),
        expires_at=_utcnow() + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    db.add(record)
    db.commit()

    if channel == "email":
        return notification_service.send_email_otp(destination, code)
    return notification_service.send_sms_otp(destination, code)


def verify_otp_code(
    db: Session,
    *,
    channel: str,
    purpose: str,
    code: str,
    user_id: Optional[int] = None,
) -> Tuple[bool, str]:
    record = (
        db.query(OTPCode)
        .filter(
            OTPCode.user_id == user_id,
            OTPCode.channel == channel,
            OTPCode.purpose == purpose,
            OTPCode.consumed.is_(False),
        )
        .order_by(OTPCode.created_at.desc())
        .first()
    )
    if record is None:
        return False, "No active code. Please request a new one."

    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if _utcnow() > expires:
        record.consumed = True
        db.commit()
        return False, "Code expired. Please request a new one."

    if record.attempts >= settings.OTP_MAX_ATTEMPTS:
        record.consumed = True
        db.commit()
        return False, "Too many attempts. Please request a new one."

    if not verify_otp(code, record.code_hash):
        record.attempts += 1
        db.commit()
        remaining = settings.OTP_MAX_ATTEMPTS - record.attempts
        return False, f"Incorrect code. {max(remaining, 0)} attempt(s) left."

    record.consumed = True
    db.commit()
    return True, "verified"
