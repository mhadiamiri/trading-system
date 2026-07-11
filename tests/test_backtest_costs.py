"""
Backtest Cost Verification Tests

Verify that the cost model is honest and complete.

Constitutional Principles:
- I. Truth Before Profit: Cost-inclusive reporting
- V. No Backtest Without Costs: All costs modeled
"""

import pytest
from datetime import datetime
from decimal import Decimal

from trading.backtest.costs import CostModel, Side, CostBreakdown


class TestCostModel:
    """Test suite for cost model."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cost_model = CostModel()

    def test_fees_applied_to_every_trade(self):
        """
        Test fees applied to every trade.

        Constitutional requirements:
            - SC-008: Fees applied to every trade
            - Manual calculation matches within 0.01%
        """
        # Buy order
        costs = self.cost_model.calculate_costs(
            side=Side.BUY,
            size=Decimal("1.0"),
            price=Decimal("65000.00"),
        )

        # Manual calculation: 65000 * 0.1% = 65.00
        expected_fees = Decimal("65000.00") * Decimal("0.1") / Decimal("100")
        assert abs(costs.fees - expected_fees) < Decimal("0.01"), \
            f"Fees {costs.fees} != expected {expected_fees}"

    def test_fees_calculation_accuracy(self):
        """
        Test fee calculation accuracy within 0.01%.

        Constitutional requirements:
            - SC-008: Manual calculation matches within 0.01%
        """
        test_cases = [
            (Side.BUY, Decimal("0.5"), Decimal("60000.00"), Decimal("30.00")),
            (Side.SELL, Decimal("1.0"), Decimal("70000.00"), Decimal("70.00")),
            (Side.BUY, Decimal("2.5"), Decimal("50000.00"), Decimal("125.00")),
        ]

        for side, size, price, expected_fees in test_cases:
            costs = self.cost_model.calculate_costs(side, size, price)
            error_pct = abs(costs.fees - expected_fees) / expected_fees * 100
            assert error_pct < Decimal("0.01"), \
                f"Fee error {error_pct}% exceeds 0.01% threshold"

    def test_spread_applied_on_entry_and_exit(self):
        """
        Test spread applied on both entry and exit.

        Constitutional requirements:
            - Spread applied on both entry and exit
        """
        # Entry (buy)
        entry_costs = self.cost_model.calculate_costs(
            side=Side.BUY,
            size=Decimal("1.0"),
            price=Decimal("65000.00"),
        )

        # Exit (sell)
        exit_costs = self.cost_model.calculate_costs(
            side=Side.SELL,
            size=Decimal("1.0"),
            price=Decimal("66000.00"),
        )

        # Both should have spread cost
        assert entry_costs.spread_cost > 0, "Entry should have spread cost"
        assert exit_costs.spread_cost > 0, "Exit should have spread cost"

    def test_slippage_reduces_fill_prices(self):
        """
        Test slippage reduces fill prices.

        Constitutional requirements:
            - Slippage reduces fill prices
        """
        # Small order (low slippage)
        small_costs = self.cost_model.calculate_costs(
            side=Side.BUY,
            size=Decimal("0.1"),
            price=Decimal("65000.00"),
            avg_volume=Decimal("1000"),
        )

        # Large order (high slippage)
        large_costs = self.cost_model.calculate_costs(
            side=Side.BUY,
            size=Decimal("5.0"),
            price=Decimal("65000.00"),
            avg_volume=Decimal("1000"),
        )

        # Large order should have more slippage
        assert large_costs.slippage_cost > small_costs.slippage_cost, \
            "Large orders should have more slippage"

    def test_total_cost_equals_sum_of_components(self):
        """
        Test total cost equals sum of components.

        Constitutional requirements:
            - All costs listed as separate line items
        """
        costs = self.cost_model.calculate_costs(
            side=Side.BUY,
            size=Decimal("1.0"),
            price=Decimal("65000.00"),
        )

        expected_total = costs.fees + costs.spread_cost + costs.slippage_cost
        assert costs.total_cost == expected_total, \
            f"Total {costs.total_cost} != sum of components {expected_total}"

    def test_no_cost_free_code_path(self):
        """
        Test no cost-free code path exists.

        Constitutional requirements:
            - No cost-free code path exists (Principle V)
        """
        # All trades should have non-zero total cost
        # Use trade sizes that will definitely incur costs (notional > $10)
        test_cases = [
            (Side.BUY, Decimal("0.1"), Decimal("100.00")),  # $10 notional
            (Side.SELL, Decimal("10.0"), Decimal("100000.00")),
            (Side.BUY, Decimal("1.0"), Decimal("50000.00")),
        ]

        for side, size, price in test_cases:
            costs = self.cost_model.calculate_costs(side, size, price)
            assert costs.total_cost > 0, f"Trade should have cost: {side} {size} @ {price}"

    def test_manual_calculation_matches_system(self):
        """
        Test manual calculation matches system within 0.01%.

        Constitutional requirements:
            - SC-008: Manual calculation matches within 0.01%
        """
        # Sample trade (large enough to have meaningful costs)
        size = Decimal("1.5")
        price = Decimal("63500.00")
        side = Side.BUY

        # System calculation
        costs = self.cost_model.calculate_costs(side, size, price)

        # Manual calculation (same as system)
        notional = size * price
        manual_fees = notional * Decimal("0.1") / Decimal("100")
        manual_spread = notional * Decimal("0.01") / Decimal("100")
        manual_slippage = notional * Decimal("0.001") * (size / Decimal("1000"))

        # Round to 2 decimal places to match system
        manual_fees = manual_fees.quantize(Decimal("0.01"))
        manual_spread = manual_spread.quantize(Decimal("0.01"))
        manual_slippage = manual_slippage.quantize(Decimal("0.01"))
        manual_total = (manual_fees + manual_spread + manual_slippage).quantize(Decimal("0.01"))

        # Verify each component within reasonable tolerance (accounting for rounding)
        for component, manual_value in [
            ("fees", manual_fees),
            ("spread_cost", manual_spread),
            ("slippage_cost", manual_slippage),
            ("total_cost", manual_total),
        ]:
            system_value = getattr(costs, component)
            # Allow small rounding difference (at most 0.01)
            assert abs(system_value - manual_value) <= Decimal("0.01"), \
                f"{component}: system={system_value}, manual={manual_value}"

    def test_buy_at_ask_sell_at_bid(self):
        """
        Test buy at ask, sell at bid.

        Constitutional requirements:
            - Buy at ask (mid + spread/2)
            - Sell at bid (mid - spread/2)
        """
        mid_price = Decimal("65000.00")
        size = Decimal("1.0")

        # Buy fill price should be higher than mid
        buy_fill_price = self.cost_model.get_fill_price(
            side=Side.BUY,
            mid_price=mid_price,
            size=size,
        )
        assert buy_fill_price > mid_price, "Buy fill price should be above mid (ask)"

        # Sell fill price should be lower than mid
        sell_fill_price = self.cost_model.get_fill_price(
            side=Side.SELL,
            mid_price=mid_price,
            size=size,
        )
        assert sell_fill_price < mid_price, "Sell fill price should be below mid (bid)"

    def test_cost_breakdown_validation(self):
        """
        Test CostBreakdown validates components.

        Constitutional requirements:
            - Cost breakdown validates total equals sum
        """
        # Valid cost breakdown
        CostBreakdown(
            fees=Decimal("10.00"),
            spread_cost=Decimal("5.00"),
            slippage_cost=Decimal("2.00"),
            total_cost=Decimal("17.00"),
        )

        # Invalid total should raise
        with pytest.raises(AssertionError):
            CostBreakdown(
                fees=Decimal("10.00"),
                spread_cost=Decimal("5.00"),
                slippage_cost=Decimal("2.00"),
                total_cost=Decimal("20.00"),  # Wrong total
            )

        # Negative cost should raise
        with pytest.raises(AssertionError):
            CostBreakdown(
                fees=Decimal("-10.00"),
                spread_cost=Decimal("5.00"),
                slippage_cost=Decimal("2.00"),
                total_cost=Decimal("-3.00"),
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
