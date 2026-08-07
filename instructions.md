# WO-048 — THE FIRST HONEST BACKTEST. Loader, six rulings, four defect fixes, then the run.
#
# D48: "The first backtest's product is a TRUSTWORTHY MEASUREMENT APPARATUS, not a verdict on one
# particular rule." Any honest strategy over real recorded data proves the pipeline tells the truth
# with real costs. That is the milestone.

BASE: HEAD `592e19e`+ (WO-047 investigation committed). Confirm in §1.
Corpus: `corpus_20260805` — 36.8867 covered h, 3,847,540 frames, 20 stretches, 19 gaps + 1 seam.
**READ ONLY. Digest `a025db1e…` must be identical at close.**

SCOPE: §2 the strategy (declared, pre-registered); §3 the loader; §4 the six rulings; §5 the four
defects; §6 bite proofs; **§7 the run**. Build + CI green BEFORE the run.
SHIP IMPACT: **YES.** Full discipline.

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.3 Fail-then-pass bite proofs, four artifacts, sha256 exact-restore, discriminating mutations.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 AUTO MODE OFF.
0.8 **PRE-REGISTRATION — THE HARD RULE OF THIS WO.** Every strategy parameter is DECLARED WITH ITS
    DERIVATION AND COMMITTED **BEFORE** the run in §7. **After seeing the P&L you may not change a
    parameter and re-run.** If the number is bad, THAT IS THE NUMBER. Tuning after seeing results is
    the classic backtest lie and it would void this entire sprint's purpose in one edit. If you
    believe a parameter is wrong after the run, REPORT IT — do not fix it and re-run. A second run
    with changed parameters is a NEW WO with the first run's number still on the record.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Where |
    |---|---|---|
    | `compute_execution_costs` | **OPERATED — TRANSFERS UNCHANGED** | needs only bid/ask/spread/mid, all present |
    | `CorpusReader` (default-deny, segments-as-intervals) | **OPERATED** | WO-046 |
    | `BacktestRunner.run()` / `PaperExecutionClient` | **OPERATED** | existing continuous path — leave `run()` untouched |
    | `corpus_20260805` | **OPERATED — READ ONLY** | ratified D46 |
    | Frame loader, segmented runner, the strategy | **THIS WO IS THE BUILDER** | §2/§3/§4 |

---

## §1 CONFIRM STATE
HEAD, test count both interpreters, `git diff -- src/` empty, all gates, corpus digest snapshotted.

---

## §2 THE STRATEGY — `BookImbalanceStrategy` (declared under its own name, D48)

**Why this and not mid-price momentum:** mid-price momentum is structurally the substitution D48
rejected, renamed. Book-imbalance consumes `bid_qty`/`ask_qty` — data only a BOOK corpus carries —
so it is the natural consumer of this artifact and cannot be mistaken for the trivial strategy.

2.1 Signal: `imbalance = (bid_qty − ask_qty) / (bid_qty + ask_qty)` ∈ [−1, 1]; take a **rolling mean
    over N ticks**; BUY when the smoothed value ≥ `+T`, SELL when ≤ `−T`, else HOLD.
    **The rolling window is deliberate:** a single-tick signal would carry no state, making U3's
    per-segment reset and U4's warm-up tick VACUOUS. The window ensures the segment machinery is
    actually exercised rather than trivially satisfied.
2.2 **Declare N and T with derivation, and COMMIT THEM BEFORE §7** (0.8). State the reasoning for
    each (e.g. N chosen to match the established 100-sample convention; T chosen as a round,
    untuned starting value). **Do not sweep, do not optimise, do not pick a value because it looks
    better.** State explicitly in the report: "these values were fixed before the run and not
    revised after."
2.3 Fixed order size, as the trivial strategy does. No position sizing logic — that is a separate
    question and would be another free parameter.
2.4 Handle degenerate ticks: `bid_qty + ask_qty == 0` → HOLD (no division). Prove it.

---

## §3 THE FRAME LOADER (D-d — the build WO's real work)
`src/trading/data/corpus_frames.py`: **streaming** (never materialise 3.85 M objects), reads the
corpus JSONL, yields `MarketState` **only inside a reader-approved segment**.
- Takes a `CorpusReader`-issued `CorpusWindow`. **Cannot be pointed at raw files** — this is the
  enforcement point that makes default-deny unbypassable by direct file reads rather than merely
  impolite (D48).
- `MarketState` construction: the corpus supplies bid/ask/sizes/spread/timestamp. The three absent
  fields (`trade_count`, `total_volume`, `last_price`) are **NOT substituted**. State how you handle
  them — the honest options are an optional-field variant or a book-only state type. **Whatever you
  choose must make it impossible for a strategy to read a fabricated `last_price`.** If that requires
  a `MarketState` change, that is production surface — report the shape before applying it, and if
  it looks like a substitution in disguise, STOP.

---

## §4 THE SIX RULINGS (D48)
4.1 **U1** — `BookImbalanceStrategy` runs; TrivialMomentumStrategy's evaluation is recorded as
    **blocked-on-trade-channel**, deferred not dropped. Add the deferred item to `progress.md`.
4.2 **U2 — FORCE-FLAT AT EVERY BOUNDARY**, no duration threshold. "Any duration threshold is a knob
    that quietly moves the P&L." Flattening is a **labelled event** in the output. The cost (a 1.7 s
    reconnect flattens where a real trader would not) is DECLARED in the report, not hidden.
