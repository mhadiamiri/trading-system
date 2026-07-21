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

import pytest
from unittest.mock import patch
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedError

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory


async def _no_sleep(_delay):
    return None


def _live_adapter(persist_path):
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
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
    adapter = _live_adapter(path)
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])

    with patch("websockets.connect", factory.connect):
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
    adapter = _live_adapter(path)
    corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
    corrupted["data"][0]["bids"][0]["price"] = "45283.7"   # real checksum failure -> gap opens
    crash = RuntimeError("injected unhandled crash mid-capture")
    # SNAPSHOT emits; corrupted opens a CHECKSUM_RESYNC gap (persisted at OPEN); then a generic
    # exception on recv propagates out of the capture (not a ConnectionClosed the loop handles).
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, corrupted, crash], "on_drain": "block"},
    ])

    with patch("websockets.connect", factory.connect):
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
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    # Unconfigured: no path AND not opted out (the real-run hazard).
    assert adapter._gap_persist_path is None and adapter._persistence_optional is False
    factory = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])

    with patch("websockets.connect", factory.connect):
        with pytest.raises(ValueError, match="GAP_PERSIST_UNCONFIGURED"):
            async for _ in adapter.get_live_market_data(duration_seconds=0.1):
                pass

    assert factory.connect_count == 0, "it must refuse before opening a live connection"
