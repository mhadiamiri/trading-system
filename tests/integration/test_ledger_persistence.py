"""
WO-014c-3 §0.1 — GAP LEDGER PERSISTENCE (append-only, redacted, crash-durable).

The ledger is only useful for a 60-min / 24-h run if it survives to disk. These prove the
observable END STATE — gap records READABLE FROM THE FILE — not that a flush was called (0.1i):
  1. a clean capture writes run_start + per-gap open/resolved + run_end, all readable;
  2. INCREMENTAL durability: a gap's "open" record is on disk the instant the gap opens, so an
     unhandled exception mid-capture (a crash) does NOT lose it — the load-bearing property, the
     shape of _reconnect() again (the mechanism that records the terminal event must survive it).

NO NETWORK (simulated transport). Persistence is append-only and redacted through the mechanical
redaction module.
"""

import copy
import json
import time

import pytest
from unittest.mock import patch
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedError

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL
from tests.fixtures.fake_ws_transport import AdvancingClock, ScriptedConnectionFactory

# WO-035 §3 (batch C) — DETERMINISTIC TIME. These captures used to be bounded by the REAL clock, so
# whether the scripted frames finished before `duration_seconds` elapsed was a race against scheduler
# load. Both races here now drive the deadline through an injected COHERENT `AdvancingClock` pair.
#
# The delta is chosen as `duration / _READS_BEFORE_DEADLINE`, so the deadline fires after a
# DETERMINATE number of monotonic reads — the same construction gives the same firing point on every
# run and in every order. 50 leaves a wide margin over the ~4 recv iterations these scripts need
# (WO-029 §9 measured its firing point rather than deriving it; the margin is deliberate, not tight).
_READS_BEFORE_DEADLINE = 50


async def _no_sleep(_delay):
    return None


def _live_adapter(persist_path, connect_fn=None, clock=None):
    adapter = KrakenV2BookAdapter(
        mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=connect_fn,
        monotonic_clock=(clock.monotonic if clock is not None else None) or time.monotonic,
    )
    if clock is not None:
        adapter._wall_clock = clock.wall        # the coherent partner (shared token) — gate PROCEEDs
    adapter._reconnect_sleep = _no_sleep
    adapter._heartbeat_absence_timeout = 100.0
    adapter._app_ping_interval = 100.0
    adapter._gap_persist_path = str(persist_path)
    return adapter


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.mark.asyncio
async def test_gap_ledger_persisted_readable_from_disk(tmp_path):
    """A clean capture with a real gap writes an append-only JSONL whose records are readable
    from disk with their fields — run_start, the gap open+resolved, and run_end."""
    path = tmp_path / "gap_ledger.jsonl"
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])
    # WO-035 §3 — race 12 terminates on the DEADLINE branch (socket 2 heartbeats keep the link up),
    # and that branch is KEPT: the injected clock fires the same deadline, it does not replace it
    # with a scripted close. Asserted below via run_end + resolved, which only exist because the run
    # reached its clean finalize after the reconnect.
    clk = AdvancingClock(delta=0.25 / _READS_BEFORE_DEADLINE)
    adapter = _live_adapter(path, connect_fn=factory.connect, clock=clk)

    async for _ in adapter.get_live_market_data(duration_seconds=0.25):
        pass

    records = _read_jsonl(path)
    events = [r["event"] for r in records]
    assert events[0] == "run_start", "the run anchor is written first (survives an early death)"
    assert "run_end" in events, "a clean capture writes the finalize summary"
    opens = [r for r in records if r["event"] == "open"]
    resolved = [r for r in records if r["event"] == "resolved"]
    assert len(opens) == 1 and len(resolved) == 1, f"one gap open+resolved on disk; got {events}"
    o = opens[0]
    # The record is readable with its fields (observable end state, not "flush called").
    assert o["cause"] == "VENUE_DISCONNECT"
    assert o["reason_code"] == "VENUE_CONNECTION_CLOSED"
    assert o["gap_id"] == 0
    assert o["open_monotonic"] > 0
    assert o["last_validated_book"]["best_bid"], "last-good book persisted"
    # run_start carries the once-per-run anchor pair.
    rs = records[0]
    assert rs["run_wall_anchor"] and rs["run_monotonic_anchor"] > 0


