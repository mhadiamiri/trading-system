# WO-065 — DEPTH READS, INJECTIVE DOCS PUSH, AND THE dYdX RECONCILIATION

**Grant used as a boundary, not a budget.** Reads spent: **Hyperliquid 5/5, dYdX 5/5, Injective 4/5**
(plus 2 requests that returned no depth — a 404 path probe and a 404 market — enumerated below).
**No order path, no credentials, no wallet, no socket, no code.** `git diff -- src/` empty.

---

## THE HEADLINE — price impact does not exist at $100 on Hyperliquid, and on dYdX it is intermittent

**The term this grant was spent to measure is zero on Hyperliquid in 5 of 5 reads and zero on dYdX
in 4 of 5. The fifth read is the finding.**

```
round 5, dYdX ask book, top of book:
   63630.0  x 0.000200  =     $12.73     <- the "best ask" is a DUST order
   63666.0  x 2.261800  = $143,999.76    <- the real liquidity, 36 ticks away
```

**dYdX's quoted touch is frequently a dust order, and the quoted spread is therefore not the
tradeable spread.** In round 5 dYdX showed the *narrowest* quoted spread of the whole window
(0.629 bps) while a $100 buy paid **4.937 bps** — because $100 exhausts a $12.73 level and fills
0.057% higher. The same appeared on the bid side in round 4 (**$6** at the touch).

**This is exactly the eighth-scope-dimension lesson §3 warned about: one instant is one regime.**
Four reads said price impact was zero. The fifth said the quoted price on dYdX can be decorative.

---

## §1 STATE CONFIRMED

| | |
|---|---|
| HEAD at read time | `2181153` (now `47f907c` — progress.md only, no code) |
| `git diff -- src/` | **empty** |
| pytest 3.14.6 / 3.11.15 | **572 passed, 2 skipped** both |
| import-linter | **6 kept, 0 broken** |
| `corpus_20260805` / `validation_20260809` | `e3ab1aec…` 38/38 · `884f9f00…` 3/3 |

**`phaseb_20260809`** — informational, not disturbed: **23.9984 of 556 covered hours**, 26/26
segments verified, **not currently running**; leg 3 is the operator's call and nothing here blocks
on it.

---

## §2 / §3 THE READS — five rounds, timestamped, with regimes

**Non-simultaneity handled by §3.3's preferred route:** both venues are read back-to-back inside one
round. **Observed round spans: 0.378 s, 0.425 s, 0.597 s, 0.957 s** (round 1 spanned 20.0 s because
it also carried the Injective read). **Sub-second across rounds 2–5, so the cross-venue difference
is a venue difference, not a timing artifact.**

| round | venue | read UTC | mid | quoted spread | levels | **L1 ask $** | $100 buy | $200 buy | min buy |
|---|---|---|---|---|---|---|---|---|---|
| 1 | hyperliquid | 19:11:43 | 63,215.5 | 0.158 | 20 | ≥200 *(derived)* | 0.000 | 0.000 | 0.000 |
| 2 | hyperliquid | 20:10:19 | 63,650.5 | 0.157 | 20 | 245,799 | 0.000 | 0.000 | 0.000 |
| 3 | hyperliquid | 21:00:20 | 63,711.5 | 0.157 | 20 | 307,468 | 0.000 | 0.000 | 0.000 |
| 4 | hyperliquid | 21:50:20 | 63,614.5 | 0.157 | 20 | 956,324 | 0.000 | 0.000 | 0.000 |
| 5 | hyperliquid | 22:40:21 | 63,654.5 | 0.157 | 20 | 16,177 | 0.000 | 0.000 | 0.000 |
| 1 | dydx_v4 | 19:11:47 | 63,194.5 | 2.374 | 100 | ≥200 *(derived)* | 0.000 | 0.000 | 0.000 |
| 2 | dydx_v4 | 20:10:20 | 63,625.0 | 2.515 | 100 | 7,496 | 0.000 | 0.000 | 0.000 |
| 3 | dydx_v4 | 21:00:20 | 63,688.0 | 1.570 | 100 | 7,497 | 0.000 | 0.000 | 0.000 |
| 4 | dydx_v4 | 21:50:21 | 63,596.5 | 5.818 | 100 | 143,999 | 0.000 | 0.000 | 0.000 |
| **5** | **dydx_v4** | **22:40:21** | 63,628.0 | **0.629** | 100 | **13** | **4.937** | **5.298** | 0.000 |

