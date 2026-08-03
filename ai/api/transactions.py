from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from ai.api.deps import get_ai_current_user
from ai.services.transaction_analytics import (
    categorise_transaction,
    compute_monthly_cashflow,
    compute_category_breakdown,
    detect_recurring_transactions,
    detect_anomaly_spikes,
    compute_income_trend,
)
from ai.database.ai_db import get_readonly_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.transaction import Transaction

router = APIRouter(tags=["transactions"])


class TransactionAnalyzeRequest(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    categories: Optional[list[str]] = None


@router.post("/transactions/analyze")
async def analyze_endpoint(
    req: TransactionAnalyzeRequest,
    current_user=Depends(get_ai_current_user),
    db: Session = Depends(get_readonly_db),
):
    rows = db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(1000)
    ).scalars().all()

    txns = [
        {
            "amount": t.amount,
            "beneficiary_name": t.beneficiary_name,
            "note": t.note or "",
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in rows
    ]
    for t in txns:
        t["category"] = categorise_transaction(
            t.get("beneficiary_name", ""),
            t.get("note", ""),
        )

    cashflow = compute_monthly_cashflow(txns, req.date_from, req.date_to)
    breakdown = compute_category_breakdown(txns)
    recurring = detect_recurring_transactions(txns)
    spikes = detect_anomaly_spikes(txns)
    trend = compute_income_trend(txns)

    # Normalize monthly_cashflow: dict → list
    cashflow_list = [
        {"month": month, "total_debit": data.get("debits", 0), "total_credit": data.get("credits", 0)}
        for month, data in sorted(cashflow.items())
    ]

    # Normalize category_breakdown: {cat: {total, count, pct}} → {cat: total}
    cat_flat = {
        cat: data.get("total", 0) if isinstance(data, dict) else float(data)
        for cat, data in breakdown.items()
    }

    # Normalize anomaly_spikes: category-level spikes → readable format
    spikes_normalized = [
        {
            "date": s.get("category", "Unknown"),
            "amount": s.get("current_30d", 0),
            "beneficiary_name": s.get("category", "Spike"),
            "note": f"Spend up {s.get('spike_pct', 0):.0f}% vs prior month",
            "z_score": s.get("spike_pct", 0) / 100,
        }
        for s in spikes
    ]

    return {
        "monthly_cashflow": cashflow_list,
        "category_breakdown": cat_flat,
        "recurring_transactions": recurring,
        "anomaly_spikes": spikes_normalized,
        "income_trend": trend,
    }
