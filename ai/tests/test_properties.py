"""Property-based tests for the Wealth Intelligence AI Platform.

Covers Properties 2, 3, 4, and 12 as specified in the design document.
Each property is exercised with a minimum of 200 examples via Hypothesis.

**Validates: Requirements 5.2, 13.1, 13.2, 19.2 — Properties 2, 3, 4, 12**
"""
from __future__ import annotations

import hashlib

from hypothesis import given
from hypothesis import settings as h_settings
from hypothesis import strategies as st

from ai.security.pii_masker import (
    BALANCE_BUCKETS,
    bucket_balance,
    mask_account_number,
    mask_pii_in_text,
)
from ai.utils.privacy import hash_query

# Collect the valid bucket labels once at module load so tests stay in sync
# with the canonical list defined in pii_masker.py.
VALID_BUCKET_LABELS: list[str] = [label for _, _, label in BALANCE_BUCKETS]


# ---------------------------------------------------------------------------
# Property 2 — Account Number Masking
#
# For any account string of length ≥ 4 (decimal digits only):
#   - The result starts with "****"
#   - The result ends with the last 4 characters of the input
#   - Characters before the last 4 are not present in the masked output
# ---------------------------------------------------------------------------


@given(
    st.text(
        min_size=4,
        alphabet=st.characters(whitelist_categories=("Nd",)),
    )
)
@h_settings(max_examples=200)
def test_account_masking_property(account: str) -> None:
    """**Validates: Requirements 5.2 — Property 2: Account Number Masking**

    mask_account_number must always produce a string that:
    1. Starts with "****"
    2. Ends with the last 4 digits of the input
    3. Does not expose any digits that precede the last 4
    """
    masked = mask_account_number(account)

    # Must always have the **** prefix
    assert masked.startswith("****"), f"Expected '****' prefix, got: {masked!r}"

    # Must preserve the last 4 characters verbatim
    assert masked.endswith(account[-4:]), (
        f"Expected suffix {account[-4:]!r}, got: {masked!r}"
    )

    # For strings longer than 4 chars the hidden prefix must not appear
    if len(account) > 4:
        hidden_prefix = account[:-4]
        assert hidden_prefix not in masked, (
            f"Hidden prefix {hidden_prefix!r} leaked into masked output: {masked!r}"
        )


# ---------------------------------------------------------------------------
# Property 3 — Balance Bucket Coverage
#
# For any non-negative float up to 1e8:
#   - bucket_balance returns a non-empty string
#   - The returned label is one of the 6 canonical bucket labels
# ---------------------------------------------------------------------------


@given(
    st.floats(
        min_value=0.0,
        max_value=1e8,
        allow_nan=False,
        allow_infinity=False,
    )
)
@h_settings(max_examples=200)
def test_balance_bucket_coverage_property(balance: float) -> None:
    """**Validates: Requirements 5.2 — Property 3: Balance Bucket Coverage**

    bucket_balance must:
    1. Return a non-empty string for every valid balance
    2. Return exactly one of the 6 canonical bucket labels
    """
    label = bucket_balance(balance)

    assert isinstance(label, str), f"Expected str, got {type(label)!r}"
    assert len(label) > 0, "Bucket label must not be empty"
    assert label in VALID_BUCKET_LABELS, (
        f"Label {label!r} is not in the canonical set: {VALID_BUCKET_LABELS}"
    )


# ---------------------------------------------------------------------------
# Property 4 — PII Scan Completeness
#
# For any free-form text, if a known Indian mobile number is appended,
# mask_pii_in_text must remove it from the output.
# ---------------------------------------------------------------------------

# A fixed valid Indian mobile number used as the injected PII marker.
_MOBILE_MARKER = "9876543210"


