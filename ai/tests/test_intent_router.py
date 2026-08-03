"""Unit tests for ai.agents.intent_router (Task 7.5).

All tests use mocking to avoid loading the real sentence-transformer model.
The INTENT_CENTROIDS dict and the model's encode method are patched with
synthetic numpy vectors so tests run fast and deterministically.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers to build synthetic centroid fixtures
# ---------------------------------------------------------------------------

# We need 13 intents.  We assign each intent a unit vector in a distinct
# direction so cosine-similarity maths is predictable.
_INTENTS = [
    "Portfolio_Review",
    "Portfolio_Rebalancing",
    "Transaction_Analysis",
    "Budgeting",
    "Savings",
    "Goal_Planning",
    "Investment_Education",
    "Taxation",
    "Banking",
    "Insurance",
    "Pension",
    "Market_News",
    "Account_Summary",
]

_DIM = 16  # small dimension sufficient for unit tests


def _make_unit_vec(idx: int, dim: int = _DIM) -> np.ndarray:
    """Return a unit vector with a 1 at position `idx % dim`."""
    v = np.zeros(dim, dtype=np.float32)
    v[idx % dim] = 1.0
    return v


# Synthetic centroids: each intent has a unique axis-aligned unit vector.
_FAKE_CENTROIDS: dict[str, np.ndarray] = {
    intent: _make_unit_vec(i) for i, intent in enumerate(_INTENTS)
}


def _fake_encode(sentences: list[str], convert_to_numpy: bool = True) -> np.ndarray:
    """Deterministic mock encoder based on keyword matching.

    Returns a high-similarity vector for whichever intent's keywords appear
    in the query, or a near-zero vector to trigger the fallback.
    """
    query = sentences[0].lower() if sentences else ""

    # Keyword → intent index mapping for the tests we care about.
    keyword_map = {
        "portfolio": 0,    # Portfolio_Review
        "spending": 2,     # Transaction_Analysis
        "analyse my spending": 2,
        "budg": 3,         # Budgeting
    }
    for kw, idx in keyword_map.items():
        if kw in query:
            # Return a vector 0.8-similar to the target centroid direction.
            return np.array([0.8 * _make_unit_vec(idx)], dtype=np.float32)

    # Garbage / no match → near-zero so max similarity < 0.5 → fallback.
    tiny = np.full(_DIM, 1e-6, dtype=np.float32)
    return np.array([tiny])


# ---------------------------------------------------------------------------
# Test fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_model_and_centroids(monkeypatch):
    """Patch INTENT_CENTROIDS and the model's encode method for every test."""
    import ai.agents.intent_router as ir

    # Replace centroids with synthetic ones.
    monkeypatch.setattr(ir, "INTENT_CENTROIDS", _FAKE_CENTROIDS)

    # Replace (or create) the module-level _MODEL with our mock.
    mock_model = MagicMock()
    mock_model.encode.side_effect = _fake_encode
    monkeypatch.setattr(ir, "_MODEL", mock_model)

    yield


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_portfolio_query_maps_to_portfolio_review():
    """'what should I do with my portfolio' → Portfolio_Review."""
    import ai.agents.intent_router as ir

    result = ir._classify("what should I do with my portfolio")
    assert result["intent"] == "Portfolio_Review", (
        f"Expected Portfolio_Review, got {result['intent']}"
    )


def test_spending_query_maps_to_transaction_analysis_or_budgeting():
    """'analyse my spending this month' → Transaction_Analysis or Budgeting."""
    import ai.agents.intent_router as ir

    result = ir._classify("analyse my spending this month")
    assert result["intent"] in ("Transaction_Analysis", "Budgeting"), (
        f"Expected Transaction_Analysis or Budgeting, got {result['intent']}"
    )


def test_garbage_string_falls_back_to_banking():
    """A nonsense string that matches no intent centroid → fallback 'Banking'."""
    import ai.agents.intent_router as ir

    result = ir._classify("zzzzqqqqxxx gibberish 12345")
    assert result["intent"] == "Banking", (
        f"Expected Banking fallback, got {result['intent']}"
    )


def test_confidence_always_in_unit_interval():
    """confidence is always a float in [0.0, 1.0]."""
    import ai.agents.intent_router as ir

    for query in [
        "what should I do with my portfolio",
        "analyse my spending this month",
        "zzzzqqqqxxx gibberish 12345",
        "",
        "a",
    ]:
        result = ir._classify(query)
        conf = result.get("confidence", -1.0)
        assert isinstance(conf, float), f"confidence should be float, got {type(conf)}"
        assert 0.0 <= conf <= 1.0, (
            f"confidence {conf} is out of [0.0, 1.0] for query {query!r}"
        )


def test_services_returned_for_valid_intent():
    """The result always includes a non-empty services list for a known intent."""
    import ai.agents.intent_router as ir

    result = ir._classify("what should I do with my portfolio")
    assert isinstance(result["services"], list)
    assert len(result["services"]) > 0


def test_all_intents_structure():
    """all_intents contains one entry per intent with label and confidence keys."""
    import ai.agents.intent_router as ir

    result = ir._classify("what should I do with my portfolio")
    all_intents = result.get("all_intents", [])
    assert len(all_intents) == len(ir.VALID_INTENTS)
    for entry in all_intents:
        assert "label" in entry
        assert "confidence" in entry
        assert entry["label"] in ir.VALID_INTENTS
        assert 0.0 <= entry["confidence"] <= 1.0


def test_intent_router_node_returns_valid_intent():
    """The LangGraph node wrapper (retryable_node) returns a valid intent."""
    import ai.agents.intent_router as ir
    from ai.orchestrator.state import initial_state

    state = initial_state(user_id=1, raw_query="portfolio review please", request_id="t1")
    result = asyncio.run(ir.intent_router_node(state))
    assert result.get("intent") in ir.VALID_INTENTS
    conf = result.get("confidence", -1.0)
    assert 0.0 <= conf <= 1.0


def test_valid_intents_list_contains_all_13():
    """VALID_INTENTS exports exactly the 13 documented intent labels."""
    import ai.agents.intent_router as ir

    expected = {
        "Portfolio_Review", "Portfolio_Rebalancing", "Transaction_Analysis",
        "Budgeting", "Savings", "Goal_Planning", "Investment_Education",
        "Taxation", "Banking", "Insurance", "Pension", "Market_News",
        "Account_Summary",
    }
    assert set(ir.VALID_INTENTS) == expected
    assert len(ir.VALID_INTENTS) == 13
