"""
Desired Position Data Model

Constitutional Principles:
- III. AI Proposes, Deterministic Code Disposes: No confidence field
- VIII. Total Observability & Provenance: feature_snapshot_hash included
"""

from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


class Side(Enum):
    """Order side direction."""
    BUY = "BUY"      # Long position
    SELL = "SELL"    # Short position
    HOLD = "HOLD"    # No position / flat


@dataclass(frozen=True)
class DesiredPosition:
    """
    Strategy's desired position output.

    Invariants:
    - quantity > 0 if side == Side.BUY
    - quantity < 0 if side == Side.SELL
    - quantity == 0 if side == Side.HOLD
    - feature_snapshot_hash is computed from the MarketState

    Constitutional requirement (Principle III: AI Proposes, Deterministic Code Disposes):
    - No confidence field: This is a latent hook for ML scores to enter live decision path
    - A trivial rule-based strategy has no meaningful confidence value
    """
    timestamp: datetime
    symbol: str
    side: Side
    quantity: Decimal
    feature_snapshot_hash: str  # Hash of MarketState this decision acted on
