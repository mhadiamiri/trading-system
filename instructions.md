# WO-062 — VENUE COMPARISON (expanded) + DEX FEASIBILITY SPIKE. Report-only. No code, no socket.
#
# The fee lever is the largest the death-certificate arithmetic identified. Kraken Tier 1 round trip
# 1.6216%; Hyperliquid spot taker ~0.070% => ~0.14% round trip, ~11.6x. Against the MEASURED moves
# (max 5-min 0.4076%, max 60-min 0.5388%, corpus_20260805), that regime CLEARS the bar Tier 1 did
# not. **The death certificate is regime-scoped and this is outside its scope — it is not
# contradicted, and nothing here re-opens it retroactively.**

BASE: current HEAD — **§1 reports actual HEAD; the WO does not pin a SHA** (three consecutive WOs
had a stale base by one report commit).
SCOPE: Track 1 venue comparison; Track 2 feasibility spike. **REPORT ONLY.**
SHIP IMPACT: **NO.** `git diff -- src/` must be empty (paste). No code. **NO SOCKET, no RPC, no
wallet, no key, no account creation anywhere.** Docs and published schedules only.
PARALLEL: does not block or delay the historical-data WO or hours-horizon prep.

**STANDING CONSTRAINTS (restated, not negotiable here):** spot only; **no live execution anywhere in
this phase**; no account-sharing or borrowed credentials in any system path; TRADING_ENV guard
semantics unchanged.

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.1e **Cite or declare-with-derivation, every figure.** The fee lesson: recall was 3.08x wrong and
     three parties shared it. Vendor fee schedules move.
0.5 Report every attempt.
0.6 AUTO MODE OFF.
0.11 Enumerate, do not assume the count.
0.12 Every observation offered as corroboration states its falsifier.
0.15 Margin-bearing declarations round up and say so.
0.16 **Any bound or comparison across two quantities states, at declaration, what mechanism generates
     each and whether they are simultaneous.** Cross-venue cost comparison is exactly this shape.
0.17 No basis, venue, or verdict enters the tree as a decision — this WO produces a comparison and a
     gap list, not an adoption.

---

## §1 CONFIRM STATE
Actual HEAD, `git diff -- src/` empty, gates green, both corpora verify. `phaseb_20260809` status
(informational — do not disturb).

---

# TRACK 1 — VENUE COMPARISON (report-only, cited)

## §2 THE CANDIDATE SET
**(a) Canada-registered CEXs**: Kraken (all tiers, our cited 17-tier table is already in the tree),
Coinbase, and **enumerate the others actually registered with the CSA/OSC — do not assume a list**
(0.11). State the registration status source and date.
**(b) ORDER-BOOK DEXs ONLY**: Hyperliquid (spot), dYdX, Injective/Helix. **AMMs and aggregators are
OUT OF SCOPE AS VENUES** — their fill model is incompatible with our CLOB apparatus (no resting
book to capture, no L2 depth, no maker/taker distinction in our sense). Record that exclusion and
its reason; it is a separate research track, not pursued.

**FIRST, A DISQUALIFIER TO CHECK, NOT ASSUME (0.11/0.1e):** the research doc lists dYdX under
"perpetual-futures". **Verify whether dYdX v4 offers SPOT at all.** If it is perps-only, spot-only
disqualifies it and the candidate set is smaller than the brief's three. Same check for each
candidate: **spot availability is a gate, not a score.** Perps are excluded on both constitutional
scope and Canadian retail restriction.

## §3 SCORING — five dimensions, each cited or derived

### 3.1 ALL-IN COST AT OUR TRADE SIZE — from actual quotes where obtainable
**Headline fees are insufficient**, per the research doc's own model:
`all-in = platform fee + pool fee + gas + price impact + failed-tx cost`.
- Use **0.1 BTC (~$6,460)** — the size every prior figure in this project uses, so the comparison is
  commensurable (0.16: same quantity, same size, or the comparison is meaningless).
- **Fees**: cited schedules, per tier, maker and taker, with the tier a $0-volume account can
  actually claim (the Tier 1 lesson — an optimistic tier is a cost assumption wearing a fact).
- **Gas**: **STRUCTURAL FINDING TO REPORT, not just a number.** Gas is **per-transaction**, our cost
  model is **percentage-of-notional**. At 0.1 BTC a $0.50 gas is 0.008%; at 0.001 BTC it is 0.8%.
  **Our cost model's SHAPE may need to change (proportional + fixed), not merely its parameters.**
  State this explicitly as an input to any future adoption WO.
