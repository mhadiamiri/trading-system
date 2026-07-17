"""
Data Adapters - Market Data Feed Adapters

Constitutional Principles:
- VII. Venue Independence: Strict abstraction over venue
"""

from trading.data.adapters.simulated_feed import SimulatedMarketFeed

# Placeholder for Sprint 2: Kraken v2 book adapter (T009-T019)
# Will be implemented in Phase 3
# from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

__all__ = ["SimulatedMarketFeed"]  # Add "KrakenV2BookAdapter" in Phase 3
