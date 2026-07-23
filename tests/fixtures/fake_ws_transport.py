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
import time


class FakeClock:
    """WO-023 §3 — ONE fake time source serving BOTH clock interfaces COHERENTLY.

    A single counter drives `wall` and `monotonic`; each is that counter plus a FIXED,
    different base — so advancing the source advances BOTH by the same delta. That is D25
    holding INSIDE the fake: the monotonic base is small (a boot-relative counter that ORDERS),
    the wall base is a real-epoch offset (calendar time that LOCATES); the two never diverge
    because there is one counter. This coherent pair is the DEFAULT construction:

        fc = FakeClock()
        adapter = KrakenV2BookAdapter(mode=..., monotonic_clock=fc.monotonic, connect_fn=...)
        adapter._wall_clock = fc.wall
        fc.advance(5.0)   # both wall and monotonic move +5.0s

    Coherence is MADE OBSERVABLE to the pre-connection gate (WO-023 §4): both readers carry a
    shared `_coherence_token` (this FakeClock instance), so the gate PROVES the two callables
    came from one source instead of inferring it. An incoherent pair carries no shared token.
    """

    _MONOTONIC_BASE = 10_000.0            # small, boot-relative — ORDERS (D25)
    _WALL_BASE = 1_700_000_000.0          # a plausible unix epoch — LOCATES in calendar time (D25)

    def __init__(self, start=0.0):
        self._counter = float(start)
        # Bind the two interfaces and stamp each with the SHARED coherence token (self).
        self.wall = self._make_reader(self._WALL_BASE)
        self.monotonic = self._make_reader(self._MONOTONIC_BASE)

    def _make_reader(self, base):
        def _read():
            return base + self._counter
        _read._coherence_token = self     # both readers share THIS instance == one source
        return _read

    def advance(self, delta):
        """Advance the single source; BOTH interfaces move by the SAME delta (coherent)."""
        self._counter += float(delta)


def incoherent_clock_pair(wall_source=None, monotonic_source=None):
    """WO-023 §3 — the EXPLICITLY-NAMED incoherent construction (NEVER the default path).

    Returns a (wall, monotonic) pair that do NOT share a coherence token: by default a fake
    wall (a fresh FakeClock's wall) against the REAL time.monotonic — the suspend-detector's
    shape, where wall and monotonic MUST be allowed to diverge (that divergence is the thing
    under test). The pre-connection gate refuses such a pair UNLESS the run passes
    incoherent_clocks_allowed=<reason> by name (RULING D34-3: inference is vigilance, so every
    incoherent run is greppable at its construction site). Naming this factory — rather than
    letting FakeClock produce incoherence — keeps incoherence off the default path."""
    import time
    wall = wall_source if wall_source is not None else FakeClock().wall
    monotonic = monotonic_source if monotonic_source is not None else time.monotonic
    return wall, monotonic


async def starve_event_loop(seconds: float) -> None:
    """
    WO-014c-1 §B.4 starvation simulation. Blocks the WHOLE event loop synchronously for
    `seconds` (a real, deterministic stall — time.sleep does not yield), so a concurrent lag
    sampler genuinely misses wakes. Used to bite-prove that the sampler SELF-REPORTS the
    degradation (missed count + gap timestamps) rather than going silently quiet.
    """
    time.sleep(seconds)


