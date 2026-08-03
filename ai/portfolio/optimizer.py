"""Portfolio optimisation using PyPortfolioOpt + cvxpy.

Tasks 11.1–11.3, 11.5
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier, expected_returns, risk_models

from ai.models.portfolio import PortfolioError, PortfolioResult

RISK_BAND_MAX_WEIGHT: dict[str, float] = {"low": 0.20, "medium": 0.35, "high": 0.50}


def _risk_metrics(
    weights: dict[str, float],
    returns: pd.DataFrame,
    risk_free_rate: float,
) -> dict[str, float]:
    """Compute annualised risk/return metrics for a weighted portfolio."""
    w = np.array([weights[c] for c in returns.columns])
    mu = returns.mean() * 252  # annualised expected returns
    cov = returns.cov() * 252  # annualised covariance

    port_return = float(mu @ w)
    port_vol = float(np.sqrt(w @ cov.values @ w))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0.0

    # Max drawdown from cumulative returns
    cumulative = (1 + returns @ w).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_dd = float(drawdown.min())

    # VaR and CVaR at 95% confidence level
    port_daily_rets = (returns @ w).values
    var_95 = float(np.percentile(port_daily_rets, 5))
    tail_mask = port_daily_rets <= var_95
    cvar_95 = float(port_daily_rets[tail_mask].mean()) if tail_mask.any() else var_95

    return {
        "annualised_volatility": port_vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "var_95": var_95,
        "cvar_95": cvar_95,
    }


def optimise_portfolio(
    asset_returns: pd.DataFrame,
    risk_band: str,
    optimization_type: str,
    target_return: float | None = None,
    risk_free_rate: float = 0.065,
) -> PortfolioResult | PortfolioError:
    """Optimise a portfolio given daily return data and constraints.

    Args:
        asset_returns: DataFrame of shape (T, N) with daily returns per asset.
        risk_band: One of "low", "medium", "high" — determines max per-asset weight.
        optimization_type: "max_sharpe", "min_volatility", or "target_return".
        target_return: Required annualised return when optimization_type="target_return".
        risk_free_rate: Annual risk-free rate (default: 0.065, RBI repo rate proxy).

    Returns:
        PortfolioResult on success, PortfolioError on failure.
    """
    n = len(asset_returns.columns)
    if n < 2:
        return PortfolioError(
            error_code="INSUFFICIENT_ASSETS",
            message=f"At least 2 assets required, got {n}.",
        )

    max_w = RISK_BAND_MAX_WEIGHT.get(risk_band, 0.50)
    mu = expected_returns.mean_historical_return(asset_returns)
    S = risk_models.sample_cov(asset_returns)

    # --- target_return: use cvxpy QP directly ---
    if optimization_type == "target_return":
        import cvxpy as cp

        if target_return is None:
            target_return = float(mu.mean())

        mu_vals = mu.values
        S_vals = S.values
        w = cp.Variable(n)
        risk = cp.quad_form(w, S_vals)
        constraints = [
            cp.sum(w) == 1,
            w >= 0,
            w <= max_w,
            mu_vals @ w >= target_return,
        ]
        prob = cp.Problem(cp.Minimize(risk), constraints)
        try:
            # Try CLARABEL first; fall back to SCS on failure
            prob.solve(solver=cp.CLARABEL)
            if w.value is None:
                prob.solve(solver=cp.SCS, eps=1e-4)
        except Exception:
            try:
                prob.solve(solver=cp.SCS, eps=1e-4)
            except Exception as exc:
                return PortfolioError(
                    error_code="OPTIMISATION_FAILED",
                    message=f"cvxpy could not find a solution: {exc}",
                )

        if w.value is None:
            return PortfolioError(
                error_code="OPTIMISATION_FAILED",
                message="cvxpy could not find a solution.",
            )

        raw_w = dict(zip(asset_returns.columns, w.value.tolist()))
        cleaned = {k: max(0.0, float(v)) for k, v in raw_w.items()}
        total = sum(cleaned.values())
        weights = {k: v / total for k, v in cleaned.items()} if total > 0 else cleaned

        metrics = _risk_metrics(weights, asset_returns, risk_free_rate)
        return PortfolioResult(
            weights=weights,
            expected_return=float(mu_vals @ [weights[c] for c in asset_returns.columns]),
            volatility=metrics["annualised_volatility"],
            sharpe_ratio=metrics["sharpe_ratio"],
            risk_metrics=metrics,
        )

    # --- max_sharpe / min_volatility: use PyPortfolioOpt EfficientFrontier ---
    ef = EfficientFrontier(mu, S, weight_bounds=(0, max_w))

    if optimization_type == "max_sharpe":
        try:
            ef.max_sharpe(risk_free_rate=risk_free_rate)
        except Exception:
            # Fallback: rebuild with SCS solver if default solver fails
            from pypfopt.efficient_frontier import EfficientFrontier as EF2
            import cvxpy as cp
            try:
                ef2 = EF2(mu, S, weight_bounds=(0, max_w), solver=cp.SCS)
                ef2.max_sharpe(risk_free_rate=risk_free_rate)
                ef = ef2
            except Exception as exc:
                return PortfolioError(
                    error_code="OPTIMISATION_FAILED",
                    message=f"max_sharpe failed: {exc}",
                )
    elif optimization_type == "min_volatility":
        ef.min_volatility()
    else:
        return PortfolioError(
            error_code="UNKNOWN_OPTIMISATION_TYPE",
            message=f"Unknown type: {optimization_type}",
        )

    cleaned = ef.clean_weights()
    metrics = _risk_metrics(cleaned, asset_returns, risk_free_rate)
    perf = ef.portfolio_performance(risk_free_rate=risk_free_rate)

    return PortfolioResult(
        weights=dict(cleaned),
        expected_return=float(perf[0]),
        volatility=float(perf[1]),
        sharpe_ratio=float(perf[2]),
        risk_metrics=metrics,
    )
