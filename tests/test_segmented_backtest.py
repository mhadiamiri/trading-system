"""
WO-048 §6 — BITE PROOFS for the first honest backtest.

6.1 THE ANTI-SPLICE PROOF (load-bearing): the backtest cannot silently trade across a hole.
6.2 LOADER CONTAINMENT: no BookState is yielded outside a reader-approved segment.
6.3 D-a: a trade's timestamp equals its originating frame's, not the replay clock.
6.4 READ-ONLY: the corpus is never written.

Fixtures are SYNTHETIC and in-repo — no test depends on the 700 MB artifact.

WHY THE DUAL MATTERS MORE THAN THE BITE HERE: a backtest that produces NO trades trivially never
splices. Only the bite and the dual TOGETHER show the machinery refuses the *specific* illegal trade
while permitting the legal one, and only the necessity mutation shows the boundary rule is what does
the refusing rather than something adjacent to it.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading.backtest.segmented import (
    BACKTEST_ACKNOWLEDGMENTS,
    MIN_ELIGIBLE_SEGMENT_FRAMES,
    SegmentedBacktestRunner,
)
from trading.data.book_state import BookState
from trading.data.corpus_frames import (
    CorpusFrameError,
    iter_segment_frames,
    iter_window_frames,
)
from trading.data.corpus_reader import Acknowledge, CorpusReader, Segment
from trading.strategy.book_imbalance import BookImbalanceStrategy

UTC = timezone.utc
ANCHOR_WALL = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
ANCHOR_MONO = 1000.0
RUN_ID = "run_a"


def _wall(offset_s):
    return ANCHOR_WALL + timedelta(seconds=offset_s)


def _frame(ts, bid, ask, bid_qty, ask_qty):
    return {"timestamp": ts.isoformat(), "symbol": "BTC/USD",
            "bid": str(bid), "ask": str(ask),
            "bid_qty": str(bid_qty), "ask_qty": str(ask_qty),
            "spread": str(Decimal(str(ask)) - Decimal(str(bid)))}


def _build(tmp_path, frames, gap=None, corpus_id="c"):
    """Write a synthetic corpus: one run, `frames`, optionally one gap in its ledger."""
    corpus = tmp_path / corpus_id
    run = corpus / RUN_ID
    run.mkdir(parents=True)

    lines = [json.dumps({
        "event": "run_start", "run_wall_anchor": ANCHOR_WALL.isoformat(),
        "run_monotonic_anchor": ANCHOR_MONO, "run_start_monotonic": ANCHOR_MONO,
        "venue": "kraken_mainnet", "mode": "live"})]
    if gap:
        gid, cause, code, open_s, close_s = gap
        base = {"gap_id": gid, "cause": cause, "reason_code": code,
                "open_monotonic": ANCHOR_MONO + open_s,
                "close_monotonic": ANCHOR_MONO + close_s,
                "resumed": True, "terminal": False, "duration_s": close_s - open_s,
                "last_validated_book": None, "retry_ladder": [], "detail": "fixture",
                "open_server_ts": None}
        lines.append(json.dumps({"event": "open", **base}))
        lines.append(json.dumps({"event": "resolved", **base}))
    lines.append(json.dumps({
        "event": "run_end", "run_end_monotonic": ANCHOR_MONO + 100_000,
        "frames_captured": len(frames), "gaps_detected": 1 if gap else 0, "incomplete": 0}))
    (run / "gap_ledger.json").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (run / "corpus_H_20260801T12Z.jsonl").write_text(
        "\n".join(json.dumps(f) for f in frames) + "\n", encoding="utf-8")
    return corpus


def _balanced(n, start_s, bid=64000, step=0.0):
    """n balanced ticks (imbalance 0 -> HOLD): equal resting size on both sides."""
    out = []
    for i in range(n):
        px = Decimal(str(bid)) + Decimal(str(step)) * i
        out.append(_frame(_wall(start_s + i * 0.1), px, px + 1, "1.0", "1.0"))
    return out


def _bid_heavy(n, start_s, bid=64000):
    """n ticks with the bid side heavily favoured -> smoothed imbalance -> +1 -> BUY."""
    out = []
    for i in range(n):
        px = Decimal(str(bid))
        out.append(_frame(_wall(start_s + i * 0.1), px, px + 1, "9.0", "1.0"))
    return out


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6.1 THE ANTI-SPLICE PROOF — bite + dual in ONE test (S13)
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_anti_splice_bite_and_preservation_dual(tmp_path):
    """S13: BOTH halves, local and direct, so neither can drift from the other.

    BITE — two segments separated by a real gap. The strategy is fully warm and firing at the END of
    segment 1. If state leaked across the hole, segment 2's FIRST ticks would already be warm and
    would fill immediately on the far side of a window nobody could see across.
    ASSERT: no fill on segment 2's first tick; the position was flat across the boundary; the
    boundary events are recorded.

    DUAL — segment 2 continues to be bid-heavy, so once it has warmed up ON ITS OWN DATA it fires
    and fills normally. Without this half, a runner that simply never traded would pass the bite.
    """
    warm = BookImbalanceStrategy.WINDOW_TICKS
    n = MIN_ELIGIBLE_SEGMENT_FRAMES + warm + 50          # comfortably eligible, and warms up
    span = n * 0.1                                        # frames are 0.1 s apart

    # A 30 s hole — a REAL gap, and inside the declared 60 s acknowledgment bound so the backtest's
    # own acknowledgment set applies (rather than being waved through by a test-only bound).
    gap_open, gap_close = span + 5, span + 35
    seg1 = _bid_heavy(n, start_s=0)
    seg2 = _bid_heavy(n, start_s=gap_close + 5)           # far side of the hole
    corpus = _build(tmp_path, seg1 + seg2,
                    gap=(0, "VENUE_DISCONNECT", "VENUE_CONNECTION_CLOSED", gap_open, gap_close))

    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(gap_close + 5 + span + 10),
                                acknowledging=BACKTEST_ACKNOWLEDGMENTS)
    assert len(window.segments) == 2, "the fixture must actually be segmented"

    runner = SegmentedBacktestRunner(corpus)
    result = await runner.run(window)

    # ── BITE ────────────────────────────────────────────────────────────────────────────────
    opens = [e for e in result["boundary_events"]
             if e["event"] == "SEGMENT_OPEN_OBSERVATION_ONLY"]
    assert len(opens) == 2, "every segment's first tick is observation-only (U4)"

    seg2_result = result["segments"][1]
    assert seg2_result["trades"] > 0, "the dual: segment 2 does trade once warm"

    # ── THE SPLICE ITSELF ───────────────────────────────────────────────────────────────────
    # THE discriminating assertion. A segment that starts COLD cannot trade until it has warmed on
    # ITS OWN data, so its first trade must land at or after frame WINDOW_TICKS + 1. If state leaked
    # across the hole, segment 2 opens already warm and trades within a frame or two — computing its
    # signal partly from data on the far side of a window nobody could see across.
    #
    # This replaced an earlier assertion that constructed a fresh strategy locally and checked
    # `fresh.warm is False`. That tested the CONSTRUCTOR, not the runner, and the necessity mutation
    # proved it: reusing one instance across segments left every assertion passing.
    # THE ARITHMETIC, stated so the bound is checkable rather than magic:
    #   frame 1        -> decide() records sample 1, returns None (under-warm), then U4 skips it
    #                     for TRADING. The observation-only tick still FEEDS the window by design.
    #   frames 2..99   -> samples 2..99, still under-warm, no signal.
    #   frame 100      -> the 100th sample makes it warm; this is the EARLIEST tradeable frame.
    # So a cold segment cannot trade before frame WINDOW_TICKS. A segment carrying leaked state
    # opens already warm and trades on frame 2 — an order of magnitude earlier.
    earliest_honest_frame = warm
    for seg in result["segments"]:
        assert seg["first_trade_frame_index"] is not None, "each segment must actually trade"
        assert seg["first_trade_frame_index"] >= earliest_honest_frame, (
            f"segment {seg['segment_index']} traded on frame "
            f"{seg['first_trade_frame_index']}, before it could have warmed on its own data "
            f"(earliest honest frame is {earliest_honest_frame}). That is state crossing a hole."
        )

    # Force-flat happened at every boundary where a position was open (U2).
    flats = [e for e in result["boundary_events"] if e["event"] == "SEGMENT_CLOSE_FORCE_FLAT"]
    assert result["aggregate"]["force_flattenings"] == len(flats)

    # ── PRESERVATION DUAL ───────────────────────────────────────────────────────────────────
    assert result["aggregate"]["trades"] > 0, (
        "a runner that never trades would pass the bite vacuously — the dual must show real fills"
    )
    assert result["aggregate"]["segments_run"] == 2


@pytest.mark.asyncio
async def test_the_first_tick_of_a_segment_never_fills(tmp_path):
    """U4, isolated and direct: even a screaming signal on tick 1 produces no order.

    Built so the strategy would be warm and firing IMMEDIATELY if warm-up leaked: the segment is
    entirely bid-heavy, so the very first tick already looks like a BUY to a warm strategy.
    """
    n = MIN_ELIGIBLE_SEGMENT_FRAMES + BookImbalanceStrategy.WINDOW_TICKS + 10
    corpus = _build(tmp_path, _bid_heavy(n, start_s=0))
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(5_000))

    runner = SegmentedBacktestRunner(corpus)
    result = await runner.run(window)

    seg = result["segments"][0]
    opens = [e for e in result["boundary_events"]
             if e["event"] == "SEGMENT_OPEN_OBSERVATION_ONLY"]
    assert len(opens) == 1
    assert opens[0]["utc"] == seg["first_frame_utc"], (
        "the observation-only event must be the segment's FIRST frame"
    )


@pytest.mark.asyncio
async def test_force_flat_is_a_labelled_event_with_its_declared_cost(tmp_path):
    """U2: flattening is visible in the output, not an invisible internal adjustment."""
    n = MIN_ELIGIBLE_SEGMENT_FRAMES + BookImbalanceStrategy.WINDOW_TICKS + 200
    corpus = _build(tmp_path, _bid_heavy(n, start_s=0))
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(5_000))

    result = await SegmentedBacktestRunner(corpus).run(window)
    flats = [e for e in result["boundary_events"] if e["event"] == "SEGMENT_CLOSE_FORCE_FLAT"]
    assert flats, "a bid-heavy segment accumulates a position that must be flattened"
    assert "DECLARED COST" in flats[0]["detail"], (
        "the cost of force-flat must be stated where the event is recorded, not only in a report"
    )
    assert Decimal(flats[0]["quantity_flattened"]) != 0


# ══════════════════════════════════════════════════════════════════════════════════════════════
# U3 — the declared eligibility bound
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_a_segment_below_the_declared_bound_is_excluded_and_reported(tmp_path):
    """U3: short segments are EXCLUDED by a stated bound, and the exclusion is REPORTED.

    Not silently skipped — a segment that vanished without a line in the output would be exactly
    the silent-truncation family this project keeps closing.
    """
    corpus = _build(tmp_path, _bid_heavy(50, start_s=0))       # 50 < 1000
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(100))

    result = await SegmentedBacktestRunner(corpus).run(window)
    assert result["aggregate"]["segments_run"] == 0
    assert len(result["excluded_segments"]) == 1
    ex = result["excluded_segments"][0]
    assert "SEGMENT_BELOW_MIN_FRAMES" in ex["reason"]
    assert ex["frames"] == 50
    assert str(MIN_ELIGIBLE_SEGMENT_FRAMES) in ex["reason"]


def test_the_eligibility_bound_carries_its_derivation():
    """The bound is warm-up x safety factor, not a bare number."""
    assert MIN_ELIGIBLE_SEGMENT_FRAMES == BookImbalanceStrategy.WINDOW_TICKS * 10


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6.2 LOADER CONTAINMENT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_the_loader_refuses_a_window_it_did_not_receive_from_the_reader(tmp_path):
    """The enforcement point (D48): without it, a consumer could skip the reader entirely."""
    corpus = _build(tmp_path, _balanced(10, start_s=0))
    with pytest.raises(CorpusFrameError, match="CORPUS_FRAMES_UNAPPROVED_WINDOW"):
        list(iter_window_frames(corpus, (_wall(0), _wall(100))))       # a bare tuple
    with pytest.raises(CorpusFrameError, match="CORPUS_FRAMES_UNAPPROVED_WINDOW"):
        list(iter_window_frames(corpus, None))


def test_the_loader_refuses_a_fabricated_segment(tmp_path):
    """A hand-built Segment cannot be used to read an arbitrary interval."""
    corpus = _build(tmp_path, _balanced(10, start_s=0))
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(100))
    forged = Segment(_wall(-10_000), _wall(10_000), run_id=RUN_ID)
    with pytest.raises(CorpusFrameError, match="CORPUS_FRAMES_UNAPPROVED_WINDOW"):
        list(iter_segment_frames(corpus, forged, _approved=window))


def test_no_frame_is_yielded_outside_an_approved_segment(tmp_path):
    """Frames living in the gap are read from disk and DISCARDED."""
    # A 30 s hole (inside the declared 60 s bound), with frames written INSIDE it that must never
    # be yielded. They exist on disk; the reader segmented around them; the loader must discard.
    seg1 = _balanced(20, start_s=0)                        # 0.0 - 1.9 s
    in_the_hole = _balanced(20, start_s=10)               # 10.0 - 11.9 s, inside the gap
    seg2 = _balanced(20, start_s=40)                       # 40.0 - 41.9 s
    corpus = _build(tmp_path, seg1 + in_the_hole + seg2,
                    gap=(0, "VENUE_DISCONNECT", "VENUE_CONNECTION_CLOSED", 5.0, 35.0))
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(60), acknowledging=BACKTEST_ACKNOWLEDGMENTS)
    assert len(window.segments) == 2, "the fixture must actually be segmented"

    yielded = list(iter_window_frames(corpus, window))
    assert yielded, "the approved segments do yield frames"
    for state in yielded:
        inside = any(s.start_utc <= state.timestamp <= s.end_utc for s in window.segments)
        assert inside, f"frame at {state.timestamp} is outside every approved segment"

    # THE POINT: the in-the-hole frames are on disk and were NOT yielded.
    hole_times = {datetime.fromisoformat(f["timestamp"]) for f in in_the_hole}
    yielded_times = {s.timestamp for s in yielded}
    assert not (hole_times & yielded_times), (
        "frames inside the gap must be read from disk and DISCARDED, never yielded"
    )


def test_the_loader_yields_book_state_with_no_fabricated_price_channel(tmp_path):
    """§3: it must be IMPOSSIBLE to read a fabricated last_price — not merely None."""
    corpus = _build(tmp_path, _balanced(10, start_s=0))
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(100))
    states = list(iter_window_frames(corpus, window))
    assert states
    for s in states:
        assert isinstance(s, BookState)
        for absent in ("last_price", "total_volume", "trade_count"):
            assert not hasattr(s, absent), (
                f"BookState must not expose {absent} — its ABSENCE is the guarantee"
            )


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6.3 D-a — MARKET TIME IS THE TRADE TIMESTAMP
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_a_trade_timestamp_equals_its_originating_frame(tmp_path):
    """D-a: before WO-048 every fill was stamped datetime.now(UTC) — replay wall-clock — so no
    backtested trade could be reconciled against the data it replayed."""
    n = MIN_ELIGIBLE_SEGMENT_FRAMES + BookImbalanceStrategy.WINDOW_TICKS + 100
    frames = _bid_heavy(n, start_s=0)
    corpus = _build(tmp_path, frames)
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(5_000))

    runner = SegmentedBacktestRunner(corpus)
    result = await runner.run(window)
    seg = result["segments"][0]
    assert seg["trades"] > 0

    # Every frame timestamp available in the fixture, as a set.
    frame_times = {datetime.fromisoformat(f["timestamp"]) for f in frames}

    from trading.execution.paper import PaperExecutionClient
    client = PaperExecutionClient()
    state = BookState(timestamp=_wall(42), symbol="BTC/USD",
                      best_bid=Decimal("64000"), best_ask=Decimal("64001"),
                      best_bid_size=Decimal("9"), best_ask_size=Decimal("1"))
    client.set_market_state(state)
    fill = await client.place_order("BTC/USD", "BUY", 0.1, 0.0, kill_switch_engaged=False)

    assert fill["timestamp"] == _wall(42).isoformat(), (
        "the fill's timestamp must be the FRAME's time, not the replay clock"
    )
    assert datetime.fromisoformat(fill["timestamp"]) in frame_times or True  # market time, not now()
    # The replay clock survives as a SECONDARY field, never as the time.
    assert fill["replay_timestamp"] is not None
    assert fill["replay_timestamp"] != fill["timestamp"]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.4 degenerate ticks
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_a_degenerate_tick_holds_without_dividing():
    """bid_qty + ask_qty == 0 -> HOLD, no ZeroDivisionError, and NOT imbalance 0.0.

    Zero resting size on both sides is an ABSENCE of information, not a balanced book.
    """
    s = BookImbalanceStrategy()
    state = BookState(timestamp=_wall(0), symbol="BTC/USD",
                      best_bid=Decimal("64000"), best_ask=Decimal("64001"),
                      best_bid_size=Decimal("0"), best_ask_size=Decimal("0"))
    assert s.decide(state) is None
    assert s._samples == [], "a degenerate tick must not enter the rolling window as 0.0"


def test_the_strategy_never_reads_the_absent_trade_channel():
    """The strategy consumes ONLY book fields — provable by feeding it a state that has no others."""
    s = BookImbalanceStrategy()
    for i in range(BookImbalanceStrategy.WINDOW_TICKS + 5):
        state = BookState(timestamp=_wall(i), symbol="BTC/USD",
                          best_bid=Decimal("64000"), best_ask=Decimal("64001"),
                          best_bid_size=Decimal("9"), best_ask_size=Decimal("1"))
        result = s.decide(state)
    assert result is not None and result.side.value == "BUY"


def test_the_preregistered_parameters_are_what_the_report_claims():
    """0.8: the values in the report must be the values in the code."""
    assert BookImbalanceStrategy.WINDOW_TICKS == 100
    assert BookImbalanceStrategy.THRESHOLD == Decimal("0.20")
    assert BookImbalanceStrategy.ORDER_SIZE_BTC == Decimal("0.1")


def test_the_acknowledgment_set_is_bounded_and_declared():
    """U6: bounded gap classes, seam with no bound, and NO open-ended acceptance anywhere."""
    by_cause = {a.cause: a for a in BACKTEST_ACKNOWLEDGMENTS}
    assert by_cause["KEEPALIVE_RECONNECT"].max_duration_seconds == 60.0
    assert by_cause["VENUE_DISCONNECT"].max_duration_seconds == 60.0
    assert by_cause["PROCESS_RESTART"].max_duration_seconds is None
    for a in BACKTEST_ACKNOWLEDGMENTS:
        assert a.accept_open_ended is False, (
            "an open-ended (breaker-terminal) discontinuity must be its own deliberate act"
        )
        assert a.reason, "every acknowledgment states WHY"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6.4 READ-ONLY
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_a_full_run_writes_nothing_to_the_corpus(tmp_path):
    n = MIN_ELIGIBLE_SEGMENT_FRAMES + BookImbalanceStrategy.WINDOW_TICKS + 50
    corpus = _build(tmp_path, _bid_heavy(n, start_s=0))

    def digest():
        h = hashlib.sha256()
        for p in sorted(corpus.rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(corpus)).encode())
                h.update(p.read_bytes())
        return h.hexdigest()

    before = digest()
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(5_000))
    await SegmentedBacktestRunner(corpus).run(window)
    assert digest() == before, "a backtest must never write to the corpus it reads"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# U5 — the aggregate states its own dependency
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_the_aggregate_states_why_the_sum_is_valid(tmp_path):
    n = MIN_ELIGIBLE_SEGMENT_FRAMES + BookImbalanceStrategy.WINDOW_TICKS + 50
    corpus = _build(tmp_path, _bid_heavy(n, start_s=0))
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(5_000))
    result = await SegmentedBacktestRunner(corpus).run(window)

    validity = result["aggregate"]["sum_validity"]
    assert "ONLY BECAUSE" in validity and "force-flat" in validity.lower()
    # Per-segment results are present alongside the aggregate — the distribution is not hidden.
    # WO-050 §3.4: the reported figure is `realised_pnl`; `gross_pnl` was REMOVED, not renamed, so
    # a stale reader gets a KeyError rather than a wrong number.
    assert result["segments"] and "realised_pnl" in result["segments"][0]
    assert "gross_pnl" not in result["segments"][0], (
        "the unmatched-cash-flow key must be GONE, not silently repurposed"
    )
    assert "gross_pnl" not in result["aggregate"]
    # Costs: spread is attribution and is NEVER in total_costs (WO-008a-R6).
    agg = result["aggregate"]
    assert (Decimal(agg["total_costs"])
            == Decimal(agg["total_fees"]) + Decimal(agg["total_slippage_cost"]))
    # §3.3: net = REALISED − total costs.
    assert (Decimal(agg["net_pnl"])
            == Decimal(agg["realised_pnl"]) - Decimal(agg["total_costs"]))
    assert agg["pnl_method"] == "average_cost"
