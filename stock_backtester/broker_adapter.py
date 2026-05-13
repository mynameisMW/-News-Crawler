"""Broker adapter interface for RuleVest.

Ver.1 uses only a simulated broker, but this interface is intentionally close to
what a paper or live broker would need.  Later versions can add
PaperBrokerAdapter or LiveBrokerAdapter without changing strategy code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from stock_backtester.models import Order, OrderStatus, Position


class BrokerAdapter(ABC):
    """Common contract for simulated, paper, semi-auto, and live brokers."""

    @abstractmethod
    def connect(self) -> None:
        """Open a broker connection or initialize a simulated session."""

    @abstractmethod
    def get_account_info(self) -> dict[str, object]:
        """Return account-level information such as mode and total value."""

    @abstractmethod
    def get_cash_balance(self) -> Decimal:
        """Return available cash balance."""

    @abstractmethod
    def get_positions(self) -> dict[str, Position]:
        """Return current positions keyed by ticker."""

    @abstractmethod
    def get_latest_price(self, ticker: str) -> Decimal:
        """Return the latest known price for one ticker."""

    @abstractmethod
    def place_order(self, order: Order) -> Order:
        """Place an order and return the updated order state."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> Order:
        """Cancel a pending order by id and return the updated order."""

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Return the current status for an order."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the broker connection or simulated session."""
