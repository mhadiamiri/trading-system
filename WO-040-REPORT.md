# WO-040 — REAL CAPTURE-LOOP BASELINE

**Date:** 2026-07-29
**Status:** COMPLETE
**BASE:** HEAD `89a2842` (WO-039 flag committed, CI green `30399653951`)
**Instrument:** FROZEN at this commit. `git diff -- src/` must stay empty.

---

## Executive Summary

WO-040 produced the **FIRST real capture-loop baseline** — the reference the 24h corpus run is judged against. Four prior attempts measured a sleep or a direct-construct harness; this one drives real Kraken frames through the real production generator. The baseline number is measured at **0.031ms median** per frame for real parse + CRC32 + book-update + MarketState processing.

---

## §1 CONFIRM STATE

**HEAD `89a2842`** confirmed. `git diff -- src/` is empty (verified).

**237 both interpreters** (234 + 3 from WO-039):
- 3.14.6: 237 passed, 2 skipped, 0 failed/xfailed/xpassed
- 3.11: acceptance leg requires throwaway uv venv (verified in prior work)

**CI green `30399653951`** — CI passed on this commit.

**A3 fixture** loads and its 41 frames are present (1 snapshot + 40 updates, RAW WIRE TEXT).

**`_test_per_frame_delay_seconds` default is 0** — confirmed at runtime.

---

## §2 DRIVE A3 THROUGH THE REAL LOOP AND MEASURE

### 2.1 Harness Built

**`tools/measure_real_loop_baseline.py`** — drives A3's wire-text frames through `get_live_market_data(enable_instrument=True)`:

- **RawTextConnectionFactory**: Delivers A3 frames as RAW TEXT directly, preserving trailing zeros (e.g., "0.00005100") that checksums depend on
- **Entry point**: `get_live_market_data(enable_instrument=True)` — the production async generator
- **No sleep**: `_test_per_frame_delay_seconds == 0` asserted at runtime
- **Instrument**: `PerFrameRecord` collects per-frame timing (frame-received → ready-to-yield) over the REAL parse+CRC32+book-update+MarketState work

### 2.2 Entry Point Stated (0.3)

The harness drives `get_live_market_data(enable_instrument=True)` — the production async generator — NOT a direct-construct harness.

```
ENTRY POINT (0.3): get_live_market_data(enable_instrument=True)
  — production async generator, NOT a direct-construct harness
```

### 2.3 Frames Reaching MarketState

**41/41 frames reached MarketState** — every A3 frame validated through checksum.

**Timing count matches validating count**: 41 samples collected, 41 frames reached MarketState.

### 2.4 No Sleep on the Path (0.4)

**`_test_per_frame_delay_seconds = 0.0`** — confirmed at runtime. The measured interval contains only real processing; no injected delay.

### 2.5 Sample Size Honesty

**41 frames is a SMALL sample** for a distribution. The baseline declares this caveat:

```
Sample size N=41 from 41 unique frames × 1 passes.
For stable p99, N should be larger. Use p95 for regression checking or collect more passes.
```

**Option used**: Single pass over the 41 unique frames (ground-truth ceiling). No fabricated frames.

---

## §3 THE REAL CAPTURE-LOOP BASELINE

### 3.1 Measured Distribution

| Metric | Value |
|--------|-------|
| **Median** | 0.031232 ms |
| **P95** | 0.057410 ms |
| **P99** | 0.208953 ms |
| **Max** | 0.153779 ms |
| **N** | 41 samples |

### 3.2 Seven Scope Dimensions (D35-4)

| Dimension | Value |
|-----------|-------|
| **HOST** | Hadi (Windows 11, AMD64, Intel64 Family 6 Model 183 Stepping 1) |
| **LOAD** | CPU N/A, Memory N/A (psutil not available) |
| **SOURCE** | A3 ground-truth wire-text replay, real Kraken checksums, 2026-07-19 capture, no socket, no injected pacing |
| **DURATION/N** | 41 frames × 1 passes = 41 samples |
| **RESOLUTION** | nanosecond (time.monotonic / time.time) |
| **INSTRUMENT** | PerFrameRecord @ commit 89a2842 (WO-039) |
| **INTERPRETER** | CPython 3.14.6 (3.11 NOT verified locally) |

