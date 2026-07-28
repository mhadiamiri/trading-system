"""
WO-014b-2 §1.3 §2 — the 4c VENUE-CLOSE path, routed into the existing recovery.

§0/gap_attachment_points recorded that an EXPLICIT venue close on recv propagated and ended
the capture with no reconnect — the same hazard class as §0's hard-stop. It is now routed
into the EXISTING reconnect + backoff + duration-breaker path (reuse; no parallel recovery).

S13 PRESERVATION DUAL — both halves in ONE test:
  - UNEXPECTED close (venue-initiated, abnormal code e.g. 1011) -> RECONNECT.
  - EXPECTED close (clean / normal-closure code 1000) -> shut down cleanly, NO reconnect.
A clean shutdown must never trigger reconnection (do not hammer a venue that closed on
purpose); an unexpected failure must never end the capture silently.

HONEST FIXTURE LIMIT: closes are injected as websockets ConnectionClosedError/Ok on recv
(simulated transport). The live re-run confirms the venue's real close behavior. NO NETWORK.
"""

import logging

import pytest
from unittest.mock import patch
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import AdvancingClock, ScriptedConnectionFactory

# WO-035 §3 (batch C): the deadline fires after a determinate number of monotonic reads.
_READS_BEFORE_DEADLINE = 50


async def _no_sleep(_delay):
    return None


@pytest.mark.asyncio
async def test_venue_close_unexpected_reconnects_expected_shuts_down_cleanly(caplog):
    """S13 dual: unexpected close -> reconnect; expected (clean) close -> clean shutdown, no reconnect."""

    # ── HALF 1: UNEXPECTED close (abnormal 1011) -> routes into recovery ──────────────
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    factory_a = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])
    # WO-035 §3 — race 26, HALF 1. Terminates on the DEADLINE branch (socket 2 heartbeats keep the
    # link up after the reconnect); kept, and asserted below by `len(emitted_a) == 2` — the
    # post-reconnect emission must land before the run ends.
    clk_a = AdvancingClock(delta=0.25 / _READS_BEFORE_DEADLINE)
    adapter_a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory_a.connect,
                                    monotonic_clock=clk_a.monotonic)
    adapter_a._wall_clock = clk_a.wall
    adapter_a._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)
    adapter_a._reconnect_sleep = _no_sleep

    emitted_a = []
    with caplog.at_level(logging.INFO):
        async for state in adapter_a.get_live_market_data(duration_seconds=0.25):
            emitted_a.append(state)

    assert factory_a.connect_count == 2, "an UNEXPECTED close must reconnect"
    assert factory_a.sockets[0].closed is True
    assert len(emitted_a) == 2, "emission resumes after recovering from the unexpected close"
    assert "VENUE_CONNECTION_CLOSED" in caplog.text

    # ── HALF 2: EXPECTED close (clean 1000) -> clean shutdown, NO reconnect ───────────
    caplog.clear()
    expected = ConnectionClosedOK(Close(1000, "normal closure"), None)
    # A clean close must NOT reconnect, so the second socket is a SPARE the correct code never
    # opens (connect_count stays 1). It exists only so that if the clean close WRONGLY
    # reconnected, that reconnect succeeds and the assertion below fails on connect_count — a
    # clean failure rather than a hang.
    factory_b = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, expected], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])
    # WO-035 §3 — race 26, HALF 2. This half terminates on the VENUE-CLOSE branch, NOT the deadline:
    # the clean 1000 close ends the run. That distinction is the point of the dual, so the conversion
    # must not let the deadline pre-empt it. The same wide margin does that — the clean close arrives
    # on recv #2 of ~50 available reads — and the branch is asserted below by `connect_count == 1`
    # plus `len(emitted_b) == 1`: a deadline-ended run would have kept the socket and emitted no
    # differently, so the CLOSE is what ends it.
    clk_b = AdvancingClock(delta=0.25 / _READS_BEFORE_DEADLINE)
    adapter_b = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory_b.connect,
                                    monotonic_clock=clk_b.monotonic)
    adapter_b._wall_clock = clk_b.wall
    adapter_b._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)
    adapter_b._reconnect_sleep = _no_sleep

    emitted_b = []
    with caplog.at_level(logging.INFO):
        async for state in adapter_b.get_live_market_data(duration_seconds=0.25):
            emitted_b.append(state)

    assert factory_b.connect_count == 1, "a CLEAN close must NOT reconnect"
    assert len(emitted_b) == 1, "only the pre-close snapshot emits; the run ends cleanly"
    assert "VENUE_CONNECTION_CLOSED" not in caplog.text, "a clean shutdown is not an unexpected close"
    assert adapter_b.capture_terminated is None, "a clean shutdown is not a breaker trip"
