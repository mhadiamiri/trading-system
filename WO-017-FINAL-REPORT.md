# WO-017 — FINAL REPORT: FR-018a(f) Literal Closure (Wire-String Retention) + First Pre-Declared Re-Baseline

**Baseline:** `3e6263f` (checkpoint) atop `0463e77`. **NO VENUE CONNECTION** — replay/simulated only.
**Result:** FR-018a(f) satisfied **literally**; 200/200 replay green; 207 passed both orders; re-baseline
executed inside the WO. Standing rules 0.1–0.9 observed (0.1a checked: private representation change, no
public signature change; 0.9 seam honored — passed only because budget was healthy).

---

### 1. Retention — where captured, how stored, what the checksum consumes
- **Captured at parse:** `json.loads(message, parse_float=WireDecimal, parse_int=WireDecimal)`
  (`kraken_v2_book.py` live path). `WireDecimal(Decimal)` stores the RAW TOKEN TEXT on `.wire` when
  constructed from a str; the Decimal value is the numeric identity used for compare/sort/zero-check.
- **Stored alongside the Decimal:** ladder levels are `(price, qty)` tuples of WireDecimal. The book never
  does arithmetic on a level (apply replaces, delete filters, sort reorders, truncate slices), so the
  subclass — and its `.wire` — survives from parse to checksum. A **private** representation change: the
  ladder still holds `(Decimal-subclass, Decimal-subclass)` tuples; no public signature changed (0.1a clear).
- **Checksum consumes the wire string EXCLUSIVELY:** `_current_ladder_strings` returns `p.wire, q.wire` via
  `_wire_pair` — **no `str()`, no `format()`, no rendering**. `compute_checksum` is unchanged (it already
  consumed strings).

### 2. §1.5 synthesis proof — every ladder-writing path, with denominator
- **Writers (create level values): 2** — `apply_snapshot` (`self.bids/asks = sorted(bid/ask_levels)`),
  `apply_incremental_update` (update/append). **Origin: 1** — both are fed exclusively by `_parse_levels`
  → `_retain_wire`. **Non-creating:** delete (filter), sort (reorder), truncate (slice), reset (empty) —
  operate on existing tuples, never synthesize a value. **Residual synthesis paths after the change: 0.**
- **Can ANY path produce a level without a wire string?** No production path can. `_retain_wire` yields a
  WireDecimal-with-`.wire` for a str, passes through a WireDecimal that already carries one, and **RAISES**
  for anything else. A plain-Decimal level can only be introduced by a *test* calling `apply_snapshot`
  directly — and that is exactly what the no-fallback bite proof (b) exercises: it hits the `_wire_pair`
  guard and raises.

### 3. No-fallback guard — bite proof, four artifacts, reason code declared
- Reason code **`CHECKSUM_WIRE_STRING_MISSING`** declared in `logkit/decision.py` (DATA), same commit.
- Guarded at BOTH ends: origin (`_retain_wire`) and consumption (`_wire_pair`). Bite proof (b) below.

### 4. Three bite proofs (§1.6) — four artifacts each, `sha256`, observable effect
`evidence/WO-017/bite_proofs.txt`; target `tests/integration/test_wire_string_retention.py`;
sha256 BEFORE/AFTER (all proofs) = `43bad39658adee000d7232e7de923044faea2dcff890c65ea1ff9bd7bfde7869`
(byte-identical restore confirmed per proof).

| Proof | Invariant | A1 PASS | A2 REAL-FAIL (weakened) | A3 PASS (restored) | A4 sha256-exact |
|---|---|---|---|---|---|
| (a) | checksum input == transmitted text, not a re-render | ✓ | ✓ (`.wire`→`str()` → `1.0E-7` ≠ `0.00000010`) | ✓ | ✓ |
| (b) | missing wire string RAISES `CHECKSUM_WIRE_STRING_MISSING` | ✓ | ✓ (guard disabled → DID NOT RAISE) | ✓ | ✓ |
| (c) | scientific-notation frame round-trips & validates | ✓ | ✓ (`.wire`→`str()` → `'E'`-sentinel fires → no emit) | ✓ | ✓ |

**ALL THREE PROOFS: OK.**

### 5. 200/200 replay — pasted
```
tests/integration/test_checksum_capture_replay.py ..                     [100%]
```
`test_all_200_captures_validate_through_production_checksum` PASSES: 200/200 captured failures validate
through `apply_snapshot → _current_ladder_strings(.wire) → compute_checksum`. The fixture stores
`str(Decimal)` (scientific `1.0E-7`), predating retention, so the harness reconstructs the transmitted wire
form via `WireDecimal(format(Decimal(x),'f'))` — the fixed-point string WO-016 proved reproduces Kraken's
transmitted text 200/200 (test-side evidence reconstruction; production retains `.wire` and never renders).

### 6. Interim fix and sentinel — raise or removed? sentinel still bites? INTERIM label resolved?
- **REMOVED**, not left dead: the `format(x,'f')` render in `_current_ladder_strings` is deleted and
  replaced by `.wire` consumption; `grep "format(...,'f')"` on the adapter → none. INTERIM label removed.
- **`'E'`-sentinel STAYS** (`compute_checksum`), now guarding the invariant "no synthesized notation reaches
  the CRC" rather than the interim implementation. **Still bites:** `test_checksum_sentinel.py` 3 passed
  (incl. counterfactual); and bite proof (c)'s weakening fires it.

