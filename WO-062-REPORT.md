# WO-062 — VENUE COMPARISON + DEX FEASIBILITY SPIKE

**Report only. No socket, no RPC, no wallet, no key, no account, no code.** Every figure below came
from a published document, and every figure that could not be obtained from one is marked
**DECLARED UNKNOWN** rather than estimated.

**The headline is not the fee.** The fee lever is real and large — Hyperliquid spot base taker is
**11.6× cheaper** round-trip than the Kraken tier we can actually claim. But three gates that are
**not scores** fire before that lever can be pulled, and two of them were not in the brief:

1. **dYdX v4 is perps-only.** Disqualified on spot. The candidate set was three; it is two.
2. **Hyperliquid's "BTC" spot market is `UBTC`** — bridged Bitcoin, not native BTC — quoted in
   USDC/USDH/USDT, not USD. That is **a different quantity from what we capture and would trade**,
   and it stacks two bases on top of each other.
3. **Hyperliquid's own Terms of Use name Ontario, Canada as a Restricted Territory** and forbid
   disguising location. Recorded as a scoring fact, not routed around.

---

## §1 STATE CONFIRMED

| | |
|---|---|
| HEAD | `d2c971c` — actual, not pinned (the WO stopped pinning a SHA; three consecutive WOs had a stale base) |
| `git diff -- src/` | **empty** |
| pytest 3.14.6 | **572 passed, 2 skipped** (315.60 s) |
| pytest 3.11.15 | **572 passed, 2 skipped** (314.36 s) |
| import-linter | **6 kept, 0 broken** |
| `corpus_20260805` | v1 `e3ab1aec…` · **38/38** verified, 0 mismatched |
| `validation_20260809` | v1 `884f9f00…` · **3/3** verified, 0 mismatched |

### A file-crossing that had to be fixed before this WO could start (0.1 / 0.5)

`instructions.md` still contained **WO-061**, and **WO-062's text had been written into
`WO-061-REPORT.md`**, overwriting a committed deliverable — 540 lines deleted, 231 inserted. On the
reaffirmed instruction I treated WO-062 as live and repaired it non-destructively:
`WO-061-REPORT.md` was restored from commit `d2c971c` (456 lines, byte-identical — it no longer
shows as modified) and WO-062 was moved into `instructions.md`. **Nothing was discarded**; the
report had been committed, so only the working copy was ever at risk.

### `phaseb_20260809` — informational, not disturbed, and NOT presently capturing

| run | state |
|---|---|
| `20260809063113` | complete, **12.000 covered h**, 13/13 segments verified |
| seam 0 | `PROCESS_RESTART`, resolved, width **6.076 h** — measured |
| `20260810003542` | **killed at 2.780 covered h** — 381,816 frames, 4 segments, **no `MANIFEST.json`, no `run_end`** |

**The leg I opened on instruction was killed when its harness task was stopped.** It is unfinalized
and **no capture is running now**. Two questions I raised remain unanswered and are restated at the
end of this report, because one of them is a corpus-integrity defect and the other is costing
covered hours every hour it stands.

---

# TRACK 1 — VENUE COMPARISON

## §2 THE CANDIDATE SET

### (a) Canada-registered CEXs — enumeration ATTEMPTED, and it is INCOMPLETE (0.11)

**The authoritative page could not be retrieved.** `securities-administrators.ca`'s
*Crypto Platforms Authorized to Do Business with Canadians* returns **HTTP 307** to both the fetch
tool and a direct request — twice, with a browser user-agent. **So I do not have a certified
enumeration, and I will not present a partial list as a complete one.** What follows is
search-surfaced and is labelled as such:

> Newton Crypto Ltd. · Shakepay Inc. · Shakepay Credit Inc. (crypto-backed lending, not a trading
> platform) · VirgoCX · Wealthsimple Investments Inc. · APX Inc. · Coinbase Canada Inc. ·
> Coinsquare Capital Markets Limited

**Status: PARTIAL, UNVERIFIED. The count is not known.** *Falsifier: any authorized platform absent
from that list — and I have positive evidence of exactly that, below.*

