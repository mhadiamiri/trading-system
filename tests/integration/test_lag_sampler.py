"""
WO-014c-1 §B.1 — the event-loop LAG sampler, the PRIMARY starvation discriminator.

The ruled requirement: a starved-quiet sampler MUST SELF-REPORT. "An instrument that stops
recording under load is measuring its own starvation" — so silence has to become a POSITIVE
signal (expected vs actual sample count + gap timestamps on the shared monotonic clock),
never a false "healthy because quiet."

This drives the REAL sampler coroutine under REAL event-loop starvation (a synchronous
time.sleep that genuinely freezes the loop — starve_event_loop, WO-014c-1 §B.4) and asserts
the record REPORTS the degradation. That is the production trigger path (0.1h): the trigger
for "the sampler reports starvation" is the loop actually being starved, which we cause.

NO NETWORK.
"""

import asyncio
import logging

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, LagSampleRecord
from tests.fixtures.fake_ws_transport import starve_event_loop


@pytest.mark.asyncio
async def test_starved_lag_sampler_self_reports_degradation():
    """Starve the loop for 300ms; the record must REPORT the missed samples + the gap, not go quiet."""
    adapter = KrakenV2BookAdapter()
    record = LagSampleRecord(interval_s=0.02)  # 20ms cadence for a fast, deterministic proof

    task = asyncio.create_task(adapter._sample_event_loop_lag(record))
    await asyncio.sleep(0.08)          # a stretch of healthy sampling (~4 samples)
    await starve_event_loop(0.30)      # REAL 300ms loop freeze -> ~15 intended wakes missed
    await asyncio.sleep(0.08)          # the loop recovers and sampling resumes
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # SELF-REPORTING: the deficit is explicit, not a silent shortfall.
    assert record.expected_samples > record.actual_samples, (
        "a healthy loop would have yielded more samples; the shortfall must be visible"
    )
    assert record.missed_samples > 0
    assert record.missed_fraction > 0.10, (
        f"the 300ms freeze exceeds the 10% VOID fraction; missed_fraction={record.missed_fraction:.2f}"
    )
    # The starvation is localizable: the ~300ms freeze is a GAP identified by timestamp.
    assert any(dur >= 0.25 for (_start, _end, dur) in record.gaps), (
        f"the ~300ms freeze must be reported as a gap with its timestamps; gaps={record.gaps}"
    )


@pytest.mark.asyncio
async def test_check_instruments_gappy_emits_declared_code(caplog):
    """Branch 5: a gappy record emits INSTRUMENTS_GAPPY (the run carries its own VOID reason)."""
    adapter = KrakenV2BookAdapter()
    record = LagSampleRecord(interval_s=0.1)
    record.started_monotonic = 0.0
    record.ended_monotonic = 10.0                              # expected 100 samples
    record.samples = [(0.1 * i, 0.0) for i in range(50)]      # only 50 -> 50% missed (> 10% VOID)
    record.gaps = [(2.0, 7.0, 5.0)]

    with caplog.at_level(logging.ERROR):
        gappy = adapter._check_instruments_gappy(record)

    assert gappy is True
    assert "INSTRUMENTS_GAPPY" in caplog.text
    # A clean record does NOT emit it.
    caplog.clear()
    clean = LagSampleRecord(interval_s=0.1)
    clean.started_monotonic = 0.0
    clean.ended_monotonic = 10.0
    clean.samples = [(0.1 * i, 0.0) for i in range(99)]       # 99/100 -> 1% missed (< 10%)
    with caplog.at_level(logging.ERROR):
        assert adapter._check_instruments_gappy(clean) is False
    assert "INSTRUMENTS_GAPPY" not in caplog.text
