"""
Data Adapters - Market Data Feed Adapters

Constitutional Principles:
- VII. Venue Independence: Strict abstraction over venue

WO-010 §5: importing this package imports every adapter module, which is what
triggers their self-registration in `registry`. These imports are deliberately
module-level and deliberately live HERE, inside `trading.data.adapters` — the
one place permitted to know concrete adapter modules. Nothing outside this
package imports an adapter module; the registry is the sole resolution path.
"""

from trading.data.adapters.kraken_public import KrakenPublicFeed
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from trading.data.adapters.simulated_feed import SimulatedMarketFeed

__all__ = ["SimulatedMarketFeed", "KrakenPublicFeed", "KrakenV2BookAdapter"]
