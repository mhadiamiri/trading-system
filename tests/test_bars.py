"""
WO-053 §3.1/§3.2 — THE BAR LAYER and the bar-granularity U4.

§0.10 — every test here is single-purpose so a mutation can attribute its failure.
§0.12 — the containment tests assert a REFUSAL, which is an observation that can fail: the
falsifier for "a bar never spans a gap" is a bar that spans one, and `test_bite_*` constructs
exactly that situation and requires the refusal.
"""

from datetime import datetime, timedelta, UTC
from decimal import Decimal

import pytest

from trading.data.bars import Bar, BarError, SegmentBarBuilder
from trading.data.book_state import BookState
from trading.data.corpus_reader import Segment
from trading.strategy.bar_momentum import (
    ROUND_TRIP_COST_PCT, BarMomentumOverFrames, BarMomentumStrategy,
)

T0 = datetime(2026, 8, 5, 22, 0, 0, tzinfo=UTC)


def _seg(start_offset=0, seconds=600, run_id="20260805220327"):
    return Segment(
        start_utc=T0 + timedelta(seconds=start_offset),
        end_utc=T0 + timedelta(seconds=start_offset + seconds),
        run_id=run_id,
    )


def _frame(offset_seconds, mid="64000"):
    """A BookState at T0+offset with the given mid (bid/ask straddle it by 0.5)."""
    m = Decimal(mid)
    return BookState(
        timestamp=T0 + timedelta(seconds=offset_seconds), symbol="BTC/USD",
        best_bid=m - Decimal("0.5"), best_ask=m + Decimal("0.5"),
        best_bid_size=Decimal("1"), best_ask_size=Decimal("1"),
    )


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §3.1 BITE — A BAR NEVER SPANS A GAP
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_bite_a_frame_from_outside_the_segment_is_refused():
    """THE BITE. A builder owns ONE segment. Offered a frame from beyond it — the far side of a
    discontinuity the reader deliberately segmented at — it must REFUSE, not bucket it."""
    b = SegmentBarBuilder(0, _seg(seconds=300), 60)
    b.add(_frame(0))
    with pytest.raises(BarError, match="BAR_FRAME_OUTSIDE_SEGMENT"):
        b.add(_frame(7200))          # two hours later: the far side of the 2.1h seam


def test_bite_a_frame_before_the_segment_start_is_refused():
    """Symmetry: the guard covers the lower bound too. A one-sided bounds check would let a bar
    absorb frames from the PREVIOUS segment, which is the same splice in the other direction."""
    b = SegmentBarBuilder(0, _seg(start_offset=600, seconds=300), 60)
    with pytest.raises(BarError, match="BAR_FRAME_OUTSIDE_SEGMENT"):
        b.add(_frame(0))


def test_dual_a_bar_entirely_inside_a_segment_builds_normally():
    """THE PRESERVATION DUAL (§0.4), local and direct. The guard must refuse foreign frames
    WITHOUT refusing legitimate ones — a builder that rejected everything would pass the bite and
    be useless."""
    b = SegmentBarBuilder(0, _seg(seconds=300), 60)
    emitted = [bar for i in range(0, 180, 10) if (bar := b.add(_frame(i))) is not None]
    assert len(emitted) == 2, "180s of frames at 60s bars closes bars 0 and 1"
    assert all(isinstance(x, Bar) for x in emitted)
    assert emitted[0].frame_count == 6, "six 10s frames land in the first 60s bucket"


def test_dual_every_frame_of_a_full_segment_is_accepted():
    """The dual again, at the boundary values themselves: the first and last instants of a segment
    are INSIDE it (inclusive bounds, matching the reader and the frame loader)."""
    seg = _seg(seconds=300)
    b = SegmentBarBuilder(0, seg, 60)
    b.add(_frame(0))                                    # exactly start_utc
    b.add(_frame(300))                                  # exactly end_utc
    assert b.bars_emitted >= 1


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.2 REGISTERED BAR RULES
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_partial_trailing_bar_is_discarded_never_emitted():
    """§2.2 registered: an incomplete bar is never reported as complete. 90s of frames at 60s bars
    yields ONE bar; the trailing 30s bucket is dropped and COUNTED."""
    b = SegmentBarBuilder(0, _seg(seconds=300), 60)
    emitted = [bar for i in range(0, 91, 10) if (bar := b.add(_frame(i))) is not None]
    assert len(emitted) == 1
    b.finish()
    assert b.discarded_partial_bars == 1
    assert b.discarded_partial_frames > 0, "the discard is counted, not silently swallowed"


