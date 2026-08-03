"""Fund-transfer logic with amount-threshold Face-ID step-up."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.transaction import Transaction
from app.models.user import User
from app.services import audit_service, face_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _reference() -> str:
    return "TXN" + secrets.token_hex(6).upper()


def _requires_stepup(user: User, amount: float) -> bool:
    """Biometric/face step-up when the amount meets the user's threshold.

    Gated only on the user's Wealth Protection preference (face_txn_enabled +
    txn_face_threshold) — NOT on `second_factor`, which is a separate,
    registration-time login-MFA choice ('face' | 'passkey' | 'biometric')
    that the transaction step-up toggle never touches. Requiring it here
    silently skipped step-up for any account whose second_factor wasn't
    exactly 'face'/'biometric' (e.g. NULL from incomplete registration, or
    'passkey'), even with the toggle on.
    """
    return bool(user.face_txn_enabled and amount >= (user.txn_face_threshold or 0))


def _stepup_factor(user: User) -> str:
    """Pick which verification the step-up should ask for.

    Use face-scan when the user has an enrolled face template (so it can
    actually be matched); otherwise fall back to on-device biometric trust.
    """
    return "face" if (user.face_enabled and user.face_embedding_enc) else "biometric"


def initiate_transfer(
    db: Session,
    user: User,
    *,
    beneficiary_name: str,
    beneficiary_account: str,
    amount: float,
    note: Optional[str] = None,
) -> dict:
    needs_stepup = _requires_stepup(user, amount)
    factor = _stepup_factor(user) if needs_stepup else None
    txn = Transaction(
        user_id=user.id,
        beneficiary_name=beneficiary_name,
        beneficiary_account=beneficiary_account,
        amount=amount,
        note=note,
        reference=_reference(),
        status="pending",
        step_up_required=needs_stepup,
        step_up_factor=factor,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    if needs_stepup:
        audit_service.log_event(
            db, event_type="txn_step_up",
            description=f"Transfer {txn.reference} of Rs.{amount:.0f} needs {factor} (>= Rs.{user.txn_face_threshold})",
            user_id=user.id, meta={"reference": txn.reference, "amount": amount},
        )
        return {
            "status": "step_up_required",
            "requires": factor,  # 'face' or 'biometric'
            "reference": txn.reference,
            "amount": amount,
            "threshold": user.txn_face_threshold,
            "message": f"Verification required for transfers of Rs.{user.txn_face_threshold:,} or more.",
        }
    return _complete(db, user, txn)


def _complete(db: Session, user: User, txn: Transaction) -> dict:
    if user.balance < txn.amount:
        txn.status = "failed"
        db.commit()
        return {
            "status": "failed",
            "reference": txn.reference,
            "message": "Insufficient balance for this transfer.",
            "balance": round(user.balance, 2),
        }
    user.balance = round(user.balance - txn.amount, 2)
    txn.status = "completed"
    txn.balance_after = user.balance
    txn.completed_at = _utcnow()
    db.commit()
    audit_service.log_event(
        db, event_type="txn_completed",
        description=f"Transfer {txn.reference} of Rs.{txn.amount:.0f} to {txn.beneficiary_name} completed",
        user_id=user.id, meta={"reference": txn.reference, "amount": txn.amount},
    )
    return {
        "status": "completed",
        "reference": txn.reference,
        "message": "Transfer completed successfully.",
        "balance": user.balance,
        "amount": txn.amount,
    }


def verify_face_and_complete(db: Session, user: User, *, reference: str, embedding: List[float]) -> dict:
    txn = (
        db.query(Transaction)
        .filter(Transaction.reference == reference, Transaction.user_id == user.id)
        .first()
    )
    if txn is None:
        raise ValueError("Transaction not found.")
    if txn.status != "pending":
        raise ValueError(f"Transaction already {txn.status}.")

    demo_ok = settings.DEMO_MODE and user.is_demo
    if demo_ok:
        ok, sim = True, 1.0
    else:
        ok, sim = face_service.compare(user.face_embedding_enc, embedding)
    if not ok:
        raise ValueError(f"Face not recognised (similarity {sim}). Transfer not authorised.")

    return _complete(db, user, txn)


def verify_biometric_and_complete(db: Session, user: User, *, reference: str) -> dict:
    """Complete a pending transfer after a successful on-device biometric.

    Trust-on-device: the mobile app already performed the native Face ID /
    fingerprint check via the OS. (Production upgrade: bind to a device key +
    attestation so the assertion can't be forged by a modified client.)
    """
    txn = (
        db.query(Transaction)
        .filter(Transaction.reference == reference, Transaction.user_id == user.id)
        .first()
    )
    if txn is None:
        raise ValueError("Transaction not found.")
    if txn.status != "pending":
        raise ValueError(f"Transaction already {txn.status}.")
    return _complete(db, user, txn)
