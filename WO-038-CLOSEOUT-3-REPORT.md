# WO-038 CLOSEOUT-3 REPORT — STOP: LOOP NOT UNIT-DRIVABLE

**Date:** 2026-07-28
**WO:** WO-038 Closeout-3 — Measure the real loop
**BASE:** `7034704` (CLOSEOUT-2 reconciliation)

---

## §0 RULES OF ENGAGEMENT — APPLIED

0.1 **No discretion.** Code wins: STOP and report.
0.2 The harness MUST drive the REAL processing path — NO src change allowed.
0.3 **BUILT-VS-OPERATED (D24):** The instrument (`e6892d9`) is OPERATED-ACCEPTED and VERIFIED. This WO was to measure the real loop with that proven instrument.

---

## §1 FINDING — THE INSTRUMENTED LOOP IS NOT UNIT-DRIVABLE

### 1.1 The Instrument Re-Initialization Bug

The committed PerFrameRecord instrument (`e6892d9`, lines 2903 and 2963) **cannot be enabled** from outside `get_live_market_data`. The method creates a fresh instance at line 2648:

```python
# Line 2648 in kraken_v2_book.py
self._per_frame_record = PerFrameRecord()  # enabled=False by default
```

The hooks check `self._per_frame_record.enabled` (lines 2902, 2962), which is always False because:
1. The instance is created fresh inside `get_live_market_data`
2. It is created with `enabled=False` (default)
3. There is no external API to enable it after creation
4. The async generator interface prevents injecting code between line 2648 and the first hook

### 1.2 Verification

Created `tools/measure_real_loop_baseline.py` to drive the real loop with the committed instrument:
- Attempted to enable instrument BEFORE calling `get_live_market_data` → overwritten by line 2648
- Measured frames received: 3 ✓
- Measured timings collected: 0 ✗ (hooks not reached because enabled=False)

**Test output:**
```
Instrument: PerFrameRecord ENABLED (e6892d9)
  enabled: True
Processing frames...
  Collected 1 states...
  Raw frames received: 1
  Timings collected: 0  ← HOOKS NOT REACHED
```

### 1.3 Alternative Approaches Considered

**Attempt 1: Use captured_frames fixture** — FAILED
- The `tests/fixtures/kraken_v2_captured_frames.py` fixture has Python floats with scientific notation (`5.1e-05`)
- The checksum validation (line 1381-1386) rejects scientific notation as a guard against WO-008b-B-RERUN bug
- Result: `CHECKSUM_INPUT_SYNTHESIZED_NOTATION` error

**Attempt 2: Use raw_frames fixture** — PARTIAL
- The `tests/fixtures/kraken_v2_raw_frames.py` fixture has string values that work with wire retention
- Only 4 frames (1 snapshot + 3 updates) vs 41 in captured_frames
- Self-generated checksums don't validate (expected per docstring)
- Instrument still cannot be enabled (same line 2648 issue)

**Attempt 3: Manual timing outside instrument** — NOT INSTRUCTIONS-COMPLIANT
- Could measure wall-clock time around `get_live_market_data` call
- But instructions require driving through the REAL processing path with the committed instrument
- Manual timing would not use the proven instrument

---

## §2 STOP — PER INSTRUCTIONS §2.3

**Instructions §2.3:** "If the processing path cannot be driven without a live socket...If none exists, STOP and report (the loop would not be unit-drivable, itself a finding)."

**FINDING:** The instrumented loop CANNOT be driven in isolation without an src change. The PerFrameRecord is:
1. Committed and frozen at `e6892d9` (no src change allowed per instructions)
2. Re-initialized inside `get_live_market_data` at line 2648
3. Created with `enabled=False` with no external enable mechanism

**NO PATH FORWARD** without violating the "no src change" constraint or the "use committed instrument" requirement.

---

## §3 PRODUCTION FILES

**No src files touched** — STOP condition reached before any production change.

---

## §4 REPORT — EVERY ATTEMPT

### Attempts

1. **§1 locate ground-truth fixtures** — SUCCESS
   - Found `tests/fixtures/kraken_v2_captured_frames.py` (41 frames, real checksums)
   - Found `tests/fixtures/kraken_v2_raw_frames.py` (4 frames, string values)

2. **§2 build measurement harness** — SUCCESS
   - Created `tools/measure_real_loop_baseline.py`
   - Used ScriptedConnectionFactory to drive get_live_market_data with fixture frames

3. **§2.1 captured_frames fixture** — FAILED
   - Checksum validation failed: `CHECKSUM_INPUT_SYNTHESIZED_NOTATION`
   - Fixtures have Python floats with scientific notation
   - Checksum path rejects scientific notation (guard against WO-008b-B-RERUN bug)

4. **§2.1 raw_frames fixture** — INSTRUMENT ISSUE
   - Frames processed (3 states collected)
   - Instrument collected 0 timings
   - Found root cause: line 2648 re-initializes PerFrameRecord as disabled

5. **§2.2 enable mechanism investigation** — NO PATH
   - No external API to enable instrument after line 2648
   - Async generator prevents code injection
   - Would require src change (prohibited)

6. **§2.3 STOP invoked** — FINDING REPORTED
   - The instrumented loop is not unit-drivable without src change
   - This is the finding itself

---

## THEN STOP

**WO-038 CLOSEOUT-3 STOPPED.**

The instrumented loop cannot be driven in isolation. The committed PerFrameRecord is re-initialized inside `get_live_market_data` with no enable mechanism, making real-loop measurement impossible without an src change.

**FINDING TO ESCALATE:** The per-frame performance instrument (`e6892d9`) is structurally unable to collect timing data when driven through `get_live_market_data`. The instrument is proven (bite-proof: 10ms injection → 10.595ms shift) but cannot be enabled for real-loop measurement due to the re-initialization at line 2648.

**RECOMMENDED PATH FORWARD:**
1. Modify line 2648 to respect an externally-enabled PerFrameRecord instead of overwriting it
2. Add an `enable_instrument: bool = False` parameter to `get_live_market_data`
3. Re-run CLOSEOUT-3 after the src change

**CORPUS PRECONDITION STATUS:** The per-frame baseline reference remains at 0.542ms (CLOSEOUT-2 provisional). The real-loop measurement could not be obtained.

**QUEUE BLOCKED:** corpus preconditions → 24h corpus
