# Decision Log: a conversion preserves the path, not just the assertions (WO-029 §6 item 1 / D39)

**Date:** 2026-07-27
**WO:** WO-029 batch A raised it; ratified as **D39 item 1**; committed as a doc by WO-032 §3.1
**Authority:** D39 (this ruling); the incidental-coverage family (r19); D24 (built-vs-operated)
**Related:** [[incidental-coverage-is-not-coverage]],
[[a-residual-clock-read-is-classified-not-waived]],
[[an-enumeration-is-only-as-good-as-its-identifiers]],
[[a-doctrine-needs-a-guard-that-reaches-every-producer]]

---

## The entry (ratified verbatim)

> A test's assertions do not fully specify which production path it covers. A conversion that keeps
> every assertion passing while changing the path the test takes is a coverage loss that no assertion
> can report.

**The tightened acceptance criterion D39 added, verbatim:**

> A conversion's acceptance includes **which production branches the test exercises before and after,
> asserted not assumed.**

---

## Specimen

WO-029's committed partition (`evidence/WO-029/batch_partition.md`, written at `d0450fa`) planned
batch A's races 1–3 as *"inject `FakeClock` at construction, terminate via scripted clean-close."*
That plan works, in the only sense a green suite can measure: every assertion in races 1–3 passes
under a frozen clock, because none of them asserts *how* the run ended.

It would also have moved three tests off the **deadline** branch of `get_live_market_data` and onto
the `ConnectionClosedOK` branch. Races 1–3 are the end-to-end wiring proofs for a capture that, in
production, ends at minute 60 by deadline. Converting them to exercise the venue-close path instead
would have left the deadline branch's end-to-end coverage resting on race 4 alone — while every gate
stayed green and no assertion ever complained. Race 3 is named
`test_short_bounded_run_completes_with_readable_artifacts`; **the bound is its subject.**

The conversion actually performed used the self-advancing `AdvancingClock` so that all five races
still terminate at the deadline. Cost of avoiding the loss: near zero, because §2.0-bis had already
built the fixture that makes a deadline fire.

---

## Why this is the conversions-layer arrival of the incidental-coverage family

[[incidental-coverage-is-not-coverage]] (r19) ruled that a branch pinned only by a neighbouring
branch is covered until the neighbour moves, and then is covered by nothing, silently. That entry is
about coverage that was never *deliberately* placed.

This entry is the same failure one level out, and it is worse in one respect: here the coverage
**was** deliberate, and a mechanical, well-intentioned refactor trades it away. The assertions are the
part of a test that is written down; the path is the part that is merely *taken*. Convert with only
the written-down part in view and the rest evaporates without a diff, without a failure, and without
a line in any report.

> **Incidental path coverage is still coverage, and silently trading it away is the cheap
> conversion's failure mode.**

---

## Standing consequence

1. **A conversion must keep the race on its own production termination branch** — deadline,
   venue-close, failure-cap, breaker-trip — and must not substitute a scripted clean-close for it.
2. **The branch is part of acceptance, asserted not assumed.** A conversion report states which
   branch the test exercised before and which after, and the "after" is demonstrated, not asserted in
   prose.
3. If keeping the branch needs a fixture that does not exist (as race 4 needed a clock that
   *advances* rather than one that is merely frozen), that is a **harness build to be flagged and
   built** — not a licence to reframe what the test observes. Reframing what a test observes is a §2
   STOP.

**Applied where:** `evidence/WO-029/batch_partition.md` was amended by WO-032 §2 — batch A's entry now
records the deadline conversion that actually happened, and batches B and C carry requirement 1 and 2
explicitly, so the thirteen and eight races still to convert face the choice with the ruling in hand
rather than rediscovering it.
