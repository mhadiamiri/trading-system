"""
Market Data Feed Factory

Creates feed instances based on configuration.

Constitutional Principles:
- VII. Venue Independence: Abstraction behind factory
"""

from typing import AsyncIterator
from trading.data.market_state import MarketState
from trading.data.adapters.simulated_feed import SimulatedMarketFeed
from trading.data.adapters.bybit_testnet import BybitTestnetFeed
from trading.logkit.decision import DecisionLogger
from config.settings import Settings


def create_feed(
    decision_logger: DecisionLogger | None = None
) -> AsyncIterator[MarketState]:
    """
    Create market data feed based on configuration.

    Args:
        decision_logger: Optional decision logger for feed events

    Returns:
        AsyncIterator yielding MarketState objects

    Constitutional requirements:
    - Feed selection via config only (no code changes)
    - Default to simulated for tests
    """
    feed_type = Settings.FEED_TYPE

    if feed_type == "simulated":
        print("Using SimulatedMarketFeed")
        feed = SimulatedMarketFeed(update_interval_ms=1000)
        return feed.get_market_data()

    elif feed_type == "bybit_testnet":
        print("Using BybitTestnetFeed (live testnet)")
        feed = BybitTestnetFeed(
            decision_logger=decision_logger,
            reconnect_base_delay=1.0,
            reconnect_max_delay=60.0,
        )
        return feed.get_market_data()

    else:
        raise ValueError(f"Unknown feed type: {feed_type}")


def get_feed_type() -> str:
    """Get current feed type."""
    return Settings.FEED_TYPE


def is_using_live_feed() -> bool:
    """Check if using live feed."""
    return Settings.FEED_TYPE == "bybit_testnet"
