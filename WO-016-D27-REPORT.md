# WO-016 ADDENDUM 2 (D27) — REPORT: 'E'-sentinel + three-component VOID gate

Ruling **D27** accepted the partition disproof and added two items. **§A** and **§B** both done
(the named seam after §A was not needed — budget sufficient). No venue connection. Baseline
`11ec211`. Then STOP for review.

## 1. Sentinel (§A) — REGRESSION SENTINEL, bite-proven
`compute_checksum` now rejects scientific notation (`'E'/'e'`) in the **assembled** checksum input
with reason code **`CHECKSUM_INPUT_SYNTHESIZED_NOTATION`** (declared in `decision.py`, same commit).
The interim render fix guards one site; this one character-class check guards the **invariant** at
all of them, turning any future render regression from a silent CRC mismatch into a **loud named
failure** — and it outlives the wire-string WO (guards the invariant, not the implementation).
**Labelled REGRESSION SENTINEL per 0.1d** (its trigger cannot occur while the fixed-point render
holds). **Bite proof** (`evidence/WO-016/bite_proof_sentinel.txt`): A1 PASS (refuses sci input w/
the code) → A2 disable → **real FAIL (DID NOT RAISE)** → A3 restore → PASS → **A4 sha256 byte-identical**.

## 2. Three components (§B) — declared per 0.1j, implemented, this run's values
`_check_instruments_gappy` lag gate is now `recorded_gaps OR elevated_lag OR mean_cycle_drift`
(pong keeps its discrete missed-SENDS gate). Full detail: `evidence/WO-016/three_component_void_metric.txt`.

| Component (mode) | per-sample bound | window | verdict fraction | derivation | THIS RUN |
|---|---|---|---|---|---|
| (1) DISCRETE | interval ≥ 2×interval = **200 ms** | capture window | Σgap/window > **0.10** | 10% lost to ≥200ms stalls = severe discrete starvation, over the correct quantity | **0.080%** → clean |
| (2) SPIKY | lag > **100 ms** | samples | count-fraction > **0.05** | adopted verbatim from WO-014c-1 "ELEVATED >100ms on >5%" | **0.036%** → clean |
| (3) UNIFORM | — (aggregate) | run | (mean_cycle−base)/base > **0.50** (signed) | below doubling (100%=starvation; 199ms=+83%), above benign variation (≪50%) | **+0%** → clean |

(1) and (2) share the ~200ms per-sample boundary but differ in **aggregation** (time-fraction vs
count-fraction), so they own different shapes (few-long-stalls vs many-spikes) — not the redundancy
D27 flagged. (3) owns the **uniform** escapee. Witnessed in isolation, incl. **the counterfactual**:
a 199ms cycle records 0 gaps and 0 elevated samples yet trips UNIFORM at +83%
(`test_lag_sampler.py::test_void_gate_uniform_drift_catches_the_counterfactual`).

## 3. Baseline protocol — FROZEN
**Standing baseline = 0.108886 s**, this run's OBSERVED mean cycle (span/actual = 3600.00/33,062).
Frozen; re-declared **only** on a pipeline change touching the loop, and that re-declaration is a
**0.4 event**. A self-re-deriving baseline can be dragged by slow-onset starvation ("got slower and
re-baselined around it" = the drift metric's own 0.1d); freezing makes that unwritable. Because the
baseline is observed, per-cycle overhead is IN it and only CHANGE registers — component (3)'s
structural immunity.

## 4. Partition rewritten (discrete / spiky / uniform → owner)
0.080% real missed-wakes → **DISCRETE**; 8.08% per-cycle overhead → **owned by no VOID component**
(it is in the frozen baseline; UNIFORM sees only change); spike clusters → **SPIKY**; uniform
slowdown → **UNIFORM**. The naive metric conflated overhead (bias) and slowdown (signal); the gate
separates them so none is laundered through another.

## 5. Residual — named as a floor limit
DEGRADATION OF THE SAMPLER'S OWN MEASUREMENT (monotonic clock skew; whole-process lockstep slowdown)
reads normal while truth does not. Every in-process detector shares its process's domain; declared
as the instrument's **floor limit**, not closed. Only an out-of-process witness (e.g. host-suspend's
wall-vs-monotonic divergence) sees below it.

## 6. Decision log
`docs/decisions/2026-07-21-gappiness-partition-failed-on-its-own-numbers.md` (verbatim D27 §C).

## 7. Verification (§D)
`evidence/WO-016/verify_d27.txt`: **198 passed** deterministic (246.09s) **and** randomized
(seed 20260725, 247.09s), 0 failed/xfailed/xpassed; lint-imports **6/6**; contract **6/6**; ruff
clean. Delta = **+6 tests** (3 sentinel + 3 gate-component), explained. New reason code
`CHECKSUM_INPUT_SYNTHESIZED_NOTATION` declared in the same commit. Secret scan 0 hits. Committed +
pushed to `master`; **local HEAD == remote HEAD** (SHA in the session hand-off).

## 8. Venue connection? **NO.** HTTPS doc fetch? **NO** (this addendum needed neither).
## 9. Prose standing in for output? **NO** — every figure traces to code + `evidence/WO-016/*` + tests.
## 10. Changed but not asked? **None.** All D27-mandated:
`src/…/kraken_v2_book.py` (§A sentinel + §B gate/properties/constants), `src/…/logkit/decision.py`
(§A reason code), `tests/integration/test_checksum_sentinel.py` (§A), `tests/integration/test_lag_sampler.py`
(§B, +3 tests), `evidence/WO-016/{bite_proof_sentinel,three_component_void_metric,verify_d27}.txt`,
`docs/decisions/2026-07-21-gappiness-partition-failed-on-its-own-numbers.md` (§C), this report.
`instructions.md` carries the lead's WO/D27 text (their edit, uncommitted).
## 11. What could not be completed? Nothing in D27. Still open by prior ruling (separate WOs):
the structural wire-string FR-018a(f) fix, and the venue-side vs corpus-blocking corpus decision.

---
**STOP for review.** Do NOT proceed to WO-013 or the corpus.
