# The $100 live-instrument ladder

**Date:** 2026-08-11
**Status:** RECORDED under WO-064 §8.2, so it is not relitigated
**Origin:** D55

## The claim being recorded

**A small live run is a legitimate MEASUREMENT INSTRUMENT — not a deployment.** $100 at risk is not
a trading strategy; it is a way to obtain data that no amount of public capture can produce, because
some quantities exist only when you have an order resting in the book.

**And the qualifier that makes it true rather than a rationalisation: the apparatus is what makes
$100 buy knowledge instead of noise.** Without pre-registration, cited costs, and bite-proved
guards, $100 of live trading produces an anecdote. With them it produces a measurement. **The
distinction is the apparatus, not the amount.**

## The three conditions — ALL must hold before any live order

**(a) The venue is chosen, with integrity mitigations declared and native capture validated.**

Not "a venue is picked" — the venue's **feed integrity property is stated in the terms it actually
supports**. Where a venue publishes no checksum, the substitute design is built and bite-proved
*first*, and the corpus header declares that its property is **consistency, not correctness**. A
corpus captured before its integrity design exists is not evidence.

**(b) A PRE-REGISTERED strategy has passed on that venue's own captured data, with cited all-in
costs.**

Three separate requirements, and each has been violated before:

- **Pre-registered** — declared in full before any result exists (0.8). Changing a cost assumption
  after a verdict is the hazard the death certificate was built to prevent.
- **That venue's own captured data** — not a bridged basis, not another venue's history. A basis
  admitted for bar-horizon evaluation does **not** validate a strategy that reads the book.
- **Cited all-in costs** — fees at the tier a zero-volume account can actually claim, plus gas, plus
  expected funding for the target hold duration, plus price impact at the declared order size. An
  optimistic tier is a cost assumption wearing a fact's clothing.

**(c) The execution path carries the standard guards, bite-proved.**

Kill switch, position cap, and `TRADING_ENV` semantics **adapted to the venue** — adapted, not
assumed to transfer. On a signing venue this is not a re-point but a rebuild: the `no_credential`
preflight scans `.env` for API credentials and **would not see a signing key at all**, and a signing
key is not a revocable session credential.

## What the ladder explicitly does not permit

- Scaling up because the instrument "worked". The instrument measures; it does not validate itself.
- Skipping (b) because live data is "more real" than captured data. Live data without
  pre-registration is how a cost assumption gets changed after the fact.
- Treating a passed condition as permanently passed. A venue's fees, minimums and feed can all
  change; each is a cited figure with a retrieval date, and vendor schedules move.

## Falsifier

**The ladder is falsified as a design if a live run under all three conditions produces a
measurement that could have been obtained from public capture alone.** In that case the instrument
was unnecessary and the risk was unjustified. The quantities believed to require it are: **fill-time
distributions conditional on queue position**, and **adverse selection on resting orders** — neither
derivable from a public book, because the book shows what *was* there, never what *would have*
filled.
