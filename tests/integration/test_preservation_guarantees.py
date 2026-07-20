"""
Preservation guarantees — the DUALS of refusal guards (WO-012c).

A refusal guard and its preservation dual FAIL IN OPPOSITE DIRECTIONS: a refusal
fails by PERMITTING (guard doesn't fire); a preservation fails by OVER-BLOCKING
(guard fires too broadly). Every prior bite proof on this project is refusal-shaped;
a system can pass all of them while being OVER-LOCKED. These tests certify the
preservation half of five refusal surfaces, each with BOTH assertions in one test
(the refusal AND its preservation are ONE guarantee — splitting them invites a
future where one is refactored away while the other still reads green).

The over-blocking bite proofs live in evidence/WO-012c/preservation_bite_proofs.txt.
Defeat mechanisms there perturb the guard toward over-firing (structural file
perturbation, sha256-restored), never a monkeypatch (WO-012b found those fragile
under sys.modules churn).
"""

import copy
from datetime import datetime, UTC, timedelta
from decimal import Decimal

import pytest

from trading.risk.engine import DeterministicRiskEngine
from trading.risk.position_state import PositionState
from trading.data.desired_position import DesiredPosition, Side
from trading.execution.paper import PaperExecutionClient
from trading.data.market_state import MarketState
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL


def _ms(bid: str, ask: str) -> MarketState:
    return MarketState(
        timestamp=datetime.now(UTC),
        symbol="BTC/USD",
        best_bid=Decimal(bid),
        best_ask=Decimal(ask),
        best_bid_size=Decimal("2.0"),
        best_ask_size=Decimal("2.0"),
        trade_count=0,
        total_volume=Decimal("0"),
        last_price=Decimal(bid),
    )


async def _place(venue) -> dict:
    return await venue.place_order(
        symbol="BTC/USD", side="BUY", size=1.0, price=0.0, kill_switch_engaged=False
    )


# ── S5: clamp shrinks, but must STILL PERMIT the reduced order ───────────────
def test_clamp_reduces_but_still_permits_the_order_not_veto_to_zero():
    """
    Principle VI: a clamp MAY only reduce size toward zero — and must STILL PERMIT
    the reduced order. Over-blocking (clamp -> veto/zero) silently converts "keep
    the strategy alive at safe size" into "kill it."
    """
    engine = DeterministicRiskEngine(max_position_btc=Decimal("0.5"))
    state = PositionState(
        symbol="BTC/USD", current_quantity=Decimal("0"),
        average_entry_price=Decimal("0"), unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"), daily_pnl=Decimal("0"),
    )
    desired = DesiredPosition(
        timestamp=datetime.now(UTC), symbol="BTC/USD", side=Side.BUY,
        quantity=Decimal("1.0"), feature_snapshot_hash="h",  # exceeds 0.5 limit
    )

    decision, order, reason = engine.check(desired, state, datetime.now(UTC))

    # REFUSAL half: the full size is NOT approved — it is clamped down.
    assert decision.value == "CLAMP"
    assert order.size < desired.quantity, "clamp must reduce the size"

    # PRESERVATION half: the reduced order is STILL PERMITTED — nonzero, not a veto.
    assert order is not None, "clamp must still PERMIT an order, never veto to None"
    assert order.size == Decimal("0.5"), "clamped size must be the max, not zero"
    assert order.size > 0, "over-blocking to zero turns every clamp into a veto"
    assert decision.value != "VETO"


# ── S6: stale MarketState refused, but a FRESH one must still fill ────────────
@pytest.mark.asyncio
async def test_stale_state_refused_but_fresh_state_still_fills():
    """
    WO-008a-R6 staleness guard: a stale MarketState is REFUSED, but a FRESH one must
    STILL price and fill. Over-blocking (window too broad) starves execution while
    reading as safety.
    """
    venue = PaperExecutionClient()
    ms = _ms("64997.50", "65002.50")

    # PRESERVATION half: a fresh state fills.
    venue.set_market_state(ms)  # timestamp = now
    fill = await _place(venue)
    assert Decimal(str(fill["fill_price"])) > 0, "a fresh MarketState must still fill"

    # REFUSAL half: a stale state is refused.
    venue._market_state_timestamp = datetime.now(UTC) - timedelta(hours=1)
    with pytest.raises(ValueError, match="EXEC_STALE_MARKET_STATE"):
        await _place(venue)


