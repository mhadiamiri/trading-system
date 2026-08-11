# WO-064 — HF INVESTIGATION: closing the unknowns

**Report only. No socket, no RPC, no wallet, no key, no account, no code.**

## THE DECLARED ORDER SIZE (0.19) — everything below is computed at it

**PRIMARY BASIS: $100 per-order notional.** Sensitivities reported at **$200** and at **$10**.

**Why $100.** Operator capital is $100–200. $100 is the entire low-end capital in a single position
— the largest order the operator can place at the bottom of the range, and therefore the *most
favourable* size for every fixed cost. Reporting there first means fixed-cost findings are
conservative: anything that dominates at $100 dominates worse at $10. The $10 row is the smallest
slice a multi-position shape permits on the venue with the highest minimum.

**THE 0.1 BTC (~$6,460) BASIS IS RETIRED FOR THIS WO.** Every carried-over figure below was
**recomputed at $100**, not scaled. Where a figure is a percentage it is size-invariant and says so;
where it is a fixed cost it is re-expressed as a percentage of $100.

**And 0.19 immediately caught a second inherited premise — in this WO's own text.** §4 states that
gas at $100 is "$0.50 → 0.5%, larger than every fee under discussion." **That premise does not hold
for any of the three DEXs.** Measured below: Hyperliquid **zero**, dYdX **zero on trades**,
Injective **$0.0003**. The $0.50 figure was an illustration from WO-062 that travelled into a
premise. It is retired here on the same grounds 0.19 retired 0.1 BTC.

---

## §1 STATE CONFIRMED

| | |
|---|---|
| HEAD | **`e3aad95`** (actual, not pinned) |
| `git diff -- src/` | **empty** |
| pytest 3.14.6 | **572 passed, 2 skipped** (316.08 s) |
| pytest 3.11.15 | **572 passed, 2 skipped** (313.83 s) |
| import-linter | **6 kept, 0 broken** |
| `corpus_20260805` | `e3ab1aec…` · **38/38** |
| `validation_20260809` | `884f9f00…` · **3/3** |

**`phaseb_20260809`** — informational. **Not running.** Leg 2 closed cleanly 2026-08-10T16:02:44Z;
**23.9984 covered hours** of the 556-hour target, 2 runs, 1 seam, 2 bounded gaps, 26/26 segments
verified. Leg 3 is the operator's call and nothing here blocks on it.

---

## §2 MINIMUM ORDER SIZE — and the first legitimate disqualifier in this comparison

| venue | instrument | **min notional** | tick / increment | **concurrent @ $100** | **@ $200** |
|---|---|---|---|---|---|
| **Hyperliquid** | perp + spot | **$10** | price ≤5 sig figs, ≤ `MAX_DECIMALS − szDecimals` (6 perp / 8 spot); size = integer × lot | **10** | 20 |
| **dYdX v4** | BTC-USD perp | **≥ $1**, increments ≈$1 | tick 1–10 bps of reference price (tiers 1–2) | **≈100** | ≈200 |
| **Injective / Helix** | spot + perp | **DECLARED UNKNOWN** | UNKNOWN | UNKNOWN | UNKNOWN |
| **Binance** | spot BTCUSDT | **5 USDT** | — | **20** | 40 |
| **Binance** | **BTCUSDT perp** | **100 USDT** | — | **1** | **2** |
| **Bybit** | spot / perp | **DECLARED UNKNOWN** | UNKNOWN | UNKNOWN | UNKNOWN |
| **OKX** | spot / perp | **DECLARED UNKNOWN** | UNKNOWN | UNKNOWN | UNKNOWN |

### THE DISQUALIFIER ON ARITHMETIC — Binance perps

**Binance raised the BTCUSDT perpetual minimum notional from 5 USDT to 100 USDT** (announced
2023-10-27, effective 2023-11-02). At $100 capital that is **exactly one position with zero
headroom**; at $200, two.

**A high-frequency short-hold strategy that cannot hold more than one position, and cannot enter
without committing 100% of capital, is not operable.** This is a disqualifier **on arithmetic** —
the minimum notional and the capital are both cited numbers and the division is the whole argument.
**It is categorically different from WO-062's disqualifiers**, which came from a self-imposed
spot-only scope. This one would survive any framing. *Falsifier: Binance lowering the BTCUSDT perp
minimum, or capital rising above ~$1,000 to give meaningful concurrency.*

**Binance spot is unaffected** — 5 USDT minimum, 20 concurrent positions at $100.

### The size ladder this creates

**dYdX (≈$1) is 10× more permissive than Hyperliquid ($10), which is 10× more permissive than
Binance perps ($100).** At $100 capital that is the difference between ~100, 10, and 1 concurrent
positions — and concurrency bounds every strategy shape before a signal is designed, exactly as §2
predicts.

---

## §3 FUNDING — mechanics cited, distribution BLOCKED, derivation done anyway