- **Price impact**: from **published L2 depth at the touch** where obtainable, against 0.1 BTC.
  Cite the depth observation with its timestamp. If depth cannot be obtained without an account or a
  socket, **say so — do not estimate it** (this project's rule: a declared unknown beats a guessed
  figure).
- **Failed-transaction cost**: on-chain venues can charge for a reverted transaction. State whether
  each does, and at what.

### 3.2 L2 DATA QUALITY AND CAPTURE-ABILITY — **the sharpest dimension for us**
For each: is there a **public WebSocket L2 order-book feed**? At what depth and update cadence?
**And the question that decides everything: WHAT IS THIS VENUE'S INTEGRITY MECHANISM — its CRC32
checksum equivalent?** Kraken's book checksum is what makes our corpus trustworthy; a feed with no
integrity mechanism cannot support an equivalent corpus, and that is a **corpus-integrity concern,
not a convenience one**. If a venue has none, say so plainly and state what could substitute
(sequence numbers, snapshot cadence, independent re-derivation) and what it would NOT cover.

### 3.3 API MATURITY AGAINST OUR EXECUTION ABSTRACTION
Our execution layer is venue-abstracted — a swap should be a one-module change. Assess each against
that: order placement/cancel semantics, auth model, rate limits (cited), SDK availability, and
**whether execution requires local transaction signing** (on-chain venues do). Note that signing is
a materially different execution path from an API key — flag it as an architecture question, do not
resolve it here.

### 3.4 SPOT AVAILABILITY — a gate (§2). Record pass/fail and the cited source.

### 3.5 REGULATORY POSTURE — plain-language note, not legal advice
For **a Canadian resident using the protocol directly via a self-custody wallet**: what is the
venue's stated availability, and does it restrict Canadian users? **No VPN-dependent access paths.
A geo-blocked frontend is recorded as a SCORING FACT, not routed around.** State plainly where a
venue is unavailable, and note that protocol-level access via self-custody may differ from frontend
access — **record the distinction, do not adjudicate it.** Recommend qualified advice for anything
load-bearing.

## §4 TRACK 1 OUTPUT
A scored table plus a short narrative per venue. **No adoption recommendation is required** — the
brief says the output feeds the Sprint 3 venue decision, which is the lead's. If one venue clearly
dominates, say so and why; if the answer is "depends on X", name X.

---

# TRACK 2 — FEASIBILITY SPIKE (report-only, NO CODE)

## §5 For the top-scoring ORDER-BOOK DEX from Track 1
Question: **can our existing capture pipeline and cost model point at its WebSocket feed under the
venue abstraction's one-module swap?** Answer from **published schemas and docs only — no socket.**

Produce **the gap list**, in two explicit columns:

**WHAT CHANGES** — at minimum: message schema (subscribe shape, book update format, snapshot vs
delta); **integrity mechanism** (their equivalent of CRC32, or its absence — and if absent, what our
`checksum_failures_total` and the FR-018a resync semantics would even mean); symbol mapping;
timestamp semantics and resolution; sequence/gap detection primitives.

**WHAT TRANSFERS UNCHANGED** — assess honestly, do not assume: the gap ledger and its five ruled
causes, corpus discipline (segments, manifests, capture-time hashes), the default-deny reader,
force-flat/U2-U6 semantics, the cost model's **structure** (§3.1 flags that its SHAPE may need a
fixed-per-transaction term — say whether that is a structural change or a parameter).

**COST ESTIMATE for a capture-adapter WO**: rough, honest, with its basis stated. Compare against
the known cost of the Kraken adapter (which took most of Sprint 2).

## §6 WHAT THIS WO DOES NOT DO
No socket, no RPC call, no wallet, no key, no account. No code. No adoption. No re-opening of the
death certificate — its scoping is noted, and a new fee regime is a **new pre-registered question**
for a future WO, not a re-run of a closed one (0.8's shape: changing a cost assumption after a
verdict is the hazard; declaring a NEW question in a NEW regime, before any run, is not).

---

## §7 ACCEPTANCE
Candidate set enumerated with spot-availability gate applied and dYdX's spot status verified;
all-in cost per venue at 0.1 BTC with every component cited or declared-unknown; the gas
structural finding stated; integrity-mechanism answered per venue; API/signing assessment;
regulatory note with geo-blocks recorded as facts; Track 2 gap list in both columns with a costed
estimate; `git diff -- src/` empty; no socket/RPC/wallet/key/account; corpora untouched; gates green.

## §8 REPORT — `WO-062-REPORT.md`
Track 1 scored table + per-venue narrative, every figure cited with retrieval date; the gas
cost-model-shape finding; Track 2's gap list and estimate; every attempt; any STOP.

**THEN STOP.** Output feeds the Sprint 3 venue decision (the lead's).