"""
WO-014 §2.1 — snapshot recovery exercises the PRODUCTION TRIGGER PATH (rule 0.1h).

The WO-008b-B defect: emission latched off after a checksum failure because
`_request_snapshot()` was `pass`. S10's consumer (fresh snapshot -> resume) was
certified; the PRODUCER (request the snapshot) did not exist. This drives a REAL
checksum failure through production and asserts production (a) REQUESTS a resubscribe
and (b) resumes emission once the fresh snapshot arrives — the producer S10 was
hand-fed.

HONEST FIXTURE LIMIT (same discipline as A1's checksum-ordering limit): this feeds
the recovery snapshot as Kraken would deliver it AFTER a resubscribe. Only the
isolated live re-run confirms Kraken actually responds to unsubscribe+subscribe with
a fresh snapshot. The producer send is exercised here; the venue's response is not.
"""
import copy
import json

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL


class _RecordingWS:
    """Records what the transport SENDS (the producer's output)."""

    def __init__(self):
        self.sent = []

    async def send(self, msg):
        self.sent.append(json.loads(msg))


@pytest.mark.asyncio
async def test_checksum_failure_requests_resubscribe_and_emission_resumes():
    adapter = KrakenV2BookAdapter()  # process_raw_frame is the shared production path

    # Baseline: the snapshot validates and emits.
    assert len(await adapter.process_raw_frame(SNAPSHOT_FRAME)) == 1
    assert adapter._awaiting_resync is False

    # PRODUCTION TRIGGER: a corrupted update fails its checksum -> resync opens and
    # the PRODUCER (_request_snapshot) sets the resubscribe flag. Emission stops.
    corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
    corrupted["data"][0]["bids"][0]["price"] = "45283.7"
    assert await adapter.process_raw_frame(corrupted) == []
    assert adapter._awaiting_resync is True
    assert adapter._pending_resubscribe is True, (
        "the checksum failure must, through production, REQUEST a fresh snapshot — "
        "the producer that was a `pass` stub and latched WO-008b-B off for 48 minutes"
    )

    # PRODUCER acts: the transport sends unsubscribe+subscribe on the live socket.
    ws = _RecordingWS()
    await adapter._maybe_resubscribe(ws)
    assert [m.get("method") for m in ws.sent] == ["unsubscribe", "subscribe"], ws.sent
    assert ws.sent[1]["params"]["channel"] == "book"
    assert adapter._pending_resubscribe is False

    # The fresh snapshot (as Kraken returns it) validates via the EXISTING consumer
    # branch -> the no-emission window CLOSES and emission RESUMES.
    assert len(await adapter.process_raw_frame(SNAPSHOT_FRAME)) == 1
    assert adapter._awaiting_resync is False, "emission must resume once the fresh snapshot validates"
    assert len(await adapter.process_raw_frame(copy.deepcopy(UPDATE_MODIFY_LEVEL))) == 1, (
        "incrementals emit again — the window is truly closed, not just the snapshot"
    )
