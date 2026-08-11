# WO-064 — HF INVESTIGATION: close the unknowns. Report-only, no socket.
#
# D55 ratified: HIGH-FREQUENCY SHORT-HOLD is the target class; hours-horizon demotes to fallback.
# Constitutional amendment ratified in narrow form: **PERPETUALS AT 1x LEVERAGE, NOTIONAL FULLY
# COLLATERALIZED, NO MARGIN MULTIPLIER, FUNDING MEASURED AS A COST. LEVERAGE >1x EXCLUDED ABSOLUTELY.**
# Death certificate SCOPED: WO-053 stands for Tier-1 taker (1.6216%) in the measured quiet regime and
# does NOT extend to a ~0.09% regime. Citing it universal is misciting it.

BASE: current HEAD (§1 reports actual — do not pin a SHA).
SCOPE: report only. **NO socket, NO RPC, NO wallet, NO key, NO account, NO code.** `git diff -- src/`
empty (paste). Docs, published schedules and published historical rate data only.
SHIP IMPACT: **NO.**

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.1e Cite or declare-with-derivation. Unobtainable → **DECLARED UNKNOWN**, never estimated.
0.5 Report every attempt.
0.6 AUTO MODE OFF.
0.11 Enumerate, do not assume the count.
0.12 Every observation offered as corroboration states its falsifier.
0.15 Margin-bearing declarations round up and say so.
0.16 Any comparison across two quantities states, at declaration, what mechanism generates each and
     whether they are simultaneous.
0.18 Jurisdiction and instrument type are RECORDED, never gates.
0.19 **NEW, AND IT GOVERNS THIS WO (D55): A PREMISE IS A DECLARED FIGURE LIKE ANY OTHER.** 0.1 BTC was
     a Sprint-2 assumption that traveled unexamined through every later figure and turned the DEX
     comparison's "largest open term" into an artifact of itself. **Every figure in this WO states the
     ORDER SIZE it was computed at, and the size is declared at the top, not inherited.**

---

