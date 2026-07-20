"""
WO-014b-2 §2 — reconnect BACKOFF + CIRCUIT BREAKER, both paths proven to effect (0.1i).

§0 recorded two production hazards on the reconnect path (evidence/WO-014b-2/
carryover_verification.txt):
  - a FAILED reopen raised ConnectionError that propagated and ENDED the capture — a
    24-hour corpus dying on one transient blip;
  - (with keepalive) a reconnect storm with zero delay.

§2 fixes both: a failed reopen RETRIES under full-jitter exponential backoff, and a
circuit breaker STOPS the run loudly (reason code + forensic tail) when reopen attempts
exceed the threshold — never a silent gap (Ruling B).

These proofs drive the PRODUCTION reconnect trigger (5 real checksum failures) and assert
the OBSERVABLE END STATE, not a retry counter:
  (a) transient: reopen fails, backoff retries, reopen succeeds -> EMISSION RESUMES.
  (b) persistent: reopen keeps failing -> breaker TRIPS -> loud CircuitBreakerTripped
      carrying the forensic tail, with the partial capture retained and labeled.

HONEST FIXTURE LIMIT: simulated transport (tests/fixtures/fake_ws_transport.py). Only the
isolated live re-run confirms Kraken's real reopen behavior and rate tolerance.

NO NETWORK. websockets.connect is replaced wholesale.
"""

import copy

import pytest
from unittest.mock import patch

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, CircuitBreakerTripped
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory, REOPEN_FAILURE


async def _no_sleep(_delay):
    """Collapse backoff waits so the proof is fast and deterministic (the delay VALUE is
    still computed and recorded in the ladder; only the real wait is skipped)."""
    return None


def _bad_snapshot():
    bad = copy.deepcopy(SNAPSHOT_FRAME)
    bad["data"][0]["checksum"] = 1  # never valid for this ladder
    return bad


def _live_adapter():
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._reconnect_sleep = _no_sleep         # no real backoff waits
    adapter._reconnect_jitter = lambda: 1.0      # deterministic ladder delays
    adapter._reconnect_backoff_base = 0.01
    adapter._reconnect_backoff_cap = 0.04
    return adapter


@pytest.mark.asyncio
async def test_transient_reopen_failure_retries_under_backoff_then_emission_resumes():
    """(a) Two reopen failures -> backoff retries -> third reopen succeeds -> emission resumes."""
    adapter = _live_adapter()

    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]  # sync, then 5 real failures
    socket2 = [SNAPSHOT_FRAME]                                        # the reopen that succeeds
    # connect #1 = socket1 (initial); #2,#3 = refused reopens; #4 = socket2.
    factory = ScriptedConnectionFactory([socket1, REOPEN_FAILURE, REOPEN_FAILURE, socket2])

    # Short window: under keepalive a silent link reconnects rather than ending the run, so
    # the capture ends at its deadline (well under the default ping/absence thresholds).
    emitted = []
    with patch("websockets.connect", factory.connect):
        async for state in adapter.get_live_market_data(duration_seconds=0.1):
            emitted.append(state)

    # END STATE: emission resumed after the retried reconnect (not "retry was attempted").
    assert len(emitted) == 2, (
        f"emission must resume once a retried reopen succeeds; got {len(emitted)} states"
    )
    assert adapter._awaiting_resync is False
    assert adapter.capture_terminated is None, "the breaker must NOT trip on a transient failure"
    # The reopen actually failed twice and then succeeded — observable in the transport.
    assert factory.failed_attempts == 2
    assert factory.connect_count == 4, "initial + 2 failed reopens + 1 successful reopen"
    assert len(adapter._reconnect_ladder) == 2, "forensic ladder records each failed attempt"


@pytest.mark.asyncio
async def test_persistent_reopen_failure_trips_breaker_loud_with_forensic_tail():
    """(b) Reopen keeps failing -> circuit breaker trips -> loud failure + forensic tail + retained capture."""
    adapter = _live_adapter()
    # The DURATION breaker trips on elapsed WALL-CLOCK, so this proof uses REAL (tiny) backoff
    # sleeps (not the no-op) and a small T: the streak crosses T=0.1s after a few ~0.01-0.04s
    # retries. Deterministic jitter (1.0, from _live_adapter) makes the ladder reproducible.
    adapter._reconnect_sleep = None            # real asyncio.sleep so wall-clock advances
    adapter._reconnect_max_failure_seconds = 0.1

    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    # connect #1 = socket1; the rest are refused reopens. The breaker trips on TIME, not
    # count, before exhausting these — plenty of failures so the trip, not the factory, ends it.
    factory = ScriptedConnectionFactory([socket1] + [REOPEN_FAILURE] * 20)

    emitted = []
    with patch("websockets.connect", factory.connect):
        with pytest.raises(CircuitBreakerTripped) as exc_info:
            async for state in adapter.get_live_market_data(duration_seconds=30):
                emitted.append(state)

    exc = exc_info.value

    # LOUD failure carrying the declared reason code.
    assert "RECONNECT_CIRCUIT_BREAKER_TRIPPED" in str(exc)

    # FORENSIC TAIL (Ruling 2B condition 1): trip time, full retry ladder, last good book.
    assert exc.trip_time is not None
    assert len(exc.reconnect_ladder) >= 2, "the retry ladder records the failed attempts"
    for entry in exc.reconnect_ladder:
        assert {"attempt", "at", "delay_s", "error"} <= set(entry), entry
    assert exc.last_validated_book is not None
    assert exc.last_validated_book["best_bid"], "the last checksum-good top-of-book is recorded"

    # RETAINED + LABELED partial capture (Ruling 2B condition 2; two-window doctrine).
    assert adapter.capture_terminated is not None
    term = adapter.capture_terminated
    assert term["reason_code"] == "RECONNECT_CIRCUIT_BREAKER_TRIPPED"
    assert term["frames_captured"] > 0
    assert "TRUNCATED-HONEST WINDOW" in term["evidentiary_bounds"]
    assert len(adapter.captured_raw_text) > 0, "the partial capture is retained, not discarded"

    # It STOPPED (Ruling B) — the initial sync emitted, but no silent continuation after.
    assert factory.failed_attempts >= 2, "reopen failed repeatedly before the breaker tripped"
