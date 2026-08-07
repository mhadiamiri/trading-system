# WO-050 — BACKTEST ACCOUNTING: R1 the missing close, R3 real P&L, R4 distinct cost channels.
#
# Then the second run. The WO-048 number stands on the record, unsuperseded (D49).

BASE: HEAD `2fff566` (WO-049, CI green run 31210060300, 424 tests). Confirm in §1.
SCOPE: §2 R1; §3 R3; §4 R4; §5 three record items; §6 bite proofs; **§7 the second run**.
SHIP IMPACT: **YES.** Full discipline. Build + CI green BEFORE the run.
**`corpus_20260805` READ ONLY — digest `a025db1e…` identical at close.**

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.3 Fail-then-pass bite proofs, four artifacts, sha256 exact-restore, discriminating mutations.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 AUTO MODE OFF.
0.8 **PRE-REGISTRATION STILL BINDS.** The strategy parameters (N, T, size) are UNCHANGED from WO-048
    and are not revisable. This WO fixes ACCOUNTING, not the strategy. **After the §7 run you may not
    revise anything and re-run** — if the number is bad, that is the number.
0.9 **ASSERT THE ECONOMIC EFFECT, NOT THE EVENT RECORD (D49).** In an economic path the observable
    effect is the LEDGER CONSEQUENCE — the trade, the cost, the position change — never the log line
    or event object announcing it. **A log line is a claim; the ledger is the effect.** R1 exists
    because a proof checked a label; do not repeat it.
