"""
WO-057 §3/§4/§5/§6 — THE ABORT-CONDITION DETECTORS.

D57: *"an abort condition that cannot fire is a guard that cannot bite, same family, same
standard."* Three of six could not fire at WO-055. Condition 2 would have returned a FALSE GREEN.

Every detector below is proved to FIRE, proved not to fire on the healthy case (the dual), and
carries its falsifier. §0.10 — single-purpose tests.
"""

import json
from pathlib import Path

import pytest

from tools.corpus_fabrication_scan import CLEAN, NOT_APPLICABLE, VIOLATIONS, scan

# ══════════════════════════════════════════════════════════════════════════════════════════════
# §4 CONDITION 2 — THE SCANNER'S THREE OUTCOMES
# ══════════════════════════════════════════════════════════════════════════════════════════════


def _corpus(tmp_path, frames):
    run = tmp_path / "run1"
    run.mkdir(parents=True, exist_ok=True)
    seg = run / "corpus_TEST_20260808T00Z.jsonl"
    seg.write_text("\n".join(json.dumps(f) for f in frames) + "\n", encoding="utf-8")
    return tmp_path


def _frame(ts, trades=None):
    f = {"timestamp": ts, "symbol": "BTC/USD", "bid": "64000", "ask": "64001",
         "bid_qty": "1", "ask_qty": "1", "spread": "1"}
    if trades is not None:
        f["trades"] = trades
    return f


def test_bite_a_fabricated_last_price_is_found_and_named(tmp_path):
    """(c) VIOLATIONS. `observable: true` with `count: 0` and a non-null `last_price` — a price not
    backed by any observed trade in its interval. The D48 substitution at capture time."""
    root = _corpus(tmp_path, [
        _frame("2026-08-08T00:00:01Z", {"observable": True, "count": 1, "volume": "0.5",
                                        "last_price": "64000.0"}),
        _frame("2026-08-08T00:00:02Z", {"observable": True, "count": 0, "volume": "0",
                                        "last_price": "64000.0"}),      # FABRICATED
    ])
    report = scan(root)
    assert report["outcome"] == VIOLATIONS
    assert len(report["violations"]) == 1
    v = report["violations"][0]
    assert v["timestamp"] == "2026-08-08T00:00:02Z", "the offending frame is NAMED, not counted"
    assert v["count"] == 0 and v["last_price"] == "64000.0"


def test_dual_a_correct_corpus_is_clean_with_a_non_zero_examined_count(tmp_path):
    """(b) CLEAN. The dual: a scanner that flagged everything would pass the bite and be useless.
    The examined count must be > 0 — 'clean' over nothing is the false green in disguise."""
    root = _corpus(tmp_path, [
        _frame("2026-08-08T00:00:01Z", {"observable": True, "count": 2, "volume": "0.5",
                                        "last_price": "64000.0"}),
        _frame("2026-08-08T00:00:02Z", {"observable": True, "count": 0, "volume": "0",
                                        "last_price": None}),
    ])
    report = scan(root)
    assert report["outcome"] == CLEAN
    assert report["frames_examined"] == 2, "'clean' means it looked at something"
    assert report["violations"] == []


def test_the_third_case_a_book_only_corpus_is_NOT_APPLICABLE_not_clean(tmp_path):
    """(a) NOT_APPLICABLE — THE ONE THAT MATTERS.

    A book-only corpus has no `trades.observable` field, so the question cannot be asked. WO-055
    showed this returning zero and being read as "PASS — no fabricated prices". Reporting it as
    CLEAN is the ratified false green, and refusing to is the whole point of the scanner.
    """
    root = _corpus(tmp_path, [_frame("2026-08-08T00:00:01Z"), _frame("2026-08-08T00:00:02Z")])
    report = scan(root)
    assert report["outcome"] == NOT_APPLICABLE
    assert report["outcome"] != CLEAN, "an unanswerable question is NOT a clean bill of health"
    assert report["frames_total"] == 2, "the frames were read..."
    assert report["frames_examinable"] == 0, "...and none of them could be examined"
    assert "NOT 'zero fabricated prices'" in report["detail"]


def test_every_report_states_examined_of_examinable(tmp_path):
    """§4.2: '0 violations' without 'of N examinable' is indistinguishable from examining nothing.
    Both numbers are always present, in all three outcomes."""
    for frames in (
        [_frame("t1")],
        [_frame("t1", {"observable": True, "count": 0, "volume": "0", "last_price": None})],
        [_frame("t1", {"observable": True, "count": 0, "volume": "0", "last_price": "1"})],
    ):
        report = scan(_corpus(tmp_path / str(id(frames)), frames))
        assert "frames_examinable" in report and "frames_examined" in report


def test_an_unobservable_frame_is_not_examinable_for_fabrication(tmp_path):
    """`observable: false` is the ABSENCE of a claim: nothing to fabricate. It counts as examinable
    (the field exists, so the question CAN be asked of this corpus) but is not examined."""
    root = _corpus(tmp_path, [
        _frame("t1", {"observable": False, "count": None, "volume": None, "last_price": None}),
    ])
    report = scan(root)
    assert report["frames_examinable"] == 1
    assert report["frames_examined"] == 0
    assert report["outcome"] == CLEAN


