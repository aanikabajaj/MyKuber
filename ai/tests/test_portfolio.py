"""Example-based tests for the portfolio optimiser.

Task 11.6
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai.models.portfolio import PortfolioError, PortfolioResult
from ai.portfolio.optimizer import optimise_portfolio


def _make_returns(n_assets: int, n_days: int = 252, seed: int = 42, loc: float = 0.0005) -> pd.DataFrame:
    """Generate reproducible synthetic daily return DataFrame."""
    rng = np.random.default_rng(seed)
    data = rng.normal(loc=loc, scale=0.01, size=(n_days, n_assets))
    cols = [f"ASSET_{i}" for i in range(n_assets)]
    return pd.DataFrame(data, columns=cols)


# ---------------------------------------------------------------------------
# 2-asset max_sharpe: weights sum to 1.0 ± 1e-6
# ---------------------------------------------------------------------------

def test_max_sharpe_2_asset_weights_sum_to_one() -> None:
    """max_sharpe on 2 assets must return weights that sum to 1.0.

    We use a positive daily drift well above the risk-free rate so PyPortfolioOpt
    can solve max_sharpe without raising 'no asset exceeds the risk-free rate'.
    """
    # loc=0.0008 → ~20% annualised, clearly above 6.5% risk-free rate
    returns = _make_returns(n_assets=2, n_days=300, seed=10, loc=0.0008)
    result = optimise_portfolio(returns, risk_band="high", optimization_type="max_sharpe")

    assert isinstance(result, PortfolioResult), f"Expected PortfolioResult, got {result!r}"
    weight_sum = sum(result.weights.values())
    assert abs(weight_sum - 1.0) <= 1e-6, (
        f"Weights should sum to 1.0 ± 1e-6, got {weight_sum}"
    )


# ---------------------------------------------------------------------------
# 5-asset min_volatility: returns valid PortfolioResult
# ---------------------------------------------------------------------------

def test_min_volatility_5_assets_returns_valid_result() -> None:
    """min_volatility on 5 assets must return a valid PortfolioResult."""
    returns = _make_returns(n_assets=5, seed=2)
    result = optimise_portfolio(returns, risk_band="low", optimization_type="min_volatility")

    assert isinstance(result, PortfolioResult), f"Expected PortfolioResult, got {result!r}"
    assert result.volatility >= 0.0, "Volatility must be non-negative"
    assert isinstance(result.risk_metrics, dict), "risk_metrics must be a dict"
    for key in ("annualised_volatility", "sharpe_ratio", "max_drawdown", "var_95", "cvar_95"):
        assert key in result.risk_metrics, f"Missing risk metric key: {key}"


# ---------------------------------------------------------------------------
# Single asset → INSUFFICIENT_ASSETS error
# ---------------------------------------------------------------------------

def test_insufficient_assets_returns_error_for_single_asset() -> None:
    """Passing a single-asset DataFrame must return PortfolioError(INSUFFICIENT_ASSETS)."""
    returns = _make_returns(n_assets=1, seed=3)
    result = optimise_portfolio(returns, risk_band="high", optimization_type="max_sharpe")

    assert isinstance(result, PortfolioError), f"Expected PortfolioError, got {result!r}"
    assert result.error_code == "INSUFFICIENT_ASSETS"


# ---------------------------------------------------------------------------
# target_return: returns a result without raising
# ---------------------------------------------------------------------------

def test_target_return_does_not_raise() -> None:
    """target_return optimisation must return a result (not raise) for valid inputs."""
    returns = _make_returns(n_assets=4, seed=4)
    result = optimise_portfolio(
        returns,
        risk_band="medium",
        optimization_type="target_return",
        target_return=0.05,  # 5% annualised target
    )
    # Accept either a valid result or an error — must not raise
    assert isinstance(result, (PortfolioResult, PortfolioError)), (
        f"Expected PortfolioResult or PortfolioError, got {type(result)}"
    )
