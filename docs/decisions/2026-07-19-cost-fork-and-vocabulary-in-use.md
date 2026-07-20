# WO-011 decision log

Four entries: three from WO-011 §7, plus one ruled in ADDENDUM 2 (the sixth 0.1d
instance).

---

## 1. A vocabulary check must run against the vocabulary in use, not on file

Fifth 0.1d instance. The prefix-freedom check as originally specified examined the
DECLARED list while the real collision (`EXEC_NO_MARKET_STATE` vs
`EXEC_MARKET_STATE_TIMESTAMP_MISSING`) sat in production raise strings. The check
had the same blind spot as the assertions it audited: it read the dictionary, not
the sentences. WO-011 §5 extends the check to scrape codes RAISED IN PRODUCTION and
to require that every raised code is declared and every declared code is producible
— and property 2's producibility scan EXCLUDES the declaration site, because if a
code's own declaration counted as production the check could never fail.

---

## 2. A captured fixture's evidentiary power is bounded by the layer it was captured at

Raw wire text witnesses everything downstream of the wire, including the
parse/rendering layer; a post-parse structure witnesses only what follows parsing.
A2 (post-parse dicts) can prove book/checksum LOGIC but structurally cannot witness
rendering — the trailing zeros were already gone. A3 (raw wire text) proves that
plus rendering. Both are kept; ground truth accretes. **Future captures default to
raw wire text**, and redaction is applied mechanically via `trading.logkit.redaction`.

---

## 3. Cost fork closed

`backtest/costs.py` carried the superseded additive-spread formula (and, more
subtly, a mid-price notional basis and a volume-scaled slippage) while the paper
venue implemented the R6 ruling — same trade, two answers, differing by exactly one
spread. Order-dependent and invisible until A3's tests reshuffled the suite. WO-011
unified both onto a single `trading.execution.costs.compute_execution_costs`, so
they now agree by CONSTRUCTION rather than by two implementations happening to
match. Unified BEFORE the 24h corpus is captured, because evidence is not built on a
known fork in the definition of truth. The discarded volume-scaling slippage is
preserved in `docs/open-cleanup.md`, not deleted silently.

---

## 4. Source-text assertions are not enforcement (sixth 0.1d instance)

`test_code_review_no_synthetic_spread` certified the no-synthetic-spread property
(FR-015a, one of the most constitutionally important behaviors) with
`inspect.getsource` and a string match. It proved a string appeared in a file, not
that the spread was observed: `spread = market_state.spread * 0` would have passed
it. Replaced with a behavioral guard — distinct observed spreads must produce
distinct tracking spread costs, and an abnormal spread must be rejected.

Lineage of the 0.1d defect class on this project: self-asserting string literal →
error class for an impossible event → bite proof against a stale object → assertion
satisfied by an adjacent guard's longer code → vocabulary check reading the declared
list instead of raised strings → source grep standing in for behavior. **Standing
consequence: source-text assertions are documentation with a test runner attached,
not enforcement.** The remaining source-inspection tests are audited (report-only)
in `evidence/WO-011/source_inspection_audit.txt` and form a cluster for a future WO.