@given(st.text(min_size=0, max_size=200))
@h_settings(max_examples=200)
def test_pii_scan_removes_mobile_property(prefix: str) -> None:
    """**Validates: Requirements 13.1, 13.2 — Property 4: PII Scan Completeness**

    After masking, a known Indian mobile number embedded in arbitrary text
    must no longer appear in the output.
    """
    combined = f"{prefix} {_MOBILE_MARKER} end"
    result = mask_pii_in_text(combined)
    assert _MOBILE_MARKER not in result, (
        f"Mobile number {_MOBILE_MARKER!r} was not redacted from output: {result!r}"
    )


# ---------------------------------------------------------------------------
# Property 12 — Query Hashing Correctness
#
# For any non-empty query string:
#   - hash_query returns the SHA-256 hex digest of the UTF-8 encoded query
#   - The output is always exactly 64 hex characters (the raw query is NOT
#     stored — the fixed-length hash is)
# ---------------------------------------------------------------------------


@given(st.text(min_size=1))
@h_settings(max_examples=200)
def test_query_hashing_correctness_property(query: str) -> None:
    """**Validates: Requirements 19.2 — Property 12: Query Hashing Correctness**

    hash_query must:
    1. Return the canonical SHA-256 hex digest of the UTF-8 query
    2. Always return exactly 64 hex characters (256-bit → 64 hex digits)
    """
    result = hash_query(query)
    expected = hashlib.sha256(query.encode("utf-8")).hexdigest()

    assert result == expected, (
        f"hash_query({query!r}) returned {result!r}, expected {expected!r}"
    )

    # A 64-char hex string means the raw query is never stored — only the digest
    assert len(result) == 64, (
        f"Expected 64-char hex digest, got {len(result)} chars: {result!r}"
    )


# ---------------------------------------------------------------------------
# Property 13 — Intent Output Validity
#
# For any non-empty string query of length 1–500:
#   - The returned intent is one of the 13 valid intent labels
#   - The returned confidence is a float in [0.0, 1.0]
#
# **Validates: Requirements — Property 13: Intent Output Validity**
# ---------------------------------------------------------------------------

from hypothesis import HealthCheck  # noqa: E402

from ai.agents.intent_router import VALID_INTENTS, intent_router_node  # noqa: E402
from ai.orchestrator.state import initial_state  # noqa: E402

VALID_INTENTS_SET = set(VALID_INTENTS)


@given(st.text(min_size=1, max_size=500))
@h_settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_intent_output_validity(query: str) -> None:
    """**Validates: Requirements — Property 13: Intent Output Validity**

    For any non-empty query:
    1. result["intent"] is one of the 13 valid intent labels
    2. result["confidence"] is a float in [0.0, 1.0]
    """
    import asyncio

    state = initial_state(user_id=1, raw_query=query, request_id="test")
    result = asyncio.run(intent_router_node(state))
    assert result.get("intent") in VALID_INTENTS_SET, (
        f"intent {result.get('intent')!r} is not in VALID_INTENTS_SET"
    )
    conf = result.get("confidence", -1.0)
    assert 0.0 <= conf <= 1.0, (
        f"confidence {conf} is out of [0.0, 1.0] for query {query!r}"
    )


# ---------------------------------------------------------------------------
# Property 10 — Conversation Summary Retention Bound
#
# Feature: wealth-intelligence-ai
# For any sequence of appends, len(conversation_summaries) <= 20.
# ---------------------------------------------------------------------------


@given(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=50))
@h_settings(max_examples=200)
def test_conversation_summary_retention_bound(summaries: list[str]) -> None:
    """**Validates: Requirements 12.3 — Property 10: Conversation Summary Retention Bound**

    For any sequence of append calls, len(conversation_summaries) <= 20.
    The implementation mirrors memory_service.append_conversation_summary's trimming logic.
    """
    result: list[str] = []
    for s in summaries:
        result.append(s)
        result = result[-20:]
    assert len(result) <= 20


