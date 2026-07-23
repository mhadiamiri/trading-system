# WO-023 §2c — THE COUPLING BRANCH'S PRESERVATION DUAL — REPORT

**Base:** `fddf1cd` on master (local == remote). **Scope: §1 + §2 only.** **Ship impact:** the §1
investigation found **NO production defect** (the early return covers it), so this WO ships **tests +
docs only** — `kraken_v2_book.py` is byte-unchanged (pristine sha256
`1a8cf00608e1eff173dd10c12a95d76950c95dbb0734bbec7a2c8316d2159691` before and after).

**`/context` reading (0.7):** I cannot invoke the `/context` slash command programmatically (it is a
user-issued CLI command, not a tool). The last ACTUAL reading was **27% (273k/1M)** at the `/context`
checkpoint just before §2b began; several suite runs and edits have occurred since. This is the last
measured value, not an estimate of the current one — a current figure requires the user to run
`/context`. Flagged honestly rather than estimated.

---

## §1 — THE GATE, VERBATIM (kraken_v2_book.py), + reachability answer

```
2361    def _assert_clock_transport_gate(self, incoherent_clocks_allowed: str) -> None:
...       (docstring 2362–2398)
2399        import time
2400
2401        wall_injected = self._wall_clock is not None
2402        mono_injected = self._monotonic_clock is not time.monotonic
2403        if not (wall_injected or mono_injected):
2404            return  # no injected clock — the default path (real runs + every non-suspend test)
2405
2406        # (1) COUPLING — test the TRANSPORT BY IDENTITY (symmetric with the clock-side identity tests
2407        # above), NOT by injection status. Resolve late (unchanged from _connect), then compare
2408        # against the genuine callable captured at import. A REAL transport with a fake clock refuses.
2409        resolved = self._connect_fn or websockets.connect
2410        if resolved is _REAL_CONNECT:
2411            raise ValueError(
2412                "CLOCK_INJECTION_REFUSED: COUPLING — a fake clock is permitted ONLY where the "
2413                "transport is not the REAL one; a REAL transport with a fake clock refuses, "
2414                "pre-connection. Inject a non-real transport through connect_fn, or drop the clock."
2415            )
2416
2417        # (2) COHERENCE — the injected clocks must be the one-source coherent pair (shared token),
2418        # unless the run declares the incoherence by name (never inferred — RULING D34-3).
2419        wall_token = getattr(self._wall_clock, "_coherence_token", None)
2420        mono_token = getattr(self._monotonic_clock, "_coherence_token", None)
2421        coherent = (wall_injected and mono_injected
2422                    and wall_token is not None and wall_token is mono_token)
2423        if not coherent and not incoherent_clocks_allowed:
2424            raise ValueError(
2425                "CLOCK_INJECTION_REFUSED: COHERENCE — injected clocks must be the coherent "
2426                "wall+monotonic pair from ONE source (D25: monotonic orders, wall locates). An "
2427                "incoherent pair is permitted ONLY when declared by name via "
2428                "incoherent_clocks_allowed=<reason>; the gate never infers it (RULING D34-3)."
2429            )
```
Call site in `get_live_market_data` (after the `GAP_PERSIST_UNCONFIGURED` refusal, same
pre-connection discipline):
```
2476        # WO-023 §2 (RULINGS D34-2/D34-3): the PRE-CONNECTION clock/transport gate. Same placement
2477        # discipline as GAP_PERSIST_UNCONFIGURED above — it refuses BEFORE any connection attempt,
2478        # so a fake clock can never drive a real socket even for one frame.
2479        self._assert_clock_transport_gate(incoherent_clocks_allowed)
```

**Is the coupling branch reachable when NO clock is injected? — NO.** The early return at 2403–2404
(`if not (wall_injected or mono_injected): return`) fires first: with both clocks at their defaults,
`not (False or False)` is True → `return` → lines 2409–2415 are never reached. The `clock_injected`
precondition the WO specified **IS present** — implemented as an early return ABOVE the branch rather
than an inline `if clock_injected and resolved is _REAL_CONNECT`; the two are semantically identical
(the coupling refusal fires only when a clock is injected). **No shipped production defect.** A
default-constructed adapter (no clock, `_connect_fn=None`) returns early and proceeds to connect — the
24-hour corpus capture starts. The §2b report's excerpt showed only lines 2409–2411 without the
early-return context above them, which is what raised the concern.

