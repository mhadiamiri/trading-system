# WO-049 — RISK LAYER: `max_position_btc` IS THE AGGREGATE POSITION CAP. Full risk-layer discipline.
#
# D49: "A limit that bounds each order but not the position is not a position limit; it's a rate
# limiter wearing one's name." Defect present since the risk engine was built, green through every
# prior run — made visible only by a strategy firing on 90.9% of 3.85M real frames.

BASE: HEAD `6e1586f` (WO-048 run) — confirm in §1.
SCOPE: the aggregate-position clamp and its bite proofs. Commit green, STOP. **Does NOT re-run the
backtest** (that follows the accounting WO).
SHIP IMPACT: **YES — RISK LAYER.** Full discipline. This is the layer that exists to say no.

**The risk layer never contains AI. Deterministic code only. No heuristics, no adaptive thresholds.**

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.3 Fail-then-pass bite proofs, four artifacts, sha256 exact-restore, discriminating mutations.
0.4 **Preservation duals mandatory, and in the risk layer they are the DANGEROUS half.** A guard that
    refuses everything looks correct and is catastrophic. See §4.2.
0.5 Report every attempt.
0.6 AUTO MODE OFF — risk-layer production edit.
0.9 **ASSERT THE ECONOMIC EFFECT, NOT THE EVENT RECORD (D49, ratified this WO's cycle).** In any
    economic path the observable effect is the LEDGER CONSEQUENCE — the clamped quantity actually
    applied, the resulting position, the veto that prevented a fill — never the log line or the
    decision object announcing it. **A log line is a claim; the ledger is the effect.** WO-048's
    §6.1 proof checked a label and missed a missing trade; do not repeat it here.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Where |
    |---|---|---|
    | `risk_engine.check()` pass/clamp/veto | **OPERATED — DEFECTIVE** | clamps ORDER SIZE, never reads `current_state.current_quantity` |
    | clamp-only-reduces-toward-zero invariant | **OPERATED** | must continue to hold — §3.3 |
    | Reason-code vocabulary (declared ⇒ producible) | **OPERATED** | reuse existing codes if they fit; the guard has bitten repeatedly and been right |
    | The aggregate-position clamp | **THIS WO IS THE BUILDER** | §3 |

---

## §1 CONFIRM STATE + READ THE ENGINE
HEAD, test count both interpreters, `git diff -- src/` clean, all gates, corpus digest snapshotted
(`a025db1e…` — this WO must not touch it).

Paste `check()` in full with line numbers, plus `PositionState`/`current_quantity`'s definition and
every existing clamp/veto reason code. **State exactly where the size clamp is and confirm from the
code that `current_quantity` is never read** — the finding, re-derived at HEAD rather than inherited.

---

## §2 THE MEANING, AS RULED (D49 — do not relitigate)
`max_position_btc` is the **AGGREGATE POSITION CAP**. Not a per-order cap. An order is evaluated
against the position it would PRODUCE, not against its own size.

---

## §3 BUILD
3.1 `check()` reads `current_state.current_quantity` and evaluates the **RESULTING** position:
    `resulting = current_quantity ± order_quantity` (signed per side).
3.2 **Clamp to exactly the remaining headroom.** If the resulting position would exceed the cap, the
    order is clamped so the resulting position equals the cap exactly — not rejected wholesale, not
    clamped to the per-order limit. At **zero headroom**, VETO.
3.3 **CLAMP-ONLY-REDUCES-TOWARD-ZERO MUST HOLD THROUGHOUT.** The clamp may only make an order
    smaller in the direction of increasing exposure. It must never increase an order, never flip a
    side, never turn a reducing order into an increasing one. State how you guarantee this and prove
    it (§4.3).
3.4 **Reason codes:** reuse existing clamp/veto codes if they fit; if a new one is genuinely needed,
    declare it properly (producible, prefix-free). State which you used and why.
3.5 Deterministic only. No adaptive sizing, no heuristics.

---

## §4 BITE PROOFS — BOTH HALVES IN ONE TEST (S13), ECONOMIC EFFECT ASSERTED (0.9)

4.1 **REFUSAL HALF.** With a position below the cap, an order that would carry the aggregate PAST it
    is clamped to **exactly the remaining headroom** — assert the RESULTING POSITION equals the cap,
    not that a clamp event was logged. At **zero/full headroom**, the order is VETOED and **no fill
    occurs** — assert the ledger, not the decision object.

4.2 **PRESERVATION HALF — THE DANGEROUS ONE (D49, the S13 analog; state it in the test's docstring).**
    **At or beyond the cap, an order that REDUCES the position toward zero MUST STILL PASS, unclamped.**
    A position limit that traps you in a position is the over-blocking nightmare in risk-layer
    clothing — it would prevent the system from ever getting flat, which is strictly more dangerous
    than the accumulation bug it replaces. Prove: at exactly the cap, and beyond it, a reducing order
    passes at full size and the resulting position moves toward zero.

4.3 **CLAMP-ONLY-REDUCES-TOWARD-ZERO.** Prove the clamp never increases an order, never flips a
    side, never converts a reducing order into an increasing one. Include the beyond-cap case (a
    position somehow above the cap — from a config change or a prior state — must still be reducible).

4.4 **NECESSITY MUTATION.** Revert `check()` to the per-order clamp (ignore `current_quantity`) →
    4.1 fails, 4.2 still passes. That asymmetry proves the aggregate check is doing the work and not
    something adjacent. Then a SECOND mutation: make the clamp refuse ALL orders at the cap →
    **4.2 fails**, proving the preservation half discriminates over-blocking. Two mutations, each
    failing a different half.

4.5 **THE WO-048 CONDITION, REPRODUCED.** A regression test driving the accumulation pattern that
    produced 738,510 trades in one segment: repeated same-side 0.1 BTC orders against a fixed cap.
    Assert the position **plateaus at the cap** and never exceeds it. This is the condition the
    fixtures never reached and the corpus did — pin it so it can never return.

Four artifacts each, sha256 exact-restore.

---

## §5 SCOPE FENCE
- Risk layer only. Does NOT touch R1/R3/R4 (the accounting WO).
- Does NOT re-run the backtest. **The WO-048 number stands on the record, unsuperseded (D49).**
- Does NOT touch `corpus_20260805`.
- Does NOT change the strategy or its declared parameters.

## §6 ACCEPTANCE
- `check()` evaluates the resulting position; clamps to exact remaining headroom; vetoes at zero
- Clamp-only-reduces-toward-zero holds and is proven, including beyond-cap
- Bite proofs 4.1–4.5, both halves in one test, **economic effect asserted**, two discriminating
  mutations, four artifacts each, sha256 exact-restore
- Reason codes declared/reused correctly
- Test count with arithmetic, both interpreters, both orders
- lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition
- `risk/engine.py` before/after sha256; corpus digest unchanged
- Commit, push, **CI green both legs — real run number, counts from the job logs**

## §7 REPORT — `WO-049-REPORT.md`
`check()` before/after with the finding re-derived at HEAD; the clamp mechanism and how
reduces-toward-zero is guaranteed; all bite proofs verbatim with sha256 and both mutations; the
§4.5 regression; reason codes; hashes; CI; every attempt; any STOP.

**Record note for the log (D49):** this defect existed since the risk engine was built and was
certified green through every prior run. It took the corpus — a strategy firing on 90.9% of 3.85M
real frames — to make accumulation-without-limit visible. **The corpus produced conditions the
fixtures never reached.** That is what it is for.

**THEN STOP.** Next: the accounting WO (R1 closing trade, R3 position-aware P&L, R4 distinct cost
rates), then the second run.