### 3.1 Mechanics

| | **Hyperliquid** | **dYdX v4** | **Injective** |
|---|---|---|---|
| interval | **1 hour** | **1 hour** | **UNKNOWN** |
| rate setting | `F = avg premium + clamp(interest − premium, ±0.0005)`, paid hourly at **⅛** of the 8-h rate; premium sampled every **5 s** | `(premium / 8) + interest`; premium = median 1-min votes averaged over the 1-h tick | UNKNOWN |
| interest component | **0.01%/8 h = 0.00125%/h** | **0% (cross markets — BTC-USD is one)**; 0.125 bps/h isolated | UNKNOWN |
| **cap** | **4%/hour** | `600% × (IMF − MMF)` = **12%/8 h ≈ 1.5%/h** for BTC (IMF 5%, MMF 3%) | UNKNOWN |

### 3.2 THE HISTORICAL DISTRIBUTION — **DECLARED UNKNOWN**, and I must report why

**§3.2 instructs me to obtain published historical funding rates. The WO's own SCOPE forbids the
only means of obtaining them.**

Verified rather than assumed: Hyperliquid's historical funding is retrieved by
**`POST https://api.hyperliquid.xyz/info` with `{"type":"fundingHistory", ...}`**, and *"The
documentation does not provide static historical data; it only specifies the endpoint structure for
dynamic retrieval."* dYdX's equivalent is an indexer REST query. **Both are RPC calls.**

SCOPE says *"NO socket, NO RPC"* and also *"published historical rate data only"* — those two
clauses are in conflict for this data, because the data is published **only through an API**.

**I did not make the call.** §3.4 provides for exactly this: *"If unobtainable, DECLARE UNKNOWN."*
So: **median, p95, p99, max, and how often the rate approached the cap are DECLARED UNKNOWN.**

**This is the single most valuable measurement outstanding in the whole venue programme, and it is
two API calls.** A one-line scope amendment — *"historical funding may be retrieved by a read-only
public API call"* — unblocks it entirely. That is the lead's to grant; I am not going to grant it to
myself.

### 3.3 THE STRADDLE DERIVATION — stated, not assumed (0.16)

**Mechanism.** Funding is **not** a continuous charge. It is levied at **discrete hourly
timestamps**. A position pays the **full interval rate** if it is open across a timestamp and
**nothing** if it is not. So for a hold of duration D minutes against an interval of 60 minutes,
with entry time uniform over the interval:

```
P(hold straddles a funding timestamp) = D / 60      for D <= 60
E[funding cost]                       = (D / 60) × (hourly rate)
```

**This is not proportionality by assumption** — it is proportionality *derived* from a uniform entry
time over a discrete-payment schedule. The two coincide in expectation, **but they differ entirely in
variance**: the realised cost is either zero or the full hourly rate, never the average. *Falsifier:
entry times correlated with the funding clock — a strategy that systematically enters just after a
timestamp would pay far less than this, and one that enters just before would pay far more.*

### Expected funding at the declared size ($100), by hold duration

| hold D | P(straddle) | **Hyperliquid E[cost]** | **dYdX E[cost]** | at HL **cap** | at dYdX **cap** |
|---|---|---|---|---|---|
| 1 min | 1.7% | **0.0000208%** ($0.00002) | **0%** | 0.0667% ($0.067) | 0.025% ($0.025) |
| 5 min | 8.3% | 0.000104% | **0%** | 0.333% ($0.333) | 0.125% |
| 15 min | 25% | 0.000313% | **0%** | 1.000% ($1.00) | 0.375% |
| 60 min | 100% | 0.00125% ($0.00125) | **0%** | 4.000% ($4.00) | 1.500% |

*dYdX BTC-USD is a cross market whose interest component is **0%**, so its baseline expectation is
exactly zero — funding is paid only when the premium is non-zero.*

### 3.4 THE NUMBER THAT MATTERS

**Fee round trips at $100: Hyperliquid perp 0.090% ($0.09), dYdX perp 0.100% ($0.10).**

- **In calm conditions, expected funding is negligible.** At 60 minutes Hyperliquid's baseline
  0.00125% is **1.4% of the fee round trip**; at HF durations (1–15 min) it is a rounding error, and
  dYdX's is exactly zero.
- **At the cap, funding dominates immediately.** A **1-minute** hold on Hyperliquid at cap costs
  **0.0667%** — **74% of the entire fee round trip** — and a 5-minute hold costs **3.7× it**.
- **So the answer is conditional, and the condition is precisely what I could not measure.**
  Expected funding is *small* almost always and *larger than every fee under discussion* on a bad
  day. **Whether "bad days" are 0.1% or 10% of hours is DECLARED UNKNOWN.**

**Stated plainly: funding does not threaten the fee thesis on average, and could invert it in the
tail. The distribution is the deciding evidence and it is one API call away.**

