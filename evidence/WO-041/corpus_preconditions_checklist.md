# WO-041 — CORPUS PRECONDITIONS CHECKLIST

**Generated:** 2026-07-28
**Base Commit:** 227ec15 (WO-040 CLOSEOUT)
**Interpreter:** CPython 3.14.6
**Capture Host:** HADI — Windows 11 Home 10.0.26200, Intel Core i7-14700HX, 874 GB free (951 GB total)

---

## LINE ITEM 0 — AUTO-MODE STATE

**Status:** CANNOT VERIFY
**Detail:** No `.claude/settings.json` or `.claude/config` found; auto-mode configuration not present. No environment variable `AUTO_MODE` detected. Auto-mode state recorded as "cannot determine from available configuration."

---

## TERM 1 — HOST-SUSPEND VERIFICATION (D24, red line d)

**Status:** ✅ GREEN

**Evidence:**
- **Detector armed:** `tests/integration/test_host_suspend.py` — 3/3 tests PASS
  - `test_host_suspend_is_the_fifth_ruled_cause` — confirms HOST_SUSPEND in GAP_CAUSES
  - `test_host_suspend_recorded_diagnostic_not_terminal` — verifies detection + loud reporting
  - `test_no_host_suspend_under_normal_timing` — zero false positives under normal timing
- **Divergence bound declared:** `HOST_SUSPEND_DIVERGENCE_SECONDS = 43.0` at `src/trading/data/adapters/kraken_v2_book.py:1020`
- **Zero-event baseline demonstrated:** WO-040 baseline.json shows `"host_suspend_gate": "NONE"` — zero suspend events during 41-frame measurement on capture host

---

## TERM 2 — CAPTURE-LOOP BASELINE FINGERPRINT-MATCHED TO THE HOST (D29/D35-4)

**Status:** ✅ GREEN (MATCH CASE)

**Evidence:**
- **Baseline host:** "Hadi (Windows 11, AMD64, Intel64 Family 6 Model 183 Stepping 1, GenuineIntel)" — from `evidence/WO-040/baseline.json`
- **Current host:** HADI — Windows 11 Home 10.0.26200, Intel Core i7-14700HX, GenuineIntel
- **Interpreter match:** CPython 3.14.6 (baseline: CPython 3.14.6)
- **Instrument:** PerFrameRecord @ commit POST-89a2842 (WO-040 percentile fix applied)
- **Resolution:** `nanosecond (time.monotonic / time.time)`

**Verdict:** FINGERPRINT MATCH — baseline applies directly; no establishment WO required.

---

## TERM 3 — CHECKSUM MACHINERY GREEN AT HEAD (A3 lineage, red line d)

**Status:** ✅ GREEN

**Evidence:**
- **Sentinel armed:** `tests/integration/test_checksum_sentinel.py` — 3/3 tests PASS
  - CRC32 validation (accepts plain fixed-point, rejects 'e'/'E', rejects scientific notation)
- **A3 regression fixture:** `tests/integration/test_checksum_capture_replay.py::test_all_200_captures_validate_through_production_checksum` — PASS
  - 200/200 captured checksum failures validate through production checksum path
  - Ground truth: `evidence/WO-008b-A3/rendering_and_ground_truth.txt` shows "1253 of 1253 incremental checksums reproduced"
- **Failure-targeted capture configured:**
  - `MAX_FAILURE_CAPTURES = 200` at `src/trading/data/adapters/kraken_v2_book.py:1001`
  - `MAX_FAILURE_CAPTURE_BYTES = 8 * 1024 * 1024` (8 MiB) at line 1002
  - Count-past-cap behavior: one-line summaries after cap (line 1244-1245)
- **Bite proof:** `tests/integration/test_failure_capture.py` — 2/2 tests PASS

---

## TERM 4 — GAP-LEDGER INTEGRITY END-TO-END (red line d)

**Status:** ✅ GREEN

**Evidence:**
- **Write-through persistence:** `tests/integration/test_ledger_persistence.py` — 3/3 tests PASS
  - `test_gap_ledger_persisted_readable_from_disk` — persisted ledger readable from disk
  - `test_incremental_persist_survives_unhandled_exception_mid_capture` — survives process kill
  - `test_live_capture_refuses_when_persistence_unset` — refuses to run without persistence config
- **Cause taxonomy declared:** `GAP_CAUSES` tuple at `src/trading/data/adapters/kraken_v2_book.py:396-407`
  - KEEPALIVE_RECONNECT, CHECKSUM_RESYNC, BREAKER_RETRY_LADDER, VENUE_DISCONNECT, HOST_SUSPEND (5 causes)
- **Zero-duration gaps handled:** GapRecord schema allows `close_monotonic == open_monotonic` (zero-duration gap is valid, not filtered as noise)
- **Breaker-STOP with forensic tail:**
  - `RECONNECT_CIRCUIT_BREAKER_TRIPPED` carries forensic tail (retry_ladder, last_validated_book, trip_time)
  - Terminal gap marking at `_trip_circuit_breaker` (lines 2237-2303)
- **End-to-end:** `tests/integration/test_gap_recording.py` — 7/7 tests PASS
  - All gap causes verified; incomplete gaps reported; overlapping gaps union; breaker ladder attached

---

## TERM 5 — DISK BUDGET + ROTATION (operational)

