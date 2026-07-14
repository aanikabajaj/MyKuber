"""WebAuthn (passkey) registration & authentication ceremonies.

Wraps the `webauthn` (py_webauthn) library. Challenges are persisted in the
``pending_challenges`` table and referenced by an opaque handle the client
echoes back, so registration/verification survives across the two HTTP calls.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.user import User
from app.models.webauthn import PendingChallenge, WebAuthnCredential

logger = get_logger("iaare.webauthn")

CHALLENGE_TTL_SECONDS = 300


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _store_challenge(db: Session, *, user_id: Optional[int], purpose: str, challenge: bytes) -> str:
    handle = uuid.uuid4().hex
    db.add(
        PendingChallenge(
            id=handle,
            user_id=user_id,
            purpose=purpose,
            challenge=bytes_to_base64url(challenge),
            expires_at=_utcnow() + timedelta(seconds=CHALLENGE_TTL_SECONDS),
        )
    )
    db.commit()
    return handle


def _pop_challenge(db: Session, handle: str, purpose: str) -> Optional[bytes]:
    rec = db.get(PendingChallenge, handle)
    if rec is None or rec.purpose != purpose:
        return None
    expires = rec.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    challenge = base64url_to_bytes(rec.challenge)
    db.delete(rec)
    db.commit()
    if _utcnow() > expires:
        return None
    return challenge


def _user_credentials(db: Session, user_id: int) -> List[WebAuthnCredential]:
    return db.query(WebAuthnCredential).filter(WebAuthnCredential.user_id == user_id).all()


# --------------------------------------------------------------------------- #
#  Registration
# --------------------------------------------------------------------------- #
def start_registration(db: Session, user: User) -> Tuple[str, str]:
    existing = _user_credentials(db, user.id)
    options = generate_registration_options(
        rp_id=settings.RP_ID,
        rp_name=settings.RP_NAME,
        user_name=user.username,
        user_id=str(user.id).encode("utf-8"),
        user_display_name=user.full_name,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
            for c in existing
        ],
    )
    handle = _store_challenge(db, user_id=user.id, purpose="register", challenge=options.challenge)
    return options_to_json(options), handle


def finish_registration(
    db: Session, user: User, *, handle: str, credential_json: str, label: str = "Passkey"
) -> bool:
    challenge = _pop_challenge(db, handle, "register")
    if challenge is None:
        raise ValueError("Registration challenge expired or invalid.")

    verification = verify_registration_response(
        credential=credential_json,
        expected_challenge=challenge,
        expected_origin=settings.EXPECTED_ORIGIN,
        expected_rp_id=settings.RP_ID,
        require_user_verification=False,
    )
    cred = WebAuthnCredential(
        user_id=user.id,
        credential_id=bytes_to_base64url(verification.credential_id),
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=verification.sign_count,
        label=label,
    )
    db.add(cred)
    user.second_factor = "passkey"
    db.commit()
    logger.info("Passkey registered for user_id=%s", user.id)
    return True


# --------------------------------------------------------------------------- #
#  Authentication
# --------------------------------------------------------------------------- #
def start_authentication(db: Session, user: User) -> Tuple[str, str]:
    creds = _user_credentials(db, user.id)
    if not creds:
        raise ValueError("No passkey registered for this account.")
    options = generate_authentication_options(
        rp_id=settings.RP_ID,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
            for c in creds
        ],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    handle = _store_challenge(db, user_id=user.id, purpose="authenticate", challenge=options.challenge)
    return options_to_json(options), handle


def finish_authentication(db: Session, user: User, *, handle: str, credential_json: str) -> bool:
    import json

    challenge = _pop_challenge(db, handle, "authenticate")
    if challenge is None:
        raise ValueError("Authentication challenge expired or invalid.")

    parsed = json.loads(credential_json)
    raw_id = parsed.get("id") or parsed.get("rawId")
    stored = (
        db.query(WebAuthnCredential)
        .filter(WebAuthnCredential.user_id == user.id, WebAuthnCredential.credential_id == raw_id)
        .first()
    )
    if stored is None:
        raise ValueError("Unknown passkey credential.")

    verification = verify_authentication_response(
        credential=credential_json,
        expected_challenge=challenge,
        expected_rp_id=settings.RP_ID,
        expected_origin=settings.EXPECTED_ORIGIN,
        credential_public_key=base64url_to_bytes(stored.public_key),
        credential_current_sign_count=stored.sign_count,
        require_user_verification=False,
    )
    stored.sign_count = verification.new_sign_count
    db.commit()
    logger.info("Passkey authentication OK for user_id=%s", user.id)
    return True
