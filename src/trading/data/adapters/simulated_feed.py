"""
Simulated Market Data Feed

Generates mock market data for testing (no live connection).

Constitutional Principles:
- VII. Venue Independence: Strict abstraction
- IX. Secrets and Safety Rails: No live connection for testnet
"""

import asyncio
from datetime import datetime, UTC
from decimal import Decimal
from typing import AsyncIterator
import random

from trading.data.market_state import MarketState


class SimulatedMarketFeed:
    """
    Simulated market data feed for testing.

    Generates mock market data updates for BTC/USD pair.

    Constitutional requirements:
    - No venue-specific types leak above adapter (Principle VII)
    - No live connection to testnet (per instructions.md)
    """

    SYMBOL = "BTC/USD"
    BASE_PRICE = Decimal("65000.00")

    def __init__(self, update_interval_ms: int = 1000) -> None:
        """
        Initialize simulated feed.

        Args:
            update_interval_ms: Milliseconds between updates (default 1000)
        """
        self._update_interval_ms = update_interval_ms
        self._running = False
        self._last_price = self.BASE_PRICE

    async def get_market_data(self) -> AsyncIterator[MarketState]:
        """
        Stream simulated market data updates.

        Yields:
            MarketState objects with mock data

        Constitutional requirements:
            - No venue-specific types leak above adapter (Principle VII)
        """
        self._running = True

        while self._running:
            # Generate realistic price movement
            price_change = Decimal(str(random.uniform(-0.005, 0.005)))  # ±0.5%
            new_price = self._last_price * (Decimal("1") + price_change)

            # Ensure price doesn't go negative
            if new_price < Decimal("1000"):
                new_price = Decimal("1000")

            self._last_price = new_price

            # Calculate bid/ask spread (0.01%)
            spread = new_price * Decimal("0.0001")
            best_bid = new_price - spread / 2
            best_ask = new_price + spread / 2

            # Generate sizes
            best_bid_size = Decimal(str(random.uniform(0.5, 5.0)))
            best_ask_size = Decimal(str(random.uniform(0.5, 5.0)))

            # Generate rolling trade stats
            trade_count = random.randint(50, 200)
            total_volume = Decimal(str(random.uniform(100, 1000)))

            yield MarketState(
                timestamp=datetime.now(UTC),
                symbol=self.SYMBOL,
                best_bid=best_bid.quantize(Decimal("0.01")),
                best_ask=best_ask.quantize(Decimal("0.01")),
                best_bid_size=best_bid_size.quantize(Decimal("0.001")),
                best_ask_size=best_ask_size.quantize(Decimal("0.001")),
                trade_count=trade_count,
                total_volume=total_volume.quantize(Decimal("0.001")),
                last_price=new_price.quantize(Decimal("0.01")),
            )

            # Wait before next update
            await asyncio.sleep(self._update_interval_ms / 1000)

    def stop(self) -> None:
        """Stop the simulated feed."""
        self._running = False

    @property
    def venue_name(self) -> str:
        """Return the venue name for this feed adapter."""
        return "simulated"


# --- WO-010 §5: self-registration ---------------------------------------
from trading.data.adapters.registry import register  # noqa: E402


@register("simulated")
def _build_simulated(decision_logger=None) -> "SimulatedMarketFeed":
    """Builder invoked by the registry when DATA_SOURCE=simulated."""
    return SimulatedMarketFeed(update_interval_ms=1000)
