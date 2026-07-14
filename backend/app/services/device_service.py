"""Trusted-device registration and lookup by browser fingerprint."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.device import Device


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def find_device(db: Session, user_id: int, fingerprint: str) -> Optional[Device]:
    return (
        db.query(Device)
        .filter(Device.user_id == user_id, Device.fingerprint == fingerprint)
        .first()
    )


def register_device(
    db: Session,
    *,
    user_id: int,
    fingerprint: str,
    info: dict,
    ip: Optional[str] = None,
    country: Optional[str] = None,
    trusted: bool = True,
) -> Device:
    device = find_device(db, user_id, fingerprint)
    if device is None:
        device = Device(
            user_id=user_id,
            fingerprint=fingerprint,
            is_trusted=trusted,
        )
        db.add(device)
    device.label = info.get("label") or device.label or "Primary device"
    device.browser = info.get("browser")
    device.os = info.get("os")
    device.timezone = info.get("timezone")
    device.language = info.get("language")
    device.screen_resolution = info.get("screen_resolution")
    device.user_agent = info.get("user_agent")
    device.last_ip = ip
    device.last_country = country
    device.last_seen = _utcnow()
    if trusted:
        device.is_trusted = True
    db.commit()
    db.refresh(device)
    return device


def is_trusted(db: Session, user_id: int, fingerprint: str) -> bool:
    device = find_device(db, user_id, fingerprint)
    return bool(device and device.is_trusted)
