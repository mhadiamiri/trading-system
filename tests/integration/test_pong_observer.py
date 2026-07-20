"""
WO-014c-1 §B.2 — protocol-level PONG observer (sanctioned ws.ping()).

The observer issues ws.ping() — an RFC 6455 §5.5.2 control frame, the PROTOCOL layer whose
timeout threw the 1011, NOT Kraken's application {"method":"ping"} — and records the per-ping
RTT distribution the branches need.

THE RULING THAT MATTERS MOST (carryover #1): a MISSED SEND (task starved) is GAPPINESS; a
ping SENT with no pong is an ABSENT PONG — a SIGNAL (Branch 1/3), NEVER gappiness. Conflating
them would VOID a run where Kraken genuinely stops answering — the strongest protocol-side
evidence — as instrument failure. The second test proves that distinction is load-bearing.

NO NETWORK; the protocol ping is answered (or not) by the fake socket's ping() future.
"""

import asyncio

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, PongRecord
from tests.fixtures.fake_ws_transport import FakeWebSocket


@pytest.mark.asyncio
async def test_pong_observer_records_rtt_distribution_via_protocol_ping():
    """Responsive socket -> per-ping RTTs recorded; ws.ping() (RFC 6455 control frame) is used."""
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._websocket = FakeWebSocket([], pong_rtt=0.02)   # answers every protocol ping, 20ms RTT
    record = PongRecord(interval_s=0.02, absent_timeout_s=0.10)

    task = asyncio.create_task(adapter._observe_protocol_pong(record))
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert adapter._websocket.pings_received > 0, "the observer must call ws.ping() (the RFC 6455 frame)"
    assert record.pings_sent > 0
    assert record.pongs_received > 0
    assert record.pongs_absent == 0
    # It is the DISTRIBUTION, not a scalar: multiple per-ping RTT samples.
    rtts = [rtt for (_ts, rtt) in record.samples if rtt is not None]
    assert len(rtts) >= 2 and all(abs(r - 0.02) < 1e-6 for r in rtts)


@pytest.mark.asyncio
async def test_absent_pongs_are_a_signal_not_gappiness():
    """
    THE BITE PROOF (carryover #1). Every ping is SENT successfully but no pong returns. The
    observer must record ABSENT pongs (a signal) and stay NOT gappy — gappiness is missed
    SENDS only. Terminates in the observable end state: pongs_absent registered, not gappy.
    """
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._websocket = FakeWebSocket([], pong_rtt=None)    # SENDS succeed; pong never comes
    record = PongRecord(interval_s=0.02, absent_timeout_s=0.05)

    task = asyncio.create_task(adapter._observe_protocol_pong(record))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert record.pings_sent > 0, "the sends themselves succeed"
    assert record.pongs_absent > 0, "no pong came back -> ABSENT pongs registered as a signal"
    assert record.pongs_received == 0
    # THE RULED DISTINCTION: absent pongs do NOT inflate gappiness (which is missed SENDS only).
    assert record.missed_send_fraction < 0.10, (
        f"all pings were SENT, so the observer is not gappy; missed_send_fraction="
        f"{record.missed_send_fraction:.2f} — absent pongs must not count as missed sends"
    )
    assert adapter._check_instruments_gappy(pong_record=record) is False, (
        "a run where the venue stops answering is Branch 1/3 evidence, never a VOID"
    )
