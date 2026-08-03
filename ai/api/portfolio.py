from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional
from ai.api.deps import get_ai_current_user
from ai.portfolio.optimizer import optimise_portfolio
from ai.models.portfolio import PortfolioResult, PortfolioError
import pandas as pd

router = APIRouter(tags=["portfolio"])


class AssetInput(BaseModel):
    symbol: str
    returns: list[float]


class PortfolioOptimizeRequest(BaseModel):
    assets: list[AssetInput]
    optimization_type: Literal["max_sharpe", "min_volatility", "target_return"]
    target_return: Optional[float] = None


@router.post("/portfolio/optimize")
async def optimize_endpoint(
    req: PortfolioOptimizeRequest,
    current_user=Depends(get_ai_current_user),
):
    if len(req.assets) < 2:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INSUFFICIENT_ASSETS",
                "message": "At least 2 assets required.",
            },
        )
    returns_data = {a.symbol: a.returns for a in req.assets}
    df = pd.DataFrame(returns_data)
    risk_band = "medium"  # default; in full impl load from Memory Service
    result = optimise_portfolio(df, risk_band, req.optimization_type, req.target_return)
    if isinstance(result, PortfolioError):
        raise HTTPException(status_code=422, detail=result.model_dump())
    return result.model_dump()
