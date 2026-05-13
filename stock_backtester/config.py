"""Default configuration values for the RuleVest Ver.1 skeleton.

The values in this file are intentionally simple and explicit.  They are used by
risk checks and the simulated broker now, and they can later be surfaced in the
Streamlit UI or persisted to a database without changing the core models.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


DISCLAIMER_TEXT = (
    "이 프로그램은 투자 추천 서비스가 아니라, 과거 데이터를 기반으로 투자 규칙을 "
    "테스트하는 학습용/분석용 도구입니다. 과거 수익률이 미래 수익률을 보장하지 않습니다."
)


class OptimizationObjective(StrEnum):
    """Supported optimization goals for future optimizer.py implementation."""

    RETURN_FIRST = "return_first"
    MDD_DEFENSE = "mdd_defense"
    SP500_OUTPERFORMANCE = "sp500_outperformance"
    BALANCED_STABILITY = "balanced_stability"


class AppConfig(BaseModel):
    """Application metadata and UI defaults."""

    project_name: str = "RuleVest"
    version: str = "1.0.0"
    benchmark_ticker: str = "SPY"
    default_tickers: tuple[str, ...] = ("SPY", "QQQ")
    default_start_date: str = "2019-01-01"
    default_end_date: str | None = None


class BacktestConfig(BaseModel):
    """Default backtest inputs used before the Streamlit UI is added."""

    initial_seed: Decimal = Field(default=Decimal("10000"), ge=Decimal("0"))
    monthly_contribution: Decimal = Field(default=Decimal("500"), ge=Decimal("0"))
    transaction_fee_rate: Decimal = Field(default=Decimal("0.001"), ge=Decimal("0"))
    slippage_rate: Decimal = Field(default=Decimal("0.0005"), ge=Decimal("0"))
    rolling_window_years: int = Field(default=5, ge=1)
    rolling_step_years: int = Field(default=1, ge=1)


class StrategyConfig(BaseModel):
    """Default rule parameters for the future rule-based strategy module."""

    target_weights: dict[str, Decimal] = Field(
        default_factory=lambda: {"SPY": Decimal("0.60"), "QQQ": Decimal("0.30")}
    )
    cash_buffer_ratio: Decimal = Field(default=Decimal("0.10"), ge=Decimal("0"), le=Decimal("1"))
    stop_loss_pct: Decimal = Field(default=Decimal("0.15"), ge=Decimal("0"), le=Decimal("1"))
    take_profit_pct: Decimal = Field(default=Decimal("0.30"), ge=Decimal("0"))
    take_profit_sell_ratio: Decimal = Field(
        default=Decimal("0.50"), ge=Decimal("0"), le=Decimal("1")
    )
    dip_buy_threshold_pct: Decimal = Field(
        default=Decimal("0.10"), ge=Decimal("0"), le=Decimal("1")
    )
    dip_buy_ratio: Decimal = Field(default=Decimal("0.25"), ge=Decimal("0"), le=Decimal("1"))
    rebalance_frequency: str = "quarterly"


class RiskConfig(BaseModel):
    """Risk limits used before simulated or real order execution."""

    max_order_value_ratio: Decimal = Field(
        default=Decimal("0.25"), gt=Decimal("0"), le=Decimal("1")
    )
    max_position_weight: Decimal = Field(default=Decimal("0.50"), gt=Decimal("0"), le=Decimal("1"))
    min_cash_ratio: Decimal = Field(default=Decimal("0.05"), ge=Decimal("0"), le=Decimal("1"))
    max_daily_orders_per_ticker: int = Field(default=3, ge=1)


class Settings(BaseModel):
    """Container for all default RuleVest settings."""

    app: AppConfig = Field(default_factory=AppConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)


settings = Settings()
