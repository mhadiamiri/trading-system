# WO-053 — THE DEATH CERTIFICATE

## THE RESULT: **0 trades. OUTCOME (ii) — INSUFFICIENT TO EVALUATE.**

The registered prior was outcome (ii), and outcome (ii) is what happened. But the run says
something sharper than "the threshold was too high":

> **The largest 5-minute move in the entire corpus was 0.4076%. The round-trip cost is 1.6216%.
> The cost bar is 4× the biggest move that occurred in 36.9 hours — and 39× the median one.**

**SHIP IMPACT: YES** (new strategy + bar layer). Corpus v1 digest `e3ab1aec…` unchanged.
Pre-registration committed at **`e7b33c8`**, before the strategy file existed.

---

## §1 THREE HOUSEKEEPING ITEMS

### §1.1 The provenance line — recorded verbatim, outside the corpus

`docs/decisions/2026-08-08-corpus-20260805-provenance.md` carries the ruled line exactly:

> historical label unverifiable by construction; interval integrity witnessed by the capture-time
> per-segment manifest (38/38 verified, hashed_at_capture, computed by committed code); manifest
> externally pinned from WO-051 by the v1 digest; v1 canonical.

The third clause is the one that closes the gap WO-052 reported honestly and could not close: the
manifest hashes prove each *segment*, and the v1 digest — which covers all 88 files **including the
manifest**, matched at WO-051, WO-052 and now WO-053 — pins the manifest from outside itself. Two
independent witnesses covering each other's blind spot.

### §1.2 Stale fee declarations annotated — ⚠ **the count was 10, not 4**

Per 0.11 I grepped rather than trusting the reported figure. **WO-052's "four" was not a ceiling:**

| # | Site | In WO-052's list? |
|---|---|---|
| 1–3 | `specs/001-walking-skeleton/spec.md:18, :99 (FR-017), :143` | yes |
| 4 | `specs/001-walking-skeleton/research.md:119` | yes |
| 5 | `specs/001-walking-skeleton/quickstart.md:254` | yes |
| 6 | `specs/001-walking-skeleton/checklists/requirements.md:71` | yes |
| **7** | **`specs/001-walking-skeleton/tasks.md:172`** | **NO — missed entirely** |
| **8** | **`specs/001-walking-skeleton/tasks.md:364`** | **NO — missed entirely** |
| 9 | `specs/001-walking-skeleton/quickstart.md:55` (`EXECUTION_FEE_RATE_PCT`) | counted separately |
| 10 | `.env.example:24` (`EXECUTION_FEE_RATE_PCT`) | counted separately |

`tasks.md` was never in the enumeration. All 10 are annotated in D47 form — dated 2026-08-08, in
place, pointing at `fee_schedule` as the living source. **The spec stays frozen; its stale figures
stop being load-bearing.** The two `EXECUTION_FEE_RATE_PCT` sites carry a stronger annotation,
because that knob is read by no code at all: it configures nothing and only misinforms.

### §1.3 The ratified specimen

`docs/decisions/2026-08-08-an-empty-result-from-a-query-that-cannot-fail.md`. Records why this
family is harder to catch than its siblings — it arrives as an **observation in a report**, and
observations get no bite proof, no discrimination set, no deliberate failure. A number in a table
looks like evidence by being formatted like evidence.

The recursion is recorded as ruled: **committed** by WO-051 (whose purpose was to stop uncheckable
figures propagating), **accepted** by the reviewer, **struck** by the executor of WO-052 while
carrying out a ruling premised on the same false assumption. Every node failed somewhere and the
error was still caught — **the loop's integrity lives in no single node.** Standing consequence
recorded as 0.12 with a practical checklist.

### §1.4 State confirmed

| Check | Value |
|---|---|
| HEAD at open | `19ed158` — WO-052 close |
| Baseline | **455 passed, 2 skipped** (3.14) |
| `git diff -- src/` | clean |
| lint-imports / contract count | 6 kept, 0 broken / 6 of 6 |
| ruff · annotation · preflight · partition | clean · 0 · PASS · **31/31** |
| corpus v1 digest | `e3ab1aec…`, 88 files — **verified** |
| corpus manifest | **38/38 segments match capture-time SHA-256** |

---

## §2 THE PRE-REGISTRATION — committed at `e7b33c8`, before the strategy existed

`evidence/WO-053/PRE_REGISTRATION.md`. **The registration commit precedes the build commit
(`80f31fa`) and the run in git history**, which is what makes "not revised after seeing a result" a
checkable claim rather than an assertion. Per 0.12, its falsifier: a registration commit dated after
the run commit, or a parameter in the code differing from the table — a test pins the latter.

