"""
Kill switch: blocks NEW orders yet PRESERVES cancellation (Principle VI / FR-008).

WO-012b closes guard surface S13 — a PRESERVATION guarantee of the shape "even when
the kill switch is engaged, cancellation must STILL succeed." WO-012's §1
enumeration was refusal-shaped ("the system refuses X") and therefore structurally
could not see it (see docs/decisions/2026-07-19-guard-surfaces-and-denominators.md
entry 3).

The failure mode of a preservation guarantee is OVER-BLOCKING: a kill switch that
also froze cancellation would leave resting orders uncancellable during the exact
emergency the switch exists for — a worse operational state than the one it guards.
Blocking and preservation are ONE guarantee, certified together here.
"""

import pytest

from trading.execution.paper import PaperExecutionClient
from trading.execution.interface import KillSwitchEngagedError


@pytest.mark.asyncio
async def test_kill_switch_blocks_orders_but_preserves_cancellation():
    """
    Principle VI / FR-008: with the kill switch engaged, place_order is REFUSED
    AND cancel_order STILL SUCCEEDS — one paired guarantee, not two.
    """
    venue = PaperExecutionClient()

    # BLOCKING: a NEW order is refused while the kill switch is engaged.
    with pytest.raises(KillSwitchEngagedError):
        await venue.place_order(
            symbol="BTC/USD", side="BUY", size=1.0, price=0.0, kill_switch_engaged=True
        )

    # PRESERVATION: a resting order can STILL be cancelled while engaged. Over-
    # blocking here — refusing the cancel during the emergency — is the failure
    # mode that matters and is what the bite proof exercises.
    venue._orders["ord-1"] = {"symbol": "BTC/USD", "side": "BUY"}
    cancelled = await venue.cancel_order("ord-1", kill_switch_engaged=True)

    assert cancelled is True, (
        "cancellation MUST succeed even while the kill switch is engaged "
        "(Principle VI / FR-008); over-blocking strands resting orders in an emergency"
    )
    assert "ord-1" not in venue._orders, "the cancelled order must be removed"
