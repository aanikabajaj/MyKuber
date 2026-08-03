"""PII masking utilities for the Wealth Intelligence AI Platform.

Provides:
- mask_account_number: prefix-masks all but the last 4 digits.
- bucket_balance: maps a raw float balance to a privacy-safe range label.
- mask_pii_in_text: redacts Indian mobile numbers, email addresses, and
  9–18 digit account numbers from free-form text.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Account number masking
# ---------------------------------------------------------------------------


def mask_account_number(account: str | None) -> str:
    """Return ``****{last4}`` for *account*.

    Parameters
    ----------
    account:
        Raw account number string.  May be ``None`` or shorter than 4 chars.

    Returns
    -------
    str
        A masked string of the form ``****XXXX`` where ``XXXX`` is the last
        4 characters of *account*.  Falls back to ``"****0000"`` when the
        input is ``None`` or has fewer than 4 characters.
    """
    if not account or len(account) < 4:
        return "****0000"
    return f"****{account[-4:]}"


# ---------------------------------------------------------------------------
# Balance buckets
# ---------------------------------------------------------------------------

BALANCE_BUCKETS: list[tuple[float, float, str]] = [
    (0,          10_000,     "< ₹10k"),
    (10_000,     50_000,     "₹10k–₹50k"),
    (50_000,     100_000,    "₹50k–₹1L"),
    (100_000,    500_000,    "₹1L–₹5L"),
    (500_000,    1_000_000,  "₹5L–₹10L"),
    (1_000_000,  float("inf"), "> ₹10L"),
]


def bucket_balance(balance: float) -> str:
    """Map *balance* (INR, non-negative float) to a privacy-safe range label.

    Uses a half-open interval ``[low, high)`` for each bucket so boundaries
    belong to exactly one range.  Any value ≥ ₹10 lakh returns ``"> ₹10L"``.
    """
    for low, high, label in BALANCE_BUCKETS:
        if low <= balance < high:
            return label
    return "> ₹10L"


# ---------------------------------------------------------------------------
# Free-text PII regex patterns
# ---------------------------------------------------------------------------

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    # Indian mobile numbers: 10-digit, starting with 6–9
    "mobile_number": re.compile(r"\b[6-9]\d{9}\b"),
    # Email addresses
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    # Bank account numbers: 9–18 consecutive digits
    "account_full": re.compile(r"\b\d{9,18}\b"),
}


def mask_pii_in_text(text: str) -> str:
    """Return *text* with all detectable PII replaced by safe placeholders.

    Substitutions applied in order:
    1. Indian mobile numbers  → ``[MOBILE REDACTED]``
    2. Email addresses        → ``[EMAIL REDACTED]``
    3. 9–18 digit sequences   → ``[ACCOUNT REDACTED]``

    The ordering matters: mobile numbers are replaced before the generic
    digit pattern so they receive the more specific label.
    """
    text = PII_PATTERNS["mobile_number"].sub("[MOBILE REDACTED]", text)
    text = PII_PATTERNS["email"].sub("[EMAIL REDACTED]", text)
    text = PII_PATTERNS["account_full"].sub("[ACCOUNT REDACTED]", text)
    return text
