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


# ── WO-016 §B (D27): the three-component OR-gate — each component witnessed in isolation ──

@pytest.mark.asyncio
async def test_void_gate_uniform_drift_catches_the_counterfactual(caplog):
    """THE D27 COUNTERFACTUAL. A UNIFORM ~199ms cycle (cycle time doubled, temporal resolution
    halved) records ZERO gaps (199ms < 200ms) and ZERO elevated samples (lag 99ms < 100ms) — it
    escapes DISCRETE and SPIKY entirely — yet the mean-cycle-drift component catches it. This is
    the mode the two-metric proposal would have missed; it is why component (3) exists."""
    adapter = KrakenV2BookAdapter()
    rec = LagSampleRecord(interval_s=0.1)
    rec.started_monotonic = 0.0
    rec.ended_monotonic = 100.0
    rec.samples = [(0.199 * i, 0.099) for i in range(502)]   # ~199ms cadence, lag 99ms (<100ms)
    rec.gaps = []                                            # 199ms < 200ms -> no recorded gaps
    # the other two components are BLIND to it:
    assert rec.recorded_gap_fraction == 0.0
    assert rec.elevated_lag_fraction(adapter.ELEVATED_LAG_THRESHOLD_SECONDS) == 0.0
    # but drift is unmissable (~83% above the 108.886ms frozen baseline):
    with caplog.at_level(logging.ERROR):
        assert adapter._check_instruments_gappy(rec) is True
    assert "UNIFORM" in caplog.text and "INSTRUMENTS_GAPPY" in caplog.text


@pytest.mark.asyncio
async def test_void_gate_spiky_component_fires_on_count_not_time(caplog):
    """SPIKY: many moderate spikes exceed the >5% COUNT fraction while their total TIME stays
    under the DISCRETE 10% — the shape recorded-gaps (time-fraction) alone would miss."""
    adapter = KrakenV2BookAdapter()
    rec = LagSampleRecord(interval_s=0.1)
    rec.started_monotonic = 0.0
    rec.ended_monotonic = 100.0
    rec.samples = [(0.1 * i, 0.11 if i < 60 else 0.0) for i in range(1000)]  # 6% elevated
    rec.gaps = [(float(i), float(i) + 0.11, 0.11) for i in range(60)]        # 6.6s = 6.6% < 10%
    assert rec.recorded_gap_fraction < adapter.RECORDED_GAP_VOID_FRACTION     # DISCRETE clean
    assert rec.mean_cycle_s < adapter.MEAN_CYCLE_BASELINE_SECONDS             # UNIFORM clean
    with caplog.at_level(logging.ERROR):
        assert adapter._check_instruments_gappy(rec) is True
    assert "SPIKY" in caplog.text


@pytest.mark.asyncio
async def test_void_gate_faster_than_baseline_is_not_drift(caplog):
    """Drift is SIGNED: a cycle FASTER than the frozen baseline is health, not degradation."""
    adapter = KrakenV2BookAdapter()
    rec = LagSampleRecord(interval_s=0.1)
    rec.started_monotonic = 0.0
    rec.ended_monotonic = 100.0
    rec.samples = [(0.1 * i, 0.0) for i in range(1000)]   # mean cycle 100ms < 108.886ms baseline
    rec.gaps = []
    with caplog.at_level(logging.ERROR):
        assert adapter._check_instruments_gappy(rec) is False
    assert "INSTRUMENTS_GAPPY" not in caplog.text