4.3 **U3 — FULL STATE RESET PER SEGMENT** via a **fresh strategy instance** (stronger than a
    `reset()` someone must call correctly). **Plus a DECLARED minimum-eligible-segment length**, with
    derivation stated (warm-up window × safety factor). Not binding on this corpus (measured 48–64×
    headroom; shortest stretch 201 s ≈ 4,823–6,431 frames vs a 100-tick warm-up) — declared anyway so
    a future reconnect-burst corpus is refused by a stated bound rather than saved by accident.
    Segments below the bound are EXCLUDED and the exclusion is reported.
4.4 **U4 — FIRST TICK OF EVERY SEGMENT IS OBSERVATION-ONLY**, never fillable. One tick, no parameter.
4.5 **U5 — PER-SEGMENT RESULTS PLUS A DECLARED AGGREGATE.** The report format must state the
    dependency: **the sum is meaningful ONLY BECAUSE U2 makes every segment start and end flat.**
    Show the distribution so a minutes-segment and an hours-segment cannot hide inside one number.
4.6 **U6 — ACKNOWLEDGMENTS**: `KEEPALIVE_RECONNECT` and `VENUE_DISCONNECT` bounded at **60 s**
    (declared engineering judgement; observed maxima 16.86 s / 3.29 s ≈ 3.5× headroom; state the
    re-declaration trigger if a future corpus's gaps approach it). `PROCESS_RESTART` acknowledged
    **to segment at, never to trade across**. `accept_open_ended` requires its own deliberate act.
    Record the structural note: **acknowledgment governs READING, force-flat governs TRADING — so
    acknowledging more never buys a more continuous backtest.**

---

## §5 THE FOUR DEFECTS
5.1 **D-a (serious) — MARKET TIME IS THE TRADE TIMESTAMP.** Today every fill and decision is stamped
    `datetime.now(UTC)` (`paper.py:288`, `trivial.py:73`) — replay wall-clock, so no trade can be
    reconciled against the data it replayed; Principle VIII fails at the backtest boundary. The
    frame's timestamp becomes THE time. Replay wall-clock may ride along as a **secondary** field,
    never as *the* time. Prove a trade's timestamp equals its originating frame's.
5.2 **D-b — DECLARED LIMIT.** The staleness guard is INERT under replay (`paper.py:178` measures
    wall-clock since registration ≈ 0). Document it where the guard is defined: it protects the LIVE
    path only; under replay, U3/U4's segment machinery is the analogous protection. State the
    equivalence.
5.3 **D-c — `max_events` BECOMES EXPLICIT-OR-ALL.** Default `None` = full corpus. A default of 1000
    silently covering 0.026% is the silent-truncation family. **Any truncated run states its coverage
    fraction in the report header.**
5.4 **D-d** — the §3 loader.

---

## §6 BITE PROOFS (0.3/0.4 — four artifacts each, sha256 exact-restore)
6.1 **THE ANTI-SPLICE PROOF — the load-bearing one.** Property: *the backtest cannot silently trade
    across a hole.*
    - **BITE:** two-segment fixture with a known gap, engineered so a naive continuous run WOULD fire
      on the first post-gap tick (a price jump across the hole exceeding the threshold). Assert: **no
      fill on that tick**, position flat across the boundary, boundary event recorded.
    - **DUAL (S13, same test):** the *same* jump placed INSIDE one segment fires and fills normally.
      Without this, a runner that never trades passes the bite.
    - **NECESSITY MUTATION:** remove the per-segment reset (or the force-flat) → the bite fails (a
      fill appears, computed against a pre-gap price) while the dual still passes.
6.2 **Loader containment:** no `MarketState` is ever yielded outside a reader-approved segment;
    the loader refuses a segment not issued by the reader.
6.3 **D-a:** a trade's timestamp equals its originating frame's, not the replay clock.
6.4 **Read-only:** corpus digest unchanged after a full run.

---

## §7 THE RUN — only after §1–§6 are committed and CI is GREEN both legs
7.1 Commit, push, **CI green both legs (real run number, counts from job logs)** BEFORE running.
7.2 Run `BookImbalanceStrategy` over `corpus_20260805`, full corpus (`max_events=None`), the
    declared N and T unchanged from §2.2.
7.3 Report, with this header, citing D48:
    > **This backtest evaluated `BookImbalanceStrategy`, NOT `TrivialMomentumStrategy`.** The corpus
    > is top-of-book and does not carry `last_price`/`total_volume`/`trade_count`; substituting them
    > would produce a number by redefining what was measured (D48, U1). TrivialMomentumStrategy's
    > evaluation is DEFERRED, blocked on a trade-channel re-capture.
7.4 Report: per-segment results AND the declared aggregate; the metric stated in full —
    *"Net P&L over 36.8867 h of verified continuous market data, in N independent segments, flat at
    every boundary, excluding 0.0167 h of in-run gaps and 2.1061 h of inter-run seam"*; total fees,
    slippage and spread attribution; trade count; segments excluded by the §4.3 bound; coverage
    fraction; and what the number explicitly is NOT (a 39-hour continuous backtest; a strategy
    verdict; a tradeable-edge estimate).
7.5 **Whatever the number is, report it.** Positive, negative, or zero. **Do not revise a parameter
    and re-run (0.8).**

## §8 ACCEPTANCE
Six rulings implemented; four defects fixed; bite proofs 6.1–6.4 with discriminating mutations;
CI green both legs before the run; corpus digest unchanged; parameters pre-registered and unchanged;
report carries the §7.3 header and the §7.4 full metric; test count with arithmetic; all gates.

## §9 REPORT — `WO-048-REPORT.md`
The declared parameters and their derivation (with the pre-registration statement); the loader; the
six rulings as built; the four defect fixes; all bite proofs verbatim with sha256; **the result**;
every attempt; any STOP; CI run.

**THEN STOP.** This is the first honest backtest.