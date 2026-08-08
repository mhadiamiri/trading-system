# WO-053 — PRE-REGISTRATION

**Committed BEFORE the strategy was written and BEFORE the run. Nothing below may be revised after
seeing a result (§0.8). A negative is the registered expectation, not a failure.**

Corpus: `corpus_20260805`, v1 digest `e3ab1aec…`, 88 files, 36.8867 covered hours. READ ONLY.

---

## §2.1 Strategy — mid-price momentum on time bars

`BarMomentumStrategy`: build fixed-interval time bars from corpus **mid prices**, take the return
over the last N closed bars, and enter in the direction of that move when its magnitude clears a
declared threshold T. Flat otherwise.

This is deliberately the **best-constructed** minutes-horizon taker variant available on this
corpus, not a strawman. It is the construction most likely to succeed among that family: bars
suppress tick noise, mid-price avoids the bid/ask sawtooth, and — critically — **T is set high
enough that only moves plausibly capable of paying the round trip are traded at all.** A weaker
construction (every-tick signal, or a threshold below cost) would lose by an uninteresting
mechanism. If this one loses, the family loses.

### A prior ruling this must address head-on

WO-048 §U1 **rejected** mid-price momentum, on the grounds that it "would read like the trivial
strategy while quietly using a fabricated price channel."

That objection was to substituting **mid for `last_price`** — presenting a book-derived number as
though it were a trade print. It does not apply here, and the difference is declared rather than
glossed:

- The signal is **explicitly mid**, named `mid_price`, sourced from `BookState.mid_price =
  (best_bid + best_ask) / 2`, computed from two real quoted sides.
- `BookState` has **no** `last_price`, `total_volume` or `trade_count` attribute, so no trade
  channel can be fabricated even by accident (WO-048 §3, D48).
- Nothing in this WO claims a traded price. The mid is a **quote midpoint** and is reported as one.

The trade-channel strategy (`TrivialMomentumStrategy`) remains **deferred**, still blocked on a
trade-channel re-capture. This does not evaluate it.

## §2.2 Bars

| Declared | Value |
|---|---|
| **Interval** | **60 seconds** |
| **Alignment** | to each **segment's own start**, not to the wall-clock epoch |
| **Price** | mid = `(best_bid + best_ask) / 2` — OHLC recorded, **close** used by the signal |
| **Containment** | **a bar is built from the frames of exactly ONE segment and never spans a gap or seam** |
| **Partial bars at segment edges** | **DISCARDED — never emitted, never marked complete** |

**Why 60 seconds.** The registered horizon is "minutes". One minute is the smallest unit that is
unambiguously *minutes* rather than seconds, and it is the standard bar in every venue's own
tooling — so it is a convention, not a number picked for this data. At the corpus's observed
~24–32 frames/s a 60-second bar holds ~1,440–1,920 frames, so a bar is densely sampled and its
close is not a single stray tick.

**Why segment-relative alignment.** Epoch alignment would let one wall-clock bucket appear on both
sides of a gap. Anchoring each segment's bars to that segment's own first frame makes
"bar k spans a discontinuity" structurally unrepresentable rather than merely checked for.

**Why partial bars are discarded.** A bar covering 12 seconds of its intended 60, reported as a
completed 60-second bar, is a small lie of exactly the kind this project refuses — and it would
land precisely at segment edges, i.e. disproportionately at the boundaries where the data is most
suspect. Discarding costs at most one bar per segment end. The discarded count is reported.

## §2.3 Signal — N and T, DERIVED FROM THE COST ARITHMETIC

**This derivation is principled construction, not tuning.** Both values are fixed from a *cited*
cost figure **before any result exists**, and neither was chosen by looking at this corpus, at a
return distribution, or at a P&L. No variant was evaluated. There is no sweep.

### The cost bar

| Component | Round trip | Source |
|---|---|---|
| Taker fee, 2 sides | **2 × 0.80% = 1.60%** | **CITED** — Kraken Pro spot Tier 1 taker, https://www.kraken.com/features/fee-schedule, retrieved 2026-08-07, via `fee_schedule.taker_pct()` |
| Slippage, 2 sides | 2 × 0.01% = **0.02%** | **MEASURED** — 50,000 corpus frames, WO-050 §4 |
| Spread crossing, 2 sides | ≈ **0.0016%** | measured mean spread 0.521 on mid 64,635.87 |
| **ROUND-TRIP COST** | **≈ 1.62% of notional** | |

### N = 5 bars

The momentum lookback is **5 closed 60-second bars = a 5-minute window**.

Derivation: 5 minutes is the smallest round multiple of the declared bar that is unambiguously a
*minutes-horizon* window. It is also **multi-bar on purpose** — the same argument WO-048 made for
its rolling window: a single-bar signal would carry no state across bars, which would render the
per-segment reset (U3) and the observation-only first bar **vacuously satisfied**, so the
machinery would appear to work while never being exercised. Carrying 5 bars of history means a
reset that failed to happen is visible in the signal.

Not derived from the data. Not swept.

### T = 3.24% — **2.0 × the round-trip cost**

```
T = 2.0 × 1.62%  =  3.24% over the 5-bar window
```

