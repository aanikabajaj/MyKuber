"""Adaptive Risk Assessment Engine.

Produces a 0-100 risk score from device, network, geography and behavioural
signals, together with a fully transparent per-factor breakdown (so the UI can
explain *why* a login was scored the way it was) and the ordered list of
authentication factors the score demands.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.services.geoip_service import GeoInfo

# --- Band thresholds -------------------------------------------------------- #
BAND_THRESHOLDS = [
    (30, "SAFE"),
    (60, "MEDIUM"),
    (80, "HIGH"),
    (100, "CRITICAL"),
]

# --- Auth factor chain per band (password already verified upstream) -------- #
BAND_STEPS = {
    "SAFE": ["mpin", "second_factor"],
    "MEDIUM": ["mpin", "second_factor", "email_otp"],
    "HIGH": ["mpin", "second_factor", "email_otp", "sms_otp", "totp"],
    "CRITICAL": [],  # blocked
}

BAND_DECISION = {
    "SAFE": "ALLOW",
    "MEDIUM": "STEP_UP",
    "HIGH": "STEP_UP",
    "CRITICAL": "BLOCK",
}


@dataclass
class Factor:
    name: str
    points: int
    detail: str


@dataclass
class RiskResult:
    score: int
    band: str
    decision: str
    factors: List[Factor] = field(default_factory=list)
    required_steps: List[str] = field(default_factory=list)
    geo: Optional[dict] = None

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "band": self.band,
            "decision": self.decision,
            "required_steps": self.required_steps,
            "factors": [f.__dict__ for f in self.factors],
            "geo": self.geo,
        }


def band_for_score(score: int) -> str:
    for upper, band in BAND_THRESHOLDS:
        if score <= upper:
            return band
    return "CRITICAL"


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _last_successful_login(db: Session, user_id: int) -> Optional[LoginAttempt]:
    return (
        db.query(LoginAttempt)
        .filter(LoginAttempt.user_id == user_id, LoginAttempt.success.is_(True))
        .order_by(LoginAttempt.created_at.desc())
        .first()
    )


def assess(
    db: Session,
    user: User,
    *,
    geo: GeoInfo,
    trusted_device: bool,
    known_device_exists: bool,
    failed_attempts: int,
    now: Optional[datetime] = None,
) -> RiskResult:
    now = now or datetime.now(timezone.utc)
    factors: List[Factor] = []
    score = 0

    # 1) Device trust
    if not known_device_exists:
        score += 30
        factors.append(Factor("new_device", 30, "Login from an unrecognised device"))
    elif not trusted_device:
        score += 20
        factors.append(Factor("untrusted_device", 20, "Device is known but not trusted"))
    else:
        factors.append(Factor("trusted_device", 0, "Recognised, trusted device"))

    # 2) VPN / proxy / hosting
    if geo.is_vpn:
        score += 25
        factors.append(Factor("vpn_detected", 25, f"VPN/proxy or datacenter IP ({geo.isp or 'unknown ISP'})"))
    else:
        factors.append(Factor("no_vpn", 0, "No VPN/proxy detected"))

    # 3) Failed recent attempts
    if failed_attempts > 0:
        pts = min(failed_attempts * 7, 21)
        score += pts
        factors.append(Factor("failed_attempts", pts, f"{failed_attempts} recent failed attempt(s)"))

    # 4) Country risk vs registered home country
    home = (user.country or "").strip().lower()
    current = (geo.country or "").strip().lower()
    if home and current and home != current:
        score += 15
        factors.append(Factor("foreign_country", 15, f"Login country '{geo.country}' differs from home '{user.country}'"))

    # 5) Impossible travel vs last successful login
    last = _last_successful_login(db, user.id)
    if (
        last is not None
        and last.latitude is not None
        and last.longitude is not None
        and geo.latitude is not None
        and geo.longitude is not None
    ):
        last_time = last.created_at
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        hours = max((now - last_time).total_seconds() / 3600.0, 0.01)
        dist = _haversine_km(last.latitude, last.longitude, geo.latitude, geo.longitude)
        speed = dist / hours
        if dist > 500 and speed > 900:  # faster than a commercial jet
            score += 30
            factors.append(
                Factor("impossible_travel", 30,
                       f"{int(dist)} km in {hours:.1f} h (~{int(speed)} km/h) since last login")
            )
        elif last.country and geo.country and last.country.lower() != geo.country.lower():
            score += 10
            factors.append(Factor("new_location", 10, f"Different country than last login ({last.country})"))
    elif last is None:
        score += 5
        factors.append(Factor("first_login", 5, "No prior successful login on record"))

    # 6) Odd-hour heuristic (00:00–05:00 local-ish, using server UTC as proxy)
    if 0 <= now.hour < 5:
        score += 5
        factors.append(Factor("odd_hour", 5, f"Unusual login hour ({now.hour:02d}:00 UTC)"))

    score = max(0, min(100, score))
    band = band_for_score(score)
    return RiskResult(
        score=score,
        band=band,
        decision=BAND_DECISION[band],
        factors=factors,
        required_steps=list(BAND_STEPS[band]),
        geo=geo.as_dict(),
    )
