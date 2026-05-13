"""Pre-trade risk checks for RuleVest Ver.1.

RiskManager is deliberately separate from strategy and broker execution.  The
strategy only explains what it wants to do, this module decides whether the
order is safe enough to simulate, and the broker applies the virtual fill.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal

from stock_backtester.config import RiskConfig, settings
from stock_backtester.models import Order, OrderSide, PortfolioState, RiskCheckResult, RiskSeverity


class RiskManager:
    """Validate orders before simulated or future real execution."""

    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or settings.risk
        self._daily_order_counts: Counter[tuple[date, str]] = Counter()

    def check_order(self, order: Order, portfolio_state: PortfolioState) -> RiskCheckResult:
        """Run all Ver.1 risk checks against an order and portfolio snapshot."""

        checks: dict[str, bool] = {}
        reasons: list[str] = []

        self._record_check(
            checks,
            reasons,
            "valid_price",
            self._is_valid_price(order.estimated_price),
            "가격 데이터가 없거나 0 이하이므로 주문할 수 없습니다.",
        )
        self._record_check(
            checks,
            reasons,
            "daily_duplicate_limit",
            self._within_daily_duplicate_limit(order),
            "같은 날짜에 동일 종목 주문이 너무 많습니다.",
        )

        if order.side == OrderSide.BUY:
            self._check_buy_order(order, portfolio_state, checks, reasons)
        else:
            self._check_sell_order(order, portfolio_state, checks, reasons)

        approved = not reasons
        severity = RiskSeverity.INFO if approved else RiskSeverity.BLOCKING
        result = RiskCheckResult(
            approved=approved,
            reasons=reasons,
            severity=severity,
            checks=checks,
        )

        # Count only approved orders so rejected duplicate attempts do not lock
        # the user out for the rest of the day in a backtest run.
        if approved:
            self._daily_order_counts[(order.timestamp.date(), order.ticker)] += 1
        return result

    def reset_daily_order_counts(self) -> None:
        """Clear duplicate-order counters between independent backtest runs."""

        self._daily_order_counts.clear()

    def _check_buy_order(
        self,
        order: Order,
        portfolio_state: PortfolioState,
        checks: dict[str, bool],
        reasons: list[str],
    ) -> None:
        """Apply checks that only matter for buy orders."""

        total_value = portfolio_state.total_value
        projected_cash = portfolio_state.cash - order.estimated_amount
        projected_position_value = (
            portfolio_state.get_position(order.ticker).market_value + order.estimated_amount
        )

        self._record_check(
            checks,
            reasons,
            "cash_available",
            order.estimated_amount <= portfolio_state.cash,
            "현금이 부족하여 매수 주문을 실행할 수 없습니다.",
        )
        self._record_check(
            checks,
            reasons,
            "max_order_value_ratio",
            self._ratio_ok(order.estimated_amount, total_value, self.config.max_order_value_ratio),
            "주문 금액이 총자산 대비 허용 비율을 초과했습니다.",
        )
        self._record_check(
            checks,
            reasons,
            "max_position_weight",
            self._ratio_ok(projected_position_value, total_value, self.config.max_position_weight),
            "주문 후 종목별 비중이 최대 허용 비중을 초과합니다.",
        )
        self._record_check(
            checks,
            reasons,
            "min_cash_ratio",
            self._cash_ratio_ok(projected_cash, total_value),
            "주문 후 최소 현금 비율을 유지할 수 없습니다.",
        )

    def _check_sell_order(
        self,
        order: Order,
        portfolio_state: PortfolioState,
        checks: dict[str, bool],
        reasons: list[str],
    ) -> None:
        """Apply checks that only matter for sell orders."""

        position = portfolio_state.get_position(order.ticker)
        self._record_check(
            checks,
            reasons,
            "position_available",
            order.quantity <= position.quantity,
            "보유 수량이 부족하여 매도 주문을 실행할 수 없습니다.",
        )

    def _within_daily_duplicate_limit(self, order: Order) -> bool:
        """Return whether a ticker is still within its daily order limit."""

        key = (order.timestamp.date(), order.ticker)
        return self._daily_order_counts[key] < self.config.max_daily_orders_per_ticker

    @staticmethod
    def _is_valid_price(price: Decimal) -> bool:
        """Return False for NaN, infinite, zero, or negative prices."""

        return price.is_finite() and price > 0

    def _cash_ratio_ok(self, cash: Decimal, total_value: Decimal) -> bool:
        """Return whether projected cash keeps the configured minimum ratio."""

        if total_value <= 0:
            return False
        return cash / total_value >= self.config.min_cash_ratio

    @staticmethod
    def _ratio_ok(numerator: Decimal, denominator: Decimal, limit: Decimal) -> bool:
        """Safely compare numerator / denominator with a configured limit."""

        if denominator <= 0:
            return False
        return numerator / denominator <= limit

    @staticmethod
    def _record_check(
        checks: dict[str, bool],
        reasons: list[str],
        name: str,
        passed: bool,
        failure_reason: str,
    ) -> None:
        """Store a single check result and append a reason when it fails."""

        checks[name] = passed
        if not passed:
            reasons.append(failure_reason)
