# The execution null: reached, not worked (WO-016 §4.1)

**Date:** 2026-07-21 · **Context:** WO-008b-B-RERUN 60-minute live capture · **Author:** project lead

> "The 60-minute capture produced 0 fills, `STRAT_NO_SIGNAL` ×111,010, and the staleness
> guard was never invoked. A truthful null — AND it means the unified cost model has still
> never run against live market data. 'The loop ran end-to-end' must not be read as 'every
> layer has been exercised live': the execution and cost layers were REACHED, not WORKED.
> Not a defect — a denominator statement about what this run certifies, and it sharpens what
> the corpus-era backtests are for. The trivial strategy firing rarely was pre-ruled
> acceptable at the channel decision; now it is measured."

**Consequence:** a future WO must force at least one live-data fill through
`trading.execution.costs.compute_execution_costs` before "Execution exercised live" may be claimed.
