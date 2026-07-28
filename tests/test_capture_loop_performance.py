"""
Capture-Loop Performance Instrument (WO-038 §3)

Tests that measure the ACTUAL per-frame loop of `get_live_market_data`.

The per-frame loop is the code path from when a frame arrives (websocket recv) to when
MarketState is yielded. WO-023 §7 established this path has no observer — the throughput
re-baseline was VOID because it measured an adjacent path.

§3.4 BITE PROOF: Inject known delay → measured distribution shifts. Remove → returns.
This proves the instrument observes the REAL loop, not an adjacent path. WITHOUT THIS,
the number is unproven and the WO STOPs.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
def kraken_v2_adapter():
    """Fixture mode adapter for testing (no socket)."""
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    return KrakenV2BookAdapter(mode="fixture")


@pytest.fixture
def sample_market_data():
    """Sample market data frames for testing."""
    # Minimal valid book frame
    return [
        {
            "channel": "book",
            "type": "snapshot",
            "data": {
                "symbol": "BTC/USD",
                "bids": [["50000.0", "1.0"]],
                "asks": [["50001.0", "1.0"]],
            },
        }
    ]


class TestPerFrameInstrument:
    """
    Tests for the per-frame performance instrument.

    APPARATUS HONESTY (D41): Timing reads are NOT on the hot path.
    - Frame arrival time from adapter's existing `last_frame` read
    - Emission time captured AFTER processing completes, BEFORE yield
    - Instrument cost is OUTSIDE the measured interval
    """

    def test_per_frame_record_exists(self, kraken_v2_adapter):
        """The PerFrameRecord class exists and has the required interface."""
        from trading.data.adapters.kraken_v2_book import PerFrameRecord

        record = PerFrameRecord()
        assert hasattr(record, "enabled")
        assert hasattr(record, "timings")
        assert hasattr(record, "enable")
        assert hasattr(record, "record_frame_start")
        assert hasattr(record, "record_frame_end")
        assert hasattr(record, "compute_distribution")

    def test_adapter_has_per_frame_record(self, kraken_v2_adapter):
        """Adapter has a _per_frame_record attribute."""
        assert hasattr(kraken_v2_adapter, "_per_frame_record")
        assert kraken_v2_adapter._per_frame_record is not None
        assert kraken_v2_adapter._per_frame_record.enabled is False  # Disabled by default

    def test_enable_starts_collection(self, kraken_v2_adapter):
        """enable() starts timing collection and resets state."""
        record = kraken_v2_adapter._per_frame_record
        record.enable()

        assert record.enabled is True
        assert len(record.timings) == 0
        assert record.start_monotonic > 0

    def test_compute_distribution_returns_stats(self, kraken_v2_adapter):
        """compute_distribution() returns median, p95, p99, max, count."""
        from trading.data.adapters.kraken_v2_book import PerFrameTiming

        record = kraken_v2_adapter._per_frame_record
        record.enable()

        # Simulate some frame timings
        record._frame_start_wall = 0.0
        record._frame_start_mono = 0.0
        record.record_frame_end(wall_ts=0.001, mono_ts=0.001)  # 1ms
        record.record_frame_end(wall_ts=0.002, mono_ts=0.002)  # 1ms
        record.record_frame_end(wall_ts=0.003, mono_ts=0.003)  # 1ms

        dist = record.compute_distribution()

        assert "wall" in dist
        assert "mono" in dist
        assert "count" in dist
        assert dist["count"] == 3
        assert "median_ns" in dist["wall"]
        assert "p95_ns" in dist["wall"]
        assert "p99_ns" in dist["wall"]
        assert "max_ns" in dist["wall"]

    def test_disabled_record_does_not_collect(self, kraken_v2_adapter):
        """When disabled, record_frame_start/end do nothing."""
        record = kraken_v2_adapter._per_frame_record
        assert record.enabled is False

        record.record_frame_start(0.0, 0.0)
        record.record_frame_end(0.001, 0.001)

        # When disabled, no timings are added. The timings list might be the dataclass
        # field descriptor on the class, so we compute_distribution to check count.
        dist = record.compute_distribution()
        assert dist["count"] == 0


class TestInstrumentBiteProof:
    """
    §3.4 BITE PROOF: The instrument observes the REAL loop.

    Inject a known per-frame delay → the measured distribution shifts.
    Remove it → returns to baseline.

    This proves the instrument sees the actual per-frame loop — measuring
    an adjacent path would NOT show the shift.
    """

    def test_injected_delay_shifts_distribution(self, kraken_v2_adapter, sample_market_data):
        """
        BITE PROOF — Mutation A: Inject delay, distribution shifts.

        This is the ANTI-VOID proof that the instrument observes the real path.
        Without this, the baseline number is unproven and the WO STOPs.
        """
        # This test requires a fixture-driven run with known frame timing
        # Implementation pending — requires feeding frames through the adapter
        # with controlled timing

        # TODO: Implement fixture-driven capture with injectable delay
        # Expected: When we inject a 10ms delay per frame, the measured
        # distribution's median/p95/p99 should shift by approximately 10ms
        pytest.skip("Bite proof implementation pending — requires fixture-driven capture")

    def test_removed_delay_returns_to_baseline(self, kraken_v2_adapter, sample_market_data):
        """
        BITE PROOF — Mutation B (restoration): Remove delay, returns to baseline.

        Preservation dual of Mutation A.
        """
        pytest.skip("Bite proof implementation pending — requires fixture-driven capture")


class TestSevenDimensions:
    """
    §4: Baseline capture with all seven D35-4 dimensions declared.

    The baseline number is meaningless without the dimensions and MUST NOT
    be quoted without them downstream.
    """

    def test_baseline_captures_all_dimensions(self):
        """
        Capture baseline with HOST, LOAD, SOURCE, DURATION, RESOLUTION,
        INSTRUMENT, INTERPRETER declared.
        """
        pytest.skip("§4 implementation pending — requires §3 completion")

    def test_host_suspend_gate_gates_validity(self):
        """
        HOST-SUSPEND GATE (D24): The host-suspend detector must run for the
        duration of baseline capture and report ZERO suspend events.

        If ANY divergence occurs, the baseline is VOID — do not record a
        contaminated number.
        """
        pytest.skip("§4 implementation pending — requires host-suspend verification")
