"""Cryptographic helpers: password/MPIN hashing, JWT, generic hashing."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from app.core.config import settings


# --------------------------------------------------------------------------- #
#  Password / MPIN hashing (bcrypt)
# --------------------------------------------------------------------------- #
def hash_secret(raw: str) -> str:
    """Hash a password or MPIN with bcrypt. Returns a utf-8 string."""
    salt = bcrypt.gensalt(rounds=12)
    # bcrypt truncates at 72 bytes; pre-hash to be safe & length-independent.
    prepared = hashlib.sha256(raw.encode("utf-8")).hexdigest().encode("utf-8")
    return bcrypt.hashpw(prepared, salt).decode("utf-8")


def verify_secret(raw: str, hashed: str) -> bool:
    if not hashed:
        return False
    prepared = hashlib.sha256(raw.encode("utf-8")).hexdigest().encode("utf-8")
    try:
        return bcrypt.checkpw(prepared, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
#  OTP hashing (fast, constant-time comparison)
# --------------------------------------------------------------------------- #
def hash_otp(code: str) -> str:
    return hashlib.sha256((settings.SECRET_KEY + code).encode("utf-8")).hexdigest()


def verify_otp(code: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_otp(code), hashed or "")


def generate_numeric_otp(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


# --------------------------------------------------------------------------- #
#  JWT access / refresh tokens
# --------------------------------------------------------------------------- #
def _create_token(subject: str, token_type: str, expires_delta: timedelta, **extra: Any) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_hex(8),
    }
    payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, **extra: Any) -> str:
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        **extra,
    )


def create_refresh_token(subject: str, **extra: Any) -> str:
    return _create_token(
        subject,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        **extra,
    )


def create_registration_token(subject: str, **extra: Any) -> str:
    """Short-lived token that authorises the multi-step registration flow."""
    return _create_token(subject, "register", timedelta(minutes=30), **extra)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