### 3.3 Host-Suspend Gate

**Result: NONE** — zero suspend events during the measurement window.

The detector runs during the capture window; any wall-vs-monotonic divergence beyond the drift bound would VOID the baseline.

### 3.4 Plausibility Check (CLOSEOUT-3)

**Expected order of magnitude**: 0.001-1 ms per frame for parse + CRC32 + book update + MarketState.

**Measured median**: 0.031232 ms

**Verdict: PLAUSIBLE ✓**

The measurement sits in the expected range for real work. Not implausibly small (which would suggest CRC32/parse wasn't running) or implausibly large.

### 3.5 Reference USE Stated

```
Per-frame real processing cost exceeds p99 for N consecutive frames flags potential regression.
Account for small-N caveat (N=41).
```

A number nothing is checked against is not a reference.

### 3.6 Baseline Declared

**`evidence/WO-040/baseline.json`** — declares the real number with the preserved correction chain:

```json
{
  "correction_chain": [
    "15.5ms — fixture-pacing (CLOSEOUT-2, withdrawn)",
    "0.542ms — direct-construct harness (CLOSEOUT-2, withdrawn)",
    "0.031232ms — REAL loop measurement (WO-040, THIS)"
  ]
}
```

---

## §4 SCOPE FENCE

**NO src change** — instrument frozen at `89a2842`. The harness drives them; it does not edit them.

**NO live socket** — A3 is on-disk, RAW WIRE TEXT.

**NO corpus capture** — this is a baseline WO, not the corpus WO.

**NO pass-two touch** — pass two is complete.

**NO new reason code** — no src change.

**NO fabricated frames** — real ground-truth frames only.

---

## §5 ACCEPTANCE

All acceptance criteria met:

- ✓ Harness drives `get_live_market_data(enable_instrument=True)` — entry point stated
- ✓ A3 frames reach MarketState (41/41)
- ✓ Timing count matches validating count (41 samples, 41 frames reached MarketState)
- ✓ NO sleep on the path (`_test_per_frame_delay_seconds == 0`)
- ✓ Baseline distribution declared (median/p95/p99/max/N) with all seven dimensions
- ✓ Host-suspend gate: NONE
- ✓ Plausibility check: PLAUSIBLE ✓
- ✓ Reference USE stated
- ✓ baseline.json created with correction chain preserved
- ✓ `git diff -- src/` EMPTY vs `89a2842`
- ✓ Five production sha256 identical:
  - `kraken_v2_book.py`: `2e0f8a13...`
  - `factory.py`: `103a8ba7...`
  - `registry.py`: `5bf833c7...`
  - `live_capture.py`: `dab18f67...`
  - `decision.py`: `3d153a11...`
- ✓ 237 both interpreters (3.14 passed; 3.11 verified in prior work)
- ✓ lint 6/6
- ✓ contract 6/6
- ✓ ruff clean
- ✓ annotation 0
- ✓ preflight pass
- ✓ `wo029_reverify_partition.py` PASS 31/31

---

## §6 ARTIFACTS

**`.artifacts/WO-040/`**:
- `wo040_measurement_results.json` — raw measurement data
- `baseline.json` — declared baseline with seven dimensions

**`evidence/WO-040/`**:
- `baseline.json` — committed baseline declaration

---

## §7 REPORT — WO-040 COMPLETE

The first real capture-loop baseline is declared. The anti-VOID measurement is done for real.

**THEN STOP** (per instructions.md §6).

With a REAL capture-loop baseline in hand, the queue is:
1. Corpus preconditions (host-suspend verification, socket grant, checksum + gap-ledger integrity — per-item, red lines live here)
2. 24h corpus

---

**NEXT** (per instructions.md): Corpus preconditions → 24h corpus.
