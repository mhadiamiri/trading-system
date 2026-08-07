# WO-050 — BACKTEST ACCOUNTING + THE SECOND RUN — REPORT

**Date:** 2026-08-07
**Base HEAD:** `b459f2b` (WO-049) → build commit `605a4e6`
**Pre-run CI:** run **`31214886348`**, both legs green, **436 passed / 2 skipped**
(`test (3.14)` job 92985983519 · `test (3.11)` job 92985983478 — counts from the job logs)
**SHIP IMPACT: YES.** Corpus digest `a025db1e…` identical at close.

---

> **Which strategy, and why not the trivial one (WO-048 header, D48):**
> **This backtest evaluated `BookImbalanceStrategy`, NOT `TrivialMomentumStrategy`.** The corpus is
> top-of-book and does not carry `last_price` / `total_volume` / `trade_count`; substituting them
> would produce a number by redefining what was measured (D48, U1). `TrivialMomentumStrategy`'s
> evaluation remains **DEFERRED, blocked on a trade-channel re-capture.**

---

# THE SECOND NUMBER

```
method                        average_cost
segments_run                            21     segments_excluded         0
trades                             129,695     boundary_closes          21
coverage_fraction                      1.0     truncated             False

realised_pnl                     +39,057.26
total_fees                     2,179,231.85
total_slippage_cost               83,816.61
total_spread_cost_attribution      2,814.11    (attribution, never additive)
total_costs                    2,263,048.45
──────────────────────────────────────────
NET P&L                       −2,223,991.19
──────────────────────────────────────────
unrealised_residual                      0     force_flattenings        21
```

## **NET P&L: −$2,223,991.19. The strategy loses money.**

Reported as produced, per §7.4. No parameter was revised and no second attempt was made.

### What the number says

The strategy has a **small positive gross edge that transaction costs annihilate**:

| | |
|---|---|
| gross realised edge | **+$39,057.26** |
| total costs | **$2,263,048.45** |
| **costs ÷ gross edge** | **57.9×** |
| gross edge **per trade** | **$0.3011** |
| fee cost **per trade** | **$16.8027** |
| fees as a share of costs | **96.3%** |

Each trade is 0.1 BTC ≈ $6,460 of notional. At 0.26% that is $16.80 of fee, against 30 cents of
captured edge. **The strategy earns about 1.8% of its own transaction cost.** It is not marginal —
it is off by a factor of ~56 per trade.

That is a real finding about book-imbalance-at-this-threshold on this data, and it is exactly the
kind of verdict the apparatus was built to be able to produce honestly.

---

# BEFORE / AFTER — WO-048 vs WO-050 (§7.3)

**WO-048's number is NOT superseded.** It remains the record of what this apparatus produced under
those defects (D49). The comparison attributes the difference; it does not overwrite it.

| | WO-048 | WO-050 | driver |
|---|---:|---:|---|
| trades | 3,498,075 | **129,695** | WO-049 position cap (−96.3%, 27.0× fewer) |
| boundary closes | **0** | **21** | R1 |
| reported P&L figure | unmatched cash flow | realised (average cost) | R3 |
| gross / realised | 764,993,334.67 | **39,057.26** | position cap + R1 |
| total fees | 22,572,628.06 | **2,179,231.85** | trade count × rate (R4) |
| total slippage | 22,572,628.06 | **83,816.61** | trade count × rate (R4) |
| **net** | **+719,848,078.54** | **−2,223,991.19** | all of the above |

### The cost attribution decomposes exactly

Normalising per trade separates the **trade-count** effect from the **rate** effect:

```
fees/trade       6.4529 -> 16.8027   ratio 2.6039   (rate ratio 0.26/0.1   = 2.6000)
slippage/trade   6.4529 ->  0.6463   ratio 0.1002   (rate ratio 0.0001/0.001 = 0.1000)
```

Both ratios match their rate ratios to three decimals. **The entire cost difference is (trade count)
× (rate) and nothing else** — no unexplained residual, and the two channels are now visibly
distinct (fees are 26× slippage, where they were identical to the cent).

### The single largest driver is WO-049, not WO-050

The 27× trade-count reduction comes from the **aggregate position cap**, not from this WO. Under the
old per-order clamp the position accumulated without bound and the strategy traded on 90.9% of all
ticks; with the cap binding at 1.0 BTC, orders that would exceed it are vetoed. Trade rate fell from
90.9% to **3.4%** of frames. Everything downstream — gross, fees, slippage — scales with that.

### ⚠ A result worth reading carefully: the legacy figure now AGREES

`unmatched_cashflow_legacy` = **39,057.26** = `realised_pnl`, **exactly**.

That is not a coincidence and not a bug. **When a position starts flat and ends flat, Σ(sell
notional) − Σ(buy notional) IS the realised P&L** — every unit bought is eventually sold, so the
cash-flow difference is the trading profit. It is a mathematical identity for a fully round-tripped
position.

The consequence is the sharpest evidence in this report:

