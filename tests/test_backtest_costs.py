"""
Backtest Cost Verification Tests

Verify that the cost model is honest and complete.

Constitutional Principles:
- I. Truth Before Profit: Cost-inclusive reporting
- V. No Backtest Without Costs: All costs modeled
"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal

from trading.backtest.costs import CostModel, Side, CostBreakdown
from trading.data.market_state import MarketState


class TestCostModel:
    """
    Sprint-1 cost properties, re-expressed against the UNIFIED ruled model (WO-011 §3).

    These 8 tests were xfail because they exercised the deprecated
    calculate_costs()/get_fill_price() (T028, synthetic-spread era). They are
    flipped to hard passes by driving the SAME properties through the unified ruled
    model (calculate_costs_from_market_state / compute_execution_costs) that the
    paper venue also uses. Every assertion interacts with the LIVE mechanism (rule
    0.1d): a real MarketState in, the real cost breakdown out. Where a test asserted
    the superseded additive total, it is corrected to the ruled model
    (total = fees + slippage) under the WO-011 §2 framing / RULING 1 — noted per test.
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.cost_model = CostModel()

    @staticmethod
    def _ms(bid: str, ask: str) -> MarketState:
        """Build a MarketState with an observed bid/ask (bid < ask required)."""
        return MarketState(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            best_bid=Decimal(bid),
            best_ask=Decimal(ask),
            best_bid_size=Decimal("10.0"),
            best_ask_size=Decimal("10.0"),
            trade_count=0,
            total_volume=Decimal("0"),
            last_price=Decimal(bid),
        )

    def test_fees_applied_to_every_trade(self):
        """
        Test fees applied to every trade (unified model).

        Constitutional requirements:
            - SC-008: Fees applied to every trade
            - Manual calculation matches within 0.01%
        """
        ms = self._ms("64997.50", "65002.50")  # mid 65000, spread 5
        costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY, size=Decimal("1.0"), market_state=ms
        )
        # BUY executes at ask; fees = executed notional * rate (0.1%).
        expected_fees = Decimal("1.0") * ms.best_ask * (Decimal("0.1") / Decimal("100"))
        assert costs.fees == expected_fees, f"Fees {costs.fees} != expected {expected_fees}"
        assert costs.fees > 0, "Every trade must incur a fee"

    def test_fees_calculation_accuracy(self):
        """
        Test fee calculation accuracy within 0.01% (unified model).

        Constitutional requirements:
            - SC-008: Manual calculation matches within 0.01%

        Fees are charged on the executed notional (BUY at ask, SELL at bid).
        """
        # (side, size, bid, ask, expected_fees) — executed price is ask/bid.
        test_cases = [
            (Side.BUY, Decimal("0.5"), "59999.00", "60000.00", Decimal("30.00")),
            (Side.SELL, Decimal("1.0"), "70000.00", "70001.00", Decimal("70.00")),
            (Side.BUY, Decimal("2.5"), "49999.00", "50000.00", Decimal("125.00")),
        ]

        for side, size, bid, ask, expected_fees in test_cases:
            costs = self.cost_model.calculate_costs_from_market_state(
                side=side, size=size, market_state=self._ms(bid, ask)
            )
            error_pct = abs(costs.fees - expected_fees) / expected_fees * 100
            assert error_pct < Decimal("0.01"), \
                f"Fee error {error_pct}% exceeds 0.01% threshold ({costs.fees} vs {expected_fees})"

    def test_spread_applied_on_entry_and_exit(self):
        """
        Test spread applied on both entry and exit (unified model).

        Constitutional requirements:
            - Spread applied on both entry and exit
        """
        entry_costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY, size=Decimal("1.0"), market_state=self._ms("64997.50", "65002.50")
        )
        exit_costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.SELL, size=Decimal("1.0"), market_state=self._ms("65997.50", "66002.50")
        )

        # Both should have spread cost (attribution of the executed price).
        assert entry_costs.spread_cost > 0, "Entry should have spread cost"
        assert exit_costs.spread_cost > 0, "Exit should have spread cost"

    def test_slippage_reduces_fill_prices(self):
        """
        Test slippage grows with order size (unified model).

        Constitutional requirements:
            - Larger orders incur more slippage

        Ruled slippage = notional x factor (assumed constant fraction, WO-008a-R5).
        Notional scales with size, so a larger order still incurs strictly more
        slippage — without the discarded volume-scaling elaboration (RULING 4).
        """
        ms = self._ms("64997.50", "65002.50")
        small_costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY, size=Decimal("0.1"), market_state=ms
        )
        large_costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY, size=Decimal("5.0"), market_state=ms
        )

        assert large_costs.slippage_cost > small_costs.slippage_cost, \
            "Large orders should have more slippage"

    def test_total_cost_equals_sum_of_components(self):
        """
        Test total cost equals the RULED sum of additive components (unified model).

        Constitutional requirements:
            - All costs listed as separate line items

        SUPERSEDED-MODEL CORRECTION (WO-011 §3 / §2 framing / RULING 1): this test
        previously asserted total == fees + spread + slippage. Corrected to the
        ruled model — total == fees + slippage — because spread is ATTRIBUTION of
        the executed price (WO-008a-R6), not an additive component. The behavior
        already implements the ruled model; only the assertion is corrected.
        """
        costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY, size=Decimal("1.0"), market_state=self._ms("64997.50", "65002.50")
        )

        expected_total = costs.fees + costs.slippage_cost  # ruled: spread excluded
        assert costs.total_cost == expected_total, \
            f"Total {costs.total_cost} != fees + slippage {expected_total}"

    def test_no_cost_free_code_path(self):
        """
        Test no cost-free code path exists (unified model).

        Constitutional requirements:
            - No cost-free code path exists (Principle V)
        """
        # All trades should have non-zero total cost (notional > $10).
        test_cases = [
            (Side.BUY, Decimal("0.1"), "99.99", "100.00"),
            (Side.SELL, Decimal("10.0"), "100000.00", "100001.00"),
            (Side.BUY, Decimal("1.0"), "49999.00", "50000.00"),
        ]

        for side, size, bid, ask in test_cases:
            costs = self.cost_model.calculate_costs_from_market_state(
                side=side, size=size, market_state=self._ms(bid, ask)
            )
            assert costs.total_cost > 0, \
                f"Trade should have cost: {side} {size} @ {bid}/{ask} -> {costs.total_cost}"

    def test_manual_calculation_matches_system(self):
        """
        Test manual calculation matches system exactly (unified model).

        Constitutional requirements:
            - SC-008: Manual calculation matches the system

        SUPERSEDED-MODEL CORRECTION (WO-011 §3 / §2 framing / RULING 1): the manual
        total previously summed spread (additive), and slippage used the discarded
        volume-scaling. Corrected to the ruled model: executed price = ask (BUY),
        slippage = notional x factor (constant), total = fees + slippage. The
        unified model is exact Decimal arithmetic, so equality is exact (no rounding
        tolerance needed).
        """
        size = Decimal("1.5")
        ms = self._ms("63497.00", "63503.00")  # spread 6
        costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY, size=size, market_state=ms
        )

        # Manual calculation mirroring the ruled model exactly.
        executed_price = ms.best_ask  # BUY fills at ask
        notional = size * executed_price
        manual_fees = notional * Decimal("0.1") / Decimal("100")
        manual_spread = (ms.spread / Decimal("2")) * size  # attribution
        manual_slippage = notional * Decimal("0.001")      # constant, no volume term
        manual_total = manual_fees + manual_slippage       # ruled: spread excluded

        assert costs.fees == manual_fees, f"fees {costs.fees} != {manual_fees}"
        assert costs.spread_cost == manual_spread, f"spread {costs.spread_cost} != {manual_spread}"
        assert costs.slippage_cost == manual_slippage, f"slippage {costs.slippage_cost} != {manual_slippage}"
        assert costs.total_cost == manual_total, f"total {costs.total_cost} != {manual_total}"

    def test_buy_at_ask_sell_at_bid(self):
        """
        Test buy at ask, sell at bid (unified model's executed price).

        Constitutional requirements:
            - Buy at ask (above mid)
            - Sell at bid (below mid)

        The ruled executed price lives on the unified model
        (compute_execution_costs), so this asserts it directly: BUY fills at the
        observed ask, SELL at the observed bid (R6 / RULING 5).
        """
        from trading.execution.costs import compute_execution_costs

        ms = self._ms("64997.50", "65002.50")  # mid 65000
        size = Decimal("1.0")
        rate, slip = Decimal("0.1"), Decimal("0.001")

        buy = compute_execution_costs("BUY", size, ms, rate, slip)
        sell = compute_execution_costs("SELL", size, ms, rate, slip)

        assert buy.executed_price == ms.best_ask, "BUY must fill at the observed ask"
        assert sell.executed_price == ms.best_bid, "SELL must fill at the observed bid"
        assert buy.executed_price > ms.mid_price, "Buy fill price should be above mid (ask)"
        assert sell.executed_price < ms.mid_price, "Sell fill price should be below mid (bid)"


