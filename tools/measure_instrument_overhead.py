#!/usr/bin/env python3
"""
Measure WO-038 §2.3 instrument overhead.

Measures the per-frame cost of the timing hooks themselves (record_frame_start,
record_frame_end) when the instrument is enabled vs disabled.
"""

from __future__ import annotations

import time
from trading.data.adapters.kraken_v2_book import PerFrameRecord


def measure_overhead(num_frames: int = 1000) -> dict:
    """
    Measure instrument overhead by comparing enabled vs disabled timing.

    Returns the overhead per frame in nanoseconds.
    """
    # Measure with instrument DISABLED (baseline)
    baseline_times = []
    for _ in range(num_frames):
        start = time.perf_counter_ns()
        # Simulate frame processing WITHOUT instrument overhead
        end = time.perf_counter_ns()
        baseline_times.append(end - start)

    # Measure with instrument ENABLED (with overhead)
    record = PerFrameRecord()
    record.enable()
    instrumented_times = []
    for _ in range(num_frames):
        frame_start_wall = time.time()
        frame_start_mono = time.monotonic()
        start = time.perf_counter_ns()
        # Instrument overhead: record_frame_start + record_frame_end
        record.record_frame_start(frame_start_wall, frame_start_mono)
        frame_end_wall = time.time()
        frame_end_mono = time.monotonic()
        record.record_frame_end(frame_end_wall, frame_end_mono)
        end = time.perf_counter_ns()
        instrumented_times.append(end - start)

    # Compute statistics
    baseline_ns = sum(baseline_times) / len(baseline_times)
    instrumented_ns = sum(instrumented_times) / len(instrumented_times)
    overhead_ns = instrumented_ns - baseline_ns

    return {
        "baseline_ns": baseline_ns,
        "instrumented_ns": instrumented_ns,
        "overhead_ns": overhead_ns,
        "overhead_ms": overhead_ns / 1_000_000,
    }


def main():
    print("=" * 70)
    print("WO-038 §2.3 — INSTRUMENT OVERHEAD MEASUREMENT")
    print("=" * 70)
    print()

    result = measure_overhead(num_frames=10000)

    print(f"Baseline (no instrument):     {result['baseline_ns']:.2f} ns")
    print(f"Instrumented (with hooks):   {result['instrumented_ns']:.2f} ns")
    print(f"Instrument overhead:          {result['overhead_ns']:.2f} ns")
    print(f"                               {result['overhead_ms']:.6f} ms")
    print()

    # Detection floor: Windows time.monotonic has ~100ns resolution
    DETECTION_FLOOR_NS = 100
    if result['overhead_ns'] < DETECTION_FLOOR_NS:
        print(f"✓ OVERHEAD BELOW DETECTION FLOOR (< {DETECTION_FLOOR_NS}ns)")
        print("  The timing hooks are below the timer resolution.")
        print("  DISPOSITION: Instrument overhead is immaterial.")
    else:
        print(f"⚠ OVERHEAD ABOVE DETECTION FLOOR (≥ {DETECTION_FLOOR_NS}ns)")
        print(f"  The 15.5ms baseline includes ~{result['overhead_ms']:.3f}ms instrument overhead per frame.")
        print("  DISPOSITION: Baseline should be restated as loop-cost-net-of-instrument.")


if __name__ == "__main__":
    main()
