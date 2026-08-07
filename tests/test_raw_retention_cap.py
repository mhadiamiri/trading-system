"""
WO-045 §2 (D46) — BOUNDED RETENTION for `captured_raw_text`.

THE DEFECT: `captured_raw_text` retained every raw wire message for the life of the run, unbounded.
Measured on corpus_20260805 at 35-48 MB/h, with run 2 ending near 1.6 GB private after 24 h.

D46 names the failure mode, and it is NOT out-of-memory — it is MISATTRIBUTION:
    unbounded retention -> memory pressure -> swap -> event-loop starvation -> HEARTBEAT_ABSENCE
i.e. a HOST problem entering the gap ledger wearing a VENUE problem's cause code. Precisely the
confusion the host-suspend detector exists to prevent, arriving through a different door.

These proofs assert the three things a retention cap must do, and the retained size is MEASURED
(`sys.getsizeof` over the live buffer) rather than asserted — a bound nobody weighed is a wish.

The cap mirrors the FAILURE_CAPTURE_CAPPED precedent (declared cap on count OR bytes, count-past-cap
surfaced, announce-once, never terminates the run) and diverges from it in exactly one respect,
which is forced rather than chosen: it keeps the LAST N, not the first, because its only in-code
consumer (`_capture_checksum_failure`) reads the trailing window.
"""

import sys

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from trading.logkit.decision import VALID_REASON_CODES


def _adapter(max_frames=100, max_bytes=10 * 1024 * 1024, trim=10):
    a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    a._persistence_optional = True
    a.captured_raw_text = []
    a._raw_text_bytes = 0
    a._raw_text_evicted = 0
    a._raw_retention_capped = False
    a._max_retained_raw_frames = max_frames
    a._max_retained_raw_bytes = max_bytes
    a._raw_text_trim_batch = trim
    return a


# ── the declared cap ──────────────────────────────────────────────────────────────────────────

def test_the_cap_is_declared_with_both_dimensions():
    """A declared cap on COUNT and on BYTES — the same dual-cap shape as the failure-capture path,
    because a cluster of large frames exhausts bytes before count and small ones the reverse."""
    assert KrakenV2BookAdapter.MAX_RETAINED_RAW_FRAMES == 50_000
    assert KrakenV2BookAdapter.MAX_RETAINED_RAW_BYTES == 64 * 1024 * 1024
    assert KrakenV2BookAdapter.RAW_TEXT_TRIM_BATCH == 500


def test_the_cap_never_starves_its_own_consumer():
    """The floor is the failure-capture window: `_capture_checksum_failure` reads the failing frame
    plus CHECKSUM_CAPTURE_PRECEDING_FRAMES of run-up. A cap that evicted below that would be a worse
    defect than the unbounded growth it replaces."""
    a = _adapter()
    assert a._raw_text_floor == KrakenV2BookAdapter.CHECKSUM_CAPTURE_PRECEDING_FRAMES + 1
    assert KrakenV2BookAdapter.MAX_RETAINED_RAW_FRAMES > a._raw_text_floor * 100


def test_the_reason_code_is_declared():
    assert "RAW_RETENTION_CAPPED" in VALID_REASON_CODES["DATA"]


# ── THE BITE: past the cap, retention stops growing and the count is surfaced ─────────────────

def test_retention_stops_growing_at_the_cap_and_evictions_are_counted():
    """BITE. Drive 1,000 messages through a cap of 100: retention is bounded, and the messages
    beyond the cap are COUNTED, not silently dropped."""
    a = _adapter(max_frames=100, trim=10)
    for i in range(1000):
        a._retain_raw_text(f"frame-{i:05d}" + "x" * 200)

    assert len(a.captured_raw_text) <= 100, (
        f"retention must not exceed the declared cap; got {len(a.captured_raw_text)}"
    )
    # COUNT-PAST-CAP: nothing is silently dropped.
    assert a._raw_text_evicted == 1000 - len(a.captured_raw_text)
    assert a._raw_retention_capped is True
    # KEEP-LAST: the most recent frame survives — the failure-capture consumer reads [-1].
    assert a.captured_raw_text[-1].startswith("frame-00999")
    # ...and the oldest is gone.
    assert not any(s.startswith("frame-00000") for s in a.captured_raw_text)


def test_the_memory_bound_is_MEASURED_not_asserted():
    """The bound must be a weighed fact. Retain 200x the cap and MEASURE the live buffer.

    Uncapped, 20,000 messages of ~600 B would retain ~12 MB and keep growing. Capped at 100, the
    measured retained size must stay under the ceiling and — decisively — must not be LARGER at the
    200x point than at the 100x point. It is not constant: batched eviction makes the buffer
    oscillate within [cap - trim, cap], so the declared guarantee is the CEILING plus O(1) growth,
    which is exactly what is asserted here.
    """
    a = _adapter(max_frames=100, trim=10)
    msg = "y" * 600

    def measured():
        return (sum(sys.getsizeof(s) for s in a.captured_raw_text)
                + sys.getsizeof(a.captured_raw_text))

    for _ in range(10_000):
        a._retain_raw_text(msg)
    size_at_10k = measured()

    for _ in range(10_000):
        a._retain_raw_text(msg)
    size_at_20k = measured()

    # O(1) IN RUN LENGTH — the property the whole cap exists for. Doubling the messages does not
    # increase the retained bytes.
    assert size_at_20k <= size_at_10k, (
        f"retained size must not grow with run length: {size_at_10k} -> {size_at_20k}"
    )
    # The CEILING: at most `cap` messages, each ~600 B plus str-object overhead.
    ceiling = 100 * (600 + 200)
    assert size_at_20k < ceiling, f"measured retained size {size_at_20k} B exceeds {ceiling} B"
    assert len(a.captured_raw_text) <= 100
    # The tracked byte counter agrees with reality (no drift between counter and buffer).
    assert a._raw_text_bytes == sum(len(s) for s in a.captured_raw_text)