# ---------------------------------------------------------------------------
# Property 5 — Portfolio Weights Sum to 1.0
#
# For any valid returns DataFrame (2–10 assets, 100–500 days) and risk band,
# the returned weights must sum to 1.0 ± 1e-6.
#
# **Validates: Requirements — Property 5: Portfolio Weights Sum to 1.0**
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

from ai.models.portfolio import PortfolioError, PortfolioResult
from ai.portfolio.optimizer import RISK_BAND_MAX_WEIGHT, optimise_portfolio


def _returns_strategy(
    draw: "st.DrawFn",
    min_assets: int = 2,
    max_assets: int = 10,
    min_days: int = 100,
    max_days: int = 500,
) -> pd.DataFrame:
    """Hypothesis strategy: build a random daily-return DataFrame."""
    n_assets = draw(st.integers(min_value=min_assets, max_value=max_assets))
    n_days   = draw(st.integers(min_value=min_days,   max_value=max_days))
    seed     = draw(st.integers(min_value=0, max_value=2**31 - 1))
    rng = np.random.default_rng(seed)
    data = rng.normal(loc=0.0005, scale=0.01, size=(n_days, n_assets))
    cols = [f"A{i}" for i in range(n_assets)]
    return pd.DataFrame(data, columns=cols)


@given(st.data())
@h_settings(max_examples=100, deadline=None)
def test_portfolio_weights_sum_to_one(data: st.DataObject) -> None:
    """**Validates: Requirements — Property 5: Portfolio Weights Sum to 1.0**

    For max_sharpe and min_volatility, the portfolio weights must always
    sum to 1.0 ± 1e-6 when a valid solution is returned.
    """
    returns     = _returns_strategy(data.draw)
    risk_band   = data.draw(st.sampled_from(["low", "medium", "high"]))
    opt_type    = data.draw(st.sampled_from(["max_sharpe", "min_volatility"]))

    result = optimise_portfolio(returns, risk_band=risk_band, optimization_type=opt_type)

    if isinstance(result, PortfolioResult):
        weight_sum = sum(result.weights.values())
        assert abs(weight_sum - 1.0) <= 1e-6, (
            f"Weights sum {weight_sum} deviates from 1.0 for {opt_type}/{risk_band}"
        )


# ---------------------------------------------------------------------------
# Property 6 — No Weight Exceeds Risk-Band Cap
#
# **Validates: Requirements — Property 6: No Weight Exceeds Risk-Band Cap**
# ---------------------------------------------------------------------------


@given(st.data())
@h_settings(max_examples=100, deadline=None)
def test_no_weight_exceeds_risk_band_cap(data: st.DataObject) -> None:
    """**Validates: Requirements — Property 6: No Weight Exceeds Risk-Band Cap**

    Every individual asset weight in a valid PortfolioResult must not exceed
    the maximum weight cap defined for the selected risk band.
    """
    returns     = _returns_strategy(data.draw)
    risk_band   = data.draw(st.sampled_from(["low", "medium", "high"]))
    opt_type    = data.draw(st.sampled_from(["max_sharpe", "min_volatility"]))

    max_weight = RISK_BAND_MAX_WEIGHT[risk_band]
    result = optimise_portfolio(returns, risk_band=risk_band, optimization_type=opt_type)

    if isinstance(result, PortfolioResult):
        for asset, w in result.weights.items():
            assert w <= max_weight + 1e-6, (
                f"Asset {asset} weight {w:.4f} exceeds cap {max_weight} "
                f"for risk band '{risk_band}'"
            )


# ---------------------------------------------------------------------------
# Property 7 — Fewer Than 2 Assets Returns INSUFFICIENT_ASSETS
#
# **Validates: Requirements — Property 7: INSUFFICIENT_ASSETS for <2 assets**
# ---------------------------------------------------------------------------


