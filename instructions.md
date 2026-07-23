# WORK ORDER — WO-023: Wall-Clock Race Audit → Deterministic Driving → Re-Run Precedent

**Status:**  **NO VENUE CONNECTION.**
**READ FIRST:** `WO-022-REPORT.md` §6 (the flake finding),
`docs/decisions/2026-07-23-an-environment-is-strict-along-axes.md`,
`tests/integration/test_ledger_persistence.py`, `tests/fixtures/fake_ws_transport.py`.
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.
**Baseline:** `d9bcd74` — **CI GREEN ON BOTH LEGS**, run `29981099178`: preflight ✓,
`import-linter lint` 6 kept / 0 broken ✓, annotation detector ✓, 215 passed both orders on 3.14 and
3.11. Local 215 both orders on both interpreters.
**Standing rules 0.1–0.9 apply in full, including 0.1j and 0.1k.**

**WHERE THE OPERATED THINGS WERE BUILT:** the simulated transport harness is
`tests/fixtures/fake_ws_transport.py` (WO-014b onward — **extend, never rebuild**); gap-ledger
persistence is WO-014c-3 §0.1.

## WHY THIS EXISTS
`test_gap_ledger_persisted_readable_from_disk` gates its assertion on a **0.25 s real wall-clock
deadline** racing a disconnect→reconnect→gap-open→resolve cycle. Under CI scheduling load the deadline
won, 0 gaps were produced, and the test failed. A re-run passed.

**The finding is not "a flaky test." It is that A FLAKE POISONS THE FAILURE SIGNAL WHILE LEAVING THE
PASS SIGNAL INTACT.** A pass still proves the path — gap produced, persisted, read from disk. Every
FAILURE becomes ambiguous between race and regression. And the ambiguity attaches to **gap-ledger
persistence**: the kill-durable path WO-014c-3 built because *"the mechanism that documents the
terminal event must survive the terminal event,"* and the path the 24-hour corpus's honesty stands on.

A real persistence regression would present identically to "the known flake" and be re-run past. That
is erosion of the investigate-first corollary by habituation, one dismissed failure at a time. **The
fix restores the failure signal's meaning, which is worth more than the green it stabilizes.**

## OUT OF SCOPE
- The taxonomy migration, 008c, the corpus. **NO VENUE CONNECTION.**
- Widening any deadline. See §2 — that is refused by ruling.

## §1 — THE DENOMINATOR, FIRST. Commit it standalone before fixing anything.

One test found by accident under CI load is **a sample, not a denominator.**

Enumerate **every test that gates an assertion on a real wall-clock deadline, `sleep`, or timeout.**
Search for all the forms: `time.sleep`, `asyncio.sleep` with real durations, `asyncio.wait_for`,
deadline parameters, `time.monotonic()`/`time.time()` comparisons controlling a loop, pytest timeouts.
**State how each was found**, and **name any form your search cannot see** — the recurring lesson is
that a check is bounded by the form it matches.

**Classify each into exactly one of two categories**, because they get different remedies:

- **STRUCTURAL RACE** — the assertion depends on WINNING A TIMING GAMBLE. The test can fail with the
  production code perfectly correct. **These get driven deterministically (§2).**
- **DETERMINISTIC OPERATION WITH A BOUND** — the timeout is a BACKSTOP against a hang, not a gate on
  the assertion. The operation completes deterministically; the bound only prevents an infinite wait.
  **These are LEGITIMATE AND STAY.**

For each classified as a race, note whether it touches a **corpus-critical path** (gap ledger, failure
capture, checksum validation, reconnect/recovery, the instruments).

**Report the count before fixing anything.** If the count is large, that is a finding and the fix
scope comes back for a ruling rather than expanding silently.
Evidence → `evidence/WO-023/wall_clock_race_audit.txt`

## §2 — FIX THE STRUCTURAL RACES BY DETERMINISTIC DRIVING

**WIDENING A DEADLINE IS TUNING TO GREEN — refused by ruling.** It changes the race's odds, not its
existence; the test still gambles against scheduler load and will lose again on a slower runner or
under the heavier corpus-era suite. Same shape as the `monkeypatch` defeat mechanism ruled out in
WO-012c: patch-based mitigation of a structural problem.

