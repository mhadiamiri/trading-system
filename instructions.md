# WO-023 §2b — GATE CORRECTNESS + VERDICT CORRECTION

BASE: HEAD `8f448cd` on master (local == remote). 216 passed both orders both interpreters,
CI green both legs (run 30026635375). import-linter 6/6, contract 6/6, ruff clean, annotation 0.

WO-023 §2 FOUNDATION is ACCEPTED with two corrections, below. Both are small. Both must land
BEFORE the 30-test conversion, because the gate's keying determines how all 30 tests construct
their adapters — fixing it after the conversion means re-touching 30 tests.

SCOPE: §1 and §2 ONLY. Commit green, STOP. Do not begin the conversion.
SHIP IMPACT: YES (§1 touches the production gate).

---

## §0 RULES OF ENGAGEMENT

0.1 No discretion. Code wins over this order; if they disagree, STOP and report.
0.2 No monkeypatching to make a guard pass.
0.3 Fail-then-pass bite proof, four artifacts, sha256 exact-restore.
0.4 Preservation duals mandatory.
0.5 Report every attempt.
0.6 **AUTO MODE OFF** for every edit in §1. This is the production gate in `kraken_v2_book.py`.
0.7 State your actual context % in the report.

---

## §1 THE COUPLING CHECK MUST TEST THE TRANSPORT BY IDENTITY, NOT BY INJECTION STATUS

### The defect
§4.2 as shipped keys coupling on `self._connect_fn is not None`. That implements:

    AN UNCONFIGURED TRANSPORT WITH A FAKE CLOCK REFUSES.

