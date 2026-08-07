# WO-048 — THE FIRST HONEST BACKTEST — REPORT

**Date:** 2026-08-07
**Base HEAD:** `1736264` (WO-047 investigation committed) → build commit `af837c9`
**Pre-capture CI:** run **`31205003045`**, both legs green, **338 passed / 2 skipped**
(`test (3.14)` job 92953743238 · `test (3.11)` job 92953743160 — counts from the job logs)
**SHIP IMPACT: YES.**

---

> ## §7.3 REQUIRED HEADER
>
> **This backtest evaluated `BookImbalanceStrategy`, NOT `TrivialMomentumStrategy`.** The corpus is
> top-of-book and does not carry `last_price` / `total_volume` / `trade_count`; substituting them
> would produce a number by redefining what was measured (D48, U1). `TrivialMomentumStrategy`'s
> evaluation is **DEFERRED, blocked on a trade-channel re-capture.**

---

# ⚠ THE RESULT — REPORTED AS PRODUCED, AND IT IS NOT A P&L

```
segments_run                     21          segments_excluded    0
trades                        3,498,075      coverage_fraction    1.0  (not truncated)
gross_pnl                   764,993,334.67
total_fees                   22,572,628.06
total_slippage_cost          22,572,628.06
total_spread_cost_attribution     71,831.95   (attribution, never additive)
total_costs                  45,145,256.13
net_pnl                     719,848,078.54
force_flattenings                21
```

**Net P&L +$719,848,078.54 on 3,498,075 trades of 0.1 BTC.**

**That number is meaningless, and I am reporting it rather than repairing it.** §0.8 and §7.5 are
explicit: whatever the number is, report it; do not revise and re-run. The defects below are
accounting defects, not parameter choices — but fixing them and re-running *after seeing this
number* is the same epistemic hazard §0.8 exists to prevent. **No second run was performed. The
parameters were not touched.**

What the number actually measures is diagnosed in the next section. **D48 asked for a trustworthy
measurement apparatus rather than a verdict on a rule. This run shows the apparatus is trustworthy
for the property it was built to guarantee — segmentation and anti-splice — and NOT yet trustworthy
for P&L.** That is a real result, and it is the honest one.

---

## WHY THE NUMBER IS NOT A P&L — FOUR DEFECTS

### DEFECT 1 (MINE, introduced in this WO) — the force-flat is a PHANTOM

`SegmentedBacktestRunner._run_segment` flattens with
`dataclasses.replace(position, current_quantity=0)` and **executes no closing trade**. The position
is zeroed; its economics are discarded. Every one of the 21 segments ended this way.

So U2's force-flat is **labelled but not economically executed**. The P&L omits the entire
cost and proceeds of closing every segment.

**My §6.1 bite proof did not catch this**, and I want that on the record: it asserted the boundary
event is *recorded* and carries a non-zero quantity. It never asserted that a closing *trade*
occurred. A proof that checks the label and not the effect is exactly the gap this project's bite
discipline exists to close, and mine had it.

### DEFECT 2 (PRE-EXISTING) — the risk engine does not bound CUMULATIVE position

`DeterministicRiskEngine.check` clamps the **order** to `max_position_btc` (default 1.0 BTC) but
**never reads `current_state.current_quantity`** — verified:

```
uses current_state.current_quantity: False
clamps ORDER size only:              True
max_position default:                1.0
```

So 0.1 BTC orders accumulate without limit. Segment 18 alone placed **738,510 trades**. Nothing in
the risk path objects. This touches **Principle VI (Risk Engine Is Sovereign)** — a max-position
limit that bounds each order but not the position is not a position limit.

It is pre-existing and predates this WO. It has never mattered before because no prior run placed
millions of orders.

### DEFECT 3 (PRE-EXISTING, DECLARED) — `gross_pnl` is unmatched cash flow

The aggregate follows `PnLReport`'s formula: `+notional` for SELL, `−notional` for BUY, with no
position matching, no cost basis, no mark-to-market. `report.py:104` says so in as many words:
*"Calculate gross P&L (simplified for walking skeleton)"*.