---

## §4 GAS AT SMALL SIZE — the feared cost does not exist on these venues

| venue | gas on trades | as % of $100 | **break-even size** (gas = fee) |
|---|---|---|---|
| **Hyperliquid** | **ZERO** — *"Trading on Hyperliquid is gas-free"* | **0%** | **none — gas never dominates** |
| **dYdX v4** | **ZERO on order placement and cancellation.** *"traders would not pay gas fees to trade"*; *"if an order is open and is then canceled, traders will not be charged a fee."* Fees only on **filled** orders | **0%** | **none** |
| **Injective** | **0.00001 INJ ≈ $0.0003 per transaction** (gas compression) | **0.0003%** | **≈ $0.60** |

**Break-even derivation (Injective).** Gas equals the fee when `0.0003 = size × 0.0005` (taker
0.05%), i.e. **size = $0.60**. Below $0.60 gas dominates; at $100 it is **0.6% of the fee**, and at
$10 still only 6% of it. **Not a constraint at any size this operator would trade.**

**What DOES cost gas**, stated so it is not overlooked: **deposits, withdrawals and bridging.**
Hyperliquid: *"Depending on the withdrawal chain and method, there may be small gas fees"* — amount
**DECLARED UNKNOWN**. dYdX: gas is needed *"when you transfer funds to create a new subaccount"*,
payable in USDC or DYDX. **These are per-cycle costs, not per-trade**, so at high frequency they
amortise over every trade in the session rather than compounding per trade — the opposite of the
shape §4 feared. **A single $5 bridge cost amortised over 1,000 trades is 0.005% per trade; over 10
trades it is 0.5%.** The break-even is therefore in *trade count per funding cycle*, not order size.

**§4's premise is retired under 0.19**, and the correction matters: gas was nominated as the cost
that would kill small-size DEX operation, and on all three candidates it is approximately zero.

---

## §5 THE NON-CANADIAN VENUES

| venue | instrument | maker | taker | **round trip** | min notional | gas |
|---|---|---|---|---|---|---|
| **Binance** | spot | **0.100%** | **0.100%** | **0.200%** (0.150% with BNB −25%) | **5 USDT** | nil |
| **Binance** | BTCUSDT perp | *see note* | *see note* | **DECLARED UNKNOWN** | **100 USDT** — **disqualifying at this capital** | nil |
| **Bybit** | spot | 0.1% flat | 0.1% flat | **0.200%** | UNKNOWN | nil |
| **Bybit** | perp | **0.02%** | **0.055%** | **0.110%** | UNKNOWN | nil |
| **OKX** | spot | — | 0.08–0.1% | **0.160–0.200%** | UNKNOWN | nil |
| **OKX** | perp | **0.02%** | **0.05%** | **0.100%** | UNKNOWN | nil |

**Binance perps fee note (0.1e):** the fetched schedule returned the strings *"Standard / 0.095%"*
and *"Standard / 0.07125%"* for USDⓈ-M futures without a clean maker/taker pairing. **I will not
guess which is which.** The base-tier perp pair is **DECLARED UNKNOWN**. It is moot for this
operator anyway — the 100 USDT minimum disqualifies it at $100–200 capital.

### The Binance asset, weighed as §5 directs

**We already hold nine years of Binance BTCUSDT data — 229/229 files checksum-verified against the
publisher's own SHA-256, monthly klines 2017-08-17 → 2026-07-31, bridged to our own Kraken capture
at r = 0.999103 (240m) and 0.997110 (60m), with the USDT basis measured out-of-sample at ±0.3 bps in
2024–2025.** No other candidate has anything comparable.

**But 0.16 requires the mechanism, and the mechanism limits the claim.** That basis is **BTC/USDT
bar data at ≥1h**. An HF short-hold strategy reads **the book, at sub-second cadence**, and the
admitted basis says **MAY NOT: anything finer than its bars — no spread, no depth, no
microstructure.** **The nine-year asset does not validate an HF strategy; it validates the venue's
bar-horizon price series.** It is a genuine advantage for venue *selection* and *regime context*, and
it is **not** a substitute for native HF capture on whichever venue is chosen. Recording it as
"starts ahead" is right; recording it as "already validated" would be misciting our own work in the
same way §0's preamble says the death certificate was miscited.

---

## §6 HYPERLIQUID'S INTEGRITY-MITIGATION DESIGN

**The problem, restated at HF scale.** Hyperliquid publishes **no checksum, no sequence number,
5 or 20 levels, ≥0.5 s cadence**. `checksum_failures_total` could never move — *a metric that cannot
move is not a metric.* At hours-horizon a stale or wrong book costs little; **an HF signal reads the
book constantly, so every read is exposed.**

**Candidate mitigations — enumerated (0.11), four from the WO and three added.**