0.10 **A DISCRIMINATION SET CONTAINS ONLY SINGLE-PURPOSE TESTS** (WO-049's finding). A test
    exercising both halves fails under either mutation and attributes nothing. Broad/contract tests
    are excluded from discrimination sets, and the exclusion is recorded IN the proof.

---

## §1 CONFIRM STATE
HEAD, 424 both interpreters, `git diff -- src/` clean, all gates, corpus digest snapshotted.

---

## §2 R1 — FORCE-FLAT MUST EXECUTE AN ECONOMIC CLOSE (ratified D49)
Today force-flat zeroes the position with **no closing trade** — U2 is labelled but never
economically executed, so the P&L omits every segment's close.

2.1 At every segment boundary the flatten is **a real fill**: costed through
    `compute_execution_costs`, at the **boundary frame's market** (its bid/ask/spread), **timestamped
    in market time** (the frame's timestamp — D-a, already ruled), on the correct side to reduce the
    position to zero.
2.2 It appears in the trade ledger like any other trade and is **labelled** as a boundary close, so
    it is attributable but not excluded.
2.3 Prove the ledger consequence: after every boundary, position == 0 **and a closing trade exists
    with non-zero cost**. Asserting the flatten event is NOT sufficient (0.9).

---

## §3 R3 — POSITION-AWARE P&L (ratified D49)
`gross_pnl` is the walking-skeleton unmatched cash-flow figure — honest at 5 trades, meaningless at
3.5M. Replace it.

3.1 Implement real position-aware accounting. **DECLARE WHICH: average-cost or FIFO.** State the
    choice and why. Either is acceptable; leaving it ambiguous is not.
3.2 Realised vs unrealised must be distinguishable. With U2 force-flat every segment ends flat, so
    **segment-end unrealised must be exactly zero** — assert it; a non-zero residual means the close
    did not execute (which R1 just fixed, so this is R1's independent check).
3.3 Net P&L = realised P&L − total costs, with fees and slippage attributed separately.
3.4 Keep the old figure available under an unambiguous name if useful for comparison, but the
    reported P&L is the new one. **Do not silently rename** — if the old key is removed, remove it
    loudly (the WO-045 precedent: a stale reader gets a KeyError, not a wrong number).

---

## §4 R4 — DISTINCT COST CHANNELS (ratified D49)
Fees and slippage are numerically identical under the default rates (22,572,628.06 each), making two
channels indistinguishable and able to mask each other's divergence.
4.1 Give them **distinct default rates**, stated with derivation (a realistic taker fee vs a
    realistic slippage assumption — say where each comes from).
4.2 **A permanent test asserting fees ≠ slippage under defaults.** Cheap, permanent, and it prevents
    the coincidence returning silently.
4.3 This changes the cost model's DEFAULTS, not its arithmetic — `compute_execution_costs` stays the
    one implementation, reconciled to the cent. Confirm the WO-011 reconciliation still holds.

---

## §5 THREE RECORD ITEMS (small, but they close open loops)
5.1 **The D49 decision doc, if not yet written:**
    `docs/decisions/2026-08-07-a-bite-proof-asserts-the-economic-effect.md` — *a bite proof must
    assert the ECONOMIC EFFECT, not the EVENT RECORD.* Lineage: D-r16 said proofs terminate in
    observable effects; this proof was written AFTER that rule and still checked the label, because
    an event record is technically observable. **In an economic path the observable effect is the
    ledger consequence — the trade, the cost, the position change — never the log line announcing
    it. A log line is a claim; the ledger is the effect.**
5.2 **The WO-049 discrimination-set finding:**
    `docs/decisions/2026-08-07-a-discrimination-set-holds-only-single-purpose-tests.md` — a test
    exercising both halves fails under either mutation and therefore attributes nothing. Specimen:
    WO-049's first run, where neither mutation discriminated because the S13 contract test and the
    70-case sweep sat in the discriminating sets. Broad tests prove the contract; only
    single-purpose tests attribute a failure. Record that the exclusion belongs IN the proof.
5.3 **Annotate the stale `DesiredPosition` docstring** (D47 form — annotate at the site, do not
    rewrite). It declares `quantity < 0 if side == SELL`; `check()` vetoes `quantity <= 0`, so a SELL
    obeying the docstring is rejected as invalid input. Actual convention: **quantity is an UNSIGNED
    MAGNITUDE; `side` carries direction.** Annotate, naming what the stale form would cause. Grep for
    other sites carrying the signed-quantity claim and annotate each; report the full list (third
    document-vs-code contradiction in this family — *detail reads as authority*).

---

## §6 BITE PROOFS (four artifacts each, sha256 exact-restore; 0.9 and 0.10 apply)
6.1 **R1 — the close exists and costs money.** BITE: a segment ending with an open position produces
    a closing trade with non-zero cost, position 0, timestamped at the boundary frame's market time.
    DUAL: a segment ending already flat produces NO spurious close. MUTATION: revert to zeroing the
    variable → the bite fails (no trade), the dual passes.
6.2 **R3 — the P&L is position-aware.** BITE: a buy-then-sell round trip yields the correct realised
    P&L under the declared method, and segment-end unrealised == 0. MUTATION: revert to unmatched
    cash-flow → the bite fails on a case where the two differ.
6.3 **R4** — the fees ≠ slippage assertion (4.2).
Use single-purpose tests in the discrimination sets (0.10); record any exclusions in the proof.

---

## §7 THE SECOND RUN — only after §1–§6 committed and CI GREEN both legs
7.1 Commit, push, **CI green both legs (real run number, counts from job logs)** before running.
7.2 Run `BookImbalanceStrategy` over `corpus_20260805`, full corpus, **parameters unchanged from
    WO-048** (0.8). Same strategy, same data, fixed accounting.
7.3 Report with the WO-048 header (which strategy, why not the trivial one, citing D48) PLUS:
    - the full metric statement (36.8867 h, N segments, flat at every boundary, gaps and seam excluded);
    - per-segment results AND the declared aggregate, with U5's dependency stated (the sum is
      meaningful **only because** U2 makes every segment start and end flat);
    - realised P&L, fees, slippage, spread attribution, trade count, boundary closes as a distinct
      line, position plateau behaviour under the new cap;
    - **an explicit before/after against WO-048's number**, with each defect's contribution
      attributed as far as it can be. The first number is NOT superseded — it is the record of what
      this apparatus produced under those defects.
7.4 **Whatever the number is, report it.** Do not revise and re-run (0.8).

## §8 ACCEPTANCE
R1/R3/R4 implemented; three record items landed; bite proofs 6.1–6.3 with single-purpose
discrimination sets; CI green before the run; parameters unchanged; corpus digest identical; the §7.3
report complete with the before/after attribution; all gates; test count with arithmetic.

## §9 REPORT — `WO-050-REPORT.md`
The three fixes; the declared P&L method and cost-rate derivations; the annotation grep list; all
bite proofs verbatim with sha256; **the second number** with its before/after attribution; every
attempt; any STOP; CI run.

**THEN STOP.** This is the first meaningful strategy verdict this project has produced.