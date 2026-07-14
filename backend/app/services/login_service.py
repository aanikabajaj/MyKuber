"""Adaptive-login session lifecycle: create, advance, finalize."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token
from app.models.auth_session import AuthSession
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.services import audit_service, device_service
from app.services.geoip_service import GeoInfo
from app.services.risk_engine import RiskResult

SESSION_TTL_SECONDS = 600


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_geo(base: GeoInfo, simulate) -> GeoInfo:
    """Overlay demo-simulation values onto a real GeoIP result."""
    if not simulate or not getattr(simulate, "enabled", False):
        return base
    return GeoInfo(
        ip=simulate.ip or base.ip,
        country=simulate.country or base.country,
        region=simulate.region or base.region,
        city=simulate.city or base.city,
        latitude=simulate.latitude if simulate.latitude is not None else base.latitude,
        longitude=simulate.longitude if simulate.longitude is not None else base.longitude,
        is_vpn=simulate.is_vpn if simulate.is_vpn is not None else base.is_vpn,
        isp=base.isp,
        source="simulated",
    )


def create_session(
    db: Session,
    user: User,
    risk: RiskResult,
    *,
    device_info: dict,
    ip: str,
    user_agent: str,
) -> AuthSession:
    steps = list(risk.required_steps)
    status = "blocked" if risk.band == "CRITICAL" else "pending"
    session = AuthSession(
        id=uuid.uuid4().hex,
        user_id=user.id,
        risk_score=risk.score,
        risk_band=risk.band,
        required_steps=steps,
        completed_steps=[],
        status=status,
        context={
            "risk": risk.as_dict(),
            "device": device_info,
            "ip": ip,
            "user_agent": user_agent,
            "geo": risk.geo,
        },
        expires_at=_utcnow() + timedelta(seconds=SESSION_TTL_SECONDS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> Optional[AuthSession]:
    session = db.get(AuthSession, session_id)
    if session is None:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if _utcnow() > expires and session.status == "pending":
        session.status = "expired"
        db.commit()
    return session


def advance(db: Session, session: AuthSession, step: str) -> None:
    completed = list(session.completed_steps or [])
    if step not in completed:
        completed.append(step)
    session.completed_steps = completed
    db.commit()
    db.refresh(session)


def record_attempt(
    db: Session,
    *,
    user: Optional[User],
    username: str,
    ip: str,
    geo: GeoInfo,
    risk_score: float,
    risk_band: str,
    decision: str,
    success: bool,
    user_agent: str,
) -> None:
    db.add(
        LoginAttempt(
            user_id=user.id if user else None,
            username=username,
            ip_address=geo.ip if geo else ip,
            country=geo.country if geo else None,
            region=geo.region if geo else None,
            city=geo.city if geo else None,
            latitude=geo.latitude if geo else None,
            longitude=geo.longitude if geo else None,
            is_vpn=geo.is_vpn if geo else False,
            risk_score=risk_score,
            risk_band=risk_band,
            decision=decision,
            success=success,
            user_agent=user_agent,
        )
    )
    db.commit()


def finalize(db: Session, session: AuthSession, user: User) -> dict:
    """All factors satisfied — approve, trust device, issue tokens."""
    session.status = "approved"
    user.failed_login_count = 0
    user.last_login_at = _utcnow()

    ctx = session.context or {}
    device_info = ctx.get("device") or {}
    geo = ctx.get("geo") or {}
    if device_info.get("fingerprint"):
        device_service.register_device(
            db, user_id=user.id, fingerprint=device_info["fingerprint"],
            info=device_info, ip=ctx.get("ip"), country=geo.get("country"), trusted=True,
        )

    db.add(
        LoginAttempt(
            user_id=user.id,
            username=user.username,
            ip_address=ctx.get("ip"),
            country=geo.get("country"),
            region=geo.get("region"),
            city=geo.get("city"),
            latitude=geo.get("latitude"),
            longitude=geo.get("longitude"),
            is_vpn=bool(geo.get("is_vpn")),
            risk_score=session.risk_score,
            risk_band=session.risk_band,
            decision="ALLOW",
            success=True,
            user_agent=ctx.get("user_agent"),
        )
    )
    db.commit()

    audit_service.log_event(
        db, event_type="login_success",
        description=f"Login approved for {user.username} (risk {session.risk_band})",
        user_id=user.id, ip_address=ctx.get("ip"),
        meta={"risk_score": session.risk_score, "band": session.risk_band},
    )

    access = create_access_token(str(user.id), is_admin=user.is_admin, username=user.username)
    refresh = create_refresh_token(str(user.id))
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "is_admin": user.is_admin,
        },
    }


def session_out(session: AuthSession, user: User, tokens: Optional[dict] = None) -> dict:
    ctx = session.context or {}
    risk = ctx.get("risk") or {}
    return {
        "session_id": session.id,
        "status": session.status,
        "risk": {
            "score": risk.get("score", int(session.risk_score)),
            "band": risk.get("band", session.risk_band),
            "decision": risk.get("decision", "ALLOW"),
            "factors": risk.get("factors", []),
            "geo": risk.get("geo"),
        },
        "required_steps": session.required_steps or [],
        "completed_steps": session.completed_steps or [],
        "next_step": session.next_step,
        "second_factor": user.second_factor,
        "user_display": user.full_name,
        "tokens": tokens,
        "message": None,
    }
