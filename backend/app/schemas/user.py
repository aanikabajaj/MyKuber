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
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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
    embedding: List[float]