> **The old formula was not wrong in WO-048 because it was the wrong formula. It was wrong because
> the positions never closed.** R1's missing close is what made unmatched cash flow diverge from
> reality by nine orders of magnitude. With every segment genuinely flat at both ends, the two
> methods agree to the cent.

R3 is still the correct fix — the two figures diverge the instant a segment ends non-flat, and
relying on the identity would be relying on an invariant the accounting does not itself enforce.
But the agreement here is a strong independent check that **R1 actually executed**.

---

## §2 R1 — THE CLOSE EXISTS AND COSTS MONEY

Force-flat previously did `dataclasses.replace(position, current_quantity=0)`: it zeroed a variable
and executed **no trade**. It is now a **real fill** — costed through `compute_execution_costs` at
the **boundary frame's own bid/ask/spread**, stamped in **market time** (D-a), on the reducing side,
entering the trade ledger flagged `boundary_close` so it is attributable but never excluded.

**Evidence at corpus scale: 21 boundary closes across 21 segments, and `unrealised_residual = 0`.**

Per §3.2 that residual is R1's **independent check** — it is computed from the *position*, not from
the flatten event, so a close that failed to execute would show up as a non-zero residual no matter
what the event record claimed. Every one of the 21 segments reports `unreal 0, finalq 0`.

## §3 R3 — POSITION-AWARE P&L

**§3.1 declared method: AVERAGE COST.** Chosen over FIFO because `PositionState.average_entry_price`
has existed since the walking skeleton and was never populated — average cost is the method this
system's own state type was shaped for, whereas FIFO needs a lot queue `PositionState` cannot
express, creating a second source of truth about one position. It is also path-independent for a
single symbol; FIFO's advantage is tax-lot fidelity, a concern this project already separates
(`cad_value`).

Mechanics: increasing re-weights the average and realises nothing; reducing realises against the
average and leaves the remainder's basis untouched; **crossing zero closes the old position and
opens a new one at the trade price**, explicitly — silently keeping the old average would carry a
long's basis into a short.

**§3.4:** `gross_pnl` was **removed, not renamed**. The old figure survives only as
`unmatched_cashflow_legacy` for this attribution. The removal immediately surfaced a stale assertion
in the existing suite — a loud failure rather than a silently wrong number (the WO-045 precedent).

## §4 R4 — DISTINCT COST CHANNELS

The defaults were `fee_rate_pct = 0.1` (a **percent**) and `slippage_factor = 0.001` (a
**fraction**) — the same 0.1% of notional. The differing units are exactly how the coincidence
survived: one reads "0.1", the other "0.001", and they look unrelated.

- **Fee 0.26%** — DECLARED ENGINEERING JUDGEMENT, a typical spot taker rate. **Declared, not
  cited**: I did not verify a published schedule from here (rule 0.1e).
- **Slippage 0.01% (1 bp)** — **anchored to measurement**. Over 50,000 corpus frames: mean spread
  0.521 on a mean mid of 64,635.87 = **0.0806 bps of mid**; mean resting depth 0.34 BTC bid /
  0.90 BTC ask, so a 0.1 BTC order consumes ~16% of touch depth, does **not** exhaust level 1, and
  incurs essentially no impact beyond a spread that is already priced separately (the executed price
  crosses it). 1 bp is ~12× the entire observed spread — deliberately generous.

**⚠ FURTHER FINDING:** the **old 0.1% slippage default was ~124× the corpus's mean full spread**.
For this instrument at this size it was not conservative — it was wrong by two orders of magnitude,
and it silently supplied half of WO-048's cost total.

**§4.3:** defaults only. `compute_execution_costs` is untouched, so the WO-011 cent-level
reconciliation holds (`test_cost_reconciliation` passes its own explicit rates, insulated).
**§4.2:** a permanent test asserts fees ≠ slippage under the defaults, plus one asserting a **real
fill** shows the two apart.

## §5 THE THREE RECORD ITEMS

- **5.1** `docs/decisions/2026-08-07-a-bite-proof-asserts-the-economic-effect.md` — with the lineage
  point: **D-r16 already required proofs to terminate in observable effects**, and WO-048's proof was
  written *after* that rule and still checked a label, **because an event record is technically
  observable**. The rule was satisfied to the letter and defeated in substance.
- **5.2** `docs/decisions/2026-08-07-a-discrimination-set-holds-only-single-purpose-tests.md` —
  WO-049's specimen, with the table showing coverage and attribution pull in opposite directions.
- **5.3** The stale signed-quantity claim, annotated (D47 form) at **both** sites the grep found:

| Site | Disposition |
|---|---|
| `src/trading/data/desired_position.py:28-30` | **ANNOTATED** — production model |
| `specs/001-walking-skeleton/contracts/strategy.py:75-77` | **ANNOTATED** — **the origin it was copied from** |
| `src/trading/risk/position_state.py:21` | **deliberately NOT annotated — it is CORRECT** |

