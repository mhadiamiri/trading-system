# Decision Log: incidental coverage is not coverage (WO-024 Pass One)

**Date:** 2026-07-24
**WO:** WO-024 Pass One — transport migration (ruled by D34/D35)
**Authority:** the S13 family (preservation duals); D37; the coverage-topology corollary ratified here
**Related:** [[a-guard-can-audit-the-object-model]],
[[a-ruling-about-a-seam-must-be-written-against-its-consumers]],
[[the-exception-must-be-requested-by-name]], WO-023 §2c

---

## The entry (ratified verbatim)

> A guard branch can be pinned only incidentally by a neighbouring branch — incidental coverage is
> coverage until the neighbour changes, and then it is nothing, silently.

**Specimen.** WO-023 §2c Mutation D (deleting the gate's early return) was caught by six unrelated
tests through the COHERENCE branch and by zero tests through COUPLING; the coupling branch's
preservation of the production path was pinned only by its neighbour. A no-clock production run with
the early return deleted fell through to coherence, which refused it — so the six live-capture tests
failed, but for a reason one branch over from the property that actually mattered (that the coupling
branch PERMITS a real-transport, no-clock run). Had the coherence branch been changed at the same
time, nothing would have caught the coupling regression, silently.

**Standing consequence**, joining the S13 family as its coverage-topology corollary:

> **A branch's preservation dual must be LOCAL and DIRECT** — it must exercise the branch's own
> permit-path and assert on that branch's behaviour, never relying on a neighbouring branch to fail
> first. Incidental coverage reads as coverage on a green suite and evaporates the moment the
> neighbour moves.

---

**What was done under this doctrine.** WO-023 §2c added Assertion 5 (real transport + no clock →
PROCEEDS) directly to the gate's own test — the coupling branch's local, direct preservation dual —
and Mutation D confirmed that only that assertion, not the six neighbours, discriminates the
early-return precondition. WO-024 Pass One's gate ledger (§3) is the same principle at the suite
level: it MEASURES the gate's behaviour directly (every invocation's outcome recorded) rather than
inferring "the gate never fired" from a green suite, so a future clock injection that trips the gate
is caught locally by the ledger assertion, not incidentally by whichever test happens to fail.
