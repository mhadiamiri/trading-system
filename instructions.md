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

## §3.5 — ADDED SCOPE: THE 14-PLATFORM CANADIAN CEX FEE SWEEP
WO-062's closeout obtained the authoritative Ontario enumeration from the OSC page
(`osc.ca/en/industry/registration-and-compliance/crypto-businesses`, HTTP 200, self-dated
2026-07-30, retrieved 2026-08-10): **14 registered crypto asset trading platforms.**

**This is a lever available TODAY with zero integration work**, and it has never been checked.
Kraken's 0.80% Tier 1 taker is the number that killed the minutes-horizon class. If any registered
Canadian CEX is materially cheaper at zero volume, that changes the arithmetic without a single line
of DEX adapter code.

For **each of the 14**, report from its **published fee schedule** (0.1e — cited, with URL and
retrieval date; **DECLARED UNKNOWN** where no public schedule exists, never estimated):
- **Taker and maker at the ZERO-VOLUME / entry tier** — the tier an account with no history can
  actually claim. **Not the best advertised tier** (the Tier 1 lesson: an optimistic tier is a cost
  assumption wearing a fact's clothing).
- **BTC/CAD and BTC/USD availability**, and which pairs are quoted — a venue offering only CAD
  introduces an FX leg, which is a **different quantity** and must be flagged under 0.16, not folded
  into the fee comparison.
- **Spread or markup practices**, if published — several retail Canadian platforms embed cost in the
  spread rather than charging a visible fee, and **a 0% fee with an embedded 1% spread is more
  expensive than Kraken.** Report the published mechanism; if a platform's real cost is not
  determinable from published documents, **say so** — that is itself a finding about the venue.
- **Whether a public market-data API and WebSocket L2 book feed exist at all.** A cheap venue we
  cannot capture from is not a candidate for this apparatus; note it as a fact per venue.
- **VirgoCX is SUSPENDED** (effective 2025-11-24, per the same OSC table) — exclude it and say why.

**The deliverable:** a 14-row table sorted by entry-tier taker fee, with Kraken's 0.80% marked as the
incumbent, and a one-line statement of **which platforms (if any) are materially cheaper AND have a
capturable feed.** If none are, that is a clean finding and it strengthens the DEX case.

**Scope limit to restate in the report:** the OSC table is **Ontario-scoped**, so a platform
registered elsewhere in Canada but not in Ontario would not appear. Authoritative for Ontario, not
established Canada-wide. Per 0.18 this is recorded, not scored.

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
Three DEXs attempted, Injective's docs sought via enumerated alternative routes; spot and perps both
scored where they exist; funding characterised or declared unknown, with its time-dimension
implication for the cost model stated; feed integrity answered per venue including dYdX's Cosmos
primitives; depth threshold stated; signing/preflight gap noted; **all 14 OSC-registered platforms
swept with entry-tier fees cited or declared unknown, spread-embedding practices reported, feed
availability noted per venue, VirgoCX excluded as suspended**; jurisdiction recorded and not scored;
`git diff -- src/` empty; no socket/RPC/wallet/key/account; corpora untouched; gates green.

## §7 REPORT — `WO-063-REPORT.md`
The DEX scored table with every figure cited or declared unknown; the funding finding and its
cost-model implication; per-venue integrity verdicts; the 4-hour-hold all-in comparison against
1.6216%; **the 14-row Canadian CEX table sorted by entry-tier taker fee with the cheaper-AND-
capturable statement**; every attempt; any STOP.

**THEN STOP.** Output feeds the Sprint 3 venue decision.