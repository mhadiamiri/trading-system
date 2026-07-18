"""
Trivial Momentum/Volume Strategy

A simple rule-based strategy for the walking skeleton.

Constitutional Principles:
- II. Walking Skeleton Before Palace: Deliberately trivial
- III. AI Proposes, Deterministic Code Disposes: Deterministic rule-based
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional

from trading.data.market_state import MarketState
from trading.data.desired_position import DesiredPosition, Side
from trading.strategy.interface import Strategy


class TrivialMomentumStrategy(Strategy):
    """
    Trivial momentum/volume strategy for walking skeleton.

    Signals:
    - BUY when price change > 1% OR volume > 2x average
    - SELL when price change < -1% OR volume > 2x average
    - HOLD otherwise

    Constitutional requirements:
    - Deterministic (same input → same output)
    - No ML/AI in decision path (Principle III)
    """

    # Strategy parameters
    PRICE_CHANGE_PCT = Decimal("0.01")  # 1% price change threshold
    VOLUME_MULTIPLE = Decimal("2.0")  # 2x average volume threshold

    def __init__(self) -> None:
        """Initialize the strategy."""
        self._version = "trivial-momentum-v1.0.0"
        self._last_price: Optional[Decimal] = None
        self._average_volume: Optional[Decimal] = None
        self._volume_samples: list[Decimal] = []

    @property
    def version(self) -> str:
        """Return strategy version identifier."""
        return self._version

    def decide(self, market_state: MarketState) -> Optional[DesiredPosition]:
        """
        Evaluate market state and return desired position.

        Args:
            market_state: Current market data view

        Returns:
            DesiredPosition if signal exists, None for "no signal"
        """
        # Update average volume (simple moving average)
        self._update_average_volume(market_state.total_volume)

        # Check for signals
        side = self._evaluate_signal(market_state)

        if side == Side.HOLD:
            return None  # No signal

        # For simplicity, always request fixed size of 0.1 BTC
        quantity = Decimal("0.1")

        return DesiredPosition(
            timestamp=datetime.now(UTC),
            symbol=market_state.symbol,
            side=side,
            quantity=quantity,
            feature_snapshot_hash=market_state.compute_snapshot_hash(),
        )

    def _update_average_volume(self, volume: Decimal) -> None:
        """Update average volume using simple moving average."""
        self._volume_samples.append(volume)

        # Keep only last 100 samples
        if len(self._volume_samples) > 100:
            self._volume_samples.pop(0)

        self._average_volume = sum(self._volume_samples) / len(self._volume_samples)

    def _evaluate_signal(self, market_state: MarketState) -> Side:
        """Evaluate trading signal based on price and volume."""
        if self._last_price is None:
            self._last_price = market_state.last_price
            return Side.HOLD

        # Calculate price change percentage
        price_change = (market_state.last_price - self._last_price) / self._last_price

        # Check volume spike
        volume_spike = False
        if self._average_volume and self._average_volume > 0:
            volume_ratio = market_state.total_volume / self._average_volume
            volume_spike = volume_ratio >= self.VOLUME_MULTIPLE

        # Update last price
        self._last_price = market_state.last_price

        # Generate signal
        if price_change >= self.PRICE_CHANGE_PCT or volume_spike:
            return Side.BUY
        elif price_change <= -self.PRICE_CHANGE_PCT:
            return Side.SELL
        else:
            return Side.HOLD
