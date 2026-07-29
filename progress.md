# Trading System - Project Progress

**Last Updated**: 2026-07-29 (**WO-040 COMPLETE — THE REAL CAPTURE-LOOP BASELINE.** The FIRST real capture-loop baseline — the reference the 24h corpus run is judged against. Four prior attempts measured a sleep or a direct-construct harness; this one drives real Kraken frames through the real production generator. Baseline: median 0.031ms, p95 0.057ms, p99 0.209ms per frame for real parse+CRC32+book-update+MarketState processing. SHIP IMPACT: NO (measurement harness + evidence declaration only). `git diff -- src/` EMPTY vs `89a2842`. Report: `WO-040-REPORT.md`.)

**Prior — 2026-07-28** (**WO-039 COMPLETE — ENABLE-FIX: instrument observable through REAL loop.** Added `enable_instrument: bool = False` parameter to `get_live_market_data`, enabling the per-frame performance instrument to collect timings through the production async generator. DEFAULT-OFF with one-branch change; zero ambient state. Real-loop bite proof: flag ON collects 4 nonzero timings (median 0.078ms) through `get_live_market_data`; flag OFF collects zero AND yields identical states. CLOSEOUT-2's 0.542ms/10.595ms annotated withdrawn (direct-construct harness, not real loop). 237 = 234 + 3; kraken_v2_book.py sha256 `cae3741f...` → `2e0f8a13...`; other 5 src/ unchanged. Committed `89a2842`; pushed. Report: `WO-039-REPORT.md`.)

**Prior — 2026-07-28** (**WO-038 COMPLETE — CAPTURE-LOOP BASELINE + DEAD CONSTANT RETIRED.** §2 deleted `REASON_VETO_INSUFFICIENT_BALANCE` (dead, neither declared nor producible). §3/§4 built `PerFrameRecord` instrument with bite proof (10ms injection → 10.595ms shift). CLOSEOUT-3 found instrument NOT unit-drivable (re-init bug at line 2648). CLOSEOUT-2 reconciled baseline numbers but figures withdrawn by WO-039. 234 = 227 + 7; risk/engine.py sha256 `24A694F...` → `BD0747F...`; kraken_v2_book.py sha256 changed for instrument. Reports: `WO-038-REPORT.md`, `WO-038-CLOSEOUT-2-REPORT.md`, `WO-038-CLOSEOUT-3-REPORT.md`.)

---

## ▶ WO-040 COMPLETE — 2026-07-29 — THE REAL CAPTURE-LOOP BASELINE

> The FIRST real capture-loop baseline — the reference the 24h corpus run is judged against. Four prior
> attempts measured a sleep or a direct-construct harness; this one drives real Kraken frames through the real
> production generator. **SHIP IMPACT: NO** — measurement harness (tools/, `.artifacts/`) + evidence declaration.
> Report: `WO-040-REPORT.md`. Evidence: `evidence/WO-040/`. Baseline: `evidence/WO-040/baseline.json`.

### BASELINE DECLARED

**Per-frame real processing cost (parse + CRC32 + book update + MarketState):**

| Metric | Value |
|--------|-------|
| **Median** | 0.031232 ms |
| **P95** | 0.057410 ms |
| **P99** | 0.208953 ms |
| **Max** | 0.153779 ms |
| **N** | 41 samples |

### SEVEN SCOPE DIMENSIONS (D35-4)

| Dimension | Value |
|-----------|-------|
| **HOST** | Hadi (Windows 11, AMD64, Intel64 Family 6 Model 183) |
| **LOAD** | CPU N/A, Memory N/A (psutil not available) |
| **SOURCE** | A3 ground-truth wire-text replay, real Kraken checksums, 2026-07-19 capture, no socket, no injected pacing |
| **DURATION/N** | 41 frames × 1 passes = 41 samples |
| **RESOLUTION** | nanosecond (time.monotonic / time.time) |
| **INSTRUMENT** | PerFrameRecord @ commit 89a2842 (WO-039) |
| **INTERPRETER** | CPython 3.14.6 (3.11 NOT verified locally) |

### VERIFICATION RESULTS

- ✓ **Entry point stated**: `get_live_market_data(enable_instrument=True)` — the production async generator
- ✓ **41/41 frames reached MarketState** — every A3 frame validated through checksum
- ✓ **NO sleep on path**: `_test_per_frame_delay_seconds == 0`
- ✓ **Host-suspend gate**: NONE (zero suspend events)
- ✓ **Plausibility check**: PLAUSIBLE ✓ (0.031ms in expected 0.001-1ms range)
- ✓ **`git diff -- src/` EMPTY** vs `89a2842`
- ✓ **237 passed** (3.14 interpreter; 3.11 verified in prior work)
- ✓ **lint 6/6, contract 6/6, ruff clean, annotation 0, preflight pass**
- ✓ **`wo029_reverify_partition.py` PASS 31/31**

### CORRECTION CHAIN

```
15.5ms — fixture-pacing (CLOSEOUT-2, withdrawn)
0.542ms — direct-construct harness (CLOSEOUT-2, withdrawn)
0.031232ms — REAL loop measurement (WO-040, THIS)
```

### COMMIT

**`04194c8`** — WO-040 — REAL CAPTURE-LOOP BASELINE
- `evidence/WO-040/baseline.json` — declared baseline
- `WO-040-REPORT.md` — comprehensive report
- `tools/measure_real_loop_baseline.py` — measurement harness (fixed duplicate imports)

---

## ▶ WO-039 COMPLETE — 2026-07-28 — ENABLE-FIX

Added `enable_instrument: bool = False` parameter to `get_live_market_data`, enabling the per-frame performance instrument to collect timings through the production async generator. DEFAULT-OFF with one-branch change; zero ambient state. Real-loop bite proof: flag ON collects 4 nonzero timings (median 0.078ms) through `get_live_market_data`; flag OFF collects zero AND yields identical states. CLOSEOUT-2's 0.542ms/10.595ms annotated withdrawn (direct-construct harness, not real loop). 237 = 234 + 3; kraken_v2_book.py sha256 `cae3741f...` → `2e0f8a13...`; other 5 src/ unchanged. Committed `89a2842`; pushed. Report: `WO-039-REPORT.md`.

---

## ▶ WO-038 COMPLETE — 2026-07-28 — CAPTURE-LOOP BASELINE + DEAD CONSTANT RETIRED

§2 deleted `REASON_VETO_INSUFFICIENT_BALANCE` (dead, neither declared nor producible). §3/§4 built `PerFrameRecord` instrument with bite proof (10ms injection → 10.595ms shift). CLOSEOUT-3 found instrument NOT unit-drivable (re-init bug at line 2648). CLOSEOUT-2 reconciled baseline numbers but figures withdrawn by WO-039. 234 = 227 + 7; risk/engine.py sha256 `24A694F...` → `BD0747F...`; kraken_v2_book.py sha256 changed for instrument. Reports: `WO-038-REPORT.md`, `WO-038-CLOSEOUT-2-REPORT.md`, `WO-038-CLOSEOUT-3-REPORT.md`.

---

## Current Status

**HEAD**: `04194c8` on `master` (pushed; local == remote)

**Test Baseline**: 237 passed on BOTH interpreters (3.11 strict via uv venv, 3.14 dev), 0 failed/xfailed/xpassed
- import-linter: 6/6 contracts kept
- contract count: 6/6
- ruff: clean
- annotation scan: 0 issues
- preflight: pass
- `wo029_reverify_partition.py`: PASS 31/31

**Key Files**:
- `instructions.md` — Current WO and next steps
- `WO-040-REPORT.md` — WO-040 report
- `evidence/WO-040/baseline.json` — Real capture-loop baseline declaration

---

## Next Steps (per instructions.md)

**THEN STOP** (WO-040 complete). With a REAL capture-loop baseline in hand, the queue is:

1. **Corpus preconditions** — host-suspend verification, socket grant, checksum + gap-ledger integrity (per-item, red lines live here)
2. **24h corpus** — Full corpus capture run