# ── S7: abnormal spread rejected, but a NORMAL spread must still price ────────
@pytest.mark.asyncio
async def test_abnormal_spread_rejected_but_normal_spread_still_prices():
    """
    FR-015b: an abnormal (>5%) spread is REJECTED, but a NORMAL spread must STILL
    price. Over-blocking (threshold too tight) rejects healthy markets.
    """
    venue = PaperExecutionClient()

    # PRESERVATION half: a normal spread prices.
    venue.set_market_state(_ms("64997.50", "65002.50"))  # ~0.008% spread
    fill = await _place(venue)
    assert Decimal(str(fill["fill_price"])) > 0, "a normal spread must still price"

    # REFUSAL half: an abnormal spread is rejected.
    venue.set_market_state(_ms("50000.00", "60000.00"))  # 20% spread
    with pytest.raises(ValueError, match="ABNORMAL_SPREAD_REJECT"):
        await _place(venue)


# ── S4: order-capable path unreachable when not paper, but paper must fill ────
@pytest.mark.asyncio
async def test_nonpaper_construction_refused_but_paper_still_fills():
    """
    Principle IX: the order-capable path is unreachable when NOT paper — but in
    paper mode it must STILL construct and fill. Over-blocking (guard refuses even
    in paper) makes paper trading impossible.
    """
    # PRESERVATION half: paper mode constructs and fills.
    venue = PaperExecutionClient()
    venue.set_market_state(_ms("64997.50", "65002.50"))
    fill = await _place(venue)
    assert Decimal(str(fill["fill_price"])) > 0, "paper execution must still fill"

    # REFUSAL half: a non-paper environment refuses construction. Settings is
    # resolved live (paper.py does a function-local import) and patched, so this is
    # order-independent — no stale module object (WO-008b-A1 _live_settings pattern).
    import config.settings
    from unittest.mock import patch as _patch

    live = config.settings.Settings
    with _patch.object(live, "TRADING_ENV", "mainnet"), \
         _patch.object(live, "is_paper_trading", staticmethod(lambda: False)):
        with pytest.raises(ValueError, match="CANNOT be used"):
            PaperExecutionClient()


# ── S10: no emit while unverified, but emission MUST RESUME after resync ──────
@pytest.mark.asyncio
async def test_resync_blocks_emission_then_resumes_after_fresh_snapshot():
    """
    FR-018a(d): while the book is unverified NO MarketState is emitted — but once a
    fresh snapshot validates, emission MUST RESUME. A latched `awaiting_resync`
    emits nothing forever while reading as safety (the over-blocking failure mode).
    """
    adapter = KrakenV2BookAdapter()

    # A validated snapshot emits (baseline).
    assert len(await adapter.process_raw_frame(SNAPSHOT_FRAME)) == 1

    # REFUSAL half: a corrupted update opens the no-emission window; nothing emits.
    corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
    corrupted["data"][0]["bids"][0]["price"] = "45283.7"
    assert await adapter.process_raw_frame(corrupted) == [], "unverified book must not emit"
    assert adapter._awaiting_resync is True
    # An incremental during the window is refused outright.
    assert await adapter.process_raw_frame(copy.deepcopy(UPDATE_MODIFY_LEVEL)) == []

    # PRESERVATION half: a fresh valid snapshot RESUMES emission.
    assert len(await adapter.process_raw_frame(SNAPSHOT_FRAME)) == 1
    assert adapter._awaiting_resync is False, "emission must resume after resync validates"
    # Incrementals emit again — the window is truly closed, not just the snapshot.
    assert len(await adapter.process_raw_frame(copy.deepcopy(UPDATE_MODIFY_LEVEL))) == 1, (
        "a latched awaiting_resync would emit nothing forever while reading as safety"
    )