| # | mechanism | **what it detects** | **what it CANNOT detect** |
|---|---|---|---|
| 1 | **Trade-print reconciliation** — do executed prints on the trade channel lie within the book's stated levels? | A book that contradicts its own venue's prints: trades outside the quoted range, or at levels the book says are empty | A book that is **uniformly stale** — if both feeds lag together, prints and book agree while both are wrong. Also silent on **depth beyond the touch**, since prints only touch one level |
| 2 | **Cross-feed consistency** — two independent connections compared | Per-connection loss, drops, and one-sided staleness | **Venue-side error**. Both connections receive the same wrong book and agree perfectly |
| 3 | **Staleness bound** — refuse a snapshot older than a declared max age | A stalled feed, a dead socket, a `time` field that stops advancing | A **fresh but wrong** book. Freshness is not correctness |
| 4 | **Snapshot re-request cadence** as periodic ground truth | Drift between the pushed feed and an on-demand read | Nothing, if both come from the same server state — it re-reads the same source, so it is a **consistency check, not an independent one** |
| 5 | **ADDED — mid-price continuity bound** | Implausible jumps between consecutive snapshots given the ≥0.5 s cadence: a discontinuity larger than the measured per-interval move distribution | A **plausible-looking wrong book**. A subtly shifted book passes trivially |
| 6 | **ADDED — cross-venue price sanity** (against Binance/dYdX BTC) | A venue-wide fault: Hyperliquid's book diverging from every other venue at once | **Genuine venue-specific dislocation**, which is real market information and would be flagged as a fault. **This one can produce false positives that destroy true signal** |
| 7 | **ADDED — book-vs-own-fills reconciliation** (live only) | Whether the book we read predicted the fill we got — the only check that measures the quantity we actually care about | Requires **live orders**; it cannot validate a corpus captured before trading, and it is unavailable at capture time |

### The verdict §6 demands

**No combination gives an integrity guarantee comparable to CRC32.** Kraken's checksum answers *"is
my reconstruction byte-identical to the venue's book?"* — a statement about **correctness**, verified
against the venue's own authority.

**Every mechanism above answers a weaker question, and the weaker property is CONSISTENCY, not
correctness.** They establish that the feed is internally coherent, fresh, and agrees with itself
and its neighbours. **None can establish that the book Hyperliquid published is the book Hyperliquid
matched against**, because Hyperliquid publishes nothing that would let anyone check.

**The strongest achievable combination is 1 + 3 + 5** — trade-print reconciliation, a staleness
bound, and a continuity bound — which together detect *stale*, *incoherent*, and *discontinuous*
books. **They cannot detect a fresh, coherent, plausible, wrong book.** That residue is exactly the
WO-063 line: **integrity failures are loud; semantic mismatches are silent.**

**The corpus's `checksum_failures_total` equivalent would be a composite counter** —
`book_consistency_failures_total`, decomposed by mechanism (`print_outside_book`, `stale_snapshot`,
`discontinuity`) so a reader can see *which* property failed. **It must be named differently from
`checksum_failures_total`**, because calling a consistency counter a checksum counter would import a
guarantee that does not exist — and that is the misciting failure this project has now recorded
three times.

**Recommendation, stated as a design constraint rather than a decision:** if Hyperliquid is chosen,
**this design must be built and bite-proved *before* any capture there is treated as evidence**, and
the corpus must carry a header declaring that its integrity property is *consistency*, not
*correctness*.

---

## §7 MAKER ECONOMICS — priced

**The prize, at the declared size.** Per $100 round trip:

| venue | taker/taker | **maker/maker** | **saving per round trip** |
|---|---|---|---|
| Hyperliquid perp | 0.090% ($0.090) | 0.030% ($0.030) | **$0.060 (67%)** |
| dYdX v4 perp | 0.100% ($0.100) | 0.020% ($0.020) | **$0.080 (80%)** |
| **Injective** | 0.100% ($0.100) | **−0.010% (a REBATE: +$0.010)** | **$0.110 — you are paid to trade** |
| Bybit perp | 0.110% ($0.110) | 0.040% ($0.040) | $0.070 (64%) |
| OKX perp | 0.100% ($0.100) | 0.040% ($0.040) | $0.060 (60%) |

**At high frequency this exceeds venue-vs-venue.** The spread between the best and worst *venue*
taker round trip is 0.090%→0.110% = **0.020%**. The spread between taker and maker on a *single*
venue is up to **0.110%** on Injective — **5.5× larger.** **Execution style dominates venue choice.**

**D51's reasoning still holds: an unvalidated queue-position fill model is fiction.** The question is
what validating one would cost.

### What validation requires, priced

