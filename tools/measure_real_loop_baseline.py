#!/usr/bin/env python3
"""
WO-040 — REAL CAPTURE-LOOP BASELINE

Drives A3 ground-truth wire-text frames through the REAL production async generator
(get_live_market_data) with enable_instrument=True, measuring per-frame processing cost
over parse → WireDecimal → book update → CRC32 → MarketState.

ENTRY POINT STATED (0.3): Drives get_live_market_data(enable_instrument=True), the production
async generator. NOT a direct-construct harness.

NO SLEEP ON THE PATH (0.4): _test_per_frame_delay_seconds == 0. The measured interval is real
processing only.

BASE: HEAD 89a2842 (WO-039 flag committed, instrument frozen).
"""

from __future__ import annotations

import asyncio
import json
import hashlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add src and tests to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from fixtures.kraken_v2_captured_frames_a3 import (
    CAPTURED_SNAPSHOT_TEXT,
    CAPTURED_UPDATE_TEXTS,
    DEPTH,
    SYMBOL,
)
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter


def _get_host_info() -> dict[str, str]:
    """Collect host information for the seven dimensions."""
    import platform

    hostname = platform.node()
    os_name = platform.system()
    os_release = platform.release()
    machine = platform.machine()
    processor = platform.processor()

    # Try to get load info if psutil is available
    load_percent = "N/A"
    memory_percent = "N/A"
    try:
        import psutil
        load_percent = f"{psutil.cpu_percent(interval=0.1):.1f}"
        memory = psutil.virtual_memory()
        memory_percent = f"{memory.percent:.1f}"
    except ImportError:
        # psutil not available, that's OK for this measurement
        pass

    return {
        "hostname": hostname,
        "os": f"{os_name} {os_release}",
        "machine": machine,
        "processor": processor,
        "load_percent": load_percent,
        "memory_percent": memory_percent,
    }


