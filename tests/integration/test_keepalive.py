"""
WO-014b-2 §1.1 / §1.2 — KEEPALIVE (heartbeat-absence detection + application ping/pong).

The 742s `1011 keepalive ping timeout` that closed WO-008b-B was a PROTOCOL-level ping
timeout. §1.3 (deliberate protocol ping params + protocol-level bite proof) is the named
checkpoint seam. These two parts add the APPLICATION-layer keepalive that the observed
hour and the documentation both point to:

  §1.1 Heartbeat-absence detection: Kraken emits a heartbeat ~1/s (observed 10 in a
       70-frame sample). If NO frame of any kind arrives within the threshold, the link is
       presumed dead and we reconnect (through the §2 backoff/breaker).
  §1.2 Application ping/pong: Kraken's DOCUMENTED keepalive is a client-initiated
       {"method":"ping"} -> pong, DISTINCT from the protocol ping. We probe on an interval;
       the pong is a frame that refreshes the absence clock, keeping a data-quiet link warm.

Both assert the OBSERVABLE END STATE. NO NETWORK; websockets.connect is replaced wholesale.

ARITHMETIC on the record (why keepalive matters): 1 disconnect / 742s -> 86400/742 ~= 116
reconnects per 24h, each a book discard, a resync, and a data gap.

DO NOT read a green keepalive proof as the 1011 being resolved — see test_no_1011_claim.
"""

import copy
import logging

import pytest
from unittest.mock import patch

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory


async def _no_sleep(_delay):
    """Collapse any reconnect backoff so these keepalive proofs are fast and can never hang
    on real sleeps — even under a mutation that provokes an unexpected reconnect."""
    return None


@pytest.mark.asyncio
async def test_heartbeat_absence_triggers_reconnect(caplog):
    """§1.1: a link that goes SILENT (no heartbeat/data/pong) is presumed dead -> reconnect."""
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)
    adapter._reconnect_sleep = _no_sleep        # backoff is instant (no real waits / hangs)
    adapter._heartbeat_absence_timeout = 0.05   # declare dead after 50ms of silence
    adapter._app_ping_interval = 100.0          # disable the app ping so §1.1 is isolated

    # Socket 1: one good snapshot (emits), then SILENT (on_drain="block") -> absence fires.
    # Socket 2: the reconnect target — a good snapshot, then heartbeats keep it alive so the
    # capture ends at its deadline instead of reconnecting again.
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])

    emitted = []
    with caplog.at_level(logging.INFO):
        with patch("websockets.connect", factory.connect):
            async for state in adapter.get_live_market_data(duration_seconds=0.25):
                emitted.append(state)

    # END STATE: the silence was DETECTED and drove a real reconnect.
    assert "HEARTBEAT_ABSENCE" in caplog.text, "absence must be detected and logged with its code"
    assert factory.connect_count == 2, "heartbeat absence must OPEN a fresh socket"
    assert factory.sockets[0].closed is True, "the dead socket must be closed"
    # Emission continued on the fresh socket (both good snapshots priced).
    assert len(emitted) == 2, f"expected initial + post-reconnect emission; got {len(emitted)}"
    assert adapter.capture_terminated is None, "a single successful reconnect must not trip the breaker"


@pytest.mark.asyncio
async def test_application_ping_pong_keeps_a_quiet_link_alive(caplog):
    """§1.2: on a data-quiet link, the app ping elicits pongs that keep it alive (no reconnect)."""
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)
    adapter._reconnect_sleep = _no_sleep        # backoff is instant (no real waits / hangs)
    adapter._app_ping_interval = 0.02           # probe every 20ms
    adapter._heartbeat_absence_timeout = 0.08   # WOULD trip in 80ms of true silence...

    # Socket 1: one good snapshot, then data-quiet but auto-PONGING. Absence (80ms) is well
    # inside the 250ms window, so WITHOUT the pong the link would be declared dead; the pong
    # refreshing the absence clock is therefore load-bearing. Socket 2 is a spare the passing
    # run never opens — it exists only so that if the ping/pong is broken, the resulting
    # absence-reconnect succeeds cleanly and the assertion below fails on connect_count, not
    # on an incidental breaker trip.
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME], "on_drain": "block", "auto_pong": True},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])

    emitted = []
    with caplog.at_level(logging.INFO):
        with patch("websockets.connect", factory.connect):
            async for state in adapter.get_live_market_data(duration_seconds=0.25):
                emitted.append(state)

    socket = factory.sockets[0]
    pings = [m for m in socket.sent if m.get("method") == "ping"]

    # END STATE: the transport actively probed, the pongs kept the link alive, no reconnect.
    assert len(pings) >= 3, f"the app ping must fire on its interval; sent {len(pings)} pings"
    assert factory.connect_count == 1, "pongs kept the link alive — no keepalive reconnect"
    assert "HEARTBEAT_ABSENCE" not in caplog.text, "a ponging link must not be declared absent"
    assert adapter.capture_terminated is None


@pytest.mark.asyncio
async def test_no_1011_claim_documented_in_report():
    """
    Guard-rail note, in code: this slice does NOT resolve the 1011. Both hypotheses
    (missing pong vs event-loop starvation) remain open; the 1011 was a PROTOCOL-level
    timeout and §1.3's protocol-level proof (the checkpoint seam) plus WO-014c's
    discriminating instruments and the live re-run are what rule it. The application
    keepalive proven here is necessary but NOT sufficient.
    """
    # This test documents the boundary; it asserts nothing runtime beyond the doc's presence.
    assert KrakenV2BookAdapter.APP_PING_INTERVAL_SECONDS > 0
    assert KrakenV2BookAdapter.HEARTBEAT_ABSENCE_TIMEOUT_SECONDS > 0
