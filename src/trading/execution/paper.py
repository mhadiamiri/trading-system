"""
Paper Execution Client

Simulated execution for paper trading (no real money).

Constitutional Principles:
- VI. Risk Engine Is Sovereign: Kill switch semantics
- IX. Secrets and Safety Rails: No real-money orders
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import AsyncIterator
import asyncio

from trading.execution.interface import ExchangeClient, KillSwitchEngagedError
from trading.execution.fill import Fill


class PaperExecutionClient(ExchangeClient):
    """
    Simulated (paper) execution client.

    All fills are simulated with realistic cost modeling:
    - Trading fees (default 0.1% taker per side)
    - Bid/ask spread cost
    - Slippage adjustment

    Constitutional requirements:
    - No real-money orders (simulated only)
    - Kill switch blocks new orders (Principle VI)
    - Cancellation succeeds even when kill switch engaged (Principle VI)
    """

    # Default cost parameters
    DEFAULT_FEE_RATE_PCT = Decimal("0.1")  # 0.1% taker fee per side
    DEFAULT_SPREAD_PCT = Decimal("0.05")  # 0.05% spread
    DEFAULT_SLIPPAGE_FACTOR = Decimal("0.001")  # 0.1% slippage factor

    def __init__(
        self,
        fee_rate_pct: Decimal = DEFAULT_FEE_RATE_PCT,
        spread_pct: Decimal = DEFAULT_SPREAD_PCT,
        slippage_factor: Decimal = DEFAULT_SLIPPAGE_FACTOR,
    ) -> None:
        """
        Initialize paper execution client.

        Args:
            fee_rate_pct: Trading fee rate as percentage (default 0.1%)
            spread_pct: Bid/ask spread as percentage (default 0.05%)
            slippage_factor: Slippage adjustment factor (default 0.001)

        Raises:
            ValueError: If TRADING_ENV is not 'paper' (constitutional guard)

        Constitutional requirements:
            - PaperExecutionClient can ONLY be used when TRADING_ENV=paper
            - This ensures no real-money orders can be placed in paper mode
            - When real-money adapters are added (Sprint 3), they will have
              an inverse check requiring TRADING_ENV=mainnet
        """
        # CONSTITUTIONAL GUARD (Principle IX):
        # Verify this client is only used in paper trading mode
        from config.settings import Settings

        if not Settings.is_paper_trading():
            raise ValueError(
                f"PaperExecutionClient CANNOT be used when TRADING_ENV={Settings.TRADING_ENV}. "
                f"PaperExecutionClient is for paper trading only (TRADING_ENV=paper). "
                f"This is a constitutional guard preventing accidental real-money order placement. "
                f"See .specify/memory/constitution.md Principle IX."
            )

        self._fee_rate_pct = fee_rate_pct
        self._spread_pct = spread_pct
        self._slippage_factor = slippage_factor
        self._orders: dict[str, dict] = {}  # Simulated order book

    async def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        kill_switch_engaged: bool,
    ) -> dict:
        """
        Place simulated order and return fill result.

        Args:
            symbol: Trading pair
            side: "BUY" or "SELL"
            size: Order size
            price: Limit price
            kill_switch_engaged: If True, raise KillSwitchEngagedError

        Returns:
            Fill dict with all cost components

        Raises:
            KillSwitchEngagedError: When kill_switch_engaged=True

        Constitutional requirements:
            - Raises KillSwitchEngagedError when kill switch engaged (Principle VI)
        """
        if kill_switch_engaged:
            raise KillSwitchEngagedError()

        # Simulate fill with realistic costs
        fill = self._simulate_fill(symbol, side, size, price)
        return {
            "timestamp": fill.timestamp.isoformat(),
            "symbol": fill.symbol,
            "side": fill.side,
            "size": float(fill.size),
            "fill_price": float(fill.fill_price),
            "fees": float(fill.fees),
            "spread_cost": float(fill.spread_cost),
            "slippage_cost": float(fill.slippage_cost),
            "total_cost": float(fill.total_cost),
            "cad_value": float(fill.cad_value),
        }

    async def cancel_order(self, order_id: str, kill_switch_engaged: bool) -> bool:
        """
        Cancel simulated order.

        Args:
            order_id: Order identifier
            kill_switch_engaged: Ignored for cancellation

        Returns:
            True if cancelled, False if order not found

        Constitutional requirements:
            - Cancellation succeeds even when kill switch engaged (Principle VI)
        """
        # Simulated cancellation - ignore kill_switch_engaged
        if order_id in self._orders:
            del self._orders[order_id]
            return True
        return False

    async def get_market_data(self) -> AsyncIterator[dict]:
        """
        Stream simulated market data updates.

        Yields:
            Market data dicts

        Note:
            This is a placeholder. Real implementation in Task 106.
        """
        # Placeholder - will be implemented in Task 106
        yield {}
        return

    def _simulate_fill(
        self, symbol: str, side: str, size: float, price: float
    ) -> Fill:
        """
        Simulate fill with realistic cost modeling.

        Args:
            symbol: Trading pair
            side: "BUY" or "SELL"
            size: Order size
            price: Intended price

        Returns:
            Fill with all cost components

        Constitutional requirements:
            - All costs included (Principle I: Truth Before Profit)
        """
        size_dec = Decimal(str(size))
        price_dec = Decimal(str(price))
        notional = size_dec * price_dec

        # Calculate trading fee
        fees = notional * (self._fee_rate_pct / Decimal("100"))

        # Calculate spread cost
        spread_cost = notional * (self._spread_pct / Decimal("100"))

        # Calculate slippage cost
        slippage_cost = notional * self._slippage_factor

        # Total cost
        total_cost = fees + spread_cost + slippage_cost

        # CAD value (assume 1 USD = 1.35 CAD for simplicity)
        cad_value = notional * Decimal("1.35")

        return Fill(
            timestamp=datetime.now(UTC),
            symbol=symbol,
            side=side,
            size=size_dec,
            fill_price=price_dec,
            spread_cost=spread_cost,
            slippage_cost=slippage_cost,
            fees=fees,
            total_cost=total_cost,
            cad_value=cad_value,
        )
