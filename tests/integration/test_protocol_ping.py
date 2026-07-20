"""
WO-014b-2 §1.3 — PROTOCOL-LEVEL ping configuration + recovery from a protocol-level close.

LAYER DISTINCTION (cited, so it survives in the code — project-lead requirement):
Kraken's documented keepalive is an APPLICATION-level ping — "Clients can ping the server
to verify connection is alive and the server will respond with a pong", explicitly "an
application level ping, distinct from the protocol-level ping in the WebSockets standard"
(https://docs.kraken.com/api/docs/websocket-v2/ping ; evidence/WO-014/lifecycle_proposal.txt).
The 742s `1011 keepalive ping timeout` that ended WO-008b-B was the PROTOCOL-level ping —
the websockets library's own WS PING/PONG, the layer BELOW the application ping of §1.2.
Kraken's docs are SILENT on protocol-ping expectations, so the config below is DECLARED
ENGINEERING JUDGMENT (rule 0.1e).

CONFIG (WS_PING_* constants): ping_interval=20s (keep sending WS pings; we do NOT disable
the protocol ping), ping_timeout=None (do NOT let the library close on a missed pong — the
exact 1011 mechanism). Liveness is decided at the application layer by heartbeat-absence
(§1.1) and app ping/pong (§1.2); those are the NAMED replacing signal.

HONEST FIXTURE LIMIT: with simulated transport a protocol-level close is injected as a
ConnectionClosedError(1011) surfaced on recv, and the RECOVERY from it is proven. The
websockets library's real ping/pong loop is NOT run here (that needs a live connection);
only the isolated live re-run confirms the library's behavior with ping_timeout=None.

ARITHMETIC: 1 disconnect / 742s -> ~116/24h — but that hour had NO working keepalive at all,
so the rate should now drop. This is NOT tuned toward; the live re-run measures it.

DO NOT read this as the 1011 being resolved — both hypotheses (missing pong vs event-loop
starvation) remain open (test_no_1011_claim_documented_in_report). NO NETWORK.
"""

import logging

import pytest
from unittest.mock import patch
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedError

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory


async def _no_sleep(_delay):
    return None


def _close_1011():
    """A protocol-level abnormal close — the signature of the WS keepalive-ping timeout (1011)."""
    return ConnectionClosedError(Close(1011, "keepalive ping timeout"), None)


@pytest.mark.asyncio
async def test_protocol_ping_params_set_deliberately():
    """The deliberate protocol-ping config reaches websockets.connect (not the library defaults)."""
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    factory = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])

    with patch("websockets.connect", factory.connect):
        async for _ in adapter.get_live_market_data(duration_seconds=0.05):
            pass

    kwargs = factory.connect_kwargs[0]
    assert kwargs["ping_interval"] == 20.0, "WS pings are still SENT (not silently disabled)"
    assert kwargs["ping_timeout"] is None, (
        "the library must NOT close on a missed pong (the 1011 mechanism); liveness is the "
        "application-layer heartbeat-absence + app ping"
    )


@pytest.mark.asyncio
async def test_protocol_level_close_recovers(caplog):
    """
    THE BITE PROOF (0.1i): a PROTOCOL-LEVEL close (ConnectionClosedError, code 1011 — the
    keepalive-ping-timeout signature that ended WO-008b-B) surfaced on recv drives RECOVERY,
    not a capture-ending crash. Terminates in the observable end state: a fresh connection is
    opened and EMISSION RESUMES. This is the layer that actually threw the 1011.
    """
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._reconnect_sleep = _no_sleep

    # Socket 1: a synchronized book (emits), then a PROTOCOL-LEVEL 1011 close on recv.
    socket1 = {"frames": [SNAPSHOT_FRAME, _close_1011()], "on_drain": "block"}
    # Socket 2: the reconnect target — a fresh snapshot, then heartbeats keep it alive so the
    # capture ends at its deadline rather than closing/absenting again.
    socket2 = {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}
    factory = ScriptedConnectionFactory([socket1, socket2])

    emitted = []
    with caplog.at_level(logging.INFO):
        with patch("websockets.connect", factory.connect):
            async for state in adapter.get_live_market_data(duration_seconds=0.25):
                emitted.append(state)

    # OBSERVABLE END STATE: the protocol-level close was recovered, not fatal.
    assert factory.connect_count == 2, "a protocol-level 1011 close must OPEN a fresh socket"
    assert factory.sockets[0].closed is True
    assert len(emitted) == 2, "emission resumes after recovering from the protocol-level close"
    assert "VENUE_CONNECTION_CLOSED" in caplog.text, "the unexpected close is logged with its code"
    assert adapter.capture_terminated is None, "a single successful recovery must not trip the breaker"