*Round 1's L1 notional is a **derived lower bound** (≥$200, from `levels_consumed = 1` at the $200
walk) — the raw-level capture was added after that read, and re-reading to obtain it would have
spent grant to recover a figure already bounded. Rounds 2–5 are measured exactly.*

**No walk exhausted the published depth**, so no figure here is a lower bound on cost.

### Range, not mean (§3.2)

| | quoted spread bps | $100 buy slip bps | $200 buy slip bps |
|---|---|---|---|
| **hyperliquid** | 0.157 / **0.157** / 0.158 | 0.000 / 0.000 / **0.000** | 0.000 / 0.000 / **0.000** |
| **dydx_v4** | 0.629 / **2.374** / 5.818 | 0.000 / 0.000 / **4.937** | 0.000 / 0.000 / **5.298** |

*(min / median / max.)* **Hyperliquid's spread is pinned at one tick in all five reads — a 0.6%
range. dYdX's varies 9.2×.**

### Regime (§3.4) — declared basis, one active read of five

**Threshold declared before labelling: |mid move| ≥ 20 bps between rounds = ACTIVE.** *Derivation:
20 bps over ~50 minutes is ~4× the median 1-minute mid move measured on `corpus_20260805`
(0.25 USD on ~64,900 = 0.39 bps), scaled to the round interval and rounded UP per 0.15.*

```
round 2  +68.8 bps  ACTIVE
round 3   +9.6 bps  QUIET
round 4  -15.2 bps  QUIET
round 5   +6.3 bps  QUIET
```

**The window spanned 3.48 hours (19:11:43 → 22:40:22 UTC) and contained ONE active transition and
three quiet stretches.** The verdict below is therefore **measured predominantly in a quiet regime**,
with one active sample — stated plainly, as every prior verdict in this project states its regime.

**And the dust-touch appeared in a QUIET round.** Round 5's $13 touch is not a stress-market
artifact; it is dYdX's book being thin at the touch in ordinary conditions. *Falsifier for the
regime labelling: a round labelled QUIET containing a larger intra-interval excursion than its
endpoints reveal — endpoint sampling cannot see it, and five reads cannot exclude it.*

### The quantity that actually enters the cost stack

**Effective round-trip touch cost = quoted spread + |buy slip| + |sell slip| at $100:**

| | min | **median** | max |
|---|---|---|---|
| **hyperliquid** | 0.157 | **0.157 bps** | 0.158 |
| **dydx_v4** | 1.570 | **2.515 bps** | **5.965** |

**Hyperliquid is 16× cheaper at the touch at the median and 38× at dYdX's worst read.**

---

## §4 THE INJECTIVE PUSH — closed, and the answer is liquidity, not documentation

**Injective is disqualified on MEASURED LIQUIDITY.** All three of its BTC perpetual books:

| market | bids | asks | best bid |
|---|---|---|---|
| `btc-usdt-perp` | **1** | **0** | $36,464 × 2.02, timestamped **2023-11-18** |
| `btc-ausd-perp` | **0** | **0** | — |
| `btc-wusdm-perp` | HTTP 404 | — | — |

**And its spot map holds 44 markets, none of them BTC** — which **corrects WO-063**, where I recorded
Injective spot as "yes". It has spot; it has no BTC spot.

**The integrity primitives are real and populated** — the live response carried
`sequence: 79811624` and `height: 167260191`, corroborating the protobuf finding from WO-063/064.
**A maker rebate and a real sequence number on an empty book are worth nothing.**

### The four cells, closed or declared (0.11 — routes enumerated)