**The incumbent is the proof that the list is incomplete.** **Kraken is registered** — Payward
Canada Inc. holds a **Restricted Dealer registration** with the OSC as principal regulator,
obtained **April 2025**, and is a FINTRAC MSB (**M19343731**). It does not appear in the
search-surfaced list. That is the falsifier firing on the first check, and it is why the list above
is not offered as the candidate set.

**Consequence for §3:** a scored comparison across Canadian CEXs cannot be completed from an
enumeration I cannot obtain. **Kraken (incumbent, cited in-tree) and Coinbase Canada (confirmed
registered) are the two I can speak to; the rest of the CEX field is a declared gap.**

**One cited fact worth carrying forward:** Kraken has **delisted USDT, DAI, WETH, WBTC and WAXL in
Canada**. Wrapped and value-referenced assets are being removed from the Canadian venue — directly
relevant, because the DEX alternative's BTC market *is* a wrapped asset.

### (b) Order-book DEXs — the spot gate applied first

| venue | spot? | verdict |
|---|---|---|
| **dYdX v4** | **NO — perpetual futures only** | **DISQUALIFIED** |
| **Hyperliquid** | Yes, but the BTC market is **UBTC** (bridged) | proceeds, with a declared quantity difference |
| **Injective / Helix** | Yes — "premier decentralized spot and derivatives exchange" | proceeds |

