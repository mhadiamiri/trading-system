"""
WO-023 §5 (+ §2b) — the CLOCK/TRANSPORT PRE-CONNECTION GATE bite proof (RULINGS D34-2, D34-3; D37).

ONE test, FIVE assertions — the gate's refusal halves AND its preservation halves in the same place
(S13/D37: a guard that only refuses passes its refusal half and looks correct):

  1. UNCONFIGURED-REAL REFUSAL — the DEFAULT (unconfigured) transport resolves to the REAL callable;
                     with a fake clock it refuses CLOCK_INJECTION_REFUSED: COUPLING, pre-connection.
  2. PRESERVATION  — a fake transport + the COHERENT fake-clock pair PROCEEDS (connects, prices).
  3. THE EXCEPTION'S OWN DUAL — the identical INCOHERENT injection (fake wall / real monotonic):
                     WITH incoherent_clocks_allowed → PROCEEDS; WITHOUT → refuses COHERENCE.
  4. EXPLICIT-REAL-TRANSPORT REFUSAL (WO-023 §2b) — connect_fn set EXPLICITLY to the real callable
                     (non-default by CONFIG, REAL by IDENTITY) + a coherent fake clock → refuses
                     COUPLING, pre-connection. This is the case a SENTINEL-keyed gate (`_connect_fn
                     is not None`) let through — a fake clock on a real socket — so it is the
                     assertion that proves the coupling check keys on transport IDENTITY, not on
                     injection status.
  5. DEFAULT-PATH PRESERVATION (WO-023 §2c) — real transport + NO clock injected → PROCEEDS
                     (the transport IS invoked). The coupling branch's preservation dual and the
                     production path: it proves the branch is conditioned on CLOCK INJECTION, not on
                     transport identity alone. The pair with assertion 4 (real+clock refuses;
                     real+no-clock proceeds).

NO NETWORK, NO VENUE CONNECTION. The transport is the simulated ScriptedConnectionFactory. The
REAL-transport cases (1, 4) substitute a SPY for the module's `_REAL_CONNECT` sentinel (via
patch.object): the gate then does its GENUINE identity comparison and refuses the spy, and even a
mutated (proceeding) gate calls the spy — never a genuine Kraken socket. connect_count == 0 proves
pre-connection. This is not "monkeypatching to make the guard pass" (0.2): it makes the guard REFUSE
a safe stand-in for the real transport, which is the only way to exercise "real transport refuses"
without opening a real socket.
"""

import pytest
from unittest.mock import patch
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedOK

import trading.data.adapters.kraken_v2_book as kv2
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import (
    ScriptedConnectionFactory, FakeClock, incoherent_clock_pair,
)

MODE_LIVE = KrakenV2BookAdapter.MODE_LIVE
_CLEAN_CLOSE = ConnectionClosedOK(Close(1000, "normal closure"), None)


def _self_terminating_spy():
    """A socket that emits the snapshot then closes CLEANLY — so a PROCEEDING (or wrongly-proceeding,
    under a mutation) capture terminates at once rather than spinning on the frozen fake deadline
    clock. The refusal cases assert connect_count == 0; the mutation cases fail FAST, never hang."""
    return ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, _CLEAN_CLOSE], "on_drain": "block"},
    ])


