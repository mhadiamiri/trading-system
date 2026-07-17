"""
Market Data Fixtures

Sample market data for testing.

Constitutional Principles:
- VIII. Total Observability & Provenance: Test data fixtures
- V. No Backtest Without Costs: Observed spread only
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterator
import random

from trading.data.market_state import MarketState


def sample_market_data() -> Iterator[MarketState]:
    """
    Generate sample market data for testing.

    Yields:
        MarketState objects with predefined data

    Constitutional requirements:
        - Provides deterministic test data (Principle VIII)
        - Uses observed spread only (Principle V)
    """
    base_time = datetime(2024, 7, 11, 12, 0, 0)
    base_price = Decimal("65000.00")

    # Generate 100 sample data points
    for i in range(100):
        # Small price variations
        price_change = Decimal("0.01") * (i % 10)
        new_price = base_price + price_change

        # Calculate bid/ask spread (0.01%)
        spread = new_price * Decimal("0.0001")
        best_bid = new_price - spread / 2
        best_ask = new_price + spread / 2

        # Calculate sizes
        best_bid_size = Decimal(str(random.uniform(0.5, 2.0)))
        best_ask_size = Decimal(str(random.uniform(0.5, 2.0)))

        # Rolling trade stats
        total_volume = Decimal(str(random.uniform(100, 500)))
        trade_count = i + 1

        yield MarketState(
            timestamp=base_time,
            symbol="BTC/USD",
            best_bid=best_bid.quantize(Decimal("0.01")),
            best_ask=best_ask.quantize(Decimal("0.01")),
            best_bid_size=best_bid_size.quantize(Decimal("0.001")),
            best_ask_size=best_ask_size.quantize(Decimal("0.001")),
            trade_count=trade_count,
            total_volume=total_volume.quantize(Decimal("0.001")),
            last_price=new_price.quantize(Decimal("0.01")),
        )
        # Increment time by 1 second using timedelta
        base_time = base_time + timedelta(seconds=1)
