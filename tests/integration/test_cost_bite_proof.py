"""
Cost bite proof test (WO-008a-R4 §1.3, WO-008a-R6 §1.4).

This test proves that a filled order MUST have strictly positive total cost
and executed quantity > 0. If costs are zero, the test fails.

WO-008a-R6 UPDATE: Total cost now equals fees + slippage only (spread is
attribution, included in executed price, NOT additive).

FAIL-THEN-PASS proof pattern:
1. Run with correct implementation → PASS
2. Force cost to zero → FAIL (with assertion error)
3. Restore → PASS
4. Empty git diff

Constitutional requirements:
- Principle I: Truth Before Profit
- Principle V: No Backtest Without Costs
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, UTC
from trading.backtest.runner import BacktestRunner
from trading.data.market_state import MarketState
from trading.execution.paper import PaperExecutionClient


@pytest.mark.asyncio
async def test_filled_order_has_strictly_positive_costs():
    """
    FAIL-THEN-PASS proof: A filled order MUST have strictly positive costs.

    This test would FAIL if costs were silently set to zero.

    Evidence requirements:
    - PASTE PASS output with correct implementation
    - PASTE FAIL output when costs forced to zero (with assertion error)
    - PASTE PASS output after restore
    - PASTE empty git diff
    """
    # Create test data that WILL trigger trades
    test_data = []
    for i in range(10):
        # Large price swings to trigger strategy
        price_change = Decimal("0.02") if i % 2 == 0 else Decimal("-0.02")  # 2% swings
        base_price = Decimal("65000.00")
        new_price = base_price * (Decimal("1") + price_change)

        test_data.append(
            MarketState(
                timestamp=datetime(2024, 7, 11, 12, 0, i),
                symbol="BTC/USD",
                best_bid=new_price - Decimal("2.50"),
                best_ask=new_price + Decimal("2.50"),
                best_bid_size=Decimal("1.5"),
                best_ask_size=Decimal("2.0"),
                trade_count=100 + i,
                total_volume=Decimal(str(200 + i * 10)),
                last_price=new_price,
            )
        )

    runner = BacktestRunner()
    result = await runner.run(data_points=test_data, max_events=10)

    # VERIFY: Trades were executed
    assert result["trades_count"] > 0, "Should have executed trades"

    # VERIFY: P&L report has strictly positive costs
    pnl = result["pnl_report"]

    # STRICTLY POSITIVE TOTAL COST (Principle I & V)
    assert pnl["total_costs"] > 0, \
        f"Total cost MUST be strictly positive, got {pnl['total_costs']}"

    # STRICTLY POSITIVE COMPONENT COSTS
    assert pnl["total_fees"] > 0, \
        f"Fees MUST be strictly positive, got {pnl['total_fees']}"

    assert pnl["total_spread_cost"] > 0, \
        f"Spread cost MUST be strictly positive, got {pnl['total_spread_cost']}"

    assert pnl["total_slippage_cost"] > 0, \
        f"Slippage cost MUST be strictly positive, got {pnl['total_slippage_cost']}"

    # VERIFY: Cost components sum to total (WO-008a-R6: spread is attribution, NOT additive)
    # Total cost = fees + slippage only (spread is included in executed price)
    expected_total = pnl["total_fees"] + pnl["total_slippage_cost"]
    assert abs(pnl["total_costs"] - expected_total) < Decimal("0.0001"), \
        f"Total cost ({pnl['total_costs']}) MUST equal fees + slippage ({expected_total})"

    print(f"\n[COST BITE PROOF - PASS]")
    print(f"  Total Fees: ${pnl['total_fees']:.4f}")
    print(f"  Total Spread: ${pnl['total_spread_cost']:.4f} (attribution, included in executed price)")
    print(f"  Total Slippage: ${pnl['total_slippage_cost']:.4f}")
    print(f"  Total Cost: ${pnl['total_costs']:.4f} (fees + slippage only)")
    print(f"  All costs strictly positive [PASS]")


@pytest.mark.asyncio
async def test_zero_cost_path_is_detectable_behaviorally():
    """
    BEHAVIORAL bite (WO-012 §3, RULING 8 remediation — replaces a source grep).

    The prior test_cost_bite_bites_when_zero asserted, via inspect.getsource, that
    the SIBLING test contained the strings "> 0" and "assert". That proved a string
    was present in a file, not that costs are enforced positive (rule 0.1d / 0.1f:
    a textual check of a behavioral claim — the worst quadrant).

    This ATTEMPTS the forbidden state — a cost-free fill — by INJECTING a venue whose
    fill costs are zeroed (BacktestRunner accepts execution_client), and asserts the
    P&L report OBSERVES zero cost. Strictly stronger: a present-but-dead cost path
    (which the grep could not see) produces zero costs here and this test detects it.
    The positive-cost guarantee itself is proven by
    test_filled_order_has_strictly_positive_costs above.

    Injection is used rather than monkeypatching trading.execution.paper's module
    global: that global is resolved through a chain the suite's sys.modules churn can
    rebind (the same function-local/reload hazard documented in
    test_mainnet_guard.py::_live_settings), which made an earlier monkeypatch version
    order-dependent. Dependency injection is order-independent by construction.

    Principle V (No Backtest Without Costs); Principle I (Truth Before Profit).
    """
    import dataclasses

    class _ZeroCostVenue(PaperExecutionClient):
        """Test-only venue whose fills carry zero cost (defeats the cost mechanism)."""

        def _simulate_fill(self, symbol, side, size, price):
            fill = super()._simulate_fill(symbol, side, size, price)
            return dataclasses.replace(
                fill,
                fees=Decimal("0"),
                spread_cost=Decimal("0"),
                slippage_cost=Decimal("0"),
                total_cost=Decimal("0"),
            )

    test_data = []
    for i in range(10):
        price_change = Decimal("0.02") if i % 2 == 0 else Decimal("-0.02")
        new_price = Decimal("65000.00") * (Decimal("1") + price_change)
        test_data.append(
            MarketState(
                timestamp=datetime(2024, 7, 11, 12, 0, i),
                symbol="BTC/USD",
                best_bid=new_price - Decimal("2.50"),
                best_ask=new_price + Decimal("2.50"),
                best_bid_size=Decimal("1.5"),
                best_ask_size=Decimal("2.0"),
                trade_count=100 + i,
                total_volume=Decimal(str(200 + i * 10)),
                last_price=new_price,
            )
        )

    # Sanity: with the REAL mechanism, a fill incurs strictly positive cost.
    real = await BacktestRunner().run(data_points=test_data, max_events=10)
    assert real["trades_count"] > 0
    assert real["pnl_report"]["total_costs"] > 0

    # Defeat the cost mechanism by injecting a zero-cost venue (order-independent).
    defeated = await BacktestRunner(execution_client=_ZeroCostVenue()).run(
        data_points=test_data, max_events=10
    )
    assert defeated["trades_count"] > 0, "trades must still occur to make the bite meaningful"
    assert defeated["pnl_report"]["total_costs"] == 0, (
        "cost mechanism defeated but P&L still reported nonzero cost — a present-but-"
        "dead cost path would go undetected"
    )
    print("\n[BEHAVIORAL COST BITE] mechanism defeated -> total_costs == 0 (observed, not grepped)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