- **Drive the cycle to completion deterministically.** `fake_ws_transport.py` already scripts
  disconnects, reconnects, and failure sequences — **EXTEND IT, do not rebuild.** The gap cycle should
  be driven, not awaited against a clock.
- Order-independent and load-independent **by construction**, not by margin.
- **The assertion must still be the same assertion.** A deterministic test that asserts something
  weaker than the racy one did is a downgrade wearing a fix's clothes — state explicitly, per test,
  that the guarantee is unchanged or strengthened.
- **Bite proof each fixed test, four artifacts, `sha256`:** break the production path the test covers
  → the test FAILS with real output → restore → passes. This proves the deterministic version still
  DETECTS, which is the whole point of restoring the failure signal.

## §3 — THE CORPUS-ERA PROJECTION (answer with the audit's numbers)
Do longer runs, heavier hosts, and parallel CI legs lengthen scheduling tails enough to promote any
remaining race from hygiene to **pre-corpus blocker**?

The project lead's prior: **yes for any structural race touching a corpus-critical path.** The audit
converts that prior into a measured claim — answer it with §1's classification in hand, not from
intuition. If §2 eliminates every corpus-critical race, say so plainly and the question closes.

## §4 — THE RE-RUN PRECEDENT, RECORDED AS A STANDING RULE

Add to the standing rules and to `progress.md`:

  **A RE-RUN IS PERMITTED ONLY WHEN THE PRIOR FAILURE HAS BEEN DIAGNOSED AND ATTRIBUTED FIRST, AND
  BOTH ATTEMPTS ARE REPORTED. UNDIAGNOSED RE-RUNNING IS PROHIBITED OUTRIGHT.**

  **THE ATTRIBUTION MUST REST ON MECHANISM, NOT ON OUTCOME.** A re-run's green is CORROBORATION,
  NEVER EVIDENCE — it is equally consistent with an intermittent regression. What made WO-022's
  instance compliant is that the attribution stood on the race mechanism identified in the test's
  construction, before the re-run, not on the re-run's result.

  Absent this clause the rule's failure mode is **diagnosis-shaped rationalization**: "probably the
  flake" written before, "confirmed by re-run" written after — undiagnosed re-running with paperwork.

  Note the intended direction: **once the structural fixes land, this rule's domain shrinks toward
  zero for the fixed tests.** It governs the residue, not the steady state.

## §5 — DECISION LOG
  *"A FLAKE POISONS THE FAILURE SIGNAL WHILE LEAVING THE PASS SIGNAL INTACT. A pass still proves the
  path — the gap was produced, persisted, and read from disk. But every failure becomes ambiguous
  between race and regression, and the ambiguity attached to gap-ledger persistence: the kill-durable
  path the corpus's honesty stands on. A real regression would present identically to 'the known
  flake' and be re-run past — erosion of the investigate-first corollary by habituation, one dismissed
  failure at a time. Widening the deadline was refused as TUNING TO GREEN: it changes the race's odds,
  not its existence. The fix restores the failure signal's meaning, which is worth more than the green
  it stabilizes. Corollary recorded with it: a re-run's green is corroboration, never evidence, and
  attribution must rest on MECHANISM rather than on OUTCOME — otherwise the re-run rule degenerates
  into undiagnosed re-running with paperwork."*

## §6 — VERIFY, COMMIT, PUSH
Local, **both interpreters**, both orders each:
    pytest tests/ -p no:randomly -rX
    pytest tests/ --randomly-seed=<state it> -rX
    lint-imports
    python tools/contract_count_check.py
    ruff check .
    python tools/annotation_name_scan.py
0 failed / 0 xfailed / 0 xpassed everywhere. Explain every delta. Secret scan. Push, paste local vs
remote HEAD.

**Then observe the real CI run**, both legs, and paste it. **If a leg fails, §4 governs: diagnose and
attribute from mechanism BEFORE any re-run, and report every attempt.**

