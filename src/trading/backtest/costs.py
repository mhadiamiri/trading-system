"""
Cost Model for Backtesting

Models realistic trading costs: fees, spread, and slippage.

Constitutional Principles:
- I. Truth Before Profit: All costs modeled explicitly
- V. No Backtest Without Costs: No cost-free code path
- FR-011: Spread cost computed from observed bid/ask
- FR-015a: No synthetic spread anywhere
- FR-015b: REJECT trade on abnormal spread
"""

from decimal import Decimal
from dataclasses import dataclass
from typing import Dict, Optional, TYPE_CHECKING
from enum import Enum

# Avoid circular import
if TYPE_CHECKING:
    from trading.data.market_state import MarketState


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
    # DEFAULT_SPREAD_PCT REMOVED (T028): No synthetic spread - use calculate_costs_from_market_state()
    DEFAULT_SLIPPAGE_FACTOR = Decimal("0.001")  # Linear slippage factor

    def __init__(
        self,
        fee_rate_pct: Decimal = None,
        slippage_factor: Decimal = None,
    ) -> None:
        """
        Initialize cost model.

        Args:
            fee_rate_pct: Taker fee rate as % of notional (default 0.1%)
            slippage_factor: Linear slippage factor (default 0.001)

        Note:
            spread_pct parameter REMOVED (T028): No synthetic spread allowed.
            Use calculate_costs_from_market_state() with observed spread instead.
        """
        self._fee_rate_pct = fee_rate_pct or self.DEFAULT_FEE_RATE_PCT
        self._slippage_factor = slippage_factor or self.DEFAULT_SLIPPAGE_FACTOR

    def calculate_costs(
        self,
        side: Side,
        size: Decimal,
        price: Decimal,
        avg_volume: Decimal = Decimal("1000"),
    ) -> CostBreakdown:
        """
        DEPRECATED (T028): No synthetic spread allowed.

        Use calculate_costs_from_market_state() with observed spread instead.

        This method is kept for backward compatibility but now raises an error
        to prevent synthetic spread usage.

        Raises:
            NotImplementedError: Always - use calculate_costs_from_market_state()
        """
        raise NotImplementedError(
            "calculate_costs() is DEPRECATED (T028: no synthetic spread). "
            "Use calculate_costs_from_market_state() with observed bid/ask spread instead."
        )

    def get_fill_price(
        self,
        side: Side,
        mid_price: Decimal,
        size: Decimal,
        avg_volume: Decimal = Decimal("1000"),
    ) -> Decimal:
        """
        DEPRECATED (T028): No synthetic spread allowed.

        Use calculate_costs_from_market_state() with observed spread instead.

        This method is kept for backward compatibility but now raises an error
        to prevent synthetic spread usage.

        Raises:
            NotImplementedError: Always - use calculate_costs_from_market_state()
        """
        raise NotImplementedError(
            "get_fill_price() is DEPRECATED (T028: no synthetic spread). "
            "Use calculate_costs_from_market_state() with observed bid/ask spread instead."
        )

    def calculate_costs_from_market_state(
        self,
        side: Side,
        size: Decimal,
        market_state: "MarketState",
        avg_volume: Decimal = Decimal("1000"),
    ) -> CostBreakdown:
        """
        Calculate trading costs using OBSERVED spread from MarketState.

        This is the PRIMARY method for Sprint 2 cost calculation.
        It uses the actual observed bid/ask spread from the market,
        NOT any synthetic/assumed/fallback spread.

        Args:
            side: Order side (BUY or SELL)
            size: Order size in base currency
            market_state: MarketState with observed bid/ask
            avg_volume: Average volume for slippage calculation (default 1000)

        Returns:
            CostBreakdown with all cost components

        Raises:
            ValueError: If spread is abnormal (>5% of mid price)

        Constitutional requirements:
            - FR-011: Spread cost computed from observed bid/ask
            - FR-015a: No synthetic spread anywhere
            - FR-015b: REJECT trade on abnormal spread (>5%)
        """
        # Calculate notional
        notional = size * market_state.mid_price

        # 1. Trading fees (taker fee for momentum strategy)
        fees = notional * (self._fee_rate_pct / Decimal("100"))

        # 2. Check for abnormal spread before calculating spread cost
        spread_pct = (market_state.spread / market_state.mid_price) * 100
        if spread_pct > 5:
            raise ValueError(
                f"ABNORMAL_SPREAD_REJECT: Spread {spread_pct:.2f}% exceeds 5% threshold. "
                f"Bid: {market_state.best_bid}, Ask: {market_state.best_ask}, "
                f"Spread: {market_state.spread}"
            )

        # 3. Spread cost using OBSERVED spread (not synthetic)
        # Buy at ask: pay (ask - mid) = half spread
        # Sell at bid: pay (mid - bid) = half spread
        spread_cost = (market_state.spread / Decimal("2")) * size

        # 4. Slippage (linear function of order size vs liquidity)
        volume_ratio = size / avg_volume if avg_volume > 0 else Decimal("0")
        slippage_cost = notional * self._slippage_factor * volume_ratio

        # Round to 2 decimal places
        fees_rounded = fees.quantize(Decimal("0.01"))
        spread_rounded = spread_cost.quantize(Decimal("0.01"))
        slippage_rounded = slippage_cost.quantize(Decimal("0.01"))

        # Calculate total from rounded components
        total_rounded = (fees_rounded + spread_rounded + slippage_rounded).quantize(Decimal("0.01"))

        return CostBreakdown(
            fees=fees_rounded,
            spread_cost=spread_rounded,
            slippage_cost=slippage_rounded,
            total_cost=total_rounded,
        )
