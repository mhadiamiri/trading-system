"""
Market Data Feed Factory

Creates feed instances based on configuration.

Constitutional Principles:
- VII. Venue Independence: Abstraction behind factory
- IX. Secrets and Safety Rails: No credentials for public feeds
"""

from typing import AsyncIterator, Optional, List
from trading.data.market_state import MarketState
from trading.data.adapters.simulated_feed import SimulatedMarketFeed
from trading.data.adapters.kraken_public import KrakenPublicFeed
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from trading.logkit.decision import DecisionLogger
from config.settings import Settings


# Store active feed instance for diagnostics
_active_feed: Optional[KrakenPublicFeed | SimulatedMarketFeed | KrakenV2BookAdapter] = None


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
    - No credentials required for any feed (public only)
    """
    global _active_feed
    data_source = Settings.DATA_SOURCE

    if data_source == "simulated":
        print("Using SimulatedMarketFeed")
        feed = SimulatedMarketFeed(update_interval_ms=1000)
        _active_feed = feed
        return feed.get_market_data()

    elif data_source == "kraken_public":
        print("Using KrakenPublicFeed (live mainnet public data)")
        feed = KrakenPublicFeed(
            decision_logger=decision_logger,
            reconnect_base_delay=1.0,
            reconnect_max_delay=60.0,
        )
        _active_feed = feed
        return feed.get_market_data()

    elif data_source == "kraken_v2":
        # WO-008a T035: kraken_v2 adapter implementation (FIXTURES ONLY)
        # No live WebSocket connections - fixture-based testing only
        print("Using KrakenV2BookAdapter (FIXTURES ONLY - no live connection)")
        feed = KrakenV2BookAdapter()
        _active_feed = feed
        return feed.get_market_data()

    else:
        raise ValueError(f"Unknown data source: {data_source}")


def get_data_source() -> str:
    """Get current data source."""
    return Settings.DATA_SOURCE


def is_using_live_feed() -> bool:
    """Check if using live feed."""
    return Settings.DATA_SOURCE in ("kraken_public", "kraken_v2")


def get_active_feed() -> Optional[KrakenPublicFeed | SimulatedMarketFeed | KrakenV2BookAdapter]:
    """
    Get the active feed instance.

    Returns:
        Active feed instance or None if no feed created
    """
    return _active_feed


def get_diagnostic_counters() -> dict:
    """
    Get diagnostic counters from the active feed.

    Returns:
        Dict with diagnostic counters (empty if not using live feed)
    """
    if _active_feed and hasattr(_active_feed, 'get_diagnostic_counters'):
        return _active_feed.get_diagnostic_counters()
    return {}


def get_venue_name() -> str:
    """
    Get the venue name from the active feed adapter.

    Returns:
        Venue name (e.g., "kraken_mainnet", "simulated")
        Returns "unknown" if no active feed
    """
    if _active_feed and hasattr(_active_feed, 'venue_name'):
        return _active_feed.venue_name
    return "unknown"