---

## §2 — ASSERTION 5 (DEFAULT-PATH PRESERVATION) + MUTATION D

### Assertion 5 (added to the existing test; count stays 216)
`test_clock_injection_gate` gained **assertion 5 — DEFAULT-PATH PRESERVATION**: no clock injected
(`_wall_clock` default, `_monotonic_clock` default), `connect_fn=None`, transport resolving to a
callable IDENTICAL to `_REAL_CONNECT` → the gate **PROCEEDS**: no refusal, transport invoked
(`connect_count == 1`), reaches the same successful end state assertion 2 checks (`emitted >= 1`).
Constructed with assertion 4's mechanism — BOTH `_REAL_CONNECT` and `websockets.connect` patched to
ONE captured bound method of a self-terminating spy (the §2b bound-method pitfall observed), so the
gate performs its genuine `is` comparison against a safe stand-in — **NO GENUINE SOCKET**. Placed
adjacent to assertion 4 with the pairing named: **4 = real transport WITH a clock refuses; 5 = real
transport WITHOUT a clock proceeds.** Together they prove the coupling branch is conditioned on CLOCK
INJECTION, not on transport identity alone.

### Mutation D — the bite (`evidence/WO-023-2C/bite_proof_clock_gate_4mutations.txt`)
**Target mutated: the early return** `if not (wall_injected or mono_injected): return` → `… pass`.
This is the correct target because the early return IS the clock-injection precondition (there is no
separate inline `clock_injected and …` guard); neutering it makes the coupling branch reachable with
no clock, so a default real run refuses. Result: **assertion 5 FAILS** — the no-clock default run
raises `CLOCK_INJECTION_REFUSED: COUPLING` (kraken_v2_book.py:2411) at test line 161 — while
**assertions 1, 2, 3, 4 still PASS** (they inject clocks, so the early return never fired for them;
execution reached line 161). Full four-mutation protocol, pristine sha256
`1a8cf00608e1eff173dd10c12a95d76950c95dbb0734bbec7a2c8316d2159691`:
- Artifact 1 — PASS on pristine.
- Mutation A (whole gate neutered) → assertion 1 FAILS; restore == pristine.
- Mutation B (coherence → False) → assertion 3b FAILS; restore == pristine.
- Mutation C (coupling → sentinel) → assertion 4 FAILS (1/2/3 pass); restore == pristine.
- Mutation D (early return → pass) → assertion 5 FAILS (1/2/3/4 pass); restore == pristine.
- Artifact 6 — PASS after restore. Artifact 7 — final sha256 == pristine (IDENTICAL: YES).

### Would Mutation D have been caught by ANY of the 216 tests before this WO? — **YES** (0.1 finding)
The WO anticipated "no." **The code says otherwise, and the code wins.** Verified empirically
(`evidence/WO-023-2C/mutation_d_caught_by_existing_tests.txt`): under Mutation D, **6 existing
no-clock live-capture tests FAIL** — `test_ledger_persistence` (×2), `test_keepalive` (×2),
`test_reconnect_to_effect` (×2). Mechanism: with the early return deleted, a no-clock run falls
through past coupling (their module-patched transport is a fake, `resolved is not _REAL_CONNECT`, so
coupling passes) into the **COHERENCE** branch, where `coherent` is `False` (no clocks injected) →
`CLOCK_INJECTION_REFUSED: COHERENCE`. So the suite catches Mutation D **incidentally, via a different
branch (coherence), in unrelated tests** — NOT via any coupling-preservation check.

**The precise gap Assertion 5 closes (the real point of the section):** the gate's OWN dedicated test
(assertions 1–4) did **NOT** catch Mutation D — all four inject clocks, so the early return never
fired for them (the bite proof confirms 1–4 pass under D). And **no test directly asserted that the
COUPLING branch permits a real-transport, no-clock run** — the production path's permission was only
tested incidentally, through the coherence branch, and only because the early return happens to guard
coherence too. Assertion 5 makes the coupling branch's preservation dual **local and direct** (S13/D37
discipline), independent of that incidental coverage: if the coherence branch were ever changed, the
production-path permission would still be pinned.

