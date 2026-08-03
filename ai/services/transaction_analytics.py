"""Transaction analytics service — deterministic spending analysis.

Tasks 12.1–12.7
All functions return empty/zero results on empty input and never raise.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Categorisation keyword table
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Food & Dining",  ["swiggy", "zomato", "restaurant", "cafe", "food", "hotel", "dominos", "mcdonald"]),
    ("Transport",      ["uber", "ola", "petrol", "fuel", "metro", "irctc", "rapido", "bus", "toll"]),
    ("Utilities",      ["electricity", "water", "gas", "broadband", "recharge", "tata power", "jio", "airtel"]),
    ("Shopping",       ["amazon", "flipkart", "myntra", "mall", "shop", "market"]),
    ("Healthcare",     ["hospital", "pharmacy", "clinic", "medplus", "apollo", "diagnostic"]),
    ("Entertainment",  ["netflix", "prime", "hotstar", "spotify", "bookmyshow", "cinema"]),
    ("Education",      ["school", "college", "university", "course", "udemy", "fees", "tuition"]),
    ("Transfers",      ["transfer", "neft", "rtgs", "imps", "upi", "payment to"]),
]

VALID_CATEGORIES = [cat for cat, _ in _CATEGORY_KEYWORDS] + ["Other"]


def categorise_transaction(beneficiary_name: str, note: str) -> str:
    """Return a category string for a transaction based on keyword matching.

    Matches against the lowercased concatenation of beneficiary_name and note.
    Returns "Other" when no keyword matches.

    Args:
        beneficiary_name: Name of the payee / beneficiary.
        note: Transaction note or description.

    Returns:
        One of the 9 canonical category strings.
    """
    combined = (beneficiary_name + " " + note).lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in combined:
                return category
    return "Other"


# ---------------------------------------------------------------------------
# Monthly cashflow
# ---------------------------------------------------------------------------

def compute_monthly_cashflow(
    transactions: list[dict],
    date_from: str | None,
    date_to: str | None,
) -> dict[str, dict[str, float]]:
    """Group transactions by YYYY-MM and compute credits/debits/net.

    Only transactions with status="completed" are included.
    Credits = sum of positive amounts; debits = sum of absolute negative amounts.

    Args:
        transactions: List of transaction dicts with "amount", "status", "created_at".
        date_from: ISO date string lower bound (inclusive), or None.
        date_to:   ISO date string upper bound (inclusive), or None.

    Returns:
        Dict keyed by "YYYY-MM" → {"credits": float, "debits": float, "net": float}.
    """
    if not transactions:
        return {}

    dt_from = _parse_date(date_from) if date_from else None
    dt_to   = _parse_date(date_to)   if date_to   else None

    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"credits": 0.0, "debits": 0.0, "net": 0.0})

    for txn in transactions:
        if txn.get("status") != "completed":
            continue
        txn_dt = _parse_date(txn.get("created_at", ""))
        if txn_dt is None:
            continue
        if dt_from and txn_dt < dt_from:
            continue
        if dt_to and txn_dt > dt_to:
            continue

        month_key = txn_dt.strftime("%Y-%m")
        amount = float(txn.get("amount", 0.0))
        if amount > 0:
            monthly[month_key]["credits"] += amount
        elif amount < 0:
            monthly[month_key]["debits"] += abs(amount)

    # Compute net for each month
    for key in monthly:
        monthly[key]["net"] = monthly[key]["credits"] - monthly[key]["debits"]

    return dict(monthly)


# ---------------------------------------------------------------------------
# Category breakdown
# ---------------------------------------------------------------------------

def compute_category_breakdown(transactions: list[dict]) -> dict[str, dict]:
    """Compute spending breakdown by category.

    Args:
        transactions: List of transaction dicts with "amount", "beneficiary_name", "note".

    Returns:
        Dict keyed by category → {"total": float, "count": int, "pct": float}.
    """
    if not transactions:
        return {}

    breakdown: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})

    for txn in transactions:
        cat = categorise_transaction(
            txn.get("beneficiary_name", "") or "",
            txn.get("note", "") or "",
        )
        amount = abs(float(txn.get("amount", 0.0)))
        breakdown[cat]["total"] += amount
        breakdown[cat]["count"] += 1

    grand_total = sum(v["total"] for v in breakdown.values())

    result: dict[str, dict] = {}
    for cat, data in breakdown.items():
        pct = (data["total"] / grand_total * 100) if grand_total > 0 else 0.0
        result[cat] = {"total": data["total"], "count": data["count"], "pct": round(pct, 4)}

    return result


# ---------------------------------------------------------------------------
# Recurring transactions
# ---------------------------------------------------------------------------

def detect_recurring_transactions(transactions: list[dict]) -> list[dict]:
    """Detect payees with ≥2 transactions at 25–35 day intervals within 90 days.

    Args:
        transactions: List of transaction dicts with "beneficiary_name", "amount", "created_at".

    Returns:
        List of dicts: {payee, interval_days, last_date, monthly_amount}.
    """
    if not transactions:
        return []

    now = datetime.utcnow()
    cutoff = now - timedelta(days=90)

    # Group by payee, filter to last 90 days
    payee_txns: dict[str, list[dict]] = defaultdict(list)
    for txn in transactions:
        txn_dt = _parse_date(txn.get("created_at", ""))
        if txn_dt is None or txn_dt < cutoff:
            continue
        payee = txn.get("beneficiary_name", "unknown") or "unknown"
        payee_txns[payee].append({"dt": txn_dt, "amount": abs(float(txn.get("amount", 0.0)))})

    recurring = []
    for payee, entries in payee_txns.items():
        if len(entries) < 2:
            continue
        sorted_entries = sorted(entries, key=lambda e: e["dt"])
        intervals: list[int] = []
        for i in range(1, len(sorted_entries)):
            delta = (sorted_entries[i]["dt"] - sorted_entries[i - 1]["dt"]).days
            intervals.append(delta)

        if all(25 <= iv <= 35 for iv in intervals):
            avg_interval = sum(intervals) / len(intervals)
            avg_amount = sum(e["amount"] for e in sorted_entries) / len(sorted_entries)
            recurring.append({
                "payee": payee,
                "interval_days": round(avg_interval, 1),
                "last_date": sorted_entries[-1]["dt"].strftime("%Y-%m-%d"),
                "monthly_amount": round(avg_amount, 2),
            })

    return recurring


# ---------------------------------------------------------------------------
# Anomaly spike detection
# ---------------------------------------------------------------------------

def detect_anomaly_spikes(transactions: list[dict]) -> list[dict]:
    """Detect categories where current 30-day spend > 120% of prior 30-day spend.

    Args:
        transactions: List of transaction dicts with "amount", "beneficiary_name", "note", "created_at".

    Returns:
        List of dicts: {category, current_30d, prior_30d, spike_pct}.
    """
    if not transactions:
        return []

    now = datetime.utcnow()
    current_start = now - timedelta(days=30)
    prior_start   = now - timedelta(days=60)

    current_spend: dict[str, float] = defaultdict(float)
    prior_spend:   dict[str, float] = defaultdict(float)

    for txn in transactions:
        amount = abs(float(txn.get("amount", 0.0)))
        if amount <= 0:
            continue
        txn_dt = _parse_date(txn.get("created_at", ""))
        if txn_dt is None:
            continue
        cat = categorise_transaction(
            txn.get("beneficiary_name", "") or "",
            txn.get("note", "") or "",
        )
        if txn_dt >= current_start:
            current_spend[cat] += amount
        elif txn_dt >= prior_start:
            prior_spend[cat] += amount

    spikes = []
    all_cats = set(current_spend) | set(prior_spend)
    for cat in all_cats:
        cur = current_spend.get(cat, 0.0)
        pri = prior_spend.get(cat, 0.0)
        if pri > 0 and cur > pri * 1.20:
            spike_pct = round((cur - pri) / pri * 100, 2)
            spikes.append({
                "category": cat,
                "current_30d": round(cur, 2),
                "prior_30d": round(pri, 2),
                "spike_pct": spike_pct,
            })

    return spikes


# ---------------------------------------------------------------------------
# Income trend
# ---------------------------------------------------------------------------

def compute_income_trend(transactions: list[dict]) -> dict:
    """Compute a 3-month rolling average of inbound (credit) amounts.

    Args:
        transactions: List of transaction dicts with "amount", "created_at".

    Returns:
        {"3m_avg": float, "months": [{"YYYY-MM": float}, ...]}.
    """
    if not transactions:
        return {"3m_avg": 0.0, "months": []}

    monthly_income: dict[str, float] = defaultdict(float)

    for txn in transactions:
        amount = float(txn.get("amount", 0.0))
        if amount <= 0:
            continue
        txn_dt = _parse_date(txn.get("created_at", ""))
        if txn_dt is None:
            continue
        month_key = txn_dt.strftime("%Y-%m")
        monthly_income[month_key] += amount

    sorted_months = sorted(monthly_income.items())
    months_list = [{m: round(v, 2)} for m, v in sorted_months]

    # 3-month rolling average over the most recent 3 months
    recent = [v for _, v in sorted_months[-3:]]
    avg_3m = sum(recent) / len(recent) if recent else 0.0

    return {"3m_avg": round(avg_3m, 2), "months": months_list}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> datetime | None:
    """Parse an ISO date/datetime string; return None on any parse failure."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str[:19], fmt)
        except (ValueError, TypeError):
            pass
    return None