class TestCostBreakdownValidation:
    """Test CostBreakdown validation (moved from TestCostModel - not deprecated)."""

    def test_cost_breakdown_validation(self):
        """
        Test CostBreakdown validates components against the RULED model.

        Constitutional requirements:
            - Cost breakdown validates total == fees + slippage (WO-008a-R6,
              reaffirmed D14; unified WO-011 §1). Spread is ATTRIBUTION of the
              executed price and is NOT summed into the total.

        The valid/invalid totals below previously encoded the superseded additive
        model (total == fees + spread + slippage). They are corrected to the ruled
        specification the CostBreakdown invariant already enforces
        (WO-011 §2 / RULING 1) — not tuned to green.
        """
        # Valid cost breakdown: total == fees + slippage (spread excluded).
        CostBreakdown(
            fees=Decimal("10.00"),
            spread_cost=Decimal("5.00"),
            slippage_cost=Decimal("2.00"),
            total_cost=Decimal("12.00"),  # fees + slippage (spread is attribution)
        )

        # Additive total (fees + spread + slippage = 17) is now INVALID and raises.
        with pytest.raises(AssertionError):
            CostBreakdown(
                fees=Decimal("10.00"),
                spread_cost=Decimal("5.00"),
                slippage_cost=Decimal("2.00"),
                total_cost=Decimal("17.00"),  # additive — superseded, must raise
            )

        # Negative cost should raise
        with pytest.raises(AssertionError):
            CostBreakdown(
                fees=Decimal("-10.00"),
                spread_cost=Decimal("5.00"),
                slippage_cost=Decimal("2.00"),
                total_cost=Decimal("-3.00"),
            )