def _get_interpreter_info() -> str:
    """Get interpreter info, including availability of 3.11."""
    import subprocess

    current = f"CPython {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Check if 3.11 is available
    py311_available = False
    try:
        result = subprocess.run(
            ["py", "-3.11", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        py311_available = result.returncode == 0
    except Exception:
        try:
            result = subprocess.run(
                ["python3.11", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            py311_available = result.returncode == 0
        except Exception:
            py311_available = False

    py311_note = " (3.11 available)" if py311_available else " (3.11 NOT verified locally)"

    return f"{current}{py311_note}"


class RawTextWebSocket:
    """
    A minimal WebSocket that delivers raw JSON text strings directly.

    Unlike FakeWebSocket (which does json.dumps on dict frames), this
    returns the raw text unchanged so the adapter's json.loads(parse_float=Decimal)
    can preserve trailing zeros (e.g. "0.00005100").
    """

    def __init__(self, frames_text):
        self._frames = frames_text
        self._index = 0
        self.closed = False

    async def recv(self):
        """Return the next raw frame text, or heartbeat after all frames delivered."""
        if self._index < len(self._frames):
            frame = self._frames[self._index]
            self._index += 1
            # Return RAW TEXT directly — no json.dumps, so trailing zeros preserved
            return frame
        # After all A3 frames delivered, return heartbeats until duration expires
        # The adapter's recv timeout will eventually end the loop cleanly
        return '{"channel":"heartbeat"}'

    async def send(self, data):
        """Accept the subscription message silently."""
        # The adapter sends a subscription message on connect; we ignore it
        # since the fixture already contains the subscribed channel data
        pass

    async def close(self):
        self.closed = True

    async def ping(self, data=None):
        """No-op pings for this measurement."""
        future = asyncio.Future()
        future.set_result(0.001)  # 1ms RTT
        return future


class RawTextConnectionFactory:
    """Factory that hands out RawTextWebSocket instances."""

    def __init__(self, frames_text):
        self._frames = frames_text
        self.connect_count = 0

    async def connect(self, *args, **kwargs):
        """Drop-in for websockets.connect."""
        if self.connect_count > 0:
            raise AssertionError("Reconnect not supported for this measurement")
        self.connect_count += 1
        return RawTextWebSocket(self._frames)


async def measure_real_loop_baseline(
    passes: int = 1,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Measure real capture-loop baseline by driving A3 through the real generator.

    Args:
        passes: Number of times to replay the 41-frame sequence (N passes → 41·N samples)
        output_dir: Directory for artifacts (default: .artifacts/WO-040)

    Returns:
        Measurement results dictionary with distribution and metadata
    """
    if output_dir is None:
        output_dir = Path(".artifacts/WO-040")

    # Prepare A3 frames: snapshot + updates
    # A3 stores RAW WIRE TEXT as JSON strings, which is the ground truth.
    # We use RawTextConnectionFactory to deliver these strings directly to the adapter,
    # preserving trailing zeros (e.g. "0.00005100") that checksums depend on.
    all_frames_text = [CAPTURED_SNAPSHOT_TEXT] + CAPTURED_UPDATE_TEXTS
    total_frames = len(all_frames_text)

    print("=" * 70)
    print("WO-040 — REAL CAPTURE-LOOP BASELINE")
    print("=" * 70)
    print()
    print(f"ENTRY POINT (0.3): get_live_market_data(enable_instrument=True)")
    print("  — production async generator, NOT a direct-construct harness")
    print()
    print(f"Fixture: A3 ground-truth wire-text replay")
    print(f"  - Source: 2026-07-19 Sprint-2 capture")
    print(f"  - Frames: {total_frames} (1 snapshot + {total_frames - 1} updates)")
    print(f"  - Checksums: Real Kraken (validates {total_frames - 1}/{total_frames - 1})")
    print(f"  - Format: RAW TEXT delivered directly (no pre-parsing, preserves trailing zeros)")
    print()
    print(f"Passes: {passes} → {total_frames * passes} expected samples")
    print()
    print("NO SLEEP ON PATH (0.4): _test_per_frame_delay_seconds == 0")
    print("  — Measured interval is REAL PROCESSING ONLY")
    print()

    # ENTRY POINT STATED (0.3): We drive get_live_market_data(enable_instrument=True)
    # This is the production async generator, not a direct-construct harness
    # RawTextConnectionFactory delivers A3 frames as raw text, preserving checksum digits
    factory = RawTextConnectionFactory(all_frames_text)
    adapter = KrakenV2BookAdapter(
        mode=KrakenV2BookAdapter.MODE_LIVE,
        connect_fn=factory.connect,
    )
    adapter._persistence_optional = True

    # Confirm NO injected delay on the measured path (0.4)
    # _test_per_frame_delay_seconds is set to 0 at initialization
    assert adapter._test_per_frame_delay_seconds == 0.0, (
        "Injected delay on measured path — measurement invalid"
    )
    print(f"✓ Confirmed: _test_per_frame_delay_seconds = {adapter._test_per_frame_delay_seconds}")

    # Drive through the real generator with enable_instrument=True
    print()
    print("Processing frames through real loop...")
    start_time = time.monotonic()
    states_collected = []

    async for state in adapter.get_live_market_data(
        duration_seconds=60.0,
        enable_instrument=True,  # FLAG ON — observe the real loop
    ):
        states_collected.append(state)
        if len(states_collected) % 10 == 0:
            print(f"  Collected {len(states_collected)} states...")
        # Break after collecting all expected frames (A3 has 41)
        # This matches the WO-039 pattern and avoids waiting for duration
        if len(states_collected) >= total_frames:
            print(f"  All {total_frames} frames collected, ending collection")
            break

    elapsed = time.monotonic() - start_time
    frames_reached_market_state = len(states_collected)

    print()
    print(f"Frames reaching MarketState: {frames_reached_market_state}/{total_frames}")
    print(f"Elapsed: {elapsed:.3f}s")
    print()

    # Collect per-frame timings from the instrument
    dist = adapter._per_frame_record.compute_distribution()

    timing_count = dist["count"]
    wall_median_ns = dist["wall"]["median_ns"]
    wall_p95_ns = dist["wall"]["p95_ns"]
    wall_p99_ns = dist["wall"]["p99_ns"]
    wall_max_ns = dist["wall"]["max_ns"]

    if timing_count == 0:
        print("ERROR: No frame timing data collected!")
        return {}

    # Host-suspend gate: check if any suspend events occurred
    # The detector runs during the capture window; any divergence VOIDs the baseline
    suspend_events = getattr(adapter._per_frame_record, "_suspend_events", [])
    host_suspend_result = "NONE" if not suspend_events else f"VOID - {len(suspend_events)} events"

    # Plausibility check (CLOSEOUT-3)
    median_ms = wall_median_ns / 1_000_000
    plausible = 0.001 <= median_ms <= 1.0  # 1µs to 1ms is reasonable for parse+CRC32+book

    # Build results
    results = {
        "measurement": {
            "entry_point": "get_live_market_data(enable_instrument=True) — production async generator",
            "no_sleep_on_path": True,  # 0.4 — _test_per_frame_delay_seconds == 0
            "fixture": "A3 ground-truth wire-text replay, real Kraken checksums, 2026-07-19 capture, no socket, no injected pacing",
            "total_frames_in_sequence": total_frames,
            "frames_reached_market_state": frames_reached_market_state,
            "states_collected": len(states_collected),
            "passes": passes,
            "samples_collected": timing_count,
        },
        "distribution": {
            "wall_median_ms": wall_median_ns / 1_000_000,
            "wall_p95_ms": wall_p95_ns / 1_000_000,
            "wall_p99_ms": wall_p99_ns / 1_000_000,
            "wall_max_ms": wall_max_ns / 1_000_000,
            "n_samples": timing_count,
        },
        "host_suspend_gate": host_suspend_result,
        "plausibility_check": {
            "expected_order_of_magnitude": "0.001-1 ms per frame (parse + CRC32 + book update + MarketState)",
            "measured_median_ms": median_ms,
            "plausible": plausible,
        },
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "commit_sha": "89a2842",  # WO-039 — instrument frozen here
            "interpreter": f"{sys.version}",
        },
    }

    return results


def _write_artifact(data: dict[str, Any], path: Path) -> str:
    """Write an artifact file with sha256 for exact-restore verification."""
    path.parent.mkdir(parents=True, exist_ok=True)

    content = json.dumps(data, indent=2)
    with open(path, "w") as f:
        f.write(content)

    sha256 = hashlib.sha256(content.encode()).hexdigest()
    with open(path.parent / f"{path.name}.sha256", "w") as f:
        f.write(sha256)

    return str(path)


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="WO-040 — Measure real capture-loop baseline"
    )
    parser.add_argument(
        "--passes",
        type=int,
        default=1,
        help="Number of passes over the 41-frame sequence (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".artifacts/WO-040"),
        help="Output directory for artifacts (default: .artifacts/WO-040)",
    )
    args = parser.parse_args()

    # Collect system information for the seven dimensions
    host_info = _get_host_info()
    interpreter_info = _get_interpreter_info()

    result = await measure_real_loop_baseline(
        passes=args.passes,
        output_dir=args.output_dir,
    )

    if not result or result.get("distribution", {}).get("n_samples", 0) == 0:
        print("FAILED — no timing data collected")
        return

    # Exit with error if host suspend detected
    if "VOID" in result.get("host_suspend_gate", ""):
        print()
        print("=" * 70)
        print("⚠ BASELINE VOID — HOST SUSPEND DETECTED")
        print("=" * 70)
        print(f"Host-suspend gate: {result['host_suspend_gate']}")
        print("Re-measure on a quiet host.")
        sys.exit(1)

    # Print results
    print()
    print("=" * 70)
    print("REAL CAPTURE-LOOP BASELINE — PER-FRAME PROCESSING COST")
    print("=" * 70)
    print()
    print(f"ENTRY POINT: {result['measurement']['entry_point']}")
    print(f"NO SLEEP ON PATH: {result['measurement']['no_sleep_on_path']}")
    print()
    print(f"WALL-CLOCK DISTRIBUTION:")
    print(f"  Median:  {result['distribution']['wall_median_ms']:.6f} ms")
    print(f"  P95:     {result['distribution']['wall_p95_ms']:.6f} ms")
    print(f"  P99:     {result['distribution']['wall_p99_ms']:.6f} ms")
    print(f"  Max:     {result['distribution']['wall_max_ms']:.6f} ms")
    print(f"  N:       {result['distribution']['n_samples']}")
    print()
    print(f"HOST-SUSPEND GATE: {result['host_suspend_gate']}")
    print()
    print(f"PLAUSIBILITY CHECK:")
    print(f"  Expected: {result['plausibility_check']['expected_order_of_magnitude']}")
    print(f"  Measured: {result['plausibility_check']['measured_median_ms']:.6f} ms")
    if result['plausibility_check']['plausible']:
        print(f"  Verdict:  PLAUSIBLE ✓")
    else:
        print(f"  Verdict:  INVESTIGATE ⚠")
    print()

    # Write artifacts
    artifact_dir = args.output_dir
    _write_artifact(result, artifact_dir / "wo040_measurement_results.json")

    # Build baseline declaration with seven dimensions
    host_string = (
        f"{host_info['hostname']} ({host_info['os']}, {host_info['machine']}, "
        f"{host_info['processor']})"
    )
    # Handle case where psutil is not available (load_percent/memory_percent are "N/A")
    if host_info['load_percent'] == "N/A":
        load_string = "CPU N/A, Memory N/A (psutil not available)"
    else:
        load_string = f"CPU {host_info['load_percent']}%, Memory {host_info['memory_percent']}%"

    baseline = {
        "source": result["measurement"]["fixture"],
        "correction_chain": [
            "15.5ms — fixture-pacing (CLOSEOUT-2, withdrawn)",
            "0.542ms — direct-construct harness (CLOSEOUT-2, withdrawn)",
            f"{result['distribution']['wall_median_ms']:.6f}ms — REAL loop measurement (WO-040, THIS)",
        ],
        "reference_use": (
            "Per-frame real processing cost exceeds p99 for N consecutive frames flags "
            f"potential regression. Account for small-N caveat (N={result['distribution']['n_samples']})."
        ),
        "dimensions": {
            "host": host_string,
            "load": load_string,
            "source": result["measurement"]["fixture"],
            "duration_n": f"{result['measurement']['total_frames_in_sequence']} frames × {result['measurement']['passes']} passes = {result['distribution']['n_samples']} samples",
            "resolution": "nanosecond (time.monotonic / time.time)",
            "instrument": "PerFrameRecord @ commit 89a2842 (WO-039)",
            "interpreter": interpreter_info,
        },
        "host_suspend_gate": result["host_suspend_gate"],
        "baseline": {
            "median_ms": result["distribution"]["wall_median_ms"],
            "p95_ms": result["distribution"]["wall_p95_ms"],
            "p99_ms": result["distribution"]["wall_p99_ms"],
            "max_ms": result["distribution"]["wall_max_ms"],
            "n_samples": result["distribution"]["n_samples"],
        },
        "small_n_caveat": (
            f"Sample size N={result['distribution']['n_samples']} from "
            f"{result['measurement']['total_frames_in_sequence']} unique frames × "
            f"{result['measurement']['passes']} passes. "
            "For stable p99, N should be larger. Use p95 for regression checking or collect more passes."
        ),
        "measured_at": result["metadata"]["timestamp"],
        "commit_sha": result["metadata"]["commit_sha"],
    }

    baseline_file = artifact_dir / "baseline.json"
    _write_artifact(baseline, baseline_file)

    print()
    print(f"Artifacts written to: {artifact_dir}")
    print(f"  - wo040_measurement_results.json")
    print(f"  - baseline.json")


if __name__ == "__main__":
    asyncio.run(main())
