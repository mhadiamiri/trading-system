"""
Test to show full cycle with actual fills and visible costs.
"""
import pytest
import asyncio
from datetime import datetime, UTC
from decimal import Decimal
from trading.loop.live import LiveTradingLoop
from trading.data.market_state import MarketState
from trading.logkit.decision import DecisionLogger, Layer
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_full_cycle_with_visible_costs():
    """Show full cycle with all cost components visible."""
    # Create test data that WILL trigger the strategy
    # Need 1% price change OR 2x volume

    # Create an iterator with signal-generating data
    from typing import AsyncIterator

    async def signal_generating_feed() -> AsyncIterator[MarketState]:
        """Generate data that triggers the strategy."""
        base_time = datetime(2024, 7, 11, 12, 0, 0)

        # First event: establish baseline
        yield MarketState(
            timestamp=base_time,
            symbol="BTC/USD",
            best_bid=Decimal("65000.00"),
            best_ask=Decimal("65005.00"),  # $5 spread
            best_bid_size=Decimal("1.5"),
            best_ask_size=Decimal("2.0"),
            trade_count=100,
            total_volume=Decimal("200.0"),
            last_price=Decimal("65000.00"),
        )

        # Second event: 1.5% price increase (triggers BUY)
        yield MarketState(
            timestamp=base_time,
            symbol="BTC/USD",
            best_bid=Decimal("65975.00"),  # 1.5% higher
            best_ask=Decimal("65980.00"),  # $5 spread
            best_bid_size=Decimal("1.5"),
            best_ask_size=Decimal("2.0"),
            trade_count=110,
            total_volume=Decimal("210.0"),
            last_price=Decimal("65975.00"),  # 1.5% higher - triggers signal
        )

        # Third event: another fill opportunity
        yield MarketState(
            timestamp=base_time,
            symbol="BTC/USD",
            best_bid=Decimal("66950.00"),  # Another 1.5% higher
            best_ask=Decimal("66955.00"),  # $5 spread
            best_bid_size=Decimal("1.5"),
            best_ask_size=Decimal("2.0"),
            trade_count=120,
            total_volume=Decimal("220.0"),
            last_price=Decimal("66950.00"),
        )

    # Patch SimulatedMarketFeed to use our signal-generating feed
    with patch('trading.data.adapters.simulated_feed.SimulatedMarketFeed.get_market_data', return_value=signal_generating_feed()):
        loop = LiveTradingLoop()

        # Clear decision log
        import os
        log_path = "logs/decisions.log"
        if os.path.exists(log_path):
            os.remove(log_path)

        # Run loop
        result = await loop.run(max_updates=10, duration_minutes=1)

        print(f"\nProcessed: {result['processed_count']}")
        print(f"Trades: {result['trades_count']}")

        # Verify trades were executed
        assert result["trades_count"] > 0, "Should have executed trades with our signal data"

        # Read and print decision log
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                log_lines = f.readlines()
            print(f"\nDecision log entries: {len(log_lines)}")
            for line in log_lines:
                print(line.strip())
