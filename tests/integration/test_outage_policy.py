"""
WO-044 §4 — THE LONG-OUTAGE POLICY (D45 ruling 2: X = 15 minutes).

WHY 15 AND NOT 10. This is the first value of RECONNECT_MAX_FAILURE_SECONDS chosen against an
OBSERVED failure rather than derived from documented silence. Corpus run `20260729190849` died on
the old T=600s: a local link outage ("[WinError 64] The specified network name is no longer
available", then repeated handshake timeouts) ran 20:49:30Z -> 20:59:41Z with 23 logged reopen
attempts, and the breaker tripped at 600s — ending a healthy 1h51m capture that had already banked
462,155 frames. The venue was not gone; the host's link was briefly down. 600s was measured to be
too tight by roughly one attempt.

THE THREE CASES (§4.4):
  (a) outage UNDER X  -> ONE gap record with its TRUE duration, retries in the forensic tail,
                          run CONTINUES
  (b) outage OVER X   -> breaker STOPs with the standard forensic tail
  (c) suspend DURING an outage -> windows still VOID (§4.3: the detector and the outage window are
                          INDEPENDENT — network patience must never launder clock divergence)

Case (c) is the one that matters most. Widening what the breaker tolerates makes long outages
ordinary; if a host suspend inside one of those windows stopped being detected, the corpus would
quietly relabel "the machine was asleep" as "we were patiently waiting", and every affected window
would be silently trusted instead of VOIDed under D24.

HONEST FIXTURE LIMIT (rule 0.1f): simulated transport throughout, and the breaker's T is scaled
down so a proof runs in milliseconds. What is proved is the POLICY SHAPE — one record, true
duration, tail retained, independence — not Kraken's real reopen behaviour at 15 minutes.

NO NETWORK. websockets.connect is replaced wholesale.
"""

import copy
import logging

import pytest

from trading.data.adapters.kraken_v2_book import (
    KrakenV2BookAdapter, CircuitBreakerTripped, GAP_CAUSES,
)
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import (
    AdvancingClock, ScriptedConnectionFactory, REOPEN_FAILURE,
)


async def _no_sleep(_delay):
    """Collapse backoff waits: the delay VALUE is still computed and recorded in the ladder;
    only the real wait is skipped."""
    return None


def _bad_snapshot():
    bad = copy.deepcopy(SNAPSHOT_FRAME)
    bad["data"][0]["checksum"] = 1        # never valid for this ladder -> drives a real reconnect
    return bad


def _live_adapter(connect_fn=None):
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=connect_fn)
    adapter._persistence_optional = True
    adapter._reconnect_sleep = _no_sleep
    adapter._reconnect_jitter = lambda: 1.0
    adapter._reconnect_backoff_base = 0.01
    adapter._reconnect_backoff_cap = 0.04
    return adapter


# ── the ruled value ───────────────────────────────────────────────────────────────────────────

def test_the_outage_window_is_fifteen_minutes():
    """D45 ruling 2, as a number the code actually carries."""
    assert KrakenV2BookAdapter.RECONNECT_MAX_FAILURE_SECONDS == 900.0
    assert KrakenV2BookAdapter.RECONNECT_MAX_FAILURE_SECONDS == 15 * 60


def test_the_old_ten_minute_window_would_have_killed_run_two():
    """The measured justification, pinned as arithmetic rather than left in prose.

    Run 20260729190849's outage ran 20:49:30Z -> 20:59:41Z = 611s of continuous retry. Under the
    old T it tripped; under the ruled T it would have been tolerated and the run would have
    continued into its third hour.
    """
    observed_outage_seconds = 611.0
    assert observed_outage_seconds > 600.0, "the old window tripped on this real outage"
    assert observed_outage_seconds < KrakenV2BookAdapter.RECONNECT_MAX_FAILURE_SECONDS, (
        "the ruled 15-minute window tolerates the outage that actually killed run 2"
    )


# ── (a) an outage UNDER X: one record, true duration, run continues ───────────────────────────

