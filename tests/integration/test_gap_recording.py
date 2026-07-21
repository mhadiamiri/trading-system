"""
WO-014c-2 §2 — DATA-GAP RECORDING, bite proof PER CAUSE (rule 0.1h/0.1i).

Each proof drives the REAL production trigger through get_live_market_data (no hand-feeding)
and asserts the OBSERVABLE END STATE: a GapRecord written to the ledger with its schema
fields populated (evidence/WO-014c-2/gap_schema.txt), on the shared time.monotonic() clock.
The four-artifact bite proof (PASS / real FAIL under a weakened recorder / PASS after
restore / sha256 exact-restore) is executed against these tests and captured in
evidence/WO-014c-2/gap_recording_bite_*.txt.

Causes (the ruled four):
  KEEPALIVE_RECONNECT   — heartbeat absence      -> a reconnect gap that RESUMES
  CHECKSUM_RESYNC       — checksum mismatch      -> a same-socket resync gap (no ladder)
  BREAKER_RETRY_LADDER  — reconnect backoff      -> the retry_ladder FIELD on a reconnect gap
  VENUE_DISCONNECT      — venue close / terminal -> resumes (4c) OR terminal breaker (4a)
Plus: overlapping/nested gaps (probe 1 union semantics) and ledger completeness accounting.

HONEST FIXTURE LIMIT: simulated transport (tests/fixtures/fake_ws_transport.py). Only the
isolated live re-run confirms Kraken's real reopen/close behavior. NO NETWORK.
"""

import copy
import logging

import pytest
from unittest.mock import patch
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedError

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, CircuitBreakerTripped
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory, REOPEN_FAILURE


async def _no_sleep(_delay):
    """Collapse backoff so proofs are fast and cannot hang (the delay VALUE is still computed
    and recorded in the ladder; only the real wait is skipped)."""
    return None


def _live_adapter():
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._reconnect_sleep = _no_sleep
    adapter._reconnect_jitter = lambda: 1.0      # deterministic ladder delays
    adapter._reconnect_backoff_base = 0.01
    adapter._reconnect_backoff_cap = 0.04
    return adapter


def _corrupted_update():
    """A real incremental whose checksum will not match the applied book (drives the
    production checksum-failure branch, exactly as test_snapshot_recovery does)."""
    corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
    corrupted["data"][0]["bids"][0]["price"] = "45283.7"
    return corrupted


def _bad_snapshot():
    bad = copy.deepcopy(SNAPSHOT_FRAME)
    bad["data"][0]["checksum"] = 1  # never valid for this ladder
    return bad


def _assert_core_fields(g):
    """Fields EVERY gap record must carry, whatever the cause."""
    assert g.gap_id is not None and g.gap_id >= 0, "gap_id (per-occurrence identity) must be set"
    assert g.cause in (
        "KEEPALIVE_RECONNECT", "CHECKSUM_RESYNC", "VENUE_DISCONNECT",
    ), f"cause must be a ruled trigger, got {g.cause!r}"
    assert g.reason_code, "reason_code links the gap to the audit vocabulary"
    assert g.open_monotonic > 0, "open bound is on the shared monotonic clock"
    assert g.last_validated_book is not None, "last checksum-good top-of-book at open"
    assert g.last_validated_book["best_bid"], "the last-good book carries a real top-of-book"
    assert g.detail, "human-readable trigger detail"
    assert g.open_server_ts, "corroborating venue wall-clock of the boundary frame"


@pytest.mark.asyncio
async def test_keepalive_reconnect_gap_recorded(caplog):
    """CAUSE 1: a silent link -> heartbeat absence -> reconnect -> a KEEPALIVE_RECONNECT gap
    that OPENS at the last frame and CLOSES at the post-reconnect validated emit."""
    adapter = _live_adapter()
    adapter._heartbeat_absence_timeout = 0.05   # dead after 50ms of silence
    adapter._app_ping_interval = 100.0          # isolate §1.1

    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME], "on_drain": "block"},        # emit, then SILENT -> absence
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},    # reconnect target: emit, stay alive
    ])

    emitted = []
    with caplog.at_level(logging.INFO):
        with patch("websockets.connect", factory.connect):
            async for state in adapter.get_live_market_data(duration_seconds=0.25):
                emitted.append(state)

    ledger = adapter.get_gap_ledger()
    assert ledger is not None
    assert ledger.gaps_detected == 1, f"exactly one keepalive gap; got {ledger.gaps_detected}"
    g = ledger.gaps[0]
    _assert_core_fields(g)
    assert g.cause == "KEEPALIVE_RECONNECT"
    assert g.reason_code == "HEARTBEAT_ABSENCE"
    # OBSERVABLE END STATE: the gap RESUMED (closed by the post-reconnect emit).
    assert g.resumed is True and g.terminal is False
    assert g.close_monotonic is not None and g.close_monotonic >= g.open_monotonic
    assert g.duration_s is not None and g.duration_s >= 0
    # once-per-run anchor present and atomic-pair shaped.
    assert ledger.run_wall_anchor and ledger.run_monotonic_anchor > 0
    assert ledger.incomplete == [], "a resumed gap is complete, not an integrity deficit"


