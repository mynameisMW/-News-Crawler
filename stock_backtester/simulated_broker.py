"""Simulated broker used for RuleVest Ver.1 backtests.

This module performs only virtual fills.  It does not send real orders, read API
keys, or connect to brokerage accounts.  Portfolio changes should happen here
(or through a future execution engine that delegates here), not inside strategy
code.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal

from stock_backtester.broker_adapter import BrokerAdapter
from stock_backtester.config import settings
from stock_backtester.models import (
    Order,
    OrderSide,
    OrderStatus,
    Position,
    PortfolioState,
    TradingMode,
)


class SimulatedBroker(BrokerAdapter):
    """In-memory broker that executes backtest orders as virtual fills."""

    def __init__(self, initial_cash: Decimal | None = None) -> None:
        self._connected = False
        self._cash = initial_cash if initial_cash is not None else settings.backtest.initial_seed
        self._positions: dict[str, Position] = {}
        self._latest_prices: dict[str, Decimal] = {}
        self._orders: dict[str, Order] = {}

    def connect(self) -> None:
        """Initialize the simulated broker session."""

        self._connected = True

    def get_account_info(self) -> dict[str, object]:
        """Return a simple account snapshot for the simulated broker."""

        self._ensure_connected()
        portfolio = self.get_portfolio_state()
        return {
            "mode": TradingMode.BACKTEST.value,
            "cash": portfolio.cash,
            "positions_value": portfolio.positions_value,
            "total_value": portfolio.total_value,
            "positions_count": len(portfolio.positions),
        }

    def get_cash_balance(self) -> Decimal:
        """Return simulated available cash."""

        self._ensure_connected()
        return self._cash

    def get_positions(self) -> dict[str, Position]:
        """Return a copy of simulated positions keyed by ticker."""

        self._ensure_connected()
        return deepcopy(self._positions)

    def get_latest_price(self, ticker: str) -> Decimal:
        """Return the latest price supplied by the backtest loop."""

        self._ensure_connected()
        try:
            return self._latest_prices[ticker]
        except KeyError as exc:
            raise ValueError(f"No latest price is available for ticker: {ticker}") from exc

    def update_latest_price(self, ticker: str, price: Decimal) -> None:
        """Store the latest market price for a ticker before virtual execution."""

        if price <= 0:
            raise ValueError("price must be positive")
        self._latest_prices[ticker] = price
        if ticker in self._positions:
            self._positions[ticker].current_price = price
            self._positions[ticker].last_updated = datetime.now(timezone.utc)

    def place_order(self, order: Order) -> Order:
        """Virtually fill an approved backtest order at its estimated price."""

        self._ensure_connected()
        if order.mode != TradingMode.BACKTEST:
            raise ValueError("SimulatedBroker only supports backtest orders in Ver.1")
        if order.risk_check_result is not None and not order.risk_check_result.approved:
            rejected_order = order.model_copy(update={"status": OrderStatus.REJECTED})
            self._orders[rejected_order.order_id] = rejected_order
            return rejected_order

        try:
            if order.side == OrderSide.BUY:
                self._buy(order)
            else:
                self._sell(order)
        except ValueError:
            failed_order = order.model_copy(update={"status": OrderStatus.FAILED})
            self._orders[failed_order.order_id] = failed_order
            raise

        simulated_order = order.model_copy(update={"status": OrderStatus.SIMULATED})
        self._orders[simulated_order.order_id] = simulated_order
        return simulated_order

    def cancel_order(self, order_id: str) -> Order:
        """Reject cancellation for already simulated Ver.1 orders."""

        self._ensure_connected()
        if order_id not in self._orders:
            raise ValueError(f"Unknown order_id: {order_id}")
        raise ValueError("Ver.1 simulated orders are filled immediately and cannot be canceled")

    def get_order_status(self, order_id: str) -> OrderStatus:
        """Return the stored status for a simulated order."""

        self._ensure_connected()
        if order_id not in self._orders:
            raise ValueError(f"Unknown order_id: {order_id}")
        return self._orders[order_id].status

    def get_portfolio_state(self) -> PortfolioState:
        """Return a validated portfolio snapshot."""

        self._ensure_connected()
        return PortfolioState(cash=self._cash, positions=deepcopy(self._positions))

    def disconnect(self) -> None:
        """Close the simulated broker session."""

        self._connected = False

    def _buy(self, order: Order) -> None:
        """Apply a virtual buy fill to cash and positions."""

        total_cost = order.estimated_amount
        if total_cost > self._cash:
            raise ValueError("insufficient simulated cash for buy order")

        self._cash -= total_cost
        position = self._positions.get(order.ticker, Position(ticker=order.ticker))
        new_quantity = position.quantity + order.quantity
        new_cost_basis = position.cost_basis + total_cost
        average_price = new_cost_basis / new_quantity if new_quantity > 0 else Decimal("0")
        self._positions[order.ticker] = position.model_copy(
            update={
                "quantity": new_quantity,
                "average_price": average_price,
                "current_price": order.estimated_price,
                "cost_basis": new_cost_basis,
                "last_updated": order.timestamp,
            }
        )

    def _sell(self, order: Order) -> None:
        """Apply a virtual sell fill to cash and positions."""

        position = self._positions.get(order.ticker)
        if position is None or position.quantity < order.quantity:
            raise ValueError("insufficient simulated position quantity for sell order")

        sell_ratio = order.quantity / position.quantity
        remaining_quantity = position.quantity - order.quantity
        remaining_cost_basis = position.cost_basis * (Decimal("1") - sell_ratio)
        self._cash += order.estimated_amount

        if remaining_quantity == 0:
            self._positions.pop(order.ticker)
            return

        self._positions[order.ticker] = position.model_copy(
            update={
                "quantity": remaining_quantity,
                "current_price": order.estimated_price,
                "cost_basis": remaining_cost_basis,
                "last_updated": order.timestamp,
            }
        )

    def _ensure_connected(self) -> None:
        """Raise a clear error when methods are used before connect()."""

        if not self._connected:
            raise RuntimeError("SimulatedBroker is not connected")
