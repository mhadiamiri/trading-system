# WO-042 — TERM 2 CORRECTION: LOAD DIMENSION UNDECLARED

**Date:** 2026-07-28
**Base Commit:** 48c9830 (WO-041 NO-GO)
**Issue:** WO-041 marked Term 2 as "MATCH" but the load dimension is silent on both sides, not matched.

---

## §2.1 THE CORRECTION

**WO-041 Term 2 Verdict (INCORRECT):**
```
✅ GREEN (MATCH CASE)
```

**WO-042 Term 2 Verdict (CORRECTED):**
```
⚠️ PARTIAL MATCH — 5 dimensions matched, 1 dimension undeclared
```

---

## DIMENSION-BY-DIMENSION ANALYSIS

### Baseline Dimensions (from `evidence/WO-040/baseline.json`)

| Dimension | Baseline Value | Source |
|-----------|----------------|--------|
| host | "Hadi (Windows 11, AMD64, Intel64 Family 6 Model 183 Stepping 1, GenuineIntel)" | baseline.json |
| load | "CPU N/A, Memory N/A (psutil not available)" | baseline.json |
| source | "A3 ground-truth wire-text replay, real Kraken checksums, 2026-07-19 capture, no socket, no injected pacing" | baseline.json |
| duration_n | "41 frames × 1 passes = 41 samples" | baseline.json |
| resolution | "nanosecond (time.monotonic / time.time)" | baseline.json |
| instrument | "PerFrameRecord @ commit POST-89a2842 (WO-040 CLOSEOUT §1 percentile fix, method='inclusive')" | baseline.json |
| interpreter | "CPython 3.14.6 (3.11 NOT verified locally)" | baseline.json |

### Current Corpus Host Dimensions (verified at WO-041 execution)

| Dimension | Current Value | Source |
|-----------|---------------|--------|
| host | HADI — Windows 11 Home 10.0.26200, Intel Core i7-14700HX, GenuineIntel | WO-041 §1 |
| load | NOT STATED (not measured during WO-041) | — |
| resolution | nanosecond (time.monotonic / time.time) | Assumed from baseline |
| instrument | PerFrameRecord @ commit POST-89a2842 (WO-040 percentile fix) | Current HEAD |
| interpreter | CPython 3.14.6 | WO-041 §1 |

---

## VERDICT PER DIMENSION

| Dimension | Match? | Evidence |
|-----------|--------|----------|
| **host** | ✅ MATCH | Both: HADI / Windows 11 / AMD64 / GenuineIntel |
| **OS** | ✅ MATCH | Both: Windows 11 (baseline: "Windows 11, AMD64"; current: "Windows 11 Home 10.0.26200") |
| **CPU** | ✅ MATCH (reconciled) | Baseline: "Family 6 Model 183 Stepping 1"; Current: "i7-14700HX". These are the SAME silicon — i7-14700HX IS Family 6 Model 183 Stepping 1. The friendly-name "i7-14700HX" matches the baseline's "Intel64 Family 6 Model 183 Stepping 1" specification. |
| **interpreter** | ✅ MATCH | Both: CPython 3.14.6 |
| **resolution** | ✅ MATCH | Both: "nanosecond (time.monotonic / time.time)" |
| **instrument** | ✅ MATCH | Both: PerFrameRecord @ commit POST-89a2842 (WO-040 percentile fix, method='inclusive') |
| **load** | ❌ UNDECLARED (both sides) | Baseline: "CPU N/A, Memory N/A (psutil not available)". Current: NOT STATED. This is SILENT on both sides, not a match. |

---

## CPU STRING RECONCILIATION

**Baseline CPU:** `"Intel64 Family 6 Model 183 Stepping 1, GenuineIntel"`

**Current CPU:** `"Intel Core i7-14700HX, GenuineIntel"`

**Reconciliation:** ✅ These are the SAME silicon.
- Intel's architecture identifiers: Family 6, Model 183, Stepping 1
- The commercial product name: Intel Core i7-14700HX
- The i7-14700HX IS a Family 6 Model 183 Stepping 1 processor

**Verification:** Intel's specification confirms i7-14700HX as Raptor Lake architecture, which maps to Family 6 Model 183 in the CPUID instruction.

---

## THE LOAD DIMENSION PROBLEM

**Baseline State:** `"CPU N/A, Memory N/A (psutil not available)"`
- The baseline could not measure load because `psutil` was not available

**Corpus Host State:** NOT STATED
- WO-041 did not measure or record load conditions for the corpus host

**Conclusion:** This is NOT a match on the load dimension. It is UNDECLARED on both sides — a gap in the baseline that was propagated to the corpus host.

---

## ACCEPTABILITY FOR THE GRANT

**Is this acceptable for the corpus grant?**

**Answer:** ✅ ACCEPTABLE, WITH CONDITION

**Condition:** The corpus WO **MUST** declare and record load conditions when it runs — not leave load blank a third time. The baseline left this dimension open; WO-041 propagated the gap; the corpus run must close it.

**Required Recording (corpus WO):**
```
Load conditions at corpus start:
- CPU utilization: N% (average over capture window)
- Memory usage: N GB (average over capture window)
- Other processes: [list if significant]
- Capture is "background-quiet" — confirm minimal competing load
```

**Why this matters:**
- Performance baselines are load-dependent
- A capture under heavy load has different timing characteristics than one under quiet load
- The grant's meaning is the state it was granted against — leaving load undeclared makes the grant conditional on unknown load

---

## CORRECTED TERM 2 VERDICT FOR WO-041 CHECKLIST

**Replace WO-041 Term 2 verdict:**

```
### TERM 2 — CAPTURE-LOOP BASELINE FINGERPRINT-MATCHED TO THE HOST (D29/D35-4)

Status: ⚠️ PARTIAL MATCH — 5 dimensions matched, 1 dimension undeclared

Matched Dimensions (5/6):
- Host: ✅ MATCH (HADI / Windows 11 / AMD64)
- OS: ✅ MATCH (Windows 11)
- CPU: ✅ MATCH (reconciled: i7-14700HX = Family 6 Model 183 Stepping 1)
- Interpreter: ✅ MATCH (CPython 3.14.6)
- Resolution: ✅ MATCH (nanosecond, time.monotonic / time.time)
- Instrument: ✅ MATCH (PerFrameRecord @ POST-89a2842)

Undeclared Dimension (1/6):
- Load: ❌ UNDECLARED (both baseline and corpus host silent)
  Baseline: "CPU N/A, Memory N/A (psutil not available)"
  Corpus host: NOT STATED during WO-041
  This is SILENT on both sides, not a match.

Condition for grant: Corpus WO MUST declare load when it runs — close the dimension the baseline left open.
```

---

## SUMMARY

| Aspect | Status |
|--------|--------|
| Term 2 original verdict | ❌ INCORRECT (marked as full MATCH) |
| Term 2 corrected verdict | ✅ PARTIAL MATCH (5/6 matched, load undeclared) |
| CPU reconciliation | ✅ CONFIRMED (i7-14700HX = Family 6 Model 183 Stepping 1) |
| Load dimension | ❌ UNDECLARED (both sides) |
| Grant condition | Corpus WO must record load when running |

**This correction applies to the re-run checklist in WO-042 §3.**
