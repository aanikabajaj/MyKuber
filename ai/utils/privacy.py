"""Privacy utilities for the Wealth Intelligence AI Platform.

Provides deterministic one-way hashing so that query text is never stored
in plain form in execution traces or log records.
"""
from __future__ import annotations

import hashlib


def hash_query(query: str) -> str:
    """Return the SHA-256 hex digest of *query* encoded as UTF-8.

    Parameters
    ----------
    query:
        The raw query string to hash.

    Returns
    -------
    str
        A 64-character lowercase hexadecimal string (256-bit digest).
    """
    return hashlib.sha256(query.encode("utf-8")).hexdigest()