### 7. §4 — domain question answered structurally
WO-016 left one unproven cell (non-fixed-point wire token) and open questions on trailing zeros, exponent
extremes, integer-valued quantities. With the wire string retained, **there is no rendering to be wrong for
any input** — the domain-completeness question is answered **structurally, not empirically**. No per-input
enumeration is required because no per-input rendering exists.

### 8. RE-BASELINE — old 108.886 ms → new → DELTA, ATTRIBUTED; old scope end-dated; material?
- **108.886 ms → 107.923 ms; DELTA −0.963 ms (−0.9%), ATTRIBUTED to wire-string retention** (a `.wire`
  attribute read replaces the per-level `format(x,'f')` render). Pinned WO-009 source, pinned ~1959/min, 60s,
  same host. Six runs: 107.732/107.923/107.923/108.520/107.933/107.733 ms (median 107.93; 108.520 is a
  warmup outlier, still favorable). Evidence `evidence/WO-017/rebaseline.txt`.
- **Old scope END-DATED (2026-07-21), never overwritten:** carried into the record's `superseded` ledger in
  `config/mean_cycle_baselines.json`. `save_baseline` now accretes history structurally (guard test added).
- **Material?** Not to any gate (well within the 50% mean-cycle drift-VOID bound and the ±20% rate scope) —
  but a **real, reproducible, FAVORABLE** result: the "at what cost" clause is answered in ms under identical
  replayed load, and **the cost is negative**.

### 9. LOAD-WORK dimension added to scope and protocol
Third scope dimension (§6). Added to the store `scope.load_work` and to the protocol declaration
(`tools/establish_mean_cycle_baseline.py` `LOAD_WORK`, printed and written on `--write`). Empirical
justification: live-vs-replay agreement +0.008 ms. **Invalidation:** deeper ladders, heavier per-level
validation, or additional per-level storage require re-validation — noted as this WO being that condition's
own first trigger (the recursion the "baselines attract scope errors" line predicted).

### 10. FR-018a(f) annotation — pasted; residual?
`specs/002-quote-level-data/spec.md` FR-018a(f) status: **SATISFIED LITERALLY** *(WO-017, 2026-07-21)*,
was "satisfied in spirit, letter unachievable." **RESIDUAL:** the only remaining re-render is in the WO-016
200-capture **test harness** (reconstructing recorded evidence's wire form) — not a production path. **No
production residual.**

### 11. Decision-log entry — pasted
`docs/decisions/2026-07-21-structural-satisfaction-retires-the-defect-class.md` carries the §8 text verbatim
plus mechanism, the §1.5 denominator, and the measured negative cost.

### 12. Verification (`evidence/WO-017/verify.txt`)
- Deterministic (`-p no:randomly`): **207 passed** in 257.33s, 0 failed / 0 xfailed / 0 xpassed.
- Randomized (`--randomly-seed=20260725`): **207 passed** in 246.28s, same.
- **Delta vs 202 baseline (+5), all explained:** +3 `test_wire_string_retention.py` (the §1.6 proof targets);
  +2 `test_mean_cycle_baseline_gate.py` (`…carries_its_rebaseline_ledger`, `…never_overwrites_a_differing_figure`).
- `lint-imports` **6 kept / 0 broken**; `tools/contract_count_check.py` **6/6**; `ruff` **All checks passed**.
- **New reason code declared same commit:** `CHECKSUM_WIRE_STRING_MISSING`.
- **Secret scan:** 0 real hits (grep matches were the word "token" in prose); store raw-hostname check: absent
  (hashed only).
- **local HEAD == remote HEAD:** see §push below.

### 13. Venue connection? **NO.** HTTPS doc fetch? **NO.**

### 14. Prose standing in for output? **NO** — 200/200 and 207-both-orders are pasted/captured; the bite
proofs are four artifacts each with sha256 in `evidence/WO-017/bite_proofs.txt`; the re-baseline is three+
captured tool runs in `evidence/WO-017/rebaseline.txt`.

### 15. Changed but not asked? — every file
- **Production:** `src/trading/data/adapters/kraken_v2_book.py` (WireDecimal, `_retain_wire`, `_parse_levels`,
  `_wire_pair`, `_current_ladder_strings`, live parse), `src/trading/logkit/decision.py` (reason code),
  `src/trading/loop/host_baseline.py` (`save_baseline` history-preservation — WO-mandated by §5 "never
  overwrite").
- **Tests:** `test_wire_string_retention.py` (new), `test_checksum_capture_replay.py` (§2 wire reconstruction),
  `test_mean_cycle_baseline_gate.py` (+2 ledger guards).
- **Tools:** `establish_mean_cycle_baseline.py` (§6 LOAD_WORK + history-aware `--write`),
  `replay_checksum_capture.py` (§2 wire path), `wire_string_bite_proof.py` (new, §1.6 harness).
- **Config/docs/evidence:** `config/mean_cycle_baselines.json` (re-baseline + ledger + load_work),
  `specs/002-quote-level-data/spec.md` (§7), the decision log (§8), `evidence/WO-017/*.txt`, this report.
- **Deliberate NON-change (declared):** the class constant `MEAN_CYCLE_BASELINE_SECONDS = 0.108886` is the
  test/default seed; the LIVE gate is host-scoped and reads the store (D28), which now carries 0.107923. Left
  as-is to avoid re-calibrating drift-gate tests against a value the live path overrides. **`instructions.md`**
  carries the lead's WO text (their edit) — never committed by me.

### 16. What could not be completed, and why? — **Nothing in WO-017.** All of §1–§10 executed. Still open by
prior ruling (separate WOs): WO-013 → CI → 008c → the 24-hour corpus.

---
**STOP for review.** Did NOT proceed to WO-013 or the corpus.