**Does this affect what ships?** State it. Expected **NO** — tests and docs only.

## §7 — HOT-PATH JUDGMENT
State it explicitly and argue it out rather than assuming it.

## §8 — REPORT — then STOP
1. **THE DENOMINATOR** — every wall-clock-gated test, how found, forms your search cannot see, and the
   two-way classification. **The count.** Which races touch corpus-critical paths?
2. **Each fixed race** — the deterministic mechanism, confirmation the harness was EXTENDED not
   rebuilt, and **confirmation the assertion is unchanged or stronger, per test.**
3. **Bite proof per fixed test** — four artifacts with `sha256`, showing the deterministic version
   still DETECTS a real break.
4. **Any test left as a legitimate backstop** — named, with why it is not a gate.
5. **§3 corpus-era projection**, answered from the audit's numbers.
6. **§4 recorded** in the standing rules and `progress.md`. Pasted.
7. Decision-log entry pasted.
8. **Verification on both interpreters locally, then the real CI run on both legs.** Green?
9. **Affects what ships?** YES/NO. **Hot-path judgment**, argued.
10. **Venue connection?** YES/NO. **HTTPS?** YES/NO.
11. **Prose standing in for output?** YES/NO.
12. **Changed but not asked?** Every file, or "none."
13. **What could not be completed, and why?**

**NAMED SEAM: after §1 (denominator committed standalone), before §2.**

STOP for review. Do NOT begin the taxonomy migration.

----

update:

# WO-023 §2 — FOUNDATION ONLY. Three-field pre-connection clock gate.

BASE: HEAD `0fd13fe` on master (local == remote). 215 passed both orders, both interpreters.
import-linter 6/6, contract 6/6, ruff clean, annotation_name_scan 0.

SHIP IMPACT: **YES** — production change authorized by ruling D34.
SCOPE: **FOUNDATION ONLY.** Commit green, then **STOP**. The 30-test conversion, §3, §4 and §5
go to a FRESH session. Do not begin them. Do not "just also" convert a second test.

---

## §0 RULES OF ENGAGEMENT

0.1 **No discretion.** Every section below is mandatory and literal. Where this order and the
    code disagree, the CODE WINS and you STOP and report — do not reconcile silently. That rule
    is why this WO exists: it fired last session and corrected two of the lead's rulings.
0.2 **No monkeypatching to make a guard pass.** If a guard cannot see something it must see, the
    object model is wrong. Report it; do not reach around it.
0.3 **Every guard gets a bite proof**: shown FAILING, then PASSING, with the four artifacts and
    `sha256` exact-restore of the mutated file. A guard without a fail-then-pass is not accepted.
0.4 **Preservation duals are mandatory** (S13/D37). A guard that refuses everything passes its
    refusal half and looks correct. Both halves in the same test.
0.5 **Report every attempt**, including the ones that failed and were retried.
0.6 **No auto mode** for any edit in §2, §3 or §4.
0.7 If you reach ~70% context, STOP at the nearest clean seam, commit what is green, and report.

---

## §1 THE `_monotonic_clock` SEAM (RULING D34-1)

Add to `KrakenV2BookAdapter.__init__`:

    self._monotonic_clock = monotonic_clock or time.monotonic

Route BOTH deadline lines in `get_live_market_data` through it:
- `kraken_v2_book.py:2388`  `deadline = time.time() + duration_seconds`
  → `deadline = self._monotonic_clock() + duration_seconds`
- `kraken_v2_book.py:2434`  `while time.time() < deadline`
  → `while self._monotonic_clock() < deadline`

RATIONALE, to be reflected in a comment at 2388: **a duration is an INTERVAL; D25 puts intervals
on monotonic.** `_wall_clock` is NOT the deadline clock — line 1136 already says so, and it is
load-bearing for the suspend detector.

DO NOT touch `_wall_clock`'s existing consumers. DO NOT add `from __future__ import annotations`.

**Checkpoint A:** after §1 alone, run `pytest tests/ -p no:randomly -rX`. Expected **215 passed,
0 failed/xfailed/xpassed**. If not 215, STOP and report — the seam is not backward-compatible and
that is a finding.

