"""
Market Data Feed Factory

Creates feed instances based on configuration.

Constitutional Principles:
- VII. Venue Independence: Abstraction behind factory
- IX. Secrets and Safety Rails: No credentials for public feeds

WO-010 §5: this module resolves adapters BY NAME through `registry`. It does not
import any concrete adapter module. Adapters self-register when
`trading.data.adapters` is imported; config names the adapter by string.
"""

from typing import Any, AsyncIterator, Optional

from trading.data.market_state import MarketState
from trading.data.adapters import registry
from trading.logkit.decision import DecisionLogger
from config.settings import Settings


# Store active feed instance for diagnostics
_active_feed: Optional[Any] = None


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

    feed = registry.create(data_source, decision_logger=decision_logger)
    print(f"Using adapter registered as {data_source!r}: {type(feed).__name__}")
    _active_feed = feed
    return feed.get_market_data()


def create_live_capture_feed(
    persist_path,
    duration_seconds: float,
    decision_logger: DecisionLogger | None = None,
):
    """
    WO-015: resolve a LIVE-mode adapter through the registry (the sole adapter-resolution path,
    Principle IV/VII) and return (adapter, live_feed_iterator) for the live-capture runner. The
    runner lives in trading.loop and MUST NOT import a concrete adapter; it goes through here.

    The registry builds the live adapter with persistence configured, so neither the factory nor
    the runner reaches into adapter internals. Sets the active feed for diagnostics/venue_name.

    Resolves the v2 BOOK adapter (`kraken_v2`) explicitly: the instrumented live transport
    (get_live_market_data + gap ledger + failure capture + discrimination) exists ONLY there, so a
    "live capture" is the v2 book adapter by definition (Settings.DATA_SOURCE for the re-run IS
    `kraken_v2`). Naming the live-capable source here is robust — it never passes a live-only kwarg
    to a non-live builder — and it is the registry's single point of venue selection (Principle VII).

    Opens NO socket itself — get_live_market_data does (real in production, patched in tests).
    """
    global _active_feed
    feed = registry.create(
        "kraken_v2",
        decision_logger=decision_logger,
        mode="live",
        gap_persist_path=str(persist_path),
    )
    _active_feed = feed
    return feed, feed.get_live_market_data(duration_seconds)


def get_data_source() -> str:
    """Get current data source."""
    return Settings.DATA_SOURCE


def is_using_live_feed() -> bool:
    """Check if using live feed."""
    return Settings.DATA_SOURCE in ("kraken_public", "kraken_v2")


def get_active_feed() -> Optional[Any]:
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