@pytest.mark.asyncio
async def test_checksum_resync_gap_recorded():
    """CAUSE 2: a single checksum failure -> CHECKSUM_RESYNC gap on the SAME socket (no
    reconnect, so retry_ladder is empty) -> closed by the fresh snapshot."""
    adapter = _live_adapter()
    adapter._heartbeat_absence_timeout = 100.0
    adapter._app_ping_interval = 100.0

    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, _corrupted_update(), SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])

    emitted = []
    with patch("websockets.connect", factory.connect):
        async for state in adapter.get_live_market_data(duration_seconds=0.25):
            emitted.append(state)

    assert factory.connect_count == 1, "a single checksum failure resyncs on the SAME socket"
    ledger = adapter.get_gap_ledger()
    assert ledger.gaps_detected == 1
    g = ledger.gaps[0]
    _assert_core_fields(g)
    assert g.cause == "CHECKSUM_RESYNC" and g.reason_code == "CHECKSUM_RESYNC"
    assert g.resumed is True and g.terminal is False
    assert g.retry_ladder == [], "a same-socket resync has no reconnect ladder"
    assert g.close_monotonic is not None


@pytest.mark.asyncio
async def test_breaker_retry_ladder_recorded_on_reconnect_gap():
    """CAUSE 3: BREAKER_RETRY_LADDER manifests as the retry_ladder FIELD (§1.1). Two failed
    reopens under backoff -> the triggering gap carries a 2-entry, well-formed ladder."""
    adapter = _live_adapter()
    adapter._heartbeat_absence_timeout = 100.0
    adapter._app_ping_interval = 100.0

    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]  # sync, then 5 real failures
    factory = ScriptedConnectionFactory(
        [socket1, REOPEN_FAILURE, REOPEN_FAILURE, [SNAPSHOT_FRAME]],
        on_drain="heartbeat",
    )

    emitted = []
    with patch("websockets.connect", factory.connect):
        async for state in adapter.get_live_market_data(duration_seconds=0.25):
            emitted.append(state)

    assert factory.failed_attempts == 2, "the reopen failed twice before succeeding"
    ledger = adapter.get_gap_ledger()
    assert ledger.gaps_detected == 1
    g = ledger.gaps[0]
    _assert_core_fields(g)
    # The trigger was the checksum escalation; the reconnect's ladder rides along as a field.
    assert g.cause == "CHECKSUM_RESYNC"
    assert len(g.retry_ladder) == 2, f"the retry ladder records each failed reopen; got {g.retry_ladder}"
    for entry in g.retry_ladder:
        assert {"attempt", "at", "delay_s", "error"} <= set(entry), entry
    assert g.resumed is True, "emission resumed once a retried reopen succeeded"


@pytest.mark.asyncio
async def test_venue_disconnect_gap_recorded(caplog):
    """CAUSE 4c: an UNEXPECTED venue close -> VENUE_DISCONNECT gap routed into reconnect ->
    resumes on the fresh socket."""
    adapter = _live_adapter()
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])

    emitted = []
    with caplog.at_level(logging.INFO):
        with patch("websockets.connect", factory.connect):
            async for state in adapter.get_live_market_data(duration_seconds=0.25):
                emitted.append(state)

    assert factory.connect_count == 2, "an unexpected close reconnects"
    ledger = adapter.get_gap_ledger()
    assert ledger.gaps_detected == 1
    g = ledger.gaps[0]
    _assert_core_fields(g)
    assert g.cause == "VENUE_DISCONNECT" and g.reason_code == "VENUE_CONNECTION_CLOSED"
    assert g.resumed is True and g.terminal is False
    assert g.close_monotonic is not None