---

## §3 — TWO CONSISTENCY CHECKS

### 3.1 Exception type — MATCHES (no action)
Both refusals raise `ValueError`: `GAP_PERSIST_UNCONFIGURED` (kraken_v2_book.py:2469) and
`CLOCK_INJECTION_REFUSED` (2411 COUPLING, 2424 COHERENCE). Same type, consistent with the
pre-connection refusal the gate was placed alongside. No difference; nothing to unify.

### 3.2 The three seams' default conventions — THREE DIFFERENT CONVENTIONS (recorded, not changed)

| Seam | Default in `__init__` | Convention | Resolution at use | Gate detects "injected" by |
|---|---|---|---|---|
| `_wall_clock` | `= None` (l.1154) | **raw None** | LATE: `self._wall_clock or time.time` (l.2531) | `is not None` (l.2401) |
| `_monotonic_clock` | `= monotonic_clock or time.monotonic` (l.1160) | **eagerly resolved** | direct: `self._monotonic_clock()` (l.2517/2563/2696) | `is not time.monotonic` (l.2402) |
| `_connect_fn` | `= connect_fn` (l.1171) | **raw None** | LATE: `self._connect_fn or websockets.connect` (l.2190/2409) | coupling: `resolved is _REAL_CONNECT` (l.2410) |

**Construction hazard for the 30-test conversion, recorded:** three fields, three different default
conventions and three different "is it injected?" tests. `_wall_clock` and `_connect_fn` are raw-None
+ late-resolved but detected differently (None-sentinel vs identity-vs-`_REAL_CONNECT`);
`_monotonic_clock` is eagerly resolved and detected by identity-vs-`time.monotonic`. The 30-test
conversion must be written against these REAL conventions, not an assumed symmetry (e.g. a test that
sets `_monotonic_clock = time.monotonic` explicitly reads as NOT injected; one that sets
`_connect_fn = websockets.connect` explicitly reads as the REAL transport and, with a clock, refuses).
**Not changed here** (per §3.2) — recorded so the conversion WO can be written correctly.

---

## §4 — ACCEPTANCE

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest -p no:randomly -rX` | **216 passed**, 0 f/xf/xp | **216 passed**, 0 f/xf/xp |
| `pytest --randomly-seed=20260725 -rX` | **216 passed**, 0 f/xf/xp | **216 passed**, 0 f/xf/xp |

- `lint-imports` → **6 kept, 0 broken** · `contract_count_check.py` → **6/6** · `ruff check .` →
  **clean** · `annotation_name_scan.py` → **0** · `preflight_path_check.py` → **pass**
- Bite proof: **5 assertions, 4 mutations, sha256 exact-restore** (above).
- **Test count stays 216** (assertion 5 added to the existing test; no new/removed test).
- **Ship impact:** tests + docs only — `kraken_v2_book.py` byte-unchanged (§1 found no defect).
- **Commit / push / CI:** committed `9175969` on master, pushed, local == remote. **CI run `30036599896` GREEN on BOTH legs** — test (3.11) success, test (3.14) success.

---

## STOPPED / attempts / changed-but-not-asked
- **STOPPED at:** nothing. §1's STOP condition (production defect) did NOT trigger — the early return
  covers the no-clock case. The §2 "would 216 catch Mutation D" answer disagreed with the WO's
  expectation ("no"); the accurate answer is YES (via coherence), reported per 0.1 — this is a
  report-answer the WO left open, not a STOP condition, and Assertion 5 remains the correct
  preservation dual regardless.
- **Every attempt reported (0.5):** the Mutation-D catchability was verified empirically (probe run,
  restored to pristine) rather than asserted — the probe found 6 existing tests catch it, correcting
  the WO's premise. No failed edits.
- **Changed but not asked?** Only: the existing bite-proof test (assertion 5 + docstring), this
  report, `progress.md` (§2c block), and §2c evidence. `kraken_v2_book.py` UNCHANGED.
  `instructions.md` carries the §2c WO text (present at session start). No other file.

**THEN STOP.** The 30-test conversion is NOT begun.
