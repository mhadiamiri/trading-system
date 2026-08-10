# WO-063 — VENUE RE-SCORE: three order-book DEXs, spot and perps

**Report only. No socket, no RPC, no wallet, no key, no account, no code.** Every figure is cited or
declared-with-derivation; anything unobtainable is **DECLARED UNKNOWN**, never estimated.

**The headline answer, up front, because §5 says not to bury it.**

**Funding does NOT erode the perps fee advantage in calm conditions — it is negligible.** A 4-hour
BTC hold costs **0% funding on dYdX** (cross-market interest component is zero) and **~0.005% on
Hyperliquid**, against fee round-trips of 0.090–0.100%. So the fee lever survives the funding test.

**But the tail is the finding.** Both venues cap funding at levels that dwarf the entire fee saving:
a 4-hour hold could cost up to **16% on Hyperliquid** and **6% on dYdX** at the published caps —
**60× to 170× the whole round-trip fee advantage.** The empirical distribution is **DECLARED
UNKNOWN**: obtaining it needs an API call this WO forbids. *A mean funding rate says nothing about
a bad day, and I do not have the bad days.*

**And the correction WO-062 needed:** dYdX is reinstated and it is **not** the weakest candidate on
the dimension that matters most. Its integrity story is the richest of the three — and stranger than
"has a checksum or doesn't."

---

## §1 STATE CONFIRMED

| | |
|---|---|
| HEAD | **`0fd82cd`** (actual, not pinned) |
| `git diff -- src/` | **empty** |
| pytest 3.14.6 | **572 passed, 2 skipped** (315.99 s) |
| pytest 3.11.15 | **572 passed, 2 skipped** (313.49 s) |
| import-linter | **6 kept, 0 broken** |
| `corpus_20260805` | `e3ab1aec…` · **38/38**, 0 mismatched |
| `validation_20260809` | `884f9f00…` · **3/3**, 0 mismatched |

**`phaseb_20260809` — informational, not disturbed. Leg 2 closed cleanly during this WO.**

```
run 20260810040133   04:02:38Z -> 16:02:44Z   12.000 h   13 segments   1,287,221 frames
corpus total         23.9984 covered hours    seam 1 (9.506 h)   host_suspend_events 0
corpus_verify        26/26 segments match their capture-time SHA-256
gaps                 2, both VENUE_CONNECTION_CLOSED, 3.88 s and 1.90 s, both resumed=true
                     terminal=false   checksum_failures_total 0
```

Both gaps are the ledger doing its job — recorded, bounded, resolved. **No capture is running now.**

---

## §2 THE CANDIDATE SET — and Injective is scoreable after all

