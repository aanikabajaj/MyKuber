"""Admin dashboard schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AdminStats(BaseModel):
    total_users: int
    logins_today: int
    blocked_logins: int
    high_risk_logins: int
    total_devices: int
    active_sessions: int


class RiskBucket(BaseModel):
    band: str
    count: int


class AuthStat(BaseModel):
    factor: str
    count: int


class LoginRow(BaseModel):
    id: int
    username: Optional[str]
    ip_address: Optional[str]
    country: Optional[str]
    city: Optional[str]
    risk_score: float
    risk_band: str
    decision: str
    success: bool
    is_vpn: bool
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class AuditRow(BaseModel):
    id: int
    event_type: str
    description: str
    severity: str
    ip_address: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class MapPoint(BaseModel):
    latitude: float
    longitude: float
    city: Optional[str]
    country: Optional[str]
    risk_band: str
    count: int
