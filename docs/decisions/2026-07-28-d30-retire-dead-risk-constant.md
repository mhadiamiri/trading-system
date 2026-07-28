# Decision Log: D30's fork applied — retire REASON_VETO_INSUFFICIENT_BALANCE as aspirational

**Date:** 2026-07-28
**WO:** WO-038 §2
**Authority:** D43 — delete the dead constant

---

## The entry

`REASON_VETO_INSUFFICIENT_BALANCE` is retired as **aspirational**. No balance check exists in the current system; paper venue models do not carry balances. The constant was dead code — defined exactly once at `risk/engine.py:42`, never referenced, never wired into the production path.

## When it returns

Returns in Sprint 3 through the **front door** — declared, produced, and proven in the WO that implements the balance check. The guard `test_every_wired_risk_reason_constant_is_declared` still governs the CLASS and will fail the moment a constant is wired without declaration.

## What was deleted

- `risk/engine.py:42`: `REASON_VETO_INSUFFICIENT_BALANCE = "RISK_VETO_INSUFFICIENT_BALANCE"`
- `tests/test_archive_readiness.py`: removed from `KNOWN_DEAD_RISK_CONSTANTS` (now empty)

Both guards remain green — the deletion is clean.
