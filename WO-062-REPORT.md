# WO-063 — VENUE RE-SCORE: three order-book DEXs, SPOT AND PERPS. Technical dimensions only.
#
# SUPERSEDES WO-062's SCOPE ON TWO POINTS, by operator direction:
#   1. **PERPETUALS ARE IN SCOPE.** WO-062's spot-only gate was a self-imposed narrowing, not a
#      requirement. dYdX was disqualified under it and is REINSTATED.
#   2. **JURISDICTION IS NEVER A GATE.** Record availability restrictions as FACTS where they exist,
#      and score nothing on them. Deployment location is an operator matter, not a design constraint.
# Do not re-derive either constraint. Do not narrow scope on any assumption not stated here.

BASE: current HEAD (§1 reports actual — do not pin a SHA).
SCOPE: report only. **NO socket, NO RPC, NO wallet, NO key, NO account, NO code.** Docs and
published schedules only. `git diff -- src/` empty (paste).
SHIP IMPACT: **NO.**
PARALLEL: does not block the hours-horizon suite pre-registration against the d54-approved basis.

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.1e Cite or declare-with-derivation, every figure. A figure that cannot be obtained is **DECLARED
     UNKNOWN**, never estimated.
0.5 Report every attempt.
0.6 AUTO MODE OFF.
0.11 Enumerate, do not assume the count.
0.12 Every observation offered as corroboration states its falsifier.
0.15 Margin-bearing declarations round up and say so.
0.16 Any comparison across two quantities states, at declaration, what mechanism generates each and
     whether they are simultaneous. **Cross-venue cost comparison is exactly this shape, and perps
     vs spot is a second instance of it inside the same table.**
0.17 No venue is adopted here. This produces a comparison; the decision is the lead's.
0.18 **DO NOT DISQUALIFY ON JURISDICTION OR ON INSTRUMENT TYPE.** Both are recorded as facts.
     WO-062 lost dYdX to a scope assumption; that is the error being corrected.

---

## §1 CONFIRM STATE
Actual HEAD, `git diff -- src/` empty, gates green, corpora verify. `phaseb_20260809` status
(informational — do not disturb).

---

## §2 THE CANDIDATE SET — three venues, two instrument classes each

| venue | spot | perps |
|---|---|---|
| **Hyperliquid** | UBTC (bridged), quoted USDC/USDH/USDT | BTC-PERP |
| **dYdX v4** | none (verified WO-062) | BTC-USD perp — **REINSTATED** |
| **Injective / Helix** | yes | yes |

**Injective was unscoreable in WO-062** — `docs.ts.injective.network` 301'd and the landing page
carried no schema, no integrity mechanism, no fees. **Try alternative routes** (0.11): the Injective
GitHub org, the Python/TypeScript SDK repos and their docstrings, the indexer/gRPC API reference,
Helix's own docs, and any published protocol spec. **If it remains unobtainable after an enumerated
search, declare that — do not score it from search snippets.**

---

## §3 THE FOUR TECHNICAL DIMENSIONS

