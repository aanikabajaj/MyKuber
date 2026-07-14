"""Adaptive authentication login flow."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.core.database import get_db
from app.core.rate_limit import allow as rate_allow
from app.core.security import verify_secret
from app.models.auth_session import AuthSession
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.schemas.auth import (
    LoginPasswordIn,
    LoginSessionOut,
    StepFaceIn,
    StepMpinIn,
    StepOtpVerifyIn,
    StepPasskeyOptionsIn,
    StepPasskeyVerifyIn,
    StepTotpIn,
)
from app.services import (
    audit_service,
    captcha_service,
    face_service,
    geoip_service,
    login_service,
    otp_service,
    totp_service,
    webauthn_service,
)
from app.services.risk_engine import BAND_DECISION, BAND_STEPS, assess, band_for_score

router = APIRouter(prefix="/api/login", tags=["login"])

_BAND_MID = {"SAFE": 15, "MEDIUM": 45, "HIGH": 70, "CRITICAL": 90}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_pending(db: Session, session_id: str) -> tuple[AuthSession, User]:
    session = login_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Login session not found.")
    if session.status == "approved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Session already approved.")
    if session.status in ("blocked", "expired"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Session {session.status}.")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return session, user


def _expect_step(session: AuthSession, step: str) -> None:
    if session.next_step != step:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unexpected step '{step}'. Next required step is '{session.next_step}'.",
        )


def _maybe_finalize(db: Session, session: AuthSession, user: User) -> dict:
    if session.is_complete:
        tokens = login_service.finalize(db, session, user)
        return login_service.session_out(session, user, tokens=tokens)
    return login_service.session_out(session, user)


# --------------------------------------------------------------------------- #
#  Step 0 — password + captcha + risk assessment
# --------------------------------------------------------------------------- #
@router.post("/password", response_model=LoginSessionOut)
def login_password(payload: LoginPasswordIn, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    if not rate_allow(f"login:{ip}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Slow down.")

    if not captcha_service.verify(payload.captcha_id, payload.captcha_answer):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect CAPTCHA.")

    ua = request.headers.get("user-agent", "")
    user = db.query(User).filter(User.username == payload.username).first()

    # Geo / simulation context (needed even for failed attempts logging)
    base_geo = geoip_service.lookup(payload.simulate.ip if (payload.simulate and payload.simulate.ip) else ip)
    geo = login_service.build_geo(base_geo, payload.simulate)

    if user is None or not verify_secret(payload.password, user.password_hash):
        if user is not None:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            db.commit()
        login_service.record_attempt(
            db, user=user, username=payload.username, ip=ip, geo=geo,
            risk_score=0, risk_band="N/A", decision="DENY", success=False, user_agent=ua,
        )
        audit_service.log_event(
            db, event_type="login_failed",
            description=f"Failed password for '{payload.username}'",
            severity="warning", user_id=user.id if user else None, ip_address=ip,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password.")

    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is blocked. Contact your bank.")
    if not user.registration_complete:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Registration is incomplete for this account.")

    # --- gather risk signals ---
    from app.services import device_service

    fp = payload.device.fingerprint
    known_device = device_service.find_device(db, user.id, fp) is not None
    trusted_device = device_service.is_trusted(db, user.id, fp)
    if payload.simulate and payload.simulate.new_device:
        known_device = False
        trusted_device = False

    since = _utcnow() - timedelta(minutes=60)
    failed_attempts = (
        db.query(LoginAttempt)
        .filter(LoginAttempt.user_id == user.id, LoginAttempt.success.is_(False),
                LoginAttempt.created_at >= since)
        .count()
    )
    if payload.simulate and payload.simulate.failed_attempts is not None:
        failed_attempts = payload.simulate.failed_attempts

    risk = assess(
        db, user, geo=geo, trusted_device=trusted_device,
        known_device_exists=known_device, failed_attempts=failed_attempts,
    )

    # --- optional explicit demo override ---
    if payload.simulate and payload.simulate.enabled and payload.simulate.force_band:
        fb = payload.simulate.force_band.upper()
        if fb in BAND_STEPS:
            from app.services.risk_engine import Factor
            risk.band = fb
            risk.score = _BAND_MID[fb]
            risk.decision = BAND_DECISION[fb]
            risk.required_steps = list(BAND_STEPS[fb])
            risk.factors.append(Factor("demo_override", 0, f"Demo scenario forced to {fb}"))

    session = login_service.create_session(
        db, user, risk, device_info=payload.device.model_dump(), ip=ip, user_agent=ua,
    )

    if risk.band == "CRITICAL":
        login_service.record_attempt(
            db, user=user, username=user.username, ip=ip, geo=geo,
            risk_score=risk.score, risk_band=risk.band, decision="BLOCK",
            success=False, user_agent=ua,
        )
        audit_service.log_event(
            db, event_type="login_blocked",
            description=f"CRITICAL risk login blocked for {user.username} (score {risk.score})",
            severity="critical", user_id=user.id, ip_address=ip,
            meta={"factors": [f.__dict__ for f in risk.factors]},
        )

    out = login_service.session_out(session, user)
    if risk.band == "CRITICAL":
        out["message"] = "Login blocked due to CRITICAL risk. Your bank has been notified."
    return out


# --------------------------------------------------------------------------- #
#  Step — MPIN
# --------------------------------------------------------------------------- #
@router.post("/step/mpin", response_model=LoginSessionOut)
def step_mpin(payload: StepMpinIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "mpin")
    if not verify_secret(payload.mpin, user.mpin_hash or ""):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect MPIN.")
    login_service.advance(db, session, "mpin")
    return _maybe_finalize(db, session, user)


# --------------------------------------------------------------------------- #
#  Step — second factor: FACE
# --------------------------------------------------------------------------- #
@router.post("/step/face", response_model=LoginSessionOut)
def step_face(payload: StepFaceIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "second_factor")
    if user.second_factor != "face":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Face is not this account's second factor.")
    from app.core.config import settings
    if settings.DEMO_MODE and user.is_demo:
        # Seeded demo account: accept the live capture so the flow can be shown
        # without the originally-enrolled face on the presentation machine.
        login_service.advance(db, session, "second_factor")
        return _maybe_finalize(db, session, user)
    ok, sim = face_service.compare(user.face_embedding_enc, payload.embedding)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Face not recognised (similarity {sim}).")
    login_service.advance(db, session, "second_factor")
    return _maybe_finalize(db, session, user)


# --------------------------------------------------------------------------- #
#  Step — second factor: PASSKEY
# --------------------------------------------------------------------------- #
@router.post("/step/passkey/options")
def step_passkey_options(payload: StepPasskeyOptionsIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "second_factor")
    try:
        options_json, handle = webauthn_service.start_authentication(db, user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"handle": handle, "options": options_json}


@router.post("/step/passkey/verify", response_model=LoginSessionOut)
def step_passkey_verify(payload: StepPasskeyVerifyIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "second_factor")
    try:
        webauthn_service.finish_authentication(
            db, user, handle=payload.handle, credential_json=json.dumps(payload.credential)
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    login_service.advance(db, session, "second_factor")
    return _maybe_finalize(db, session, user)


# --------------------------------------------------------------------------- #
#  Step — Email OTP
# --------------------------------------------------------------------------- #
@router.post("/step/email-otp/send")
def step_email_otp_send(payload: StepPasskeyOptionsIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "email_otp")
    from app.core.utils import mask_email
    result = otp_service.issue_otp(
        db, channel="email", purpose="login", destination=user.email, user_id=user.id
    )
    return {
        "channel": "email", "destination_masked": mask_email(user.email),
        "provider": result.provider, "dev_code": result.dev_code,
        "message": f"Code sent to {mask_email(user.email)}",
    }


@router.post("/step/email-otp/verify", response_model=LoginSessionOut)
def step_email_otp_verify(payload: StepOtpVerifyIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "email_otp")
    ok, reason = otp_service.verify_otp_code(
        db, channel="email", purpose="login", code=payload.code, user_id=user.id
    )
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    login_service.advance(db, session, "email_otp")
    return _maybe_finalize(db, session, user)


# --------------------------------------------------------------------------- #
#  Step — SMS OTP
# --------------------------------------------------------------------------- #
@router.post("/step/sms-otp/send")
def step_sms_otp_send(payload: StepPasskeyOptionsIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "sms_otp")
    from app.core.utils import mask_phone
    result = otp_service.issue_otp(
        db, channel="sms", purpose="login", destination=user.mobile, user_id=user.id
    )
    return {
        "channel": "sms", "destination_masked": mask_phone(user.mobile),
        "provider": result.provider, "dev_code": result.dev_code,
        "message": f"Code sent to {mask_phone(user.mobile)}",
    }


@router.post("/step/sms-otp/verify", response_model=LoginSessionOut)
def step_sms_otp_verify(payload: StepOtpVerifyIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "sms_otp")
    ok, reason = otp_service.verify_otp_code(
        db, channel="sms", purpose="login", code=payload.code, user_id=user.id
    )
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    login_service.advance(db, session, "sms_otp")
    return _maybe_finalize(db, session, user)


# --------------------------------------------------------------------------- #
#  Step — Google Authenticator (TOTP)
# --------------------------------------------------------------------------- #
@router.post("/step/totp", response_model=LoginSessionOut)
def step_totp(payload: StepTotpIn, db: Session = Depends(get_db)):
    session, user = _load_pending(db, payload.session_id)
    _expect_step(session, "totp")
    from app.core.config import settings
    demo_ok = settings.DEMO_MODE and user.is_demo
    if not demo_ok and (
        not user.totp_secret_enc or not totp_service.verify_token(user.totp_secret_enc, payload.token)
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid authenticator code.")
    login_service.advance(db, session, "totp")
    return _maybe_finalize(db, session, user)


# --------------------------------------------------------------------------- #
#  Session state (resume / refresh)
# --------------------------------------------------------------------------- #
@router.get("/session/{session_id}", response_model=LoginSessionOut)
def get_login_session(session_id: str, db: Session = Depends(get_db)):
    session = login_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    user = db.get(User, session.user_id)
    return login_service.session_out(session, user)
