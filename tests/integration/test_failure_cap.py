"""
WO-014c-3 §0.2 — FAILURE-CAPTURE RETENTION CAP (keep first N, count all, announce, never
silently truncate, never terminate the run).

If checksum failures cluster pathologically, unbounded capture fills the disk and ENDS the run
it was meant to document. The cap bounds retention while:
  (a) KEEPING THE FIRST N — the onset is the most diagnostic part;
  (b) COUNTING EVERY failure — the count is itself a finding, never capped;
  (c) NOT terminating the run — the breaker owns termination; the cap only guards disk;
and ANNOUNCING itself (FAILURE_CAPTURE_CAPPED) rather than silently truncating — a silently
truncated failure ledger is the same defect class as the positional sampling §3 exists to kill.

NO NETWORK (simulated transport).
"""

import copy
import logging

import pytest
from unittest.mock import patch

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory


def _bad_snapshot():
    bad = copy.deepcopy(SNAPSHOT_FRAME)
    bad["data"][0]["checksum"] = 1  # never valid for this ladder -> a real checksum failure
    return bad


def _live_adapter():
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)
    adapter._heartbeat_absence_timeout = 100.0
    adapter._app_ping_interval = 100.0
    # Isolate the CAP from the 5-consecutive-failure reconnect: raise the reconnect threshold so
    # the run is driven only by the cap, not the breaker (§0.2(c): the cap must not terminate).
    adapter.CHECKSUM_FAILURE_THRESHOLD = 1000
    return adapter


@pytest.mark.asyncio
async def test_count_cap_keeps_first_n_counts_all_announces(caplog):
    """COUNT cap: 6 failures, cap 3 -> the FIRST 3 kept (the onset), all 6 COUNTED, announced,
    run NOT terminated."""
    adapter = _live_adapter()
    adapter._max_failure_captures = 3

    # SNAPSHOT (position 1) then six bad snapshots (positions 2..7), each a real checksum failure.
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(6)], "on_drain": "heartbeat"},
    ])

    with caplog.at_level(logging.ERROR):
        with patch("websockets.connect", factory.connect):
            async for _ in adapter.get_live_market_data(duration_seconds=0.25):
                pass

    # COUNT is never capped.
    assert adapter.get_checksum_failure_count() == 6, "every failure is counted"
    # KEEP only the first N.
    caps = adapter.get_checksum_failure_captures()
    assert len(caps) == 3, f"cap keeps only the first N; got {len(caps)}"
    # KEEP THE FIRST N (the onset), not the last — the earliest failures by run position.
    positions = [c["sequence_position_in_run"] for c in caps]
    assert positions == [2, 3, 4], f"the FIRST three failures are kept (onset); got {positions}"
    # ANNOUNCED, not silently truncated.
    assert "FAILURE_CAPTURE_CAPPED" in caplog.text
    # NOT terminated by the cap (the breaker owns termination).
    assert adapter.capture_terminated is None, "the cap must not terminate the run"


@pytest.mark.asyncio
async def test_byte_cap_binds_independently(caplog):
    """BYTE cap binds independently of count (whichever comes first). A tiny byte budget caps
    retention well before the count limit; the count keeps rising, and it announces."""
    adapter = _live_adapter()
    adapter._max_failure_captures = 1000          # count will NOT bind
    adapter._max_failure_capture_bytes = 2000     # ~2 KB: binds after very few captures

    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(6)], "on_drain": "heartbeat"},
    ])

    with caplog.at_level(logging.ERROR):
        with patch("websockets.connect", factory.connect):
            async for _ in adapter.get_live_market_data(duration_seconds=0.25):
                pass

    assert adapter.get_checksum_failure_count() == 6, "count is never capped"
    assert len(adapter.get_checksum_failure_captures()) < 6, "the byte cap bound before count"
    assert "FAILURE_CAPTURE_CAPPED" in caplog.text
    assert adapter.capture_terminated is None


@pytest.mark.asyncio
async def test_capped_failures_get_one_line_summaries():
    """WO-014c-3 addendum A: failures BEYOND the cap get a ONE-LINE summary (utc, expected/
    computed checksum, sequence position; NO raw frames), so a cluster's PHASES stay visible
    where the count alone cannot show them."""
    adapter = _live_adapter()
    adapter._max_failure_captures = 2   # first 2 fully captured; the rest summarized

    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(6)], "on_drain": "heartbeat"},
    ])
    with patch("websockets.connect", factory.connect):
        async for _ in adapter.get_live_market_data(duration_seconds=0.25):
            pass

    caps = adapter.get_checksum_failure_captures()
    summaries = adapter.get_checksum_failure_summaries()
    assert adapter.get_checksum_failure_count() == 6
    assert len(caps) == 2, f"first N fully captured; got {len(caps)}"
    assert len(summaries) == 4, f"the other failures get one-line summaries; got {len(summaries)}"
    s = summaries[0]
    assert set(s) == {"sequence_position_in_run", "utc", "monotonic",
                      "expected_checksum", "computed_checksum"}, s
    assert "failing_frame_raw_text" not in s and "local_book_bids" not in s, "NO raw frames"
    assert s["expected_checksum"] != s["computed_checksum"]
    # The summaries cover the TAIL (positions after the fully-captured onset).
    assert (min(x["sequence_position_in_run"] for x in summaries)
            > max(c["sequence_position_in_run"] for c in caps))
