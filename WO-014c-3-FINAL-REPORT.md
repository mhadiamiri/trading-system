# WO-014c-3 — FINAL REPORT (§0 carry-over probes + fixes; stub-lint; precondition sweep)

**Status:** COMPLETE. STOP for review. Do NOT proceed to the re-run.
**Baseline:** `f065ff6` (WO-014c-2 report). **Authority:** `.specify/memory/constitution.md`.
**Venue connection:** NO — simulated transport only.

Commits (in order):
- `9cf8f9d` — §0 probes answered (2 findings + §0.3 declared limit + docstring).
- `62cef3b` — §0.1 + §0.2 fixes implemented (approved), with bite proofs.
- (this report commit) — §1 stub-lint + §2 sweep + §4 report.

---

## 1. §0.1 LEDGER PERSISTENCE — persisted? survives a trip / exception / kill?

**FINDING (at probe):** the gap ledger was in-memory only, written nowhere — lost on a trip,
an exception, or a kill (a run dying at minute 58 lost every gap). **FIX (approved, `62cef3b`):**
append-only redacted JSONL. Writes are:
- **run_start** first (anchor durable even on an early death);
- **incremental at gap OPEN** — write + `flush` + `os.fsync` the instant a gap opens. This is the
  load-bearing, **kill-durable** write: the record does not depend on a clean finalize;
- **RESOLVED** on close; **TERMINAL** flush in `_trip_circuit_breaker` before the exception leaves
  (the trip is the event the ledger most needs to survive);
- **run_end** finalize summary in the `finally`.
Every line redacted via the mechanical redaction module. Best-effort/non-fatal (a persist error
never ends the run it documents). Opt-in via `_gap_persist_path` (explicit like `mode`).
**Survival:** breaker trip ✓ (terminal flush), unhandled exception ✓ (incremental already on disk),
**process kill ✓** (incremental fsync — proven). Bite proof
(`evidence/WO-014c-3/bite_ledger_persistence.txt`): a crash (unhandled exception at a gap) leaves
the gap OPEN record readable on disk; weakening the incremental write leaves only run_start+run_end
(a real kill would not even reach run_end). 4 artifacts, sha256 exact.

## 2. §0.2 CAPTURE RETENTION — bounded? bound + how it announces itself

**FINDING (at probe):** `_checksum_failure_captures` was unbounded (a failure cluster fills the
disk and ends the run). **FIX (approved, `62cef3b`), per the ruled policy:**
- **KEEP THE FIRST N** (the onset is the most diagnostic part), never a ring buffer;
- **COUNT EVERY failure** uncapped (`get_checksum_failure_count`) — the count is itself a finding;
- cap by **COUNT (200) AND BYTES (8 MiB)**, whichever binds first (declared engineering judgment,
  anchor ~21 frames/capture at the WO-008b-B profile; instance-overridable);
- **announce ONCE** via `FAILURE_CAPTURE_CAPPED` (declared in `decision.py` the same commit) —
  never silent truncation;
- **NO run-termination path** (the breaker owns termination; the cap only guards disk).
Bite proof (`evidence/WO-014c-3/bite_failure_cap.txt`): 6 failures / cap 3 → first three kept
(positions 2,3,4), all six counted, announced, run not terminated; weakening the cap grows captures
to 6 without announcing. 4 artifacts, sha256 exact.

## 3. §0.3 DRIFT — bound over 24h, acceptable? docstring pasted

Declared bound: mapping-vs-calendar error over a 24h run **< ~5 s typical** (oscillator ~10-50 ppm,
slewed out by NTP); **worst case ≤ ~43 s/24h** (bounded by the standard 500 ppm NTP slew ceiling,
pathological continuous slew only). **Acceptable:** relative timing (every gap bound, inter-gap
interval, cross-record correlation) is on `time.monotonic()` and is UNAFFECTED — only the single
absolute calendar anchor drifts, and locating a gap to the right minute tolerates seconds of error.
Pasted into the `GapLedger` docstring (WALL/MONOTONIC DRIFT LIMIT paragraph). Evidence:
`evidence/WO-014c-3/clock_drift_limit.txt`.

## 4. STUB-LINT (§1) — bite proof, EVERY hit, allowlist justifications

`tests/test_stub_lint.py` — an AST guard over every production module under `src/` for `pass` /
bare-`return` / `...` bodied functions (a pytest guard, NOT an import-linter contract, so the
contract count stays 6). **EVERY hit in the current tree (10):**

    execution/interface.py:35,68,85   place_order / cancel_order / get_market_data   pass  @abstractmethod
    risk/interface.py:42,72,77,82,87  check / get_kill_switch_state / set_kill_switch /
                                      get_max_position_size / get_max_daily_loss_pct  pass  @abstractmethod
    strategy/interface.py:35,49       version / decide                               pass  @abstractmethod

