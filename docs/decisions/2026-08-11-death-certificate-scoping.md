# SCOPING NOTE — what WO-053's death certificate does and does not cover

**Date:** 2026-08-11
**Status:** RECORDED under WO-064 §8.3
**Applies to:** WO-053-REPORT.md and every later citation of it

## Read this before citing the death certificate

**WO-053 stands. Its scope is narrower than the way it has been cited.**

### What it establishes

At **Kraken Tier 1 taker fees**, giving a round-trip cost of **1.6216%** — derived in committed code
as `2 × 0.80% cited fee + 2 × 1 bp measured slip + 0.0016% measured spread` — **in the measured quiet
regime of `corpus_20260805`**, the minutes-horizon momentum class is dead. The arithmetic is not
close:

```
largest 5-minute move in 36.9 covered hours : 0.4076%
largest 60-minute move                      : 0.5388%
round-trip cost                             : 1.6216%
observations >= the round-trip cost alone   : 0
```

**No move in the entire corpus paid for a round trip.** That finding is correct and is not disturbed.

### What it does NOT establish

**It does not extend to a materially different fee regime.** The verdict is a statement about
**1.6216%**, not about trading. At a round trip of **~0.09–0.10%** — the level measured on
perpetual venues in WO-063 — the same measured moves clear the bar by a wide margin. The 5-minute
maximum of 0.4076% is **4.5×** a 0.090% round trip.

**Citing WO-053 as a universal verdict on short-horizon trading is MISCITING IT.**

**It also does not extend beyond the measured regime.** `corpus_20260805` is 36.9 covered hours of
one quiet period. The move distribution in a volatile regime is not the one measured, and the
certificate says nothing about it either way.

## The correct procedure for a new fee regime

**A new fee regime is a NEW PRE-REGISTERED QUESTION, not a re-run of a closed one.** The distinction
matters and 0.8 owns it:

- **The hazard** is changing a cost assumption *after* seeing a verdict, then re-running until the
  verdict flips. That is the failure the certificate exists to prevent, and it remains prevented.
- **What is legitimate** is declaring a NEW question, in a NEW regime, **in full and before any run**
  — including the fee schedule with its tier, retrieval date and source; the gas treatment; the
  expected funding for the target hold duration with its straddle derivation; and the price impact
  at the declared order size.

**Nothing in this note re-opens WO-053 retroactively.** Its verdict at 1.6216% is untouched, and it
stays the answer for any strategy paying that cost.

## Falsifier

**This scoping is falsified if the ~0.09% regime turns out not to be reachable in practice** — if
minimum order sizes, price impact at the operator's size, or realised funding push the true all-in
cost back toward 1.6216%. In that case the certificate's original scope covers the new regime after
all, and it does so on the arithmetic rather than by assumption.

**The measurement that would settle it: all-in round-trip cost at the declared order size on the
chosen venue, including realised funding and measured price impact.** As of this note, price impact
and the historical funding distribution are both **DECLARED UNKNOWN**.
