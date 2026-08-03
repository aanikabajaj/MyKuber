"""Central application configuration.

All settings can be overridden via environment variables prefixed with
``IAARE_`` or a ``.env`` file. The application is designed to run fully
without any .env file (demo mode), so the prototype works out of the box.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IAARE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core ---
    PROJECT_NAME: str = "IAARE"
    PROJECT_DESCRIPTION: str = (
        "Intelligent Adaptive Authentication & Risk Assessment Engine"
    )
    VERSION: str = "2.0.0"
    SECRET_KEY: str = "iaare-dev-secret-key-change-in-production-0123456789"
    DEMO_MODE: bool = True

    # --- JWT ---
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./iaare.db"

    # --- WebAuthn ---
    RP_ID: str = "localhost"
    RP_NAME: str = "IAARE - Punjab & Sind Bank"
    EXPECTED_ORIGIN: str = "http://localhost:5173"

    # --- CORS (web app :5173, Expo web :8081/:19006) ---
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8081,http://127.0.0.1:8081,"
        "http://localhost:19006,http://127.0.0.1:19006"
    )

    # --- OTP ---
    OTP_LENGTH: int = 6
    OTP_TTL_SECONDS: int = 300  # 5 minutes
    OTP_MAX_ATTEMPTS: int = 5

    # --- Email (SMTP) ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "IAARE Security <no-reply@iaare.bank>"

    # --- SMS (Twilio) ---
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # --- SMS (Fast2SMS — India free tier, alternative to Twilio) ---
    # Sign up at https://www.fast2sms.com → Dashboard → Dev API → API Key
    FAST2SMS_API_KEY: str = ""

    # --- GeoIP ---
    GEOIP_ENABLED: bool = True

    # --- Rate limiting ---
    RATE_LIMIT_MAX_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize the legacy `postgres://` scheme some hosts (Render, Heroku)
        still hand out — SQLAlchemy 1.4+ only recognizes `postgresql://`."""
        if self.DATABASE_URL.startswith("postgres://"):
            return "postgresql://" + self.DATABASE_URL[len("postgres://"):]
        return self.DATABASE_URL

    @property
    def fernet_key(self) -> bytes:
        """Derive a stable Fernet key from SECRET_KEY.

        This means encrypted secrets survive restarts without needing a
        separately managed key, while still being real Fernet encryption.
        """
        digest = hashlib.sha256(self.SECRET_KEY.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