@pytest.mark.asyncio
async def test_outage_under_the_window_is_one_gap_record_and_the_run_continues():
    """Reopen fails twice, then succeeds — ONE gap record, retries in its tail, no termination."""
    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    socket2 = [SNAPSHOT_FRAME]
    factory = ScriptedConnectionFactory([socket1, REOPEN_FAILURE, REOPEN_FAILURE, socket2])

    clk = AdvancingClock(delta=0.1 / 50)
    adapter = _live_adapter(connect_fn=factory.connect)
    adapter._monotonic_clock = clk.monotonic
    adapter._wall_clock = clk.wall

    emitted = []
    async for state in adapter.get_live_market_data(duration_seconds=0.1):
        emitted.append(state)

    ledger = adapter.get_gap_ledger()

    # ONE record for the whole outage — not one per retry (§4.1).
    assert len(ledger.gaps) == 1, (
        f"a sustained outage is ONE gap record, not one per attempt; got "
        f"{[(g.cause, g.reason_code) for g in ledger.gaps]}"
    )
    gap = ledger.gaps[0]
    assert gap.cause in GAP_CAUSES

    # TRUE duration, measured and closed — the run recovered.
    assert gap.resumed is True and gap.terminal is False
    assert gap.duration_s is not None and gap.duration_s >= 0.0

    # The retry ladder rides along as the forensic detail (D-r10 machinery unchanged).
    assert len(gap.retry_ladder) == 2, f"both failed attempts in the tail; got {gap.retry_ladder}"
    for entry in gap.retry_ladder:
        assert {"attempt", "at", "delay_s", "error"} <= set(entry), entry

    # The run CONTINUED: emission resumed, breaker never judged, ledger has no deficit.
    assert adapter.capture_terminated is None, "an outage under X must not terminate the run"
    assert adapter._awaiting_resync is False
    assert len(emitted) == 2, f"emission resumed after the outage; got {len(emitted)}"
    assert ledger.incomplete == []


# ── (b) an outage OVER X: breaker STOPs with the forensic tail ────────────────────────────────

@pytest.mark.asyncio
async def test_outage_past_the_window_trips_the_breaker_with_the_forensic_tail():
    """Past X the breaker STOPs — loud, with the standard tail, partial capture retained.

    T is scaled to 0.1s so the proof is fast; the BRANCH is the shipped one (the same
    `elapsed > self._reconnect_max_failure_seconds` comparison the 900s constant feeds).
    """
    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    factory = ScriptedConnectionFactory([socket1] + [REOPEN_FAILURE] * 20)

    adapter = _live_adapter(connect_fn=factory.connect)
    adapter._reconnect_sleep = None                 # real (tiny) sleeps so the streak clock advances
    adapter._reconnect_max_failure_seconds = 0.1

    with pytest.raises(CircuitBreakerTripped) as exc_info:
        async for _ in adapter.get_live_market_data(duration_seconds=30):
            pass

    exc = exc_info.value
    assert "RECONNECT_CIRCUIT_BREAKER_TRIPPED" in str(exc)

    # The breaker remains the SOLE run-terminator, and it still carries the full tail (§4.2).
    assert exc.trip_time is not None
    assert len(exc.reconnect_ladder) >= 2
    assert exc.last_validated_book is not None
    term = adapter.capture_terminated
    assert term["reason_code"] == "RECONNECT_CIRCUIT_BREAKER_TRIPPED"
    assert "TRUNCATED-HONEST WINDOW" in term["evidentiary_bounds"]

    # The gap that was open at the trip is TERMINAL, never silently closed.
    ledger = adapter.get_gap_ledger()
    terminal = [g for g in ledger.gaps if g.terminal]
    assert terminal, "the trip must mark the open gap terminal"
    assert terminal[0].close_monotonic is None, (
        "a terminal gap stays open-ended (+infinity) so a default-deny reader denies from open on"
    )
    assert terminal[0].retry_ladder, "the ladder is preserved on the terminal record"
    # A terminal gap is COMPLETE (a known open-ended gap), not a ledger deficit.
    assert ledger.incomplete == []


# ── (c) §4.3 INDEPENDENCE: a suspend DURING an outage still VOIDs ─────────────────────────────

class _JumpClock:
    """A wall clock that advances slightly per call, then JUMPS once — a suspend's signature."""

    def __init__(self, base=1_000_000.0, jump_at_call=3, jump_by=120.0):
        self.base = base
        self.calls = 0
        self.jump_at_call = jump_at_call
        self.jump_by = jump_by
        self.offset = 0.0

    def __call__(self):
        self.calls += 1
        if self.calls == self.jump_at_call:
            self.offset += self.jump_by
        return self.base + self.calls * 0.001 + self.offset