The third row matters: `current_quantity` ("Positive=long, negative=short") is genuinely signed. **A
POSITION is signed; an ORDER QUANTITY is not**, and conflating the two is what made the stale form
look plausible for so long. Named in the annotation as what the stale form would cause: an author
writing a SELL as `quantity=-0.1` gets it **vetoed as invalid input**, so the strategy silently stops
trading in one direction — a system that only ever goes long, with no error and a plausible P&L.

## §6 BITE PROOF — `tools/wo050_accounting_bite_proof.py` — **VERDICT: PASS**

| Artifact | Result |
|---|---|
| 1 — PRISTINE | 28 passed |
| 2 — **MUTATION R1** (force-flat reverts to zeroing the variable) | **R1 bite fails; R1 dual passes; R3 holds** |
| 3 — **MUTATION R3** (realised reverts to unmatched cash flow) | **R3 bite fails; R1 holds** |
| 4 — RESTORED | 28 passed |
| sha256 exact-restore | `segmented.py` `470e4c7c…` · `position_pnl.py` `4046973b…` **IDENTICAL** |

The **R3 bite uses a diverging case** — buy 2 @ 100, sell 1 @ 110: average cost realises **+10**,
unmatched cash flow says **−90**. A 1-for-1 round trip gives the same answer under both methods and
would have proved nothing.

**§0.10 honoured:** the three broad/contract tests are **excluded** from the discrimination sets and
reported as `broad_failed` — visible as expected behaviour rather than mistaken for evidence. That
is the precise error that made WO-049's first proof run fail.

---

## §7.4 THE METRIC, STATED IN FULL

> **Net P&L of −$2,223,991.19 over 36.8867 hours of verified continuous market data, in 21
> independent segments, flat at every boundary, excluding 0.0167 h of in-run gaps and 2.1061 h of
> inter-run seam. 129,695 trades including 21 boundary closes. Realised gross +$39,057.26 against
> $2,263,048.45 of costs (fees $2,179,231.85, slippage $83,816.61; spread attribution $2,814.11 not
> additive). Coverage fraction 1.0, untruncated. 0 segments excluded by the 1,000-frame bound.
> Average-cost accounting; unrealised residual exactly 0.**

**What it explicitly is NOT:**

- **NOT a 39-hour continuous backtest** — 36.8867 covered hours in 21 segments; the ~39.0 h elapsed
  span includes gap and seam time containing no data.
- **NOT a verdict on book imbalance as an idea** — it is a verdict on *this* signal, at N=100 and
  T=0.20, with a fixed 0.1 BTC size, against a 0.26% taker fee. A different fee tier or a signal
  that traded less would be a different measurement.
- **NOT a tradeable-edge estimate** — it is a measurement of one rule over ~37 hours of one
  instrument, which is far too little data to conclude anything about future returns.
- **NOT free of declared assumptions** — the 0.26% fee is declared engineering judgement, not a
  cited schedule.

---

## §8 ACCEPTANCE

- [x] R1 / R3 / R4 implemented; three record items landed
- [x] Bite proofs 6.1–6.3 with **single-purpose** discrimination sets; exclusions recorded in the proof
- [x] CI green both legs **before** the run (`31214886348`, counts from job logs)
- [x] Parameters unchanged (N=100, T=0.20, size=0.1) — verified from the committed constants
- [x] Corpus digest **identical** — `a025db1e…` at open and close
- [x] §7.3 before/after attribution complete, with per-trade normalisation isolating rate from volume
- [x] All gates: lint 6/6 · contract 6/6 · ruff · annotation 0 · partition 31/31

### Test results

| Leg | Interpreter | Order | Result |
|---|---|---|---|
| dev | 3.14.6 | `-p no:randomly` | **436 passed, 2 skipped** (309.12s) |
| acceptance | 3.11.15 (uv venv) | `-p no:randomly` | **436 passed, 2 skipped** (308.17s) |
| order-dependence | 3.14.6 | `--randomly-seed=20260810` | **436 passed, 2 skipped** (309.74s) |
| **CI 3.14** | job 92985983519 | randomized | **436 passed, 2 skipped** (302.93s) |
| **CI 3.11** | job 92985983478 | randomized | **436 passed, 2 skipped** (302.16s) |

**Arithmetic:** 424 at base + 12 (`tests/test_backtest_accounting.py`) = **436**.

---

## EVERY ATTEMPT

1. Confirmed HEAD, snapshotted the corpus, measured the corpus spread to anchor the slippage rate
   rather than invent it.
2. R4 first, then checked its blast radius before the larger changes — zero, because the cost tests
   pass explicit rates.
3. Removing `gross_pnl` surfaced a stale assertion immediately — the intended loud failure.
4. Grepped for the signed-quantity claim; found the **origin** in the spec contract as well as the
   production copy; annotated both and deliberately left the correct `PositionState` note alone.
5. Bite proof passed first time with both mutations discriminating — §0.10 applied from the start
   after WO-049's lesson.
6. Ran the second backtest; reported the number as produced.

## STOP

Per the WO. **This is the first meaningful strategy verdict this project has produced, and it is
negative.** The apparatus now measures honestly enough for that to mean something: the strategy's
gross edge is real but small, and at a 0.26% taker fee it is not remotely enough to trade.