| cell | outcome |
|---|---|
| **minimum order notional / increments** | **ON-CHAIN, NOT DOCUMENTED.** `min_notional`, `min_price_tick_size`, `min_quantity_tick_size` are per-market fields declared in `injective/exchange/v2/market.proto`, set by governance. **That is where the truth lives** — a doc-based answer would have been wrong by construction. |
| **funding interval / mechanism / cap** | **Interval: hourly. Mechanism: `FundingRate = cap(TWAP + HourlyInterestRate, HourlyFundingRateCap)`. Cap: `HOURLY_FUNDING_RATE_CAP`, an on-chain exchange-module parameter** — again per-market, not a documented constant. |
| **terms of use** | **DECLARED UNKNOWN.** `injective.com/terms-and-conditions` → 404; `helixapp.com/terms/` → JS-rendered, returned only a page title. Site-level check attempted per the WO-060 discipline and not obtainable. |
| **published depth / cadence** | `OrderbookV2Request` takes a **client-specified `depth`** parameter — unlike Hyperliquid's venue-fixed 5/20. **Cadence not measurable without a stream**, which the grant does not cover. |

**Routes attempted (0.11):** docs landing page · InjectiveLabs GitHub org (100 repos) ·
`injective-proto` tree (640 files) · raw `stream/v2/query.proto` and `exchange/v2/market.proto` ·
`injective-lists` static market maps · Helix fee docs · Helix terms · injective.com terms.

---

## §5 THE RECONCILIATION — required before the ranking can carry a venue decision

**The answer is (b), and the depth reads turn it from an assertion into a measured, bounded one.**

D-r51 ruled dYdX's non-canonical book disqualifying **for strategies that read book state**. That
disqualifier is **not** answered by the integrity route: WO-063 established that the question CRC32
asks has no referent on dYdX, because *"the correct order book at any given time is whatever the
current block proposer has in its mempool"*, and full-node streaming with `execModeFinalize` tells
you what **executed**, not what was **quotable**. Nothing found in this WO changes that. What
resolves the tension is **scope**: an order that never leaves level 1 does not read book state — it
reads the **touch**, a single price-and-size pair, and the trade tape. At the declared $100 size the
target class is therefore a touch-and-tape class, not a book-state class, and D-r51's disqualifier
was scoped to a class we are not building. **But this WO measured the threshold at which that ceases
to be true, and it is not comfortable: the disqualifier is dormant only while the order stays inside
level 1, and on dYdX level-1 ask notional ranged from $143,999 down to $13 across five reads — a
$100 order left level 1 in 1 of 5 reads (20%), in a quiet regime.** On Hyperliquid it stayed inside
level 1 in 5 of 5, with a measured minimum of $16,177. **So the constraint that must travel with any
venue decision is a number, not a sentiment: on dYdX at $100, book state is read roughly one time in
five, and the scoping that clears D-r51 is therefore only approximately true there.** A larger
capital base, a book-reading signal, or a venue whose touch is routinely dust **re-triggers the
disqualifier in full**, and that constraint binds *before* the suite is pre-registered, not after.

---

## §6 THE COMPLETE COST STACK — price impact filled in

**All figures at $100 per-order notional. Funding from WO-064's measured distribution (p99, 15-min
hold). Effective touch = quoted spread + both-side slippage, measured here.**

| venue | inst. | fees RT | **touch (median)** | **touch (worst)** | funding p99@15m | **ALL-IN median** | **ALL-IN worst** | min | concurrent @$100 | integrity |
|---|---|---|---|---|---|---|---|---|---|---|
| **Hyperliquid** | perp | 9.00 bps | **0.157** | 0.158 | +0.0008 | **9.16 bps = 0.0916%** | **9.16 bps** | $10 | 10 | **NONE** |
| **dYdX v4** | perp | 10.00 bps | **2.515** | **5.965** | +0.0023 | **12.51 bps = 0.1251%** | **15.97 bps = 0.1597%** | **$1** | **≈100** | offset; no canonical book |
| **Injective** | perp | 10.00 bps | **n/a — BOOKS EMPTY** | — | UNKNOWN | **NOT TRADEABLE** | — | on-chain | — | `seq`+`height` (real, unusable) |
| **Kraken** *(incumbent)* | spot | 162.16 bps | — | — | n/a | **1.6216%** | — | UNKNOWN | UNKNOWN | **CRC32** |

### DOES PRICE IMPACT CHANGE THE LEADER? **Yes — it reverses it.**

