"""
Staleness Guard Bite Proof — WO-008a-R6 §2.3

This test proves the staleness guard correctly prevents filling against:
1. No MarketState (set_market_state never called)
2. Stale MarketState (state older than threshold)

Both guards EXECUTE with real assertion output.

Constitutional Principles:
- VIII. Total Observability: No fabricated evidence in capture corpus
- WO-008a-R6: Staleness guard prevents fills against non-existent market data
"""

import pytest
import asyncio
from datetime import datetime, UTC, timedelta
from decimal import Decimal

from trading.execution.paper import PaperExecutionClient
from trading.data.market_state import MarketState


@pytest.mark.asyncio
async def test_no_market_state_guard():
    """
    BITE PROOF 1: No MarketState Guard

    Assert that place_order() RAISES when set_market_state() was never called.
    This prevents filling against a non-existent market (would be fabricated evidence).
    """
    venue = PaperExecutionClient()

    # Create a valid market state (but DON'T register it)
    market_state = MarketState(
        timestamp=datetime.now(UTC),
        symbol="BTC/USD",
        best_bid=Decimal("65975.0"),
        best_ask=Decimal("65980.0"),
        best_bid_size=Decimal("10.0"),
        best_ask_size=Decimal("10.0"),
        trade_count=1000,
        total_volume=Decimal("1000.0"),
        last_price=Decimal("65977.5"),
    )

    # Intentionally DON'T call venue.set_market_state(market_state)

    # Act & Assert: place_order() MUST RAISE with EXEC_NO_MARKET_STATE
    with pytest.raises(ValueError) as exc_info:
        await venue.place_order(
            symbol="BTC/USD",
            side="BUY",
            size=0.1,
            price=0.0,
            kill_switch_engaged=False,
        )

    # Assert the error message contains the correct reason code
    error_message = str(exc_info.value)
    # WO-008b-A3 §2: EXACT-code assertion, not a substring. A bare
    # `"EXEC_NO_MARKET_STATE" in msg` was satisfied by the ADJACENT guard's
    # message, so this test passed with its own guard disabled (rule 0.1d).
    # Anchoring on the trailing colon pins the code to itself.
    assert error_message.startswith("EXEC_NO_MARKET_STATE:"), (
        f"Error must raise reason code exactly 'EXEC_NO_MARKET_STATE'. "
        f"Got: {error_message}"
    )

    print(f"\n[NO-STATE GUARD - PASS]")
    print(f"  Error message: {error_message}")
    print(f"  Guard correctly prevents filling without market state")


@pytest.mark.asyncio
async def test_stale_market_state_guard():
    """
    BITE PROOF 2: Stale MarketState Guard

    Assert that place_order() RAISES when the MarketState is older than threshold.
    This prevents filling against stale data (feed stall or reconnect scenario).
    """
    venue = PaperExecutionClient(staleness_threshold_seconds=1.0)  # 1 second threshold for test

    # Create and register market state
    market_state = MarketState(
        timestamp=datetime.now(UTC),
        symbol="BTC/USD",
        best_bid=Decimal("65975.0"),
        best_ask=Decimal("65980.0"),
        best_bid_size=Decimal("10.0"),
        best_ask_size=Decimal("10.0"),
        trade_count=1000,
        total_volume=Decimal("1000.0"),
        last_price=Decimal("65977.5"),
    )

    venue.set_market_state(market_state)

    # Wait for state to become stale (beyond 1 second threshold)
    await asyncio.sleep(1.5)

    # Act & Assert: place_order() MUST RAISE with EXEC_STALE_MARKET_STATE
    with pytest.raises(ValueError) as exc_info:
        await venue.place_order(
            symbol="BTC/USD",
            side="BUY",
            size=0.1,
            price=0.0,
            kill_switch_engaged=False,
        )

    # Assert the error message contains the correct reason code
    error_message = str(exc_info.value)
    # WO-008b-A3 §2: EXACT-code assertion (see note above).
    assert error_message.startswith("EXEC_STALE_MARKET_STATE:"), (
        f"Error must raise reason code exactly 'EXEC_STALE_MARKET_STATE'. "
        f"Got: {error_message}"
    )

    print(f"\n[STALE-STATE GUARD - PASS]")
    print(f"  Error message: {error_message}")
    print(f"  Guard correctly prevents filling against stale data")


@pytest.mark.asyncio
async def test_fresh_market_state_accepted():
    """
    Verify that fresh MarketState (within threshold) is accepted.

    This proves the guard doesn't reject valid states.
    """
    venue = PaperExecutionClient(staleness_threshold_seconds=18.0)  # Default threshold

    # Create and register market state
    market_state = MarketState(
        timestamp=datetime.now(UTC),
        symbol="BTC/USD",
        best_bid=Decimal("65975.0"),
        best_ask=Decimal("65980.0"),
        best_bid_size=Decimal("10.0"),
        best_ask_size=Decimal("10.0"),
        trade_count=1000,
        total_volume=Decimal("1000.0"),
        last_price=Decimal("65977.5"),
    )

    venue.set_market_state(market_state)

    # Act: place_order() should succeed (state is fresh)
    fill_result = await venue.place_order(
        symbol="BTC/USD",
        side="BUY",
        size=0.1,
        price=0.0,
        kill_switch_engaged=False,
    )

    # Assert: Order filled successfully
    assert fill_result is not None
    assert fill_result["side"] == "BUY"
    assert fill_result["size"] == 0.1

    print(f"\n[FRESH STATE ACCEPTED - PASS]")
    print(f"  Executed Price: {fill_result['fill_price']}")
    print(f"  Total Cost: {fill_result['total_cost']}")
    print(f"  Fresh state correctly accepted")


if __name__ == "__main__":
    print("Running staleness guard bite proofs...")
    asyncio.run(test_no_market_state_guard())
    asyncio.run(test_stale_market_state_guard())
    asyncio.run(test_fresh_market_state_accepted())
    print("\n[BITE PROOFS COMPLETE]")
