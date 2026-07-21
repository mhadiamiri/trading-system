"""WO-016 §D28 §C — BASELINE-ESTABLISHMENT PROTOCOL (no verdict authority, no venue).

Establishes THIS host's frozen mean-cycle baseline for the UNIFORM drift gate. It drives RECORDED
frames through the PRODUCTION loop (KrakenV2BookAdapter.process_raw_frame) at a REPRESENTATIVE
message rate while the production lag sampler runs, then reports the observed mean cycle. Load
without a socket, so a new host can be baselined with NO venue authorization.

DECLARED (rule 0.1j / 0.4 — a declaration, not a verdict):
  - MESSAGE RATE = ~1,959 msg/min (32.65/s), ANCHORED to WO-008b-B-RERUN's received rate. The
    baseline must be measured under load comparable to the run that will reference it — a constant
    is only as portable as the LOAD it was measured under, not only the host. An IDLE-loop baseline
    would be too low and would convict every real run at startup.
  - WARMUP DURATION = 120 s (default). Derivation: at the 100 ms lag interval that is ~1,200 lag
    samples — far above the ~100 needed for a stable mean — while keeping establishment to ~2 min.
  - "REPRESENTATIVE" = the ACHIEVED send rate is within 10% of the ~1,959/min target; verified and
    reported below. If the replay path cannot sustain the rate, that is REPORTED as a finding.
  - COMPATIBILITY: the standing 0.108886 s was derived under LIVE load at ~1,959 msg/min, so it is
    compatible with this protocol (same load), not superseded by it. This tool re-measures under the
    same load for a NEW host; on the standing host it CONFIRMS, and does not overwrite, unless --write.

Usage:
  python tools/establish_mean_cycle_baseline.py [--seconds N] [--write]
    (default: 120s, report only. --write saves this host's record to the store.)
"""
import asyncio
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, os.path.join(REPO, "src")]

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, LagSampleRecord  # noqa: E402
from trading.loop import host_baseline                                                  # noqa: E402
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL      # noqa: E402

TARGET_PER_MIN = 1959.0
TARGET_PER_S = TARGET_PER_MIN / 60.0


async def establish(seconds: float):
    adapter = KrakenV2BookAdapter()
    await adapter.process_raw_frame(SNAPSHOT_FRAME)          # seed the book once
    record = LagSampleRecord(interval_s=adapter.LAG_SAMPLE_INTERVAL_SECONDS)
    sampler = asyncio.create_task(adapter._sample_event_loop_lag(record))

    interval = 1.0 / TARGET_PER_S
    sent = 0
    start = time.monotonic()
    # Deadline-based pacer with catch-up: schedule each frame at start + i*interval; if behind
    # (asyncio.sleep granularity is ~15ms on Windows), skip the sleep and catch up. This is proper
    # pacing, not a workaround — if the loop genuinely cannot keep up, the achieved rate still falls
    # short and that is reported as a finding.
    while time.monotonic() - start < seconds:
        await adapter.process_raw_frame(UPDATE_MODIFY_LEVEL)  # representative parse+apply+checksum load
        sent += 1
        delay = (start + sent * interval) - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(0)   # yield to the lag sampler without adding wall time
    elapsed = time.monotonic() - start
    sampler.cancel()
    try:
        await sampler
    except asyncio.CancelledError:
        pass

    achieved_per_min = sent / elapsed * 60.0
    within_10pct = abs(achieved_per_min - TARGET_PER_MIN) / TARGET_PER_MIN <= 0.10
    return {
        "seconds": elapsed, "frames_sent": sent,
        "achieved_per_min": achieved_per_min, "target_per_min": TARGET_PER_MIN,
        "representative_within_10pct": within_10pct,
        "mean_cycle_s": record.mean_cycle_s, "lag_samples": record.actual_samples,
    }


def main():
    seconds = 120.0
    if "--seconds" in sys.argv:
        seconds = float(sys.argv[sys.argv.index("--seconds") + 1])
    r = asyncio.run(establish(seconds))
    standing = 0.108886
    print("=== WO-016 §D28 §C — mean-cycle baseline establishment (no verdict authority) ===")
    print(f"host fingerprint: {host_baseline.fingerprint_key()}  {host_baseline.host_fingerprint()}")
    print(f"duration={r['seconds']:.1f}s  frames_sent={r['frames_sent']}  lag_samples={r['lag_samples']}")
    print(f"target rate={r['target_per_min']:.0f}/min  achieved={r['achieved_per_min']:.0f}/min  "
          f"REPRESENTATIVE(<=10%)={r['representative_within_10pct']}")
    print(f"REPLAY CAN SUSTAIN THE RATE: {r['representative_within_10pct']} "
          f"(finding, not worked around, if False)")
    print(f"measured mean_cycle={r['mean_cycle_s']*1000:.3f}ms  vs standing baseline "
          f"{standing*1000:.3f}ms  delta={(r['mean_cycle_s']-standing)*1000:+.3f}ms "
          f"({(r['mean_cycle_s']/standing-1)*100:+.1f}%)")
    print("(the standing 0.108886s was derived under LIVE load at ~1,959/min -> compatible with "
          "this protocol, not superseded)")
    if "--write" in sys.argv:
        rec = host_baseline.save_baseline(
            mean_cycle_seconds=round(r["mean_cycle_s"], 6),
            derivation=f"establishment protocol: {r['frames_sent']} recorded frames replayed at "
                       f"{r['achieved_per_min']:.0f}/min over {r['seconds']:.0f}s, mean_cycle=span/actual",
            date="(set-at-write)", load=f"replay ~{r['achieved_per_min']:.0f} msg/min (representative)")
        print(f"[--write] saved this host's baseline: {rec['mean_cycle_seconds']}s")
    else:
        print("[report only] not written; pass --write to save this host's record (new host).")


if __name__ == "__main__":
    main()