Over a handful of trades that is a crude but bounded approximation. Over **3.5 million unmatched
trades** it is a sum of notionals whose sign is an artefact of the BUY/SELL mix, not an economic
result. 16 segments positive, 5 negative, range −174,211,033 to +365,031,015.

### DEFECT 4 (COSMETIC, but it hides things) — fees and slippage are numerically identical

`total_fees == total_slippage_cost` exactly. Both are `notional × rate`, and the default fee rate
(0.1%) and slippage factor (0.001) coincide. Not a bug, but it makes two independent cost channels
indistinguishable in any output, and a genuine divergence between them would be invisible.

### And the trade rate itself

**3,498,075 trades over 3,847,530 frames = 90.9% of all ticks.** The strategy has no position
awareness and no throttle: it emits a `DesiredPosition` on *every* tick whose smoothed imbalance
exceeds T, and BTC/USD top-of-book is persistently imbalanced. This is a property of the strategy as
declared, not a defect — but it is why the defects above compound so violently.

---

## ✅ WHAT THE RUN *DOES* PROVE — the apparatus, at corpus scale

The segmentation guarantees held on real data, and this is the part that transfers:

| Property | Evidence at corpus scale |
|---|---|
| Every segment force-flattened (U2) | `force_flattenings = 21` of 21 segments |
| **Anti-splice held (U3+U4)** | **`first_trade_frame_index` ≥ 100 on every one of 21 segments** (values: 100 ×19, 108, 156) |
| Full coverage, no silent truncation (D-c) | `coverage_fraction = 1.0`, `truncated = False`, `max_events = None` |
| Eligibility bound applied (U3) | 0 segments excluded — all 21 exceeded 1,000 frames, as predicted |
| Read-only (6.4) | corpus digest **identical** before and after |

**The anti-splice column is the headline result of this WO.** A cold segment cannot trade before
frame 100 (the window must fill on its own data). Every segment's first trade landed at frame 100 or
later — 19 at exactly 100, one at 108, one at 156. **No segment traded on data it could not have
seen.** That is D20's guarantee holding across 3.85 million real frames and 20 real discontinuities.

**Frame accounting:** 3,847,530 frames processed against the manifest's 3,847,540 — a difference of
**10 frames**, which are the frames lying *inside* recorded gaps. The loader read them from disk and
discarded them, which is precisely §3's containment working.

---

## §1 CONFIRM STATE

HEAD `1736264`, `git diff -- src/` empty, corpus digest `a025db1e…` snapshotted before any work.
Baseline 322 both interpreters (CI `31191726876`).

---

## §2 THE STRATEGY — `BookImbalanceStrategy`

`imbalance = (bid_qty − ask_qty) / (bid_qty + ask_qty)` ∈ [−1, +1], rolling mean over N ticks;
BUY ≥ +T, SELL ≤ −T, else HOLD. It consumes `bid_qty`/`ask_qty` — data only a BOOK corpus carries —
so it is the natural consumer of this artifact and cannot be mistaken for the trivial strategy.
Mid-price momentum was rejected as structurally the substitution D48 forbids.

### §2.2 PRE-REGISTERED PARAMETERS

> **These values were fixed before the run and not revised after.**

| Parameter | Value | Derivation |
|---|---|---|
| `WINDOW_TICKS` | **100** | The established house convention: `TrivialMomentumStrategy` already keeps its rolling volume history at exactly 100 samples (`trivial.py:85-86`). Reusing the house number means the window was not selected *for this data*. |
| `THRESHOLD` | **0.20** | A round, untuned value on a scale bounded a priori — imbalance is in [−1, +1] by construction, so 0.20 is one-fifth of the available range. Not derived from this corpus; no alternative was evaluated. |
| `ORDER_SIZE_BTC` | **0.1** | Identical to the trivial strategy's fixed size (`trivial.py:70`). §2.3 requires fixed; sizing would be another free parameter. |

Not swept. Not optimised. Not revised after seeing the result above.

**§2.4 degenerate ticks:** `bid_qty + ask_qty == 0` → HOLD, no division attempted, and **not**
imbalance `0.0` — zero resting size on both sides is an *absence* of information, not a balanced
book. Proved by `test_a_degenerate_tick_holds_without_dividing`, which also asserts the tick does
not enter the rolling window.

