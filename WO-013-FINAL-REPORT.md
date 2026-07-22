# WO-013 — FINAL REPORT: Reason-Code Emission + Vocabulary Enforcement

**Baseline:** `36a3f9a`. **NO VENUE CONNECTION** — simulated transport only. Standing rules 0.1–0.9
observed (0.1h: production emission path exercised; 0.1i: proofs terminate in the decision-log line;
0.4: no contract weakened). **Result:** the three declared-but-unproducible codes are wired and
behaviorally proved; `declared ⇒ producible` is fully enforced; 210 passed both orders.

---

### 1. §0 diagnosis — per code; NO_SIGNAL reconciled; PASS/CLAMP/VETO producible?
`evidence/WO-013/emission_diagnosis.txt`. All three were **WIRED BUT UNDER A DIFFERENT NAME** (not
unwired, not merely untriggered): the emission call existed but emitted an *undeclared* string, so
the declared code appeared nowhere.
- **KILL_SWITCH_ENGAGED:** the loop caught `KillSwitchEngagedError` and logged `e.reason_code`, but
  the exception defaulted to the undeclared `EXEC_BLOCKED_KILL_SWITCH`. (Secondary finding: in the
  integrated loop the except branch is unreachable — the risk engine vetoes first with
  `RISK_VETO_KILL_SWITCH`; the proof isolates the execution-layer block, defense-in-depth.)
- **LONG_SIGNAL / SHORT_SIGNAL:** the loop emitted `STRAT_SIGNAL_BUY` / `STRAT_SIGNAL_SELL` (undeclared);
  in the capture the strategy also never triggered a signal (0 of 111,010).
- **NO_SIGNAL vs STRAT_NO_SIGNAL — RECONCILED.** The loop emitted the undeclared `STRAT_NO_SIGNAL`;
  `NO_SIGNAL` read "producible" only because `event_type="NO_SIGNAL"` is a literal. Reconciled by
  emitting the declared `NO_SIGNAL` as the reason_code; `STRAT_NO_SIGNAL` retired. The STRATEGY
  reason-code vocabulary now equals its declared set {NO_SIGNAL, LONG_SIGNAL, SHORT_SIGNAL}.
- **PASS / CLAMP / VETO — CONFIRMED producible; NOT declared-only; scope unchanged.** The risk engine
  emits distinct `RISK_PASS` / `RISK_CLAMP_MAX_POSITION` / `RISK_VETO_*` codes (Principle VI
  satisfied), and PASS/CLAMP/VETO are recorded as the decision-log line's `event_type` (RiskDecision
  enum values). They are producible AND recorded under their own name — they do not join scope.

### 2. Three behavioral proofs — four artifacts each, sha256; decision-log + production path
`tests/integration/test_reason_code_emission.py`; bite proofs in `evidence/WO-013/emission_bite_proofs.txt`.
Each asserts the code **IS IN THE DECISION LOG** (the JSON-lines file the production `DecisionLogger`
writes) after driving `LiveTradingLoop.run` — a test strategy / risk double supplies the trigger only;
the emission is the loop's own `log_decision` call.

| Proof | A1 PASS | A2 REAL-FAIL (weakened to old undeclared string) | A3 PASS | A4 sha256-exact |
|---|---|---|---|---|
| LONG_SIGNAL in the decision log | ✓ | ✓ (→ `STRAT_SIGNAL_BUY`) | ✓ | ✓ |
| SHORT_SIGNAL in the decision log | ✓ | ✓ (→ `STRAT_SIGNAL_SELL`) | ✓ | ✓ |
| KILL_SWITCH_ENGAGED in the decision log | ✓ | ✓ (→ `EXEC_BLOCKED_KILL_SWITCH`) | ✓ | ✓ |

**ALL THREE PROOFS: OK.**

### 3. Kill-switch preservation dual (S13) — same test
`test_kill_switch_engaged_emitted_and_cancellation_preserved`: with the switch engaged, `place_order`
is blocked and logged as `ORDER_REJECTED` / `KILL_SWITCH_ENGAGED` (never `EXEC_ORDER_FILLED`), **and
`cancel_order` still succeeds** and removes the resting order. The emission does not break cancellation;
a cancellation is not logged as a blocked order.

### 4. Vocabulary check fully enforced — exemption removed, four properties intact, bite-proved
`tests/test_reason_code_vocabulary.py`: `_KNOWN_UNPRODUCIBLE` emptied; `declared ⇒ producible` is
unconditional. The four properties are kept (raised ⇒ declared; declared ⇒ producible excluding the
declaration site; prefix-freedom across the union; the scan reads raised strings). Enforcement bite
proof `evidence/WO-013/enforcement_bite_proof.txt`: inject a declared-but-unproducible code → the
check REAL-FAILS naming it → remove → PASS → sha256 exact restore. Four artifacts, OK. T018 closed.

