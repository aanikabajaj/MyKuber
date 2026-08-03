"""Tests for ai/agents/response_formatter.py — Tasks 17.1–17.6.

Four unit tests:
1. All 8 required keys present in formatted_response.
2. confidence defaults to 0.0 when llm_confidence is None.
3. session_id always included (even when empty string).
4. charts, portfolio, recommendations, citations are always lists (never None).
"""
from __future__ import annotations

import pytest

from ai.agents.response_formatter import REQUIRED_KEYS, response_formatter_node
from ai.orchestrator.state import initial_state


# ---------------------------------------------------------------------------
# Test 1 — All 8 required keys present in formatted_response
# ---------------------------------------------------------------------------


def test_all_required_keys_present():
    """formatted_response must contain all 8 required keys."""
    state = initial_state(user_id=1, raw_query="test", request_id="rf1")
    state["llm_response"] = "Your financial summary."
    state["llm_confidence"] = 0.75

    result = response_formatter_node(state)
    formatted = result["formatted_response"]

    for key in REQUIRED_KEYS:
        assert key in formatted, f"Required key '{key}' missing from formatted_response"


# ---------------------------------------------------------------------------
# Test 2 — confidence defaults to 0.0 when llm_confidence is None
# ---------------------------------------------------------------------------


def test_confidence_defaults_to_zero_when_none():
    """When llm_confidence is None, confidence in formatted_response must be 0.0."""
    state = initial_state(user_id=1, raw_query="test", request_id="rf2")
    state["llm_response"] = "Some advice."
    state["llm_confidence"] = None  # type: ignore[assignment]

    result = response_formatter_node(state)
    formatted = result["formatted_response"]

    assert formatted["confidence"] == 0.0, (
        f"Expected confidence=0.0 when llm_confidence is None, got {formatted['confidence']}"
    )
    assert isinstance(formatted["confidence"], float), "confidence must be a float"


# ---------------------------------------------------------------------------
# Test 3 — session_id always included (even as empty string)
# ---------------------------------------------------------------------------


def test_session_id_always_present():
    """session_id key must always be in formatted_response, even if it's an empty string."""
    state = initial_state(user_id=1, raw_query="test", request_id="rf3")
    # session_id not provided → should default to ""
    state["llm_response"] = "Advice text."

    result = response_formatter_node(state)
    formatted = result["formatted_response"]

    assert "session_id" in formatted, "session_id must always be present in formatted_response"
    # It must be a string (empty or a real UUID)
    assert isinstance(formatted["session_id"], str), "session_id must be a string"


def test_session_id_preserved_when_provided():
    """When a session_id is supplied it must appear verbatim in the formatted_response."""
    sid = "550e8400-e29b-41d4-a716-446655440000"
    state = initial_state(user_id=1, raw_query="test", request_id="rf3b", session_id=sid)
    state["llm_response"] = "Advice text."

    result = response_formatter_node(state)
    formatted = result["formatted_response"]

    assert formatted["session_id"] == sid, (
        f"Expected session_id={sid!r}, got {formatted['session_id']!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — charts, portfolio, recommendations, citations are always lists
# ---------------------------------------------------------------------------


def test_array_fields_are_always_lists():
    """charts, portfolio, recommendations, citations must always be lists (never None)."""
    state = initial_state(user_id=1, raw_query="test", request_id="rf4")
    state["llm_response"] = "Summary."
    state["llm_confidence"] = 0.5
    # Leave analytics_result, portfolio_result, safe_response all unset / None

    result = response_formatter_node(state)
    formatted = result["formatted_response"]

    for arr_key in ("charts", "portfolio", "recommendations", "citations"):
        assert isinstance(formatted[arr_key], list), (
            f"'{arr_key}' must be a list, got {type(formatted[arr_key])!r}"
        )
        # Must not be None
        assert formatted[arr_key] is not None, f"'{arr_key}' must not be None"


def test_portfolio_populated_from_portfolio_result():
    """When portfolio_result has weights, portfolio list must be populated."""
    state = initial_state(user_id=1, raw_query="test", request_id="rf4b")
    state["llm_response"] = "Portfolio advice."
    state["llm_confidence"] = 0.9
    state["portfolio_result"] = {"weights": {"RELIANCE": 0.45, "INFY": 0.55}}

    result = response_formatter_node(state)
    formatted = result["formatted_response"]

    assert isinstance(formatted["portfolio"], list), "portfolio must be a list"
    assert len(formatted["portfolio"]) == 2, "portfolio must have 2 assets"
    assets = {entry["asset"] for entry in formatted["portfolio"]}
    assert assets == {"RELIANCE", "INFY"}
