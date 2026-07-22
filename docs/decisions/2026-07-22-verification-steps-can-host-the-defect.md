# Decision Log: Any layer that reports verification can host the "green-while-checking-nothing" defect (WO-020)

**Date:** 2026-07-22
**WO:** WO-020 — CI Verification-Surface Repair
**Authority:** Principle IV / VII (import boundaries), Principle VIII (observability)
**Related:** [[instrument-competence]], the WO-010 malformed-config incident, the WO-008b-A `Mock()` incident,
the WO-019 CI diagnosis, standing rules 0.1d / 0.1k

---

## 5.1 — the third layer

> "GREEN-WHILE-CHECKING-NOTHING has now been found at three layers: the CODE (a malformed contract
> config evaluating zero contracts while appearing configured), the TEST DOUBLES (a `Mock()` silencing
> the alarm it was meant to raise), and THE PIPELINE THAT VERIFIES BOTH (a bare invocation exiting 0
> without running). The induction from three layers is uncomfortable and worth writing down: ANY LAYER
> THAT REPORTS VERIFICATION CAN HOST THIS DEFECT. That is why bite proofs now attach to verification
> steps themselves, not only to the behavior they verify."

## 5.2 — the demolished premise

> "'import-linter passes in CI, pytest fails' drove ten work orders of reasoning about real-import-time
> failure. The inference was VALID; the PREMISE was hollow — the step never ran — and the conclusion
> inherited the hollowness. Nothing downstream turned out to depend on it, because the local diagnosis
> stood on its own evidence. The lesson: AN INFERENCE FROM CI BEHAVIOR IS ONLY AS GOOD AS PROOF THAT
> THE CI STEP EXECUTED. This is the prove-the-instrument-ran doctrine extended to the pipeline's own
> steps."

---

**What was done (WO-020).** CI's `import-linter` step (bare, a no-op on import-linter 2.x — prints help,
exits 0) → `import-linter lint`, bite-proved with the old-form-exits-0 half pasted
(`evidence/WO-020/import_linter_step_bite_proof.txt`). `pytest-randomly` added to `requirements-dev.txt`
(it was in the dev env but absent from CI, so CI never randomized), and CI now runs BOTH orders with the
randomized run printing its seed. The D10 / WO-010 §2 preflight path assertion — flagged "not yet wired
into ci.yml" — was wired in as a standalone step BEFORE import-linter (`pytest_sessionstart` runs the same
assertion again at the pytest step, defense in depth).

**Damage bound (accuracy, not comfort).** The exposure was PROSPECTIVE: CI has been red overall throughout,
so no false green ever shipped, and the local gate (`lint-imports` 6/6 + the contract-count assertion,
both bite-proved, run at `pytest_sessionstart`) was the real enforcement all along. The repair matters
because the moment the pytest step is fixed, the pipeline would otherwise certify Principle IV/VII with a
command that prints help.

**Not confirmed here (honest bound on THIS entry).** That the repaired steps ACTUALLY RUN in CI — the
literal content of 5.2 — requires observing a real CI run. `gh` is unavailable in this environment and the
repo is private (no anonymous API), so that observation is deferred (WO-020 §4 blocker). The local bite
proof establishes the commands behave correctly; it does not by itself establish that CI executed them.
The entry's own doctrine therefore applies to its own closure: this is recorded as PENDING CI observation,
not asserted as done.
