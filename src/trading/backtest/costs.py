"""
Cost Model for Backtesting

Models realistic trading costs: fees, spread, and slippage.

Constitutional Principles:
- I. Truth Before Profit: All costs modeled explicitly
- V. No Backtest Without Costs: No cost-free code path
"""

from decimal import Decimal
from dataclasses import dataclass
from typing import Dict
from enum import Enum


class Side(Enum):
    """Order side."""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class CostBreakdown:
    """
    Cost breakdown for a single trade.

    Constitutional requirements:
        - All cost components listed separately (Principle I)
        - No cost-free code path exists (Principle V)
    """
    fees: Decimal
    spread_cost: Decimal
    slippage_cost: Decimal
    total_cost: Decimal

    def __post_init__(self):
        """Validate cost breakdown."""
        assert self.fees >= 0, "Fees cannot be negative"
        assert self.spread_cost >= 0, "Spread cost cannot be negative"
        assert self.slippage_cost >= 0, "Slippage cost cannot be negative"
        assert self.total_cost == self.fees + self.spread_cost + self.slippage_cost, \
            "Total cost must equal sum of components"


class CostModel:
    """
    Trading cost model for backtesting.

    Models three cost components:
    1. Trading fees (taker fees for momentum strategy)
    2. Bid/ask spread (buy at ask, sell at bid)
    3. Slippage (price impact based on order size)

    Constitutional requirements:
        - Fees applied to every simulated trade (Principle V)
        - No cost-free code path exists (Principle V)
        - Taker fees for momentum strategy crossing spread
    """

    # Default parameters (configurable)
    DEFAULT_FEE_RATE_PCT = Decimal("0.1")  # 0.1% taker fee per side
    DEFAULT_SPREAD_PCT = Decimal("0.01")  # 0.01% spread (0.5 bps)
    DEFAULT_SLIPPAGE_FACTOR = Decimal("0.001")  # Linear slippage factor

    def __init__(
        self,
        fee_rate_pct: Decimal = None,
        spread_pct: Decimal = None,
        slippage_factor: Decimal = None,
    ) -> None:
        """
        Initialize cost model.

        Args:
            fee_rate_pct: Taker fee rate as % of notional (default 0.1%)
            spread_pct: Bid/ask spread as % of mid-price (default 0.01%)
            slippage_factor: Linear slippage factor (default 0.001)
        """
        self._fee_rate_pct = fee_rate_pct or self.DEFAULT_FEE_RATE_PCT
        self._spread_pct = spread_pct or self.DEFAULT_SPREAD_PCT
        self._slippage_factor = slippage_factor or self.DEFAULT_SLIPPAGE_FACTOR

    def calculate_costs(
        self,
        side: Side,
        size: Decimal,
        price: Decimal,
        avg_volume: Decimal = Decimal("1000"),
    ) -> CostBreakdown:
        """
        Calculate all trading costs for an order.

        Args:
            side: Order side (BUY or SELL)
            size: Order size in base currency
            price: Mid-price or reference price
            avg_volume: Average volume for slippage calculation (default 1000)

        Returns:
            CostBreakdown with all cost components

        Constitutional requirements:
            - Fees applied to every trade (Principle V)
            - Spread applied on both entry and exit
            - Slippage reduces fill prices
            - No cost-free code path exists
        """
        notional = size * price

        # 1. Trading fees (taker fee for momentum strategy)
        fees = notional * (self._fee_rate_pct / Decimal("100"))

        # 2. Spread cost (buy at ask, sell at bid)
        # Spread is paid on both entry and exit
        spread_cost = notional * (self._spread_pct / Decimal("100"))

        # 3. Slippage (linear function of order size vs liquidity)
        # Slippage increases with order size relative to average volume
        volume_ratio = size / avg_volume if avg_volume > 0 else Decimal("0")
        slippage_cost = notional * self._slippage_factor * volume_ratio

        # Round to 2 decimal places
        fees_rounded = fees.quantize(Decimal("0.01"))
        spread_rounded = spread_cost.quantize(Decimal("0.01"))
        slippage_rounded = slippage_cost.quantize(Decimal("0.01"))

        # Calculate total from rounded components to ensure validation passes
        total_rounded = (fees_rounded + spread_rounded + slippage_rounded).quantize(Decimal("0.01"))

        return CostBreakdown(
            fees=fees_rounded,
            spread_cost=spread_rounded,
            slippage_cost=slippage_rounded,
            total_cost=total_rounded,
        )

    def get_fill_price(
        self,
        side: Side,
        mid_price: Decimal,
        size: Decimal,
        avg_volume: Decimal = Decimal("1000"),
    ) -> Decimal:
        """
        Calculate effective fill price including spread and slippage.

        Args:
            side: Order side (BUY or SELL)
            mid_price: Mid-price or reference price
            size: Order size
            avg_volume: Average volume for slippage calculation

        Returns:
            Effective fill price after spread and slippage

        Constitutional requirements:
            - Buy at ask (mid + spread/2)
            - Sell at bid (mid - spread/2)
            - Slippage worsens the price
        """
        costs = self.calculate_costs(side, size, mid_price, avg_volume)

        # Calculate spread adjustment (half spread each way)
        half_spread = mid_price * (self._spread_pct / Decimal("100")) / Decimal("2")

        if side == Side.BUY:
            # Buy at ask: mid + half spread + slippage impact
            spread_adjustment = half_spread
        else:
            # Sell at bid: mid - half spread - slippage impact
            spread_adjustment = -half_spread

        # Slippage also worsens the price (higher for buy, lower for sell)
        slippage_per_unit = costs.slippage_cost / size if size > 0 else Decimal("0")

        if side == Side.BUY:
            return mid_price + spread_adjustment + slippage_per_unit
        else:
            return mid_price + spread_adjustment - slippage_per_unit
