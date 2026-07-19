"""
Bite Proof Test — WO-008a-R6 §1.4: No Double-Count of Spread Cost

This test proves that spread cost is NOT double-counted in the total economic cost
of a trade. Spread is an ATTRIBUTION of the executed price (which already includes
the spread crossing cost), NOT an additive cost component.

Constitutional Principles:
- I. Truth Before Profit: Cost model must be accurate, not overstated
- WO-008a-R6: Spread double-count is a blocker that creates untrustworthy economics
"""

import pytest
from decimal import Decimal
from datetime import datetime, UTC

from trading.execution.paper import PaperExecutionClient
from trading.data.market_state import MarketState


# Async test wrapper
@pytest.mark.asyncio
async def test_no_spread_double_count_in_total_cost():
    """Async wrapper for the bite proof test."""
    # Arrange: Create paper venue
    venue = PaperExecutionClient()

    # Market state with known bid/ask spread
    market_state = MarketState(
        timestamp=datetime.now(UTC),
        symbol="BTC/USD",
        best_bid=Decimal("65975.0"),  # Bid
        best_ask=Decimal("65980.0"),  # Ask (spread = 5.0)
        best_bid_size=Decimal("10.0"),
        best_ask_size=Decimal("10.0"),
        trade_count=1000,
        total_volume=Decimal("1000.0"),
        last_price=Decimal("65977.5"),
    )

    # Register market state (WO-008a-R5 pattern)
    venue.set_market_state(market_state)

    # Act: Simulate a BUY order
    fill_result = await venue.place_order(
        symbol="BTC/USD",
        side="BUY",
        size=0.1,
        price=0.0,  # Market order
        kill_switch_engaged=False,
    )

    # Extract cost components
    fees = Decimal(str(fill_result["fees"]))
    spread_cost = Decimal(str(fill_result["spread_cost"]))
    slippage_cost = Decimal(str(fill_result["slippage_cost"]))
    total_cost = Decimal(str(fill_result["total_cost"]))

    # Calculate expected total_cost (fees + slippage only, NO spread)
    expected_total = fees + slippage_cost

    # Assert: total_cost MUST equal fees + slippage only
    # If spread is incorrectly included, this assertion will FAIL
    assert total_cost == expected_total, (
        f"Total cost MUST NOT double-count spread! "
        f"Expected {expected_total} (fees + slippage only), "
        f"got {total_cost}. "
        f"Components: fees={fees}, spread_cost={spread_cost}, slippage={slippage_cost}"
    )

    # Assert: spread_cost is still reported for transparency
    assert spread_cost > 0, "Spread cost MUST be reported (as attribution)"

    # Verify the arithmetic: executed price already includes spread
    executed_price = Decimal(str(fill_result["fill_price"]))
    size = Decimal(str(fill_result["size"]))

    # BUY should execute at ask (65980.0)
    assert executed_price == Decimal("65980.0"), "BUY should execute at ask"

    # Spread cost should be half-spread × size
    expected_spread = (Decimal("65980.0") - Decimal("65975.0")) / 2 * size
    assert spread_cost == expected_spread, f"Spread cost should be {expected_spread}"

    # Print for evidence
    print(f"\n[DOUBLE-COUNT CHECK - PASS]")
    print(f"  Executed Price: {executed_price} (includes spread)")
    print(f"  Size: {size}")
    print(f"  Fees (additive): ${fees}")
    print(f"  Spread (attribution only): ${spread_cost} (half-spread × size)")
    print(f"  Slippage (additive): ${slippage_cost}")
    print(f"  Total Cost (fees + slippage): ${total_cost}")
    print(f"  Expected Total: ${expected_total}")
    print(f"  Match: PASS (total_cost == fees + slippage only, spread NOT counted twice)")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_no_spread_double_count_in_total_cost())
    print("\n[BITE PROOF COMPLETE - NO DOUBLE-COUNT]")
