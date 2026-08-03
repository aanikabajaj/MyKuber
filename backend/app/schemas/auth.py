"""Request/response schemas for registration and adaptive login."""
from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# --------------------------------------------------------------------------- #
#  Shared
# --------------------------------------------------------------------------- #
class DeviceInfo(BaseModel):
    fingerprint: str = Field(..., min_length=6, max_length=128)
    browser: Optional[str] = None
    os: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    screen_resolution: Optional[str] = None
    user_agent: Optional[str] = None
    label: Optional[str] = None


class SimulatedContext(BaseModel):
    """Optional demo override so a presenter can force any risk scenario."""
    enabled: bool = False
    ip: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_vpn: Optional[bool] = None
    failed_attempts: Optional[int] = None
    new_device: Optional[bool] = None
    force_band: Optional[str] = None


class Message(BaseModel):
    message: str
    detail: Optional[str] = None


# --------------------------------------------------------------------------- #
#  Registration
# --------------------------------------------------------------------------- #
STRONG_PW = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$"
)


class RegisterDetails(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    dob: Optional[str] = None
    gender: Optional[str] = None
    email: EmailStr
    mobile: str = Field(..., min_length=8, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pin_code: Optional[str] = None
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.]+$")
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        if not STRONG_PW.match(v):
            raise ValueError(
                "Password must be 8+ chars with upper, lower, number and symbol."
            )
        return v

    @field_validator("confirm_password")
    @classmethod
    def _match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v


class RegisterDetailsOut(BaseModel):
    user_id: int
    registration_token: str
    stage: str


class OtpSendOut(BaseModel):
    channel: str
    destination_masked: str
    provider: str
    dev_code: Optional[str] = None   # present only in DEMO_MODE
    message: str


class OtpVerifyIn(BaseModel):
    code: str = Field(..., min_length=4, max_length=8)


class AuthenticatorSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    qr_data_uri: str


class MpinIn(BaseModel):
    mpin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class FaceEnrollIn(BaseModel):
    embeddings: List[List[float]] = Field(..., min_length=1)


class FaceImagesEnrollIn(BaseModel):
    images: List[str] = Field(..., min_length=1)


class StepFaceImageIn(BaseModel):
    session_id: str
    image: str


class PasskeyVerifyIn(BaseModel):
    handle: str
    credential: dict


class StageOut(BaseModel):
    stage: str
    complete: bool


# --------------------------------------------------------------------------- #
#  SIM verification schemas
# --------------------------------------------------------------------------- #
class SimEnrollIn(BaseModel):
    """SHA-256 hex fingerprint of the device's SIM hardware fields."""
    sim_fingerprint: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
        description="SHA-256 hex of (carrier_name + mcc + mnc + country_iso)",
    )


class SimVerifyConfirmIn(OtpVerifyIn):
    """OTP code + optional SIM fingerprint sent together at registration."""
    sim_fingerprint: Optional[str] = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
    )


class StepSimVerifyIn(BaseModel):
    """SIM fingerprint submitted during the sim_check login step."""
    session_id: str
    sim_fingerprint: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
        description="SHA-256 hex of the SIM hardware fields on the current device",
    )


# --------------------------------------------------------------------------- #
#  Login
# --------------------------------------------------------------------------- #
class LoginPasswordIn(BaseModel):
    username: str
    password: str
    captcha_id: str
    captcha_answer: str
    device: DeviceInfo
    simulate: Optional[SimulatedContext] = None


class RiskFactorOut(BaseModel):
    name: str
    points: int
    detail: str


class RiskOut(BaseModel):
    score: int
    band: str
    decision: str
    factors: List[RiskFactorOut]
    geo: Optional[dict] = None


class LoginSessionOut(BaseModel):
    session_id: Optional[str] = None
    status: str
    risk: RiskOut
    required_steps: List[str]
    completed_steps: List[str]
    next_step: Optional[str]
    second_factor: Optional[str]
    user_display: Optional[str] = None
    message: Optional[str] = None
    tokens: Optional[dict] = None


class StepMpinIn(BaseModel):
    session_id: str
    mpin: str


class StepOtpVerifyIn(BaseModel):
    session_id: str
    code: str


class StepTotpIn(BaseModel):
    session_id: str
    token: str


class StepFaceIn(BaseModel):
    session_id: str
    embedding: List[float]


class StepPasskeyOptionsIn(BaseModel):
    session_id: str


class StepPasskeyVerifyIn(BaseModel):
    session_id: str
    handle: str
    credential: dict


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshIn(BaseModel):
    refresh_token: str


class CaptchaOut(BaseModel):
    captcha_id: str
    image: str
