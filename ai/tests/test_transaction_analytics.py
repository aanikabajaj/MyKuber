"""Example-based tests for the transaction analytics service.

Task 12.8
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ai.services.transaction_analytics import (
    categorise_transaction,
    compute_category_breakdown,
    compute_income_trend,
    compute_monthly_cashflow,
    detect_anomaly_spikes,
    detect_recurring_transactions,
)


# ---------------------------------------------------------------------------
# Categorisation tests
# ---------------------------------------------------------------------------

def test_swiggy_beneficiary_returns_food_and_dining() -> None:
    """'swiggy' in beneficiary_name must map to 'Food & Dining'."""
    assert categorise_transaction("Swiggy", "") == "Food & Dining"


def test_uber_beneficiary_returns_transport() -> None:
    """'uber' in beneficiary_name must map to 'Transport'."""
    assert categorise_transaction("Uber India", "") == "Transport"


def test_unknown_beneficiary_returns_other() -> None:
    """An unrecognised beneficiary must fall back to 'Other'."""
    assert categorise_transaction("Unknown Corp XYZ", "") == "Other"


def test_note_keyword_match() -> None:
    """Keyword in the note field (not beneficiary) must still trigger correct category."""
    assert categorise_transaction("", "zomato delivery") == "Food & Dining"


def test_case_insensitive_matching() -> None:
    """Category matching must be case-insensitive."""
    assert categorise_transaction("NETFLIX", "") == "Entertainment"


# ---------------------------------------------------------------------------
# Empty-input tests — all functions return zeros / empty structures
# ---------------------------------------------------------------------------

def test_compute_monthly_cashflow_empty_input() -> None:
    result = compute_monthly_cashflow([], None, None)
    assert result == {}


def test_compute_category_breakdown_empty_input() -> None:
    result = compute_category_breakdown([])
    assert result == {}


def test_detect_recurring_transactions_empty_input() -> None:
    result = detect_recurring_transactions([])
    assert result == []


def test_detect_anomaly_spikes_empty_input() -> None:
    result = detect_anomaly_spikes([])
    assert result == []


def test_compute_income_trend_empty_input() -> None:
    result = compute_income_trend([])
    assert result == {"3m_avg": 0.0, "months": []}


# ---------------------------------------------------------------------------
# Recurring payee detection
# ---------------------------------------------------------------------------

def _make_txn(beneficiary: str, amount: float, days_ago: int) -> dict:
    dt = (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "beneficiary_name": beneficiary,
        "amount": -abs(amount),
        "created_at": dt,
        "status": "completed",
        "note": "",
    }


def test_known_recurring_payee_is_detected() -> None:
    """A payee with two transactions ~30 days apart within 90 days must be detected."""
    txns = [
        _make_txn("Netflix", 649.0, days_ago=60),
        _make_txn("Netflix", 649.0, days_ago=30),
    ]
    result = detect_recurring_transactions(txns)
    payees = [r["payee"] for r in result]
    assert "Netflix" in payees, f"Expected 'Netflix' in recurring payees, got {payees}"


def test_non_recurring_payee_not_detected() -> None:
    """A payee appearing only once must not appear in the recurring list."""
    txns = [_make_txn("RandomShop", 500.0, days_ago=10)]
    result = detect_recurring_transactions(txns)
    payees = [r["payee"] for r in result]
    assert "RandomShop" not in payees


# ---------------------------------------------------------------------------
# Monthly cashflow — basic correctness
# ---------------------------------------------------------------------------

def test_monthly_cashflow_separates_credits_and_debits() -> None:
    """Monthly cashflow must correctly sum credits and debits for a known month."""
    month = "2024-03"
    txns = [
        {
            "amount": 50000.0,
            "status": "completed",
            "created_at": "2024-03-10T10:00:00",
            "beneficiary_name": "Salary",
            "note": "",
        },
        {
            "amount": -1200.0,
            "status": "completed",
            "created_at": "2024-03-15T10:00:00",
            "beneficiary_name": "Uber",
            "note": "",
        },
    ]
    result = compute_monthly_cashflow(txns, None, None)
    assert month in result
    assert abs(result[month]["credits"] - 50000.0) < 0.01
    assert abs(result[month]["debits"] - 1200.0) < 0.01
    assert abs(result[month]["net"] - 48800.0) < 0.01


def test_non_completed_transactions_excluded_from_cashflow() -> None:
    """Transactions with status != 'completed' must be excluded from cashflow."""
    txns = [
        {
            "amount": 10000.0,
            "status": "pending",
            "created_at": "2024-03-05T10:00:00",
            "beneficiary_name": "Test",
            "note": "",
        }
    ]
    result = compute_monthly_cashflow(txns, None, None)
    assert result == {}
