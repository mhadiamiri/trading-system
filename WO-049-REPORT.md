# WO-049 — RISK LAYER: `max_position_btc` IS THE AGGREGATE POSITION CAP — REPORT

**Date:** 2026-08-07
**Base HEAD:** `6e1586f` (WO-048 run)
**SHIP IMPACT: YES — RISK LAYER.** The layer that exists to say no.
**Scope fence honoured:** does NOT touch R1/R3/R4 (the accounting WO), does NOT re-run the backtest
(**the WO-048 number stands on the record, unsuperseded**), does NOT touch `corpus_20260805`, does
NOT change the strategy or its declared parameters.

> **D49:** *"A limit that bounds each order but not the position is not a position limit; it's a
> rate limiter wearing one's name."*

---

## §1 CONFIRM STATE + THE FINDING, RE-DERIVED AT HEAD

HEAD `6e1586f` · `git diff -- src/` empty · lint-imports 6/6 · ruff clean · corpus digest
`a025db1e…` snapshotted. `risk/engine.py` sha256 **before**
`bd0747fcc7306dd7bab56624aff028320d3e00da0f3ab860f4e4d037221993e7`.

### `check()` as it stood — the defect, re-derived not inherited

```python
 77        # Check kill switch first
 78        if self._kill_switch_engaged:
 79            return RiskDecision.VETO, None, self.REASON_VETO_KILL_SWITCH
 81        # Validate inputs
 82        if desired.quantity <= 0:
 83            return RiskDecision.VETO, None, self.REASON_VETO_INVALID_INPUT
 85        # Check daily loss limit
 86        if current_state.daily_pnl <= -(self._account_equity_usd * self._max_daily_loss_pct):
 87            return RiskDecision.VETO, None, self.REASON_VETO_DAILY_LOSS
 89        # Check position size limit
 90        approved_size = min(desired.quantity, self._max_position_btc)      # <-- THE SIZE CLAMP
 92        if approved_size < desired.quantity:
 ...            return RiskDecision.CLAMP, approved_order, self.REASON_CLAMP_MAX_POSITION
115        return RiskDecision.PASS, approved_order, self.REASON_PASS
```

**The size clamp is line 90, and it reads only `desired.quantity`.** `current_state` appears exactly
once in the whole method — **line 86, for `daily_pnl`**. `current_quantity` is never read. Confirmed
mechanically at HEAD:

```
uses current_state.current_quantity: False
clamps ORDER size only:              True
max_position default:                1.0
```

`PositionState.current_quantity: Decimal  # Positive=long, negative=short, zero=flat`
(`position_state.py:21`).

Existing reason codes: `RISK_PASS`, `RISK_CLAMP_MAX_POSITION`, `RISK_VETO_KILL_SWITCH`,
`RISK_VETO_DAILY_LOSS`, `RISK_VETO_INVALID_INPUT`.

### ⚠ §1 FINDING — the declared sign invariant contradicts the code (code wins, §0.1)

`DesiredPosition`'s docstring declares:

> - quantity > 0 if side == Side.BUY
> - **quantity < 0 if side == Side.SELL**

**The code does the opposite.** `check()` line 82 VETOES any `quantity <= 0`, so a SELL obeying the
docstring would be rejected as invalid input. Both strategies emit a positive magnitude for both
sides (`trivial.py:70`, `book_imbalance.py:123`), and every position-update site derives direction
from `side`: `+size if BUY else -size` (`runner.py:257/259`, `segmented.py:287`).

