"""Small shared helpers."""
from __future__ import annotations


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked = local[0] + "*"
    else:
        masked = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked}@{domain}"


def mask_phone(phone: str) -> str:
    if not phone:
        return ""
    digits = phone[-4:]
    return "*" * max(0, len(phone) - 4) + digits
