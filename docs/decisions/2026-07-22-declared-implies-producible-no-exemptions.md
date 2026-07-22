# Decision Log: declared ⇒ producible, now with no exemptions (WO-013)

**Date:** 2026-07-22
**WO:** WO-013 — Reason-Code Emission + Vocabulary Enforcement
**Baseline:** `36a3f9a` → this WO
**Authority:** Principle VI (risk outcomes / kill switch), Principle VIII (observability)

---

> Three reason codes were declared and unproducible for the life of the project: the kill switch
> raised an exception without recording why, and the strategy returned a position without naming its
> signal. The vocabulary checker carried them as a known-set exemption — an audit that knew its own
> holes and let them stand. Wiring them rather than deleting them was the ruled direction, because
> deleting shrinks the specification to match the implementation, which is tuning to green wearing a
> dictionary. Principle VIII is not satisfied by a system that CAN be observed; it is satisfied by
> one that RECORDS what it did. Consequence: declared ⇒ producible now holds with no exemptions, and
> the T018 thread is closed rather than half-audited.

---

**What was wired.** `KillSwitchEngagedError`'s default `reason_code` is now the declared
`KILL_SWITCH_ENGAGED` (was the undeclared `EXEC_BLOCKED_KILL_SWITCH`); the loop emits `LONG_SIGNAL` /
`SHORT_SIGNAL` for a BUY / SELL (was `STRAT_SIGNAL_BUY` / `STRAT_SIGNAL_SELL`), and `NO_SIGNAL` for
no-signal (was `STRAT_NO_SIGNAL`). The STRATEGY reason-code vocabulary now equals its declared set
exactly. Each of the three previously-unproducible codes carries a behavioral proof that the code
lands IN THE DECISION LOG on its triggering event, driven through the production emission path
(`tests/integration/test_reason_code_emission.py`), with a four-artifact bite proof each.

**The shape that keeps recurring** (recorded so the next instance is diagnosed, not rediscovered):
the declared canonical codes were emitted as the decision-log line's *event_type* / enum value while
the *reason_code* was a namespaced string. The producibility checker counts any string literal, so a
canonical code present only as an event_type read as "producible" though nobody emitted it under that
name as a reason_code. `PASS`/`CLAMP`/`VETO` share the shape but are genuinely recorded (event_type +
distinct `RISK_*` reason codes satisfying Principle VI), so they stayed out of scope; `NO_SIGNAL` was
the masked fourth instance and was reconciled here.

**Enforcement.** The known-set exemption is removed; `declared ⇒ producible` is unconditional and
bite-proved (inject a declared-but-unproducible code → the check fails → remove → passes).

**Cost.** WO-013 added no per-frame work: the no-signal emission was a rename of a call already made
111,010× in the 60-minute capture; the signal and kill-switch codes fire only on their triggering
events. The mean-cycle baseline (107.923 ms, the adapter cycle WO-013 does not touch) holds — see the
store's `assessments` entry and [[baselines-attract-scope-errors]] for the ledger discipline.
