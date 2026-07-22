# WO-018 — FINAL REPORT: Event-Type Governance + Closing the raised⇒declared Escape Hatch

**Baseline:** `cb6bd55` → §1 seam `1933d9d` → this commit. **NO VENUE CONNECTION.** Principle VIII the
substantive authority. **Governance, not redesign** — no namespace merged, renamed, or restructured.

---

### 1. The denominator (§1) — both namespaces, every literal form, how found
`evidence/WO-018/namespace_enumeration.txt` (committed at the seam). Seven literal forms exist:
(1) `"CODE:"` colon, (2) `reason_code="CODE"`, (3) `event_type="CODE"`, (4) `=<var>/<attr>`,
(5) `CONST="CODE"`, (6) enum member, (7) `f"{CONST}:"`. The prior scan saw only (1).
- **reason_code:** 30 declared; **12 EMITTED-BUT-UNDECLARED** (bigger than the WO's headline 2) —
  `DATA_RECEIVED`, `EXEC_ORDER_FILLED`, 5×`FEED_*`, 5×`RISK_*` — all in the `reason_code=` keyword blind
  spot. Found by multi-pattern grep + semantic resolution of variables/constants/enum.
- **event_type:** 0 declared (entirely ungoverned); 13 emitted, with a lowercase-feed/UPPERCASE-loop
  casing split.
- **Form the literal scan cannot see (reported):** variable indirection (`reason_code=<var>` for the
  `RISK_*` constants, `signal_reason`, `e.reason_code`; `event_type=decision.value`). Handled by
  declaring the resolved values (verified in the denominator) + the enum drift guard.

### 2. reason_code hatch closed (§2)
Scan extended to the non-colon keyword form (`_RC_KWARG`). All 12 emitted-undeclared reason codes
**DECLARED, not retired** — they are the canonical strings in use across 5 modules; declaring closes
the hatch without a rename (WO-013 retired only where a declared code already existed and the emission
was the stray — not the case here). `EXEC_ORDER_FILLED` (the fill event, the decisive weight) declared
in EXECUTION alongside the `EXEC_` convention; whether it and the event_type-only `ORDER_FILLED` should
be one code is a §6 taxonomy finding, not a rename made here. `raised ⇒ declared` now holds in **both**
literal forms.

### 3. event_type vocabulary declared (§3)
`VALID_EVENT_TYPES` added to `decision.py`, structured as `VALID_REASON_CODES` (FEED / LOOP / RISK).
Every free event_type reconciled — declared as emitted (casing preserved; normalising is a §6 ruling).
**Enum sync:** the RISK event_types must equal `RiskDecision.value`; `decision.py` (logkit) must not
import `trading.risk` (layering/cycle), so the sync is enforced **mechanically** by
`test_event_type_risk_values_match_enum` (the test may import both) — a hand-restated enum would be a
second source of truth; drift fails the test, not silently.

### 4. Four properties across both namespaces (§4) — pasted
`tests/test_reason_code_vocabulary.py` (11 tests, all green):
1. **raised/emitted ⇒ declared** — `test_every_emitted_reason_code_is_declared` (colon + keyword),
   `test_every_emitted_event_type_is_declared`.
2. **declared ⇒ producible** — `test_every_declared_reason_code_is_producible`,
   `test_every_declared_event_type_is_producible` (excluding `decision.py`).
3. **prefix-freedom across the UNION** — `test_declared_union_is_prefix_free`,
   `test_emitted_union_is_prefix_free` (+ detector self-test).
4. **scan reads EMITTED strings** — `_emitted_reason_codes`/`_emitted_event_types` read source, never
   the declared lists.

### 5. Four bite proofs on the scan (§5) — four artifacts each, sha256
`evidence/WO-018/scan_bite_proofs.txt`, **ALL FOUR OK**:
| proof | injected | scan fails naming | 
|---|---|---|
| emitted-but-undeclared **event_type** | `event_type="BITEPROOF_EVENT_XYZZY"` | ✓ names it |
| emitted-but-undeclared **reason_code (non-colon)** | `reason_code="BITEPROOF_RC_XYZZY"` | ✓ names it |
| **declared-but-unproducible** | `"BITEPROOF_UNPRODUCIBLE_XYZZY"` in VALID_REASON_CODES | ✓ names it |
| **cross-namespace prefix collision** | event_type `"CHECKSUM"` vs reason_code `CHECKSUM_*` | ✓ names both |

Each: A1 PASS → A2 REAL-FAIL (named) → A3 PASS → A4 sha256 byte-identical restore. The last is the
mechanism by which WO-013's defect hid.

### 6. Overlap finding (§6) — REPORT ONLY; acted on nothing
`evidence/WO-018/overlap_finding.txt`. Values in **both** namespaces: `NO_SIGNAL` (identical string,
same line — pure redundancy), `PASS`/`CLAMP`/`VETO` (declared reason_code but emitted only as
event_type), `ORDER_FILLED`/`ORDER_REJECTED`. Inferable (unstated) rule: **event_type = line KIND,
reason_code = specific CAUSE** — it holds where they differ (ORDER_REJECTED + RISK_VETO_KILL_SWITCH) and
blurs where they don't (NO_SIGNAL; ORDER_FILLED/EXEC_ORDER_FILLED; bare PASS/CLAMP/VETO as reason codes).
Casing split reported too. Taxonomy directions listed for the lead. **I confirm I acted on none of it.**
Dead constant `RISK_VETO_INSUFFICIENT_BALANCE` (defined, never returned) reported and left as-is.

### 7. Hot-path judgment (§7)
**NOT hot path — no re-baseline.** This WO changed only `decision.py` (declarations) and the test-side
scan. **Zero emission code on the per-frame path** was touched — no `live.py`/risk/adapter emission
renamed or retired; the loop emits exactly the same strings, now declared. "When in doubt re-baseline"
is argued OUT of here explicitly: there is no new per-frame work to measure.

### 8. Decision-log entry (§8)
`docs/decisions/2026-07-22-a-check-is-bounded-by-the-form-it-matches.md` — the §8 text verbatim: *"A
CHECK IS BOUNDED BY THE FORM IT MATCHES AND THE NAMESPACE IT READS."*

### 9. Verification (`evidence/WO-018/verify.txt`)
- Deterministic (`-p no:randomly`): **215 passed** (245.80 s); randomized `--randomly-seed=20260730`:
  **215 passed** (245.62 s); 0 failed / xfailed / xpassed both orders.
- **Delta vs 212 baseline (+3):** `tests/test_reason_code_vocabulary.py` rewritten from 8 → 11 tests
  (2 raised⇒declared, 2 declared⇒producible, 3 prefix-union, 1 enum drift guard, 3 scan self-tests);
  no other test count change. `lint-imports` **6/6**; contract **6/6**; `ruff` clean.
- **New codes declared same commit:** 12 reason codes + the `VALID_EVENT_TYPES` vocabulary (13 event
  types). **Secret scan:** 0 hits. **local HEAD == remote HEAD:** see §push.

### 10. Venue connection? **NO.** HTTPS doc fetch? **NO.**
### 11. Prose standing in for output? **NO** — enumeration, four properties, and four bite proofs are all executed artifacts.
### 12. Changed but not asked? — every file
- **Production:** `src/trading/logkit/decision.py` (12 reason-code declarations + `VALID_EVENT_TYPES`).
- **Tests:** `tests/test_reason_code_vocabulary.py` (rewritten for both namespaces + the four properties).
- **Tools:** `tools/vocabulary_scan_bite_proof.py` (new, §5 harness).
- **Docs/evidence:** `evidence/WO-018/namespace_enumeration.txt` (seam), `overlap_finding.txt`,
  `scan_bite_proofs.txt`, `verify.txt`, the decision log, this report. `instructions.md` carries the
  lead's WO text (uncommitted, never by me).
### 13. What could not be completed, and why? — **Nothing in WO-018.** All of §1–§9 executed. The overlap
taxonomy (§6) is a reported finding awaiting a ruling; not a gap in this WO.

---
**STOP for review.** Do NOT proceed to CI work or the corpus. Next by sequence (post-ruling on §6 if
the lead chooses): CI capture + version ruling → CI green → 008c → the 24-h corpus.