**Why a multiple at all, and why 2.0.** Entering requires believing the *subsequent* move will
exceed 1.62%. Under the momentum premise — that an observed move tends to continue at similar
magnitude — setting T equal to the round-trip cost would buy an expected continuation that exactly
equals cost: **zero expectancy before variance**. A multiple of 2.0 demands an observed move twice
the cost bar, so the expected continuation covers the round trip roughly twice over, leaving margin
for the continuation being weaker than the observed move.

2.0 is the smallest whole multiple that leaves any margin at all; 1.0 is provably zero-expectancy
and anything below 1.0 is negative by construction. It is the **most favourable defensible choice**
for the strategy — a larger multiple would trade even less. Chosen from the cost arithmetic alone.

### Direction

Enter **BUY** when the 5-bar mid return ≥ +3.24%, **SELL** when ≤ −3.24%, flat otherwise.

## §2.4 Size — 0.1 BTC fixed

Identical to WO-048 and WO-050, so this result is directly comparable to the existing record.
Position sizing is a separate question and would add a free parameter to a run that is testing a
declared hypothesis.

## §2.5 Costs

- Fee: **cited** Tier 1 taker 0.80% via `fee_schedule.taker_pct()` — not typed in.
- Slippage: **measured** 1 bp (WO-050 §4), reused, not re-derived.
- Neither is assumed. Both channels are numerically distinct (0.008 vs 0.0001).

## §2.6 THE REGISTERED EXPECTATION — both admissible outcomes, declared in advance

> **(i) NEGATIVE NET P&L**, if the signal fires often enough to trade; **or**
>
> **(ii) TOO FEW TRADES TO EVALUATE** — because a T derived from a 1.60% round-trip bar fires
> rarely on BTC at minutes horizon, and 36.9 hours may contain only a handful of qualifying moves.
>
> **Outcome (ii) is itself the finding**, and arguably the sharper one: at Tier 1 taker, the only
> minutes-horizon trades worth taking are so rare that this corpus cannot evaluate them, while the
> ones frequent enough to evaluate lose by construction.
>
> **A positive, statistically meaningful result is NOT expected. If one appears, it is a finding to
> REPORT and INVESTIGATE, not to celebrate** — and it must not be obtained by any post-hoc change.

**My registered prior, stated plainly so it cannot be claimed after the fact: I expect outcome
(ii).** A 3.24% move inside 5 minutes is a violent event for BTC — the kind that accompanies a
macro print or a liquidation cascade, not ordinary trading. I expect **zero or very few** such
windows in 36.9 hours of one instrument, and therefore expect the run to be *insufficient to
evaluate* rather than *evaluated and negative*.

## §2.7 THE FALSIFIER (0.12) and the trade-count floor

**What result would show the arithmetic wrong:** a **materially positive net P&L over a trade count
at or above the floor below.** That, and only that, would falsify "minutes-horizon taker strategies
at Tier 1 are dead by arithmetic."

### Declared trade-count floor — **30 round trips**

> **≥ 30 round-trip trades → the run EVALUATES the strategy.** The verdict is then whatever the net
> P&L says, positive or negative.
>
> **< 30 round trips → the run is INSUFFICIENT TO EVALUATE.** Net P&L is reported but is **not** a
> verdict on the strategy, in either direction — including if it is positive.

Derivation: 30 is the conventional small-sample threshold, chosen because it is conventional rather
than because it suits this corpus. Below it, a net P&L is dominated by a handful of individual
outcomes and no inference about expectancy is warranted.

**This floor is declared now precisely so the verdict cannot be chosen after seeing the number.** A
positive P&L on 4 trades is "insufficient", and so is a negative one — the rule cuts both ways and
is committed before either is possible.

### What would NOT falsify the arithmetic

- A negative net P&L (outcome i) — confirms it.
- Too few trades (outcome ii) — confirms it, via the rarity mechanism rather than the loss
  mechanism.
- A positive net P&L on **fewer than 30** trades — insufficient; reportable, not a falsification.

---

## Registered parameter table — the whole of it

| Parameter | Value | Source |
|---|---|---|
| `BAR_INTERVAL_SECONDS` | 60 | convention (minutes horizon) |
| `BAR_ALIGNMENT` | segment-relative | containment |
| partial bars | discarded | honesty at edges |
| `MOMENTUM_BARS` (N) | 5 | smallest round minutes-horizon window; multi-bar so U3/U4 are non-vacuous |
| `THRESHOLD_PCT` (T) | **3.24%** | **2.0 × round-trip cost (1.62%), cost-derived** |
| `ROUND_TRIP_COST_PCT` | 1.62% | cited fee + measured slippage + measured spread |
| `ORDER_SIZE_BTC` | 0.1 | comparability with WO-048/050 |
| fee | 0.80% taker | cited, `fee_schedule` |
| slippage | 0.0001 | measured, WO-050 |
| **evaluation floor** | **30 round trips** | conventional small-sample threshold |

Reused unchanged, all previously proven: default-deny reader, force-flat at every boundary (U2),
fresh strategy per segment (U3), observation-only first unit (U4), average-cost position P&L,
aggregate position cap. **No new accounting.**
