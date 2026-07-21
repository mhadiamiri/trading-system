# WORK ORDER — WO-014c-3: §0 Carry-Over Probes + Stub-Lint + Widened Precondition Sweep

**Status:** ACTIVE. Fresh session. WO-014c-2 COMPLETE.
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.
**Baseline:** the WO-014c-2 report commit — state it at preflight. 167 passed both orders,
0 failed / 0 xfailed / 0 xpassed, import-linter 6/6, contract 6/6, ruff clean.
**NO VENUE CONNECTION.** Simulated transport only.
**Standing rules 0.1–0.9 apply in full.** Note 0.6c is amended: `instructions.md` is
committed with its WO, so at preflight it is either committed or genuinely unmodified —
a modified `instructions.md` now means the WO text changed mid-flight.

## §0 — CARRY-OVER PROBES (do these FIRST; answer with pasted evidence)

Three questions from the 014c-2 review. Each is cheap now and impossible-to-repair later.
**If any requires a production change beyond a trivial fix, STOP and report rather than
absorbing it** — that instruction surfaced two real hazards last time.

### 0.1 — IS THE GAP LEDGER PERSISTED? (highest priority)
`GapLedger` is described as an in-memory structure with computed properties. For a
60-minute run and later a 24-hour capture, that is only useful if it survives to disk.
- Is the ledger written out? When — periodically, or only at capture end?
- **Does it survive a BREAKER TRIP?** That is the terminal event it most needs to
  document, and a ledger flushed only on clean shutdown would be lost on exactly the
  failure it exists to record.
- Does it survive an unhandled exception or process kill?
- If it is written only at the end, the ~116-reconnect scenario means a run that dies at
  minute 58 loses every gap record it accumulated.
State the answer plainly. If persistence is absent or end-only, report it as a finding
with a proposed fix — **do not implement without approval.**
Evidence → `evidence/WO-014c-3/ledger_persistence.txt`

### 0.2 — IS FAILURE-CAPTURE RETENTION BOUNDED?
Every checksum failure persists the failing frame plus 20 preceding frames of raw wire
text. Correct for the observed 0.021% rate. But the rate is UNDIAGNOSED — that is why
the capture exists.
- Is there any cap on total failure-capture retention?
- If failures cluster pathologically (a resync loop, a rendering regression on a symbol
  we haven't seen), what bounds disk growth over 24 hours?
- **A capture that fills the disk ends the run it was meant to document.**
If unbounded, report as a finding with a proposed bound — and state how the bound
**announces itself** when hit rather than silently truncating. A silently-truncated
failure ledger is the same defect class as positional sampling.
Evidence → `evidence/WO-014c-3/capture_retention.txt`

### 0.3 — DECLARE THE WALL/MONOTONIC DRIFT BOUND
`wall(t) = run_wall_anchor + (t − run_monotonic_anchor)` assumes both clocks advance at
the same rate. Over 24 hours, NTP slewing can separate them by seconds.
- This is not a defect — one anchor was the right call, and mixed bases would be worse.
  It is an **undeclared limit**, and this project declares limits.
- State the expected drift bound over a 24-hour run and confirm it is acceptable for
  locating gaps in calendar time (it almost certainly is).
- Put it in the ledger's docstring alongside the anchor, same discipline as the
  active-probe limit.
Evidence → `evidence/WO-014c-3/clock_drift_limit.txt`

## §1 — MAKE 0.1g MECHANICAL (stub-lint)

Lint check for `pass`-bodied and bare-`return`-bodied functions in production modules
under `src/`.
- **Allowlist legitimate cases with EXPLICIT JUSTIFICATION** — protocol stubs on ABCs,
  etc. Per ruling: *an unexamined exception is how 0.1g gets its own 0.1d.* Every entry
  names why.
- If it changes the import-linter contract count, update `EXPECTED_CONTRACT_COUNT` **in
  the same commit**.
- **Bite proof:** introduce a `pass`-bodied production function → PASTE THE ACTUAL
  FAILING OUTPUT → remove → PASS → `sha256` exact-restore.
- **Run against the current tree and report EVERY hit** — §2 consumes this output.

Historical note for calibration: this rule was ruled after `_request_snapshot(): pass`
zeroed 48 of 60 minutes, and `_reconnect(): pass` meant the five-failure recovery never
worked. Both are now implemented; the lint is what stops the third instance.
Evidence → `evidence/WO-014c-3/stub_lint.txt`

## §2 — WIDENED PRECONDITION SWEEP (REPORT ONLY — fix nothing)

**State the denominator first.** An audit without a denominator audits what it noticed —
three prior instances.

Hunt BOTH shapes:
- **SHAPE A (0.1h):** tests that SUPPLY what production is supposed to produce — the test
  hand-feeds a precondition. *(S10: the fresh snapshot.)*
- **SHAPE B (0.1i):** tests that STOP AT A CALL BOUNDARY the production path continues
  through — the test asserts invocation and never verifies the effect.
  *(`_reconnect`: escalation fires, callee was `pass`.)*

Shape B is mechanically detectable: cross-reference call-assertions (`assert_called*`, or
any assertion whose subject is "was invoked") against §1's stub-lint output. **Run §1
first so §2 consumes its results.**

- **REPORT ONLY. Fix nothing.**
- State how each hit was found — semantic reading vs. pattern match.
- If the count is a cluster, it returns to the project lead on standing pre-authorized
  terms. Report the number; do not act on it.
Evidence → `evidence/WO-014c-3/precondition_sweep.txt`

## §3 — VERIFY, COMMIT, PUSH
    pytest tests/ -p no:randomly -rX
    pytest tests/ --randomly-seed=<state it> -rX
    lint-imports
    python tools/contract_count_check.py
    ruff check .
0 failed / 0 xfailed / 0 xpassed BOTH orders. Explain every delta. Per 0.2a stop before
push if you cannot reach it. Secret scan, push, paste local vs remote HEAD.

## §4 — FINAL REPORT — then STOP
1. **§0.1 ledger persistence** — persisted? Survives a breaker trip? An exception? A kill?
2. **§0.2 capture retention** — bounded? If not, proposed bound and how it announces itself.
3. **§0.3 drift** — expected bound over 24h, acceptable? Docstring pasted.
4. **Stub-lint** — bite proof, EVERY hit in the current tree, every allowlist entry with
   its justification.
5. **Sweep** — the denominator, the count, how each hit was found, shape A vs B. Cluster?
   Confirm you fixed nothing.
6. Verification: both runs with seeds and durations, deltas, linter, contract count, ruff,
   local/remote HEAD.
7. **Venue connection?** YES/NO. **HTTPS doc fetch?** YES/NO.
8. **Prose standing in for output?** YES/NO.
9. **Changed but not asked?** Every file, or "none."
10. **What could not be completed, and why?** Named seam: after §0 (probes answered and
    committed), before §1.

STOP for review. Do NOT proceed to the re-run.