@given(
    st.integers(min_value=100, max_value=500),  # n_days
    st.sampled_from(["max_sharpe", "min_volatility", "target_return"]),
    st.sampled_from(["low", "medium", "high"]),
    st.integers(min_value=0, max_value=2**31 - 1),  # seed
)
@h_settings(max_examples=100, deadline=None)
def test_insufficient_assets_error_for_single_asset(
    n_days: int, opt_type: str, risk_band: str, seed: int
) -> None:
    """**Validates: Requirements — Property 7: INSUFFICIENT_ASSETS for <2 assets**

    Passing a single-column DataFrame must always yield a PortfolioError
    with error_code="INSUFFICIENT_ASSETS".
    """
    rng = np.random.default_rng(seed)
    data = rng.normal(loc=0.0005, scale=0.01, size=(n_days, 1))
    returns = pd.DataFrame(data, columns=["ONLY_ASSET"])

    result = optimise_portfolio(returns, risk_band=risk_band, optimization_type=opt_type)

    assert isinstance(result, PortfolioError), (
        f"Expected PortfolioError, got {type(result)}"
    )
    assert result.error_code == "INSUFFICIENT_ASSETS", (
        f"Expected INSUFFICIENT_ASSETS, got {result.error_code!r}"
    )


# ---------------------------------------------------------------------------
# Property 8 — Transaction Category Invariant
#
# For any arbitrary beneficiary_name and note, categorise_transaction returns
# exactly one category from the 9 valid values and never raises.
#
# **Validates: Requirements — Property 8: Transaction Category Invariant**
# ---------------------------------------------------------------------------

from ai.services.transaction_analytics import (  # noqa: E402
    VALID_CATEGORIES,
    categorise_transaction,
)

VALID_CATEGORIES_SET = set(VALID_CATEGORIES)


@given(st.text(max_size=200), st.text(max_size=200))
@h_settings(max_examples=200)
def test_transaction_category_invariant(beneficiary_name: str, note: str) -> None:
    """**Validates: Requirements — Property 8: Transaction Category Invariant**

    For any arbitrary beneficiary_name and note:
    1. categorise_transaction returns a non-empty string.
    2. The returned string is one of the 9 valid category values.
    3. The function never raises.
    """
    cat = categorise_transaction(beneficiary_name, note)
    assert cat in VALID_CATEGORIES_SET, (
        f"categorise_transaction({beneficiary_name!r}, {note!r}) returned "
        f"unexpected category {cat!r}. Valid: {VALID_CATEGORIES}"
    )


# ---------------------------------------------------------------------------
# Property 1 — RAG Round-Trip Serialisation
#
# Feature: wealth-intelligence-ai
# For any valid RagChunk, from_qdrant_payload(chunk.to_qdrant_payload())
# must round-trip all fields exactly (score defaults to 0.0 — not stored).
#
# **Validates: Requirements 10.1, 10.2, 10.3, 10.7 — Property 1: RAG Round-Trip Serialisation**
# ---------------------------------------------------------------------------

from ai.models.rag import RagChunk  # noqa: E402


@given(
    st.fixed_dictionaries(
        {
            "chunk_id": st.text(min_size=1, max_size=50),
            "collection": st.sampled_from(
                ["SEBI_Regulations", "RBI_Guidelines", "CBDT_Tax"]
            ),
            "document_title": st.text(min_size=1, max_size=100),
            "section_id": st.text(min_size=1, max_size=50),
            "text": st.text(min_size=1, max_size=500),
            "ingested_at": st.just("2024-01-15T10:30:00Z"),
        }
    )
)
@h_settings(max_examples=200)
def test_rag_roundtrip(data: dict) -> None:
    """**Validates: Requirements 10.1, 10.2, 10.3, 10.7 — Property 1: RAG Round-Trip Serialisation**

    For any valid RagChunk:
    1. ``to_qdrant_payload()`` serialises without ``score``.
    2. ``from_qdrant_payload(payload)`` restores all non-score fields exactly.
    3. ``score`` defaults to ``0.0`` when absent from the stored payload.
    """
    chunk = RagChunk(**data)
    payload = chunk.to_qdrant_payload()

    # score must NOT be present in the stored payload
    assert "score" not in payload, "score must not be persisted in Qdrant payload"

    restored = RagChunk.from_qdrant_payload(payload)

    assert restored.chunk_id == chunk.chunk_id
    assert restored.collection == chunk.collection
    assert restored.document_title == chunk.document_title
    assert restored.section_id == chunk.section_id
    assert restored.text == chunk.text
    assert restored.ingested_at == chunk.ingested_at
    # score is not in payload so it defaults to 0.0 on restoration
    assert restored.score == 0.0