def test_bars_are_aligned_to_the_segment_not_the_wall_clock_epoch():
    """§2.2: alignment is segment-relative, which is what makes a gap-spanning bucket
    unrepresentable. A segment whose first frame is at :37 starts bar 0 at :37, not at :00."""
    b = SegmentBarBuilder(0, _seg(start_offset=37, seconds=300), 60)
    b.add(_frame(37))
    bar = None
    for i in range(38, 130):
        bar = b.add(_frame(i)) or bar
    assert bar is not None
    assert bar.start_utc == T0 + timedelta(seconds=37), "bar 0 anchors on the segment's own start"


def test_bar_ohlc_reflects_the_frames_it_contains():
    """The bar is a real summary of its frames, not a copy of one of them."""
    b = SegmentBarBuilder(0, _seg(seconds=300), 60)
    for i, mid in ((0, "64000"), (10, "64500"), (20, "63900"), (30, "64100")):
        b.add(_frame(i, mid))
    bar = b.add(_frame(70, "64200"))       # closes bucket 0
    assert bar.open == Decimal("64000") and bar.close == Decimal("64100")
    assert bar.high == Decimal("64500") and bar.low == Decimal("63900")


def test_a_bar_carries_a_provenance_hash_of_itself():
    """Principle VIII: a bar-based decision must identify the BAR it acted on."""
    b = SegmentBarBuilder(0, _seg(seconds=300), 60)
    b.add(_frame(0, "64000"))
    bar1 = b.add(_frame(70, "64100"))
    b2 = SegmentBarBuilder(0, _seg(seconds=300), 60)
    b2.add(_frame(0, "64000"))
    bar2 = b2.add(_frame(70, "64100"))
    assert bar1.compute_snapshot_hash() == bar2.compute_snapshot_hash()
    assert len(bar1.compute_snapshot_hash()) == 64


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.3 THE REGISTERED PARAMETERS — pinned to their derivation
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_threshold_is_the_registered_multiple_of_the_round_trip_cost():
    """§2.3: T is DERIVED, not typed. If someone edits the threshold without changing the cost
    arithmetic, or vice versa, this fails."""
    assert ROUND_TRIP_COST_PCT == Decimal("1.6216"), "2x0.80 fee + 2x0.01 slip + 0.0016 spread"
    assert BarMomentumStrategy.THRESHOLD_PCT == ROUND_TRIP_COST_PCT * Decimal("2.0")
    assert BarMomentumStrategy.THRESHOLD_PCT == Decimal("3.24320")


def test_registered_parameters_are_exactly_as_pre_registered():
    """The parameter table from `evidence/WO-053/PRE_REGISTRATION.md` (commit e7b33c8), pinned."""
    assert BarMomentumStrategy.BAR_INTERVAL_SECONDS == 60
    assert BarMomentumStrategy.MOMENTUM_BARS == 5
    assert BarMomentumStrategy.ORDER_SIZE_BTC == Decimal("0.1")


def test_the_fee_half_of_the_cost_bar_matches_the_cited_schedule():
    """The round-trip bar must track the CITED fee, not a literal that happens to equal it today."""
    from trading.execution import fee_schedule
    from trading.strategy.bar_momentum import ROUND_TRIP_FEE_PCT
    assert ROUND_TRIP_FEE_PCT == fee_schedule.taker_pct() * 2


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE SIGNAL
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _bar(idx, close):
    return Bar(segment_index=0, bar_index=idx, start_utc=T0 + timedelta(minutes=idx),
               end_utc=T0 + timedelta(minutes=idx + 1), open=Decimal(close), high=Decimal(close),
               low=Decimal(close), close=Decimal(close), frame_count=100)


def test_under_warm_is_flat_not_a_signal_on_partial_history():
    """A 2-bar return is not the registered 5-bar signal. Acting on it would silently change the
    strategy near every segment boundary."""
    s = BarMomentumStrategy()
    for i, px in enumerate(["60000", "62000", "64000", "66000", "68000"]):
        assert s.observe_bar(_bar(i, px), "BTC/USD") is None, "not yet warm — 5 closes < N+1"
    assert not s.warm


def test_a_move_above_the_threshold_fires_in_its_direction():
    """The economic effect: a +5% 5-bar move clears the registered 3.2432% bar and buys."""
    s = BarMomentumStrategy()
    closes = ["60000", "60000", "60000", "60000", "60000", "63000"]   # +5% over 5 bars
    out = [s.observe_bar(_bar(i, px), "BTC/USD") for i, px in enumerate(closes)]
    assert out[-1] is not None and out[-1].side.value == "BUY"
    assert out[-1].quantity == Decimal("0.1")


