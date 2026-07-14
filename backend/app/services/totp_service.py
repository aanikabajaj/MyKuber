"""Google-Authenticator-compatible TOTP (RFC 6238) via PyOTP."""
from __future__ import annotations

import base64
from io import BytesIO

import pyotp
import qrcode

from app.core.config import settings
from app.core.encryption import decrypt_str, encrypt_str


def generate_secret() -> str:
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    return encrypt_str(secret)


def provisioning_uri(secret: str, account_name: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=account_name, issuer_name=settings.RP_NAME
    )


def qr_data_uri(secret: str, account_name: str) -> str:
    """Return a base64 PNG data-URI of the provisioning QR code."""
    uri = provisioning_uri(secret, account_name)
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def verify_token(encrypted_secret: str, token: str, *, plain_secret: str = "") -> bool:
    secret = plain_secret or decrypt_str(encrypted_secret)
    if not secret:
        return False
    # valid_window=1 tolerates ~30s clock drift each way.
    return pyotp.TOTP(secret).verify(token.strip(), valid_window=1)
