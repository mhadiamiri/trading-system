"""
WO-015 addendum A — HOST_SUSPEND: the ruled fifth gap-ledger cause.

A host suspend counts on the wall clock but not the monotonic clock (or vice versa), so a
single loop iteration shows a wall-vs-monotonic divergence far beyond any legitimate drift
(~5s typical, <=43s worst over 24h; WO-014c-3 §0.3). Without detecting it, a mid-capture
suspend MASQUERADES as catastrophic starvation — a wrong verdict at the discrimination layer.

Role here is DIAGNOSTIC: record a HOST_SUSPEND gap and report loudly, DO NOT terminate (the
corpus WO makes it window-invalidating). Simulated via an injected wall clock that jumps —
NO real suspend, NO network.
"""

import logging

import pytest
from unittest.mock import patch

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, GAP_CAUSES
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory


class _JumpClock:
    """A wall clock that advances slightly per call, then JUMPS once (a suspend's signature)."""

    def __init__(self, base=1_000_000.0, jump_at_call=3, jump_by=120.0):
        self.base = base
        self.calls = 0
        self.jump_at_call = jump_at_call
        self.jump_by = jump_by
        self.offset = 0.0

    def __call__(self):
        self.calls += 1
        if self.calls == self.jump_at_call:
            self.offset += self.jump_by   # the machine "resumed" 120s later on the wall clock
        return self.base + self.calls * 0.001 + self.offset


def test_host_suspend_is_the_fifth_ruled_cause():
    assert "HOST_SUSPEND" in GAP_CAUSES and len(GAP_CAUSES) == 5


@pytest.mark.asyncio
async def test_host_suspend_recorded_diagnostic_not_terminal(caplog):
    """A wall/monotonic divergence beyond the drift bound records a HOST_SUSPEND gap, reports
    loudly, and DOES NOT terminate the capture."""
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._persistence_optional = True
    adapter._heartbeat_absence_timeout = 100.0    # a live-but-quiet link stays up
    adapter._app_ping_interval = 100.0
    adapter._wall_clock = _JumpClock(jump_at_call=3, jump_by=120.0)   # 120s > 43s bound

    # SNAPSHOT emits, then heartbeats keep the link alive so the loop iterates past the jump.
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])

    emitted = []
    with caplog.at_level(logging.ERROR):
        with patch("websockets.connect", factory.connect):
            async for state in adapter.get_live_market_data(duration_seconds=0.25):
                emitted.append(state)

    ledger = adapter.get_gap_ledger()
    suspends = [g for g in ledger.gaps if g.cause == "HOST_SUSPEND"]
    assert len(suspends) == 1, f"exactly one host-suspend gap; got {[g.cause for g in ledger.gaps]}"
    g = suspends[0]
    assert g.reason_code == "HOST_SUSPEND"
    assert "divergence" in g.detail and "drift bound" in g.detail
    # DIAGNOSTIC, not terminal: recorded, resumed, run continued.
    assert g.terminal is False and g.resumed is True
    assert g.close_monotonic is not None and g.close_monotonic >= g.open_monotonic
    assert adapter.capture_terminated is None, "a suspend is diagnostic, never a termination"
    assert "HOST_SUSPEND" in caplog.text, "the suspend must be reported loudly"
    assert len(emitted) >= 1, "the capture continued past the suspend (the snapshot priced)"
    # It is a COMPLETE record (a resolved diagnostic gap), not a ledger-integrity deficit.
    assert ledger.incomplete == []


@pytest.mark.asyncio
async def test_no_host_suspend_under_normal_timing():
    """Normal operation (no injected jump) records NO host-suspend gap — wall and monotonic
    track each other well within the drift bound."""
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._persistence_optional = True
    adapter._heartbeat_absence_timeout = 100.0
    adapter._app_ping_interval = 100.0
    factory = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])

    with patch("websockets.connect", factory.connect):
        async for _ in adapter.get_live_market_data(duration_seconds=0.2):
            pass

    ledger = adapter.get_gap_ledger()
    assert [g for g in ledger.gaps if g.cause == "HOST_SUSPEND"] == []
