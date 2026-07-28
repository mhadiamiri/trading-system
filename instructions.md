# WO-033 — BOUND MEASUREMENT PASS: measure all 6 remaining audit bounds. CLASSIFY ONLY.

BASE: current HEAD on master (WO-031 close, `aef3166`) — confirm actual HEAD in §1 and use it.
222 both interpreters, CI green both legs (run 30316789147).

SCOPE: **MEASURE AND STOP.** Converts nothing, threads no seam, edits no test/src/fixture. Runs the
D40-ruled measurement on the 6 remaining audit BOUNDS (entries 31–34, 36–37) and reports each one's
MEASURED category. One committed evidence artifact + a re-runnable probe under `tools/` +
progress.md. Nothing else.
SHIP IMPACT: **NO.** Every production and test file byte-unchanged; §5 proves it (five sha256s).

WHAT D40 RULED (this WO executes ruling 2 verbatim):
- Entry 35 already reclassified to a RACE (ruling 1): clock-injectable 26→27, bounds 7→6. It is NOT
  in this WO — it is settled; its home is batch C (now 9). This WO measures the OTHER SIX.
- **Measure all six before batch C is planned.** The audit's bound/race split is prose margin-
  reasoning; 1-of-7 was already wrong (entry 35). Doctrine line, ratified:
  **bound-versus-race is a measurement, not a margin argument; a bound classified by prose ratio is a
  race pending measurement.**
- **Two measurement DESIGNS, by claim-kind — the distinction is honored in the measurement, not used
  to exempt any bound from measurement:**
  - **Structural pair (entries 36–37, "terminates BEFORE the deadline is consulted"):** a
    ZERO-CONSULTATION probe — instrument the deadline read and demonstrate the deadline clock is
    consulted ZERO times on the test's path. Converts "never consulted" from assertion to observation.
  - **Ratio cases (entries 31–34, "~300× margin"):** the existing margin probe measures the ACTUAL
    margin against the ACTUAL work — the frames-reached / terminator-timing form from WO-031 §3-bis.
- Expectation set by the lead: **the pass may flip another entry.** That moves the denominator again,
  and that is the pass doing its job, not churn. Report a flip as a finding; do not fold it into a batch.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report. A flip (a bound measuring as a race)
    is an EXPECTED possible outcome, reported and escalated — not a failure, and not folded into a batch.
0.2 No conversions, no seam threading, no test/src/fixture edits. One evidence artifact + one tools/
    probe (writing to `.artifacts/`, per the WO-032 boundary) + progress.md. If you edit a test or src
    file, you have exceeded scope — STOP.
0.3/0.4 No guards built; no bite proof owed. The probe is a re-runnable tool, not a guard — but it
    MUST write to `.artifacts/`, never `evidence/` (a tools/ script writing under evidence/ now FAILS
    `tests/test_evidence_write_boundary.py`).
0.5 Report every attempt.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | WO-023 §1 audit: 30 races + BOUNDS (entries 31–37) | **OPERATED** | `86e2a33` — entry 35 now reclassified (D40) |
    | `tools/wo031_bound_reaudit_probe.py` (margin/frames-reached form) | **OPERATED** | WO-031 §3-bis; generalizes by swapping script+duration |
    | `AdvancingClock` fixture | **OPERATED** | WO-029 §2.0-bis, shared harness |
    | D40 doctrine (bound-vs-race is a measurement) | **OPERATED** | `d40` — echo into a decision doc, §4 |
    | The zero-consultation probe (structural pair) | **THIS WO IS THE BUILDER** | Does not exist — §3.A |
    | The measured category of all six bounds | **THIS WO IS THE BUILDER** | Does not exist — §3 |

    Any OPERATED row not verified → STOP.

---

## §1 CONFIRM HEAD, SUITE, DENOMINATOR STATE
State actual HEAD. `pytest tests/ -p no:randomly -rX` both interpreters → confirm **222**. Run
`wo029_reverify_partition.py` → PASS 30/30 by name, writes `.artifacts/`, `git status` clean after.
State the current denominator per D40: **clock-injectable 27, bounds 6, audit total 30** (entry 35
moved; this WO measures the surviving 6 bounds).

The six under measurement, with the audit's prose justification and the ruled design for each:

| Entry | Bound test | Audit prose | Design |
|---|---|---|---|
| 31 | `test_backoff_breaker.py:88 test_persistent_reopen_failure_trips_breaker_loud` | 30 s dl vs ~0.1 s breaker | RATIO probe |
| 32 | `test_gap_recording.py:202 test_terminal_venue_disconnect_breaker_gap_recorded` | 30 s dl vs breaker | RATIO probe |
| 33 | `test_live_capture.py:172 test_breaker_trip_terminates_run_with_forensic_tail` | 30 s dl vs breaker | RATIO probe |
| 34 | `test_reconnect_to_effect.py:100 test_stranded_reconnect_flag_fails_loudly` | 30 s dl vs flag-raise | RATIO probe |
| 36 | `test_no_silent_fallback.py:25 test_connection_failure_raises_and_does_not_replay` | raises during connect, before loop | ZERO-CONSULTATION probe |
| 37 | `test_no_silent_fallback.py:52 test_live_method_refuses_fixture_mode_adapter` | refuses pre-loop, dl never consulted | ZERO-CONSULTATION probe |

