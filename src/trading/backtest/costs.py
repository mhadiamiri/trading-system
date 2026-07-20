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

from trading.execution.costs import compute_execution_costs

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
    spread_cost: Decimal  # attribution of the executed price; NOT part of total
    slippage_cost: Decimal
    total_cost: Decimal  # fees + slippage_cost (WO-008a-R6, reaffirmed D11/D14)

    def __post_init__(self):
        """
        Validate cost breakdown against the RULED model.

        total_cost == fees + slippage_cost. Spread is ATTRIBUTION of the executed
        price (already embedded in it) and is never summed into the total
        (WO-008a-R6, reaffirmed D14; unified in WO-011 §1). This is not a weakened
        guard (rule 0.4): the invariant is corrected to the ruled definition the
        behavior already implements, not relaxed.
        """
        assert self.fees >= 0, "Fees cannot be negative"
        assert self.spread_cost >= 0, "Spread cost cannot be negative"
        assert self.slippage_cost >= 0, "Slippage cost cannot be negative"
        assert self.total_cost == self.fees + self.slippage_cost, \
            "Total cost must equal fees + slippage (spread is attribution, WO-008a-R6)"


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
    DEFAULT_FEE_RATE_PCT = Decimal("0.1")  # 0.1% taker fee per side (observed)
    # DEFAULT_SPREAD_PCT REMOVED (T028): No synthetic spread - use calculate_costs_from_market_state()
    DEFAULT_SLIPPAGE_FACTOR = Decimal("0.001")  # Linear slippage factor (ASSUMED CONSTANT - WO-008a-R5)

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

        WO-011 §1: this delegates to the SINGLE unified cost model
        (trading.execution.costs.compute_execution_costs) that the paper venue
        also calls. The former mid-price notional, volume-scaled slippage, and
        additive total lived here only; they are superseded by the ruled model
        (RULING 4/5/6). The discarded volume-scaling is preserved in
        docs/open-cleanup.md.

        Note:
            avg_volume is retained for signature compatibility (rule 0.1a). The
            ruled constant-slippage model (WO-008a-R5) does not use it.
        """
        costs = compute_execution_costs(
            side=side.value,
            size=size,
            market_state=market_state,
            fee_rate_pct=self._fee_rate_pct,
            slippage_factor=self._slippage_factor,
        )
        return CostBreakdown(
            fees=costs.fees,
            spread_cost=costs.spread_cost,
            slippage_cost=costs.slippage_cost,
            total_cost=costs.total_cost,
        )
