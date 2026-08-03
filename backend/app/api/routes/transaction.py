"""Fund-transfer endpoints with Face-ID step-up."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.core.config import settings
from app.schemas.transaction import (
    TransactionOut,
    TransferIn,
    TransferOut,
    TxnBiometricVerifyIn,
    TxnFaceImageVerifyIn,
    TxnFaceVerifyIn,
)
from app.services import face_service, transaction_service

router = APIRouter(prefix="/api/txn", tags=["transactions"])


@router.get("/balance")
def get_balance(user: User = Depends(get_current_user)):
    return {
        "balance": user.balance,
        "account_number": user.account_number,
        "currency": "INR",
        "face_txn_enabled": user.face_txn_enabled,
        "txn_face_threshold": user.txn_face_threshold,
    }


@router.post("/transfer", response_model=TransferOut)
def transfer(payload: TransferIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = transaction_service.initiate_transfer(
        db, user,
        beneficiary_name=payload.beneficiary_name,
        beneficiary_account=payload.beneficiary_account,
        amount=payload.amount,
        note=payload.note,
    )
    return TransferOut(**result)


@router.post("/verify-face", response_model=TransferOut)
def verify_face(payload: TxnFaceVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = transaction_service.verify_face_and_complete(
            db, user, reference=payload.reference, embedding=payload.embedding
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return TransferOut(**result)


@router.post("/verify-face-image", response_model=TransferOut)
def verify_face_image(payload: TxnFaceImageVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    embedding = face_service.embedding_from_image_b64(payload.image)
    if not embedding and not (settings.DEMO_MODE and user.is_demo):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "No clear face detected. Center your face and try again.")
    try:
        result = transaction_service.verify_face_and_complete(db, user, reference=payload.reference, embedding=embedding)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return TransferOut(**result)


@router.post("/verify-biometric", response_model=TransferOut)
def verify_biometric(payload: TxnBiometricVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = transaction_service.verify_biometric_and_complete(db, user, reference=payload.reference)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return TransferOut(**result)


@router.get("/history", response_model=List[TransactionOut])
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .limit(50)
        .all()
    )