## §1 CONFIRM STATE + DECLARE THE SIZE
Actual HEAD, `git diff -- src/` empty, gates green, corpora verify. `phaseb_20260809` status
(informational — leg 3 is the operator's call, nothing here blocks on it).

**DECLARE THE ORDER SIZE ALL FIGURES USE** (0.19). Operator capital is **$100-200**. State the
per-order notional you compute at and why — and note explicitly that **the prior 0.1 BTC (~$6,460)
basis is retired for this WO** and every carried-over figure must be recomputed, not scaled by
assumption.

---

## §2 MINIMUM ORDER SIZE AND INCREMENT — a HARD DESIGN CONSTRAINT at $100
Per venue and instrument: **minimum order notional, minimum quantity increment, and minimum price
tick.** Cited, per market (BTC specifically — do not generalise from a venue-wide statement).

**Why this is first:** at $100 with a $10 minimum, the account holds **at most 10 concurrent
positions**, and that bounds every strategy shape before a signal is designed. State, per venue:
**how many concurrent minimum-size positions $100 and $200 permit.** If a venue's minimum makes
high-frequency operation impossible at this capital, that is a **disqualifier on arithmetic** — the
first legitimate one in this comparison, and it must be distinguished from the assumption-based
disqualifiers WO-062 got wrong.

---

## §3 FUNDING — MEASURED FROM PUBLISHED HISTORY, AS A DISTRIBUTION
Ops's honest form, ratified: funding for short holds is a **low-probability, bounded-magnitude
event, NOT zero and NOT continuous.** A hold that straddles a funding timestamp pays the full
interval; one that doesn't pays nothing.
3.1 Per venue: funding interval, how the rate is set, and the **cap**.
3.2 **Obtain published HISTORICAL funding rates for BTC** — Hyperliquid and dYdX both publish them.
    Report the **distribution**: median, p95, p99, max, and **how often the rate approached the cap**.
    A mean says nothing about what a hold costs on a bad day.
3.3 **Compute the expected funding cost for a hold of duration D**, for D in {1 min, 5 min, 15 min,
    60 min}, at the declared order size. **State the mechanism (0.16): funding is charged at discrete
    timestamps, so the probability a hold of duration D straddles one is D/interval** — state that
    derivation rather than assuming proportionality.
3.4 **The number that matters: at the declared size and target hold duration, is expected funding
    small, comparable to, or larger than the fee round trip?** If unobtainable, DECLARE UNKNOWN.

---

## §4 GAS AT SMALL SIZE — now decisive
Gas is **FIXED PER TRANSACTION**, so it scales inversely with order size. At 0.1 BTC a $0.50 gas is
0.008%; **at $100 it is 0.5%, larger than every fee under discussion**, and at high frequency it
compounds per trade.
4.1 **Hyperliquid**: WO-062 established trading is gas-free — **re-confirm with a citation**, and
    state what (if anything) does cost gas (deposits, withdrawals, bridging).
4.2 **dYdX v4**: gas at small order size is **UNKNOWN and load-bearing**. Obtain it.
4.3 **Injective**: same.
4.4 Per venue, express gas as a **percentage of the declared order size**, and state the order size
    at which gas equals the fee — the **break-even size below which gas dominates.**

---

## §5 THE NON-CANADIAN VENUES — score them (0.18: the frame was never a constraint)
**Binance, Bybit, OKX**, spot and perps. Cited entry-tier maker/taker at zero volume, minimum order
size, gas (nil — centralised), feed integrity mechanism, depth and cadence, API maturity.
**Note for Binance: we already hold nine years of its data, checksum-verified 229/229 and bridged to
our own capture at r=0.9991.** That is a real asset for that candidate and should be weighed —
a venue whose historical basis is already admitted starts ahead.

---

## §6 HYPERLIQUID'S INTEGRITY-MITIGATION DESIGN (D55 requires it before any capture there is trusted)
Hyperliquid leads on cost and has **no checksum, no sequence number, 5/20 levels, >=0.5s cadence** —
and **this matters MORE at high frequency**, since an HF signal reads the book constantly.
**Design the replacement, declared before any capture is trusted.** Candidates to evaluate, and
enumerate others (0.11):
- **trade-print reconciliation** — do executed trades on the trade channel reconcile against the
  book's stated levels? A book that disagrees with its own prints is detectably wrong.
- **cross-feed consistency** — two independent connections compared.
- **staleness bounds** — a declared maximum age beyond which a snapshot is refused.
- **snapshot re-request cadence** as a periodic ground truth.
For each: **what it detects, what it CANNOT detect, and what the corpus's equivalent of
`checksum_failures_total` would be.** State plainly whether any combination gives an integrity
guarantee comparable to CRC32, or only a weaker property — **and say which weaker property.**
Recall the WO-063 line: *integrity failures are loud; semantic mismatches are silent.*

---

## §7 MAKER ECONOMICS — priced, so park-or-build is decided on numbers
D51 parked maker execution because an unvalidated queue-position fill model is fiction. **That
reasoning still holds; the prize has grown.** Hyperliquid maker 0.015%; **Injective -0.005% (a
REBATE — you are paid).** At high frequency, maker-vs-taker may exceed venue-vs-venue.
**Deliverable: what would VALIDATING a maker fill model require on the leading venue, PRICED.**
What data (queue position observable? fill-time distributions? cancel/replace latency?), what
capture, what bite proofs, what WO count — so the decision is made on cost, not on instinct.
**Do not build or assume a fill model here.**

---

## §8 RECORD THE AMENDMENT AND THE LADDER
8.1 Write the constitutional amendment as an artifact, dated and reasoned: **perpetual contracts at
    1x leverage, notional fully collateralized, no margin multiplier, funding measured as a cost;
    leverage >1x excluded absolutely.** Reasoning: at 1x the economic exposure is spot-equivalent, so
    the instrument choice is a fee-and-access decision rather than a leverage decision.
8.2 Record the **$100 live-instrument ladder** (D55), so it is not relitigated: a small live run
    becomes a legitimate measurement instrument — **not a deployment** — only when (a) the venue is
    chosen with integrity mitigations declared and native capture validated; (b) a **pre-registered**
    strategy has passed on that venue's own captured data with cited all-in costs; (c) the execution
    path carries the standard guards bite-proved (kill switch, position cap, TRADING_ENV semantics
    adapted to the venue). **The apparatus is what makes $100 buy knowledge instead of noise.**
8.3 Record the death-certificate scoping note where a future reader will hit it.

---

## §9 OUTPUT — the decision table
One table, all candidates (Hyperliquid, dYdX, Injective, Binance, Bybit, OKX), spot and perps,
**at the declared order size**, with: all-in round-trip cost including gas and expected funding for
the target hold duration; minimum order size and max concurrent positions at $100/$200; feed
integrity mechanism and its verdict; depth/cadence; maker rate or rebate.
**Then one sentence: which venue leads, on what, and what unknown could still overturn it.**

## §10 ACCEPTANCE
Order size declared and every figure computed at it (0.19); minimums enumerated per venue with the
concurrent-position arithmetic; funding measured as a distribution from published history with the
straddle derivation stated, or declared unknown; gas per venue as a percentage of the declared size
with the break-even size; the three non-Canadian venues scored; Hyperliquid's integrity-mitigation
design with what each candidate cannot detect; maker validation priced; the amendment, the ladder and
the scoping note recorded; `git diff -- src/` empty; no socket/RPC/wallet/key/account; gates green.

## §11 REPORT — `WO-064-REPORT.md`
The declared size; the decision table; every figure cited or declared unknown; the funding
distribution and straddle derivation; gas break-even sizes; the integrity-mitigation design with its
limits; the maker pricing; the three recorded artifacts; every attempt; any STOP.

**THEN STOP.** Next: venue chosen with its integrity design → native capture → pre-registered HF
suite on venue data → the $100 instrument under D55's three conditions.