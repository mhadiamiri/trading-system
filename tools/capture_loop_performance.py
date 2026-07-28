#!/usr/bin/env python3
"""
Capture-Loop Performance Instrument (WO-038 §3)

Measures the ACTUAL per-frame loop of `get_live_market_data` — the code path
WO-023 §7 established has no observer. The instrument measures per-iteration
wall+monotonic timing at the loop's real boundaries (frame received → MarketState emitted).

Instrument writes to .artifacts/ (WO-032 boundary); baseline is a deliberate snapshot
into evidence/WO-038/ (WO-026 stream-vs-snapshot doctrine).

PER-FORMANCE-LOOP BOUNDARIES (the hot path):
- START: Frame received from websocket (last_frame monotonic)
- END: After all MarketStates yielded for this frame
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter


@dataclass
class PerFrameTimings:
    """Per-iteration timing measurements."""

    frame_wall_start: float
    frame_mono_start: float
    frame_wall_end: float
    frame_mono_end: float

    @property
    def wall_duration_ns(self) -> int:
        """Wall-clock duration in nanoseconds."""
        return int((self.frame_wall_end - self.frame_wall_start) * 1e9)

    @property
    def mono_duration_ns(self) -> int:
        """Monotonic-clock duration in nanoseconds."""
        return int((self.frame_mono_end - self.frame_mono_start) * 1e9)


@dataclass
class Distribution:
    """Statistical distribution of timings."""

    median_ns: int
    p95_ns: int
    p99_ns: int
    max_ns: int
    count: int

    def to_dict(self) -> dict:
        return {
            "median_ns": self.median_ns,
            "p95_ns": self.p95_ns,
            "p99_ns": self.p99_ns,
            "max_ns": self.max_ns,
            "count": self.count,
        }


@dataclass
class InstrumentResult:
    """Result of the performance instrument run."""

    wall_distribution: Distribution
    mono_distribution: Distribution
    raw_timings: list[PerFrameTimings] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "wall_distribution": self.wall_distribution.to_dict(),
            "mono_distribution": self.mono_distribution.to_dict(),
        }


class CaptureLoopInstrument:
    """
    Instruments the per-frame loop of `get_live_market_data`.

    The instrument WRAPS the adapter and intercepts at the loop's REAL boundaries:
    - When a frame arrives (websocket recv)
    - After all MarketStates for that frame are yielded

    APPARATUS HONESTY (D41): The instrument's timing reads themselves are NOT on the
    hot path being measured. We capture frame arrival time from the adapter's own
    `last_frame` read (line 2777 in kraken_v2_book.py) and capture emission time
    AFTER the yield completes — the measurement overhead is OUTSIDE the measured interval.

    SEPARATION OF INSTRUMENT COST FROM LOOP COST:
    - Frame arrival time: Read from adapter's existing `last_frame` variable (already measured)
    - Emission time: Captured AFTER the yield returns, not before
    - Distribution computation: Post-hoc, outside the capture loop
    - File write: After capture ends, .artifacts/ (WO-032 boundary)

    Therefore the instrument's own cost does NOT inflate the measured loop cost.
    """

    def __init__(self, adapter: KrakenV2BookAdapter):
        self._adapter = adapter
        self._timings: list[PerFrameTimings] = []

    def record_frame_start(self, wall_start: float, mono_start: float) -> None:
        """Record when a frame arrives (called at loop boundary, before yield)."""
        # Store start time for this frame; will be paired with end time after yield
        self._frame_start_wall = wall_start
        self._frame_start_mono = mono_start

    def record_frame_end(self, wall_end: float, mono_end: float) -> None:
        """Record after MarketState emission completes (called after yield)."""
        timing = PerFrameTimings(
            frame_wall_start=self._frame_start_wall,
            frame_mono_start=self._frame_start_mono,
            frame_wall_end=wall_end,
            frame_mono_end=mono_end,
        )
        self._timings.append(timing)

    def compute_distribution(self) -> InstrumentResult:
        """Compute statistical distribution from captured timings."""
        if not self._timings:
            raise ValueError("No timings captured — instrument did not observe any frames")

        wall_durations_ns = [t.wall_duration_ns for t in self._timings]
        mono_durations_ns = [t.mono_duration_ns for t in self._timings]

        wall_dist = Distribution(
            median_ns=int(statistics.median(wall_durations_ns)),
            p95_ns=int(statistics.quantiles(wall_durations_ns, n=100)[94]),  # 0-indexed
            p99_ns=int(statistics.quantiles(wall_durations_ns, n=100)[98]),
            max_ns=max(wall_durations_ns),
            count=len(wall_durations_ns),
        )

        mono_dist = Distribution(
            median_ns=int(statistics.median(mono_durations_ns)),
            p95_ns=int(statistics.quantiles(mono_durations_ns, n=100)[94]),
            p99_ns=int(statistics.quantiles(mono_durations_ns, n=100)[98]),
            max_ns=max(mono_durations_ns),
            count=len(mono_durations_ns),
        )

        return InstrumentResult(
            wall_distribution=wall_dist,
            mono_distribution=mono_dist,
            raw_timings=self._timings,
        )


async def run_with_instrument(
    adapter: KrakenV2BookAdapter,
    duration_seconds: float,
    injected_delay_ns: int = 0,
) -> InstrumentResult:
    """
    Run a capture with the instrument.

    Args:
        adapter: The live Kraken adapter (must be in MODE_LIVE)
        duration_seconds: Capture duration
        injected_delay_ns: Optional injected delay per frame (for bite proof)

    Returns:
        InstrumentResult with distribution statistics
    """
    instrument = CaptureLoopInstrument(adapter)

    # Patch the adapter's clock to inject delay if requested (bite proof)
    original_monotonic = adapter._monotonic_clock
    injected = 0

    def delayed_monotonic() -> float:
        """Clock that injects delay on first read per frame."""
        nonlocal injected
        result = original_monotonic()
        if injected_delay_ns > 0 and injected == 0:
            # Inject delay on first call
            time.sleep(injected_delay_ns / 1e9)
            injected += 1
            return original_monotonic()
        return result

    if injected_delay_ns > 0:
        adapter._monotonic_clock = delayed_monotonic

    # Run the capture loop, instrumenting at the boundaries
    # Note: We instrument by wrapping the generator
    async for market_state in adapter.get_live_market_data(duration_seconds):
        # Frame has arrived and been processed; about to be yielded
        # Record end time AFTER yield (outside the measured interval)
        wall_now = time.time()
        mono_now = time.monotonic()
        # We would need to record this after the yield, but we can't intercept that
        # without modifying the adapter. For now, we'll measure from last_frame.
        # This is a limitation of wrapping vs. patching.
        # See §3.4 bite proof requirement — we need to prove we observe the real path.
        pass

    # For now, return a placeholder until we implement proper instrumentation
    # The proper implementation requires either:
    # 1. Patching the adapter to add instrument hooks
    # 2. Subclassing and overriding the loop
    # 3. Adding instrumentation points to the adapter itself
    raise NotImplementedError(
        "Instrument implementation pending — requires adapter modification "
        "or subclassing to measure at the real loop boundaries."
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Capture-loop performance instrument (WO-038 §3)"
    )
    parser.add_argument(
        "--duration", type=float, default=10.0, help="Capture duration in seconds"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".artifacts/capture_loop_performance"),
        help="Output directory (WO-032: writes to .artifacts/)",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("evidence/WO-038"),
        help="Snapshot directory for deliberate baseline snapshot",
    )
    args = parser.parse_args()

    print("Capture-loop performance instrument (WO-038 §3)")
    print("Implementation pending — requires adapter modification for boundary hooks")
    print(f"Output would go to: {args.output_dir}")
    print(f"Baseline snapshot would go to: {args.snapshot}")


if __name__ == "__main__":
    main()
