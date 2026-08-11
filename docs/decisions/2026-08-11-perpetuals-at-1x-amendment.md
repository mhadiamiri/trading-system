# Constitutional amendment — perpetual contracts at 1x leverage

**Date:** 2026-08-11
**Status:** RATIFIED (narrow form), recorded under WO-064 §8.1
**Supersedes:** the spot-only scope assumption that WO-062 applied and WO-063 corrected

## The amendment

> **Perpetual contracts are admitted as a tradeable instrument class, at 1x leverage only, with
> notional fully collateralized, no margin multiplier, and funding measured as a cost.**
>
> **Leverage greater than 1x is excluded absolutely.**

## The reasoning

**At 1x leverage with the notional fully collateralized, the economic exposure is spot-equivalent.**
A long perpetual position of notional N, backed by N of collateral, gains and loses exactly what N
of spot gains and loses, plus funding. There is no margin multiplier, no amplified drawdown, and no
liquidation path that spot does not also have — because there is nothing borrowed.

It follows that **choosing a perpetual over spot is a fee-and-access decision, not a leverage
decision.** The instrument is selected because a venue prices it better, lists it in a smaller
minimum size, or exposes a better feed — the same grounds on which any venue is selected. It is not
selected to take more risk, and under this amendment it cannot be.

**Why leverage >1x is excluded absolutely rather than bounded.** A bound invites relitigation at
every review; an absolute exclusion does not. Leverage introduces liquidation as a failure mode with
**no counterpart in the spot apparatus** — the risk layer, the force-flat semantics, and the
position caps were all designed against an instrument that cannot be liquidated by an adverse price
move alone. Admitting leverage would require re-deriving all of them. That work is not in scope and
this amendment does not open it.

## What the amendment obliges

1. **Funding is a COST and must be measured, not assumed.** It is a third cost shape:
   `funding ∝ notional × time held`, where the existing model carries only `fee ∝ notional` and
   `gas = fixed`. **Nothing in the cost model currently has a time dimension.** Any suite evaluated
   on a perpetual instrument states its funding treatment in its header.

2. **Funding is discrete, not continuous.** It is levied at interval timestamps; a hold either
   straddles one and pays the full interval rate, or does not and pays nothing. Expected cost over
   uniform entry is `(D / interval) × rate` — **derived, not assumed proportional** — and the
   variance is the whole distance between zero and the full rate.

3. **Liquidation mechanics are recorded as facts for a future risk-layer WO, and are not modelled
   until one exists.** At 1x fully collateralized they should not arise; "should not" is not
   "cannot", and the difference is a risk-layer question.

## Falsifier

**This amendment is falsified if a 1x fully-collateralized perpetual position is shown to carry a
loss path that spot does not** — for example a venue liquidating at 1x on a mark-price excursion,
an auto-deleveraging mechanism, or a socialised-loss regime. **Any such finding reopens the
amendment**, because the entire justification is spot-equivalence of economic exposure.

## What this does NOT do

It does not adopt a venue, admit a data basis, or authorise live execution. Those are governed
separately — see the $100 live-instrument ladder recorded alongside this note.