def test_the_byte_cap_binds_independently_of_the_count_cap():
    """A cluster of LARGE frames must hit the byte cap long before the count cap.

    The count cap is set far above the floor so the BYTE cap is genuinely the binding constraint —
    the point of the test. (With a count cap below the floor, the floor would bind instead and this
    would prove nothing; that precedence is pinned separately below.)
    """
    a = _adapter(max_frames=10_000, max_bytes=500_000, trim=5)
    for _ in range(500):
        a._retain_raw_text("z" * 5_000)          # 500 x 5 KB = 2.5 MB against a 500 KB budget

    assert len(a.captured_raw_text) < 10_000, "the byte cap must bind before the count cap"
    assert a._raw_text_bytes <= 500_000, f"byte budget exceeded: {a._raw_text_bytes}"
    assert a._raw_text_evicted > 0
    assert a._raw_retention_capped is True


def test_the_floor_outranks_both_caps():
    """DECLARED PRECEDENCE: FLOOR > BYTE CAP > COUNT CAP.

    Retention never drops below the failure-capture window even when that exceeds the configured
    budget. Holding 21 extra frames is strictly better than starving `_capture_checksum_failure`,
    which is the path this buffer exists to serve. Pinned so the precedence is a stated guarantee
    rather than emergent behaviour someone later "fixes".
    """
    floor = KrakenV2BookAdapter.CHECKSUM_CAPTURE_PRECEDING_FRAMES + 1
    # Both budgets set absurdly small — below the floor.
    a = _adapter(max_frames=5, max_bytes=10, trim=2)
    for i in range(500):
        a._retain_raw_text(f"m{i}" + "q" * 100)

    assert len(a.captured_raw_text) == floor, (
        f"the floor ({floor}) must hold against caps below it; got {len(a.captured_raw_text)}"
    )
    # The effective bound is max(cap, floor) — and it is still BOUNDED.
    assert a._raw_text_evicted == 500 - floor


def test_the_cap_announces_once_and_does_not_terminate_the_run(caplog):
    """Announce ONCE with the declared code; never terminate. Mirrors _announce_capture_capped."""
    import logging
    a = _adapter(max_frames=50, trim=5)
    with caplog.at_level(logging.ERROR):
        for i in range(500):
            a._retain_raw_text(f"m{i}")

    announcements = [r for r in caplog.records if "RAW_RETENTION_CAPPED" in r.getMessage()]
    assert len(announcements) == 1, f"announce ONCE, got {len(announcements)}"
    # The cap guards memory; the breaker owns termination.
    assert a.capture_terminated is None


# ── THE DUAL (local and direct): under the cap, nothing changes ───────────────────────────────

def test_under_the_cap_everything_is_retained_and_nothing_is_counted():
    """PRESERVATION DUAL. A cap that truncates early is as wrong as one that never fires."""
    a = _adapter(max_frames=100, trim=10)
    for i in range(99):
        a._retain_raw_text(f"frame-{i:05d}")

    assert len(a.captured_raw_text) == 99, "under the cap, EVERY message is retained"
    assert a._raw_text_evicted == 0, "no evictions under the cap"
    assert a._raw_retention_capped is False, "the cap must not announce when it has not engaged"
    assert a.captured_raw_text[0].startswith("frame-00000"), "the oldest is still present"
    assert a._raw_text_bytes == sum(len(s) for s in a.captured_raw_text)


def test_exactly_at_the_cap_nothing_is_evicted():
    """The boundary: at the cap, not over it, retention is untouched."""
    a = _adapter(max_frames=100, trim=10)
    for i in range(100):
        a._retain_raw_text(f"frame-{i:05d}")
    assert len(a.captured_raw_text) == 100
    assert a._raw_text_evicted == 0
    assert a._raw_retention_capped is False


# ── the count-past-cap is SURFACED, not merely stored ─────────────────────────────────────────

def test_the_eviction_count_is_surfaced_in_the_diagnostic_counters():
    """A silent drop would make a memory-bounded run indistinguishable from a quiet one. The
    diagnostic counters must carry the distinction: total received vs retained vs evicted."""
    a = _adapter(max_frames=50, trim=5)
    a._raw_received = 0
    for i in range(500):
        a._raw_received += 1
        a._retain_raw_text(f"m{i}")

    counters = a.get_diagnostic_counters()
    assert counters["raw_messages_received"] == 500, "the TOTAL stays uncapped"
    assert counters["raw_text_retained"] == len(a.captured_raw_text)
    assert counters["raw_text_evicted"] == 500 - counters["raw_text_retained"]
    assert counters["raw_retention_capped"] is True
    assert counters["raw_text_bytes_retained"] == a._raw_text_bytes
    # received == retained + evicted: the accounting closes, so nothing vanished unexplained.
    assert (counters["raw_text_retained"] + counters["raw_text_evicted"]
            == counters["raw_messages_received"])


def test_frames_captured_reports_reach_not_buffer_size():
    """The breaker's forensic tail and the gap ledger mean frames CAPTURED, not frames RETAINED.

    Before the cap those were the same number. With a bounded window, reading the buffer's length
    would UNDER-REPORT the run's reach — a capped buffer silently shrinking the evidentiary claim.
    """
    a = _adapter(max_frames=50, trim=5)
    a._raw_received = 0
    for i in range(1000):
        a._raw_received += 1
        a._retain_raw_text(f"m{i}")

    assert len(a.captured_raw_text) <= 50
    assert a.get_diagnostic_counters()["raw_messages_received"] == 1000, (
        "the run's reach is 1000 frames even though at most 50 are retained"
    )
