# WO-023 §2c — THE COUPLING BRANCH'S PRESERVATION DUAL (the production path)

BASE: HEAD `fddf1cd` on master (local == remote). 216 passed both orders both interpreters,
CI green both legs (run 30030741629).

WO-023 §2b is ACCEPTED on mechanism: the identity keying is correct, the both-direction
verification is correct, Mutation C is a genuine discrimination proof, and the §7 VOID
correction is correct. This WO closes ONE gap the §2b report surfaced.

SCOPE: §1 and §2 ONLY. Commit green, STOP. Do not begin the 30-test conversion.
SHIP IMPACT: possibly (§1 may reveal a production-path defect; §2 is tests+evidence only).

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins; if code and this order disagree, STOP and report.
0.2 No monkeypatching to make a guard pass.
0.3 Fail-then-pass bite proof, four artifacts, sha256 exact-restore.
0.4 Preservation duals mandatory.
0.5 Report every attempt.
0.6 **AUTO MODE OFF** for any edit to `kraken_v2_book.py`.
0.7 Report your context % as READ FROM `/context`, not estimated.

---

## §1 FIRST ACTION — PASTE THE GATE, DO NOT DESCRIBE IT

Before editing anything, paste `_assert_clock_transport_gate` **in full, verbatim, with line
numbers**, from its `def` line to its last line, plus the call site in `get_live_market_data`.

The §2b report's excerpt showed:

    resolved = self._connect_fn or websockets.connect
    if resolved is _REAL_CONNECT:
        raise ValueError("CLOCK_INJECTION_REFUSED: COUPLING — …")

with NO `clock_injected` precondition, though the WO specified
`if clock_injected and resolved is _REAL_CONNECT`. Read literally, that refuses EVERY REAL RUN:
a default-constructed adapter has `_connect_fn is None`, so `resolved is _REAL_CONNECT`, so
`get_live_market_data` raises before connecting — the 24-hour corpus capture would refuse to
start. The foundation's §4.2 early return ("no injected clock → return immediately") probably
sits above it and makes this safe.

**Do not tell me which it is. Show me the code.** Then state explicitly: is the coupling branch
reachable when NO clock is injected — yes or no?

If the precondition is genuinely absent and the early return does not cover it, that is a
SHIPPED PRODUCTION DEFECT on the live path: STOP, report, and wait. Do not fix it in the same
breath as discovering it.

---

## §2 THE MISSING PRESERVATION DUAL — REAL TRANSPORT, NO CLOCK, MUST PROCEED

### Why this is the gap
Every existing test that injects no clock ALSO module-patches the transport, so `resolved` is a
fake and `is not _REAL_CONNECT` — those tests pass **whether or not the precondition exists**.
Assertion 2's preservation half is *fake transport + fake clock*. Mutation A neutered the whole
gate, which cannot detect a missing precondition INSIDE it.

So the single case that discriminates — **real transport + no clock injected → PROCEEDS** — is
the production path, and no test in 216 exercises it. Assertion 1 proves the gate refuses the
hazard; nothing proves it permits the real run. That is the coupling branch's preservation dual
(D37/S13), and it is the half that carries the corpus.

### Assertion 5 — add to the EXISTING test (count stays 216)
`tests/integration/test_clock_injection_gate.py::test_clock_injection_gate` gains:

5. **DEFAULT-PATH PRESERVATION** — no clock injected (`_wall_clock` default, `_monotonic_clock`
   default), `connect_fn=None`, and the transport resolving to a callable that IS identical to
   `_REAL_CONNECT` → the gate **PROCEEDS**: no refusal raised, the transport IS invoked
   (`connect_count == 1`), and the run reaches the same successful end state assertion 2 checks.

Construct it with the mechanism assertion 4 already established: patch BOTH `_REAL_CONNECT` and
`websockets.connect` to ONE captured bound method of a self-terminating spy, so the gate performs
its genuine `is` comparison and resolves TRUE, against a safe stand-in. **NO GENUINE SOCKET.**
Observe the bound-method identity pitfall already reported in §2b — one captured bound method
shared by both patches.

This is the inverse of assertion 4 and must be adjacent to it in the test, with a comment naming
the pair: assertion 4 = real transport WITH a clock refuses; assertion 5 = real transport WITHOUT
a clock proceeds. Together they prove the coupling branch is conditioned on clock injection and
not on transport identity alone.

### Mutation D — the bite
Re-run the bite proof with a FOURTH mutation: **delete the `clock_injected` precondition** (or
the early return, whichever actually guards the branch — state which you mutated and why it is
the correct target). Assertion 5 must FAIL. Assertions 1–4 must still pass, proving the mutation
is discriminated by the new assertion alone.

Full four-artifact protocol, sha256 exact-restore, all mutations A/B/C/D.

### Report explicitly
State whether Mutation D, before this WO, would have been caught by ANY of the 216 tests. If the
answer is no — say so plainly. That is the finding, and it is the point of the section.

---

## §3 TWO CONSISTENCY CHECKS (report answers; change nothing without reporting first)

3.1 The gate raises `ValueError`. Confirm this matches the exception TYPE used by
    `GAP_PERSIST_UNCONFIGURED`, the refusal this gate was placed alongside for consistency. If
    they differ, report the difference and STOP — do not unify them in this WO.
3.2 Confirm the three seams' default conventions and state them in one table: `_wall_clock`
    (raw `None`?), `_monotonic_clock` (eagerly resolved to `time.monotonic`?), `_connect_fn`
    (raw `None`, resolved late?). Three fields with three different default conventions is a
    construction hazard for the 30-test conversion. Do not change them here — record them, so
    the conversion WO can be written against the real conventions rather than an assumed
    symmetry.

---

## §4 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → **216 passed**, 0 failed / 0 xfailed / 0 xpassed
- `pytest tests/ --randomly-seed=20260725 -rX` → same
- BOTH interpreters (3.11 strict, 3.14 dev)
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff check .` clean ·
  `annotation_name_scan.py` 0 · `preflight_path_check.py` pass
- Bite proof: **5 assertions, 4 mutations**, sha256 exact-restore
- Commit, push, local == remote, CI green BOTH legs via `gh run view`
- Append a §2c block to `progress.md`; do not rewrite existing content

Report `WO-023-2C-REPORT.md`: the verbatim gate paste from §1, the yes/no reachability answer,
assertion 5, the four-mutation bite proof verbatim, the "would 216 have caught Mutation D"
answer, the two §3 tables, `/context` reading, and any point you STOPPED.

**THEN STOP.** The 30-test conversion is NOT begun.