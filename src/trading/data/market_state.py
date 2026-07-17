"""
Market Data Model

Constitutional Principles:
- VIII. Total Observability & Provenance
- V. No Backtest Without Costs: Observed spread only
"""

from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional
import hashlib
import json


@dataclass(frozen=True)
class MarketState:
    """
    Aggregated market data view at a point in time.

    Sprint 2: Quote-centric schema with observed spread (no synthetic/assumed values).

    Constitutional Requirements:
    - V. No Backtest Without Costs: spread, mid_price derived from actual bid/ask
    - VIII. Total Observability & Provenance: compute_snapshot_hash() provides
      hash for decision reconstruction
    """
    timestamp: datetime
    symbol: str

    # Quote-level fields (Sprint 2)
    best_bid: Decimal
    best_ask: Decimal
    best_bid_size: Decimal
    best_ask_size: Decimal

    # Derived fields (computed from bid/ask)
    mid_price: Decimal = field(init=False)
    spread: Decimal = field(init=False)

    # Rolling trade stats (Sprint 2)
    trade_count: int
    total_volume: Decimal
    last_price: Optional[Decimal]

    def __post_init__(self):
        """Validate and compute derived fields after initialization."""
        # Validation: bid > 0, ask > 0, bid < ask
        if self.best_bid <= 0:
            raise ValueError(f"best_bid must be > 0, got {self.best_bid}")
        if self.best_ask <= 0:
            raise ValueError(f"best_ask must be > 0, got {self.best_ask}")
        if self.best_bid >= self.best_ask:
            raise ValueError(f"best_bid ({self.best_bid}) must be < best_ask ({self.best_ask})")

        # Validate sizes
        if self.best_bid_size < 0:
            raise ValueError(f"best_bid_size must be >= 0, got {self.best_bid_size}")
        if self.best_ask_size < 0:
            raise ValueError(f"best_ask_size must be >= 0, got {self.best_ask_size}")

        # Validate trade stats
        if self.trade_count < 0:
            raise ValueError(f"trade_count must be >= 0, got {self.trade_count}")
        if self.total_volume < 0:
            raise ValueError(f"total_volume must be >= 0, got {self.total_volume}")

        # Compute derived fields
        object.__setattr__(self, 'mid_price', (self.best_bid + self.best_ask) / 2)
        object.__setattr__(self, 'spread', self.best_ask - self.best_bid)

    def compute_snapshot_hash(self) -> str:
        """
        Compute a hash of the market state snapshot for provenance.

        Returns:
            SHA256 hash string representing this market state

        Constitutional requirement (Principle VIII: Total Observability & Provenance):
        - DecisionRecord requires feature_snapshot_hash for audit trail
        - This hash captures the exact market state the decision acted on
        """
        # Create a canonical representation of the market state
        state_dict = {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "best_bid": str(self.best_bid),
            "best_ask": str(self.best_ask),
            "best_bid_size": str(self.best_bid_size),
            "best_ask_size": str(self.best_ask_size),
            "mid_price": str(self.mid_price),
            "spread": str(self.spread),
            "trade_count": self.trade_count,
            "total_volume": str(self.total_volume),
            "last_price": str(self.last_price) if self.last_price else None,
        }
        state_json = json.dumps(state_dict, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()