| Parameter | Value | Source |
|---|---|---|
| `BAR_INTERVAL_SECONDS` | 60 | convention (minutes horizon) |
| bar alignment | segment-relative | containment |
| partial bars | discarded | honesty at edges |
| `MOMENTUM_BARS` (N) | 5 | smallest round minutes-horizon window; multi-bar so U3/U4 are non-vacuous |
| **`THRESHOLD_PCT` (T)** | **3.2432%** | **2.0 × round-trip cost, cost-derived** |
| `ROUND_TRIP_COST_PCT` | 1.6216% | 2×0.80% cited fee + 2×1bp measured slip + 0.0016% measured spread |
| `ORDER_SIZE_BTC` | 0.1 | comparability with WO-048/050 |
| **evaluation floor** | **30 round trips** | conventional small-sample threshold |

T is **computed in code** from named cost constants rather than typed, so the derivation is
executable and a future edit cannot leave one number stale. A test pins T to that arithmetic and
pins the fee half to `fee_schedule.taker_pct()`.

---

## §3 THE BUILD

### §3.1 The bar layer — two mechanisms, deliberately

**Structural:** buckets anchor to each **segment's own first frame**, not the wall-clock epoch.
Under epoch alignment one bucket could legitimately hold frames from both sides of a gap;
per-segment anchoring makes that state *unrepresentable* rather than merely detectable.

**Enforced:** `add()` refuses any frame outside its segment with the new declared code
`BAR_FRAME_OUTSIDE_SEGMENT`. Alignment alone is arithmetic on a timestamp, and **arithmetic never
complains** — handed a foreign frame it computes a bucket index and carries on. The refusal is what
stops the splice being *silent*.

### Bite proof — `tools/wo053_bar_containment_bite_proof.py`, **VERDICT: PASS**

| Artifact | Result |
|---|---|
| 1 — PRISTINE | rc 0, 20 passed |
| 2 — MUTATION (boundary check removed) | rc 1 — **both** containment tests fail; **dual 5/5 still passes** |
| 3 — RESTORED | rc 0, 20 passed |
| 4 — **DIRECT DEMONSTRATION** | a real splice across the 2.1h seam is **REFUSED**; no `Bar` constructed |

```
bars.py sha256 BEFORE/AFTER : 7eb50ac1b49fce99340fa319f7783fc6761c38ad1c30acc5e510fecd9ad4392c
IDENTICAL                   : True
MUTATION bites (BOTH containment tests fail) : True
DUAL holds under the mutation                : True (5/5 passed)
DIRECT demonstration refused                 : True
```

The dual is what makes the bite mean anything: a builder that refused *everything* would also fail
the bite tests, and a proof checking only "something failed" could not tell the two apart.
Artifact 4 asserts the **economic object** (§0.9) — no `Bar` spanning the hole is ever constructed —
rather than only a test outcome.

### §3.2 U4 at bar granularity — declared and proved

The runner's frame-level U4 skips frame 0, which under a 60-second bar is **one of ~1,500 frames
inside bar 0** and suppresses nothing about bar 0's tradeability. So the adapter suppresses the
first **closed bar** itself: observed, feeds the momentum history, never fillable.

In practice the strategy cannot be warm by then anyway — **which is exactly why it is asserted
rather than assumed.** A protection satisfied only incidentally is the incidental-coverage defect
(D51) and would break silently the moment N changed. The test forces the only condition under which
it can matter (a pre-warmed strategy) and shows a +10% move suppressed; its dual shows bar 2 fires.

`BarMomentumStrategy` is deliberately **not** a `Strategy` subclass — `Strategy` requires
`decide(market_state)`, a per-frame interface a bar strategy has no honest answer for. Implementing
it to satisfy the ABC would be the substitution D48 forbids, one interface down.

### §3.3 No new accounting

Two minimal, commented changes to the proven runner: a factory may declare `wants_segment`, and the
U3 exclusion message reads `WINDOW_TICKS` off the factory class rather than constructing one.
Force-flat (U2), fresh instance per segment (U3), average-cost P&L, cited costs and the aggregate
position cap are **untouched**.

---

## §4 THE RUN

**CI green before the run — run `31232684456`**, both legs, counts from job logs:
`test (3.11)` 93039450185 → 475/2 both orders; `test (3.14)` 93039450249 → 475/2 both orders.

Run once, full corpus, `max_events=None`. Parameters read from the committed constants — the run
script sets none, so it cannot differ from the registration.

### §4.3 The result against the registration

