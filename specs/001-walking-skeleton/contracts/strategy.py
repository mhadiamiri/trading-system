"""
Strategy Interface Contract

This module defines the Strategy interface that all trading strategies must implement.

Constitutional Principles:
- II. Walking Skeleton Before Palace: Simple strategy before sophistication
- III. AI Proposes, Deterministic Code Disposes: Strategy output is advisory only
"""

from typing import Optional
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


@dataclass(frozen=True)
class DesiredPosition:
    """
    Strategy's desired position output.

    Invariants:
    - quantity > 0 if side == Side.BUY
    - quantity < 0 if side == Side.SELL
    - quantity == 0 if side == Side.HOLD
    - confidence in range [0.0, 1.0]

    Note: This is ADVISORY only. The risk engine makes the final decision.
    """
    timestamp: datetime
    symbol: str
    side: Side
    quantity: Decimal
    confidence: float


class Strategy:
    """
    Strategy interface.

    All trading strategies must implement this interface.

    Constitutional requirements:
    - Output is advisory only (risk engine has final authority)
    - Must be deterministic (same input → same output)
    - May use AI internally but output must be a simple DesiredPosition
    """

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

        Example:
            A simple momentum strategy:
            - Returns DesiredPosition(symbol="BTC/USD", side=Side.BUY, quantity=0.1)
              when price change > 1% in last 60 seconds
            - Returns None otherwise
        """
        raise NotImplementedError("Strategy must implement decide()")
