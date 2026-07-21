"""WO-016 §D28 §C — BASELINE-ESTABLISHMENT PROTOCOL (no verdict authority, no venue).

Establishes THIS host's frozen mean-cycle baseline for the UNIFORM drift gate. It drives RECORDED
frames through the PRODUCTION loop (KrakenV2BookAdapter.process_raw_frame) at a REPRESENTATIVE
message rate while the production lag sampler runs, then reports the observed mean cycle. Load
without a socket, so a new host can be baselined with NO venue authorization.

DECLARED (rule 0.1j / 0.4 — a declaration, not a verdict; every scope dimension enumerated: host,
load, source, duration — D29):
  - MESSAGE RATE = ~1,959 msg/min (32.65/s), SCOPED: "representative of OBSERVED 60-MINUTE LOAD
    (WO-008b-B-RERUN)". NOT a universal constant. A constant is only as portable as the LOAD it was
    measured under, not only the host; an IDLE-loop baseline would be too low and convict every real
    run at startup. RE-DECLARATION TRIGGERS (D29): (i) the corpus host faces a materially different
    SUSTAINED rate; (ii) a future capture window observes a materially different rate. On either, the
    representative rate is RE-DECLARED, DATED, and the old scope ANNOTATED — never silently replaced.
    "MATERIALLY DIFFERENT" (numeric): a sustained rate outside ±20% of 1,959/min (i.e. <1,567 or
    >2,351/min). Derivation: measured mean_cycle varied <0.2% across a ~28% rate span (1,531/min ->
    108.798ms, 1,959/min -> 108.894ms), so within ±20% the baseline stays valid; beyond it, re-declare.
  - REPLAY SOURCE (PINNED by identity, immutable, NOT recency/convention-picked — D29): the WO-009 §2
    ground-truth fixture `tests/fixtures/kraken_v2_raw_frames.py` (SNAPSHOT_FRAME + UPDATE_MODIFY_LEVEL,
    a self-consistent valid snapshot+update that exercises the full parse+apply+checksum path). It
    calibrates against the LOAD of run WO-008b-B-RERUN-20260721T170944Z (its rate). The run's own
    retained frames cannot be replayed standalone (they need the full multi-thousand-frame prior book
    they accreted against — replaying them cold only manufactures checksum failures), so a PINNED
    valid fixture at the pinned RATE is the comparability anchor. Both the source fixture and the load
    run-ID are named here and written into the baseline record, so two hosts baselined a month apart
    use identical input.
  - WARMUP DURATION = 60 s (default). Derivation: ~600 lag samples at the 100 ms interval — far above
    the ~100 for a stable mean — AND it is the duration actually VALIDATED (this host: 108.894ms,
    +0.0% vs the standing figure). Declared figure == validated figure (D29 §C).
  - "REPRESENTATIVE" = ACHIEVED send rate within 10% of the ~1,959/min target; verified and reported.
    If the replay path cannot sustain the rate, that is REPORTED as a finding.
  - COMPATIBILITY: the standing 0.108886 s was derived under LIVE load at ~1,959 msg/min, so it is
    compatible with this protocol (same load), not superseded. This tool re-measures under the same
    load for a NEW host; on the standing host it CONFIRMS, and does not overwrite, unless --write.

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
RATE_SCOPE = "representative of OBSERVED 60-MINUTE LOAD (WO-008b-B-RERUN)"
RATE_MATERIAL_DIFF = "sustained rate outside +-20% of 1959/min (<1567 or >2351/min)"
REPLAY_SOURCE = ("tests/fixtures/kraken_v2_raw_frames.py (WO-009 ground truth: SNAPSHOT_FRAME + "
                 "UPDATE_MODIFY_LEVEL) — PINNED, immutable, not recency-picked")
LOAD_RUN_ID = "WO-008b-B-RERUN-20260721T170944Z"
DEFAULT_WARMUP_SECONDS = 60.0   # validated duration (D29 §C: declared == validated)


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
    seconds = DEFAULT_WARMUP_SECONDS
    if "--seconds" in sys.argv:
        seconds = float(sys.argv[sys.argv.index("--seconds") + 1])
    r = asyncio.run(establish(seconds))
    print(f"REPLAY SOURCE (pinned): {REPLAY_SOURCE}")
    print(f"LOAD scope: {RATE_SCOPE}; run-id {LOAD_RUN_ID}; material-diff trigger: {RATE_MATERIAL_DIFF}")
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
            derivation=f"establishment protocol: {r['frames_sent']} frames replayed at "
                       f"{r['achieved_per_min']:.0f}/min over {r['seconds']:.0f}s from {REPLAY_SOURCE}; "
                       f"mean_cycle=span/actual",
            date="(set-at-write)",
            load=f"replay ~{r['achieved_per_min']:.0f} msg/min ({RATE_SCOPE}); source run-id "
                 f"{LOAD_RUN_ID}; duration {r['seconds']:.0f}s; material-diff trigger: {RATE_MATERIAL_DIFF}")
        print(f"[--write] saved this host's baseline: {rec['mean_cycle_seconds']}s")
    else:
        print("[report only] not written; pass --write to save this host's record (new host).")


if __name__ == "__main__":
    main()