```
segments_run       21        segments_excluded   0
trades              0        boundary_closes     0
realised_pnl        0        total_fees          0
total_costs         0        NET P&L             0
unrealised_residual 0        force_flattenings   0

coverage_fraction 1.0   processed 3,847,530 / 3,847,530 frames   truncated: False
```

| Against the registration | |
|---|---|
| signal-initiated entries | **0** |
| completed round trips | **0** |
| declared floor | 30 |
| **verdict** | **OUTCOME (ii) — INSUFFICIENT TO EVALUATE** |

Net P&L is exactly 0 and **is not a verdict in either direction**, per the floor declared before the
run. Nothing traded, so there is nothing to be right or wrong about.

**The apparatus worked.** 2,187 complete bars built across 21 segments; 21 partial bars discarded —
exactly one per segment, which is what the registered rule predicts. 20 of 21 segments were long
enough to warm (segment 2 produced 3 bars, below the 6 needed). **2,084 five-bar windows were
evaluated.** The signal was tested 2,084 times and declined every time.

### §4.4 THE VERDICT IN THE RULED FRAME

> **The arithmetic issued the death certificate. This run is the apparatus's witness signature.**

The derivation, so the verdict is legible without the run — measured from the corpus **after** the
run, as explanation only:

| 5-minute absolute move, within segments (n = 2,084) | |
|---|---:|
| median | **0.0412%** |
| p90 | 0.1076% |
| p99 | 0.2619% |
| p99.9 | 0.3514% |
| **maximum in 36.9 hours** | **0.4076%** |

against

| The cost bar | |
|---|---:|
| round-trip cost | **1.6216%** |
| registered threshold T | 3.2432% |

```
count of 5-minute windows >= T (3.2432%)          : 0
count >= the round-trip cost alone (1.6216%)      : 0
count >= 1.0%                                     : 0
count >= 0.5%                                     : 0
```

**This is the finding, and it is stronger than the registered expectation.**

The obvious objection to a zero-trade result is "you set the threshold too high." That objection
does not survive the numbers. **The round-trip cost alone — 1.6216%, the break-even bar, a
threshold with mathematically zero expectancy and the most permissive choice defensible — would
also have fired zero times.** So would 1.0%. So would 0.5%.

> **Cost is 4× the largest minutes-horizon move that occurred in the entire corpus, and 39× the
> median one. There was no threshold, at any multiple ≥ 1.0, that would have produced a single
> trade.** The result is not an artifact of the 2.0 multiple I registered.

Put plainly: at Tier 1 taker on BTC/USD, a minutes-horizon taker strategy is not *unprofitable* —
it is **inoperable**. The moves it would need do not occur.

### §4.5 Reported as-is

No parameter was revised. No re-run was performed. The one re-execution in this WO was the
distribution measurement above, which reads the corpus and touches no parameter.

---

## §2.7 THE FALSIFIER — status

**NOT triggered.** The falsifier was a *materially positive net P&L over ≥ 30 round trips*. There
were 0 round trips and net P&L is exactly 0. The arithmetic stands, unfalsified, and now with an
apparatus signature.

Note what the floor bought: it was declared before the run precisely so the verdict could not be
chosen afterwards, and it did real work here — it stopped "net P&L = 0" from being reported as a
break-even result. Zero P&L on zero trades is **absence of evidence**, and the registered rule says
so without me having to decide that after the fact.

---

## HONEST LIMITS OF THIS RESULT

Stated because the result is emphatic and emphatic results invite overreach:

1. **One instrument, one regime, 36.9 hours.** BTC/USD over 2026-08-05/06, which the distribution
   shows was a **quiet** market — a 0.41% maximum 5-minute move is calm. A volatile stretch would
   produce larger moves. It would need moves **4× the corpus maximum** merely to break even, but
   this corpus cannot speak to how often that happens.
2. **It says nothing about maker strategies.** Everything here is taker economics at 0.80%. The
   maker rate (0.40%, recorded not wired) is a different arithmetic and is D51's parked track.
3. **It says nothing about longer horizons.** Cost is fixed per round trip; a horizon of hours or
   days faces the same 1.62% bar against a much wider move distribution.
4. **It says nothing about better tiers.** Tier 1 is the only tier this account can substantiate.
   Tier 12 taker (0.10%) gives a 0.22% round trip — still above this corpus's median 5-minute move,
   but below its maximum.
5. **The trade channel remains unevaluated.** `TrivialMomentumStrategy` is still deferred, blocked
   on a trade-channel re-capture.

---

## EVERY ATTEMPT

