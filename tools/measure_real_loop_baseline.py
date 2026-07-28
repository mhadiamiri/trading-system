#!/usr/bin/env python3
"""
WO-038 CLOSEOUT-3 — Measure the REAL per-frame loop with REAL processing.

This harness drives the committed PerFrameRecord instrument (e6892d9) with
GROUND-TRUTH Kraken v2 fixture frames through the ACTUAL production path:
parse → CRC32 checksum validation → book update → MarketState construction.

NO artificial delays on the measured path. The measurement is pure processing cost.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

# Add src and tests to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from fixtures.fake_ws_transport import ScriptedConnectionFactory
from fixtures.kraken_v2_raw_frames import (
    ALL_BOOK_FRAMES,
    SNAPSHOT_FRAME,
    UPDATE_MODIFY_LEVEL,
)
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter


async def measure_real_loop_baseline() -> dict[str, Any]:
    """
    Drive the committed instrument with REAL frames through the REAL processing path.

    Returns:
        Distribution metrics (median, p95, p99, max) of per-frame processing time.
    """
    print("=" * 70)
    print("WO-038 CLOSEOUT-3 — REAL LOOP BASELINE MEASUREMENT")
    print("=" * 70)
    print()
    print(f"Fixture corpus: {len(ALL_BOOK_FRAMES)} frames")
    print(f"  - 1 snapshot (GROUND_TRUTH: Kraken docs)")
    print(f"  - 3 incremental updates (self-generated)")
    print()
    print("Processing path: REAL parse → CRC32 validation → book update → state")
    print("Artificial delays: NONE")
    print()

    # Build adapter in LIVE mode (required for get_live_market_data)
    # Use real clocks (no fake time injection — we want real processing cost)
    factory = ScriptedConnectionFactory([ALL_BOOK_FRAMES], on_drain="timeout")
    adapter = KrakenV2BookAdapter(
        mode=KrakenV2BookAdapter.MODE_LIVE,
        connect_fn=factory.connect,
    )

    # Fixture mode: no persistence required for this measurement
    adapter._persistence_optional = True

    # Enable the committed PerFrameRecord instrument
    adapter._per_frame_record.enable()
    print("Instrument: PerFrameRecord ENABLED (e6892d9)")
    print(f"  enabled: {adapter._per_frame_record.enabled}")
    print()

    # Drive frames through the REAL get_live_market_data path
    # This goes through the instrumented loop with hooks at lines 2903 and 2963
    start_time = time.monotonic()
    states_collected = 0

    print("Processing frames...")
    async for state in adapter.get_live_market_data(duration_seconds=10.0):
        states_collected += 1
        if states_collected % 1 == 0:
            print(f"  Collected {states_collected} states...")
            print(f"  Raw frames received: {adapter._raw_received}")
            print(f"  Timings collected: {len(adapter._per_frame_record.timings)}")

    elapsed = time.monotonic() - start_time
    print()
    print(f"Collected {states_collected} states in {elapsed:.3f}s")
    print()

    # Extract the per-frame timing distribution from the instrument
    distro = adapter._per_frame_record.compute_distribution()

    if not distro or distro.get("count", 0) == 0:
        print("ERROR: No frame timing data collected!")
        print("The instrument may not be properly installed.")
        return {}

    return {
        "n": distro["count"],
        "wall_ns": distro["wall"],
        "mono_ns": distro["mono"],
    }


def _write_artifact(data: dict[str, Any], path: Path) -> None:
    """Write measurement artifact with sha256 verification."""
    path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(path, "w"), indent=2)
    # Compute sha256
    import hashlib
    sha256 = hashlib.sha256(open(path, "rb").read()).hexdigest()
    print(f"Artifact written: {path}")
    print(f"sha256: {sha256}")
    print()
    return sha256


async def main():
    result = await measure_real_loop_baseline()

    if not result:
        print("FAILED — no timing data collected")
        return

    print("=" * 70)
    print("REAL-FRAME DISTRIBUTION — PER-FRAME PROCESSING COST")
    print("=" * 70)
    print()
    print("Wall clock:")
    print(f"  Median: {result['wall_ns']['median_ns'] / 1_000_000:.3f} ms")
    print(f"  P95:   {result['wall_ns']['p95_ns'] / 1_000_000:.3f} ms")
    print(f"  P99:   {result['wall_ns']['p99_ns'] / 1_000_000:.3f} ms")
    print(f"  Max:   {result['wall_ns']['max_ns'] / 1_000_000:.3f} ms")
    print()
    print("Monotonic:")
    print(f"  Median: {result['mono_ns']['median_ns'] / 1_000_000:.3f} ms")
    print(f"  P95:   {result['mono_ns']['p95_ns'] / 1_000_000:.3f} ms")
    print(f"  P99:   {result['mono_ns']['p99_ns'] / 1_000_000:.3f} ms")
    print(f"  Max:   {result['mono_ns']['max_ns'] / 1_000_000:.3f} ms")
    print()
    print(f"N frames: {result['n']}")
    print()

    # Sanity check: this is real processing cost (parse + checksum + book + state)
    # Should be plausibly in the microsecond-to-low-millisecond range for full-depth L2 book
    median_ms = result['wall_ns']['median_ns'] / 1_000_000
    if median_ms < 0.001:
        print("⚠ PLAUSIBILITY CHECK: Median < 1µs — suspiciously low")
        print("  This may indicate the checksum/parse isn't actually running.")
    elif median_ms > 50:
        print(f"⚠ PLAUSIBILITY CHECK: Median {median_ms:.1f}ms — suspiciously high")
        print("  Real parse+CRC32+book-update should be sub-50ms for L2 book.")
    else:
        print(f"✓ PLAUSIBILITY CHECK: {median_ms:.3f}ms is physically reasonable")
        print("  Parse + CRC32 + book-update for full-depth L2 book.")

    print()
    print("Writing artifacts...")
    artifact_path = Path("tools/.artifacts/real_loop_baseline.json")
    _write_artifact(result, artifact_path)


if __name__ == "__main__":
    asyncio.run(main())