@pytest.mark.asyncio
async def test_terminal_venue_disconnect_breaker_gap_recorded():
    """CAUSE 4a: a venue close whose reopen never succeeds -> the breaker trips -> the
    VENUE_DISCONNECT gap is TERMINAL: never closes (+inf, default-deny), carries the retry
    ladder, and is COMPLETE (a known open-ended gap, not an integrity deficit)."""
    adapter = _live_adapter()
    adapter._reconnect_sleep = None                 # real tiny sleeps so the DURATION breaker advances
    adapter._reconnect_max_failure_seconds = 0.1
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    factory = ScriptedConnectionFactory(
        [{"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"}] + [REOPEN_FAILURE] * 20,
    )

    emitted = []
    with patch("websockets.connect", factory.connect):
        with pytest.raises(CircuitBreakerTripped):
            async for state in adapter.get_live_market_data(duration_seconds=30):
                emitted.append(state)

    ledger = adapter.get_gap_ledger()
    assert ledger.gaps_detected == 1
    g = ledger.gaps[0]
    _assert_core_fields(g)
    assert g.cause == "VENUE_DISCONNECT"
    assert g.terminal is True, "a breaker trip is a terminal gap"
    assert g.reason_code == "RECONNECT_CIRCUIT_BREAKER_TRIPPED"
    assert g.close_monotonic is None, "a terminal gap never closes (+inf => default-deny)"
    assert g.resumed is False
    assert g.duration_s is None, "an open-ended gap has no closed duration"
    assert len(g.retry_ladder) >= 2, "the terminal record carries the retry ladder forensic tail"
    assert g.complete is True, "a terminal gap is COMPLETE (known open-ended), not incomplete"
    assert ledger.incomplete == [], "a terminal gap is not a ledger-integrity deficit"
    assert adapter.capture_terminated is not None


@pytest.mark.asyncio
async def test_overlapping_gaps_union_and_collective_close():
    """PROBE 1: a CHECKSUM_RESYNC gap is open when a VENUE_DISCONNECT occurs -> TWO records,
    distinguished per-occurrence (gap_id), their no-emission windows OVERLAP (gaps are NOT
    disjoint — the union query, not containment, is what the reader needs), and BOTH close at
    the SAME instant (collective close — a child cannot close while its parent stays open)."""
    adapter = _live_adapter()
    adapter._heartbeat_absence_timeout = 100.0
    adapter._app_ping_interval = 100.0
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)

    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, _corrupted_update(), unexpected], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])

    emitted = []
    with patch("websockets.connect", factory.connect):
        async for state in adapter.get_live_market_data(duration_seconds=0.25):
            emitted.append(state)

    ledger = adapter.get_gap_ledger()
    assert ledger.gaps_detected == 2, f"two overlapping gaps; got {ledger.gaps_detected}"
    checksum_gap, venue_gap = ledger.gaps[0], ledger.gaps[1]
    assert checksum_gap.cause == "CHECKSUM_RESYNC"
    assert venue_gap.cause == "VENUE_DISCONNECT"
    # per-occurrence identity.
    assert checksum_gap.gap_id != venue_gap.gap_id
    # COLLECTIVE CLOSE: both resumed at the SAME instant (probe-1: a child cannot close while
    # its parent stays open, because close == global emission resume).
    assert checksum_gap.resumed and venue_gap.resumed
    assert checksum_gap.close_monotonic == venue_gap.close_monotonic
    close = checksum_gap.close_monotonic
    # OVERLAP (not disjoint): both windows are open together — max(opens) < the shared close,
    # so [t0,t1] queries in that span intersect BOTH via the union test.
    assert max(checksum_gap.open_monotonic, venue_gap.open_monotonic) < close
    assert ledger.incomplete == []


@pytest.mark.asyncio
async def test_ledger_reports_incomplete_gap(caplog):
    """LEDGER COMPLETENESS: a checksum gap that opens but whose capture ENDS before a fresh
    snapshot validates is DETECTED-but-uncompleted. It is retained (open-ended, default-deny)
    and reported loudly as GAP_LEDGER_INCOMPLETE — never silently dropped."""
    adapter = _live_adapter()
    adapter._heartbeat_absence_timeout = 100.0   # do NOT let absence reconnect and close it
    adapter._app_ping_interval = 100.0

    # SNAPSHOT emits; the corrupted update opens a checksum gap; then the link goes silent and
    # the capture reaches its deadline with the gap still open.
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, _corrupted_update()], "on_drain": "block"},
    ])

    emitted = []
    with caplog.at_level(logging.INFO):
        with patch("websockets.connect", factory.connect):
            async for state in adapter.get_live_market_data(duration_seconds=0.15):
                emitted.append(state)

    ledger = adapter.get_gap_ledger()
    assert ledger.gaps_detected == 1
    g = ledger.gaps[0]
    assert g.cause == "CHECKSUM_RESYNC"
    assert g.resumed is False and g.terminal is False
    assert g.close_monotonic is None, "the gap never closed (open-ended => default-deny)"
    assert g.complete is False
    assert len(ledger.incomplete) == 1, "the ledger reports the uncompleted gap, not drops it"
    assert "GAP_LEDGER_INCOMPLETE" in caplog.text, "the deficit is reported loudly at capture end"
