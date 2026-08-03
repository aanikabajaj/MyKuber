"""FastAPI dependencies for the AI Gateway.

Provides JWT authentication that re-uses the existing IAARE backend token
infrastructure.  The AI module NEVER issues, refreshes, or stores tokens —
it only validates them.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

# Import decode_token from the IAARE backend (PYTHONPATH includes workspace root,
# so `app.core.security` resolves to backend/app/core/security.py).
from app.core.security import decode_token

# User model lives in the existing backend — read-only access only.
from app.models.user import User

# Read-only session factory for the IAARE database.
from ai.database.ai_db import get_readonly_db

_WWW_AUTH = {"WWW-Authenticate": "Bearer"}


def _extract_bearer(authorization: str | None) -> str:
    """Strip the ``Bearer `` prefix from the Authorization header value.

    Raises HTTP 401 when the header is absent or does not start with
    ``Bearer `` (case-insensitive prefix check).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers=_WWW_AUTH,
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers=_WWW_AUTH,
        )
    return token


async def get_ai_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_readonly_db),
) -> User:
    """FastAPI dependency: authenticate the request via the existing IAARE JWT.

    Steps
    -----
    1. Extract the Bearer token from the ``Authorization`` header.
    2. Decode + verify the token using ``decode_token`` (same secret/algorithm
       as the IAARE backend).  Returns ``None`` on any JWT error.
    3. Require ``payload["type"] == "access"`` — refresh or registration tokens
       are rejected.
    4. Load the ``User`` record from the IAARE database using the ``sub`` claim.
    5. Reject inactive (``is_active=False``) or blocked (``is_blocked=True``)
       accounts with HTTP 403.

    Returns
    -------
    User
        The authenticated, active, unblocked ``User`` ORM instance.

    Raises
    ------
    HTTPException(401)
        Token absent, malformed, expired, or not of type ``"access"``.
    HTTPException(403)
        Token valid but the account is inactive or blocked.
    """
    token = _extract_bearer(authorization)

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers=_WWW_AUTH,
        )

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers=_WWW_AUTH,
        )

    if user.is_active is False or user.is_blocked is True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or blocked.",
        )

    return user
