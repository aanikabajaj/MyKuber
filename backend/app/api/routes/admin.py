"""Admin dashboard analytics endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.auth_session import AuthSession
from app.models.device import Device
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.models.webauthn import WebAuthnCredential
from app.schemas.admin import (
    AdminStats,
    AuditRow,
    AuthStat,
    LoginRow,
    MapPoint,
    RiskBucket,
)

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _start_of_day() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("/stats", response_model=AdminStats)
def stats(db: Session = Depends(get_db)):
    today = _start_of_day()
    total_users = db.query(func.count(User.id)).scalar() or 0
    logins_today = (
        db.query(func.count(LoginAttempt.id))
        .filter(LoginAttempt.success.is_(True), LoginAttempt.created_at >= today)
        .scalar() or 0
    )
    blocked = (
        db.query(func.count(LoginAttempt.id))
        .filter(LoginAttempt.decision == "BLOCK")
        .scalar() or 0
    )
    high_risk = (
        db.query(func.count(LoginAttempt.id))
        .filter(LoginAttempt.risk_band.in_(["HIGH", "CRITICAL"]))
        .scalar() or 0
    )
    total_devices = db.query(func.count(Device.id)).scalar() or 0
    active_sessions = (
        db.query(func.count(AuthSession.id))
        .filter(AuthSession.status == "pending")
        .scalar() or 0
    )
    return AdminStats(
        total_users=total_users,
        logins_today=logins_today,
        blocked_logins=blocked,
        high_risk_logins=high_risk,
        total_devices=total_devices,
        active_sessions=active_sessions,
    )


@router.get("/risk-distribution", response_model=List[RiskBucket])
def risk_distribution(db: Session = Depends(get_db)):
    rows = (
        db.query(LoginAttempt.risk_band, func.count(LoginAttempt.id))
        .group_by(LoginAttempt.risk_band)
        .all()
    )
    order = {"SAFE": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3, "N/A": 4}
    buckets = [RiskBucket(band=b or "N/A", count=c) for b, c in rows]
    buckets.sort(key=lambda x: order.get(x.band, 9))
    return buckets


@router.get("/auth-stats", response_model=List[AuthStat])
def auth_stats(db: Session = Depends(get_db)):
    mpin = db.query(func.count(User.id)).filter(User.mpin_hash.isnot(None)).scalar() or 0
    totp = db.query(func.count(User.id)).filter(User.totp_enabled.is_(True)).scalar() or 0
    face = db.query(func.count(User.id)).filter(User.face_enabled.is_(True)).scalar() or 0
    passkey = db.query(func.count(func.distinct(WebAuthnCredential.user_id))).scalar() or 0
    total = db.query(func.count(User.id)).scalar() or 0
    return [
        AuthStat(factor="Password", count=total),
        AuthStat(factor="MPIN", count=mpin),
        AuthStat(factor="Authenticator", count=totp),
        AuthStat(factor="Face", count=face),
        AuthStat(factor="Passkey", count=passkey),
    ]


@router.get("/login-attempts", response_model=List[LoginRow])
def login_attempts(limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(LoginAttempt).order_by(LoginAttempt.created_at.desc()).limit(limit).all()
    )


@router.get("/audit-logs", response_model=List[AuditRow])
def audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()


@router.get("/users")
def users(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "country": u.country,
            "city": u.city,
            "second_factor": u.second_factor,
            "is_admin": u.is_admin,
            "is_blocked": u.is_blocked,
            "registration_stage": u.registration_stage,
            "last_login_at": u.last_login_at,
            "created_at": u.created_at,
        }
        for u in rows
    ]


@router.get("/map", response_model=List[MapPoint])
def login_map(db: Session = Depends(get_db)):
    rows = (
        db.query(
            LoginAttempt.latitude,
            LoginAttempt.longitude,
            LoginAttempt.city,
            LoginAttempt.country,
            LoginAttempt.risk_band,
            func.count(LoginAttempt.id),
        )
        .filter(LoginAttempt.latitude.isnot(None), LoginAttempt.longitude.isnot(None))
        .group_by(
            LoginAttempt.latitude, LoginAttempt.longitude,
            LoginAttempt.city, LoginAttempt.country, LoginAttempt.risk_band,
        )
        .all()
    )
    return [
        MapPoint(latitude=lat, longitude=lon, city=city, country=country,
                 risk_band=band or "N/A", count=count)
        for lat, lon, city, country, band, count in rows
    ]
