"""Pydantic data models for RuleVest Ver.1.

The models in this file define the data contract between strategy generation,
risk checks, simulated execution, and future broker integrations.  Ver.1 uses
only simulated orders, but the same object flow is designed to remain valid for
paper, semi-auto, and live trading in later versions.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class SignalAction(StrEnum):
    """Rule-based action suggested by a strategy."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalReason(StrEnum):
    """Allowed rule-based reasons for StrategySignal objects."""

    MONTHLY_BUY = "monthly_buy"
    DIP_BUY = "dip_buy"
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    REBALANCE = "rebalance"
    MANUAL = "manual"


class TradingMode(StrEnum):
    """Execution modes supported by the shared Order model."""

    BACKTEST = "backtest"
    PAPER = "paper"
    SEMI_AUTO = "semi_auto"
    LIVE = "live"


class OrderSide(StrEnum):
    """Order direction accepted by brokers."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Order type accepted by the execution layer."""

    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(StrEnum):
    """Order lifecycle states used by Ver.1 and future broker adapters."""

    CREATED = "created"
    SIMULATED = "simulated"
    REJECTED = "rejected"
    FAILED = "failed"


class RiskSeverity(StrEnum):
    """Severity levels for risk check failures or warnings."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class Position(BaseModel):
    """Current holding for one ticker in the portfolio."""

    ticker: str = Field(min_length=1)
    quantity: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    average_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    current_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    cost_basis: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def market_value(self) -> Decimal:
        """Return the current market value of this position."""

        return self.quantity * self.current_price

    @computed_field
    @property
    def unrealized_pnl(self) -> Decimal:
        """Return unrealized profit or loss based on current market value."""

        return self.market_value - self.cost_basis


class PortfolioState(BaseModel):
    """Point-in-time portfolio snapshot used by strategies and risk checks."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cash: Decimal = Field(ge=Decimal("0"))
    positions: dict[str, Position] = Field(default_factory=dict)
    total_contributions: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def positions_value(self) -> Decimal:
        """Return the total market value of all positions."""

        return sum(
            (position.market_value for position in self.positions.values()),
            Decimal("0"),
        )

    @computed_field
    @property
    def total_value(self) -> Decimal:
        """Return cash plus current position market value."""

        return self.cash + self.positions_value

    def get_position(self, ticker: str) -> Position:
        """Return a position, or an empty placeholder when the ticker is absent."""

        return self.positions.get(ticker, Position(ticker=ticker))


class StrategySignal(BaseModel):
    """Rule-based strategy output that never mutates the portfolio directly."""

    timestamp: datetime
    ticker: str = Field(min_length=1)
    action: SignalAction
    target_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    target_weight: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("1"))
    quantity: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    reason: SignalReason
    current_price: Decimal = Field(ge=Decimal("0"))
    cash_available: Decimal = Field(ge=Decimal("0"))
    current_position: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    expected_cash_after_signal: Decimal = Field(ge=Decimal("0"))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_has_quantity(self) -> "StrategySignal":
        """Require buy/sell signals to carry either quantity or target amount."""

        if self.action in {SignalAction.BUY, SignalAction.SELL}:
            if self.quantity <= 0 and self.target_amount <= 0:
                raise ValueError("buy/sell signals require quantity or target_amount")
        return self


class RiskCheckResult(BaseModel):
    """Result produced by RiskManager before an order is executed."""

    approved: bool
    reasons: list[str] = Field(default_factory=list)
    severity: RiskSeverity = RiskSeverity.INFO
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checks: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Order(BaseModel):
    """Virtual or real order request generated from a StrategySignal."""

    order_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime
    mode: TradingMode = TradingMode.BACKTEST
    ticker: str = Field(min_length=1)
    side: OrderSide
    quantity: Decimal = Field(gt=Decimal("0"))
    order_type: OrderType = OrderType.MARKET
    limit_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    estimated_price: Decimal = Field(gt=Decimal("0"))
    estimated_amount: Decimal = Field(ge=Decimal("0"))
    reason: SignalReason
    strategy_name: str = Field(default="rule_based")
    risk_check_result: RiskCheckResult | None = None
    status: OrderStatus = OrderStatus.CREATED
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_limit_order_price(self) -> "Order":
        """Require limit_price when order_type is limit."""

        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("limit orders require limit_price")
        return self


class BacktestResult(BaseModel):
    """Summary output of a completed backtest run."""

    strategy_name: str
    start_date: date
    end_date: date
    initial_seed: Decimal = Field(ge=Decimal("0"))
    monthly_contribution: Decimal = Field(ge=Decimal("0"))
    final_value: Decimal = Field(ge=Decimal("0"))
    total_return: float
    cagr: float
    yearly_returns: dict[int, float] = Field(default_factory=dict)
    mdd: float
    volatility: float
    worst_period_return: float | None = None
    worst_period_mdd: float | None = None
    sp500_excess_return: float | None = None
    rolling_sp500_win_rate: float | None = None
    rolling_positive_rate: float | None = None
    stability_score: float | None = None
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    cash_weight_history: list[dict[str, Any]] = Field(default_factory=list)
    position_weight_history: list[dict[str, Any]] = Field(default_factory=list)
    signal_log: list[StrategySignal] = Field(default_factory=list)
    order_log: list[Order] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationResult(BaseModel):
    """Result of testing one parameter set across rolling windows."""

    parameter_set_id: str = Field(default_factory=lambda: str(uuid4()))
    parameters: dict[str, Any]
    objective: str
    rolling_results: list[BacktestResult] = Field(default_factory=list)
    average_cagr: float | None = None
    average_mdd: float | None = None
    worst_period_return: float | None = None
    worst_period_mdd: float | None = None
    average_sp500_excess_return: float | None = None
    sp500_win_rate: float | None = None
    positive_window_rate: float | None = None
    performance_std: float | None = None
    strategy_complexity: int = Field(default=1, ge=1)
    stability_score: float | None = None
    recommendation_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sp500_win_rate", "positive_window_rate")
    @classmethod
    def validate_rate(cls, value: float | None) -> float | None:
        """Keep optional rates within the 0 to 1 range."""

        if value is not None and not 0 <= value <= 1:
            raise ValueError("rate values must be between 0 and 1")
        return value
