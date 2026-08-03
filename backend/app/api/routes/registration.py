"""Multi-step registration / enrollment flow.

Registration stages (in order):
  details → mobile → email → sim_verify → mpin → second_factor → complete

SIM verify replaces the TOTP/QR authenticator step.
The mobile app reads the SIM hardware number, sends an OTP to it,
and the user confirms — binding the physical SIM card to this account.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_registration_user
from app.core.database import get_db
from app.core.security import create_registration_token, hash_secret
from app.core.utils import mask_email, mask_phone
from app.models.user import User
from app.schemas.auth import (
    FaceEnrollIn,
    FaceImagesEnrollIn,
    Message,
    MpinIn,
    OtpSendOut,
    OtpVerifyIn,
    PasskeyVerifyIn,
    RegisterDetails,
    RegisterDetailsOut,
    SimEnrollIn,
    SimVerifyConfirmIn,
    StageOut,
)
from app.schemas.auth import DeviceInfo
from app.services import (
    audit_service,
    device_service,
    face_service,
    geoip_service,
    otp_service,
    webauthn_service,
)

router = APIRouter(prefix="/api/register", tags=["registration"])


# --------------------------------------------------------------------------- #
#  Step 1 — account details
# --------------------------------------------------------------------------- #
@router.post("/details", response_model=RegisterDetailsOut, status_code=status.HTTP_201_CREATED)
def register_details(payload: RegisterDetails, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered.")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken.")

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        dob=payload.dob,
        gender=payload.gender,
        email=payload.email,
        mobile=payload.mobile,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        pin_code=payload.pin_code,
        username=payload.username,
        password_hash=hash_secret(payload.password),
        registration_stage="mobile",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit_service.log_event(
        db, event_type="register_start",
        description=f"Registration started for {user.username}",
        user_id=user.id, ip_address=get_client_ip(request),
    )
    token = create_registration_token(str(user.id))
    return RegisterDetailsOut(user_id=user.id, registration_token=token, stage=user.registration_stage)


# --------------------------------------------------------------------------- #
#  Step 2 — mobile OTP
# --------------------------------------------------------------------------- #
@router.post("/mobile/send-otp", response_model=OtpSendOut)
def mobile_send_otp(user: User = Depends(get_registration_user), db: Session = Depends(get_db)):
    result = otp_service.issue_otp(
        db, channel="sms", purpose="register", destination=user.mobile, user_id=user.id
    )
    return OtpSendOut(
        channel="sms", destination_masked=mask_phone(user.mobile),
        provider=result.provider, dev_code=result.dev_code,
        message=f"Verification code sent to {mask_phone(user.mobile)}",
    )


@router.post("/mobile/verify-otp", response_model=StageOut)
def mobile_verify_otp(payload: OtpVerifyIn, user: User = Depends(get_registration_user),
                      db: Session = Depends(get_db)):
    ok, reason = otp_service.verify_otp_code(
        db, channel="sms", purpose="register", code=payload.code, user_id=user.id
    )
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    user.mobile_verified = True
    user.registration_stage = "email"
    db.commit()
    return StageOut(stage=user.registration_stage, complete=False)


# --------------------------------------------------------------------------- #
#  Step 3 — email OTP
# --------------------------------------------------------------------------- #
@router.post("/email/send-otp", response_model=OtpSendOut)
def email_send_otp(user: User = Depends(get_registration_user), db: Session = Depends(get_db)):
    result = otp_service.issue_otp(
        db, channel="email", purpose="register", destination=user.email, user_id=user.id
    )
    return OtpSendOut(
        channel="email", destination_masked=mask_email(user.email),
        provider=result.provider, dev_code=result.dev_code,
        message=f"Verification code sent to {mask_email(user.email)}",
    )


@router.post("/email/verify-otp", response_model=StageOut)
def email_verify_otp(payload: OtpVerifyIn, user: User = Depends(get_registration_user),
                     db: Session = Depends(get_db)):
    ok, reason = otp_service.verify_otp_code(
        db, channel="email", purpose="register", code=payload.code, user_id=user.id
    )
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    user.email_verified = True
    # Advance to SIM verification (replaces the old TOTP QR authenticator step)
    user.registration_stage = "sim_verify"
    db.commit()
    return StageOut(stage=user.registration_stage, complete=False)


# --------------------------------------------------------------------------- #
#  Step 4 — SIM number verification (replaces TOTP / QR authenticator)
#
#  Flow:
#    a) Mobile app reads the SIM mobile number via TelephonyManager (Android).
#    b) An OTP is sent to that number via SMS.
#    c) User enters the OTP — proves physical possession of the SIM.
#    d) The SIM fingerprint (SHA-256 of carrier fields) is stored so the
#       sim_check login factor activates on every subsequent login.
# --------------------------------------------------------------------------- #
@router.post("/sim-verify/send-otp", response_model=OtpSendOut)
def sim_verify_send_otp(
    user: User = Depends(get_registration_user),
    db: Session = Depends(get_db),
):
    """Send an OTP to the mobile number currently in the device SIM."""
    if user.registration_stage not in ("sim_verify", "email"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot send SIM OTP at stage '{user.registration_stage}'.",
        )
    result = otp_service.issue_otp(
        db, channel="sms", purpose="sim_bind",
        destination=user.mobile, user_id=user.id,
    )
    return OtpSendOut(
        channel="sms",
        destination_masked=mask_phone(user.mobile),
        provider=result.provider,
        dev_code=result.dev_code,
        message=f"Verification code sent to {mask_phone(user.mobile)}",
    )


@router.post("/sim-verify/confirm", response_model=StageOut)
def sim_verify_confirm(
    payload: SimVerifyConfirmIn,
    request: Request,
    user: User = Depends(get_registration_user),
    db: Session = Depends(get_db),
):
    """Verify the OTP and bind the SIM fingerprint to the account."""
    ok, reason = otp_service.verify_otp_code(
        db, channel="sms", purpose="sim_bind",
        code=payload.code, user_id=user.id,
    )
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)

    # Store fingerprint if the mobile app supplied one (Android only)
    if payload.sim_fingerprint and len(payload.sim_fingerprint) == 64:
        user.sim_fingerprint = payload.sim_fingerprint.strip().lower()
        user.sim_enrolled    = True

    user.registration_stage = "mpin"
    db.commit()
    audit_service.log_event(
        db, event_type="sim_bound",
        description=f"SIM number verified and bound for {user.username}",
        severity="info", user_id=user.id,
        ip_address=get_client_ip(request),
    )
    return StageOut(stage=user.registration_stage, complete=False)


# --------------------------------------------------------------------------- #
#  SIM fingerprint enrollment (standalone — called from Settings)
# --------------------------------------------------------------------------- #
@router.post("/sim/enroll", response_model=Message)
def enroll_sim_registration(
    payload: SimEnrollIn,
    request: Request,
    user: User = Depends(get_registration_user),
    db: Session = Depends(get_db),
):
    """Store the SHA-256 SIM fingerprint supplied by the mobile app.

    Called during registration after mobile OTP, or later from Settings
    to bind / update the device SIM. Raw SIM data is never transmitted —
    only the hex hash.
    """
    user.sim_fingerprint = payload.sim_fingerprint.strip().lower()
    user.sim_enrolled    = True
    db.commit()
    audit_service.log_event(
        db,
        event_type="sim_enrolled",
        description=f"SIM fingerprint enrolled during registration for {user.username}",
        severity="info",
        user_id=user.id,
        ip_address=get_client_ip(request),
    )
    return Message(message="SIM fingerprint enrolled successfully.")


# --------------------------------------------------------------------------- #
#  Step 5 — MPIN
# --------------------------------------------------------------------------- #
@router.post("/mpin", response_model=StageOut)
def set_mpin(payload: MpinIn, user: User = Depends(get_registration_user),
             db: Session = Depends(get_db)):
    user.mpin_hash = hash_secret(payload.mpin)
    user.registration_stage = "second_factor"
    db.commit()
    return StageOut(stage=user.registration_stage, complete=False)


# --------------------------------------------------------------------------- #
#  Step 6a — Face enrollment
# --------------------------------------------------------------------------- #
@router.post("/second-factor/face", response_model=StageOut)
def enroll_face(payload: FaceEnrollIn, request: Request,
                user: User = Depends(get_registration_user), db: Session = Depends(get_db)):
    user.face_embedding_enc = face_service.encrypt_templates(payload.embeddings)
    user.face_enabled  = True
    user.second_factor = "face"
    user.registration_stage = "complete"
    db.commit()
    audit_service.log_event(
        db, event_type="register_complete",
        description=f"Registration complete (face) for {user.username}",
        user_id=user.id, ip_address=get_client_ip(request),
    )
    return StageOut(stage=user.registration_stage, complete=True)


# --------------------------------------------------------------------------- #
#  Step 6a-mobile — Face enrollment from camera images
# --------------------------------------------------------------------------- #
@router.post("/second-factor/face-images", response_model=StageOut)
def enroll_face_images(payload: FaceImagesEnrollIn,
                       request: Request,
                       user: User = Depends(get_registration_user),
                       db: Session = Depends(get_db)):
    templates = face_service.embeddings_from_images(payload.images)
    if not templates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "No face detected in the captured frames. Ensure your face is well-lit and centered, then retry.")
    user.face_embedding_enc = face_service.encrypt_templates(templates)
    user.face_enabled  = True
    user.second_factor = "face"
    user.registration_stage = "complete"
    db.commit()
    audit_service.log_event(
        db, event_type="register_complete",
        description=f"Registration complete (camera face, {len(templates)} angles) for {user.username}",
        user_id=user.id, ip_address=get_client_ip(request),
    )
    return StageOut(stage=user.registration_stage, complete=True)


# --------------------------------------------------------------------------- #
#  Step 6c — Device biometric enrollment
# --------------------------------------------------------------------------- #
@router.post("/second-factor/biometric", response_model=StageOut)
def enroll_biometric(request: Request, user: User = Depends(get_registration_user),
                     db: Session = Depends(get_db)):
    user.second_factor = "biometric"
    user.face_enabled  = False
    user.registration_stage = "complete"
    db.commit()
    audit_service.log_event(
        db, event_type="register_complete",
        description=f"Registration complete (device biometric) for {user.username}",
        user_id=user.id, ip_address=get_client_ip(request),
    )
    return StageOut(stage=user.registration_stage, complete=True)


# --------------------------------------------------------------------------- #
#  Step 6b — Passkey (WebAuthn) enrollment
# --------------------------------------------------------------------------- #
@router.post("/second-factor/passkey/options")
def passkey_register_options(user: User = Depends(get_registration_user),
                             db: Session = Depends(get_db)):
    options_json, handle = webauthn_service.start_registration(db, user)
    return {"handle": handle, "options": options_json}


@router.post("/second-factor/passkey/verify", response_model=StageOut)
def passkey_register_verify(payload: PasskeyVerifyIn, request: Request,
                            user: User = Depends(get_registration_user),
                            db: Session = Depends(get_db)):
    import json
    try:
        webauthn_service.finish_registration(
            db, user, handle=payload.handle,
            credential_json=json.dumps(payload.credential), label="Primary passkey",
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    user.second_factor = "passkey"
    user.registration_stage = "complete"
    db.commit()
    audit_service.log_event(
        db, event_type="register_complete",
        description=f"Registration complete (passkey) for {user.username}",
        user_id=user.id, ip_address=get_client_ip(request),
    )
    return StageOut(stage=user.registration_stage, complete=True)


# --------------------------------------------------------------------------- #
#  Device registration
# --------------------------------------------------------------------------- #
@router.post("/device", response_model=Message)
def register_device(info: DeviceInfo, request: Request,
                    user: User = Depends(get_registration_user), db: Session = Depends(get_db)):
    ip  = get_client_ip(request)
    geo = geoip_service.lookup(ip)
    device_service.register_device(
        db, user_id=user.id, fingerprint=info.fingerprint,
        info=info.model_dump(), ip=ip, country=geo.country, trusted=True,
    )
    return Message(message="Device registered as trusted.")


@router.get("/status", response_model=StageOut)
def registration_status(user: User = Depends(get_registration_user)):
    return StageOut(stage=user.registration_stage, complete=user.registration_complete)
