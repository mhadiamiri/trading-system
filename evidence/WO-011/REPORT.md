# WO-011 — Cost Model Unification + Reason-Code Vocabulary Completeness

**Status:** COMPLETE. Stopped for human review (did NOT proceed to WO-008b-B).
**Baseline:** `1ef7447` (119 passed + 8 xfailed; the "1 failing" was order-dependent — deterministic was green).
**Commit:** `452914f` — pushed, local == remote.
**Gates:** 139 passed deterministic AND randomized (seed 20260719); 0 failed / 0 xfailed / 0 xpassed; import-linter 6/6; contract 6/6; ruff clean; secret scan clean.

This work order took **three turns** because two enumeration gaps were disclosed and
ruled on before code was written (the discipline RULING 1 exists to produce):
1. Escalated the cost fork's blast radius beyond the one named test → RULING 1 froze
   the legalized set at 3 tests + the 8 xfails.
2. Disclosed a source-inspection test the approved design would break → ADDENDUM 2
   RULING 7 (behavioral replacement) + RULING 8 (audit the rest, report-only).

---

## Section 1 — Unification (one implementation, two callers)

Single model: **`src/trading/execution/costs.py::compute_execution_costs`**.
- `execution/paper.py:275` delegates to it.
- `backtest/costs.py:190` delegates to it.

The superseded second implementation is gone: mid-price notional (0), volume-scaled
slippage (0), additive total in `report.py` (0). Ruled model — executed price crosses
the spread (BUY ask / SELL bid), `total = fees + slippage`, spread is attribution.
No public signature changed → **no 0.1a event**. import-linter **6 kept / 0 broken**.

Rulings applied: **R3** paper venue gains the >5% abnormal-spread guard;
**R4** slippage unified onto the constant (volume-scaling preserved in
`docs/open-cleanup.md`); **R5** notional basis = executed price;
**R6** `report.py::add_trade` per-trade total corrected + `fill.py` docstring fixed.

Evidence: `cost_model_unification.txt`.

## Section 2 + RULING 1 — the frozen set of 3 corrected assertions

`test_cost_inclusive_pnl_report`, `test_observed_spread_used_in_cost_calculation`,
`test_cost_breakdown_validation` — each corrected from the superseded additive
assertion to the ruled model, each citing R6/D14, each stating the behavior already
implements the ruling (not tuned to green). Confirmed green in the randomized full run.

## Section 3 — 8 xfails flipped to hard passes

All 8 `TestCostModel` methods pass against the unified model; none could-not-pass.
Two asserted the superseded model and were corrected under the §2 framing
(`test_total_cost_equals_sum_of_components`, `test_manual_calculation_matches_system`).
Each has a four-artifact bite proof interacting with the LIVE mechanism.

Evidence: `xfail_to_bite_proofs.txt`.

## Section 4 — reconciliation to the cent

Both paths identical across executed price, fees, spread, slippage, total for BUY,
SELL, and a wide-spread edge case; identical `ABNORMAL_SPREAD_REJECT` at 20% spread.
Permanent regression test (`tests/integration/test_cost_reconciliation.py`),
bite-proofed by diverging the paper path only.

Evidence: `reconciliation_to_the_cent.txt`, `reconciliation_bite.txt`.

## Section 5 — reason-code vocabulary completeness

Declared the 3 raised-but-undeclared staleness codes. Extended the check to three
properties (raised⇒declared; declared⇒producible, scan EXCLUDES the declaration
site; prefix-freedom across the union). Each bite-proofed.

- Undeclared-but-raised remaining: **none**.
- **Declared-but-unproducible (reported, NOT deleted — needs a ruling):**
  `KILL_SWITCH_ENGAGED`, `LONG_SIGNAL`, `SHORT_SIGNAL`. The kill switch raises a
  class (`KillSwitchEngagedError`); the strategy returns a `DesiredPosition`. None
  emit their reason-code string. Documented as a known set that bites on any new one.

Evidence: `vocabulary_completeness.txt`.

## RULING 7 — behavioral no-synthetic-spread guard

`test_code_review_no_synthetic_spread` source grep replaced with a behavioral guard
(distinct observed spreads → distinct tracking spread cost; abnormal spread →
declared-code rejection). Strictly stronger; its bite catches a synthetic constant
spread the grep could not. FR-015a cited in the docstring.

Evidence: `ruling7_behavioral_guard_bite.txt`, `ruling3_abnormal_spread_bite.txt`.

## Section 6 — fixture hygiene

Mechanical redaction module `trading.logkit.redaction`. Scrubbed A2's `connection_id`
(and an A3 evidence file surfaced by the §8 secret scan). Both fixtures labeled with
evidentiary bounds (A2 = post-parse, proves logic not rendering; A3 = raw wire,
proves rendering) and the raw-wire-text default doctrine.

Evidence: `fixture_labels.txt`, `secret_scan.txt`.

## RULING 8 — source-inspection audit (report-only)

Every `inspect.getsource` / code-text-assertion test enumerated. Tests [1]–[4] (the
paper/mainnet guard surfaces) and [6] would still pass with the mechanism
disabled-but-string-present → a **cluster for its own WO**. Not fixed here.

Evidence: `source_inspection_audit.txt`.

## Section 7 — decision log

`docs/decisions/2026-07-19-cost-fork-and-vocabulary-in-use.md` — four entries
(three §7 + the sixth-0.1d instance from ADDENDUM 2).

## Section 8 — verification

`verify.txt`: both full-suite summary lines, delta accounting, import-linter,
contract count, ruff. Deterministic 139 passed (237.05s); randomized seed 20260719
139 passed (236.88s). Pushed `1ef7447..452914f`; local == remote == `452914f`.

## Report answers (§9 items 9–11)

- **Prose standing in for output in evidence/WO-011/?** No — all bite/recon/verify/scan
  files are redirected output. The two escalation files are the stop-and-ask records
  (prose by design) with embedded real output.
- **Changed but not asked:** scrubbed a `connection_id` in
  `evidence/WO-008b-A3/rendering_and_ground_truth.txt` (surfaced by the §8 secret
  scan; same inert session id as A2). Nothing else. `instructions.md` left unstaged.
- **Could not be completed:** everything in WO-011 is done. Two items surfaced for a
  ruling (not blockers): the 3 declared-but-unproducible codes (§5) and the
  source-inspection cluster (R8) — both documented, both honestly green.

## Open items handed to the lead
1. Ruling on the 3 declared-but-unproducible reason codes (remove, or wire emission).
2. The source-inspection cluster WO (RULING 8).
3. Vestigial `sequence` params on `LocalBookData` and the discarded volume-scaling
   slippage — both tracked in `docs/open-cleanup.md`.