---

## §3 THE FRAME LOADER + `BookState`

**The missing-fields decision: a BOOK-ONLY STATE TYPE, not an optional-field `MarketState`.**

With `Optional` fields, a strategy can still write `state.last_price`, receive `None`, and the next
author who wants the code to run writes `or self._mid` — the fabrication returns in one line, in a
strategy file, far from this decision. `BookState` has **no such attribute at all**, so reading one
raises `AttributeError`. **The absence is the guarantee.**

`MarketState` is **deliberately untouched**. Widening it would weaken the guarantee for every
existing consumer in order to serve one new one, and §3 warns that a `MarketState` change resembling
a substitution in disguise is a STOP.

`compute_execution_costs` transfers **unchanged** — it reads only `best_bid`, `best_ask`, `spread`,
`mid_price`, all genuinely observed, and binds structurally (its `MarketState` annotation is
`TYPE_CHECKING`-only).

**Loader:** streaming, never materialising 3.85 M objects; takes a `CorpusReader`-issued
`CorpusWindow` and **cannot be pointed at raw files** — the enforcement point that makes default-deny
unbypassable rather than merely impolite. Frames inside gaps are read and discarded.

### A defect found and fixed during the build

The loader would have **silently yielded zero frames** for a segment whose `run_id` could not be
resolved (a window starting before the run's own emission bounds). An empty stream is
indistinguishable from an honest empty window and would have produced a clean, entirely wrong
backtest. It now refuses with `CORPUS_FRAMES_UNRESOLVED_RUN`.

---

## §4 THE SIX RULINGS AS BUILT

- **U1** — `BookImbalanceStrategy` runs; `TrivialMomentumStrategy` recorded as
  **blocked-on-trade-channel**, deferred not dropped (added to `progress.md`).
- **U2** — force-flat at every boundary, **no duration threshold**, as a labelled event carrying its
  **declared cost** (a 1.7 s reconnect flattens where a real trader would not — conservative in a
  stated direction). ⚠ See DEFECT 1: the label is emitted, the closing trade is not.
- **U3** — **fresh strategy instance** per segment (stronger than a `reset()` someone must call
  correctly) plus a declared minimum eligible length = warm-up × safety factor 10 = **1,000 frames**.
  Not binding on this corpus (0 exclusions), declared anyway so a future reconnect-burst corpus is
  refused by a stated bound rather than saved by accident.
- **U4** — first tick of every segment observation-only. One tick, no parameter.
- **U5** — per-segment results plus a declared aggregate that **states its own dependency** in the
  output: *the sum is meaningful ONLY BECAUSE U2 makes every segment start and end flat.*
- **U6** — `KEEPALIVE_RECONNECT` / `VENUE_DISCONNECT` bounded at **60 s** (observed maxima 16.863 s /
  3.287 s), with the **re-declaration trigger** stated: if a future corpus's gaps approach ~30 s,
  re-derive rather than rely on it. `PROCESS_RESTART` acknowledged **to segment at, never to trade
  across**. `accept_open_ended` set nowhere. Structural note recorded: **acknowledgment governs
  READING, force-flat governs TRADING — acknowledging more never buys a more continuous backtest.**

---

## §5 THE FOUR DEFECTS — FIXED

- **D-a** — **market time is the trade timestamp.** Was `datetime.now(UTC)`, so no backtested trade
  could be reconciled against the frame it was priced from and Principle VIII failed at the backtest
  boundary. Now the state's own timestamp; the replay clock rides along as `replay_timestamp`,
  secondary, on both the `Fill` and the `place_order` dict. A state with **no** timestamp now
  **raises** rather than falling back to `now()`, which would silently restore the bug.
- **D-b** — the staleness guard's inertness under replay is **declared where the guard is defined**,
  with the equivalence stated: it protects the live path; U3/U4's segment machinery is the analogous
  replay protection; neither substitutes for the other.
- **D-c** — `max_events` is **explicit-or-all**, default `None`. Was 1000, silently covering 0.026%.
  Every run now reports `coverage_fraction` and `truncated`.
- **D-d** — the §3 loader.

---

## §6 BITE PROOFS — `tools/wo048_antisplice_bite_proof.py` — **VERDICT: PASS**

| Artifact | Result |
|---|---|
| 1 — PRISTINE | 16 passed |
| 2 — **MUTATION A** (U3: one strategy instance reused across segments) | BITE fails; **all 8 duals pass** |
| 3 — **MUTATION B** (U4: first tick made fillable) | BITE fails; **all 8 duals pass** |
| 4 — RESTORED | 16 passed |
| sha256 exact-restore | `43d04678af0e19d20c3e0e0ffe8358362b360f58ba0a4112ec4d3844ee2cc9b4` **IDENTICAL** |

```
MUTATION A discriminates (bite fails, duals hold): True
MUTATION B discriminates (bite fails, duals hold): True
```

### The bite proof caught a weakness in my own test

Mutation A initially **did not discriminate** — all 16 tests passed with a runner leaking strategy
state across every segment. My "anti-splice" assertion constructed a fresh strategy locally and
checked `fresh.warm is False`, which tests the **constructor**, not the runner.

Replaced with a real discriminator: each segment records `first_trade_frame_index`, and a cold
segment cannot trade before frame `WINDOW_TICKS` (the observation-only tick still feeds the window,
so the earliest honest frame is exactly 100), whereas a leaking segment trades on frame 2. This is
what necessity mutations are for, and it is reported rather than quietly corrected.

**6.2 loader containment**, **6.3 D-a market time**, **6.4 read-only** — all covered in
`tests/test_segmented_backtest.py` (16 tests).

---

## §7.4 THE METRIC, STATED IN FULL

> **Net "P&L" of +$719,848,078.54 over 36.8867 h of verified continuous market data, in 21
> independent segments, flat at every boundary, excluding 0.0167 h of in-run gaps and 2.1061 h of
> inter-run seam. 3,498,075 trades. Coverage fraction 1.0 (untruncated). 0 segments excluded by the
> 1,000-frame eligibility bound.**

**What this number explicitly is NOT:**

- **NOT a P&L.** See DEFECTS 1–3: no closing trade at flattening, no cumulative position bound, and
  an unmatched-cash-flow formula. It is a sum of notionals.
- **NOT a 39-hour continuous backtest.** 36.8867 covered hours in 21 segments; the elapsed span was
  ~39.0 h and the difference is gap and seam time that contains no data.
- **NOT a strategy verdict.** 21 forced flattenings are an artefact of the data's discontinuities.
- **NOT a tradeable-edge estimate.** It has no economic interpretation whatsoever.

---

## §8 ACCEPTANCE

- [x] Six rulings implemented · four defects fixed · bite proofs with discriminating mutations
- [x] CI green both legs **before** the run (`31205003045`, counts from job logs)
- [x] Corpus digest unchanged — `a025db1e…` identical at open and close
- [x] Parameters pre-registered and **unchanged**; no second run
- [x] Report carries the §7.3 header and the §7.4 full metric
- [x] Test count with arithmetic: **322 + 16 = 338**, both interpreters, both orders
- [x] lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

---

## STOP — AND WHAT THE LEAD MUST RULE

Per §7.5 the number stands. Per §0.1 (code wins: STOP and report) the defects are reported, **not
repaired in this WO** — repairing them and re-running after seeing this number is exactly the hazard
§0.8 forbids.

| # | Defect | Owner |
|---|---|---|
| **R1** | Force-flat executes no closing trade — U2 is labelled but not economically executed. **Mine, this WO.** | needs a fix WO |
| **R2** | Risk engine bounds order size but not cumulative position (Principle VI). **Pre-existing.** | needs a ruling: is this the intended reading of the max-position limit? |
| **R3** | `gross_pnl` is unmatched cash flow, not P&L. **Pre-existing, self-declared "walking skeleton".** | needs a real P&L engine before any number means anything |
| **R4** | Fees and slippage numerically identical under default rates — two channels indistinguishable. | cosmetic; worth separating |

**The apparatus's segmentation guarantees are proven at corpus scale** — that is this WO's real
product, and it survives the P&L defects entirely. The next number will only be worth reading once
R1–R3 are closed.
