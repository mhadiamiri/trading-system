# WO-023 §2b — GATE CORRECTNESS + VERDICT CORRECTION — REPORT

**Base:** `8f448cd` on master (local == remote). **Scope: §1 + §2 only.** **Ship impact: YES** (§1
touches the production gate). Context at report time: **~38%** (last measured 27% = 273k/1M at the
`/context` checkpoint just before §2b began; grown with the §2b work — deliberate, no compaction).

Two corrections to the accepted foundation, both landed green, both before the 30-test conversion.

---

## §1 — COUPLING KEYS ON TRANSPORT **IDENTITY**, NOT INJECTION STATUS

### The defect (as shipped in `fbdaf58`)
The coupling check keyed on `self._connect_fn is not None`, implementing *"an UNCONFIGURED transport
with a fake clock refuses."* The ruled invariant is *"a REAL transport with a fake clock refuses."*
The gap admits the hazard: `KrakenV2BookAdapter(connect_fn=websockets.connect, monotonic_clock=fake,
…)` — non-default by CONFIG, REAL by IDENTITY — passed coupling, so a fake clock could drive a real
socket. The gate was also self-inconsistent: it tested the CLOCK by identity (`is not
time.monotonic`) but the transport by sentinel.

### The fix (production, `kraken_v2_book.py`)
- Module scope, captured at import (before any test can patch): `_REAL_CONNECT = websockets.connect`
  (with a module-level `import websockets`).
- Coupling now:
  ```python
  resolved = self._connect_fn or websockets.connect     # late binding unchanged
  if resolved is _REAL_CONNECT:
      raise ValueError("CLOCK_INJECTION_REFUSED: COUPLING — …")
  ```
  Compared against the import-captured `_REAL_CONNECT`, **not** the live module attribute (a
  module-patching test replaces that attribute; comparing against it would read a patched fake as
  real and refuse the currently-green module-patching tests). Late-binding decision unchanged;
  coherence branch unchanged; clock-side identity tests unchanged.

### Both directions verified (`evidence/WO-023-2B/identity_keying_both_directions.txt`)
- **module-patched (FAKE) transport + injected clock** → `resolved` is the patched fake → `is not
  _REAL_CONNECT` → NON-default → **coupling PASSES** (it proceeded, `connect_count=1`, emitted=1) — the
  module-patching tests stay green.
- **explicit `connect_fn=<genuine _REAL_CONNECT>` + injected clock** → `is _REAL_CONNECT` →
  **REFUSES `CLOCK_INJECTION_REFUSED: COUPLING`**, pre-connection (the genuine callable is never
  invoked because the refusal precedes `_connect`).

### The coherence token, declared
The gate docstring now DECLARES `_coherence_token`: what it is (a shared attribute the FakeClock
harness stamps on both readers — the token IS the one FakeClock instance, the single source), that
coherence is PROVED by the shared token rather than inferred from clock values, and that a pair
without a shared token is NOT coherent regardless of how it behaves (two clocks that happen to agree
numerically are still two sources). Accepted as a production-read attribute whose only producer is a
test fixture — declared, not incidental.