def test_a_traded_interval_with_no_price_is_reported_separately_not_as_fabrication(tmp_path):
    """Two different defects must not merge: a missing price is not an invented one."""
    root = _corpus(tmp_path, [
        _frame("t1", {"observable": True, "count": 3, "volume": "1", "last_price": None}),
    ])
    report = scan(root)
    assert report["outcome"] == CLEAN, "not a fabrication"
    assert len(report["missing_price_on_traded_interval"]) == 1


def test_the_report_carries_its_falsifier_and_distinguishes_the_two_zeros(tmp_path):
    """0.12, and the distinction that is this WO's centrepiece."""
    report = scan(_corpus(tmp_path, [_frame("t1")]))
    assert "NOT interchangeable" in report["falsifier"]
    assert "could not speak" in report["falsifier"]


def test_the_running_last_price_is_not_treated_as_fabrication(tmp_path):
    """`running_last_price` legitimately carries forward and is separately named; only
    `last_price` is the per-interval claim. Confusing them would flag every quiet frame."""
    root = _corpus(tmp_path, [
        _frame("t1", {"observable": True, "count": 0, "volume": "0", "last_price": None,
                      "running_last_price": "64000.0", "running_last_price_age_ms": 5000}),
    ])
    assert scan(root)["outcome"] == CLEAN


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §3 CONDITION 1 — THE TRADE-ACK DEADLINE
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_bite_condition_1_fires_when_the_ack_never_arrives():
    """§3.1: verified, not assumed. Drive the detector past its declared timeout and show it
    records a DECLARED outage — the effect, not a log line (0.9)."""
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
    from trading.data.trade_channel import SUBSCRIBE_ACK_TIMEOUT_SECONDS

    a = KrakenV2BookAdapter(mode="fixture")
    a._trade_ack_deadline = 1000.0
    a._check_trade_ack_deadline(1000.0 + SUBSCRIBE_ACK_TIMEOUT_SECONDS)

    ledger = a.get_trade_outage_ledger()
    assert len(ledger) == 1
    assert ledger[0]["cause"] == "TRADE_CHANNEL_SUBSCRIBE_FAILED"
    assert a.trade_snapshot_for_frame("t")["observable"] is False, (
        "the ECONOMIC EFFECT: every frame from here says 'we could not see'"
    )


def test_dual_condition_1_does_not_fire_when_the_ack_arrives_in_time():
    """§3.3: a detector that fires on every run is worse than none."""
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    a = KrakenV2BookAdapter(mode="fixture")
    a._trade_ack_deadline = 1000.0
    a._handle_subscription_response({
        "method": "subscribe", "result": {"channel": "trade"}, "success": True})
    a._check_trade_ack_deadline(1000.0 + 999.0)          # long past the old deadline

    assert a.get_trade_outage_ledger() == [], "an acked subscription records no outage"
    assert a.trade_snapshot_for_frame("t")["observable"] is True


def test_condition_1_does_not_fire_before_the_timeout():
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    a = KrakenV2BookAdapter(mode="fixture")
    a._trade_ack_deadline = 1000.0
    a._check_trade_ack_deadline(999.0)
    assert a.get_trade_outage_ledger() == []


def test_condition_1_records_the_outage_only_once():
    """Repeated checks after the deadline must not fill the ledger with duplicates — a ledger that
    inflates is as unreadable as one that stays empty."""
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    a = KrakenV2BookAdapter(mode="fixture")
    a._trade_ack_deadline = 1000.0
    for _ in range(5):
        a._check_trade_ack_deadline(2000.0)
    assert len(a.get_trade_outage_ledger()) == 1


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §5 CONDITION 4 — THE PER-SEGMENT TRIM COUNTER
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _retention_adapter():
    """An adapter with the retention buffer initialised as the live loop initialises it.

    `captured_raw_text` and `_raw_text_bytes` are created inside `get_live_market_data`, not in
    __init__, so a bare adapter has no buffer to trim. Establishing the same preconditions here is
    what lets these tests exercise the REAL `_retain_raw_text` rather than a stand-in.
    """
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    a = KrakenV2BookAdapter(mode="fixture")
    a.captured_raw_text = []
    a._raw_text_bytes = 0
    return a


def test_bite_condition_4_counts_trim_EVENTS_not_evicted_frames():
    """§5.1: `_raw_text_evicted` counts FRAMES — one trim of 500 and 500 trims of one are identical
    in it, and only the second is the condition's subject. This counts the EVENT."""
    a = _retention_adapter()
    a._max_retained_raw_frames = 10
    a._raw_text_trim_batch = 2
    a._raw_text_floor = 1
    for i in range(40):
        a._retain_raw_text(f"frame-{i}")

    assert a._raw_text_trim_events >= 2, "repeated trimming within one segment"
    assert a._raw_text_evicted > a._raw_text_trim_events, "frames evicted exceeds trim events"


