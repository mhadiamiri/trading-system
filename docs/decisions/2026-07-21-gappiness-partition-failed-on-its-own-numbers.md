# The gappiness partition failed on its own declared numbers (WO-016 D27 §C)

**Date:** 2026-07-21 · **Context:** WO-016 §B VOID-metric re-ruling · **Author:** project lead

> "The instrument-gappiness partition failed on its own declared numbers: missed-wake at 2.0 x
> interval and elevated-lag at overrun > 100ms are the same threshold wearing two names. The
> counterfactual escaped both — uniform 199ms cycles, cycle time doubled, temporal resolution
> halved, zero recorded gaps, zero elevated samples — while the 'naive' metric we were about to
> discard as overhead-noise would have caught it. THE NAIVE METRIC'S STRUCTURAL BIAS AND ITS
> SENSITIVITY WERE THE SAME PROPERTY: measuring against an idealized clock made it wrong about
> health and right about degradation. Separately: the accounting identity offered as proof
> (2,908 + 29 + ~0 = 2,937) was correct and insufficient — AN IDENTITY OVER OBSERVED DATA IS
> NOT A COVERAGE CLAIM OVER THE INPUT DOMAIN. That is the fixture-coverage doctrine restated
> for metrics. Consequence: the VOID gate becomes a three-component OR-gate — discrete, spiky,
> uniform — each mode owned by construction, with the residual (degradation of the sentinel's
> own measurement) declared as a floor limit rather than papered over."

**Implemented:** WO-016 §B — `_check_instruments_gappy` is now the three-component OR-gate
(recorded-gaps / elevated-lag / mean-cycle-drift-vs-frozen-baseline), with the residual declared as
the instrument's floor limit (`evidence/WO-016/three_component_void_metric.txt`). The mean-cycle
baseline is FROZEN at this run's observed 108.886 ms; re-declaration is a 0.4 event.