### The fourth bite assertion + third mutation (no new test; count stays 216)
`test_clock_injection_gate` gained **assertion 4 — EXPLICIT-REAL-TRANSPORT REFUSAL**:
`connect_fn=<real by identity>` + coherent fake clock → refuses `COUPLING`, `connect_count == 0`.
The REAL-transport assertions (1 and 4) substitute a SPY for `_REAL_CONNECT` via `patch.object` so
the gate does its genuine identity comparison against a safe stand-in — **no genuine socket even
under a mutation** (NO VENUE CONNECTION); `connect_count == 0` proves pre-connection. This is not
"monkeypatching to make a guard pass" (0.2): it makes the guard REFUSE a safe stand-in for the real
transport, the only way to exercise "real transport refuses" without a real socket. (A bound-method
identity pitfall was hit and fixed: `spy.connect` yields a NEW object per access, so the two patches
must share ONE captured bound method for the gate's `is` comparison — reported under "every
attempt".)

**Three-mutation bite proof** (`evidence/WO-023-2B/bite_proof_clock_gate_3mutations.txt`), pristine
sha256 `1a8cf00608e1eff173dd10c12a95d76950c95dbb0734bbec7a2c8316d2159691`:
- **Artifact 1** — PASS on pristine.
- **Mutation A** (whole gate neutered) → assertion 1 (UNCONFIGURED-REAL/COUPLING) FAILS `DID NOT
  RAISE`; restore == pristine.
- **Mutation B** (coherence branch → `False`) → assertion 3b (COHERENCE) FAILS `DID NOT RAISE`;
  restore == pristine.
- **Mutation C** (coupling reverted to the sentinel `self._connect_fn is None`) → **assertion 4
  FAILS** `DID NOT RAISE` **at test line 133**, meaning assertions 1, 2 and 3 executed and PASSED
  first. This is the section's point: the new assertion discriminates the two keyings, and the old
  sentinel keying was permissive to an explicit real transport. Restore == pristine.
- **Artifact 5** — PASS after restore. **Artifact 6** — final sha256 == pristine (IDENTICAL: YES).

---

## §2 — §7 RE-BASELINE VERDICT: **NOT COVERED / VOID**, not "CONFIRMED"

An instrument that does not execute the changed line cannot confirm a prediction about it. The §7
instrument replays `process_raw_frame` + `LiveTradingLoop` and never runs `get_live_market_data`'s
while-loop where the changed per-iteration call sits; the +0.196 ms (ratio 0.10) measures an
UNAFFECTED path. This is the WO-008b-B precedent (honest data over a `pass` stub → VOID, not PASS).

Corrected in **both** places by **appending** the correction and **preserving** the original
mis-labelled "CONFIRMED" text (a mis-labelled verdict is itself evidence — the `progress.md` dated
correction treatment):
- `evidence/WO-023-FOUNDATION/hot_path_rebaseline.txt` — appended correction block.
- `WO-023-FOUNDATION-REPORT.md` §7 — appended correction block; struck the "CONFIRMED" label.

Corrected verdict text (verbatim): **VERDICT: NOT COVERED — VOID.** Prediction (recorded first):
BELOW FLOOR / UNDETECTABLE — neither confirmed nor refuted. **NO INSTRUMENT IN THE PROJECT CURRENTLY
OBSERVES THE CAPTURE LOOP'S PER-ITERATION COST** — instrument-coverage gap, RECORDED, not closed (no
new instrument built). Decision log added:
`docs/decisions/2026-07-23-a-verdict-inherits-its-instrument-s-coverage.md` (second instance;
"right" and "shown" are different claims).

---

## §3 — ACCEPTANCE

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest -p no:randomly -rX` | **216 passed**, 0 f/xf/xp | **216 passed**, 0 f/xf/xp |
| `pytest --randomly-seed=20260724 -rX` | **216 passed**, 0 f/xf/xp | **216 passed**, 0 f/xf/xp |

- `lint-imports` → **6 kept, 0 broken** · `contract_count_check.py` → **6/6** · `ruff check .` →
  **clean** · `annotation_name_scan.py` → **0** · `preflight_path_check.py` → **pass**
- Bite proof re-run: **4 assertions, 3 mutations, sha256 exact-restore** (above).
- **Test count stays 216** (assertion 4 added to the existing test; no new test, no removed test).
- Secret scan: clean (one production module import, one module-level capture, a gate rewording, and
  test/docs edits; no credentials).
- **Commit / push / CI:** __COMMIT_CI__

---

## STOPPED / attempts / changed-but-not-asked
- **Every attempt reported (0.5):** the bound-method identity pitfall in the test (fixed by capturing
  one bound method for both patches). No other retries.
- **STOPPED at:** nothing — no code/order disagreement arose in §1/§2 (the identity mechanism the WO
  specified matched the code). 
- **Changed but not asked?** Only the WO-specified surface: the production gate + `_REAL_CONNECT`
  capture (`kraken_v2_book.py`), the existing bite-proof test (assertion 4 + identity-safe
  construction), the §7 verdict correction in the evidence file and foundation report, one new
  decision log, this report, `progress.md` (§2b block), and §2b evidence. `instructions.md` carries
  the §2b WO text (present at session start). No other file.

**THEN STOP.** The 30-test conversion is NOT begun.
