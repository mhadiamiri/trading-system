# WO-065 — DEPTH READS (granted), INJECTIVE DOCS PUSH, and the dYdX DISQUALIFIER RECONCILIATION.
#
# Closes the last unmeasured term in the cost stack. After this, the venue decision is made on a
# complete table — the last gate before the native-capture spike.

BASE: current HEAD (§1 reports actual — do not pin a SHA).
SHIP IMPACT: **NO.** `git diff -- src/` empty (paste). No code.

## THE GRANT (lead, this turn) — read it as the boundary, not the budget
**ONE read-only order-book depth read per venue — dYdX, Hyperliquid, Injective — extended to UP TO
FIVE reads per venue** under §3's conditions. **Named public endpoints only. No order path. No
credentials. No wallet connection. Expiry 14 days from issue.**
**Everything else remains forbidden**: no socket capture, no key, no account, no order placement, no
code changes. The funding grant (WO-064 §3.2) is spent and closed; this is a separate, narrower one.
**Do not extend it to anything not named here** — WO-064 declined to grant itself an exception and
that is the standard.

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.1e Cite or declare-with-derivation. Unobtainable → **DECLARED UNKNOWN**, never estimated.
0.5 Report every attempt, including reads that failed or returned unusable depth.
0.6 AUTO MODE OFF.
0.11 Enumerate, do not assume the count.
0.12 Every observation offered as corroboration states its falsifier.
0.15 Margin-bearing declarations round up and say so.
0.16 Any comparison across two quantities states, at declaration, what mechanism generates each and
     whether they are simultaneous. **Depth read at venue A at 14:00 and venue B at 16:00 are NOT
     simultaneous — see §3.3.**
0.18 Jurisdiction and instrument type are recorded, never gates.
0.19 **A premise is a declared figure.** Every number states the order size it was computed at.

---

## §1 CONFIRM STATE
Actual HEAD, `git diff -- src/` empty, gates green, corpora verify. `phaseb_20260809` status
(informational; 23.9984 of 556 covered hours, leg 3 the operator's call, nothing blocks on it).

---

## §2 THE DELIVERABLE IS THE COST OF WALKING THE BOOK, NOT A SNAPSHOT (grant condition a)
For each venue, per read, compute and report:
2.1 **Cost of walking the book at $100 and at $200 notional** — the volume-weighted execution price
    against the touch, expressed as **basis points of slippage**. That is the quantity that enters
    the cost stack; **a level-1 screenshot is not the deliverable.**
2.2 **The same at the venue's own minimum order size** (dYdX ~$1, Hyperliquid $10, Injective UNKNOWN
    — if Injective's minimum is still unknown at read time, use $10 and label it as a stand-in, not
    a finding).
2.3 **Spread at the touch** in bps, and **cumulative depth** at each published level.
2.4 **State how many levels the venue published on that read** — Hyperliquid publishes 5 or 20, and
    if $200 walks past the published depth, **say so**: the cost is then a *lower bound*, not a
    measurement, and must be labelled that way.
2.5 Express every figure at the declared size (0.19). **Do not scale between sizes by assumption** —
    walking a book is non-linear, which is the whole reason this is being measured.

---

## §3 FIVE READS, TIMESTAMPED, ACROSS A STATED WINDOW (grant condition b)
**One instant is one regime — the eighth-scope-dimension lesson waiting to fire.**
3.1 **Up to five reads per venue**, spread across a **stated window of at least a few hours**,
    **ideally spanning a quiet and an active period.** Record the UTC timestamp of every read.
3.2 Report **per-read** figures and then the **range** (min/median/max) — not a mean alone. A mean
    spread across a quiet and an active period describes neither.
3.3 **0.16 applies to the cross-venue comparison.** Reads at different instants on different venues
    are **not simultaneous**, and BTC moves. State how you handled it: either read the three venues
    within a tight window of each other per round (preferred, and cheap — three requests), or declare
    the non-simultaneity as a bound on the comparison. **Do not compare a quiet-period read on one
    venue against an active-period read on another and call it a venue difference.**
