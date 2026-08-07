"""
WO-045 §3 (D46) — THE TERMINATION LOG LEVEL.

Ratified doctrine (docs/decisions/2026-08-07-the-line-that-says-why-it-ended.md), verbatim:

    For unattended runs, any message that explains a TERMINATION logs at WARNING or above.
    The line that says why it ended must never be the line that gets dropped.

WHY. WO-044's corpus run `20260805220327` ended at 12.9 h, not at its 24 h deadline. The reason —
a clean venue close — was logged at INFO, and a detached run captures WARNING and above, so the one
line explaining the termination existed in NO log. The cause had to be reconstructed by ELIMINATION
over the loop's three exits. That reconstruction was sound but it should never have been necessary.

§3.2 ENUMERATION then found something worse than the reported defect: the DEADLINE exit — the
ordinary planned end of every bounded capture, and the exit that ended run `20260806130401` —
logged NOTHING AT ALL. "Enumerate, don't fix the one you found."

NO NETWORK. Scripted transport throughout.
"""

import logging

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from trading.logkit.decision import VALID_REASON_CODES
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import AdvancingClock, ScriptedConnectionFactory


WARNING_AND_ABOVE = logging.WARNING


def _live_adapter(connect_fn):
    a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=connect_fn)
    a._persistence_optional = True
    return a


def _survives_a_warning_filter(caplog):
    """The records an unattended run would actually keep — WARNING and above, nothing else."""
    return [r for r in caplog.records if r.levelno >= WARNING_AND_ABOVE]


# ── the vocabulary ────────────────────────────────────────────────────────────────────────────

def test_the_termination_causes_are_declared():
    """Termination causes are first-class governed vocabulary, not free text in a log line."""
    declared = set(VALID_REASON_CODES["DATA"])
    for code in ("CAPTURE_ENDED_DEADLINE", "CAPTURE_ENDED_CLEAN_VENUE_CLOSE",
                 "CAPTURE_ENDED_UNDECLARED"):
        assert code in declared, f"{code} must be declared"


# ── path 1: the DEADLINE (logged NOTHING before this WO) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_deadline_termination_survives_a_warning_filter(caplog):
    """The ordinary planned end. Before WO-045 this path emitted no log line at all."""
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])
    clk = AdvancingClock(delta=0.15 / 50)
    a = _live_adapter(factory.connect)
    a._monotonic_clock = clk.monotonic
    a._wall_clock = clk.wall

    with caplog.at_level(logging.DEBUG):
        async for _ in a.get_live_market_data(duration_seconds=0.15):
            pass

    kept = _survives_a_warning_filter(caplog)
    msgs = [r.getMessage() for r in kept]
    assert any("CAPTURE ENDED" in m for m in msgs), (
        f"a termination line must survive a WARNING filter; kept: {msgs}"
    )
    assert any("CAPTURE_ENDED_DEADLINE" in m for m in msgs), (
        f"the deadline termination must name its declared cause; kept: {msgs}"
    )


# ── path 2: the CLEAN VENUE CLOSE (was logger.INFO — the reported finding) ────────────────────

@pytest.mark.asyncio
async def test_clean_venue_close_termination_survives_a_warning_filter(caplog):
    """THE FINDING. A normal-closure venue close ends the capture without reconnect; its reason was
    at INFO and vanished from run 20260805220327's logs entirely."""
    from websockets.exceptions import ConnectionClosedOK
    from websockets.frames import Close

    closed = ConnectionClosedOK(Close(1000, "normal closure"), None)
    factory = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME, closed]}])
    clk = AdvancingClock(delta=0.2 / 200)
    a = _live_adapter(factory.connect)
    a._monotonic_clock = clk.monotonic
    a._wall_clock = clk.wall

    with caplog.at_level(logging.DEBUG):
        async for _ in a.get_live_market_data(duration_seconds=0.2):
            pass

    kept = _survives_a_warning_filter(caplog)
    msgs = [r.getMessage() for r in kept]
    assert any("CAPTURE_ENDED_CLEAN_VENUE_CLOSE" in m for m in msgs), (
        f"the clean-close reason must survive a WARNING filter; kept: {msgs}"
    )
    # And it says what it did about reconnecting — the substantive fact a reader needs.
    line = next(m for m in msgs if "CAPTURE_ENDED_CLEAN_VENUE_CLOSE" in m)
    assert "WITHOUT reconnect" in line


# ── the preservation dual: the line is not merely present, it is INFORMATIVE ──────────────────

@pytest.mark.asyncio
async def test_the_termination_line_carries_the_run_s_reach(caplog):
    """DUAL. A termination line that says only "ended" would satisfy a level check and still leave
    the reader guessing. It must carry the counters that say how far the run got."""
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])
    clk = AdvancingClock(delta=0.15 / 50)
    a = _live_adapter(factory.connect)
    a._monotonic_clock = clk.monotonic
    a._wall_clock = clk.wall

    with caplog.at_level(logging.DEBUG):
        async for _ in a.get_live_market_data(duration_seconds=0.15):
            pass

    line = next(r.getMessage() for r in _survives_a_warning_filter(caplog)
                if "CAPTURE ENDED" in r.getMessage())
    assert "frames received" in line and "states emitted" in line, line


# ── the sentinel: an exit that declares nothing is LOUD, not silent ───────────────────────────

def test_the_undeclared_sentinel_exists_and_is_declared():
    """A future `break` that forgets to set a reason reports CAPTURE_ENDED_UNDECLARED rather than
    ending the capture in silence — loud by construction, which is the whole point of centralising
    the termination line instead of logging at each exit."""
    import inspect
    src = inspect.getsource(KrakenV2BookAdapter.get_live_market_data)
    assert "CAPTURE_ENDED_UNDECLARED" in src
    assert "termination_reason = None" in src, (
        "the reason must default to unset so a forgetful exit trips the sentinel"
    )
    assert "CAPTURE_ENDED_UNDECLARED" in set(VALID_REASON_CODES["DATA"])
