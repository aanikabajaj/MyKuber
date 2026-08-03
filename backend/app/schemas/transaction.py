"""Transaction / fund-transfer schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TransferIn(BaseModel):
    beneficiary_name: str = Field(..., min_length=2, max_length=120)
    beneficiary_account: str = Field(..., min_length=4, max_length=30)
    amount: float = Field(..., gt=0)
    note: Optional[str] = None


class TransferOut(BaseModel):
    status: str            # 'completed' | 'step_up_required' | 'failed'
    reference: str
    requires: Optional[str] = None   # 'face' when biometric step-up is needed
    message: str
    balance: Optional[float] = None
    threshold: Optional[int] = None
    amount: Optional[float] = None


class TxnFaceVerifyIn(BaseModel):
    reference: str
    embedding: List[float]


class TxnBiometricVerifyIn(BaseModel):
    reference: str


class TxnFaceImageVerifyIn(BaseModel):
    reference: str
    image: str


class TransactionOut(BaseModel):
    id: int
    beneficiary_name: str
    beneficiary_account: str
    amount: float
    note: Optional[str]
    status: str
    step_up_required: bool
    step_up_factor: Optional[str]
    reference: str
    balance_after: Optional[float]
    created_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
