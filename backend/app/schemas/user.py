"""User profile / settings schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    full_name: str
    email: str
    mobile: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    username: str
    is_admin: bool
    second_factor: Optional[str] = None
    totp_enabled: bool
    face_enabled: bool
    email_verified: bool
    mobile_verified: bool
    # security preferences + banking
    face_login_enabled: bool = True
    face_txn_enabled: bool = True
    txn_face_threshold: int = 10000
    preferred_language: str = "en"
    account_number: Optional[str] = None
    balance: float = 0.0
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SecurityPrefsIn(BaseModel):
    face_login_enabled: Optional[bool] = None
    face_txn_enabled: Optional[bool] = None
    txn_face_threshold: Optional[int] = None
    preferred_language: Optional[str] = None


class DeviceOut(BaseModel):
    id: int
    label: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    timezone: Optional[str]
    last_ip: Optional[str]
    last_country: Optional[str]
    is_trusted: bool
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]

    class Config:
        from_attributes = True


class PasskeyOut(BaseModel):
    id: int
    label: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class LoginHistoryOut(BaseModel):
    id: int
    ip_address: Optional[str]
    country: Optional[str]
    city: Optional[str]
    risk_score: float
    risk_band: str
    decision: str
    success: bool
    is_vpn: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class MpinResetIn(BaseModel):
    current_password: str
    new_mpin: str


class FaceReenrollIn(BaseModel):
    embeddings: List[List[float]]


class FaceImagesReenrollIn(BaseModel):
    images: List[str]
