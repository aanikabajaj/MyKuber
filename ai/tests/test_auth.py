"""Unit tests for ai.api.deps.get_ai_current_user.

Tests call the dependency function directly with mocked collaborators,
so no real database or JWT signing key is required.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from ai.api.deps import get_ai_current_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(*, is_active: bool = True, is_blocked: bool = False) -> MagicMock:
    """Return a MagicMock that looks like a User ORM instance."""
    user = MagicMock()
    user.id = 1
    user.is_active = is_active
    user.is_blocked = is_blocked
    return user


async def _call(
    authorization: str | None,
    decode_return: dict | None,
    db_get_return: MagicMock | None,
) -> MagicMock:
    """Invoke the dependency under test with mocked collaborators."""
    mock_db = MagicMock()
    mock_db.get.return_value = db_get_return

    with (
        patch("ai.api.deps.decode_token", return_value=decode_return),
        patch("ai.api.deps.get_readonly_db"),  # factory irrelevant; we pass db directly
    ):
        return await get_ai_current_user(authorization=authorization, db=mock_db)


# ---------------------------------------------------------------------------
# 1. Valid access token → user returned
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_token_returns_user() -> None:
    """A valid Bearer access token resolves to the active user."""
    user = _make_user()
    result = await _call(
        authorization="Bearer valid.jwt.token",
        decode_return={"sub": "1", "type": "access"},
        db_get_return=user,
    )
    assert result is user


# ---------------------------------------------------------------------------
# 2. Expired / invalid token → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_token_raises_401() -> None:
    """`decode_token` returning None (expired/bad sig) → HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        await _call(
            authorization="Bearer expired.jwt.token",
            decode_return=None,
            db_get_return=None,
        )
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 3. Missing Authorization header → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_authorization_header_raises_401() -> None:
    """No Authorization header → HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        await _call(
            authorization=None,
            decode_return=None,  # decode_token is never reached
            db_get_return=None,
        )
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 4. Wrong token type ("refresh") → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token_type_raises_401() -> None:
    """A refresh token must be rejected with HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        await _call(
            authorization="Bearer some.refresh.token",
            decode_return={"sub": "1", "type": "refresh"},
            db_get_return=None,
        )
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 5. Inactive user → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inactive_user_raises_403() -> None:
    """An access token for an inactive account → HTTP 403."""
    user = _make_user(is_active=False)
    with pytest.raises(HTTPException) as exc_info:
        await _call(
            authorization="Bearer valid.jwt.token",
            decode_return={"sub": "1", "type": "access"},
            db_get_return=user,
        )
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 6. Blocked user → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_blocked_user_raises_403() -> None:
    """An access token for a blocked account → HTTP 403."""
    user = _make_user(is_blocked=True)
    with pytest.raises(HTTPException) as exc_info:
        await _call(
            authorization="Bearer valid.jwt.token",
            decode_return={"sub": "1", "type": "access"},
            db_get_return=user,
        )
    assert exc_info.value.status_code == 403
