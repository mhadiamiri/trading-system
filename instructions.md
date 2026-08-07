# WO-047 — BACKTEST-OVER-SEGMENTED-CORPUS: INVESTIGATION AND PROPOSAL. NO IMPLEMENTATION.

BASE: WO-046 closeout HEAD (reader landed, CI green). Confirm in §1.
Reference artifact: `corpus_20260805` — 36.8867 covered h, 3,847,540 frames, 19 gaps, 1 seam
(`PROCESS_RESTART`, 2.1061 h), across 2 runs.

SCOPE: **INVESTIGATE, PROPOSE, STOP.** No production code. No backtest run. No number produced.
SHIP IMPACT: **NO.** `git diff -- src/` must be empty (paste). Evidence + proposal only.

WHY AN INVESTIGATION. The reader deliberately returns `.segments` and has NO `.concat()` — D20's
"continuous-looking data across a gap is not a thing the API can emit." Every existing backtest
component was built against a continuous stream. Feeding it 19 gaps and a 2.1-hour seam raises
SEMANTIC questions that change what the P&L MEANS, and none have been ruled. Getting them wrong
produces a beautiful number that is fiction — the exact failure this apparatus exists to prevent.
Ops will not specify the mechanism from memory: **propose from the code.** This is the WO-027 shape.

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.2 **No implementation.** Not a line. If a question can only be answered by writing code, say so and
    scope it — do not answer it by building.
0.5 Report every attempt.
0.7 **BUILT-VS-OPERATED (D24).** Everything below is OPERATED and READ; this WO builds only a proposal.

    | Thing | Status | Where |
    |---|---|---|
    | `compute_execution_costs` (the ONE cost model) | **OPERATED** | `execution/costs.py`; ruled `total = fees + slippage`, executed price crosses the spread, spread is attribution, >5% abnormal-spread reject; reconciled to the cent (WO-011) |
    | `BacktestRunner` → `PaperExecutionClient._simulate_fill` | **OPERATED** | the live backtest path |
    | `CorpusReader` (default-deny, segments) | **OPERATED** | WO-046 |
    | `corpus_20260805` | **OPERATED — READ ONLY** | ratified D46; never write to it |

---

## §1 CONFIRM STATE, THEN READ AND PASTE THE THREE SURFACES
HEAD, test count both interpreters, `git diff -- src/` empty, gates green, corpus digest snapshotted.

Paste verbatim, with line numbers:
1.1 **`BacktestRunner`** — how it ingests data today: what it iterates, what shape it expects, where
    the loop is, and every assumption of CONTINUITY in it (a `for` over one stream, index arithmetic,
    "previous bar", rolling windows, warm-up counters, timestamp deltas used as elapsed time).
1.2 **The strategy under test** — whatever the "simple strategy" is. Name it, paste its entry/exit
    logic, and enumerate every piece of STATE it carries across ticks (indicators, warm-up
    requirements, position, pending orders).
1.3 **`compute_execution_costs` + `_simulate_fill`** — the fill path, confirming what a fill needs
    from a MarketState (bid/ask/spread/timestamp) and whether anything in it assumes the PREVIOUS
    state is adjacent in time.

---

## §2 THE SEMANTIC QUESTIONS — answer each from the code, or mark it UNRULED and escalate

For each: state what the code does TODAY if naively fed segmented data, and what you believe it
SHOULD do. Do not implement either.

2.1 **Position across a gap.** A position is open when a segment ends. The next segment begins after
    a 16-second (or 2.1-hour) hole with no data. Options: force-flat at segment end; carry the
    position and mark it at the next segment's first price; refuse to backtest across a gap at all.
    What does the code do now? What is honest? Note the asymmetry: carrying a position across a
    2.1-hour blind window and claiming the P&L is real is a strictly bigger lie than doing it across
    16 seconds — does the answer depend on gap DURATION or CAUSE, and if so that is a class-aware
    decision like the reader's acknowledgment.
2.2 **Indicator warm-up across a segment boundary.** Does the strategy need N ticks of history? If a
    segment is shorter than N, is it tradeable at all? Does state carry across a gap or reset? An
    indicator computed from ticks spanning a hole is an indicator over data that does not exist.
2.3 **Fill legality on the first tick after a gap.** The first MarketState after a 2.1-hour blind
    window may be far from the last one seen. A fill there is executable in the model but was NOT
    executable in reality — nobody could have traded on a price they could not see coming. State
    whether the current fill path would happily fill it.
2.4 **Elapsed-time assumptions.** Anything using `t[i] - t[i-1]` as elapsed (rates, annualisation,
    holding periods, drawdown durations) silently absorbs gap time. Enumerate every such site.
2.5 **What "the backtest ran over the corpus" would MEAN.** Given 36.8867 covered hours in 20
    discontinuous stretches: is the deliverable one result over the union, or per-segment results
    aggregated? If aggregated, how do costs, position, and P&L compose? Name the metric the number
    would be.

---

## §3 THE ACKNOWLEDGMENT DECISION (the reader forces it — this is the point)
The reader will REFUSE a corpus-spanning read unless the backtest explicitly acknowledges gap
classes, per request, per class. **So the backtest must state, in code, which discontinuities it
tolerates and why.** That is D20's guarantee reaching the consumer. Propose: which classes should a
backtest acknowledge (`KEEPALIVE_RECONNECT` sub-second? `VENUE_DISCONNECT`? `PROCESS_RESTART`
never?), with the reasoning for each, and what it must do at the boundaries it does accept. An
acknowledgment that accepts everything to make the backtest run is the failure mode — say so if you
find yourself reaching for it.

---

## §4 PROPOSE AND STOP
Produce: the recommended design (how the runner consumes segments, what happens at each boundary,
which classes are acknowledged and why, what the reported metric is and what it excludes), its diff
shape (files and signatures, NOT applied), what it costs, what it forecloses, and the acceptance
criterion you would hold it to — including the bite proof that would prove the backtest CANNOT
silently trade across a hole.

Then **STOP.** Any question you mark UNRULED goes to the lead. Ops expects several: these are
semantics, not implementation, and they decide what the first honest number MEANS.

## §5 ACCEPTANCE
- Three surfaces pasted with line numbers; every continuity assumption enumerated
- 2.1–2.5 each answered from the code or marked UNRULED with the question stated precisely
- §3 acknowledgment proposal with per-class reasoning
- §4 proposal with diff shape, cost, foreclosures, acceptance criterion, and the anti-splice bite proof
- `git diff -- src/` EMPTY (paste); corpus digest unchanged; test count unchanged
- Commit the investigation evidence standalone; push; CI green both legs (real run number, counts
  from job logs)

## §6 REPORT — `WO-047-INVESTIGATION-REPORT.md`
The three surfaces; the continuity-assumption enumeration; 2.1–2.5 with evidence or UNRULED
verdicts; the acknowledgment proposal; the design proposal with its anti-splice bite proof; every
attempt; any STOP; CI run.

**THEN STOP.** The lead rules the unruled semantics; then the backtest is built and run against
`corpus_20260805`.