---

## §2 THE `_connect_fn` SEAM (RULING D34-2)

The transport is currently module-level `websockets.connect`, monkeypatched by tests — the object
cannot name its own transport, which is why the coupled check had nothing to compare against.

Add to `KrakenV2BookAdapter.__init__`:

    self._connect_fn = connect_fn or websockets.connect

Replace the module-level call site(s) inside the adapter with `self._connect_fn(...)`. Enumerate
EVERY call site you change and list them in the report.

**Checkpoint B:** run the deterministic suite again. Expected 215. Module-level monkeypatching in
existing tests must STILL WORK (the default is resolved at call time through the field, which
still resolves to the patched module attribute only if you bind late — verify this explicitly and
state in the report which binding you chose and why). If late binding is required for 215 to hold,
say so; if it conflicts with the gate's ability to detect a default transport, **STOP and report
— that is a finding, not something to work around.**

---

## §3 THE COHERENT FakeClock HARNESS (GUARD 2)

EXTEND `tests/fixtures/fake_ws_transport.py`. **Do not rebuild it.**

ONE fake time source serving BOTH interfaces: `wall` and `monotonic` derived from a single
counter with a FIXED OFFSET, so D25's doctrine (monotonic orders, wall locates) holds INSIDE the
fake. Advancing the source advances both by the same delta.

Expose a coherent pair as the DEFAULT construction. Incoherent construction must be a separate,
explicitly-named factory — never the default path.

---

## §4 THE THREE-FIELD PRE-CONNECTION GATE + REASON CODE (RULINGS D34-2, D34-3)

### 4.1 Reason code
Declare **`CLOCK_INJECTION_REFUSED`** in `src/trading/logkit/decision.py` (`VALID_REASON_CODES`).
Both vocabulary properties proved (declared⇒producible, raised⇒declared), both literal forms.

Its docstring carries the ruled invariant VERBATIM:

    A NON-DEFAULT CLOCK IS PERMITTED ONLY WHERE THE TRANSPORT IS ALSO NON-DEFAULT.
    A REAL TRANSPORT WITH A FAKE CLOCK REFUSES, PRE-CONNECTION, WITH THE DECLARED CODE.

### 4.2 The gate
Placement: **before any connection attempt**, same placement discipline as
`GAP_PERSIST_UNCONFIGURED`. It inspects three constructor-injected fields — `_wall_clock`,
`_monotonic_clock`, `_connect_fn` — and asserts:

1. **COUPLING** — if either clock is non-default, `_connect_fn` MUST also be non-default.
2. **COHERENCE** — if clocks are injected, they MUST be the coherent pair (one source, both
   interfaces), UNLESS the named exception is explicitly passed.

Violation → refuse with `CLOCK_INJECTION_REFUSED`, before connecting. The refusal payload MUST
name WHICH assertion failed (coupling vs coherence) — one code, diagnosable.

### 4.3 The named exception (RULING D34-3 — explicit, never inferred)
An explicit per-invocation named argument the gate reads, of the shape:

    incoherent_clocks_allowed="suspend-detector-test"

**The gate MUST NOT infer the exception from the injection pattern.** *Inference is vigilance.*
A gate that deduces "this looks like the suspend test" will one day bless an accidental
incoherence that happens to match the shape. Every incoherent run in the project's history must
be greppable by its declaration.

---

## §5 THE BITE PROOF — THREE ASSERTIONS, ONE TEST (D37 + D34-3)

Four artifacts, `sha256` exact-restore. All three in the same test:

1. **REFUSAL** — real transport (default `_connect_fn`) + fake clock → refuses with
   `CLOCK_INJECTION_REFUSED`, **before any connection attempt** (prove pre-connection: the
   connect callable is never invoked).
2. **PRESERVATION** — fake transport + coherent fake clock pair → PROCEEDS.
3. **THE EXCEPTION'S OWN DUAL** — the identical incoherent injection:
   - passed WITH `incoherent_clocks_allowed="suspend-detector-test"` → PROCEEDS;
   - passed WITHOUT it → REFUSES with the declared code.

