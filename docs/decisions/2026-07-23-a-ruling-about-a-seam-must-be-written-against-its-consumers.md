# Decision Log: a ruling about a seam must be written against its consumers (WO-023 §2)

**Date:** 2026-07-23
**WO:** WO-023 §2 (FOUNDATION) — routing the capture deadline onto the injectable clock
**Authority:** D25 (monotonic orders, wall locates — intervals go on monotonic); rule 0.1 (the code
wins; STOP and report on disagreement)
**Related:** [[a-guard-can-audit-the-object-model]], [[the-exception-must-be-requested-by-name]],
[[a-check-is-bounded-by-the-form-it-matches]], the `Mock()`-shadowing finding (WO-008b-A1), the bare
`import-linter` step (WO-020)

---

## The entry

> "Ruling D33-1 named 'the injectable clock' and, taken literally, would have routed the most
> safety-critical interval in the system — the capture deadline — onto `_wall_clock`, the ONE clock
> that can jump. The source at line 1136 already said, in the field's own comment, *'NOT used for
> the deadline.'* The suspend detector injects `_wall_clock` as a clock that JUMPS 120s; a deadline
> on that clock would end the run before the suspend it exists to detect. And a duration is an
> INTERVAL, so D25 puts it on monotonic regardless. The ruling named the seam by its type ('a
> clock') when the seam is DEFINED BY ITS CURRENT CONSUMERS: `_wall_clock` already had a consumer
> (the suspend sampler) whose whole purpose is to make that clock diverge. A ruling written against
> the seam's NAME instead of against who already uses it will pick the wrong seam.
>
> This is the same family as the `Mock()` that shadowed `_log_error` and the bare `import-linter`
> step that checked nothing: in each, THE FILE SAID THE TRUE THING AND NOBODY READ IT — the comment
> said 'not the deadline,' the method said it logged, the step said it linted. Rule 0.1 (the code
> wins) is the operational answer: when the order and the code disagree, read the consumers first."

---

**What was done.** The deadline was routed onto a NEW `_monotonic_clock` seam (default
`time.monotonic`), not `_wall_clock`. The suspend test keeps injecting only `_wall_clock` (fake wall
against real monotonic — the enumerated incoherent exception), so the deadline stays on monotonic and
the 120s wall jump never touches it.

**The §1 corollary — the enumeration was written against the name, too (found at Checkpoint A).** The
order said "route BOTH deadline lines" and named two (`deadline = …`, `while … < deadline`). The CODE
had a THIRD deadline consumer — `remaining = deadline - time.time()`, which bounds the recv timeout.
Routing only the two named lines left that third site subtracting wall-clock `time.time()` from a
now-monotonic `deadline` (monotonic minus epoch → a huge negative `remaining` → immediate break →
zero frames). "The deadline" is defined by everything that READS `deadline`, not by a count in the
order. Checkpoint A caught it exactly as written ("if not 215, that is a finding"); the third site
was routed as the forced completion of D34-1, and reported rather than reconciled silently.
