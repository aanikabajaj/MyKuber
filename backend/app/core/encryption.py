"""Symmetric encryption for secrets at rest (TOTP secrets, face embeddings)."""
from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_fernet = Fernet(settings.fernet_key)


def encrypt_str(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_str(ciphertext: str) -> str:
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def encrypt_json(data: Any) -> str:
    return encrypt_str(json.dumps(data))


def decrypt_json(ciphertext: str) -> Any:
    raw = decrypt_str(ciphertext)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