| # | requirement | why | cost |
|---|---|---|---|
| 1 | **Queue position observable?** | A maker fill model needs to know where in the queue an order sits. Hyperliquid publishes `n` (order count per level) but **not** our position within it | **1 WO to determine observability per venue.** If unobservable, the model must be *statistical*, not positional — a materially weaker artifact that must be declared as such |
| 2 | **Fill-time distributions** | P(fill within horizon H \| queue depth, spread, volatility) — the model's core | Requires **native capture with our own resting orders**. Cannot be derived from a public book alone: the book shows what *was* there, never what *would have* filled |
| 3 | **Cancel/replace latency** | An HF maker strategy cancels constantly; latency bounds the achievable quote update rate | Measurable from published rate limits + one latency measurement WO |
| 4 | **Adverse selection measurement** | The cost that makes maker rebates illusory: fills concentrate when the market moves against the quote. **Not modelling this is how a maker model becomes fiction** | Requires fill data with subsequent price paths — i.e. **live orders** |
| 5 | **Bite proofs** | A fill model that cannot fail its own tests is not validated | 4 artifacts, exact-restore, discriminating mutations — the standard |

**Estimated WO count: 4–6.** One for observability (1), one for capture design (2), one for latency
(3), **two for adverse selection (4)** — it is the hardest and needs live orders — and one for bite
proofs (5). **Rounded up per 0.15: call it 6.**

**The blocking dependency, stated plainly: items 2 and 4 require LIVE RESTING ORDERS.** They cannot
be validated from public data at all. **So maker validation is downstream of the $100 instrument,
not upstream of it** — which inverts the natural ordering and is the single most important thing
this pricing reveals. **Park-or-build is therefore not yet a free choice**: building requires the
instrument to exist first.

**No fill model is built or assumed here.**

---

## §8 THE THREE RECORDED ARTIFACTS

Written to `docs/decisions/` so a future reader hits them where they will look.

1. **`2026-08-11-perpetuals-at-1x-amendment.md`** — the constitutional amendment.
2. **`2026-08-11-hundred-dollar-instrument-ladder.md`** — D55's three conditions.
3. **`2026-08-11-death-certificate-scoping.md`** — the scoping note.

---

## §9 THE DECISION TABLE — all figures at **$100 per-order notional**

| venue | inst. | **fees RT** | **+ gas** | **+ E[funding] 5-min hold** | **all-in RT** | min | **max concurrent @$100** | integrity | depth / cadence | maker |
|---|---|---|---|---|---|---|---|---|---|---|
| **dYdX v4** | perp | 0.100% | **0** | **+0.000%** | **0.100%** ($0.10) | **$1** | **≈100** | offset; **no canonical book**; full-node: L3 + height + finality | UNKNOWN / per block | 0.020% |
| **Hyperliquid** | perp | **0.090%** | **0** | +0.000104% | **≈0.090%** ($0.09) | $10 | 10 | **NONE** | 5 or 20 lv / ≥0.5 s | 0.030% |
| **Injective** | perp | 0.100% ¹ | 0.0003% | UNKNOWN | **≥0.100%** | UNKNOWN | UNKNOWN | **`seq` + `block_height`** | UNKNOWN / per block | **−0.010% REBATE** |
| **OKX** | perp | 0.100% | nil | UNKNOWN | **0.100%** | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 0.040% |
| **Bybit** | perp | 0.110% | nil | UNKNOWN | **0.110%** | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 0.040% |
| **Hyperliquid** | spot | 0.140% | 0 | n/a | **0.140%** | $10 | 10 | NONE | 5/20 lv | 0.080% |
| **Binance** | spot | 0.200% | nil | n/a | **0.200%** (0.150% BNB) | **$5** | **20** | UNKNOWN | UNKNOWN | 0.100% |
| **Bybit** | spot | 0.200% | nil | n/a | 0.200% | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 0.100% |
| **Binance** | **perp** | UNKNOWN | nil | UNKNOWN | — | **$100** | **1 — DISQUALIFIED on arithmetic** | — | — | — |
| **Ndax** *(CEX, ref.)* | spot | 0.400% | nil | n/a | **0.400%** | UNKNOWN | UNKNOWN | none documented | L2 via `SubscribeLevel2` | 0.200% |
| **Kraken** *(incumbent)* | spot | **1.6216%** | nil | n/a | **1.6216%** ($1.62) | UNKNOWN | UNKNOWN | **CRC32** | full book / 106.3 ms | 0.80% RT |

¹ Injective's 0.05% taker is documented as *typical* and varies by market.

### Which venue leads, on what, and what could overturn it

**dYdX v4 leads** — not on headline cost, where Hyperliquid is 0.010% cheaper, but on the two
dimensions that actually bind at $100 capital: **a $1 minimum giving ~100 concurrent positions
against Hyperliquid's 10**, and **zero baseline funding** on a cross market against Hyperliquid's
non-zero interest component. It is gas-free on trades, and its full-node stream offers L3 depth with
block-height and finality markers that no centralised feed provides. **Its cost is that the quantity
CRC32 verifies does not exist there — dYdX has no canonical book — and that the stronger integrity
route requires running a node this apparatus does not have.**