@pytest.mark.asyncio
async def test_a_suspend_during_an_outage_still_voids(caplog):
    """§4.3 — the suspend detector and the outage window are INDEPENDENT.

    The host suspends WHILE the transport is riding out a venue outage inside the tolerated window.
    The outage is recorded as its own gap AND the suspend is recorded as its own HOST_SUSPEND gap.
    Network patience does not extend to clock divergence: widening T must never turn "the machine
    was asleep" into "we were waiting", because the affected windows would then be trusted instead
    of VOIDed under D24.

    Uses the SOLE enumerated incoherent clock construction (D34-3) — a fake wall that jumps against
    the real monotonic — declared BY NAME, exactly as test_host_suspend_recorded does. The
    divergence IS the thing under test, so a coherent pair could not manufacture it.
    """
    # Socket 1 syncs, then 5 real checksum failures drive a reconnect; the reopen fails once
    # (an outage INSIDE the tolerated window) before socket 2 succeeds. The wall clock jumps
    # while all this is happening.
    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    socket2 = {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}
    factory = ScriptedConnectionFactory([socket1, REOPEN_FAILURE, socket2])

    adapter = _live_adapter(connect_fn=factory.connect)
    adapter._heartbeat_absence_timeout = 100.0     # a quiet-but-live link stays up
    adapter._app_ping_interval = 100.0
    # T is generous here ON PURPOSE: the outage must sit INSIDE the tolerated window, so the only
    # thing that can produce a VOID verdict is the suspend detector acting independently.
    adapter._reconnect_max_failure_seconds = 900.0
    adapter._wall_clock = _JumpClock(jump_at_call=3, jump_by=120.0)   # 120s >> the 43s bound

    with caplog.at_level(logging.ERROR):
        async for _ in adapter.get_live_market_data(
                duration_seconds=0.3, incoherent_clocks_allowed="suspend-during-outage-test"):
            pass

    ledger = adapter.get_gap_ledger()
    causes = [g.cause for g in ledger.gaps]

    # THE INDEPENDENCE: the suspend is detected even though the outage was inside the window.
    suspends = [g for g in ledger.gaps if g.cause == "HOST_SUSPEND"]
    assert len(suspends) >= 1, (
        f"a host suspend during a tolerated outage MUST still be detected and VOID the affected "
        f"windows — network patience does not extend to clock divergence. Gap causes seen: {causes}"
    )
    assert suspends[0].reason_code == "HOST_SUSPEND"
    assert "divergence" in suspends[0].detail
    assert "HOST_SUSPEND" in caplog.text, "the suspend must be reported loudly"

    # And it is a SEPARATE record from the outage — one cause never absorbs the other.
    outage_gaps = [g for g in ledger.gaps if g.cause != "HOST_SUSPEND"]
    assert outage_gaps, f"the outage must keep its own record; causes seen: {causes}"

    # The suspend stays DIAGNOSTIC (it VOIDs windows; the breaker still owns termination).
    assert suspends[0].terminal is False
    assert adapter.capture_terminated is None


@pytest.mark.asyncio
async def test_no_suspend_recorded_when_only_the_network_is_out():
    """The preservation dual of the independence proof.

    An outage with COHERENT clocks records the outage and NOTHING ELSE. Without this half, the
    test above could pass on a detector that fired on every reconnect — which would VOID honest
    windows and be just as wrong in the other direction.
    """
    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    factory = ScriptedConnectionFactory([socket1, REOPEN_FAILURE, [SNAPSHOT_FRAME]])

    clk = AdvancingClock(delta=0.1 / 50)          # ONE source: wall and monotonic never diverge
    adapter = _live_adapter(connect_fn=factory.connect)
    adapter._monotonic_clock = clk.monotonic
    adapter._wall_clock = clk.wall

    async for _ in adapter.get_live_market_data(duration_seconds=0.1):
        pass

    ledger = adapter.get_gap_ledger()
    assert [g for g in ledger.gaps if g.cause == "HOST_SUSPEND"] == [], (
        "a pure network outage must NOT be recorded as a host suspend"
    )
    assert ledger.gaps, "the outage itself is still recorded"