def test_a_move_below_the_threshold_does_not_fire():
    """THE DUAL for the signal: a 1% move — real, but under the cost bar — must NOT trade. This is
    the whole registered thesis: moves that do not clear cost are not opportunities."""
    s = BarMomentumStrategy()
    closes = ["60000", "60000", "60000", "60000", "60000", "60600"]   # +1%, under 3.2432%
    out = [s.observe_bar(_bar(i, px), "BTC/USD") for i, px in enumerate(closes)]
    assert out[-1] is None


def test_a_downward_move_above_the_threshold_sells():
    s = BarMomentumStrategy()
    closes = ["60000", "60000", "60000", "60000", "60000", "57000"]   # −5%
    out = [s.observe_bar(_bar(i, px), "BTC/USD") for i, px in enumerate(closes)]
    assert out[-1] is not None and out[-1].side.value == "SELL"


def test_the_decision_is_stamped_in_market_time_at_the_bar_close():
    """D-a: market time, never now()."""
    s = BarMomentumStrategy()
    closes = ["60000", "60000", "60000", "60000", "60000", "63000"]
    out = [s.observe_bar(_bar(i, px), "BTC/USD") for i, px in enumerate(closes)]
    assert out[-1].timestamp == _bar(5, "63000").end_utc


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §3.2 — U4 AT BAR GRANULARITY
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_u4_the_first_closed_bar_of_a_segment_cannot_trade():
    """§3.2 — U4's analog at bar granularity, asserted EXPLICITLY rather than left incidental.

    The runner's frame-level U4 skips frame 0, which under a 60-second bar is one of ~1,500 frames
    inside bar 0 and suppresses nothing about bar 0's tradeability. So the adapter suppresses the
    first CLOSED BAR itself.

    The suppression is proved by forcing the only condition under which it could matter: a strategy
    that is already warm when its first bar closes. A real segment cannot reach that state, which
    is exactly why asserting it matters — a protection satisfied only incidentally is the
    incidental-coverage defect (D51) and would break silently the moment N changed.
    """
    adapter = BarMomentumOverFrames(segment_index=0, segment=_seg(seconds=600))
    adapter._inner._closes = [Decimal("60000")] * (BarMomentumStrategy.MOMENTUM_BARS + 1)
    assert adapter._inner.warm, "precondition: warm before the first bar closes"

    # Bucket 0 ends on 66000, so bar 0's CLOSE is +10% against the preloaded history — far above
    # the threshold. Note the frame that *triggers* the close belongs to the NEXT bucket, so the
    # move must be inside bucket 0 for this test to exercise anything at all.
    for i in range(0, 50, 10):
        assert adapter.decide(_frame(i, "60000")) is None      # mid-bar, nothing closed
    assert adapter.decide(_frame(50, "66000")) is None         # still mid-bar; sets bar 0's close
    # This frame opens bucket 1 and therefore CLOSES bar 0 (close = 66000, a +10% move). The only
    # thing that can suppress an order here is the first-bar rule.
    assert adapter.decide(_frame(70, "66000")) is None, "the first closed bar is never fillable"
    assert adapter.bars_built == 1


def test_u4_dual_the_second_closed_bar_can_trade():
    """THE DUAL (§0.4): the suppression must apply to the FIRST bar only. A rule that silenced
    every bar would pass the test above and make the strategy inert."""
    adapter = BarMomentumOverFrames(segment_index=0, segment=_seg(seconds=600))
    adapter._inner._closes = [Decimal("60000")] * (BarMomentumStrategy.MOMENTUM_BARS + 1)
    for i in range(0, 60, 10):
        adapter.decide(_frame(i, "60000"))
    adapter.decide(_frame(70, "60000"))                        # closes bar 0 (flat) — suppressed
    adapter.decide(_frame(110, "66000"))                       # inside bucket 1: its close is +10%
    result = adapter.decide(_frame(130, "66000"))              # closes bar 1 — must fire
    assert result is not None and result.side.value == "BUY"
    assert adapter.bars_built == 2


def test_u3_a_fresh_adapter_is_cold():
    """U3: a new instance carries no state. A reset that silently failed shows up here."""
    adapter = BarMomentumOverFrames(segment_index=0, segment=_seg(seconds=600))
    assert not adapter.warm
    assert adapter.bars_built == 0


def test_the_adapter_declares_that_it_needs_its_segment():
    """The wiring that makes containment possible: a bar builder that does not know its segment
    cannot refuse a foreign frame."""
    assert BarMomentumOverFrames.wants_segment is True