**The unknown that could overturn it: the historical funding distribution.** dYdX's baseline is zero
*because its interest component is zero*, but its **premium** component is unmeasured, and its cap
permits 1.5%/hour. **If dYdX's realised funding is materially worse than Hyperliquid's despite the
zero baseline, the ranking inverts** — and that is precisely the measurement this WO's scope
prevented me from taking. **Two read-only API calls would settle it.**

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | State + gates + corpora | HEAD `e3aad95`; 572/2 both; 6/6; both corpora verify |
| 2 | Hyperliquid contract specs | **no minimum order info on that page** |
| 3 | Hyperliquid tick/lot rules | **min order value $10**; tick and lot rules cited |
| 4 | dYdX market params (2 routes) | **min ≥$1, ~$1 increments**; exact BTC-USD quantums need an indexer query → **UNKNOWN** |
| 5 | Binance fee schedule | spot VIP0 **0.100%/0.100%**, 0.075% with BNB; **perp pair ambiguous → UNKNOWN** |
| 6 | Binance minimum notional | spot **5 USDT**; **BTCUSDT perp raised to 100 USDT** (2023-11-02) |
| 7 | Bybit fees | spot 0.1% flat; perp **maker 0.02% / taker 0.055%** |
| 8 | OKX fees | spot 0.08–0.1%; perp **0.02% / 0.05%** |
| 9 | Hyperliquid `fundingHistory` | **POST to api.hyperliquid.xyz — no static data published** |
| 10 | **Historical funding distribution** | **NOT ATTEMPTED — the only route is the RPC this WO's scope forbids.** Conflict reported |
| 11 | dYdX gas | **zero for placement and cancellation**; fees only on fills |
| 12 | Injective gas | **0.00001 INJ ≈ $0.0003/tx** |
| 13 | Injective minimums, funding, terms | **NOT OBTAINED → DECLARED UNKNOWN** |
| 14 | Bybit / OKX minimum order sizes | **NOT OBTAINED → DECLARED UNKNOWN** |
| 15 | Price impact, all venues | **NOT ATTEMPTED** — requires reading live depth (RPC) |

**Zero sockets, zero RPC calls, zero wallets, zero keys, zero accounts, zero lines of code.**

---

## §10 ACCEPTANCE

| requirement | status |
|---|---|
| Order size declared, every figure computed at it | **met** — $100 primary, $200/$10 sensitivities, 0.1 BTC retired |
| Minimums enumerated + concurrent-position arithmetic | **met** — 3 of 7 venues cited, 4 declared unknown; **Binance perps disqualified on arithmetic** |
| Funding as a distribution, or declared unknown | **DECLARED UNKNOWN with cause** — the WO's scope forbids the only route. **Straddle derivation stated and computed** |
| Gas per venue as % of size + break-even | **met** — and §4's own $0.50 premise retired |
| Three non-Canadian venues scored | **met**, with gaps declared |
| Hyperliquid integrity design + what each cannot detect | **met** — 7 mechanisms, verdict: **consistency, not correctness** |
| Maker validation priced | **met** — 4–6 WOs, rounded to 6; **blocked on live orders** |
| Amendment, ladder, scoping note recorded | **met** — three artifacts in `docs/decisions/` |
| `git diff -- src/` empty | **met** |
| No socket/RPC/wallet/key/account | **met** |
| Gates green | **met** |

---

# ADDENDUM — §3.2 MEASURED under the narrow scope amendment; Binance withdrawn

**Two changes from the lead/operator, both applied:**

1. **Scope amendment (granted):** read-only public retrieval permitted **for historical funding
   rates only** — `POST api.hyperliquid.xyz/info {"type":"fundingHistory"}` and dYdX's indexer
   equivalent. **Nothing else changed.** No socket, wallet, key, account, order-path call, or code.
   **The permission was not extended** to price impact, depth, or anything else; those remain
   DECLARED UNKNOWN exactly as reported.
2. **Binance withdrawn as a venue candidate**, by **operator decision**.

**API calls made: 19 to Hyperliquid, 18 to dYdX. All `fundingHistory` / `historicalFunding`. Nothing
else was called.**

---

## BINANCE — WITHDRAWN, and the record must say by whom

**The exclusion is OPERATOR-DIRECTED, not a technical finding.** It is recorded as such so a future
reader does not mistake it for evidence. Binance was not measured and found wanting on the
dimensions that removed it; it was withdrawn as a candidate.

**Two things survive the withdrawal and are unaffected:**

- **The perps disqualifier on arithmetic stands independently.** Binance raised the BTCUSDT
  perpetual minimum notional from 5 to 100 USDT (2023-11-02), which permits exactly one position at
  $100 capital. That finding was reached on cited numbers before the withdrawal and **remains in the
  record on its own merits.** It would disqualify Binance perps at this capital regardless of the
  operator's decision.