Assertion 3 is what keeps the escape hatch from becoming a hole. It is not optional.

---

## §6 THE ONE AUTHORIZED TEST EDIT

`tests/.../test_host_suspend_recorded` currently injects `_wall_clock` as a `_JumpClock(120s)`
against a real monotonic and patches the transport at module level. Under the new gate that is
(i) a non-default clock with a default `_connect_fn` and (ii) an unnamed incoherent pair — it
will refuse.

Migrate THIS TEST ONLY:
- construct its transport through `_connect_fn` instead of module-level patching;
- pass `incoherent_clocks_allowed="suspend-detector-test"` explicitly;
- docstring states that it is the SOLE enumerated incoherent customer and why (it tests the
  wall-vs-monotonic divergence detector, so coherence would destroy the thing under test).

This is the only test this WO edits. If migrating it requires anything beyond injection through
the two new seams, **STOP and report** — that is a finding about the seams' completeness.

---

## §7 HOT-PATH RE-BASELINE (standing rule)

Line 2434 is the loop's per-iteration condition; `time.time()` → `self._monotonic_clock()` is a
hot-path touch by the standing rule's letter. The entry is REQUIRED, not skipped as
obviously-nothing. Record the PREDICTION FIRST (Ops predicts: BELOW FLOOR / UNDETECTABLE against
the ~10 ms/frame detection floor), then the measurement, then whether it confirmed or surprised.
An honest "below floor" ledger entry is the correct record (D31).

---

## §8 DECISION LOG — THREE ENTRIES

`docs/decisions/2026-07-23-*.md`:
1. **`a-guard-can-audit-the-object-model.md`** — the invariant was implementable only by making
   it true. Beyond refusing bad states and preserving good ones, a well-specified guard can audit
   the object model: "compare your clock against your transport" exposed that the object could not
   name its own transport. Side benefit recorded: transport injection retires transport
   monkeypatching — the 0.1a direction of travel.
2. **`a-ruling-about-a-seam-must-be-written-against-its-consumers.md`** — Ruling D33-1 named
   "the injectable clock" and would have put the most safety-critical interval in the system on
   the one clock that can jump. The source at line 1136 already said "NOT used for the deadline."
   Same family as the `Mock()` and the bare `import-linter` step: the file said the true thing and
   nobody read it. A seam is defined by its current consumers, not by its name.
3. **`the-exception-must-be-requested-by-name.md`** — inference is vigilance; the enumerated
   exception is declared per-invocation and greppable, and carries its own refusal/preservation
   dual.

---

## §9 ACCEPTANCE — ALL MUST HOLD BEFORE COMMIT

- `pytest tests/ -p no:randomly -rX` → **215 passed**, 0 failed / 0 xfailed / 0 xpassed
- `pytest tests/ --randomly-seed=20260723 -rX` → same
- BOTH interpreters (3.11 strict, 3.14 dev)
- `lint-imports` → 6 kept / 0 broken
- `python tools/contract_count_check.py` → 6/6
- `ruff check .` → clean
- `python tools/annotation_name_scan.py` → 0
- `python tools/preflight_path_check.py` → pass

Note: the test COUNT stays 215 (§5 adds a test, §6 edits one — reconcile the arithmetic in the
report and state the new number explicitly rather than asserting "unchanged").

Commit, push, confirm local == remote, confirm CI green on BOTH legs via `gh run view`. Update
`progress.md` (append a WO-023 §2 block; do not rewrite existing content).

**THEN STOP.** Report and wait. Do not start the 30-test conversion.

---

## §10 REPORT

Write `WO-023-FOUNDATION-REPORT.md`. Must contain: every `_connect_fn` call site changed; the
binding decision from Checkpoint B and its justification; Checkpoint A and B suite results;
the three-assertion bite proof with all four artifacts and sha256 lines; the vocabulary proof for
`CLOCK_INJECTION_REFUSED`; the re-baseline prediction-then-measurement; the test-count arithmetic;
the full §9 gate output pasted verbatim; and any point at which you STOPPED.