### 5. Boundaries (§3) — contract count before/after
**6/6 before → 6/6 after, unchanged.** `lint-imports`: 6 kept, 0 broken. No contract was pressured:
the emission changes are string constants in `live.py` (loop) and the exception default in
`interface.py` (execution) — no new imports into `risk/` or `strategy/`, no venue/ML edges. Nothing
was weakened to emit (rule 0.4).

### 6. RE-BASELINE (§4) — hot path, standing rule APPLIED
`evidence/WO-013/rebaseline.txt`. Establishment replay (pinned source, ~1959/min, 60 s) run ×3:
109.305 / 108.910 / 108.721 ms. **The loop IS hot path, but WO-013 added NO per-frame work:** the
establishment tool measures the *adapter* `process_raw_frame` cycle (byte-identical to WO-017 — WO-013
touches only `live.py`/`interface.py`), and the loop change RENAMED an already-existing per-frame
emission (`STRAT_NO_SIGNAL` → `NO_SIGNAL`, byte-identical call) while the signal/kill-switch codes fire
only on their rare triggering events. The measured 108.7–109.3 ms differs from 107.923 ms by
**cross-session environmental noise, not this change** — attributing it to reason-code emission would
be false attribution. **Baseline HOLDS at 107.923 ms; NOT re-declared** (nothing superseded it, the
measured path is unchanged); the store's `assessments` entry records the evaluation. **Material? No —
no per-frame cost was added.** (Minor finding reported: the establishment tool's printed comparison
constant `0.108886` is stale vs the store's `0.107923`; display-only, flagged for a future hygiene pass.)

### 7. Decision-log entry
`docs/decisions/2026-07-22-declared-implies-producible-no-exemptions.md` — the §5 text verbatim plus
the recurring event_type-vs-reason_code shape and the cost note.

### 8. Verification (`evidence/WO-013/verify.txt`)
- Deterministic (`-p no:randomly`): **210 passed**, 246.34s, 0 failed / 0 xfailed / 0 xpassed.
- Randomized (`--randomly-seed=20260726`): **210 passed**, 246.17s, same.
- **Delta vs 207 baseline (+3), explained:** all three in `test_reason_code_emission.py` (the §1
  behavioral proofs). No other test count change (the vocabulary tests were tightened in place; the
  bite-proof harnesses are tools, not collected tests).
- `lint-imports` **6/6**; contract **6/6**; `ruff` clean. **No new reason code** (the three codes were
  already declared; `decision.py` is unchanged — the exemption lived in the test).
- **Secret scan:** 0 hits. **local HEAD == remote HEAD:** see §push.

### 9. Venue connection? **NO.** HTTPS doc fetch? **NO.**

### 10. Prose standing in for output? **NO** — 210 both orders captured; behavioral + enforcement bite
proofs are four artifacts each with sha256 in `evidence/WO-013/`; the re-baseline is three captured runs.

### 11. Changed but not asked? — every file
- **Production:** `src/trading/execution/interface.py` (KillSwitchEngagedError default → declared code),
  `src/trading/loop/live.py` (emit NO_SIGNAL / LONG_SIGNAL / SHORT_SIGNAL). `decision.py` **unchanged**.
- **Tests:** `tests/integration/test_reason_code_emission.py` (new, §1 proofs),
  `tests/test_reason_code_vocabulary.py` (exemption removed, §2).
- **Tools:** `tools/emission_bite_proof.py`, `tools/vocabulary_enforcement_bite_proof.py` (new harnesses).
- **Config/docs/evidence:** `config/mean_cycle_baselines.json` (§4 assessment — figure unchanged),
  the decision log, `evidence/WO-013/*`, this report.
- **Retired (not added):** the undeclared strings `STRAT_NO_SIGNAL`, `STRAT_SIGNAL_BUY/SELL`,
  `EXEC_BLOCKED_KILL_SWITCH`. **Deliberate NON-changes (reported, out of scope):** `DATA_RECEIVED` and
  `EXEC_ORDER_FILLED` remain emitted-but-undeclared (invisible to the colon-form raised scan); the
  establishment tool's stale `0.108886` comparison constant. `instructions.md` carries the lead's WO
  text (uncommitted, never by me).

### 12. What could not be completed, and why? — **Nothing in WO-013.** All of §0–§6 executed. Still
open by ruling (separate WOs): CI capture + version ruling → CI green → 008c → the 24-hour corpus.

---
**STOP for review.** Did NOT proceed to CI work or the corpus.