- **Binance's historical data remains ADMITTED as the bridge basis. WO-061's verdict is untouched.**
  229/229 files checksum-verified, nine years of BTCUSDT, bridged to our own capture at r = 0.999103
  (240m). **Venue candidacy and data admissibility are different questions**, and only the former is
  withdrawn.

---

## §3.2 THE FUNDING DISTRIBUTION — MEASURED

**One year, 8,760 hourly observations per venue — complete coverage, no gaps.** Thresholds and the
mechanism were declared before the data was fetched (see `funding_dist.py` header).

| | **Hyperliquid BTC perp** | **dYdX v4 BTC-USD perp** |
|---|---|---|
| n | **8,760** | **8,760** |
| cap | 4.00%/h | 1.50%/h |
| signed min | −0.006939%/h | **−0.024337%/h** |
| signed median | **+0.001250%/h** | +0.000150%/h |
| signed p95 / p99 | +0.001250% / +0.002469% | +0.003063% / +0.005588% |
| signed max | +0.023266%/h | +0.011325%/h |
| **\|rate\| median** | **0.001250%/h** | **0.000987%/h** |
| **\|rate\| p95** | **0.001363%/h** | **0.005250%/h** |
| **\|rate\| p99** | **0.003003%/h** | **0.008988%/h** |
| **\|rate\| max** | **0.023266%/h** | **0.024337%/h** |
| max as % of cap | **0.582%** | **1.623%** |
| hours ≥ 1% of cap | **0** | 8 (0.0913%) |
| hours ≥ 10% of cap | **0** | **0** |
| **hours ≥ 50% of cap ("approached")** | **0** | **0** |
| hours at exactly 0 | 0.00% | **3.60%** |

### THE CAP SCENARIO DID NOT MATERIALISE — my own §3 concern, retired on evidence

WO-064 warned that *"at the cap, funding dominates immediately"* — a one-minute Hyperliquid hold at
4%/h would cost 0.0667%, 74% of the entire fee round trip.

**In 8,760 hours neither venue came within 10% of its cap.** Hyperliquid's worst hour reached
**0.582% of cap**; dYdX's **1.623%**. The mechanical worst case was correct arithmetic about a state
that **did not occur once in a year.**

*Falsifier, stated: a volatility regime outside this window — a liquidation cascade or a funding
squeeze — could still reach the cap, and one year of BTC data does not exclude it. What is now
established is that the cap scenario is rare, not that it is impossible.*

### The "same quantity" falsifier was checked and did NOT fire

I declared that the mechanism claim would be falsified by a venue's observed floor disagreeing with
its documented interest component. **Hyperliquid's median is exactly +0.001250%/h — precisely the
documented 0.01%/8h interest component.** Corroborated. And dYdX's **3.60% of hours at exactly zero**
is what a 0% interest component with zero premium predicts. **Both venues' published mechanics match
their published data.**

---

## §3.3 RECOMPUTED — expected funding at $100, from measured rates

`E[cost] = (D/60) × rate`, the straddle derivation unchanged.

| hold | P(straddle) | HL median | HL p95 | HL p99 | **HL max** | dYdX median | dYdX p95 | dYdX p99 | **dYdX max** |
|---|---|---|---|---|---|---|---|---|---|
| **1 min** | 1.7% | 0.00002% | 0.00002% | 0.00005% | 0.00039% | 0.00002% | 0.00009% | 0.00015% | 0.00041% |
| **5 min** | 8.3% | 0.00010% | 0.00011% | 0.00025% | 0.00194% | 0.00008% | 0.00044% | 0.00075% | 0.00203% |
| **15 min** | 25.0% | 0.00031% | 0.00034% | 0.00075% | 0.00582% | 0.00025% | 0.00131% | 0.00225% | 0.00608% |
| **60 min** | 100% | 0.00125% | 0.00136% | 0.00300% | 0.02327% | 0.00099% | 0.00525% | 0.00899% | **0.02434%** |

**Against fee round trips of 0.090% (HL) and 0.100% (dYdX):**

- At **HF durations (1–15 min)**, funding at p99 is **0.06% to 2.3% of the fee round trip.**
- At the **worst observed hour of the year**, a 60-minute hold costs **26% of the fee round trip on
  dYdX** and **26% on Hyperliquid.**
- **Funding never exceeded the fee round trip at any duration, at any percentile, in a full year.**

---

## THE SPECIFIC QUESTION ANSWERED

> *Does dYdX's realised funding stay below Hyperliquid's, or does the ranking invert?*

**It inverts at the tail and not at the median — and by my own pre-declared criterion, that counts
as an inversion.**