class FakeWebSocket:
    """A single simulated Kraken v2 socket. See module docstring; WO-014b-2 adds keepalive
    modes (silence / heartbeat / application pong) so time-based behavior is testable."""

    def __init__(self, frames, on_drain="block", heartbeat_interval=0.005, auto_pong=False,
                 pong_rtt=None):
        # frames: JSON-serializable dict envelopes (the raw v2 fixtures), delivered first.
        # on_drain: behavior once scripted frames (and any queued pongs) are exhausted —
        #   "block"     : recv blocks until the transport's recv timeout cancels it — a
        #                 SILENT link. Under keepalive this makes the heartbeat-absence
        #                 detector trip after its threshold. (Default.)
        #   "heartbeat" : recv returns a paced {"channel":"heartbeat"} — a LIVE-but-quiet
        #                 link that refreshes the absence clock, so a capture ends at its
        #                 deadline instead of reconnecting.
        #   "timeout"   : recv raises asyncio.TimeoutError at once (legacy 014b-1 "no more
        #                 frames" semantics; retained for any caller that wants it).
        # auto_pong: when True, a sent {"method":"ping"} queues a {"method":"pong"} that a
        #   subsequent recv returns — models Kraken's application ping/pong (§1.2).
        # pong_rtt (WO-014c-1 §B.2): the simulated PROTOCOL-level ws.ping() round-trip time in
        # seconds; None means the pong never comes back (an ABSENT pong the observer times out).
        self._frames = list(frames)
        self._index = 0
        self._on_drain = on_drain
        self._heartbeat_interval = heartbeat_interval
        self._auto_pong = auto_pong
        self._pong_rtt = pong_rtt
        self.pings_received = 0      # protocol-level ws.ping() calls this socket received
        self._pending = []      # frames (e.g. pongs) queued in response to sends
        self.sent = []          # parsed messages the transport sent on this socket
        self.closed = False

    async def send(self, message):
        """Record what the transport sends; auto-pong replies to an application ping."""
        msg = json.loads(message)
        self.sent.append(msg)
        if self._auto_pong and msg.get("method") == "ping":
            pong = {"method": "pong"}
            if "req_id" in msg:
                pong["req_id"] = msg["req_id"]
            self._pending.append(pong)

    async def recv(self):
        """Deliver the next scripted frame, then any queued pong, then the drain behavior.

        WO-014b-2 §1.3: a scripted entry that is an EXCEPTION INSTANCE is RAISED instead of
        returned — this is how a test injects a protocol-level close (e.g. a websockets
        ConnectionClosedError with code 1011, or ConnectionClosedOK with 1000) surfaced on recv.
        """
        if self._index < len(self._frames):
            frame = self._frames[self._index]
            self._index += 1
            if isinstance(frame, BaseException):
                raise frame
            return json.dumps(frame)
        if self._pending:
            return json.dumps(self._pending.pop(0))
        if self._on_drain == "timeout":
            raise asyncio.TimeoutError("scripted FakeWebSocket drained (no more frames)")
        if self._on_drain == "heartbeat":
            await asyncio.sleep(self._heartbeat_interval)
            return json.dumps({"channel": "heartbeat"})
        # "block": a silent link — wait until the transport's recv timeout cancels us.
        await asyncio.Event().wait()

    async def close(self):
        self.closed = True

    async def ping(self, data=None):
        """
        WO-014c-1 §B.2: model the sanctioned protocol-level ws.ping() — returns a future
        (the pong-waiter) whose result is the round-trip latency in seconds. Resolves
        immediately to pong_rtt if set; if pong_rtt is None the future is never resolved, so
        the observer records an ABSENT pong when its absent-timeout elapses. This is the RFC
        6455 §5.5.2 control frame, NOT Kraken's application {"method":"ping"}.
        """
        self.pings_received += 1
        fut = asyncio.get_event_loop().create_future()
        if self._pong_rtt is not None:
            fut.set_result(self._pong_rtt)
        return fut


# WO-014b-2 §2: a script entry of REOPEN_FAILURE makes that connect() attempt RAISE
# (as a real refused reopen would), which _connect() wraps in ConnectionError — the exact
# signal the backoff/circuit-breaker path handles. A list entry is a successful socket.
# This lets one factory model "fail N times then succeed" (backoff) and "fail forever"
# (breaker) without rebuilding the harness.
REOPEN_FAILURE = "__REOPEN_FAILURE__"


class ScriptedConnectionFactory:
    """Hands out a fresh FakeWebSocket per connection, or fails a scripted attempt.
    See module docstring and REOPEN_FAILURE above."""

    def __init__(self, socket_scripts, on_drain="block", auto_pong=False):
        # socket_scripts: ordered list; each entry is either a frame-list (a successful
        # connection), REOPEN_FAILURE (that connect attempt raises), or a dict
        # {"frames": [...], "on_drain": "...", "auto_pong": bool} for per-socket control.
        # on_drain / auto_pong set the defaults applied to plain frame-list entries.
        self._scripts = list(socket_scripts)
        self._default_on_drain = on_drain
        self._default_auto_pong = auto_pong
        self.sockets = []
        self.connect_count = 0        # total connect() calls (successes + failures)
        self.failed_attempts = 0      # connect() calls that raised
        self.connect_kwargs = []      # kwargs of each connect() call (WO-014b-2 §1.3: ping params)

    async def connect(self, *args, **kwargs):
        """Drop-in for `websockets.connect`; records kwargs, ignores URL/timeout values."""
        self.connect_kwargs.append(dict(kwargs))
        if self.connect_count >= len(self._scripts):
            raise AssertionError(
                f"transport opened connection #{self.connect_count + 1} but the harness "
                f"scripted only {len(self._scripts)} — unexpected reconnect."
            )
        spec = self._scripts[self.connect_count]
        self.connect_count += 1
        if isinstance(spec, str) and spec == REOPEN_FAILURE:
            self.failed_attempts += 1
            # OSError is what a refused/timed-out reopen surfaces; _connect() wraps it in
            # ConnectionError, which the backoff/breaker path catches.
            raise OSError("simulated reopen failure (scripted REOPEN_FAILURE)")
        if isinstance(spec, dict):
            socket = FakeWebSocket(
                spec["frames"],
                on_drain=spec.get("on_drain", self._default_on_drain),
                auto_pong=spec.get("auto_pong", self._default_auto_pong),
                heartbeat_interval=spec.get("heartbeat_interval", 0.005),
            )
        else:
            socket = FakeWebSocket(
                spec, on_drain=self._default_on_drain, auto_pong=self._default_auto_pong,
            )
        self.sockets.append(socket)
        return socket