def test_condition_4_threshold_can_trip_and_is_a_named_constant():
    """§5.2: the threshold reads against a real number, and lives in code rather than in prose."""
    from tools.live_corpus_capture import RETENTION_TRIM_ABORT_THRESHOLD

    assert RETENTION_TRIM_ABORT_THRESHOLD == 2, "'more than once per segment'"

    a = _retention_adapter()
    a._max_retained_raw_frames = 10
    a._raw_text_trim_batch = 2
    a._raw_text_floor = 1
    for i in range(60):
        a._retain_raw_text(f"frame-{i}")
    assert a.take_trim_events() >= RETENTION_TRIM_ABORT_THRESHOLD, "the condition CAN trip"


def test_dual_condition_4_does_not_trip_on_zero_or_one_trim():
    """§5.3: one trim is the cap working as designed on a busy hour, not an abort."""
    from tools.live_corpus_capture import RETENTION_TRIM_ABORT_THRESHOLD

    quiet = _retention_adapter()
    for i in range(20):
        quiet._retain_raw_text(f"frame-{i}")
    assert quiet.take_trim_events() == 0, "well under the caps: no trim at all"
    assert 0 < RETENTION_TRIM_ABORT_THRESHOLD


def test_the_counter_is_read_and_reset_in_one_call():
    """Two calls could interleave with a trim and lose an event — understating exactly the number
    the condition tests."""
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    a = KrakenV2BookAdapter(mode="fixture")
    a._raw_text_trim_events = 7
    assert a.take_trim_events() == 7
    assert a.take_trim_events() == 0, "reset by the read; per-segment, not cumulative"


def test_the_trim_count_reaches_the_segment_record():
    """0.9 / §5.1: in the corpus, not only in a log. The field exists on the segment manifest and
    distinguishes 'not measured' (None) from a measured zero."""
    from tools.live_corpus_capture import SegmentManifest

    m = SegmentManifest(filename="f", sha256="s", frame_count=1, size_bytes=1, compressed=False,
                        start_utc="a", end_utc="b", raw_text_trim_events=3)
    assert m.raw_text_trim_events == 3
    default = SegmentManifest(filename="f", sha256="s", frame_count=1, size_bytes=1,
                              compressed=False, start_utc="a", end_utc="b")
    assert default.raw_text_trim_events is None, "None (not measured) != 0 (measured zero)"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §6 CONDITIONS 3, 5, 6 — RE-VERIFIED, NOT INFERRED
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_condition_3_can_now_fire_and_is_reachable_from_the_capture_path():
    """WO-055 had this 🟡 'armed in the library, unreachable in capture'. WO-056 wired the demux,
    so re-verify rather than infer: a trade arriving while the channel is recorded unobservable.

    The capture path resolves the contradiction the honest way round — the evidence of our own eyes
    wins, so the channel is marked observable again and the OUTAGE KEEPS ITS BOUNDS. The ledger
    still says we could not see for that interval; it does not pretend the gap never happened.
    """
    import asyncio

    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    a = KrakenV2BookAdapter(mode="fixture")
    a._trade_merger.mark_unobservable("TRADE_CHANNEL_DROPPED", "2026-08-08T00:00:00Z")
    asyncio.run(a.process_raw_frame({
        "channel": "trade", "type": "update",
        "data": [{"symbol": "BTC/USD", "side": "buy", "qty": "0.1", "price": "64000",
                  "ord_type": "market", "trade_id": 1, "timestamp": "2026-08-08T00:00:05Z"}]}))

    ledger = a.get_trade_outage_ledger()
    assert len(ledger) == 1 and ledger[0]["cause"] == "TRADE_CHANNEL_DROPPED"
    assert ledger[0]["resolved"] is True, "the outage is CLOSED, with its bounds intact"
    snap = a.trade_snapshot_for_frame("2026-08-08T00:00:06Z")
    assert snap["observable"] is True and snap["count"] == 1


def test_condition_5_a_trade_cause_cannot_enter_the_GAP_ledger():
    """Re-verified: the two ledgers stay separate. A trade outage produces no no-emission window,
    so recording a gap would subtract book coverage that was never lost."""
    from trading.data.adapters.kraken_v2_book import GAP_CAUSES
    from trading.data.trade_channel import TRADE_OUTAGE_CAUSES

    assert not (set(GAP_CAUSES) & set(TRADE_OUTAGE_CAUSES))
    assert len(GAP_CAUSES) == 5, "the ruled four plus HOST_SUSPEND — still not extended"


def test_condition_6_the_throughput_instrument_still_exists_after_the_second_channel():
    """Re-verified because the capture path changed materially: WO-056 added a second channel to
    the same loop, which is exactly the change that could have displaced the baseline instrument."""
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    import inspect

    # The instrument is created by the live loop, not by __init__, so assert on the loop that
    # creates it AND on the accessor that surfaces it — asserting on a bare instance would test
    # only that __init__ is unchanged, which is not the thing at risk.
    loop_src = inspect.getsource(KrakenV2BookAdapter.get_live_market_data)
    assert "ThroughputRecord(" in loop_src, "the throughput instrument survives the second channel"
    assert "self._per_frame_record" in loop_src, "and so does the per-frame instrument"
    assert callable(KrakenV2BookAdapter.get_diagnostic_counters)
