# Decision Log: an environment is not strict or lax — it is strict along axes (WO-022)

**Date:** 2026-07-23
**WO:** WO-022 — Baseline-Test Injection + Gap-Ordering Assertion + Two Declared Records
**Authority:** Principle VIII (observability); the scope-dimension doctrine (host / interpreter / instrument)
**Related:** [[interpreter-is-a-scope-dimension]], [[instrument-competence]], the WO-019→WO-021 CI arc,
standing rules 0.1b / 0.1h / 0.1j / 0.1k

---

## The detector symmetry and its corollary

> "Linux/3.11 is the strict instrument for annotation names; the Windows dev host is the strict
> instrument for clock ties. NEITHER HOST DOMINATES — an environment is strict along PARTICULAR AXES,
> and coverage comes from the SET of environments, never from picking the strictest one. The CI arc's
> original lesson implicitly framed CI as the second, stricter opinion; the truth is that the dev host
> was ALSO a detector all along — its coarse tick caught what Linux's finer clock masks — and we saw
> that only once both environments ran the same suite. This completes the scope-dimension doctrine:
> an environment is not strict or lax, it is strict along axes.
>
> STANDING COROLLARY: WHEN A TEST FAILS ON EXACTLY ONE ENVIRONMENT, THE FIRST QUESTION IS NOT 'WHICH
> ENVIRONMENT IS WRONG' BUT 'WHICH AXIS IS THIS ENVIRONMENT STRICT ON.' A single-host failure is a
> DETECTOR REPORT until diagnosed otherwise. The gap-ordering test demonstrated the full lifecycle:
> Windows-only failure → diagnosis → real invariant question → consumer enumeration → correct fix.
> Treating it as flaky would have discarded all of it."

---

**What was done (WO-022, tests only — no production behavior changed).** Eight host-scoped baseline
tests now INJECT a synthetic baseline (structural DI via `MEAN_CYCLE_BASELINE_STORE`) instead of relying
on the dev machine's ambient `config/mean_cycle_baselines.json`; the injected record is unmistakably a
fixture (labeled fingerprint, sentinel numbers — `tests/integration/conftest.py`). The runner's refusal
on a host with NO baseline stays bite-proved (`test_runner_refuses_host_with_no_baseline`), so the
corpus-protecting property is intact. The gap-ordering assertion moved `<` → `<=`, with identity carried
by the already-distinct `gap_id` (a per-run open-sequence counter), because the consumer enumeration
found no consumer requires strict temporal separation. Both defects were invisible until the version
matrix ran the same suite on a second host — the concrete proof of the entry above.
