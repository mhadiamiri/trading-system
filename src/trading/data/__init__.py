"""
Data Layer - Market Data Models and Adapters

Constitutional Principles:
- IV. Layered Architecture, Enforced Boundaries
- VII. Venue Independence: Strict abstraction
- VIII. Total Observability & Provenance
"""

from trading.data.market_state import MarketState
from trading.data.desired_position import DesiredPosition, Side
from trading.data.adapters.simulated_feed import SimulatedMarketFeed
from trading.data.fixtures import sample_market_data

__all__ = [
    "MarketState",
    "DesiredPosition",
    "Side",
    "SimulatedMarketFeed",
    "sample_market_data",
]
