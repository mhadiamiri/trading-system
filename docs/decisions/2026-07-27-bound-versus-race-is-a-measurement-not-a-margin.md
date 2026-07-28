# Decision Log: bound-versus-race is a measurement, not a margin (D40 ruling 2)

**Date:** 2026-07-27
**WO:** raised by WO-031 §3-bis; ratified as **D40**; executed and committed by WO-033
**Authority:** D40 (this ruling); D39 (the classification method); the prose-figure family
**Related:** [[a-residual-clock-read-is-classified-not-waived]],
[[a-conversion-preserves-the-path-not-just-the-assertions]],
[[incidental-coverage-is-not-coverage]], [[instrument-competence]],
[[a-check-is-bounded-by-the-form-it-matches]],
[[an-enumeration-is-only-as-good-as-its-identifiers]],
[[a-doctrine-needs-a-guard-that-reaches-every-producer]]

---

## The entry (ratified verbatim)

> **Bound-versus-race is a measurement, not a margin argument; a bound classified by prose ratio is a
> race pending measurement.**

And the sentence that produced it:

> **What differs is the ratio, not the rhetoric.**

---

## Specimen

The WO-023 §1 audit split 37 wall-clock-gated tests into **30 STRUCTURAL RACES** and **7 legitimate
BOUNDS**. The bounds were justified in prose, one line each — *"dur=30, breaker trips ~0.1s"*,
*"dur=0.25, injected crash ends it"*, *"refuses before any loop"* — under a shared rationale: *"In each
the deadline is a BACKSTOP against a hang; the passing path terminates via the script, not the clock."*

**One of the seven was wrong.** WO-032's CI leg failed on
`test_incremental_persist_survives_unhandled_exception_mid_capture` — audit entry 35, filed as a bound
with *"dur=0.25, injected crash ends it"*. WO-031 §3-bis measured it: the crash ends the run only if the
loop drains three frames before a 0.25 s deadline. At `AdvancingClock(delta=0.05)` the gap opens and
the crash never arrives. It was a race the whole time, and the prose said otherwise with total
confidence.

The exposure was not luck in the ordinary sense. It took a CI run in a randomized order on a loaded
runner — that is, it took the *real clock* disagreeing with the prose — and even then the first
instinct was to call it a flake.

## Why the reasoning failed

Every one of those seven justifications has the same form: **X ends it, so the deadline never matters.**
That is only true if X *wins a race* against the deadline. The prose states the conclusion and omits
the race, so the sentence reads like a structural fact when it is an empirical claim with an unstated
margin. A reader — including the audit's own author — cannot tell from the text whether the margin is
18,750× or 1.1×.

This is the **seventh** specimen in the prose-figure family, and the **first found in an audit's own
taxonomy rather than in what the audit examined**. The earlier six were defects the audit or a guard
was pointed at. This one is in the instrument's *classification scheme* — the part nobody re-checks,
because it is the thing doing the checking.

**Note the recursion, which is the entry's real content:** the audit that defined pass two, and whose
30-race enumeration every batch is scheduled against, is now held to pass two's own evidentiary
standard. An enumeration that demands measurement of everything it lists must itself be measured. It
was not, for four work orders.

## Standing consequence

1. **A bound is a measured category.** Filing a test as "terminates via the script, not the clock"
   requires a measurement: either the margin between terminator and deadline, or an observation that
   the deadline is never consulted.
2. **Two designs, by claim-kind** — the distinction is honored in the measurement, never used to
   exempt a claim from being measured:
   - *structural* ("terminates before the deadline is consulted") → a **zero-consultation probe**:
     instrument the deadline read via the injectable seam and show the count is zero;
   - *ratio* ("30 s deadline vs a 0.1 s trip") → a **margin probe**: measure the actual elapsed time
     to the terminator and state the number.
3. **A prose ratio in an audit is a to-do, not a finding.** Where one already exists, it is a race
   pending measurement.

## What was measured under this ruling (WO-033)

All six surviving bounds. **None flipped** — the audit's verdicts survive. But the pass was not
ceremonial: the measured margins are **199× · 220× · 43× · 18,750×**, against a prose figure of
"~300×" applied uniformly. Entry 33 is nearly an order of magnitude tighter than claimed, and the four
span a factor of 436 between them. The verdicts were right; the numbers behind them were never taken.

`tools/wo033_bound_measurement.py` is the instrument, and it generalises: a future bound claim gets
measured by swapping the script and duration, rather than argued.