3.4 **Characterise the regime of each read** — at minimum, note whether it fell in a quiet or active
    stretch and on what basis (recent price movement, observable volume). The verdict must state
    **which regime it measured**, exactly as every prior verdict in this project does.

---

## §4 THE INJECTIVE DOCS PUSH — weighted seriously, not as a courtesy
**The undervalued profile:** real `seq` + `block_height` is the **only native answer any candidate
has** to the problem we otherwise have to engineer around (Hyperliquid's checksum-free feed), and a
**maker rebate is the largest single lever in the stack** if the fill-model question is ever answered.
Four unknowns against that upside justifies one targeted pass.
Close, or declare unknown with the routes attempted enumerated (0.11): **minimum order notional and
increments**; **funding interval, rate mechanism and cap**; **terms of use** (the WO-060 discipline —
site-level, not just docs pages); **published book depth and update cadence**.
Routes to try beyond the docs site that 301'd: the Injective GitHub org and `injective-proto`, the
Python/TypeScript SDK repos and their docstrings, the indexer/gRPC API reference, Helix's own docs,
any published protocol spec or governance parameter listing. **If a parameter is on-chain rather than
documented, say so** — that is a finding about where the truth lives, not a failure.

---

## §5 THE RECONCILIATION — required before the ranking can carry a venue decision
**D-r51 ruled dYdX's non-canonical book DISQUALIFYING for strategies that read the book** — *"the
correct order book at any given time is whatever the current block proposer has in its mempool"*.
**WO-064 now ranks dYdX first.** The record cannot carry an unreconciled prior disqualifier into a
venue decision.

**Write one paragraph stating which of these resolved it:**
- **(a)** The investigation found the integrity route (per-level `offset`, full-node L3 + block height
  + `execModeFinalize`) **answers** the canonical-book problem — in which case state precisely *what
  it answers and what it still does not*, since WO-063 held that CRC32's question has no referent
  there and that **semantic mismatches are silent where integrity failures are loud**; or
- **(b)** The target strategy class **reads trades/prices rather than book state**, so the
  disqualifier was scoped to a class we are not building — in which case **state that scope
  explicitly**, and note the consequence: **a future strategy that reads book state on dYdX
  re-triggers the disqualifier**, and that constraint must travel with the venue decision.

**Either answer is acceptable. An unstated one is not.** Ops flags that (b) is the likelier honest
answer and it carries a real cost — it constrains the strategy class *before* the suite is
pre-registered — so it should be stated as a constraint, not a clearance.

---

## §6 OUTPUT — the complete cost stack
Restate §9's decision table with **price impact filled in** for all three candidates at $100/$200,
per-read range and regime labelled, plus Injective's closed or still-unknown cells.
**Then: which venue leads on a fully measured stack, by how much, and what remains unknown.**
State plainly whether price impact **changes the leader** — at a 0.0115% margin between dYdX and
Hyperliquid, a few basis points of impact difference decides it, and that is precisely why this
grant was worth spending.

## §7 ACCEPTANCE
Book-walk cost at $100/$200 and at venue minimum, per venue, per read, in bps; ≤5 reads per venue
with UTC timestamps across a stated window; per-read figures plus range, not mean alone;
non-simultaneity handled and stated; regime characterised per read; published-level count stated and
lower-bound labelling where depth is exceeded; Injective's four cells closed or declared unknown with
routes enumerated; **the §5 reconciliation paragraph written**; decision table restated with impact
filled; `git diff -- src/` empty; **no order path, no credentials, no wallet, no code**; gates green.

## §8 REPORT — `WO-065-REPORT.md`
Per-read tables with timestamps and regimes; the book-walk costs; Injective's outcome with routes
attempted; **the reconciliation paragraph**; the complete decision table; the leader and what could
still overturn it; every attempt; any STOP.

**THEN STOP.** Next: the venue decision (the lead's), then the native-capture spike on the chosen venue.