@pytest.mark.asyncio
async def test_clock_injection_gate():
    # ── 1. UNCONFIGURED-REAL REFUSAL — default connect_fn resolves to the REAL transport. ─────────
    # The spy stands in for the real callable BY IDENTITY: patch both the module's _REAL_CONNECT
    # sentinel and the live websockets.connect to the SAME spy, so the default resolve
    # (`None or websockets.connect`) equals _REAL_CONNECT and refuses — with no genuine socket.
    fc = FakeClock()
    refuse_adapter = KrakenV2BookAdapter(mode=MODE_LIVE, monotonic_clock=fc.monotonic)  # connect_fn default
    refuse_adapter._persistence_optional = True
    refuse_adapter._wall_clock = fc.wall
    spy = _self_terminating_spy()
    # Capture the bound method ONCE: `spy.connect` yields a NEW bound-method object per access, so
    # the two patches must share the SAME object for the gate's identity comparison to hold. (In
    # production _REAL_CONNECT and websockets.connect are the one module-level function — identical.)
    spy_connect = spy.connect
    with patch.object(kv2, "_REAL_CONNECT", spy_connect), patch("websockets.connect", spy_connect):
        with pytest.raises(ValueError, match="CLOCK_INJECTION_REFUSED") as exc1:
            async for _ in refuse_adapter.get_live_market_data(duration_seconds=0.1):
                pass
    assert "COUPLING" in str(exc1.value), "the payload names WHICH assertion failed (coupling)"
    assert spy.connect_count == 0, "REFUSED PRE-CONNECTION — the connect callable was never invoked"

    # ── 2. PRESERVATION — fake transport + the COHERENT fake-clock pair PROCEEDS. ─────────────────
    fc2 = FakeClock()
    factory = _self_terminating_spy()
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
    factory_a = _self_terminating_spy()
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
    factory_b = _self_terminating_spy()
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

    # ── 4. EXPLICIT-REAL-TRANSPORT REFUSAL (WO-023 §2b) — connect_fn IS the real callable. ─────────
    # connect_fn is set EXPLICITLY to the (spy standing in as) real transport: non-default by CONFIG
    # yet REAL by IDENTITY. A sentinel-keyed gate (_connect_fn is not None) would PASS this and drive
    # a fake clock on a real socket; the identity-keyed gate REFUSES it. The spy is also _REAL_CONNECT,
    # so a wrongly-proceeding (mutated) gate calls the spy, never a genuine socket.
    fc4 = FakeClock()
    spy4 = _self_terminating_spy()
    spy4_connect = spy4.connect          # one bound-method object for BOTH the sentinel and connect_fn
    with patch.object(kv2, "_REAL_CONNECT", spy4_connect):
        real_adapter = KrakenV2BookAdapter(
            mode=MODE_LIVE, monotonic_clock=fc4.monotonic, connect_fn=spy4_connect)
        real_adapter._persistence_optional = True
        real_adapter._wall_clock = fc4.wall
        with pytest.raises(ValueError, match="CLOCK_INJECTION_REFUSED") as exc4:
            async for _ in real_adapter.get_live_market_data(duration_seconds=0.1):
                pass
    assert "COUPLING" in str(exc4.value), "explicit real transport + fake clock refuses on COUPLING"
    assert spy4.connect_count == 0, "REFUSED PRE-CONNECTION — an explicit real transport is caught by identity"

    # ── 5. DEFAULT-PATH PRESERVATION (WO-023 §2c) — the PRODUCTION PATH: real transport, NO clock. ─
    # The INVERSE of assertion 4, and its PAIR: assertion 4 = real transport WITH a clock REFUSES;
    # assertion 5 = real transport WITHOUT a clock PROCEEDS. Together they prove the coupling branch
    # is conditioned on CLOCK INJECTION (the early-return precondition), NOT on transport identity
    # alone — the half that carries the 24-hour corpus capture: a default-constructed adapter (no
    # clock, real transport) MUST start. No test in the prior 216 exercised this (every no-clock test
    # module-patches to a FAKE, so `resolved is not _REAL_CONNECT` and the branch is skipped for a
    # reason unrelated to the precondition). Here the transport resolves to the (spy standing in as)
    # REAL callable by identity, so ONLY the clock-injection precondition keeps the gate from refusing.
    spy5 = _self_terminating_spy()
    spy5_connect = spy5.connect          # one bound-method object shared by both patches (§2b pitfall)
    default_adapter = KrakenV2BookAdapter(mode=MODE_LIVE)   # NO clock injected, connect_fn=None (default)
    default_adapter._persistence_optional = True
    default_adapter._heartbeat_absence_timeout = 100.0
    default_adapter._app_ping_interval = 100.0
    emitted5 = []
    with patch.object(kv2, "_REAL_CONNECT", spy5_connect), patch("websockets.connect", spy5_connect):
        async for state in default_adapter.get_live_market_data(duration_seconds=0.25):
            emitted5.append(state)
    assert spy5.connect_count == 1, "DEFAULT PATH PROCEEDS — the real transport IS invoked (no refusal)"
    assert len(emitted5) >= 1, "the default real run reaches the same successful end state as assertion 2"