The ruled invariant (D34, carried verbatim in the reason code's own docstring) is:

    A REAL TRANSPORT WITH A FAKE CLOCK REFUSES.

These differ, and the difference admits the exact hazard the guard exists to refuse:

    KrakenV2BookAdapter(connect_fn=websockets.connect,   # non-default by CONFIG, REAL by IDENTITY
                        wall_clock=fake, monotonic_clock=fake)

Coupling passes. A fake clock now runs against a REAL SOCKET — deadline, gap-ledger wall
timestamps and the suspend detector corrupting simultaneously while a genuine capture runs.

Note the gate is already inconsistent with itself: it tests the CLOCK by identity
(`_monotonic_clock is not time.monotonic`) and the TRANSPORT by sentinel. Make them agree.

### The mechanism — a reference captured at import
Do NOT compare against the live module attribute (`resolved is websockets.connect`); a
module-patching test replaces that attribute, so the comparison would read a fake as real and
refuse 13 currently-green tests. Capture the genuine callable at import instead:

    _REAL_CONNECT = websockets.connect          # module scope, captured at import

Coupling becomes:

    resolved = self._connect_fn or websockets.connect     # late binding preserved, unchanged
    if clock_injected and resolved is _REAL_CONNECT:
        refuse(CLOCK_INJECTION_REFUSED, assertion="COUPLING")

Verify BOTH directions explicitly and state the result in the report:
- module-patched transport + injected clock → `resolved` is the patched fake → `is not
  _REAL_CONNECT` → NON-default → coupling PASSES (the 13 tests stay green);
- explicit `connect_fn=websockets.connect` + injected clock → `is _REAL_CONNECT` → REFUSES.

Do not change the late-binding decision. Do not change the coherence branch. Do not change the
clock-side identity tests.

### The fourth bite assertion — add to the EXISTING test, no new test
`tests/integration/test_clock_injection_gate.py::test_clock_injection_gate` gains a fourth
assertion (count stays 216):

4. **EXPLICIT-REAL-TRANSPORT REFUSAL** — `connect_fn=websockets.connect` passed EXPLICITLY +
   coherent fake clock pair → refuses `CLOCK_INJECTION_REFUSED: COUPLING`, `connect_count == 0`
   (pre-connection). This is the assertion a sentinel-keyed gate passes today by letting it
   through, so it is the one that proves the correction.

Re-run the four-artifact bite proof over the whole test. Add a THIRD mutation:
- MUTATION C — revert the coupling check to the sentinel form (`self._connect_fn is not None`)
  → assertion 4 must FAIL `DID NOT RAISE` while assertions 1, 2 and 3 still pass. Restore,
  sha256 == pristine. This mutation is the point of the section: it demonstrates that the new
  assertion discriminates the two keyings and that the old keying was permissive.

### Declare the coherence token
`_coherence_token` is a production-read attribute whose only producer is a test fixture. That is
accepted (proving one source is the only alternative to inferring it, and D34-3 refused
inference), but it must be DECLARED, not incidental. Add to the gate's docstring: what the token
is, that coherence is PROVED by shared token rather than inferred from clock values, and that a
clock pair without a shared token is not coherent regardless of how it behaves.

---

## §2 §7 RE-BASELINE — THE VERDICT IS **NOT COVERED / VOID**, NOT "CONFIRMED"

`evidence/WO-023-FOUNDATION/hot_path_rebaseline.txt` and §7 of the report record the prediction
(BELOW FLOOR), then state that the instrument replays `process_raw_frame` + `LiveTradingLoop` and
is **STRUCTURALLY BLIND** to `get_live_market_data`'s while-loop where the changed line lives —
and then report the outcome as CONFIRMED.

An instrument that does not cover the changed line cannot confirm a prediction about it. The
+0.196 ms figure is a measurement of a DIFFERENT code path. This is the WO-008b-B throughput
precedent exactly: sixty minutes of honest data measuring a `pass` stub was ruled **VOID, not
PASS**, because a verdict must measure the real path.

CORRECT BOTH the evidence file and the report §7 to read:

    VERDICT: NOT COVERED — VOID.
    Prediction (recorded first): BELOW FLOOR / UNDETECTABLE. Neither confirmed nor refuted.
    The re-baseline instrument replays process_raw_frame + LiveTradingLoop and does not execute
    get_live_market_data's while-loop, where the changed per-iteration call sits. The measured
    delta (+0.196 ms, ratio 0.10) is a measurement of an unaffected path and carries no
    information about this change.
    NO INSTRUMENT IN THE PROJECT CURRENTLY OBSERVES THE CAPTURE LOOP'S PER-ITERATION COST.
    Recorded as an instrument-coverage gap, not as a performance result.

Preserve the original text; append the correction rather than rewriting it (the record of a
mis-labelled verdict is itself evidence — same treatment as the progress.md dated correction).

Add a decision log entry `docs/decisions/2026-07-23-a-verdict-inherits-its-instrument-s-coverage.md`:
a measurement that does not execute the changed path is VOID, not a confirmation, however honest
the number is and however correct the prediction turns out to be. Second instance (throughput
VOID was the first). The prediction may still be right; "right" and "shown" are different claims.

Do NOT build a new instrument. The coverage gap is RECORDED, not closed, in this WO.

---

## §3 ACCEPTANCE

- `pytest tests/ -p no:randomly -rX` → **216 passed**, 0 failed / 0 xfailed / 0 xpassed
- `pytest tests/ --randomly-seed=20260724 -rX` → same
- BOTH interpreters (3.11 strict, 3.14 dev)
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff check .` clean ·
  `annotation_name_scan.py` 0 · `preflight_path_check.py` pass
- Bite proof re-run with all four assertions and all three mutations, sha256 exact-restore
- Commit, push, local == remote, CI green BOTH legs via `gh run view`
- Append a §2b block to `progress.md`; do not rewrite existing content

Report: `WO-023-2B-REPORT.md`. Must contain both-direction verification of the identity keying,
the three-mutation bite proof verbatim, the corrected §7 verdict text, and any point you STOPPED.

**THEN STOP.** The 30-test conversion is NOT begun.