# WO-054 §2 — TRADE CHANNEL MERGE SCHEMA (declarative; the contract a future backtest reads)

Committed as a schema **before** the reader that will consume it exists, following the WO-014c-2
precedent: the capture and any future reader are both built to satisfy this document, so neither
inherits "whatever the capture happened to write".

---

## §2.1 THE CITATION

| Field | Value |
|---|---|
| **Source** | https://docs.kraken.com/api/docs/websocket-v2/trade |
| **Retrieved** | **2026-08-08** |
| Endpoint | `wss://ws.kraken.com/v2` — the same socket the book channel already uses (`kraken_v2_book.WS_URL`) |
| Auth | none; public channel |

**Subscribe** (as published):

```json
{"method": "subscribe",
 "params": {"channel": "trade", "symbol": ["BTC/USD"], "snapshot": false}}
```

**Unsubscribe**: `{"method":"unsubscribe","params":{"channel":"trade","symbol":["BTC/USD"]}}`

**Message payload** — every published field:

| Field | Type | Meaning (as published) |
|---|---|---|
| `symbol` | string | currency pair, e.g. `BTC/USD` |
| `side` | string | direction of the **taker** order — `buy` / `sell` |
| `qty` | float | trade size |
| `price` | float | average execution price |
| `ord_type` | string | taker order classification — `limit` / `market` |
| `trade_id` | integer | unique sequential identifier per order book |
| `timestamp` | string | RFC3339 execution time |

`type` distinguishes `snapshot` from `update`; both carry identical schemas. With
`snapshot: true` the channel first delivers "the most recent 50 trades".

**We subscribe with `snapshot: false`.** The snapshot is 50 *historical* trades that occurred
**before** capture began. Merging them into the first frame would attribute pre-capture activity to
a capture-window interval — a fabricated `trade_count` for the opening frame. Declining the snapshot
costs nothing (we want only what happens during the window) and removes the failure mode entirely.

---

## §2.3 MERGE SEMANTICS — declared

### Association: **per book frame, as a delta since the previous frame**

Trades are accumulated as they arrive and attached to the **next book frame written**. Each frame's
trade fields describe the half-open interval `(previous frame timestamp, this frame timestamp]`.

Why not the alternatives:

- **Per time bucket** would impose a bar interval *at capture time*, freezing a choice that WO-053
  demonstrated belongs to the strategy layer (the bar interval was a registered strategy parameter,
  not a property of the data). A corpus captured in 1-second buckets cannot later be read at
  100 ms.
- **A separate record stream** would force every reader to time-align two streams itself. That
  alignment is precisely where splices get introduced (the D20 family) — and unlike the book's
  discontinuities, nothing would segment it. Attaching at capture, where both streams are already
  in hand and ordered, means the reader never has to.

The cost of per-frame attachment is declared: **the interval length is the book's update cadence,
which is irregular** (~24–32 frames/s observed, but not fixed). A consumer wanting a fixed interval
must aggregate, exactly as `bars.py` already does for prices.

### The fields

Written as a `trades` sub-object on each frame, so the addition is unambiguous and a pre-WO-054
frame (no `trades` key at all) is distinguishable from a WO-054 frame that saw no trades.

```json
"trades": {
  "observable": true,
  "count": 3,
  "volume": "0.04210000",
  "last_price": "64123.4",
  "running_last_price": "64123.4",
  "running_last_price_age_ms": 0
}
```

| Field | Type | Semantics |
|---|---|---|
| `observable` | bool | **Were we listening?** `true` = the trade subscription was live for this whole interval, so the numbers below are claims about the market. `false` = the channel was down; the numbers below are **not** claims. |
| `count` | int \| null | trades in **this interval** — a DELTA, not a running total |
| `volume` | str(Decimal) \| null | summed `qty` over **this interval** — a DELTA |
| `last_price` | str(Decimal) \| null | price of the last trade **in this interval**; `null` when the interval contained no trade |
| `running_last_price` | str(Decimal) \| null | last traded price **carried forward** across intervals; `null` only before the first trade of the run |
| `running_last_price_age_ms` | int \| null | how stale `running_last_price` is, in milliseconds |

### The three states, and why each reads differently

| Situation | `observable` | `count` | `volume` | `last_price` | `running_last_price` |
|---|---|---|---|---|---|
| trades occurred | `true` | ≥1 | sum | the price | the price, age 0 |
| **listening, genuinely no trades** | `true` | **`0`** | **`"0"`** | **`null`** | carried, age > 0 |
| **channel down — we cannot see** | **`false`** | **`null`** | **`null`** | `null` | carried, with age |