### 3.1 ALL-IN COST AT 0.1 BTC (~$6,460), SPOT AND PERPS SEPARATELY
Cited fee tables, the tier a **zero-volume account can actually claim** (the Tier 1 lesson: an
optimistic tier is a cost assumption wearing a fact's clothing). Maker and taker. Plus gas, price
impact from published depth where obtainable, and failed-transaction cost.

**AND THE NEW COST STRUCTURE THIS WO EXISTS TO SURFACE — FUNDING.**
Perpetuals charge **funding**: a periodic payment between longs and shorts, typically hourly or
8-hourly. **This is a THIRD cost shape our model does not have:**
```
  fee      = proportional to NOTIONAL, per trade        (we model this)
  gas      = FIXED per transaction                       (WO-062 flagged this)
  funding  = proportional to NOTIONAL x TIME HELD        (NOTHING in our model has a time dimension)
```
**For an hours-horizon strategy this may dominate.** A 4-hour hold pays funding; a 4-hour spot hold
does not. Report, per venue: the funding interval, how the rate is determined, and **published
historical funding rates for BTC** if obtainable — the *distribution*, not a single figure, since a
mean funding rate says nothing about what a 4-hour hold costs on a bad day.
State plainly: **is funding large or small relative to the 0.14%-ish round-trip fee advantage?**
If it is comparable or larger, the fee lever is smaller than it appears for held positions, and that
is the finding. **Declare it unknown rather than estimating it.**

Also record, not scored: **leverage and liquidation.** Perps permit leverage; liquidation is a
risk-layer concern with no counterpart in spot. Note maintenance margin and liquidation mechanics
per venue as facts for a future risk-layer WO. **Do not model them here.**

### 3.2 FEED INTEGRITY — the dimension that decides feasibility
For each venue and instrument: is there a public WebSocket L2 book feed, at what depth and cadence,
and **what is its integrity mechanism?**
- Kraken gives CRC32 book checksums. Hyperliquid publishes **none** (WO-062: snapshots only, no
  checksum, no sequence — `checksum_failures_total` could never move, and *a metric that cannot move
  is not a metric*).
- **dYdX v4 is a Cosmos chain and this is genuinely unexplored.** Block heights, indexer sequence
  numbers, and on-chain state commitments may provide an integrity primitive **stronger** than a
  checksum — a book derivable from committed chain state is verifiable in a way a broadcast snapshot
  is not. **Nobody has checked. Check it.** If it exists, say what it guarantees and what it does not.
- Injective: same question, same unknown.
For any venue with no mechanism, state what could substitute (sequence numbers, snapshot cadence,
independent re-derivation from chain state) and **what that substitute would NOT cover.**

### 3.3 DEPTH AND CADENCE
Levels published, update frequency, whether full-depth is available on any channel. Hyperliquid is
5 or 20 levels at ≥0.5s. **Depth-dependent quantities in our apparatus (spread, touch depth, the
measured slippage) do not port below some level count — state the threshold you would need.**

### 3.4 API AND SIGNING MATURITY
Order lifecycle, auth model, rate limits (cited), SDKs. **Whether execution requires local
transaction signing** — a materially different path from an API key, and note that our
`no_credential` preflight scans `.env` for API credentials and **would not see a signing key**
(WO-062's finding). Flag as an architecture question; do not resolve here.

---

## §4 JURISDICTION — RECORDED, NEVER SCORED (0.18)
One short factual line per venue on stated availability restrictions. **No venue is penalised,
ranked down, or excluded for it.** No VPN paths are proposed or evaluated; a restriction is simply
noted where the venue publishes one.

---

## §5 OUTPUT
A scored table across the four technical dimensions, spot and perps as separate rows, plus a short
narrative per venue. **State which venue wins on which dimension and where the trade-offs sit.**
If funding materially erodes the perps fee advantage, say so — that is the most likely finding and
it should be stated plainly rather than buried.

**And the one comparison that matters:** against Kraken Tier 1's **1.6216% round trip**, what is
each venue's all-in round-trip cost at 0.1 BTC **including funding for a 4-hour hold** on the perps
rows? That single number is what decides whether the hour-scale horizon class reopens in a new fee
regime — a **new pre-registered question for a future WO**, not a re-run of the death certificate.

## §6 ACCEPTANCE
Three venues attempted, Injective's docs sought via enumerated alternative routes; spot and perps
both scored where they exist; funding characterised or declared unknown, with its time-dimension
implication for the cost model stated; feed integrity answered per venue including dYdX's Cosmos
primitives; depth threshold stated; signing/preflight gap noted; jurisdiction recorded and not
scored; `git diff -- src/` empty; no socket/RPC/wallet/key/account; corpora untouched; gates green.

## §7 REPORT — `WO-063-REPORT.md`
The scored table with every figure cited or declared unknown; the funding finding and its cost-model
implication; per-venue integrity verdicts; the 4-hour-hold all-in comparison against 1.6216%; every
attempt; any STOP.

**THEN STOP.** Output feeds the Sprint 3 venue decision.
---

# ADDENDUM — §2(a) ENUMERATION COMPLETED, and it corrects the partial list in BOTH directions

The original pass left exactly one §7 acceptance item unmet: the Canadian CEX enumeration. The CSA's
*Crypto Platforms Authorized to Do Business with Canadians* page returns **HTTP 307** to every route
tried, on two separate days. **It still does.**

**A different authoritative source serves it: the OSC.** `osc.ca/en/industry/registration-and-compliance/crypto-businesses`
returned HTTP 200 and carries the registrant tables directly. **The page states its own last-updated
date: 2026-07-30.** Retrieved 2026-08-10.

## REGISTERED crypto asset trading platforms — 14, enumerated (0.11)

> *"The following crypto asset trading platforms have received exemptive relief to offer crypto
> products to investors in Ontario"*

| # | platform | category | most recent decision |
|---|---|---|---|
| 1 | Coinsquare Capital Markets Ltd. (dba **Bitbuy**) | Investment Dealer (Dealer and Marketplace) | 2024-10-11 |
| 2 | **Coinbase Canada Inc.** | Restricted Dealer (Dealer and Marketplace) | amended 2026-04-01 |
| 3 | Cybrid Canada Inc. | Restricted Dealer (Dealer – **Ontario only**) | 2025-01-17 |
| 4 | Fidelity Clearing Canada ULC (Fidelity Digital Assets) | Investment Dealer (Dealer) | 2026-04-14 |
| 5 | Fidelity Digital Asset Services, LLC | Exempt Marketplace and Clearing Agency | 2023-01-18 |
| 6 | Foris DAX CAN ULC et al (**Crypto.com**) | Restricted Dealer (Dealer and Marketplace) | — |
| 7 | Ndax Canada Inc. | Investment Dealer (Dealer and Marketplace) | 2024-12-19 |
| 8 | Netcoins Inc. | Restricted Dealer (Dealer) | amended 2025-09-29 |
| 9 | Newton Crypto Ltd. | Investment Dealer (Dealer) | amended 2026-03-25 |
| 10 | **Payward Canada Inc. and Payward, Inc. (operating as KRAKEN)** | **Restricted Dealer (Dealer and Marketplace)** | **2025-04-01** |
| 11 | Satstreet Inc. | Restricted Dealer (Dealer) | 2026-07-06 |
| 12 | Shakepay Inc. | Investment Dealer (Dealer) | 2025-01-08 |
| 13 | Wealthsimple Investments Inc. | Investment Dealer (Dealer) | amended 2025-12-22 |
| 14 | Webull Canada Crypto Limited | Investment Dealer (Dealer) | 2026-06-17 |

Separately listed and **not trading platforms**: APX Inc. and Shakepay Credit Inc. (crypto-backed
*lending*), zerohash llc (immediate-delivery VRCA platform), and two VRCA issuer undertakings
(Circle/USDC, QCAD Digital Trust).

## The earlier partial list was wrong in BOTH directions — 0.11 vindicated again

My first pass offered a search-surfaced list of 8 names, labelled PARTIAL and UNVERIFIED. Against
the authoritative table it was wrong twice over:

**IT OMITTED 8 REGISTERED PLATFORMS** — Coinsquare/Bitbuy, Cybrid, both Fidelity entities,
Crypto.com, Ndax, Netcoins, Satstreet, Webull.

**IT INCLUDED ENTRIES THAT DO NOT BELONG:**

- **VirgoCX — registration SUSPENDED effective 2025-11-24.** It appears in the OSC's
  *not currently registered* table, not the registered one. I listed it as authorized.
- **APX Inc.** and **Shakepay Credit Inc.** are crypto-backed **lending** platforms, not trading
  platforms.

**And the falsifier I declared fired exactly as predicted**: I wrote *"any authorized platform
absent from that list"* would overturn it, and named Kraken as positive evidence it was incomplete.
Confirmed — Kraken is #10, **Restricted Dealer (Dealer and Marketplace), decision 2025-04-01**.

## Also enumerated: NOT currently registered (12)

Bitbuy Technologies (expired, acquired by Coinsquare) · Bitvo (expired, acquired by Bitbuy) · ByteX
(PRU expired) · CatalX (PRU withdrawn, subject to an Alberta cease-trade order) · Coinberry
(expired, acquired by Bitbuy) · DigiFinex (PRU) · **Gemini (PRU expired; no longer offers services
to retail clients)** · Hibit (expired) · CoinSmart (expired, acquired) · Uphold (PRU withdrawn) ·
**VirgoCX (suspended 2025-11-24)** · Wealthsimple Digital Assets (expired 2024-01-01).

Context the OSC states directly: as announced **2024-08-06**, the CSA **no longer accepts new
pre-registration undertakings**; new CTPs apply directly to **CIRO**.

## SCOPE LIMIT, declared (0.1e)

**This table is the OSC's, and it is scoped to Ontario** — *"exemptive relief to offer crypto
products to investors in Ontario."* The CSA maintains the multi-jurisdiction list and **that page
remains unobtainable (HTTP 307)**. So the enumeration is **authoritative for Ontario and not
established Canada-wide.** A platform registered in another province and not in Ontario would not
appear above. *Falsifier: the CSA list, when reachable, showing a registered CTP absent from this
table.*

This scope limit is not incidental to this WO: **WO-062's own regulatory finding is that
Hyperliquid's Terms name Ontario as a Restricted Territory.** Ontario is the jurisdiction the
comparison turns on either way.

## §7 ACCEPTANCE — the outstanding item

| requirement | status |
|---|---|
| Candidate set enumerated, spot gate applied | **NOW MET for Ontario** — 14 registered CTPs enumerated from the OSC with decision dates; DEX side unchanged (dYdX disqualified perps-only) |
| all other items | unchanged from the original pass |

**Nothing else in WO-062 changes.** The scored table, the three gates (dYdX perps-only, UBTC≠BTC,
Ontario restricted), the gas cost-model-shape finding, the integrity assessment, and the Track 2 gap
list at 40–60% of the Kraken adapter all stand as reported.