1. **Grepped the stale-declaration count rather than trusting "four"** — found 10 across 6 files,
   including a file (`tasks.md`) absent from the previous enumeration.
2. **Confirmed `evidence/` is not gitignored before relying on committing into it** — 0.12 applied
   to my own workflow: the falsifier was a `check-ignore` rule being printed, and none was.
3. **Addressed WO-048 §U1's rejection of mid-price momentum head-on** in the registration rather
   than quietly reversing a prior ruling.
4. **Two test bugs of mine, found and fixed before the run:** the U4 tests initially placed the
   +10% frame in a bucket that had not closed, so bar 0's close was flat and the tests would have
   passed *vacuously* — asserting suppression of a signal that was never going to fire. Fixed to
   put the move inside the closing bucket. This is the same vacuous-satisfaction failure the
   registration warns about for N=1, caught in the proof of the protection against it.
5. **`BarMomentumStrategy` initially subclassed `Strategy`** and failed to instantiate (abstract
   `decide`). Resolved by *not* implementing `decide` — the adapter is the `Strategy` — rather than
   stubbing it, which would have been the D48 substitution one interface down.
6. **The run script crashed after the run** on a wrong key name (`excluded` vs `excluded_segments`)
   while printing its trailing summary. The result JSON was already written; the remaining figures
   were read from that artifact rather than re-running the backtest, so §4.5 holds strictly.
7. **Measured the return distribution only after the run**, as explanation, never as input to a
   parameter.

---

## §5 ACCEPTANCE

- [x] Three housekeeping items landed (§1.1 verbatim, §1.2 **10 sites** annotated, §1.3 doc)
- [x] `PRE_REGISTRATION.md` committed as **its own commit `e7b33c8`, before the build and the run**
- [x] Bar layer bite-proved — **PASS**, discriminating mutation, dual 5/5, direct demonstration
- [x] **CI green before the run** — `31232684456`, both legs, 475/2, counts from job logs
- [x] Parameters unchanged from registration — pinned by test, read from constants by the runner
- [x] Corpus v1 digest `e3ab1aec…` **unchanged**; 38/38 capture hashes verify
- [x] The report answers §2.6 (outcome ii) and §2.7 (falsifier not triggered) explicitly
- [x] All gates: lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

### Test count arithmetic

```
  455  baseline at HEAD 19ed158 (WO-052 close, CI 31227410759)
+  20  tests/test_bars.py (new)
─────
  475  expected  (+ 2 skipped)
```

| Leg | Order A (declaration) | Order B (seed 53053) |
|---|---|---|
| Python 3.14.6 | **475 passed, 2 skipped** (309.63s) | **475 passed, 2 skipped** (309.32s) |
| Python 3.11.15 | **475 passed, 2 skipped** (307.78s) | **475 passed, 2 skipped** (308.24s) |
| **CI 3.11** (93039450185) | **475, 2 skipped** (304.58s) | **475, 2 skipped** (301.17s) |
| **CI 3.14** (93039450249) | **475, 2 skipped** (304.87s) | **475, 2 skipped** (303.06s) |

**Post-run CI — run `31233356291`, GREEN both legs** on the report commit `ee42a41`:
`test (3.11)` 93041348293 → 475/2 both orders; `test (3.14)` 93041348280 → 475/2 both orders.
Twelve independent runs (four local, eight CI across the two commits) all report 475/2.

---

## FILES

| File | Disposition |
|---|---|
| `evidence/WO-053/PRE_REGISTRATION.md` | **NEW** — committed `e7b33c8`, before the strategy |
| `docs/decisions/2026-08-08-corpus-20260805-provenance.md` | **NEW** — §1.1 |
| `docs/decisions/2026-08-08-an-empty-result-from-a-query-that-cannot-fail.md` | **NEW** — §1.3 |
| `src/trading/data/bars.py` | **NEW** — the bar layer |
| `src/trading/strategy/bar_momentum.py` | **NEW** — strategy + frame adapter |
| `src/trading/backtest/segmented.py` | **CHANGED** — 2 minimal hooks, no accounting change |
| `src/trading/logkit/decision.py` | **CHANGED** — `BAR_FRAME_OUTSIDE_SEGMENT` declared |
| `tests/test_bars.py` | **NEW** — 20 single-purpose tests |
| `tools/wo053_bar_containment_bite_proof.py` | **NEW** — PASS |
| `specs/…` (6 files), `.env.example` | **ANNOTATED** — D47, frozen spec preserved |
| `captures/corpus_24h/corpus_20260805/` | **READ-ONLY — untouched**, verified twice |
