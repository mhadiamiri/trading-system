"""
Strategy Interface Contract

This module defines the Strategy interface that all trading strategies must implement.

Constitutional Principles:
- II. Walking Skeleton Before Palace: Simple strategy before sophistication
- III. AI Proposes, Deterministic Code Disposes: Strategy output is advisory only
- VIII. Total Observability & Provenance: Decision records include version and snapshot hash
"""

from typing import Optional
from abc import ABC, abstractmethod
from decimal import Decimal

from trading.data.market_state import MarketState
from trading.data.desired_position import DesiredPosition, Side


class Strategy(ABC):
    """
    Strategy interface.

    All trading strategies must implement this interface.

    Constitutional requirements:
    - Output is advisory only (risk engine has final authority)
    - Must be deterministic (same input → same output)
    - May use AI internally but output must be a simple DesiredPosition
    - Must expose version identifier for provenance (Principle VIII)
    """

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Strategy version identifier for provenance.

        Returns:
            Version string (e.g., "v1.0.0", "trivial-momentum-2024-07-11")

        Constitutional requirement (Principle VIII: Total Observability & Provenance):
        - DecisionRecord requires strategy_version for audit trail
        - This version identifies which strategy logic produced a given decision
        """
        pass

    @abstractmethod
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
        """
        pass