**Zero unexamined stubs.** ALLOWLIST: a single justified RULE — an `@abstractmethod` body never
executes (`abc.ABCMeta` refuses to instantiate a subclass that has not overridden it), so a `pass`
there is the interface DECLARATION, not an unimplemented path (the exact case 0.1g names). The
explicit non-abstractmethod allowlist is EMPTY (no such case), and an honesty test forbids stale
entries. The former `_request_snapshot`/`_reconnect` `pass` stubs are gone (implemented), so the
lint is meaningful. Bite proof (`evidence/WO-014c-3/stub_lint.txt`): a `pass`-bodied production
function introduced into `kraken_v2_book.py` → the lint FAILS naming it → removed → PASS → sha256
exact. Detector self-test proves it fires (rule 0.1d).

## 5. SWEEP (§2) — denominator, count, how found, shape A vs B, cluster?

**Denominator: 175 tests** (whole suite, not a noticed subset). Evidence:
`evidence/WO-014c-3/precondition_sweep.txt`. **REPORT ONLY — nothing fixed.**
- **Shape B** (found by MECHANICAL pattern match on `assert_called*`, cross-referenced with §1):
  **1 shaped test** — `test_data_adapters.py` (lines 225, 230) asserts `_reconnect` was called on
  the 5th failure. `_reconnect` is not a stub (§1), and the EFFECT is fully covered by
  `test_reconnect_to_effect.py` (drives the real transport, asserts emission resumes, deliberately
  does not assert the call). A legitimate trigger-unit / effect-integration pair, **not a gap.**
- **Shape A** (found by SEMANTIC reading): **1 shaped test** — `test_snapshot_recovery.py` hand-calls
  `_maybe_resubscribe` and feeds the fresh snapshot, but the PRODUCTION TRIGGER is driven, the
  fixture limit is EXPLICITLY declared, and the effect is covered by `test_reconnect_to_effect.py`.
  **Not a gap.** (`set_market_state(...)` usages and raw-frame feeds were examined and rejected as
  Shape A — the venue's real interface / external venue output.)
- **LIVE false-confidence gaps (the S13 class): ZERO. NOT a cluster.** Nothing returns to the lead;
  nothing was fixed.

## 6. VERIFICATION

| Run | Command | Result | Duration |
|---|---|---|---|
| Deterministic | `pytest tests/ -p no:randomly -rX` | 175 passed, 0 failed/xfailed/xpassed | (host-suspend inflated wall time; ~4min CPU) |
| Randomized | `pytest tests/ --randomly-seed=20260725 -rX` | 175 passed, 0 failed/xfailed/xpassed | 243.60s |

**DELTA vs `f065ff6` (167 → 175, +8 tests, all new):** §0.1 persistence (+2), §0.2 cap (+2), §1
stub-lint (+4); §0/§2/§3 added no tests. No existing test changed count, state, or outcome; no
xfail/xpass introduced or cleared. import-linter **6 kept / 0 broken**; contract check **6/6**
(unchanged — stub-lint is a pytest guard); `ruff check .` clean. HEADs pasted at push (§ below).

## 7. Venue connection? **NO.** HTTPS doc fetch? **NO** (the monotonic/NTP claims cite stable
doc URLs at the point of claim; no fetch was needed).

## 8. Prose standing in for output? **NO** — every claim is backed by executed evidence
(redirected bite-proof files with real assertion text and sha256, pasted suite summaries with
seeds/durations, the pasted stub-lint hit list and sweep denominator).

## 9. Changed but not asked?

- `instructions.md` — the WO-014c-3 text + the lead's UPDATE block, committed with their WO (the
  ratified committed-with-its-WO convention). Disclosed.
- `progress.md` — NOT touched this WO (its header was refreshed in WO-014c-2).
- No other unrequested change. `redaction.py` was imported, not modified.

## 10. What could not be completed, and why?

Nothing in WO-014c-3 was left incomplete. Out of scope and NOT done (by ruling): the corpus reader,
and **the 60-minute live re-run** (this WO's §0 fixes were the re-run-blocking items and are now
resolved). Honest limits stated at each site: persistence, the cap, and the gap/failure mechanisms
are exercised under SIMULATED transport; only the isolated live re-run confirms Kraken's real
behavior. Named seam (after §0) was taken for the findings review, per the WO; the lead approved
the fixes and §1/§2 followed as budget allowed.

**STOP for review.**