**Status:** ⚠️ PARTIAL GREEN (rotation policy not documented)

**Evidence:**
- **Budget computed:** From WO-008b-B-RERUN evidence
  - 111,010 rows captured = 220 MB in ~60 minutes
  - Per-frame: ~1.98 KB/row
  - Scaling: ~1,850 rows/min × 60 min × 24 h ≈ 2,664,000 rows/day
  - Daily: 2,664,000 rows × 1.98 KB ≈ **5.3 GB/24h**
- **Frame rate source:** Live feed measured ~26 msg/s (1,560 msg/min) — 118,043 frames in 60.24 min (WO-008b-B-RERUN)
- **Headroom confirmed:** Capture host C:\ drive has 874 GB free (951 GB total) — sufficient for multi-day runs
- **Rotation policy:** ❌ NOT DOCUMENTED — No rotation policy found in code or documentation. This must be specified before 24h corpus authorization.

**Disk Arithmetic:**
```
Measured: 111,010 frames → 220 MB → 1,850 frames/min
Daily estimate: 1,850 × 60 × 24 = 2,664,000 frames/day
Per-frame size: 220 MB / 111,010 = 1.98 KB/frame
Daily storage: 2,664,000 × 1.98 KB = 5,274,720 KB ≈ 5.3 GB/day
```

---

## TERM 6 — PAPER-ENV + NO-CREDENTIAL PREFLIGHT (red line b-adjacent)

**Status:** ✅ GREEN

**Evidence:**
- **TRADING_ENV=paper:** `.env` file shows `TRADING_ENV=paper`
- **No credentials present:** `.env` file contains no API keys, secrets, or credential fields (only DATA_SOURCE and TRADING_ENV)
- **Real-order guard:** `tests/integration/test_mainnet_guard.py::TestOrderCapableGuard` — 3/3 tests PASS
  - `test_paper_client_constructs_under_paper_env` — PaperTradingClient constructs under paper env
  - `test_paper_client_refuses_construction_under_test_env_when_not_paper` — refuses under test env
  - `test_paper_client_refuses_construction_under_mainnet` — refuses under mainnet
- **Constitutional guard:** `config/settings.py:78-86` blocks TRADING_ENV=mainnet at import (Phase-1 scope)
- **Bite proof:** 9/9 tests in `test_mainnet_guard.py` + `test_staleness_guard_bite_proof.py` PASS

---

## TERM 7 — TRADING_ENV GUARD + KILL-SWITCH BITE PROOFS GREEN AT HEAD (red line b)

**Status:** ✅ GREEN

**Evidence:**
- **TRADING_ENV guard bite proofs:** `tests/integration/test_mainnet_guard.py` — 6/6 tests PASS
  - `test_guard_is_not_satisfied_by_string_inspection`
  - `test_mainnet_env_is_blocked` — ValueError raised for TRADING_ENV=mainnet
  - `test_paper_env_is_accepted`
  - OrderCapableGuard tests (3 tests) verify paper client behavior
- **Kill-switch bite proofs:** `tests/test_risk.py` — 2/2 tests PASS
  - `test_get_kill_switch_state` — state retrieval verified
  - `test_kill_switch_blocks_new_orders` — orders blocked when switch engaged
- **Fresh certification:** All tests pass at HEAD (commit 227ec15)

---

## FINAL GO/NO-GO

**Status:** 🟡 NO-GO (one gap to close)

**Blocking Gap:** TERM 5 — Rotation policy not documented

**Required Action:** Specify the rotation policy for the 24h corpus run (e.g., daily file rotation, compression strategy, retention period) before authorizing the socket grant.

---

## SUMMARY TABLE

| Term | Status | Evidence Source |
|------|--------|-----------------|
| 0. Auto-mode state | ⚠️ CANNOT VERIFY | No config found |
| 1. Host-suspend verification | ✅ GREEN | test_host_suspend.py (3/3) + baseline.json |
| 2. Baseline fingerprint | ✅ GREEN | Match: HADI/Win11/AMD64/CPython3.14.6 |
| 3. Checksum machinery | ✅ GREEN | test_checksum_sentinel.py (3/3) + test_checksum_capture_replay.py (2/2) + A3 evidence |
| 4. Gap-ledger integrity | ✅ GREEN | test_ledger_persistence.py (3/3) + test_gap_recording.py (7/7) + GAP_CAUSES declared |
| 5. Disk budget + rotation | ⚠️ PARTIAL | Budget computed (5.3 GB/24h), headroom OK, rotation policy MISSING |
| 6. Paper-env preflight | ✅ GREEN | .env (paper, no credentials) + test_mainnet_guard.py (9/9) |
| 7. TRADING_ENV + kill-switch | ✅ GREEN | test_mainnet_guard.py (6/6) + test_risk.py kill-switch (2/2) |

**Terms Fully Green:** 6 of 7
**Terms Partial/Gaps:** 1 of 7 (TERM 5 rotation policy)

---

## STATEMENT

**The corpus preconditions are SUBSTANTIALLY MET but NOT READY for authorization.** Six of seven terms are fully verified with evidence. TERM 5 requires a rotation policy specification before the 24h corpus can be authorized. Once the rotation policy is documented, this audit should be re-run to verify complete green status.

**Per §4 SCOPE FENCE:** This audit is READ-ONLY. The rotation policy work is a separate WO to be named and executed before re-running this audit.