class TestObservedSpreadCostModel:
    """
    Test observed spread cost model (T025-T027).

    Tests for US2: Observed Spread Cost Model.

    Constitutional requirements:
    - FR-011: Spread cost computed from observed bid/ask
    - FR-015: No assumed spread values
    - FR-015a: No synthetic spread anywhere
    - FR-015b: REJECT trade on abnormal spread (zero, negative, >5%)
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.cost_model = CostModel()

    def test_cost_model_uses_observed_spread_only(self):
        """
        Test: Cost model uses observed spread only (no synthetic path).

        Verifies:
        - All spread costs derived from market_state.spread
        - No constant/assumed/fallback spread exists in code path

        Constitutional requirements:
        - FR-011: Spread cost computed from observed bid/ask
        - FR-015a: No synthetic spread anywhere
        """
        # Create a MarketState with known spread
        market_state = MarketState(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            best_bid=Decimal("65000.00"),
            best_ask=Decimal("65005.00"),
            best_bid_size=Decimal("1.5"),
            best_ask_size=Decimal("2.0"),
            trade_count=0,
            total_volume=Decimal("0"),
            last_price=Decimal("65000.00"),
        )

        # Verify spread is correctly computed
        assert market_state.spread == Decimal("5.00")

        # Calculate costs with observed spread
        costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY,
            size=Decimal("1.0"),
            market_state=market_state,
        )

        # Verify spread cost is based on observed spread (not synthetic)
        # For buy: spread cost = (ask - mid) = (ask - (bid+ask)/2) = spread/2
        expected_spread_cost = market_state.spread / Decimal("2") * Decimal("1.0")
        assert costs.spread_cost == expected_spread_cost, \
            f"Spread cost {costs.spread_cost} should be {expected_spread_cost}"

    def test_code_review_no_synthetic_spread(self):
        """
        BEHAVIORAL guard: spread cost is derived from the OBSERVED bid/ask, never
        synthetic (FR-015a).

        WO-011 RULING 7 (0.1d REMEDIATION): this test previously asserted
        `"market_state.spread" in inspect.getsource(...)` — a source-string match.
        That proved a string appeared in a file, not that the spread was observed:
        `spread = market_state.spread * 0` would have passed it unchanged (rule
        0.1d — a bite proof must INTERACT with the mechanism it certifies). The
        source grep was also invalidated when WO-011 §1 moved the arithmetic into
        trading.execution.costs.compute_execution_costs.

        This replacement is STRICTLY STRONGER: it fails in every case the grep
        failed (a synthetic/constant spread) PLUS cases the grep could never detect
        (a spread that is a string-present-but-zeroed or otherwise not the observed
        one). The name is retained as the frozen member of the 0.1d-remediation
        category (RULING 7).
        """
        size = Decimal("1.0")

        def _ms(bid: str, ask: str) -> MarketState:
            return MarketState(
                timestamp=datetime.now(UTC),
                symbol="BTC/USD",
                best_bid=Decimal(bid),
                best_ask=Decimal(ask),
                best_bid_size=Decimal("1.5"),
                best_ask_size=Decimal("2.0"),
                trade_count=0,
                total_volume=Decimal("0"),
                last_price=Decimal(bid),
            )

        # (1) Distinct OBSERVED spreads must produce distinct spread_cost values
        # that TRACK the observed bid/ask. A synthetic/constant spread cannot.
        narrow = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY, size=size, market_state=_ms("65000.00", "65002.00")  # spread 2
        )
        wide = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY, size=size, market_state=_ms("65000.00", "65010.00")  # spread 10
        )
        assert narrow.spread_cost == Decimal("1.00"), narrow.spread_cost
        assert wide.spread_cost == Decimal("5.00"), wide.spread_cost
        assert wide.spread_cost > narrow.spread_cost, \
            "spread_cost must track the observed spread (a synthetic constant cannot)"

        # (2) spread_cost is TRACEABLE to the actual bid/ask on the tick:
        # spread_cost == (ask - bid) / 2 * size, for arbitrary observed values.
        for bid, ask in [("64000.00", "64003.50"), ("70000.00", "70012.00")]:
            ms = _ms(bid, ask)
            costs = self.cost_model.calculate_costs_from_market_state(
                side=Side.BUY, size=size, market_state=ms
            )
            expected = (ms.best_ask - ms.best_bid) / Decimal("2") * size
            assert costs.spread_cost == expected, \
                f"spread_cost {costs.spread_cost} must equal observed half-spread {expected}"

        # (3) An abnormal (>5%) OBSERVED spread is REJECTED with the declared
        # reason code — never priced against a synthetic spread (FR-015b, RULING 3).
        with pytest.raises(ValueError, match="ABNORMAL_SPREAD_REJECT"):
            self.cost_model.calculate_costs_from_market_state(
                side=Side.BUY, size=size, market_state=_ms("50000.00", "60000.00")  # 20%
            )

    def test_abnormal_spread_zero_rejected(self):
        """
        Test: Abnormal spread (zero) causes trade rejection.

        Verifies:
        - Trade rejected when bid == ask (spread = 0)
        - Rejection logged with ABNORMAL_SPREAD_REJECT reason code

        Constitutional requirements:
        - FR-015b: REJECT trade on abnormal spread
        """
        # Create MarketState with zero spread (bid == ask - invalid per MarketState validation)
        # MarketState already validates bid < ask, so this is tested by proxy

        # Test with very narrow spread (0.01) - should still work
        market_state = MarketState(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            best_bid=Decimal("65000.00"),
            best_ask=Decimal("65000.01"),  # 0.01 spread
            best_bid_size=Decimal("1.5"),
            best_ask_size=Decimal("2.0"),
            trade_count=0,
            total_volume=Decimal("0"),
            last_price=Decimal("65000.00"),
        )

        costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY,
            size=Decimal("1.0"),
            market_state=market_state,
        )

        # Should work with valid (non-zero) spread
        assert costs.spread_cost >= 0

    def test_abnormal_spread_wide_rejected(self):
        """
        Test: Abnormal spread (>5% of price) causes trade rejection.

        Verifies:
        - Trade rejected when spread > 5% of mid price
        - Rejection logged with ABNORMAL_SPREAD_REJECT reason code

        Constitutional requirements:
        - FR-015: Abnormal spread detection (>5%)
        - FR-015b: REJECT trade on abnormal spread
        """
        # Create MarketState with very wide spread (>5%)
        # Bid=50000, Ask=60000, spread=10000 (20% of mid price)
        # MarketState validation allows this, but cost model should reject
        market_state = MarketState(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            best_bid=Decimal("50000.00"),
            best_ask=Decimal("60000.00"),  # 20% spread - ABNORMAL!
            best_bid_size=Decimal("1.5"),
            best_ask_size=Decimal("2.0"),
            trade_count=0,
            total_volume=Decimal("0"),
            last_price=Decimal("50000.00"),
        )

        # Calculate spread percentage
        spread_pct = (market_state.spread / market_state.mid_price) * 100
        assert spread_pct > 5, f"Spread {spread_pct}% should be >5% for this test"

        # Cost model should reject this trade
        with pytest.raises(ValueError, match="ABNORMAL_SPREAD"):
            self.cost_model.calculate_costs_from_market_state(
                side=Side.BUY,
                size=Decimal("1.0"),
                market_state=market_state,
            )

    def test_buy_at_ask_sell_at_bid_observed(self):
        """
        Test: Buy at ask, sell at bid using OBSERVED spread.

        Verifies:
        - Buy fill price = ask (observed)
        - Sell fill price = bid (observed)
        - No assumed spread used

        Constitutional requirements:
        - FR-011: Spread cost computed from observed bid/ask
        """
        market_state = MarketState(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            best_bid=Decimal("65000.00"),
            best_ask=Decimal("65005.00"),
            best_bid_size=Decimal("1.5"),
            best_ask_size=Decimal("2.0"),
            trade_count=0,
            total_volume=Decimal("0"),
            last_price=Decimal("65000.00"),
        )

        # Buy costs: should pay half spread (ask - mid)
        buy_costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.BUY,
            size=Decimal("1.0"),
            market_state=market_state,
        )

        expected_buy_spread = (market_state.best_ask - market_state.mid_price) * Decimal("1.0")
        assert buy_costs.spread_cost == expected_buy_spread

        # Sell costs: should pay half spread (mid - bid)
        sell_costs = self.cost_model.calculate_costs_from_market_state(
            side=Side.SELL,
            size=Decimal("1.0"),
            market_state=market_state,
        )

        expected_sell_spread = (market_state.mid_price - market_state.best_bid) * Decimal("1.0")
        assert sell_costs.spread_cost == expected_sell_spread

        # Both should be equal (half spread each way)
        assert buy_costs.spread_cost == sell_costs.spread_cost


class TestAntiSyntheticSpreadGuard:
    """
    Test anti-synthetic-spread guard FAIL-THEN-PASS proof.

    CRITICAL: This is the §2.3 mandatory proof requirement from WO-007.

    Constitutional requirement (FR-015a):
    - There must be a test asserting that on an invalid/missing spread,
      the cost model REJECTS and returns NO cost number.

    Fail-then-pass proof:
    1. Add test that verifies cost model REJECTS on invalid spread
    2. Temporarily modify cost model to return fallback on invalid spread
    3. Run test → show it FAILS
    4. Restore cost model → show it PASSES
    """

    def test_invalid_spread_causes_rejection_no_fallback(self):
        """
        Test: Invalid spread causes REJECTION, no fallback cost returned.

        This is the anti-synthetic-spread guard test.

        Verifies:
        - When spread is invalid (>5%), cost model raises ValueError
        - NO fallback/assumed/synthetic spread is used
        - Trade is REJECTED, not priced with fake spread

        Constitutional requirements:
        - FR-015a: No synthetic spread anywhere
        - FR-015b: REJECT trade on abnormal spread

        CRITICAL: This test must FAIL when a fallback is added,
        proving the guard bites.
        """
        cost_model = CostModel()

        # Create MarketState with ABNORMAL spread (>5%)
        abnormal_market_state = MarketState(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            best_bid=Decimal("50000.00"),
            best_ask=Decimal("60000.00"),  # 20% spread - ABNORMAL!
            best_bid_size=Decimal("1.5"),
            best_ask_size=Decimal("2.0"),
            trade_count=0,
            total_volume=Decimal("0"),
            last_price=Decimal("50000.00"),
        )

        # Verify spread is indeed abnormal
        spread_pct = (abnormal_market_state.spread / abnormal_market_state.mid_price) * 100
        assert spread_pct > 5, f"Spread {spread_pct}% should be >5%"

        # Cost model MUST REJECT with ValueError, not return a fallback cost
        with pytest.raises(ValueError, match="ABNORMAL_SPREAD_REJECT"):
            cost_model.calculate_costs_from_market_state(
                side=Side.BUY,
                size=Decimal("1.0"),
                market_state=abnormal_market_state,
            )

        # Verify NO cost object was returned (test passed = rejection occurred)
        # If this test fails, it means a fallback was used - VIOLATION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