Confirm these six names+lines resolve at HEAD before measuring; if any differs, note it (not a STOP —
just report the current identity).

---

## §3 THE MEASUREMENTS

### §3.A ZERO-CONSULTATION PROBE — entries 36, 37 (this WO builds it)
The structural claim is "the deadline clock is never consulted on this test's path." Convert it from
assertion to observation:
- Instrument the deadline read — wrap/count consultations of `_monotonic_clock` at the deadline sites
  (the 3 sites WO-031 §3-bis pinned: deadline set / deadline guard / recv timeout), via a counting
  clock injected through the same seam a conversion would use. Do NOT edit src to instrument — inject
  a counting clock as the test would inject a fake one (the seam exists post-WO-030).
- Run each test's exact path and record the CONSULTATION COUNT.
- **Verdict per test:** count == 0 → the structural claim is OBSERVED; the test terminates before the
  deadline is ever read; it is a genuine BOUND (structurally, not by margin). count > 0 → the deadline
  IS consulted; the "never consulted" claim is false and the entry is a RACE pending the same
  outcome-bearing/incidental classification as any race (run D39's method on it, name the assertion).
- Note: a counting clock must still be COHERENT (pass the gate) — inject it as a coherent pair or via
  the injected-transport path, per batch A's pattern, so the gate does not refuse and mask the count.
  If the gate refuses, that is an injection error, not a finding — fix the injection, per WO-031 §Attempt 6.

### §3.B RATIO / FRAMES-REACHED PROBE — entries 31, 32, 33, 34 (existing tool, generalized)
Use `tools/wo031_bound_reaudit_probe.py`'s form (swap script + duration). For each: drive the test's
path under real clock and under `AdvancingClock` at a spread of deltas (include a delta near the
audit's implied margin AND deltas fast enough to make the deadline win, as WO-031's delta=0.05 row
did). Record, per delta: whether the terminator (breaker trip / flag-raise) is reached BEFORE the
deadline fires.
- **Verdict per test:** the terminator always precedes the deadline across the realistic delta range →
  genuine BOUND, the margin is MEASURED not assumed. There exists a delta where the deadline wins and
  changes the outcome an assertion rests on → RACE (the entry-35 shape); run D39's method, name the
  assertion, report the reclassification.
- State the ACTUAL measured margin (terminator time vs deadline) for each — "~300×" was the audit's
  prose; replace it with the number.

### §3.C AGGREGATE
- Per entry: design used, measurement, verdict (BOUND-measured / RACE-flipped), and for any flip the
  D39 classification (outcome-bearing read named, assertion named, injectable or not).
- New denominator state: clock-injectable = 27 + (flips), bounds = 6 − (flips), total 30.
- **Any flip ESCALATES** as a reclassification (like entry 35) — reported, not folded into a batch.
  State whether batch C's denominator is now settled (all 6 measured, N flips reported) or whether a
  flip needs a lead ruling before batch C is planned (it does — a denominator change is the lead's).

---

## §4 DECISION DOC
`docs/decisions/2026-07-27-bound-versus-race-is-a-measurement-not-a-margin.md` — the D40 doctrine line
verbatim: *bound-versus-race is a measurement, not a margin argument; a bound classified by prose ratio
is a race pending measurement.* Record it as the SEVENTH specimen of the prose-figure family and the
FIRST found in an audit's OWN taxonomy rather than in what the audit examined. Carry Claude Code's
sentence: *what differs is the ratio, not the rhetoric.* Note the recursion: the audit that defined
pass two is now held to pass two's own evidentiary standard.

---

## §5 SCOPE FENCE
Converts NO race. Threads NO seam. Edits NO test/src/fixture. Plans NO batch C (produces the measured
bound set that lets it be planned). Does NOT fold a flip into a batch — escalates it. Touches entry 35
NOT AT ALL (settled, ruling 1). Touches NONE of the 3 asyncio.sleep races.

## §6 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → 222 both interpreters (unchanged — edits no test)
- `wo029_reverify_partition.py` → PASS 30/30 by name, `.artifacts/`, `git status` clean after
- Five src sha256 IDENTICAL (`b06c347e…`,`103a8ba7…`,`5bf833c7…`,`dab18f67…`,`3d153a11…`);
  `git diff -- src/ tests/` empty
- `test_evidence_write_boundary.py` PASSES (both probes write to `.artifacts/`)
- lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass
- `evidence/WO-033/bound_measurement_pass.md` committed; the §4 decision doc committed
- progress.md WO-033 block; commit, push, local == remote, CI green both legs (REAL run number)

## §7 REPORT — `WO-033-REPORT.md`
Per-entry: design used, the measurement table, the verdict, and for any flip the full D39
classification. The §3.C aggregate with the new denominator state and whether batch C is settled or
gated on a flip ruling. The zero-consultation probe's mechanism (how it counts without editing src).
The decision doc as committed. Five unchanged sha256. Every attempt; any STOP. The CI run number, real.

**THEN STOP.** If all six measure as bounds → batch C is planned against the measured set (9 races).
If any flips → the reclassification escalates before batch C. The keepalive seam WO runs in parallel,
separately.