**The dYdX disqualifier, verified rather than assumed** (§2's explicit instruction): dYdX's own
material describes the platform as *"Trade Perpetuals"* and *"Leading Decentralized Platform for
Crypto Perpetual Trading"*; its help material states dYdX Chain **may** support spot in future but
that there are **no current plans**, perpetuals being the focus. **Spot is a gate, not a score, so
dYdX is out** — and perps are independently excluded on constitutional scope and Canadian retail
restriction. *Falsifier: a dYdX v4 spot market existing today would overturn this; I found none,
and their own product pages say perpetuals.*

**AMMs and aggregators — EXCLUDED AS VENUES, with the reason recorded** (§2(b)): their fill model
is incompatible with the CLOB apparatus. There is no resting book to capture, no L2 depth to
record, and no maker/taker distinction in our sense. The entire corpus discipline — book snapshots,
checksummed deltas, spread and depth at the touch — has no referent against a constant-product
pool. **A separate research track, not pursued here.**

---

## §3 SCORING

### 3.1 ALL-IN COST AT 0.1 BTC (~$6,460) — the same size every prior figure in this project uses

**0.16 statement.** Kraken's rate is a **percentage of notional** charged by a custodial venue on a
fiat-quoted pair. Hyperliquid's is a **percentage of notional** charged by a protocol on a
crypto-quoted pair in a bridged asset. Same *shape*, so the percentages are commensurable — **but
they are not the same quantity**, because the assets differ (BTC vs UBTC) and the quote differs
(USD vs USDC/USDH/USDT). The percentage comparison below is valid; the **basis** difference is a
separate term and is declared, not folded in.

| component | **Kraken Tier 1** (committed, in-tree) | **Hyperliquid spot Tier 0** |
|---|---|---|
| taker, one side | **0.80%** | **0.070%** |
| maker, one side | 0.40% | 0.040% |
| **round trip, taker/taker** | **1.6216%** (incl. 2×1bp measured slip + 0.0016% measured spread) | **0.140%** (fees only) |
| at 0.1 BTC | **~$104.76** | **~$9.04** |
| **gas** | n/a | **ZERO — "Trading on Hyperliquid is gas-free"** |
| failed-transaction cost | n/a | **DECLARED UNKNOWN** — not stated in the docs read |
| price impact at 0.1 BTC | **DECLARED UNKNOWN** | **DECLARED UNKNOWN** |

**Ratio: 1.6216 / 0.140 = 11.58× — round UP to 11.6× per 0.15.** This confirms the brief's
arithmetic from the committed schedule rather than from recall.

**The tier a $0-volume account can actually claim** — the Tier 1 lesson, applied to both sides.
Kraken's committed table has **17 tiers**, `ASSUMED_TIER = "Tier 1"` (taker 0.80%), source
`kraken.com/features/fee-schedule`, retrieved **2026-08-07**. Kraken's *best* tier (Pro 5) is
0.05%/0.00% but requires **$500M** 30-day volume and **$100M** assets on platform — unclaimable.
Hyperliquid's base spot tier is likewise **Tier 0, $0 volume: taker 0.070%, maker 0.040%**, and its
best tier (>$7B) is 0.025%/0.000% — equally unclaimable. **Both figures above are the tiers a new
account genuinely gets.** Hyperliquid additionally publishes staking discounts (5–40% by HYPE
staked) and referral discounts on the first $25M of volume — **not claimed here**, because a
discount requiring us to hold a venue token is a cost assumption wearing a fact.

**PRICE IMPACT IS A DECLARED UNKNOWN, deliberately.** §3.1 asks for it from published L2 depth at
the touch. Obtaining depth requires calling `l2Book` — an **RPC/API request this WO forbids**. So I
did not obtain it. **A declared unknown beats a guessed figure**, and this one is material: at
0.1 BTC against a book whose *published* depth is only **5 levels (fast) or 20 levels (slow)**,
impact could plausibly exceed the entire fee saving. **It is the single largest open term in the
comparison.**

### THE GAS FINDING — a change to the cost model's SHAPE, not its parameters

**Reported as §3.1 requires, and it stands even though Hyperliquid's own trading gas is zero.**

Our cost model is **proportional**: cost = notional × rate. Gas is **per-transaction**. Those are
different functional forms, and mixing them silently is a units error:

```
$0.50 gas at 0.1 BTC ($6,460)  = 0.008% of notional
$0.50 gas at 0.001 BTC ($64.6) = 0.774% of notional     — 97x the same fee, same dollar
```

**A percentage-only cost model cannot express a fixed cost.** It is not that the parameter is
wrong — the model has no term to put it in. Any adoption WO for an on-chain venue must change the
model to `proportional + fixed`, and **that is a structural change, not a re-parameterisation.**
It also silently makes small orders uneconomic in a way a percentage model will never show.

**This applies even to Hyperliquid.** Trading is gas-free, but **deposits and withdrawals are not**
— *"Depending on the withdrawal chain and method, there may be small gas fees to process the
withdrawal"* — and bridging into UBTC has its own cost. Those are fixed per-event costs sitting
outside a percentage model. **DECLARED UNKNOWN: the exact deposit/withdrawal/bridge amounts are not
published in the pages read.**

### 3.2 L2 DATA QUALITY AND CAPTURE-ABILITY — **the sharpest dimension, and it is where the DEX case weakens**

**Hyperliquid's `l2Book` WebSocket feed, from its published schema:**

```
subscribe : { "type": "l2Book", "coin": "<coin>" }   (+ nSigFigs, mantissa, fast)
payload   : WsBook { coin, levels: [ [WsLevel], [WsLevel] ], time }
            WsLevel { px, sz, n }
depth     : "5 levels if fast, 20 levels if slow"
cadence   : "Snapshot feed, pushed on each block that is at least 0.5 since last push"
```

**INTEGRITY MECHANISM: NONE.** The documentation contains **no checksum, no CRC, no sequence
number, and no verification mechanism** for order-book data. Stated plainly, as §3.2 requires.

**What that does and does not mean — the honest reading, not the alarming one.** Kraken's CRC32
exists because Kraken sends **deltas** and we reconstruct the book locally; the checksum catches
reconstruction drift. Hyperliquid sends **snapshots**, so there is no accumulated local state to
drift — the failure mode CRC32 guards against largely does not arise. **The absence is less severe
than it first appears.**

**But three things are genuinely lost, and one of them is worse than the missing checksum:**

- **Depth truncation is the real problem.** 5 or 20 levels is not a book. Our corpus records the
  touch *and* the depth behind it; price-impact modelling at 0.1 BTC needs the depth. A 20-level
  snapshot may not even span our order size — **and we cannot know without calling the endpoint,
  which this WO forbids.**
- **Cadence is ~5× coarser.** ≥0.5 s per push against our measured Kraken capture cadence of
  **106.3 ms**. Every microstructure quantity we have measured would be observed at a fifth of the
  resolution.
- **No sequence number means no gap detection primitive.** With deltas you detect a hole; with
  unsequenced snapshots you cannot distinguish "no update" from "update lost". Our gap ledger's
  causes are about the *connection*, so they survive — but `checksum_failures_total` and the
  FR-018a resync semantics would have **no referent at all**.

**What could substitute, and what it would not cover:** the snapshot cadence itself is a weak
liveness check (a stalled feed shows as a frozen `time` field), and an independent re-derivation
against `recentTrades` could corroborate the touch. **Neither substitutes for depth.** No mechanism
recovers levels the venue never published.

**Injective / Helix: DECLARED UNKNOWN.** The docs index confirms *"a fully on-chain orderbook
exchange"* but the pages retrieved contained **no order-book streaming schema, no depth, no
cadence, and no integrity statement**. `docs.ts.injective.network` 301-redirects to
`docs.injective.network`, whose landing page carries none of it. **I am not going to characterise a
feed I did not read.** This is the largest documentation gap in Track 1 and it is why Injective is
unscored below rather than scored low.

### 3.3 API MATURITY AGAINST OUR EXECUTION ABSTRACTION

**Hyperliquid — published rate limits, cited exactly:**

| limit | value |
|---|---|
| REST aggregate, per IP | **1200 / minute** |
| `l2Book` info request | weight **2** |
| most other info requests | weight **20** |
| WebSocket connections, per IP | **10** |
| new WS connections | **30 / minute** |
| WS subscriptions | **1000** |
| messages to Hyperliquid | **2000 / minute** |
| open orders per address | **1000**, +1 per $5M volume, capped **5000** |

Documented SDKs exist; mainnet `api.hyperliquid.xyz`, testnet `api.hyperliquid-testnet.xyz` — **a
real testnet, which matters for a TRADING_ENV-guarded apparatus.**

**LOCAL TRANSACTION SIGNING — flagged as an architecture question, not resolved here (§3.3's
instruction).** An on-chain venue authenticates by signing, not by an API key. **DECLARED UNKNOWN:
the specific scheme** — the API landing page I read did not state it, and I did not chase it
further because the finding does not depend on the details. What matters architecturally:

- **A key that signs is not a key that authenticates.** Our secrets discipline, kill-switch, and
  TRADING_ENV guard are built around a credential that a venue can revoke. **A signing key cannot
  be revoked by anyone but us**, and a compromised one is not a compromised session — it is a
  compromised wallet.
- **`no_credential` preflight has no referent.** Its check is *"No credentials in .env"*. A signing
  key held for an on-chain venue is exactly the thing that check exists to prevent, and it would
  need rebuilding, not re-pointing.
- **The one-module swap assumption is where this bites.** Reading is venue-abstracted; *signing* is
  not an adapter concern in our current architecture.

### 3.4 SPOT AVAILABILITY — the gate

| venue | spot | source |
|---|---|---|
| Kraken | **PASS** | in-tree committed schedule, spot crypto |
| Coinbase Canada | **PASS** | registered CATP |
| **dYdX v4** | **FAIL** | perpetuals only — **disqualified** |
| Hyperliquid | **PASS with a caveat** | spot exists; **the BTC market is UBTC**, bridged |
| Injective / Helix | **PASS** | "decentralized spot and derivatives exchange" |

**The UBTC caveat is a §0.16 quantity difference and belongs here, not in a footnote.**
`BTC/USDC` on the Hyperliquid frontend **is `UBTC/USDC` on mainnet HyperCore** — L1 name `UBTC`,
token index 197, "Unit Bitcoin". So a strategy validated on Kraken BTC/USD and run on Hyperliquid
would be trading **a bridged claim on Bitcoin quoted in a stablecoin**, carrying:

- **bridge/custody risk** in the Unit protocol — a failure mode with no analogue on a CEX spot pair;
- a **UBTC/BTC basis** and a **USDC-or-USDH/USD basis**, compounding — and we already measured the
  USDT/USD basis at **~+9 bps** with <4 bps dispersion in WO-061, so these terms are not zero;
- **the pointed irony that Kraken has delisted WBTC in Canada** — the incumbent venue's regulator
  is removing wrapped assets while the alternative's only BTC market is one.

### 3.5 REGULATORY POSTURE — plain-language, not legal advice

**Kraken**: Restricted Dealer registration, OSC principal regulator, **April 2025**; FINTRAC MSB
`M19343731`. Payward Canada states an intent to seek investment-dealer registration, CIRO
membership, and ATS approval. **Registered and operating.**

**Hyperliquid — a recorded scoring fact.** Its Terms of Use define **Restricted Persons** to
include persons resident, located, or incorporated in **the United States of America or Ontario,
Canada**, and state Restricted Persons are prohibited from accessing the Interface. The Terms
further prohibit *"using any technology or method to disguise their location or otherwise evade
access restrictions."*

**Recorded, not routed around** (§3.5's explicit instruction). **No VPN-dependent path is
considered.** I do not know which province applies here and **will not infer a jurisdiction from a
timezone** — the host clock is UTC−04:00, which covers Ontario and several non-Ontario zones alike.
If Ontario applies, the frontend is closed by the venue's own terms.

**The distinction §3.5 asks me to record and not adjudicate:** the Terms restrict *the Interface*.
The chain is permissionless, so protocol-level access via self-custody is a **different question
from frontend access**. I record that they are different and **do not adjudicate whether the
restriction reaches protocol access.** That needs qualified advice, and anything load-bearing here
should get it.

**Injective / Helix**: **DECLARED UNKNOWN** — I did not retrieve its terms.

---

## §4 TRACK 1 OUTPUT

| dimension | **Kraken** (incumbent) | **Hyperliquid** | **Injective/Helix** | **dYdX v4** |
|---|---|---|---|---|
| **spot gate** | PASS | PASS (**UBTC**, not BTC) | PASS | **FAIL — out** |
| round-trip cost, claimable tier | **1.6216%** | **0.140%** — **11.6× cheaper** | ~0.1% taker / −0.01% maker *(varies by pair)* | — |
| gas | n/a | **zero for trading**; nonzero deposit/withdraw | UNKNOWN | — |
| price impact @0.1 BTC | UNKNOWN | UNKNOWN | UNKNOWN | — |
| **book integrity mechanism** | **CRC32** | **NONE** (snapshot feed mitigates) | **UNKNOWN** | — |
| **published depth** | full book | **5 or 20 levels** | UNKNOWN | — |
| **cadence** | **106.3 ms** measured | **≥0.5 s** | UNKNOWN | — |
| auth model | API key (revocable) | **local signing** | signing (assumed, unverified) | — |
| testnet | yes | **yes** | UNKNOWN | — |
| Canada posture | **Restricted Dealer, OSC** | **Ontario is a Restricted Territory** | UNKNOWN | — |

**No venue dominates, and the answer is "depends on X" — so, per §4, X is named.**

**X₁ — price impact at 0.1 BTC against a 20-level book.** The fee saving is **$95.72 per round
trip** at our size. If impact on a shallow book exceeds that, the entire case inverts. **This is
one measurement, and it requires exactly the socket call this WO forbids.** It should be the first
thing any follow-on WO obtains.

**X₂ — jurisdiction.** If Ontario applies, Hyperliquid's frontend is closed by its own terms and
no amount of fee advantage changes that.

**X₃ — whether UBTC is an acceptable instrument.** Not a cost question. A strategy validated on
BTC/USD trading UBTC/USDC is trading a different thing, and Kraken's Canadian delisting of wrapped
assets suggests the regulator has a view.

**What I will say plainly:** the fee lever is real, confirmed from the committed schedule, and
**11.6×** is the correct order of magnitude. But it is the *only* dimension on which the DEX wins.
It loses on depth, cadence, integrity, instrument identity, and jurisdiction — and **three of those
five are corpus-integrity concerns, not conveniences.**

---

# TRACK 2 — FEASIBILITY SPIKE

## §5 Top-scoring order-book DEX: **Hyperliquid** — from published schemas only, no socket

Injective could not be scored (§3.2), so Hyperliquid takes this by default rather than on merit.

### WHAT CHANGES

| area | change |
|---|---|
| **subscribe shape** | `{"type":"l2Book","coin":"UBTC"}` vs Kraken's `{"method":"subscribe","params":{"channel":"book",...}}` — trivial |
| **book update format** | `WsBook{coin, levels:[bids,asks], time}`, `WsLevel{px,sz,n}`. **`n` (order count per level) is new information Kraken's book does not carry** |
| **snapshot vs delta** | **THE STRUCTURAL ONE.** Kraken = snapshot + deltas + CRC32. Hyperliquid = **snapshots only**. `kraken_v2_book`'s entire delta-application and resync path has **no counterpart** |
| **integrity** | **none published.** `checksum_failures_total` would always be 0 — **and a metric that cannot move is not a metric.** FR-018a's resync semantics would have **no trigger**. Both must be either removed or explicitly redefined; **leaving them wired and always-zero is the worst option**, because it reads as "integrity verified" |
| **depth** | full book → **5 or 20 levels**. Depth-dependent measurements do not port |
| **symbol mapping** | `BTC/USD` → `UBTC` (index 197), quote USDC/USDH/USDT. **Not a rename — a different instrument** |
| **timestamps** | `time` field, resolution not stated in the schema read — **DECLARED UNKNOWN** |
| **gap detection** | no sequence number. Detection must fall back to connection state and `time` monotonicity |

### WHAT TRANSFERS UNCHANGED — assessed, not assumed

| component | verdict |
|---|---|
| **corpus discipline** — segments, manifests, capture-time SHA-256, rotation, digests | **TRANSFERS FULLY.** Venue-agnostic by construction; it hashes bytes |
| **gap ledger, five ruled causes** | **FOUR of five transfer.** `KEEPALIVE_RECONNECT`, `BREAKER_RETRY_LADDER`, `VENUE_DISCONNECT`, `HOST_SUSPEND` are about the connection and the host. **`CHECKSUM_RESYNC` has no referent** — 0.11 applies: the count is 4, not 5 |
| **default-deny reader** | **TRANSFERS.** Operates on the ledger, not the venue |
| **seam machinery** | **TRANSFERS.** Process-level |
| **force-flat / U2–U6** | **TRANSFERS in principle**, but **U-semantics assume an order lifecycle with a revocable session.** Signing changes the failure mode, not the state machine |
| **cost model** | **STRUCTURE CHANGES.** Per §3.1, it needs a `proportional + fixed` form. **Structural, not a parameter** |
| **`fee_schedule.py`** | **PATTERN TRANSFERS, CONTENT DOES NOT.** Named-tier-with-citation is exactly right; a whole new cited table is needed |
| **TRADING_ENV guard** | **TRANSFERS**, and a real testnet exists |
| **`no_credential` preflight** | **DOES NOT TRANSFER.** Scans `.env` for API credentials; a signing key is a different artifact. **Needs rebuilding** |

### COST ESTIMATE for a capture-adapter WO

**Basis, stated:** the Kraken v2 adapter consumed most of Sprint 2, and its expensive parts were
**not** the message plumbing — they were CRC32 validation, delta-application correctness, resync
semantics, and the harness (`ScriptedConnectionFactory`, `FakeWebSocket`, `AdvancingClock`) that
made all of it testable without a socket. **That harness already exists and is venue-agnostic.**

**Estimate: 40–60% of the Kraken adapter's cost**, and the split is informative:

- **Cheaper**: no checksum validation, no delta application, no resync ladder — a snapshot feed is
  markedly simpler. The test harness is built. The corpus layer is untouched.
- **Not cheaper**: symbol/instrument mapping for a bridged asset; the cost-model shape change;
  rebuilding `no_credential`; deciding what `checksum_failures_total` and FR-018a *mean* — a
  **semantic** question, and this project's evidence is that semantic questions cost more than
  plumbing (WO-054's `count: 0` vs `count: null` was one line of code and most of a work order).
- **The unknown that could dominate**: whether 20 levels suffices. If not, this is not an adapter
  WO at all — it is a re-derivation of every depth-dependent quantity in the apparatus.

**Rounded up per 0.15, and stated honestly: 40–60%, with a named tail risk that could exceed 100%.**

## §6 WHAT THIS WO DID NOT DO

No socket, no RPC, no wallet, no key, no account, no code, no adoption. **The death certificate is
not re-opened** — its scoping is noted, and a new fee regime is a **new pre-registered question for
a future WO**, not a re-run of a closed one.

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | Read `instructions.md` | **Contained WO-061, not WO-062** |
| 2 | Locate WO-062 | Found in `WO-061-REPORT.md`, having overwritten it (540 deleted / 231 inserted) |
| 3 | Repair | Report restored from `d2c971c` (456 lines, no longer modified); WO-062 moved to `instructions.md` |
| 4 | dYdX v4 spot check | **Perps only — DISQUALIFIED** |
| 5 | Hyperliquid fee schedule | Spot Tier 0 **0.070% / 0.040%**; perp Tier 0 0.045%/0.015% |
| 6 | Hyperliquid `l2Book` schema | Snapshot feed, **5 or 20 levels**, ≥0.5 s, **no checksum/sequence** |
| 7 | Hyperliquid BTC spot | **It is `UBTC`** (index 197), quoted USDC/USDH/USDT |
| 8 | Hyperliquid rate limits | Full cited table above |
| 9 | Hyperliquid API auth page | **Signing scheme NOT stated** on the page read — declared unknown |
| 10 | Hyperliquid gas | **"Trading on Hyperliquid is gas-free"**; withdrawal gas exists, amount unstated |
| 11 | Hyperliquid Terms | **Ontario, Canada is a Restricted Territory**; no-VPN clause |
| 12 | Injective docs (`docs.ts.` → `docs.`) | 301 redirect; landing page has **no book schema, no integrity, no fees** |
| 13 | Injective/Helix fees via search | ~0.1% taker / −0.01% maker on some pairs; protocol minimums 0.1%/0.2%; **varies by pair** |
| 14 | CSA authorized-platforms page | **HTTP 307 twice** — authoritative enumeration **NOT OBTAINED** |
| 15 | Kraken Canada status | **Restricted Dealer, OSC, April 2025**; FINTRAC MSB M19343731 — **absent from the search list, proving it partial** |
| 16 | Kraken committed fee schedule | 17 tiers, Tier 1 0.80%/0.40%, retrieved 2026-08-07; best tier unclaimable |
| 17 | Price impact at 0.1 BTC | **NOT ATTEMPTED** — requires an RPC call this WO forbids. Declared unknown |

---

## §7 ACCEPTANCE

| requirement | status |
|---|---|
| Candidate set enumerated, spot gate applied | **PARTIAL** — DEX side complete; **Canadian CEX enumeration NOT obtainable (307)**, declared |
| dYdX spot status verified | **met — perps only, disqualified** |
| All-in cost at 0.1 BTC, every component cited or declared-unknown | **met** |
| Gas structural finding stated | **met** |
| Integrity mechanism answered per venue | **met for Kraken and Hyperliquid; UNKNOWN for Injective**, declared |
| API / signing assessment | **met**, with the scheme itself declared unknown |
| Regulatory note, geo-blocks as facts | **met** — Ontario recorded, not routed around |
| Track 2 gap list both columns + costed estimate | **met** |
| `git diff -- src/` empty | **met** |
| no socket / RPC / wallet / key / account | **met** |
| corpora untouched | **met** |
| gates green | **met** — 572/2 both interpreters (574 collected, unchanged), 6/6 contracts, both corpora verify |

---

## THE TWO OPEN QUESTIONS, RESTATED — they are not part of this WO but they are still costing

1. **The coverage-query defect.** A run killed before writing `run_end` contributes **zero** covered
   hours and is reported as `incomplete_runs: []`. Leg 2's 2.780 hours and 381,816 frames are on
   disk and invisible to the accounting, with nothing saying so. Over ~46 legs to 556 hours, every
   interrupted leg silently under-counts. **My recommendation remains a WO of its own** — it is a
   corpus-integrity bug in the metric the whole phase-B plan is measured by.
2. **The 2.780 hours.** Reconcile them in, or discard the unfinalized run? They are real and
   readable but have **no capture-time manifest**, so they cannot be hash-verified the way every
   other segment can — which may itself be reason to drop them rather than admit an unverifiable
   run into a corpus whose value is that every segment is provable.

**And no phase-B capture is currently running.**