WO-062 could not score Injective: `docs.ts.injective.network` 301'd and the landing page carried no
schema. §2 directed alternative routes. **They worked** (0.11 — the search's extent, enumerated):

| # | route | result |
|---|---|---|
| 1 | `docs.injective.network` landing | no schema, no integrity, no fees — as before |
| 2 | **`InjectiveLabs` GitHub org, 100 public repos** | located `injective-proto`, `sdk-python`, `sdk-go`, `injective-ts`, `api-exchange-docs` |
| 3 | **`injective-proto` tree, 640 files** | `injective/stream/v2/query.proto`, `injective/exchange/v2/orderbook.proto` |
| 4 | **raw protobuf definitions** | **DECISIVE — the integrity primitives are declared in the schema** |
| 5 | `docs.helixapp.com/trading/fees-and-rebates` | fee figures obtained |

**Injective is scored below on the strength of its own committed protobuf**, which is a stronger
citation than any rendered doc page — it is the wire contract itself.

**AMMs and aggregators remain out of scope as venues**, reason unchanged from WO-062: no resting
book to capture, no L2 depth, no maker/taker distinction in our sense.

---

## §3.1 ALL-IN COST AT 0.1 BTC (~$6,460) — SPOT AND PERPS SEPARATELY

**0.16 statement, and there are two comparisons inside one table.** *(a)* Across venues: all fees
are percentage-of-notional, so they are commensurable — but the **instruments differ** (Kraken BTC/USD
spot, Hyperliquid UBTC/USDC spot, three BTC perps), and that difference is declared, not folded in.
*(b)* **Spot vs perps is a second comparison of unlike quantities inside the same table**: a spot
position has **no time-dependent cost**; a perp position pays funding for every hour held. They are
only comparable once a holding period is fixed — which is why the 4-hour column exists.

### Entry-tier fees — the tier a zero-volume account can actually claim

| venue | instrument | maker | **taker** | **round trip (taker/taker)** | at 0.1 BTC |
|---|---|---|---|---|---|
| **Kraken** (incumbent, in-tree) | spot BTC/USD | 0.40% | **0.80%** | **1.6216%** ¹ | **$104.76** |
| **Hyperliquid** | spot UBTC | 0.040% | **0.070%** | **0.140%** | $9.04 |
| **Hyperliquid** | **BTC perp** | 0.015% | **0.045%** | **0.090%** | **$5.81** |
| **dYdX v4** | **BTC-USD perp** | 1.0 bps | **5.0 bps** | **0.100%** | $6.46 |
| **Injective / Helix** | spot + perp | **−0.005%** (rebate) | **0.05%** | **0.100%** | $6.46 |

¹ Kraken's 1.6216% is the in-tree figure: 2×0.80% cited fee + 2×1 bp measured slip + 0.0016%
measured spread. The others are **fees only** — slip and spread are not measured for them.

**Tiers claimable, not advertised** — the Tier 1 lesson applied to all four:

- Kraken's table has **17 tiers**; best (Pro 5, 0.05%/0.00%) needs **$500M** volume and **$100M**
  on-platform. `ASSUMED_TIER = "Tier 1"`, source `kraken.com/features/fee-schedule`, retrieved
  2026-08-07.
- Hyperliquid Tier 0 is **$0 volume**; best tier needs **>$7B**.
- **dYdX Tier 1 is `< $1M` 30-day volume** — a genuinely low bar, and the only venue here whose
  entry tier is not the worst-case bottom of a steep ladder. Tiers: 5.0/4.5/4.0/3.5/3.0/2.5/2.5 bps
  taker.
- Injective/Helix: *"Trading fees on Injective are typically set to: Maker Fee: −0.005%, Taker Fee:
  0.05%"*. **Flagged**: Helix documents these as *typical* and fees **vary by market**; separately
  the exchange module's protocol minimums are quoted elsewhere as 0.1% maker / 0.2% taker. **The
  effective rate for a specific BTC market is DECLARED UNKNOWN** pending a per-market lookup.

### THE NEW COST SHAPE — FUNDING

```
fee      ∝ NOTIONAL                      per trade      (our model has this)
gas      = FIXED per transaction                        (WO-062 flagged this)
funding  ∝ NOTIONAL × TIME HELD                         (NOTHING in our model has a time dimension)
```

| | **Hyperliquid** | **dYdX v4** | **Injective** |
|---|---|---|---|
| interval | **every hour** | **every hour** | **DECLARED UNKNOWN** |
| formula | `F = avg premium + clamp(interest − premium, −0.0005, +0.0005)`, paid hourly at **⅛** of the 8-h rate | `rate = (premium / 8) + interest`, `premium = (max(0, impactBid − index) − max(0, index − impactAsk)) / index` | **DECLARED UNKNOWN** |
| premium sampling | every **5 s**, averaged over the hour | median vote per **1-minute** sample, averaged over the **1-hour** tick | UNKNOWN |
| interest component | **0.01% / 8 h = 0.00125% / h** (11.6% APR, paid to short) | **0% for cross markets**; 0.125 bps/h for isolated | UNKNOWN |
| **cap** | **4% / hour** | 8-h rate capped at `600% × (IMF − MMF)`; for BTC (5% IMF, 3% MMF) = **12% / 8 h ≈ 1.5% / h** | UNKNOWN |

**A 4-hour hold, calm market (interest component only, zero premium):**

```
Hyperliquid : 0.00125%/h × 4 = 0.005%
dYdX (BTC-USD is a CROSS market, interest = 0%) : 0.000%
```

**A 4-hour hold at the published cap:**

```
Hyperliquid : 4%/h × 4    = 16%     <- 178x the entire 0.090% fee round trip
dYdX        : 1.5%/h × 4  =  6%     <-  60x the entire 0.100% fee round trip
```

**IS FUNDING LARGE OR SMALL RELATIVE TO THE FEE ADVANTAGE? Both, and which one depends on the day.**
In calm conditions it is **negligible — 0% to 0.005% against a 0.09–0.10% round trip.** At the caps
it is **two orders of magnitude larger than the entire fee saving.** The honest statement is that
funding does not erode the advantage *on average* and can annihilate it *in the tail*.

**The empirical distribution is DECLARED UNKNOWN.** §3.1 asked for published historical BTC funding
rates as a distribution. Both venues expose them through their APIs (`fundingHistory` on
Hyperliquid; historical funding on dYdX's indexer) — **and querying either is the RPC call this WO
forbids.** No estimate is offered in its place. **This is the single highest-value measurement a
follow-on WO could take, and it is one API call per venue.**

### Gas, price impact, failed transactions

| | Hyperliquid | dYdX v4 | Injective |
|---|---|---|---|
| gas on trades | **zero** — *"Trading on Hyperliquid is gas-free"* | **DECLARED UNKNOWN** (Cosmos chain; gas exists for txs, rate not obtained) | **DECLARED UNKNOWN** |
| deposit/withdraw cost | *"there may be small gas fees"* — amount **UNKNOWN** | UNKNOWN | UNKNOWN |
| failed-tx cost | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** |
| **price impact at 0.1 BTC** | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** |

**Price impact is unknown for all three by construction**: it requires reading published L2 depth,
which requires an RPC/socket call this WO forbids. **It remains the largest open term in the whole
comparison** — the fee saving against Kraken is ~$95–99 per round trip, and impact on a shallow book
could exceed that.

### Leverage and liquidation — recorded, not modelled (§3.1's instruction)

dYdX BTC-USD: **initial margin 5%, maintenance margin 3%** (cited via the funding-cap worked
example). Hyperliquid and Injective: **DECLARED UNKNOWN**. Liquidation is a risk-layer concern with
**no counterpart in spot**, and it is noted here as a fact for a future risk-layer WO. **Not
modelled here.**

---

## §3.2 FEED INTEGRITY — and dYdX turns out to be the interesting one

### Hyperliquid — **no mechanism**

`{"type":"l2Book","coin":"..."}` → `WsBook{coin, levels:[bids,asks], time}`. **No checksum, no
sequence number, no version.** As WO-062 recorded: `checksum_failures_total` could never move, and
**a metric that cannot move is not a metric.**

Mitigating, honestly: it is a **snapshot** feed, so there is no locally-reconstructed state to
drift — the failure mode CRC32 guards against largely does not arise. **What it cannot do is prove
the snapshot you got is the book the venue had.**

### dYdX v4 — **an ordering primitive, and the absence of the thing a checksum would check**

**Indexer WebSocket** (`{"type":"subscribe","channel":"v4_orderbook","id":"BTC-USD"}`): levels are
`[price, size, offset]`. The **offset is a logical sequence** — *"each websocket update has a
message-id which is a logical offset to use."*

**But the deeper finding is why that offset exists**, and it is quoted directly:

> *"there is no centralized order book"* … *"The 'correct' order book at any given time is whatever
> the current block proposer has in its mempool, which is not what the indexer or the front end can
> directly see."* … *"The block proposer changes every block, so there is a new canonical mempool,
> and therefore, a new canonical order book every block."*

**dYdX does not have one book to checksum.** The indexer's view can be **crossed** (bid ≥ ask) as a
normal condition, and clients are expected to run a documented **uncrossing algorithm** locally,
discarding the side with the lower offset.

**This is not "weaker than CRC32". It is a different world.** Kraken's checksum answers *"does my
reconstruction match the venue's book?"* — **on dYdX v4 that question has no referent.** A corpus of
dYdX book states would faithfully record *the indexer's view*, which is explicitly not the matching
state. **That is a corpus-semantics problem, not a corpus-integrity one, and it is worse**, because
integrity failures are loud and semantic mismatches are silent.

**Full-node gRPC streaming — genuinely stronger, at a price.** §3.2 asked whether chain state
provides a primitive stronger than a checksum. **It does:**

- **L3 order-level** book updates — *more* than Kraken's L2.
- **Block height on every update.**
- **An `execMode` field**: *"Only `ClobMatch` messages with `execModeFinalize` are trades confirmed
  by consensus."* — **you can distinguish consensus-finalised from optimistic**, which no
  centralised feed offers at all.
- **A snapshot flag** to sync: *"Discard order messages until you receive a `StreamOrderbookUpdate`
  with `snapshot` set to `true`."*

**What it does NOT guarantee**, stated plainly: **exactly-once delivery is not guaranteed** —
*"If the buffer reaches maximum capacity, all connections and updates are dropped."* And
**you must run your own full node**: *"We recommend you use this exclusively with your own node."*
That is infrastructure this apparatus does not have and has never costed.

### Injective — **a sequence number AND a block height, declared in the wire contract**

From `injective/stream/v2/query.proto`, quoted from the committed protobuf:

```protobuf
message StreamResponse {
  uint64 block_height = 1;                        // the block height
  int64  block_time   = 2;                        // the block time
  repeated OrderbookUpdate spot_orderbook_updates = 9;
  ...
}
message OrderbookUpdate {
  uint64 seq = 1;          // "the sequence number of the orderbook update"
  Orderbook orderbook = 2;
}
```

**An explicit per-orderbook `seq`, plus chain block height and block time on every response.**
**No checksum field** — searched, absent from both `stream/v2/query.proto` and
`exchange/v2/orderbook.proto`.

### Integrity verdict, three venues

| | ordering primitive | canonical book exists? | verifiable against chain? |
|---|---|---|---|
| Kraken (incumbent) | implicit in delta order | **yes** | n/a — **CRC32 proves agreement** |
| **Hyperliquid** | **none** | yes (venue-internal) | no |
| **dYdX v4** indexer | **offset** (logical) | **NO — per-block-proposer mempool** | no |
| **dYdX v4** full node | **block height + execMode** | finalised state, yes | **yes, with your own node** |
| **Injective** | **`seq` + `block_height`** | yes (chain state) | **yes** |

**What a substitute covers and what it does not.** A sequence number proves you did not *miss* an
update. **It does not prove the update you received is correct**, and it cannot detect a venue-side
error. Only a checksum over the book state does that, and only Kraken publishes one. **Injective's
`seq` + `block_height` is the closest of the three to a real substitute**, because the book is
derivable from committed chain state and is therefore independently re-derivable — the strongest
form of *"independent re-derivation"* §3.2 asks about.

---

## §3.3 DEPTH AND CADENCE — and the threshold we would need

| | depth published | cadence |
|---|---|---|
| Kraken (incumbent) | full book | **106.3 ms** measured |
| Hyperliquid | **5 levels (fast) or 20 (slow)** | **≥ 0.5 s** |
| dYdX indexer | **DECLARED UNKNOWN** — level count not stated in the docs read | UNKNOWN |
| dYdX full node | **L3, full order-level** | per block |
| Injective | **DECLARED UNKNOWN** — the proto carries a repeated level list with no documented cap | per block |

**The threshold, stated as §3.3 requires.** Our depth-dependent quantities are the quoted spread,
touch depth, and the measured slippage that feeds the 1 bp term in the 1.6216% round trip. Spread
and touch depth need **only level 1** and port anywhere. **Slippage at 0.1 BTC is the binding
constraint**: to compute it we must walk the book until cumulative size ≥ 0.1 BTC. On
`corpus_20260805` the measured touch quantities are order 0.01–5 BTC per side, so **0.1 BTC is
frequently filled within the first few levels but not reliably at level 1.**

**Declared threshold: 10 levels per side minimum, 20 preferred**, rounded up per 0.15. Hyperliquid's
**slow feed at 20 levels clears it; its fast feed at 5 does not.** *Falsifier: a measured slippage
walk on `corpus_20260805` showing >10 levels are routinely consumed by 0.1 BTC would raise this
threshold — that measurement is available in-tree and has not been run.*

---

## §3.4 API AND SIGNING MATURITY

| | Hyperliquid | dYdX v4 | Injective |
|---|---|---|---|
| rate limits | **cited**: 1200 wt/min REST per IP; `l2Book` weight 2; **10** WS connections, **1000** subscriptions, **2000** msg/min; **1000** open orders/address (+1 per $5M, cap 5000) | **DECLARED UNKNOWN** | **DECLARED UNKNOWN** |
| SDKs | documented, multiple | TS/Python indexer clients | **`injective-ts`, `sdk-go`, `sdk-python`, `injective-proto`** — enumerated on GitHub |
| testnet | **yes** (`api.hyperliquid-testnet.xyz`) | yes | yes |
| **local signing required** | **yes** | **yes** | **yes** |

**All three require local transaction signing. Flagged as an architecture question, not resolved.**
Three consequences, restated because they are unchanged and still load-bearing:

- **A signing key is not a revocable session credential.** A compromised API key is revoked by the
  venue; a compromised signing key is a compromised wallet.
- **`no_credential` preflight would not see it.** Its check is literally *"No credentials in .env"* —
  verified in this session's own preflight output. It scans `.env` for API credentials and **would
  not detect a signing key at all.** It needs rebuilding, not re-pointing.
- **The one-module swap assumption holds for reading, not for signing.** Reading is venue-abstracted;
  signing is not an adapter concern in the current architecture.

---

## §3.5 THE 14-PLATFORM CANADIAN CEX FEE SWEEP

Source enumeration: OSC `crypto-businesses` page, HTTP 200, **self-dated 2026-07-30**, retrieved
2026-08-10. **VirgoCX excluded — registration SUSPENDED effective 2025-11-24** per the same table;
it appears in the OSC's *not currently registered* list, so it is not a candidate.

**Sorted by entry-tier taker fee. Kraken marked as incumbent.**

| # | platform | **entry taker** | maker | cost mechanism | public WS L2 feed? |
|---|---|---|---|---|---|
| 1 | **Ndax Canada** | **0.20% flat** | 0.20% (no maker/taker split) | *"flat 0.20% trading fee… **There are no volume tiers**"*; *"You trade at the displayed order-book price, with the 0.20% commission charged on top"* | **YES — `SubscribeLevel2`**, configurable depth |
| 2 | Coinsquare / **Bitbuy** (Pro) | **0.50%** | 0.50% | published tiers; best tier ($5M+) 0.10% taker / 0% maker | **UNKNOWN** |
| 3 | **Kraken** *(incumbent)* | **0.80%** | 0.40% | 17-tier published schedule | **YES — with CRC32** |
| 4 | Coinbase Canada (Advanced) | **0.60%** *(derived)* | 0.40% *(derived)* | published **range** taker 0.04–0.60%, maker 0.00–0.40%; fee page 403s without sign-in | UNKNOWN |
| 5 | Bitbuy **Express** | **NO FEE — SPREAD** | — | *"generates trade quotes using a **spread** which allows us to eliminate trading fees"* — **spread not published** | UNKNOWN |
| 6 | **Shakepay** | **NO FEE — SPREAD** | — | *"Shakepay makes money by applying a **spread**, which allows us to eliminate commission fees"* — **spread not published** | UNKNOWN |
| 7 | **Wealthsimple** | **NO COMMISSION — SPREAD** | — | *"If you're trading crypto in CAD, you won't pay any commission fees"* — **spread not published** | UNKNOWN |
| 8 | Newton Crypto | **DECLARED UNKNOWN** | — | page advertises *"Trading fees and asset tiers"*; figures not retrievable from the page fetched | UNKNOWN |
| 9 | Netcoins | **DECLARED UNKNOWN** | — | **fee page returned HTTP 522** (their server) on two attempts | UNKNOWN |
| 10 | Crypto.com (Foris DAX CAN) | **DECLARED UNKNOWN** | — | fees page returned **133 bytes** — JS-rendered, no content | UNKNOWN |
| 11 | Webull Canada Crypto | **DECLARED UNKNOWN** | — | page advertises *"$0 Commission"* for **equities**; crypto schedule not surfaced | UNKNOWN |
| 12 | Satstreet | **DECLARED UNKNOWN** | — | 1,771-byte page; **OTC desk**, not a retail order-book venue | UNKNOWN |
| 13 | Cybrid Canada | **N/A** | — | **B2B embedded-finance infrastructure**, not a retail trading venue; also *Ontario only* | UNKNOWN |
| 14 | Fidelity Clearing Canada / Fidelity Digital Asset Services | **DECLARED UNKNOWN** | — | institutional; no public retail schedule | UNKNOWN |
| — | ~~VirgoCX~~ | **EXCLUDED** | — | **registration suspended 2025-11-24** | — |

### THE ANSWER TO §3.5's QUESTION

**Which platforms are materially cheaper than Kraken AND have a capturable feed? Exactly one: Ndax.**

**Ndax at 0.20% flat is 4× cheaper than Kraken's 0.80% Tier 1** — a round trip of **0.400%** against
**1.6216%**, saving **~$79 per 0.1 BTC round trip** with **zero DEX integration work**. And it is
capturable: `SubscribeLevel2` provides an L2 book over WebSocket with specifiable depth.

**Three caveats, all material and none of them estimated away:**

1. **No integrity mechanism found.** No checksum or sequence number is documented on the Ndax L2
   feed. It would land in the same category as Hyperliquid.
2. **Market data may require an account.** *"Only a user with Operator permission can issue a
   Level2MarketData permission"* — whether public market data is available unauthenticated is
   **DECLARED UNKNOWN**, and this WO cannot open an account to find out.
3. **The flat fee is the whole published cost** — *"charged on top and shown before you place the
   order"* — so unlike the spread platforms, the cost is determinable. That is itself the finding.

### THE SPREAD-EMBEDDING FINDING — §3.5's trap, and three platforms are in it

**Bitbuy Express, Shakepay and Wealthsimple all advertise zero commission and embed their cost in an
undisclosed spread.** Each says so in its own words, quoted above. **None publishes the spread.**

**Their real cost is not determinable from published documents. That is a finding about the venue,
not a gap in this report.** §3.5 anticipated exactly this: *"a 0% fee with an embedded 1% spread is
more expensive than Kraken."* At a 1% spread, a round trip would cost **2%** — worse than Kraken's
1.6216%. At 0.25% it would beat Ndax. **We cannot tell which, and neither can any customer**, which
is the point.

**BTC/CAD vs BTC/USD — flagged under 0.16, not folded in.** Wealthsimple's zero-commission claim is
explicitly scoped to *"trading crypto in **CAD**"*. A CAD-quoted venue introduces an **FX leg**,
which is a **different quantity** from a USD-quoted fee and must not be added to it. Per-platform
pair availability is **DECLARED UNKNOWN** for most of the table.

**Scope limit, restated per §3.5:** the OSC table is **Ontario-scoped** — *"exemptive relief to offer
crypto products to investors in Ontario."* A platform registered elsewhere in Canada but not in
Ontario would not appear. **Authoritative for Ontario; not established Canada-wide.** Per 0.18 this
is recorded, not scored.

---

## §4 JURISDICTION — RECORDED, NEVER SCORED (0.18)

One factual line each. **No venue is penalised, ranked down, or excluded on this basis, and no VPN
path is proposed or evaluated.**

- **Hyperliquid**: its Terms of Use define Restricted Persons to include those in **the United States
  and Ontario, Canada**, and prohibit disguising location. The Terms restrict *the Interface*;
  protocol access via self-custody is a distinct question, **recorded and not adjudicated**.
- **dYdX v4**: publishes software terms with restricted-jurisdiction provisions; **the specific list
  is DECLARED UNKNOWN** — not retrieved in this pass.
- **Injective / Helix**: **DECLARED UNKNOWN** — terms not retrieved.
- **Ndax, Kraken and the other OSC-registered CEXs**: registered to serve Ontario investors, which
  is what the OSC table certifies.

---

## §5 OUTPUT — THE COMPARISON THAT MATTERS

**All-in round-trip cost at 0.1 BTC, including funding for a 4-hour hold on the perps rows,
against Kraken Tier 1's 1.6216%:**

| venue | instrument | fees | + 4 h funding (calm) | **all-in** | **vs Kraken** |
|---|---|---|---|---|---|
| **Kraken** | spot | 1.6216% | n/a | **1.6216%** | — |
| **Hyperliquid** | **BTC perp** | 0.090% | +0.005% | **≈ 0.095%** | **17.1× cheaper** |
| **dYdX v4** | **BTC-USD perp** | 0.100% | **+0.000%** | **0.100%** | **16.2× cheaper** |
| **Injective** | perp | 0.100% ¹ | **UNKNOWN** | **≥ 0.100%** | ≥16.2× *(funding unknown)* |
| **Hyperliquid** | spot UBTC | 0.140% | n/a | **0.140%** | 11.6× cheaper |
| **Ndax** | **spot BTC** | 0.400% | n/a | **0.400%** | **4.1× cheaper, TODAY, no integration** |

¹ Injective's rate is documented as *typical* and varies by market — treat as provisional.

**At the published funding caps, the perps rows become 16.09% and 6.10% respectively** — *worse than
Kraken by an order of magnitude.* Both numbers are in the same table because both are true; which one
applies depends on the day, and **the distribution that would tell us how often is DECLARED UNKNOWN.**

### Which venue wins which dimension

- **Cost (calm): Hyperliquid perp**, marginally over dYdX. The gap between them (0.095% vs 0.100%)
  is **smaller than the unmeasured price-impact term**, so this ranking is not yet meaningful.
- **Feed integrity: Injective**, on `seq` + `block_height` in a committed wire contract, with the
  book derivable from chain state. **dYdX full-node streaming is arguably stronger still** (L3 +
  execMode + finality) but requires running a node. **Hyperliquid is last, with nothing.**
- **Depth and cadence: dYdX full node** (L3) — but only via self-hosted infrastructure. Among public
  feeds, **Hyperliquid's 20-level slow feed is the only one whose depth is documented at all**, and
  it clears the declared 10-level threshold while its 5-level fast feed does not.
- **Fee-lever available today with zero integration: Ndax**, 4× cheaper than the incumbent, on a
  registered Ontario venue, with an L2 WebSocket feed.
- **Nobody wins on integrity in Kraken's sense.** No candidate publishes a book checksum. On dYdX
  the quantity a checksum verifies **does not exist**.

### Where the trade-offs sit

The fee lever is real — **16–17× on perps, 11.6× on DEX spot, 4× on Ndax spot** — and it survives
funding in calm conditions. What it costs is: **integrity** (no checksum anywhere), **instrument
identity** (UBTC is not BTC; a perp is not spot), **a new time-dimension cost shape** our model
cannot express, **an unmeasured price-impact term** that could exceed the entire saving, and, for
the DEXs, **a signing architecture** the preflight cannot see.

**The most consequential thing this WO can say: the cheapest credible step is also the smallest
one.** Ndax needs no DEX adapter, no signing path, no funding model, and no new cost shape — and it
is 4× cheaper than the number that killed the minutes-horizon class.

**Whether the hour-scale horizon class reopens in a new fee regime is a NEW pre-registered question
for a future WO** — declared before any run — **not a re-run of the death certificate**, whose
scoping is noted and untouched.

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | State, gates, corpora | HEAD `0fd82cd`; 572/2 both; 6/6; both corpora verify |
| 2 | phase-B leg 2 close | **clean**: MANIFEST, `run_end`, 26/26 verified, 2 bounded gaps |
| 3 | dYdX indexer WS docs (3 URLs) | two 404/thin; **`how_to_uncross_orderbook` decisive** |
| 4 | dYdX full-node gRPC streaming | **L3 + block height + execMode + snapshot flag**; needs own node |
| 5 | dYdX fee tiers (3 routes) | **Tier 1 `< $1M`: taker 5.0 bps, maker 1.0 bps**; full 7-tier table |
| 6 | dYdX funding | hourly; formula, premium sampling, **cap 12%/8 h for BTC**; IMF 5% / MMF 3% |
| 7 | Hyperliquid funding | hourly at ⅛ of 8-h rate; interest 0.01%/8 h; **cap 4%/hour** |
| 8 | Injective docs landing | **no schema, no integrity, no fees** — as in WO-062 |
| 9 | **InjectiveLabs GitHub org** | 100 repos enumerated |
| 10 | **`injective-proto` tree** | 640 files; located stream + orderbook protos |
| 11 | **raw protobuf** | **`seq` + `block_height` found; no checksum field** |
| 12 | Helix fees | maker −0.005%, taker 0.05%, *typical*, varies by market |
| 13 | OSC enumeration | 14 registered; VirgoCX suspended |
| 14 | Ndax fees | **0.20% flat, no tiers**, charged on top of book price |
| 15 | Ndax API | **`SubscribeLevel2` exists**; Operator-permission caveat |
| 16 | Bitbuy fees | Pro 0.50%/0.50%; **Express = undisclosed spread** |
| 17 | Coinbase fees (2 URLs) | **403 both**; range 0.04–0.60% taker via search; base **derived** |
| 18 | Shakepay | **spread, not published** |
| 19 | Wealthsimple | **no commission in CAD, spread not published** |
| 20 | Newton / Netcoins / Crypto.com / Webull / Satstreet / Cybrid | **522, JS-only, or no crypto schedule → DECLARED UNKNOWN** |
| 21 | Price impact, all venues | **NOT ATTEMPTED** — requires the RPC call this WO forbids |
| 22 | Funding distributions | **NOT ATTEMPTED** — same reason. Named as the highest-value follow-on |

**Zero sockets, zero RPC calls, zero wallets, zero keys, zero accounts, zero lines of code.**

---

## §6 ACCEPTANCE

| requirement | status |
|---|---|
| Three DEXs attempted | **met** |
| Injective sought via enumerated alternative routes | **met — and scored**, from its committed protobuf |
| Spot and perps both scored where they exist | **met** |
| Funding characterised or declared unknown + time-dimension implication | **met** — mechanics cited, caps cited, **distribution declared unknown** |
| Feed integrity per venue incl. dYdX Cosmos primitives | **met** — incl. the finding that dYdX has no canonical book |
| Depth threshold stated | **met — 10 levels min, 20 preferred**, with its falsifier |
| Signing / preflight gap noted | **met** |
| All 14 OSC platforms swept, VirgoCX excluded | **met** — cited or DECLARED UNKNOWN per row |
| Spread-embedding practices reported | **met** — three platforms, quoted |
| Feed availability noted per venue | **met** (mostly UNKNOWN, declared) |
| Jurisdiction recorded, not scored | **met** |
| `git diff -- src/` empty | **met** |
| No socket/RPC/wallet/key/account | **met** |
| Corpora untouched, gates green | **met** |
