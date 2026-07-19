"""
Frozen invariant bite proof test (WO-008a-R5 §2.3).

This test proves that PositionState is genuinely immutable (frozen=True)
and that attempts to mutate it raise FrozenInstanceError.
"""
import pytest
from decimal import Decimal
from datetime import datetime, UTC
from trading.risk.position_state import PositionState
from dataclasses import FrozenInstanceError


def test_position_state_is_frozen():
    """
    Test that PositionState is frozen and rejects in-place mutation.

    This test enforces the frozen invariant. If someone removes frozen=True,
    this test will pass when it should fail.
    """
    # Create a PositionState
    state = PositionState(
        symbol="BTC/USD",
        current_quantity=Decimal("1.0"),
        average_entry_price=Decimal("65000.00"),
        unrealized_pnl=Decimal("100.00"),
        realized_pnl=Decimal("50.00"),
        daily_pnl=Decimal("150.00"),
    )

    # Attempt to mutate in-place - SHOULD RAISE FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        state.current_quantity = Decimal("2.0")

    # Attempt another mutation - SHOULD RAISE FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        state.realized_pnl = Decimal("200.00")

    print(f"\n[FROZEN INVARIANT PROOF - PASS]")
    print(f"  PositionState is frozen and rejects in-place mutation")
    print(f"  state.current_quantity = {state.current_quantity} (unchanged)")
    print(f"  state.realized_pnl = {state.realized_pnl} (unchanged)")


def test_position_state_immutability_with_replace():
    """
    Test that PositionState can be updated using dataclasses.replace().

    This is the CORRECT way to update frozen dataclasses.
    """
    import dataclasses

    # Create a PositionState
    state = PositionState(
        symbol="BTC/USD",
        current_quantity=Decimal("1.0"),
        average_entry_price=Decimal("65000.00"),
        unrealized_pnl=Decimal("100.00"),
        realized_pnl=Decimal("50.00"),
        daily_pnl=Decimal("150.00"),
    )

    # Update using dataclasses.replace() - SHOULD SUCCEED
    new_state = dataclasses.replace(
        state,
        current_quantity=Decimal("2.0"),
        realized_pnl=Decimal("200.00"),
    )

    # Original state unchanged
    assert state.current_quantity == Decimal("1.0")
    assert state.realized_pnl == Decimal("50.00")

    # New state has updated values
    assert new_state.current_quantity == Decimal("2.0")
    assert new_state.realized_pnl == Decimal("200.00")

    print(f"\n[IMMUTABLE UPDATE - PASS]")
    print(f"  dataclasses.replace() correctly creates new instance")
    print(f"  Original state unchanged: quantity={state.current_quantity}")
    print(f"  New state updated: quantity={new_state.current_quantity}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
