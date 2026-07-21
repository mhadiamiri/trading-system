# WO-016 ADDENDUM 3 (D28) — REPORT: host-scoped mean-cycle baseline

Ruling **D28** — the frozen UNIFORM-drift baseline is a HOST property, not a pipeline property.
Implemented: host fingerprint on the baseline record (A), preflight refusal on mismatch (B),
load-representative establishment protocol (C), original teeth unchanged (D), decision log (E).
No venue connection. Baseline `7bf3025`. Then STOP for review.

## 1. Fingerprint fields + hashing choice (A)
`src/trading/loop/host_baseline.py`. The baseline record carries the properties that make the
number what it is: **machine_id, python_version, os, cpu_arch**, plus the measured value, date,
derivation, and load. **`machine_id` is a TRUNCATED sha256 of the hostname** (16 hex), never the
raw name — these files are committed and a personal machine name is avoidable (0.5-adjacent
hygiene, not a secret). The lookup key is a truncated hash of the four-field fingerprint. This
host: `machine_id a28a45c1cac79570`, Python 3.14.6, Windows 11, AMD64 → key `ba47c96a36f36642`.
Store: `config/mean_cycle_baselines.json` (this host → 0.108886s, derivation + load stated).

## 2. Preflight refusal + bite proof (B)
`LiveCaptureRunner._preflight` loads this host's baseline (`host_baseline.load_baseline()`) BEFORE
the drift component arms; on **no match the run REFUSES to start** — before any connection — with
reason code **`MEAN_CYCLE_BASELINE_HOST_MISMATCH`** (declared same commit). It does not limp and does
not guess (and it does not reactively re-baseline — that is the drift metric's own 0.1d). No public
signature change (0.1a): the store path is an env seam (`MEAN_CYCLE_BASELINE_STORE`), and the runner
sets the adapter's baseline via the same direct-private-attr pattern it already uses for
`_gap_persist_path`.
**Bite proof** (`evidence/WO-016/bite_proof_host_baseline.txt`, terminates in the observable effect
0.1i — asserts the REFUSAL): A1 PASS (no-baseline host refuses) → A2 weaken (guard bypassed) →
**real FAIL (DID NOT RAISE)** → A3 restore → PASS → **A4 sha256 byte-identical**.

## 3. Establishment protocol — 0.1j components (C)
`tools/establish_mean_cycle_baseline.py` (NO verdict authority; its own evidence file
`evidence/WO-016/baseline_establishment.txt`). Drives RECORDED frames through the PRODUCTION loop
(`process_raw_frame`) with the production lag sampler running — load without a socket, so a new host
needs no venue authorization.
- **MESSAGE RATE = ~1,959 msg/min (32.65/s)**, anchored to WO-008b-B-RERUN's received rate.
- **WARMUP DURATION = 120 s** (default). Derivation: at the 100 ms lag interval that is ~1,200 lag
  samples — far above the ~100 for a stable mean — while keeping establishment ~2 min.
- **"REPRESENTATIVE"** = achieved send rate within 10% of target; verified and reported. It is
  measured under REPRESENTATIVE LOAD because a constant is only as portable as the LOAD it was
  measured under — an idle-loop baseline would be too low and convict every real run at startup.

## 4. Can the replay sustain the representative rate?
**YES.** A deadline-based pacer (proper pacing, not a workaround) sustains it: 60 s run → **1959/min
achieved vs 1959 target (within 10%: True)**. (A first naive sleep-paced attempt hit only 1531/min —
a Windows asyncio sleep-granularity limit of the PACER, not the processing path; reported, then
fixed with a standard deadline scheduler.) The processing path was never the bottleneck.

## 5. Is 108.886 ms compatible or superseded?
**COMPATIBLE, not superseded.** The standing 0.108886 s was derived under LIVE load at ~1,959
msg/min. The establishment protocol, re-measuring THIS host under the same replayed load, produced
**mean_cycle = 108.894 ms — +0.008 ms (+0.0%)** from the standing figure (60 s run; a 30 s run gave
108.798 ms, −0.1%). Same load, same number to microseconds → the standing baseline stands; the
protocol confirms it rather than overwriting it (report-only unless `--write`).

## 6. Decision log (E)
`docs/decisions/2026-07-21-declared-constant-portable-as-what-measured-on.md` (verbatim). Third
instance of the shape (keepalive-scoped ~116/24h; cadence-scoped 18 s staleness; host+load-scoped
baseline). Corollary recorded: scope includes LOAD as well as host.

## 7. Verification (F)
`evidence/WO-016/verify_d28.txt`: **202 passed** deterministic (246.19s) **and** randomized
(seed 20260725, 246.83s), 0 failed/xfailed/xpassed; lint-imports **6/6**; contract **6/6**; ruff
clean. Delta = **+4 tests** (host-baseline gate), explained. New reason code
`MEAN_CYCLE_BASELINE_HOST_MISMATCH` declared same commit. Secret scan 0 hits. Committed + pushed to
`master`; **local HEAD == remote HEAD** (SHA in the session hand-off).

## 8. Venue connection? **NO.** HTTPS doc fetch? **NO** (D28 needed neither).
## 9. Prose standing in for output? **NO** — fingerprint, refusal, establishment, and compatibility
all trace to code + `evidence/WO-016/{bite_proof_host_baseline,baseline_establishment,verify_d28}.txt`
+ tests + the committed store.
## 10. Changed but not asked? **None.** All D28-mandated:
`src/trading/loop/host_baseline.py` (new), `config/mean_cycle_baselines.json` (new store),
`src/trading/loop/live_capture.py` (preflight refusal), `src/trading/data/adapters/kraken_v2_book.py`
(host-scoped baseline attr), `src/trading/logkit/decision.py` (reason code),
`tools/establish_mean_cycle_baseline.py` (new), `tests/integration/test_mean_cycle_baseline_gate.py`
(new), the D28 evidence + decision log + this report. `instructions.md` carries the lead's WO/D28
text (their edit, uncommitted).
## 11. What could not be completed? Nothing in D28. Still open by prior ruling (separate WOs):
the structural wire-string FR-018a(f) closure, then WO-013 → CI → 008c → corpus (the corpus WO
now inherits the host-baseline precondition alongside no-sleep host and ~5.3 GB/24h).

---
**STOP for review.** Do NOT proceed to WO-013 or the corpus.