**Before this WO** (WO-064): dYdX led on concurrency (~100 positions vs 10) at a **0.010%**
per-round-trip cost penalty — one cent per $100.

**After measurement:** the penalty is **0.0335% at the median and 0.0681% at the worst read** —
**3.3× to 6.8× larger than the fee gap alone.** dYdX is **37% more expensive all-in at the median**
and **74% more expensive at its worst observed touch.**

**Hyperliquid leads on a fully measured stack.** Its all-in round trip is **0.0916%**, it is
**stable** — the same 0.157 bps touch in all five reads across an active transition and three quiet
stretches — and its level-1 depth never fell below $16,177.

**What it costs to say that**, stated rather than buried: Hyperliquid has **no feed integrity
mechanism at all**, and a **$10 minimum giving 10 concurrent positions against dYdX's ~100**. The
leader on cost is the laggard on both integrity and concurrency. **The decision is a trade between a
measured 0.0335% and an unmeasurable book**, and that is the lead's to make, not mine.

### What could still overturn it

- **Five reads is five instants.** Round 5 proved a single read can misrepresent a venue by 38×.
  Hyperliquid's stability across 5 reads is evidence, not proof; **a dust-touch episode on
  Hyperliquid would collapse the gap**, and 5 reads cannot exclude one.
- **The regime is predominantly quiet** — one active transition of five reads. **Neither venue was
  observed under stress**, and dYdX's thin touch appeared in a *quiet* round, which suggests its
  behaviour under stress is unmeasured rather than benign.
- **Order size interacts with the finding.** At dYdX's $1 minimum, slippage was **0.000 bps in all
  five reads including round 5** — the dust touch absorbs a $1 order completely. **dYdX is cheap for
  many small orders and expensive for one $100 order**; Hyperliquid is flat at both. A strategy
  shape that places ~100 × $1 orders would not pay dYdX's touch penalty at all, and that shape is
  exactly what its $1 minimum permits.

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | Gates, corpora, state | 572/2 both; 6/6; both corpora verify |
| 2 | Injective market IDs from `injective-lists` (static, not an API read) | 3 BTC perp markets found; **spotMap has no BTC** |
| 3 | Injective `derivative/v2/orderbook` round 1 | **empty book** — parsed as no usable depth |
| 4 | Injective shape probe `v2` | 1 stale bid, **0 asks**, `sequence`/`height` present |
| 5 | Injective shape probe `v1` | **HTTP 404** — no depth returned |
| 6 | Injective `btc-ausd-perp` | **0 bids, 0 asks** |
| 7 | Injective `btc-wusdm-perp` | **HTTP 404** — no depth returned |
| 8 | Depth rounds 1–5, Hyperliquid + dYdX | **all 10 reads succeeded**; table above |
| 9 | Injective funding / minimums / terms | closed as **on-chain** (2 cells), **declared unknown** (terms) |
| 10 | Injective in rounds 2–5 | **deliberately excluded** — settled in round 1; grant not respent |

**Reads that returned no depth (5 and 7) are reported as attempts, not counted as measurements.**

---

## §7 ACCEPTANCE

| requirement | status |
|---|---|
| Book-walk cost at $100/$200/min, per venue, per read, in bps | **met** |
| ≤5 reads per venue, UTC timestamps, stated window | **met** — HL 5, dYdX 5, Injective 4; window 19:11:43 → 22:40:22 UTC (3.48 h) |
| Per-read figures **plus range**, not mean alone | **met** |
| Non-simultaneity handled and stated | **met** — same-round reads, spans 0.378–0.957 s (round 1: 20.0 s) |
| Regime characterised per read | **met** — declared threshold, 1 ACTIVE of 5, stated as a limit |
| Published-level count stated; lower-bound labelling | **met** — 20 (HL) / 100 (dYdX); **no walk exhausted the book**, so no cost figure is a lower bound |
| Injective's four cells closed or declared with routes | **met** — 2 on-chain, 1 declared unknown, 1 partially closed |
| **The §5 reconciliation paragraph written** | **met** — answer (b), with the measured threshold and the re-trigger condition |
| Decision table restated with impact filled | **met** |
| `git diff -- src/` empty; no order path/credentials/wallet/code | **met** |
| Gates green | **met** |
