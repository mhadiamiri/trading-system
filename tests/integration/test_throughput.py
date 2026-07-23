"""
WO-014c-1 §B.3 — receive-to-process latency + message-rate COMPLETENESS.

Per-second receive-to-process latency and message counts, on the shared time.monotonic()
clock. The record carries its OWN expected-vs-actual completeness: a SILENT second (no
messages) is reported explicitly, so a Branch-5 nomination (correlating lag-sampler gaps
against message-rate peaks) can STATE whether the message data at those timestamps is
trustworthy — "nomination unmakeable, message record also degraded here" is honest;
silently correlating against incomplete data is not.

NO NETWORK.
"""

import asyncio

import pytest
from unittest.mock import patch

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, ThroughputRecord
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory


@pytest.mark.asyncio
async def test_receive_to_process_latency_recorded_through_production_path():
    """A real capture populates the throughput record from the recv -> process_raw_frame path."""
    factory = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory.connect)
    adapter._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)

    async for _ in adapter.get_live_market_data(duration_seconds=0.1):
        pass

    rec = adapter._throughput_record
    assert rec.observed_seconds >= 1, "frames were received and timed"
    total_messages = sum(b["messages"] for b in rec.per_second.values())
    assert total_messages >= 1
    assert all(b["lat_n"] >= 1 and b["lat_max"] >= 0.0 for b in rec.per_second.values())


def test_message_rate_completeness_reports_silent_seconds():
    """
    THE BITE PROOF (0.1i): a second with NO message data is REPORTED (silent_seconds), so
    trustworthiness at gap timestamps is statable — never a silent shortfall the correlation
    would trust blindly.
    """
    rec = ThroughputRecord(bucket_seconds=1.0)
    rec.start_monotonic = 1000.0
    rec.record(1000.10, 1000.11)          # second 0
    rec.record(1000.20, 1000.24)          # second 0 (latency 0.04)
    rec.record(1002.10, 1002.11)          # second 2  (second 1 is SILENT)
    rec.end_monotonic = 1002.5

    # The completeness deficit is EXPLICIT.
    assert 1 in rec.silent_seconds, (
        f"the silent second must be reported so a nomination can judge its data; "
        f"silent_seconds={rec.silent_seconds}"
    )
    assert rec.observed_seconds == 2
    assert rec.expected_seconds >= 3
    # Per-second receive-to-process latency is available for the elevated-lag corroboration.
    assert abs(rec.mean_latency(0) - 0.025) < 1e-6
    assert abs(rec.per_second[0]["lat_max"] - 0.04) < 1e-6