@pytest.mark.asyncio
async def test_incremental_persist_survives_unhandled_exception_mid_capture(tmp_path):
    """CRASH SIMULATION (WO-014c-3 §0.1): a gap opens, then an unhandled exception is raised
    mid-capture. The gap's "open" record was written+fsync'd AT OPEN, so it is ON DISK despite
    the crash — durability does not depend on reaching a clean end."""
    path = tmp_path / "gap_ledger.jsonl"
    corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
    corrupted["data"][0]["bids"][0]["price"] = "45283.7"   # real checksum failure -> gap opens
    crash = RuntimeError("injected unhandled crash mid-capture")
    # SNAPSHOT emits; corrupted opens a CHECKSUM_RESYNC gap (persisted at OPEN); then a generic
    # exception on recv propagates out of the capture (not a ConnectionClosed the loop handles).
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, corrupted, crash], "on_drain": "block"},
    ])
    # WO-035 §3 — ENTRY 35, the race this whole bound re-audit began with.
    #
    # This test asserts the CRASH wins: `pytest.raises(RuntimeError)` requires the loop to drain the
    # THIRD scripted frame. Against the real clock that was a race — the 0.25s deadline could end the
    # capture cleanly first, and CI observed exactly that (run 30304749145, seed 2050525690, "DID NOT
    # RAISE"). WO-033 §3-bis measured the boundary: at AdvancingClock(delta=0.05) the gap opens but
    # the crash never arrives; at delta<=0.01 the crash reliably wins.
    #
    # The conversion pins the asserted winner rather than leaving it to the real-time race: delta is
    # 0.25/50 = 0.005, so ~50 monotonic reads are available against the ~3 recvs the crash needs. The
    # CRASH branch is kept — the run still ends by the injected exception propagating out, not by a
    # deadline and not by a scripted close.
    clk = AdvancingClock(delta=0.25 / _READS_BEFORE_DEADLINE)
    adapter = _live_adapter(path, connect_fn=factory.connect, clock=clk)

    with pytest.raises(RuntimeError, match="injected unhandled crash"):
        async for _ in adapter.get_live_market_data(duration_seconds=0.25):
            pass

    # OBSERVABLE END STATE: the gap open record is readable from the file, written incrementally
    # BEFORE the crash — not batched to a finalize that a real kill would never reach.
    records = _read_jsonl(path)
    opens = [r for r in records if r["event"] == "open"]
    assert len(opens) == 1, f"the gap open was persisted incrementally before the crash; got {records}"
    assert opens[0]["cause"] == "CHECKSUM_RESYNC"
    assert opens[0]["gap_id"] == 0
    # It never resolved (crash before recovery) -> no "resolved" line -> default-deny open-ended.
    assert not [r for r in records if r["event"] == "resolved"]


@pytest.mark.asyncio
async def test_live_capture_refuses_when_persistence_unset():
    """WO-014c-3 addendum C: a LIVE capture started with gap-ledger persistence UNSET and no
    explicit opt-out REFUSES to run — an opt-in durability feature that silently no-ops when
    unset is the vigilance-enforced guarantee the persistence fix closed. Observable end state:
    it refuses BEFORE opening any connection."""
    factory = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory.connect)
    # Unconfigured: no path AND not opted out (the real-run hazard).
    assert adapter._gap_persist_path is None and adapter._persistence_optional is False

    with pytest.raises(ValueError, match="GAP_PERSIST_UNCONFIGURED"):
        async for _ in adapter.get_live_market_data(duration_seconds=0.1):
            pass

    assert factory.connect_count == 0, "it must refuse before opening a live connection"
