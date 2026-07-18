"""
Exchange Client Interface Contract

This module defines the Exchange Client interface.

Constitutional Principles:
- VI. Risk Engine Is Sovereign: Kill switch semantics
- VII. Venue Independence: Strict abstraction over venue
- IX. Secrets and Safety Rails: TRADING_ENV defaults to testnet
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class KillSwitchEngagedError(Exception):
    """Raised when place_order is called while kill switch is engaged."""

    def __init__(self, reason_code: str = "EXEC_BLOCKED_KILL_SWITCH") -> None:
        self.reason_code = reason_code
        super().__init__(f"Kill switch engaged: {reason_code}")


class ExchangeClient(ABC):
    """
    Exchange Client interface.

    Constitutional requirements:
    - Venue independence (Principle VII) - strict abstraction
    - Kill switch blocks new orders, permits cancellations (Principle VI)
    - TRADING_ENV defaults to testnet (Principle IX)
    """

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        kill_switch_engaged: bool,
        spread_cost: float = None,
    ) -> dict:
        """
        Place order and return fill result.

        Args:
            symbol: Trading pair (e.g., "BTC/USD")
            side: "BUY" or "SELL"
            size: Order size in base currency
            price: Limit price (or market approximation)
            kill_switch_engaged: If True, raise KillSwitchEngagedError
            spread_cost: Observed spread cost from market (T028: no synthetic spread)

        Returns:
            Fill dict with keys: timestamp, symbol, side, size, fill_price,
            fees, spread_cost, slippage_cost, total_cost, cad_value

        Constitutional requirements:
            - Raises KillSwitchEngagedError when kill_switch_engaged=True
            - Kill switch blocks new orders (Principle VI)
            - No synthetic spread (T028): spread_cost must be calculated from market state
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, kill_switch_engaged: bool) -> bool:
        """
        Cancel order.

        Args:
            order_id: Order identifier
            kill_switch_engaged: If True, cancellation still succeeds

        Returns:
            True if cancelled, False otherwise

        Constitutional requirements:
            - Cancellation succeeds even when kill switch engaged (Principle VI)
        """
        pass

    @abstractmethod
    async def get_market_data(self) -> AsyncIterator[dict]:
        """
        Stream market data updates.

        Yields:
            Market data dicts with keys: timestamp, symbol, bid_price,
            ask_price, last_price, volume_24h

        Constitutional requirements:
            - No venue-specific types leak above adapter (Principle VII)
        """
        pass