**Actual convention: `quantity` is an UNSIGNED MAGNITUDE; `side` carries direction.** This is
load-bearing for §3.1 — "resulting = current ± order (signed per side)" must take the sign from
`side`, not from the quantity. The stale docstring is **reported, not obeyed, and not edited**
(out of this WO's scope fence).

---

## §3 THE BUILD

```python
current   = current_state.current_quantity
cap       = self._max_position_btc                       # a MAGNITUDE: band is [-cap, +cap]
direction = +1 if side == "BUY" else -1
increasing = (direction * current) >= 0                  # flat counts as increasing

if increasing:
    headroom = cap - abs(current)
    if headroom <= 0:
        return VETO, None, REASON_VETO_MAX_POSITION      # zero headroom
    allowed = min(desired.quantity, headroom)            # clamp to EXACTLY the remaining room
else:                                                    # REDUCING
    allowed = min(desired.quantity, abs(current) + cap)  # only the overshoot past zero is bounded
```

**§3.1** the resulting position is what is evaluated. **§3.2** partial headroom clamps so the
resulting position equals the cap exactly; zero headroom vetoes. **§3.5** deterministic — no
adaptive sizing, no heuristics, pinned by `test_check_is_deterministic`.

**The cap is two-sided.** `cap` is a magnitude, so a 1.5 BTC short breaches a 1.0 BTC cap exactly as
a 1.5 BTC long does.

### §3.3 How clamp-only-reduces-toward-zero is GUARANTEED

Structurally, not by inspection:

1. **Never increases** — `allowed` is always `min(desired.quantity, …)`, so it cannot exceed the
   request. Arithmetically closed, not conditionally checked.
2. **Never flips a side** — `desired.side.value` is passed through untouched; no branch writes it.
3. **Never converts reducing → increasing** — the reducing branch only shrinks the magnitude, and
   any positive magnitude in the opposite direction still moves toward zero.
4. **The VETO can never block a reduction** — it lives *inside* `if increasing:`. That placement is
   the §4.2 safety property, and it is structural rather than a condition someone must maintain.

### §3.4 Reason codes

- **REUSED** `RISK_CLAMP_MAX_POSITION` for the clamp — it fits exactly; no new code invented.
- **NEW** `RISK_VETO_MAX_POSITION` for the zero-headroom veto. Genuinely needed: the existing vetoes
  name a kill switch, a daily-loss breach and malformed input — none describes "the aggregate
  position is already at its cap". Declared in `VALID_REASON_CODES["RISK"]`, prefix-free, and
  genuinely producible (returned by `check()`, driven by the tests and the bite proof). The
  archive-readiness guard's `test_every_wired_risk_reason_constant_is_declared` covers it, since it
  is a wired `REASON_*` constant reaching an archived decision record.

---

## §4 BITE PROOFS — `tools/wo049_risk_bite_proof.py` — **VERDICT: PASS**

Every assertion is on the **ledger consequence** (§0.9): the resulting position, or the approved size
that would reach the venue, or the absence of any approved size. Never on the decision enum alone.
A helper `_apply()` mirrors the real position-update sites so the proofs are economic rather than
declarative.

| Artifact | Result |
|---|---|
| 1 — PRISTINE | 86 passed |
| 2 — **MUTATION A** (per-order clamp restored — the WO-048 defect) | **refusal half fails; preservation half passes (2/2)** |
| 3 — **MUTATION B** (over-blocking: reductions refused at the cap) | **preservation half fails; refusal half passes (4/4)** |
| 4 — RESTORED | 86 passed |
| sha256 exact-restore | `ec34922b82af260d6ab21be3b9ba3e801a44a321bbeb12b118491cb5276baf02` **IDENTICAL** |

```
MUTATION A discriminates (refusal fails, preservation holds) : True
MUTATION B discriminates (preservation fails, refusal holds) : True
```

**The two mutations fail DIFFERENT halves.** That asymmetry is what distinguishes *"the cap works"*
from *"the cap is merely present"* — and mutation B is what proves the preservation half
discriminates **over-blocking**, the dangerous risk-layer failure.

### §4.1 REFUSAL + §4.2 PRESERVATION in ONE test (S13)

`test_aggregate_cap_refusal_and_preservation_in_one_test` asserts, on one engine:

- partial headroom (position 0.7, BUY 0.8, cap 1.0) → **CLAMP to 0.3, resulting position == 1.0**
  — the cap exactly, asserted as a position, not as a logged clamp event;
- zero headroom (position 1.0, BUY 0.1) → **VETO, no size approved, position unchanged at 1.0**;
- **at the cap, SELL 0.4 → PASS at full size, resulting 0.6** — moved toward zero.

### §4.2 THE DANGEROUS HALF, stated in the test's docstring

> *A position limit that traps you in a position is the over-blocking nightmare in risk-layer
> clothing — strictly more dangerous than the accumulation bug it replaces.*

Proved at the cap and beyond it: from 5.0 with a 1.0 cap, SELL 0.1 → PASS unclamped → 4.9; SELL 4.0
→ PASS → 1.0; SELL 5.0 → PASS → **exactly flat**. A position above the cap (from a config change or
a prior state) remains fully reducible.

An overshooting reduction (position 1.0, SELL 3.0) is **clamped to 2.0 → resulting −1.0**: capped on
the far side, never refused. The reduction itself is never restricted; only the new exposure built
beyond zero is.

### §4.3 Clamp-only-reduces-toward-zero

`test_the_clamp_never_increases_never_flips_never_converts` — **70 combinations** (7 positions ×
2 sides × 5 sizes) including beyond-cap and both signs. Asserts: approved ≤ requested; side
unchanged; a reducing request never becomes increasing; and — the safety property — **any VETO
occurred only on an increasing order**, so no reduction was ever blocked.

### §4.5 THE WO-048 CONDITION, REPRODUCED

`test_repeated_same_side_orders_plateau_at_the_cap` drives the accumulation pattern that produced
738,510 trades in one segment: 1,000 same-side 0.1 BTC orders against a 1.0 BTC cap.

```
position PLATEAUS at exactly 1.0     (was: unbounded growth)
total approved size == 1.0            (nothing extra got through)
990 orders vetoed with RISK_VETO_MAX_POSITION
```

Its dual, `test_the_plateau_releases_when_the_position_is_reduced`, proves the plateau is not a
one-way ratchet: reduce to 0.5 and headroom reappears.

### ⚠ AN ATTEMPT WORTH RECORDING (§0.5) — the proof caught my own classification error

On the first run **neither mutation discriminated**: both halves failed under both mutations, and
the verdict was FAIL. The cause was my test *classification*, not the code. I had put broad tests in
the discriminating sets — the S13 contract test (both halves by design) and the 70-case invariant
sweep — and a test exercising both halves fails under either mutation and therefore distinguishes
nothing.

Fixed by adding four **narrowly-scoped** single-purpose tests (`test_pure_refusal_*`,
`test_pure_preservation_*`) and excluding the both-halves tests from the sets, with their exclusion
recorded in the proof itself. Their failure under both mutations is correct behaviour, reported as
`both_halves_failed`, never used as evidence.

---

## §6 ACCEPTANCE

- [x] `check()` evaluates the resulting position; clamps to exact remaining headroom; vetoes at zero
- [x] Clamp-only-reduces-toward-zero holds and is proven, including beyond-cap
- [x] Bite proofs 4.1–4.5, both halves in one test, **economic effect asserted**, two discriminating
      mutations, four artifacts, sha256 exact-restore
- [x] Reason codes: `RISK_CLAMP_MAX_POSITION` reused, `RISK_VETO_MAX_POSITION` declared
- [x] lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition
- [x] Corpus digest unchanged; backtest NOT re-run; WO-048's number unsuperseded

### Test results

| Leg | Interpreter | Order | Result |
|---|---|---|---|
| dev | 3.14.6 | `-p no:randomly` | **424 passed, 2 skipped** (309.88s) |
| acceptance | 3.11.15 (uv venv) | `-p no:randomly` | **424 passed, 2 skipped** (308.23s) |
| order-dependence | 3.14.6 | `--randomly-seed=20260809` | **424 passed, 2 skipped** (309.91s) |

**Arithmetic:** 338 at base + 86 (`tests/test_risk_aggregate_position.py`, including the 70-case
invariant sweep) = **424**.

### CI — the real run on this commit

**Commit `2fff566`** (pushed `6e1586f..2fff566`) · **CI run `31210060300`** · triggered via push.

| Job | ID | Duration | Result |
|---|---|---|---|
| `test (3.14)` | 92970477414 | 10m37s | ✅ **424 passed, 2 skipped** (302.54s) |
| `test (3.11)` | 92970477281 | 10m37s | ✅ **424 passed, 2 skipped** (301.40s) |

Counts pulled from the job logs, not inferred from the ✓. Both legs ran the randomized-order step
and reported 424/2, matching all three local legs.

### `risk/engine.py`

```
BEFORE  bd0747fcc7306dd7bab56624aff028320d3e00da0f3ab860f4e4d037221993e7
AFTER   ec34922b82af260d6ab21be3b9ba3e801a44a321bbeb12b118491cb5276baf02
```

---

## RECORD NOTE FOR THE LOG (D49)

**This defect existed since the risk engine was built and was certified green through every prior
run.** Ten risk tests covered pass, clamp, veto, kill switch and invalid input — every one of them
with `current_quantity = 0`, where a per-order clamp and an aggregate cap are indistinguishable.
The fixtures could not reach the condition.

It took the corpus — a strategy firing on 90.9% of 3.85 million real frames — to make
accumulation-without-limit visible. **The corpus produced conditions the fixtures never reached.
That is what it is for.**

## STOP

Per the WO. Next: the accounting WO (**R1** the missing closing trade, **R3** position-aware P&L,
**R4** distinct cost rates), then the second run.
