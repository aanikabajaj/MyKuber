"""Authenticated user dashboard & settings endpoints."""
from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import hash_secret, verify_secret
from app.models.device import Device
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.models.webauthn import WebAuthnCredential
from app.schemas.auth import Message, PasskeyVerifyIn
from app.schemas.user import (
    DeviceOut,
    FaceImagesReenrollIn,
    FaceReenrollIn,
    LoginHistoryOut,
    MpinResetIn,
    PasskeyOut,
    SecurityPrefsIn,
    UserOut,
)
from app.services import face_service, webauthn_service

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/devices", response_model=List[DeviceOut])
def list_devices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Device).filter(Device.user_id == user.id).order_by(Device.last_seen.desc()).all()


@router.delete("/devices/{device_id}", response_model=Message)
def remove_device(device_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if device is None or device.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    db.delete(device)
    db.commit()
    return Message(message="Device removed.")


@router.get("/login-history", response_model=List[LoginHistoryOut])
def login_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(LoginAttempt)
        .filter(LoginAttempt.user_id == user.id)
        .order_by(LoginAttempt.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/passkeys", response_model=List[PasskeyOut])
def list_passkeys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(WebAuthnCredential).filter(WebAuthnCredential.user_id == user.id).all()


@router.delete("/passkeys/{cred_id}", response_model=Message)
def remove_passkey(cred_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cred = db.get(WebAuthnCredential, cred_id)
    if cred is None or cred.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Passkey not found.")
    db.delete(cred)
    db.commit()
    return Message(message="Passkey removed.")


@router.post("/mpin/reset", response_model=Message)
def reset_mpin(payload: MpinResetIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_secret(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")
    if not (payload.new_mpin.isdigit() and len(payload.new_mpin) == 6):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MPIN must be exactly 6 digits.")
    user.mpin_hash = hash_secret(payload.new_mpin)
    db.commit()
    return Message(message="MPIN updated successfully.")


@router.post("/face/re-enroll", response_model=Message)
def reenroll_face(payload: FaceReenrollIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.face_embedding_enc = face_service.encrypt_templates(payload.embeddings)
    user.face_enabled = True
    user.second_factor = "face"
    db.commit()
    return Message(message="Face re-enrolled successfully.")


@router.post("/face/re-enroll-images", response_model=Message)
def reenroll_face_images(payload: FaceImagesReenrollIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    templates = face_service.embeddings_from_images(payload.images)
    if not templates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "No face detected in the captured frames. Ensure your face is well-lit and centered, then retry.")
    user.face_embedding_enc = face_service.encrypt_templates(templates)
    user.face_enabled = True
    user.second_factor = "face"
    db.commit()
    return Message(message="Face re-enrolled successfully.")


@router.get("/security-prefs")
def get_security_prefs(user: User = Depends(get_current_user)):
    return {
        "second_factor": user.second_factor,
        "face_enabled": user.face_enabled,
        "face_login_enabled": user.face_login_enabled,
        "face_txn_enabled": user.face_txn_enabled,
        "txn_face_threshold": user.txn_face_threshold,
        "preferred_language": user.preferred_language,
    }


@router.put("/security-prefs", response_model=Message)
def update_security_prefs(payload: SecurityPrefsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.face_login_enabled is not None:
        user.face_login_enabled = payload.face_login_enabled
    if payload.face_txn_enabled is not None:
        user.face_txn_enabled = payload.face_txn_enabled
    if payload.txn_face_threshold is not None:
        if payload.txn_face_threshold < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Threshold cannot be negative.")
        user.txn_face_threshold = payload.txn_face_threshold
    if payload.preferred_language is not None:
        user.preferred_language = payload.preferred_language[:8]
    db.commit()
    return Message(message="Security preferences updated.")


@router.post("/passkey/add/options")
def add_passkey_options(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    options_json, handle = webauthn_service.start_registration(db, user)
    return {"handle": handle, "options": options_json}


@router.post("/passkey/add/verify", response_model=Message)
def add_passkey_verify(payload: PasskeyVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        webauthn_service.finish_registration(
            db, user, handle=payload.handle, credential_json=json.dumps(payload.credential),
            label="Added passkey",
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return Message(message="Passkey added.")
