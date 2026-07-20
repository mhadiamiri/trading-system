"""
Simulated Kraken v2 WebSocket transport for driving get_live_market_data() across
a close/reopen (reconnect) boundary WITHOUT touching the network (WO-014b-1, note 2).

WHY THIS EXISTS
---------------
The reconnect-to-effect proof (rule 0.1i) cannot use the shortcut the snapshot-recovery
proof used — feeding process_raw_frame() directly and calling _maybe_resubscribe() by
hand. "Reconnection occurred" is only observable by driving the REAL transport loop
(get_live_market_data) and watching it CLOSE one socket and OPEN a fresh one. That
requires a fake `websockets.connect` that hands out a *different* socket each time the
transport reconnects. That is precisely what this module provides.

WHAT IT EXPOSES (stable surface for WO-014b-2 to extend, not rebuild)
---------------------------------------------------------------------
  FakeWebSocket(frames)
      One simulated socket. `recv()` yields each scripted frame as JSON wire TEXT
      (the form the transport json.loads()); `send()` records the parsed message in
      `.sent`; `close()` sets `.closed`. When the script is exhausted `recv()` raises
      asyncio.TimeoutError — the SAME signal a real quiet/drained socket gives the
      transport's `asyncio.wait_for(recv(), timeout=...)`, so a capture ends
      deterministically and instantly instead of waiting out the wall clock.

  ScriptedConnectionFactory(socket_scripts)
      Patches `websockets.connect`. Connection N is handed FakeWebSocket(socket_scripts[N]).
      The transport's first _connect() gets socket 0; after _perform_reconnect() closes
      it, the next _connect() gets socket 1 — the close/reopen boundary a reconnect
      crosses. Records `.connect_count` and every socket in `.sockets`. Opening more
      connections than scripted is an AssertionError (a runaway reconnect loop must not
      pass silently).

WO-014b-2 REUSE: script a socket that goes silent mid-stream (a short frame list that
drains) to drive heartbeat-absence detection, and a second script for the socket the
resulting reconnect opens. No change to this module is required.

NO NETWORK. Nothing here opens a socket; `websockets.connect` is replaced wholesale.
"""

from __future__ import annotations

import asyncio
import json


class FakeWebSocket:
    """A single simulated Kraken v2 socket. See module docstring for the contract."""

    def __init__(self, frames):
        # frames: list of JSON-serializable dict envelopes (the raw v2 fixtures).
        self._frames = list(frames)
        self._index = 0
        self.sent = []      # parsed messages the transport sent on this socket
        self.closed = False

    async def send(self, message):
        """Record what the transport sends (subscribe / unsubscribe producer output)."""
        self.sent.append(json.loads(message))

    async def recv(self):
        """
        Deliver the next scripted frame as wire TEXT. When drained, raise
        asyncio.TimeoutError — identical in effect to a real socket that returns no
        frame within the transport's recv timeout, so the capture loop breaks cleanly.
        """
        if self._index >= len(self._frames):
            raise asyncio.TimeoutError("scripted FakeWebSocket drained (no more frames)")
        frame = self._frames[self._index]
        self._index += 1
        return json.dumps(frame)

    async def close(self):
        self.closed = True


class ScriptedConnectionFactory:
    """Hands out a fresh FakeWebSocket per connection. See module docstring."""

    def __init__(self, socket_scripts):
        # socket_scripts: list of frame-lists, one per expected connection, in order.
        self._scripts = list(socket_scripts)
        self.sockets = []
        self.connect_count = 0

    async def connect(self, *args, **kwargs):
        """Drop-in for `websockets.connect`; ignores URL/timeout kwargs."""
        if self.connect_count >= len(self._scripts):
            raise AssertionError(
                f"transport opened connection #{self.connect_count + 1} but the harness "
                f"scripted only {len(self._scripts)} — unexpected reconnect."
            )
        socket = FakeWebSocket(self._scripts[self.connect_count])
        self.connect_count += 1
        self.sockets.append(socket)
        return socket
