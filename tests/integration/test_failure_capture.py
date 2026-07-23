"""
WO-014c-2 §3 — FAILURE-TARGETED CHECKSUM CAPTURE, bite proof (rule 0.1h/0.1i).

WO-008b-B lost 3 of 14,251 checksum failures (0.021%) to POSITIONAL sampling. After A3's
1254/1254, that residual rate is UNDIAGNOSED and NOT presumed benign — so no corpus is
blessed until a run's capture shows whether the failures are wire-level anomalies or our
residual parse/apply bug. This proves that on EVERY checksum failure, driven through the
PRODUCTION path, the FULL forensic artifact is persisted with every ruled field:
  raw wire text (verbatim) | local book both ladders at depth | expected + computed checksums
  | preceding N frames (N justified) | UTC + monotonic + sequence position | redacted.

NOT positional sampling — the capture fires at the failure, which is exactly what positional
sampling lost. NO NETWORK (simulated transport).
"""

import copy

import pytest
from unittest.mock import patch

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from trading.logkit.redaction import scan
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory


async def _no_sleep(_delay):
    return None


def _live_adapter(connect_fn=None):
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=connect_fn)
    adapter._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)
    adapter._reconnect_sleep = _no_sleep
    adapter._heartbeat_absence_timeout = 100.0   # isolate the checksum failure, no reconnect
    adapter._app_ping_interval = 100.0
    return adapter


def _bad_snapshot(with_identifier=False):
    """A snapshot whose declared checksum will not match the applied ladder — the REAL
    production checksum-failure trigger."""
    bad = copy.deepcopy(SNAPSHOT_FRAME)
    bad["data"][0]["checksum"] = 1  # never valid for this ladder
    if with_identifier:
        # A session identifier riding on the wire frame — must be REDACTED in the capture.
        bad["connection_id"] = 1234567890
    return bad


@pytest.mark.asyncio
async def test_checksum_failure_capture_has_every_ruled_field():
    """Drive ONE real checksum failure through the live transport; assert the artifact carries
    every ruled field, populated, and is redacted."""
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, _bad_snapshot(with_identifier=True)], "on_drain": "heartbeat"},
    ])
    adapter = _live_adapter(connect_fn=factory.connect)

    async for _ in adapter.get_live_market_data(duration_seconds=0.2):
        pass

    caps = adapter.get_checksum_failure_captures()
    assert len(caps) >= 1, "a checksum failure must be captured"
    art = caps[0]

    # RAW WIRE TEXT of the failing frame, verbatim (non-empty on the live path).
    assert art["failing_frame_raw_text"], "the failing frame's raw wire text must be captured"
    # LOCAL BOOK — BOTH ladders at subscribed depth.
    assert len(art["local_book_bids"]) == KrakenV2BookAdapter.BOOK_DEPTH
    assert len(art["local_book_asks"]) == KrakenV2BookAdapter.BOOK_DEPTH
    assert art["local_book_bids"][0][0], "book levels carry (price, size) strings"
    # WO-017 follow-up A: the TRANSMITTED wire text is persisted per level, so a FUTURE capture can
    # witness the wire-retention path end-to-end (these frames carry string values -> WireDecimal ->
    # .wire present). None would flag a level that lost its wire string; here every level has it.
    assert len(art["local_book_bids_wire"]) == KrakenV2BookAdapter.BOOK_DEPTH
    assert len(art["local_book_asks_wire"]) == KrakenV2BookAdapter.BOOK_DEPTH
    assert all(pw is not None and qw is not None for pw, qw in art["local_book_bids_wire"]), \
        "each captured level must persist its transmitted wire string (not None)"
    # and it is the TRANSMITTED text, not str()'s render: the top bid matches the frame verbatim.
    assert art["local_book_bids_wire"][0] == ("45283.5", "0.10000000")
    # EXPECTED (Kraken's) and COMPUTED checksums — and they differ (that's the failure).
    assert art["expected_checksum"] == 1
    assert art["computed_checksum"] != art["expected_checksum"]
    # PRECEDING N FRAMES for reconstruction, with N stated.
    assert art["preceding_frames_n"] == adapter._checksum_capture_preceding
    assert isinstance(art["preceding_frames_raw_text"], list)
    assert len(art["preceding_frames_raw_text"]) >= 1, "the prior good snapshot is in the window"
    # UTC + MONOTONIC timestamps, plus SEQUENCE POSITION in the run.
    assert art["utc"].endswith("Z") or "+" in art["utc"]
    assert isinstance(art["monotonic"], float) and art["monotonic"] > 0
    assert art["sequence_position_in_run"] and art["sequence_position_in_run"] >= 1
    # REDACTION (mechanical): the connection_id on the wire is gone; scan finds nothing in clear.
    assert "1234567890" not in art["failing_frame_raw_text"], "identifier must be redacted"
    assert "<REDACTED>" in art["failing_frame_raw_text"]
    all_text = art["failing_frame_raw_text"] + "".join(art["preceding_frames_raw_text"])
    assert scan(all_text) == [], "no unredacted session/connection identifier may remain"


@pytest.mark.asyncio
async def test_every_checksum_failure_captured_not_positionally_sampled():
    """THREE distinct failures -> THREE captures. The count proves capture-on-every-occurrence,
    the property WO-008b-B's positional sampling did not have."""
    # SNAPSHOT (good) then three bad snapshots — each applies and fails its checksum. Three is
    # below the 5-failure reconnect threshold, so all three are same-socket failures.
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, _bad_snapshot(), _bad_snapshot(), _bad_snapshot()],
         "on_drain": "heartbeat"},
    ])
    adapter = _live_adapter(connect_fn=factory.connect)

    async for _ in adapter.get_live_market_data(duration_seconds=0.2):
        pass

    caps = adapter.get_checksum_failure_captures()
    assert len(caps) == 3, f"every failure captured (not sampled); got {len(caps)}"
    # Each is a full artifact, and the run position advances across them (positional distinctness).
    positions = [c["sequence_position_in_run"] for c in caps]
    assert positions == sorted(positions) and len(set(positions)) == 3, positions
    for c in caps:
        assert c["failing_frame_raw_text"] and c["computed_checksum"] != c["expected_checksum"]
