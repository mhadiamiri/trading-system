"""
WO-023 §5 — the CLOCK/TRANSPORT PRE-CONNECTION GATE bite proof (RULINGS D34-2, D34-3; D37).

ONE test, THREE assertions — the gate's refusal half AND its two preservation halves in the same
place (S13/D37: a guard that only refuses passes its refusal half and looks correct):

  1. REFUSAL       — a real transport (default connect_fn) + a fake clock refuses with
                     CLOCK_INJECTION_REFUSED, BEFORE any connection (the connect callable is never
                     invoked). This is the ruled invariant: a non-default clock is permitted ONLY
                     where the transport is also non-default.
  2. PRESERVATION  — a fake transport + the COHERENT fake-clock pair PROCEEDS (connects, emits).
  3. THE EXCEPTION'S OWN DUAL — the identical INCOHERENT injection (fake wall / real monotonic):
                     passed WITH incoherent_clocks_allowed → PROCEEDS; passed WITHOUT it → REFUSES.
                     This is what keeps the suspend-detector escape hatch (RULING D34-3) from
                     becoming a hole: the hatch opens only when it is named.

NO NETWORK — the transport is the simulated ScriptedConnectionFactory; the clocks are the coherent
FakeClock / the named incoherent_clock_pair from the harness (WO-023 §3). The pre-connection cases
patch websockets.connect with a spy factory purely to PROVE the connect callable is never called.
"""

import pytest
from unittest.mock import patch
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedOK

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import (
    ScriptedConnectionFactory, FakeClock, incoherent_clock_pair,
)

MODE_LIVE = KrakenV2BookAdapter.MODE_LIVE
_CLEAN_CLOSE = ConnectionClosedOK(Close(1000, "normal closure"), None)


def _proceeding_factory():
    """A socket that emits the snapshot then closes CLEANLY — so a PROCEEDING capture terminates
    deterministically without leaning on the (frozen) fake deadline clock."""
    return ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, _CLEAN_CLOSE], "on_drain": "block"},
    ])


@pytest.mark.asyncio
async def test_clock_injection_gate():
    # ── 1. REFUSAL — real transport (default connect_fn) + a fake clock. ─────────────────────────
    # Even a WELL-FORMED coherent fake pair refuses when the transport is the real one: a fake clock
    # must never drive a live websockets socket. Proven pre-connection: the connect spy is untouched.
    fc = FakeClock()
    refuse_adapter = KrakenV2BookAdapter(mode=MODE_LIVE, monotonic_clock=fc.monotonic)  # connect_fn default
    refuse_adapter._persistence_optional = True
    refuse_adapter._wall_clock = fc.wall
    # A SELF-TERMINATING spy (snapshot then clean close): the gate MUST refuse pre-connection, but
    # if it ever failed to, this script ends the capture at once rather than spinning on the frozen
    # fake deadline clock — so the assertion fails FAST ("did not raise"), never hangs. The
    # pre-connection guarantee is carried by connect_count == 0, not by the script.
    spy = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME, _CLEAN_CLOSE], "on_drain": "block"}])
    with patch("websockets.connect", spy.connect):
        with pytest.raises(ValueError, match="CLOCK_INJECTION_REFUSED") as exc1:
            async for _ in refuse_adapter.get_live_market_data(duration_seconds=0.1):
                pass
    assert "COUPLING" in str(exc1.value), "the payload names WHICH assertion failed (coupling)"
    assert spy.connect_count == 0, "REFUSED PRE-CONNECTION — the connect callable was never invoked"

    # ── 2. PRESERVATION — fake transport + the COHERENT fake-clock pair PROCEEDS. ─────────────────
    fc2 = FakeClock()
    factory = _proceeding_factory()
    ok_adapter = KrakenV2BookAdapter(
        mode=MODE_LIVE, monotonic_clock=fc2.monotonic, connect_fn=factory.connect)
    ok_adapter._persistence_optional = True
    ok_adapter._wall_clock = fc2.wall
    ok_adapter._heartbeat_absence_timeout = 100.0
    ok_adapter._app_ping_interval = 100.0
    emitted = []
    async for state in ok_adapter.get_live_market_data(duration_seconds=0.25):
        emitted.append(state)
    assert factory.connect_count >= 1, "PROCEEDED past the gate and opened the injected transport"
    assert len(emitted) >= 1, "PROCEEDED — the snapshot priced (the gate did not refuse a valid pair)"

    # ── 3. THE EXCEPTION'S OWN DUAL — identical INCOHERENT injection, named vs unnamed. ───────────
    # 3a. WITH the named exception → PROCEEDS.
    wall_a, mono_a = incoherent_clock_pair()          # fake wall / real monotonic (the suspend shape)
    factory_a = _proceeding_factory()
    allowed = KrakenV2BookAdapter(mode=MODE_LIVE, monotonic_clock=mono_a, connect_fn=factory_a.connect)
    allowed._persistence_optional = True
    allowed._wall_clock = wall_a
    allowed._heartbeat_absence_timeout = 100.0
    allowed._app_ping_interval = 100.0
    emitted_a = []
    async for state in allowed.get_live_market_data(
            duration_seconds=0.25, incoherent_clocks_allowed="suspend-detector-test"):
        emitted_a.append(state)
    assert factory_a.connect_count >= 1, "the NAMED incoherent run PROCEEDS (the hatch opens by name)"

    # 3b. WITHOUT it — the IDENTICAL injection → REFUSES, pre-connection. This is the half that keeps
    # the hatch from being a hole: an incoherent pair that forgets to declare itself is refused.
    wall_b, mono_b = incoherent_clock_pair()
    factory_b = _proceeding_factory()
    forgot = KrakenV2BookAdapter(mode=MODE_LIVE, monotonic_clock=mono_b, connect_fn=factory_b.connect)
    forgot._persistence_optional = True
    forgot._wall_clock = wall_b
    forgot._heartbeat_absence_timeout = 100.0
    forgot._app_ping_interval = 100.0
    with pytest.raises(ValueError, match="CLOCK_INJECTION_REFUSED") as exc3:
        async for _ in forgot.get_live_market_data(duration_seconds=0.25):
            pass
    assert "COHERENCE" in str(exc3.value), "the payload names WHICH assertion failed (coherence)"
    assert factory_b.connect_count == 0, "the UNNAMED incoherent run REFUSES PRE-CONNECTION"
