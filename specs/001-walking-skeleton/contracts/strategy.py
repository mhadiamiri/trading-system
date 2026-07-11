"""
Strategy Interface Contract

This module defines the Strategy interface that all trading strategies must implement.

Constitutional Principles:
- II. Walking Skeleton Before Palace: Simple strategy before sophistication
- III. AI Proposes, Deterministic Code Disposes: Strategy output is advisory only
- VIII. Total Observability & Provenance: Decision records include version and snapshot hash
"""

from typing import Optional, Tuple
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import hashlib
import json


class Side(Enum):
    """Order side direction."""
    BUY = "BUY"      # Long position
    SELL = "SELL"    # Short position
    HOLD = "HOLD"    # No position / flat


@dataclass(frozen=True)
class MarketState:
    """
    Aggregated market data view at a point in time.

    Invariants:
    - ask_price >= bid_price (spread is non-negative)
    - timestamp is UTC timezone-aware
    """
    timestamp: datetime
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    last_price: Decimal
    volume_24h: Decimal

    def compute_snapshot_hash(self) -> str:
        """
        Compute a hash of the market state snapshot for provenance.

        Returns:
            SHA256 hash string representing this market state

        Constitutional requirement (Principle VIII: Total Observability & Provenance):
        - DecisionRecord requires feature_snapshot_hash for audit trail
        - This hash captures the exact market state the decision acted on
        - Enables reconstruction of why a decision was made during failure review
        """
        # Create a canonical representation of the market state
        state_dict = {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "bid_price": str(self.bid_price),
            "ask_price": str(self.ask_price),
            "last_price": str(self.last_price),
            "volume_24h": str(self.volume_24h),
        }
        state_json = json.dumps(state_dict, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()


@dataclass(frozen=True)
class DesiredPosition:
    """
    Strategy's desired position output.

    Invariants:
    - quantity > 0 if side == Side.BUY
    - quantity < 0 if side == Side.SELL
    - quantity == 0 if side == Side.HOLD

    Constitutional requirement (Principle III: AI Proposes, Deterministic Code Disposes):
    - No confidence field: This is a latent hook for ML scores to enter live decision path
    - A trivial rule-based strategy has no meaningful confidence value
    - If a future phase needs confidence, it gets added deliberately with a requirement

    Note: This is ADVISORY only. The risk engine makes the final decision.
    """
    timestamp: datetime
    symbol: str
    side: Side
    quantity: Decimal
    feature_snapshot_hash: str  # Hash of MarketState this decision acted on


class Strategy:
    """
    Strategy interface.

    All trading strategies must implement this interface.

    Constitutional requirements:
    - Output is advisory only (risk engine has final authority)
    - Must be deterministic (same input → same output)
    - May use AI internally but output must be a simple DesiredPosition
    - Must expose version identifier for provenance (Principle VIII)
    - Must provide feature_snapshot_hash for decision reconstruction (Principle VIII)
    """

    @property
    def version(self) -> str:
        """
        Strategy version identifier for provenance.

        Returns:
            Version string (e.g., "v1.0.0", "trivial-momentum-2024-07-11")

        Constitutional requirement (Principle VIII: Total Observability & Provenance):
        - DecisionRecord requires strategy_version for audit trail
        - This version identifies which strategy logic produced a given decision
        - Enables tracing decisions back to specific strategy code during failure review
        """
        raise NotImplementedError("Strategy must implement version property")

    def decide(self, market_state: MarketState) -> Optional[DesiredPosition]:
        """
        Evaluate market state and return desired position.

        Args:
            market_state: Current market data view

        Returns:
            DesiredPosition if signal exists, None for "no signal"

        Behavioral contract:
        - MUST be deterministic (same market_state → same output)
        - MAY return None to indicate "no signal"
        - MUST NOT directly place orders (that's execution's job)
        - MUST NOT depend on risk engine or execution layer
        - MUST include feature_snapshot_hash for provenance (Principle VIII)

        Provenance capture (Principle VIII: Total Observability & Provenance):
        - DesiredPosition.feature_snapshot_hash must be computed from market_state
        - Use MarketState.compute_snapshot_hash() to generate the hash
        - This hash becomes part of DecisionRecord for audit trail

        Example:
            A simple momentum strategy:
            - Returns DesiredPosition(
                symbol="BTC/USD",
                side=Side.BUY,
                quantity=Decimal("0.1"),
                feature_snapshot_hash=market_state.compute_snapshot_hash()
              ) when price change > 1% in last 60 seconds
            - Returns None otherwise
        """
        raise NotImplementedError("Strategy must implement decide()")