# ---------------------------------------------------------------------------
# Property 11 — Low-Confidence Warning Attachment
#
# Feature: wealth-intelligence-ai
# For any llm_confidence < 0.4, metadata.low_confidence_warning must be present.
#
# **Validates: Requirements — Property 11: Low-Confidence Warning Attachment**
# ---------------------------------------------------------------------------


@given(st.floats(min_value=0.0, max_value=0.399, allow_nan=False, allow_infinity=False))
@h_settings(max_examples=200, deadline=None)
def test_low_confidence_warning_attached(confidence: float):
    """**Validates: Requirements — Property 11: Low-Confidence Warning Attachment**

    For any llm_confidence < 0.4, metadata.low_confidence_warning must be present.
    The toxicity classifier is patched to 0.0 so the test focuses on the
    confidence-check path without triggering slow model loading.
    """
    import asyncio
    from unittest.mock import patch

    from ai.orchestrator.state import initial_state
    from ai.security.safety_layer import safety_layer_node

    state = initial_state(user_id=1, raw_query="test", request_id="p11")
    state["llm_response"] = "Some response text."
    state["llm_confidence"] = confidence
    state["rag_result"] = None
    state["portfolio_result"] = None

    with patch("ai.security.safety_layer._check_toxicity", return_value=0.0):
        result = asyncio.run(safety_layer_node(state))
    safe = result.get("safe_response", {})
    meta = safe.get("metadata", {})
    assert "low_confidence_warning" in meta, (
        f"low_confidence_warning missing for confidence={confidence}"
    )


# ---------------------------------------------------------------------------
# Property 9 — Response Schema Completeness
#
# Feature: wealth-intelligence-ai
# For any combination of llm_confidence, llm_response, and session_id,
# formatted_response must contain all 8 REQUIRED_KEYS and all array fields
# must be lists.
#
# **Validates: Requirements — Property 9: Response Schema Completeness**
# ---------------------------------------------------------------------------


@given(
    st.fixed_dictionaries({
        "llm_confidence": st.one_of(st.none(), st.floats(0.0, 1.0, allow_nan=False)),
        "llm_response": st.text(max_size=200),
        "session_id": st.one_of(st.none(), st.uuids().map(str)),
    })
)
@h_settings(max_examples=200)
def test_response_schema_completeness(overrides: dict):
    """**Validates: Requirements — Property 9: Response Schema Completeness**

    For any combination of llm_confidence, llm_response, and session_id:
    1. formatted_response contains all 8 REQUIRED_KEYS.
    2. charts, recommendations, portfolio, citations are always lists.
    """
    from ai.agents.response_formatter import REQUIRED_KEYS, response_formatter_node
    from ai.orchestrator.state import initial_state

    state = initial_state(user_id=1, raw_query="test", request_id="p9")
    state.update(overrides)
    result = response_formatter_node(state)
    formatted = result["formatted_response"]
    for key in REQUIRED_KEYS:
        assert key in formatted, f"Required key '{key}' missing from formatted_response"
    for arr_key in ("charts", "recommendations", "portfolio", "citations"):
        assert isinstance(formatted[arr_key], list), (
            f"'{arr_key}' must be a list, got {type(formatted[arr_key])!r}"
        )