**This is the misattribution guard (§2.4).** `count: 0` is a positive claim — *we were listening and
nothing traded*. `count: null` is the absence of a claim — *we could not see*. A corpus that wrote
`0` during an outage would say "no trades occurred" when it meant "the trade channel dropped",
which is the host-problem-as-venue-problem family one channel over.

`last_price` is **`null`, never fabricated**, when the interval held no trade. There is no
substitution from mid, from the previous trade, or from anything else at capture time — that would
be the D48 substitution moved earlier in the pipeline, where it is *harder* to detect because the
reader has no way to tell an invented price from an observed one.

**Why `running_last_price` is retained during an outage** (rather than nulled): the last price we
saw genuinely is the last price we saw, and `running_last_price_age_ms` states exactly how stale it
is. Nulling it would discard true information; `observable: false` is what stops a reader treating
it as current. A consumer that needs freshness must check the age — the field exists so that check
is possible.

### Mapping to `MarketState`

`MarketState` documents `trade_count` / `total_volume` / `last_price` as **"rolling trade stats"**.
This corpus stores **per-frame deltas**, from which any rolling window is derivable, while the
reverse is not true — a stored rolling total cannot be un-rolled to recover the deltas. Any future
reader that constructs a `MarketState` must therefore declare its own rolling window and aggregate;
it must not pass `count` straight through as `trade_count` and silently mean something different.

**`MarketState` requires `last_price: Optional[Decimal]` and rejects `total_volume < 0`, but has no
concept of "unobservable".** A frame with `observable: false` cannot be honestly converted to a
`MarketState` at all. That conversion, and what a strategy should do at such a frame, is **out of
scope here and left to the WO that builds the reader** — flagged so it cannot evaporate.

---

## §2.4 PARTIAL OUTAGE — declared, and NOT a fifth gap cause

### The ruling this respects

`GAP_CAUSES` in `kraken_v2_book.py` is **a ruled, exhaustive set** (`evidence/WO-014c-2/gap_schema.txt`
§1.1: "The taxonomy is RULED and EXHAUSTIVE. It is not extended here."). Its fifth member,
`HOST_SUSPEND`, was added by an explicit **lead ruling** (WO-015 addendum A), not by an executor.

**I did not extend it.** Two reasons, the second decisive:

1. Extending a ruled closed set is a lead ruling, not mine to make (§0.1).
2. **It would be semantically wrong.** That schema defines a gap as *"a half-open interval during
   which NO validated `MarketState` is emitted"*. During a trade-channel outage the book feed keeps
   flowing and validated states keep being emitted. **There is no gap.** Recording one would corrupt
   the gap ledger's meaning and, downstream, the covered-hours accounting — a trade outage would
   subtract book coverage that was never lost.

So a trade-channel outage is a **separate record type with its own ledger**, not a `GapRecord`.

### `TradeChannelOutage` — the declared causes

Both are producible, and prefix-free against each other and against every existing declared code
(`TRADE_CHANNEL_` is a unique stem; neither of the two prefixes the other):

| Cause | Meaning | Detection |
|---|---|---|
| `TRADE_CHANNEL_SUBSCRIBE_FAILED` | the subscription was NACKed, errored, or never acknowledged within the declared bound | an `error`/`status: error` response to our subscribe, or no `subscribe` ack within `SUBSCRIBE_ACK_TIMEOUT_SECONDS` |
| `TRADE_CHANNEL_DROPPED` | an acknowledged subscription ended while the socket stayed alive | an unsolicited unsubscribe/error naming `channel: trade` |

### ⚠ SILENCE IS DELIBERATELY **NOT** A CAUSE — and this is the honest limit

A live trade subscription that simply stops producing messages is **indistinguishable from a market
in which nothing traded.** Both look identical on the wire: nothing arrives.

Inventing a `TRADE_CHANNEL_SILENT` cause on a timeout would be the misattribution family running in
the *opposite* direction — recording "the channel broke" when the truth may be "nobody traded". On
an illiquid pair or a quiet night that would fabricate outages wholesale. WO-053's corpus makes the
point concrete: it was a genuinely quiet market.

So silence is recorded as what it is — `observable: true, count: 0` — and **this corpus cannot
distinguish a silently-wedged trade channel from a quiet market.** That limitation is stated here
rather than papered over with a threshold. Both channels ride one socket, so the failure modes that
*are* detectable (socket death, explicit unsubscribe, failed ack) are covered; a channel that stays
subscribed and silently stops delivering is not.

**Falsifier for the "no outage occurred" claim (0.12):** an outage record would have been written if
a subscribe ack failed to arrive within the bound, or an unsubscribe/error naming the trade channel
arrived on a live socket. Both conditions are exercised in `tests/test_trade_channel.py` and in the
§2.5 bite proof, so an empty outage ledger is a query that *could* have spoken.