| statistic | Hyperliquid | dYdX | verdict |
|---|---|---|---|
| \|rate\| median | 0.001250%/h | **0.000987%/h** | **dYdX LOWER** |
| \|rate\| p95 | **0.001363%/h** | 0.005250%/h | **dYdX HIGHER — 3.9×** |
| \|rate\| p99 | **0.003003%/h** | 0.008988%/h | **dYdX HIGHER — 3.0×** |
| \|rate\| max | **0.023266%/h** | 0.024337%/h | **dYdX HIGHER — 1.05×** |

**Why, mechanically.** dYdX's **zero interest component** gives it a lower *median* — it sits at
exactly zero 3.60% of the time, which Hyperliquid never does because its 0.00125%/h interest floor
pins it above zero. **But dYdX's premium component is more volatile**, so its tail is worse.
**Hyperliquid's `clamp(interest − premium, ±0.0005)` term bounds how far the rate can move from the
interest component**, and that clamp is visible in the data: Hyperliquid's p95 sits at its median
(+0.001250%) while dYdX's p95 is 5× its median. **The clamp is doing exactly what it is documented
to do.**

**And the answer that matters: it does not change the decision.** Both tails are so small relative
to fees that the inversion is real but not material.

```
all-in round trip at $100, 15-minute hold, p99 funding:
  Hyperliquid : 0.090% + 0.00075% = 0.09075%
  dYdX v4     : 0.100% + 0.00225% = 0.10225%
difference: 0.0115% -- the SAME 0.010% fee gap that existed before funding was measured
```

**Funding moved the gap by 0.0015 percentage points.** The measurement's value is that it
**removes an unknown**, not that it changes an answer — and removing it is what the WO existed to do.

---

## §9 RESTATED — decision table, Binance removed, funding measured

All figures at **$100 per-order notional**; funding at **p99, 15-minute hold** (the target HF band).

| venue | inst. | fees RT | gas | **+funding p99@15m** | **all-in RT** | min | **concurrent @$100** | integrity | maker |
|---|---|---|---|---|---|---|---|---|---|
| **Hyperliquid** | perp | **0.090%** | 0 | +0.00075% | **0.09075%** ($0.091) | $10 | 10 | **NONE** | 0.030% |
| **dYdX v4** | perp | 0.100% | 0 | +0.00225% | **0.10225%** ($0.102) | **$1** | **≈100** | offset; **no canonical book**; full-node L3 + height + finality | 0.020% |
| **Injective** | perp | 0.100% ¹ | 0.0003% | **UNKNOWN** | **≥0.1003%** | UNKNOWN | UNKNOWN | **`seq` + `block_height`** | **−0.010% REBATE** |
| **OKX** | perp | 0.100% | nil | UNKNOWN | ≥0.100% | UNKNOWN | UNKNOWN | UNKNOWN | 0.040% |
| **Bybit** | perp | 0.110% | nil | UNKNOWN | ≥0.110% | UNKNOWN | UNKNOWN | UNKNOWN | 0.040% |
| **Hyperliquid** | spot | 0.140% | 0 | n/a | **0.140%** | $10 | 10 | NONE | 0.080% |
| ~~Binance~~ | — | — | — | — | **WITHDRAWN — operator decision** | — | — | — | — |
| **Ndax** *(CEX, ref.)* | spot | 0.400% | nil | n/a | 0.400% | UNKNOWN | UNKNOWN | none documented | 0.200% |
| **Kraken** *(incumbent)* | spot | **1.6216%** | nil | n/a | **1.6216%** ($1.62) | UNKNOWN | UNKNOWN | **CRC32** | 0.80% RT |

¹ Injective's 0.05% taker is documented as *typical* and varies by market.

### THE LEADER — restated

**dYdX v4 still leads, and the funding measurement did not change that — it strengthened the basis
for saying so.**

Hyperliquid is **0.0115% cheaper all-in** at the target hold duration. dYdX gives **~100 concurrent
positions against 10**, and a real integrity route via full-node streaming. **At $100 capital,
concurrency is the binding constraint and 0.0115% is $0.0115 per round trip** — one cent. **The
ordering is unchanged and now rests on measured funding rather than an unmeasured one.**

**What could still overturn it, updated:**

- **Price impact at $100** — still **DECLARED UNKNOWN** for every venue, still requiring a depth read
  the scope does not permit. **This is now the ONLY unmeasured term in the cost stack**, and at a
  0.0115% margin between the leaders it is more than large enough to decide between them.
- **Injective remains unscored** on minimums, funding and depth — and it is the only venue paying a
  **maker rebate**, which §7 showed dominates venue choice.
- **dYdX's integrity semantics**: the book has no canonical form, so a corpus captured there records
  the indexer's view rather than the matching state. **That is a semantics problem, and semantic
  mismatches are silent.**

**One sentence:** dYdX v4 leads on concurrency and integrity at a one-cent cost penalty per round
trip; **the unknown that could still overturn it is price impact at $100**, which is now the last
unmeasured term and needs one depth read per venue.
