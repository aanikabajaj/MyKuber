"""Pydantic models for portfolio optimisation outputs.

Task 11.4
"""
from __future__ import annotations

from pydantic import BaseModel


class PortfolioResult(BaseModel):
    weights: dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    risk_metrics: dict[str, float]  # keys: annualised_volatility, sharpe_ratio, max_drawdown, var_95, cvar_95


class PortfolioError(BaseModel):
    error_code: str
    message: str
