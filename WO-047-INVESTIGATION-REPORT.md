# WO-047 — BACKTEST OVER A SEGMENTED CORPUS: INVESTIGATION AND PROPOSAL

**Date:** 2026-08-07
**Base HEAD:** `592e19e` (WO-046 closeout, CI green run `31191726876`, 322 tests)
**SHIP IMPACT: NO** — investigation only. `git diff -- src/` **EMPTY** (pasted §5).
**Reference artifact:** `corpus_20260805` — 36.8867 covered h, 3,847,540 frames, 19 gaps, 1 seam
(`PROCESS_RESTART`, 2.1061 h), 2 runs. Read-only; digest unchanged (§5).

> **NO IMPLEMENTATION. Not a line.** Every question below is answered from the code as it stands, or
> marked **UNRULED** and escalated.

---

## ⚠ HEADLINE: TWO BLOCKING FINDINGS UPSTREAM OF EVERY QUESTION IN §2

The WO asks five semantic questions about running the backtest over segmented data. Before any of
them can matter, two structural facts make the run **impossible as currently specified**. Both are
code-wins findings; neither is a semantic choice.

### FINDING A — the corpus does not contain the fields the strategy needs

A real corpus frame (`corpus_HADI_20260805T22Z.jsonl:1`):

```json
{"timestamp": "2026-08-05T22:03:33.556536+00:00", "symbol": "BTC/USD",
 "bid": "64590.0", "ask": "64590.1", "bid_qty": "0.85185740", "ask_qty": "5.13905039",
 "spread": "0.1"}
```

`MarketState` requires (`market_state.py:29-45`):

| Field | In the corpus? |
|---|---|
| `timestamp`, `symbol` | ✅ |
| `best_bid`, `best_ask`, `best_bid_size`, `best_ask_size` | ✅ (as `bid`/`ask`/`bid_qty`/`ask_qty`) |
| **`trade_count`** | ❌ **ABSENT** |
| **`total_volume`** | ❌ **ABSENT** |
| **`last_price`** | ❌ **ABSENT** |

**Demonstrated, not inferred** — attempting the construction from a real corpus frame:

```
corpus frame keys: ['ask', 'ask_qty', 'bid', 'bid_qty', 'spread', 'symbol', 'timestamp']
TypeError: MarketState.__init__() missing 3 required positional arguments:
           'trade_count', 'total_volume', and 'last_price'
```

They are **required positional arguments**, not optional fields with defaults — so this is a hard
construction failure, not a degraded-quality read.

`TrivialMomentumStrategy` has exactly two signals, and **both depend on the three missing fields**:

- `trivial.py:97` — `price_change = (market_state.last_price - self._last_price) / self._last_price`
  → `last_price` is absent. With `None` this raises `TypeError`; with a substituted mid price it is
  **a different strategy**.
- `trivial.py:61` — `self._update_average_volume(market_state.total_volume)` → `total_volume` is
  absent, so the volume-spike branch (`trivial.py:101-103`) cannot be evaluated at all.

**Consequence:** the strategy as written cannot run over `corpus_20260805`. This is not a gap
problem; it is a *capture-schema* problem. The corpus writer (WO-043/WO-044,
`live_corpus_capture.py`) persisted top-of-book only. That was adequate for a continuity corpus and
is inadequate for this strategy.

**This is UNRULED and it is the first thing the lead must decide.** Options, none of which I have
implemented:
1. **Substitute** a derived price (mid, or last trade proxy) for `last_price` and drop the volume
   branch → a *different strategy*; the number would not be "the trivial strategy over real data".
2. **Re-capture** with the fields included → a new corpus, a new grant, and `corpus_20260805`
   becomes a continuity artifact rather than a backtest input.
3. **Choose a different strategy** whose inputs are top-of-book only.

Option 1 is the tempting one and is the failure this apparatus exists to prevent: it produces a
number quickly by quietly redefining what was measured.

### FINDING B — the reader returns time windows, not data

`CorpusReader.read_window()` returns `CorpusWindow.segments`, and a `Segment` is
`(start_utc, end_utc, run_id)` — **an interval, not frames**. The reader answers *"may I read this
window, and where are its continuous stretches"*; it does not load market data.

The only corpus-to-`MarketState` loader that exists is `load_market_data_from_parquet`
(`runner.py:34-80`), which reads **Parquet**. The corpus is **JSONL**. There is no path today from a
corpus segment to a `List[MarketState]`.

**Consequence:** a frame-loading layer must be built, and it is the natural place to enforce that
frames are only ever yielded *within* an acknowledged segment. That is a design opportunity, not
just a cost — see §4.

---

## §1 THE THREE SURFACES

### §1.1 `BacktestRunner` — ingestion and every continuity assumption

`src/trading/backtest/runner.py`, the whole loop (`126-228`), key lines:

```python
157        for market_state in data_points:
158            if processed_count >= max_events:
159                break
161            # Track data window
162            if window_start is None:
163                window_start = market_state.timestamp
164            window_end = market_state.timestamp
167            desired_position = self._strategy.decide(market_state)
174            decision, approved_order, _ = self._risk_engine.check(
175                desired_position, self._position_state, market_state.timestamp)
185            self._execution_client.set_market_state(market_state)
188            fill = await self._execution_client.place_order(...)
197            self._pnl_report.add_trade(
198                timestamp=datetime.fromisoformat(fill["timestamp"]), ...)
209            self._update_position(fill)
```

**Shape expected:** `data_points: List[MarketState]` (`128`) — a single, fully-materialised, in-memory
list. Not an iterator, not segments.

**Continuity assumptions enumerated:**

| # | Site | Assumption |
|---|---|---|
| C1 | `157` | ONE `for` over ONE stream. There is no segment concept; adjacency in the list *is* adjacency in time. |
| C2 | `162-164` | `window_start`/`window_end` are first and last timestamps. Reported as `data_window` (`222-226`) — **a span that silently absorbs every gap and the seam**: 36.8867 covered hours would be reported as a ~39.0-hour window. |
| C3 | `158` | `max_events` default **1000** (`129`). The corpus has **3,847,540** frames — a naive run covers **0.026%** and silently truncates. |
| C4 | `128` | `List[MarketState]` materialised in memory. 3.85 M `MarketState` objects is a multi-GB allocation; this shape does not survive corpus scale. |
| C5 | `167` | `self._strategy` is a single instance across the whole loop — its state (see §1.2) crosses every boundary, because no boundary exists. |
| C6 | `114-121, 245-249` | `self._position_state` likewise persists across the whole loop; nothing resets or flattens it. |
| C7 | `198` | The trade timestamp comes from `fill["timestamp"]`, which is `datetime.now(UTC)` (`paper.py:288`) — **replay wall-clock, not market time**. Every trade in the P&L report is stamped "now". |

**Not present (checked, and their absence matters):** no index arithmetic, no `t[i] - t[i-1]`, no
rolling *time* windows, no annualisation, no drawdown-duration, no bar aggregation. The runner is
tick-driven and order-driven only. **The elapsed-time exposure is C2 alone** — see §2.4.

### §1.2 The strategy under test — `TrivialMomentumStrategy`

`src/trading/strategy/trivial.py`. Entry/exit logic (`90-114`):

```python
 90    def _evaluate_signal(self, market_state: MarketState) -> Side:
 92        if self._last_price is None:
 93            self._last_price = market_state.last_price
 94            return Side.HOLD
 97        price_change = (market_state.last_price - self._last_price) / self._last_price
100        volume_spike = False
101        if self._average_volume and self._average_volume > 0:
102            volume_ratio = market_state.total_volume / self._average_volume
103            volume_spike = volume_ratio >= self.VOLUME_MULTIPLE
106        self._last_price = market_state.last_price
109        if price_change >= self.PRICE_CHANGE_PCT or volume_spike:
110            return Side.BUY
111        elif price_change <= -self.PRICE_CHANGE_PCT:
112            return Side.SELL
114            return Side.HOLD
```

**State carried across ticks (`38-43`):**

| State | Warm-up | Nature |
|---|---|---|
| `_last_price` | **1 tick** (`92-94` returns HOLD on the first) | the *immediately preceding tick's* price — the comparison is tick-adjacent, never time-aware |
| `_volume_samples` | up to **100 samples** (`85-86`, FIFO) | count-based, not time-based |
| `_average_volume` | needs ≥1 sample; meaningful at ~100 | simple mean over the last ≤100 samples |

**There is no position state in the strategy** — it emits a fixed 0.1 BTC `DesiredPosition` (`70`)
and never reads its own position. Entry and exit are the same code path; "exit" is just a SELL
signal. **Warm-up is by COUNT, never by elapsed time** — which is the crux of §2.2.

Also note `trivial.py:73`: `DesiredPosition.timestamp = datetime.now(UTC)` — replay time, not market
time, mirroring C7.

### §1.3 `compute_execution_costs` + `_simulate_fill` — what a fill needs

`execution/costs.py:58-125`. A fill consumes **only** the current `MarketState`:

```python
 88    spread_pct = (market_state.spread / market_state.mid_price) * Decimal("100")
 89    if spread_pct > ABNORMAL_SPREAD_PCT_THRESHOLD:      # >5% -> ABNORMAL_SPREAD_REJECT
 98    if side == "BUY":  executed_price = market_state.best_ask
101    else:              executed_price = market_state.best_bid
104    notional = size * executed_price
107    fees = notional * (fee_rate_pct / Decimal("100"))
111    spread_cost = (market_state.spread / Decimal("2")) * size    # attribution only
114    slippage_cost = notional * slippage_factor
117    total_cost = fees + slippage_cost
```

**Needs:** `best_bid`, `best_ask`, `spread`, `mid_price`. **All present in the corpus.** The cost
model is the one component that transfers to corpus data unchanged.

**Does anything assume the previous state is adjacent in time? — NO, and that is the problem.**
`compute_execution_costs` is memoryless: it prices whatever tick it is handed, with no reference to
any prior state. There is no site at which the fill path *could* notice a gap.

The staleness guard (`paper.py:171-184`) looks like it would:

```python
178        state_age = datetime.now(UTC) - self._market_state_timestamp
179        if state_age > self._staleness_threshold:        # DEFAULT_STALENESS_THRESHOLD_SECONDS = 18
```

but `_market_state_timestamp` is set to `datetime.now(UTC)` at registration (`paper.py:122`), **not**
from `market_state.timestamp`. In a backtest, `set_market_state()` is followed immediately by
`place_order()` (`runner.py:185-188`), so `state_age ≈ 0` **regardless of how old the data is or how
large the preceding gap was**. **The staleness guard is inert under replay.** It protects the live
path only.

---

## §2 THE SEMANTIC QUESTIONS

### 2.1 Position across a gap

**Today:** the position (`runner.py:114-121`) is mutated by `_update_position` (`230-249`) and
**never reset**. There is no gap concept, so a position open at a segment end simply continues into
the next segment's first tick as if nothing happened. Feeding segmented data naively **carries the
position across the hole silently**.

**What is honest — my recommendation:** **force-flat at segment end, and make the flattening
visible as a labelled event.** The position was held over an interval in which the system could not
see the market and could not have reacted; claiming P&L across it asserts a counterfactual.

**Does the answer depend on duration or cause?** Yes, and the WO's asymmetry is exactly right —
carrying across 2.1 hours is a strictly bigger lie than across 16 seconds. But I recommend **NOT**
making the rule duration-dependent, for one reason: any threshold is arbitrary and becomes a knob
that quietly changes the P&L. **Force-flat at every boundary is the one rule with no free
parameter.** The cost is realism (a 1.7-second reconnect would not have flattened a real trader);
the benefit is that no number depends on where a threshold was set.

**UNRULED — for the lead:** force-flat-always (my recommendation, no free parameter) vs
force-flat-above-a-duration (more realistic, introduces a tunable that moves the P&L) vs
refuse-to-backtest-across-gaps (most conservative; yields 20 independent results, see §2.5).

### 2.2 Indicator warm-up across a segment boundary

**Today:** `_volume_samples` and `_last_price` (`trivial.py:41-43`) are instance state on a single
strategy object; **nothing resets them**. Naively fed, the first tick of segment N+1 computes
`price_change` against the **last tick of segment N** — across the hole. For the 2.1-hour seam that
is a price change over a window in which no data exists.

`_update_average_volume` would likewise mix samples from both sides of a gap into one mean.

**Warm-up is count-based (100 samples), never time-based**, so the strategy has no notion that its
history spans a discontinuity.

**Is a short segment tradeable? — MEASURED, not assumed.** The 19 gaps + 1 seam split the corpus
into 20 stretches:

```
INTER-DISCONTINUITY STRETCHES: n=19
  shortest 201.0 s    longest 27,838.5 s
  at the observed ~24-32 frames/s the SHORTEST holds ~4,823-6,431 frames
```

Against a 100-sample warm-up, the shortest stretch carries ~48-64× the requirement, so **warm-up is
not practically binding on this corpus**. **But that is an accident of this corpus, not a property
of the design** — a future capture with a burst of reconnects could produce sub-100-frame stretches,
and nothing in the current code would notice.

**Recommendation:** **reset all strategy state at every segment boundary**, and treat the first
tick of each segment as the warm-up tick (HOLD, per `trivial.py:92-94`). An indicator computed
across a hole is an indicator over data that does not exist.

**UNRULED:** if state resets per segment, a corpus with many short segments spends a large fraction
of its ticks in warm-up and never trades. The lead should rule whether a minimum segment length
(in frames) is required for a segment to be *eligible* — and if so, that threshold is itself a
number that shapes the result and must be declared.

### 2.3 Fill legality on the first tick after a gap

**Would the current fill path happily fill it? — YES, unconditionally.**

Three independent reasons, all verified above:
1. `compute_execution_costs` is memoryless (`§1.3`) — no site references a previous state.
2. The staleness guard is **inert under replay** (`paper.py:178` measures wall-clock since
   registration, ≈0 in a backtest).
3. The only rejection in the fill path is `ABNORMAL_SPREAD_REJECT` (`costs.py:89`), which tests the
   *spread within the tick*, not the *distance from the previous tick*. A post-gap tick with a
   healthy 0.1 spread passes cleanly however far the price has moved.

So a fill on the first tick after the 2.1-hour seam is executable in the model and **was not
executable in reality** — nobody could trade on a price they could not see coming.

**Recommendation:** the first tick of every segment is **observation-only, never fillable**. This
composes naturally with §2.2's warm-up reset (that tick already returns HOLD for `_last_price`
reasons) and it is a *structural* rule with no threshold.

**UNRULED:** whether the embargo is one tick or a declared settling interval. One tick is the
minimum honest rule and has no free parameter; longer is more conservative and introduces one.

### 2.4 Elapsed-time assumptions — the enumeration

I searched the backtest, strategy, execution and report surfaces for elapsed-time arithmetic.
**The exposure is far smaller than the WO anticipates**, because nothing is annualised or rate-based:

| Site | Uses elapsed? | Verdict |
|---|---|---|
| `runner.py:162-164, 222-226` `data_window` | **YES** — first→last timestamp | **THE ONE REAL SITE.** Silently absorbs 19 gaps + a 2.1 h seam: reports ~39.0 h for 36.8867 h of data |
| `runner.py:146, 213` `elapsed_seconds` | No (measures *replay* runtime) | harmless, but must never be confused with market time |
| `report.py:97-119` aggregates | No — sums and counts only | no annualisation, no Sharpe, no drawdown duration, no holding period |
| `trivial.py:80-88` volume SMA | No — **count**-based (100 samples) | see §2.2 |
| `costs.py` (whole module) | No | memoryless |
| `paper.py:178` staleness | Wall-clock of the *replaying process* | inert under replay (§2.3) |

**Nothing computes `t[i] - t[i-1]`.** No rates, no annualisation, no holding periods, no drawdown
durations exist to corrupt. **`data_window` is the single site that would lie**, and it would lie by
~2.1 hours.

**Recommendation:** `data_window` must report **covered** time (Σ segment durations) and
**elapsed** span separately, with the excluded gap and seam time itemised — precisely the vocabulary
WO-044 already established for the corpus meter (`cumulative_covered_hours` vs `elapsed_wall_hours`).
Reusing that vocabulary keeps one definition across capture and backtest.

### 2.5 What "the backtest ran over the corpus" would MEAN

Given 36.8867 covered hours in **20 discontinuous stretches**, "one result over the union" is not
available without deciding §2.1 — and every version of that decision changes the number.

**Recommendation: per-segment results, explicitly aggregated, with the aggregation stated.**

- Each segment is an **independent** backtest: fresh strategy state (§2.2), flat at start and end
  (§2.1), first tick observation-only (§2.3).
- **Costs** compose trivially — they are per-fill and memoryless, so Σ fees and Σ slippage over
  segments is exact.
- **P&L** composes by summation **only because every segment starts and ends flat**. That is the
  property that makes the sum meaningful; without force-flat, cross-boundary position carry would
  make the sum depend on boundary handling.
- **Position** never composes — it is per-segment by construction.

**The metric would be:** *"Net P&L over 36.8867 hours of verified continuous market data, in 20
independent segments, flat at every boundary, excluding 0.0167 h of in-run gaps and 2.1061 h of
inter-run seam."* Anything shorter than that sentence overstates what was measured.

**What it explicitly is NOT:** a 39-hour continuous backtest; a strategy evaluation (20 forced
flattenings are an artefact of the data, not of the strategy); or a tradeable-edge estimate.

**UNRULED:** whether per-segment results should also be reported individually. My view: yes — a
single aggregate hides that some segments are minutes and others hours, and the distribution across
segments is more informative than the sum.

---

## §3 THE ACKNOWLEDGMENT DECISION

The reader refuses a corpus-spanning read unless the backtest names the classes it tolerates, per
request, per class. In `corpus_20260805` the classes present are:

Measured from the corpus via the reader (not from memory):

```
KEEPALIVE_RECONNECT    n= 1   min=16.863s     max=16.863s
VENUE_DISCONNECT       n=18   min= 1.681s     max= 3.287s
PROCESS_RESTART        n= 1   min=7581.835s   max=7581.835s   (2.1061 h)
```

| Class | Count | Observed durations | Recommendation |
|---|---|---|---|
| `KEEPALIVE_RECONNECT` | 1 | 16.863 s — the longest *gap* in the corpus | **ACKNOWLEDGE**, bounded |
| `VENUE_DISCONNECT` | 18 | 1.681 – 3.287 s | **ACKNOWLEDGE**, bounded |
| `PROCESS_RESTART` (seam) | 1 | 7581.835 s = 2.1061 h | **ACKNOWLEDGE — but only to SEGMENT at it, never to trade across it** |

**Per-class reasoning:**

- **`VENUE_DISCONNECT`** — seconds-scale, the venue dropped and we reconnected with a fresh
  checksum-validated book. Acknowledging it means "I accept that a few seconds are missing and I
  will not trade across them." Bound it explicitly (e.g. ≤ 60 s) so a *long* venue disconnect in a
  future corpus does not slip through under the same acknowledgment.
- **`KEEPALIVE_RECONNECT`** — same shape, same reasoning, same bound. The 16.86 s instance is the
  corpus's largest and is comfortably inside any sane bound.
- **`PROCESS_RESTART`** — 2.1 hours. Acknowledging it does **not** mean tolerating a 2.1-hour hole
  inside a continuous analysis; under the §2.1/§2.5 design it means *the backtest is permitted to
  read both sides and will treat them as separate segments*. Because force-flat applies at every
  boundary, acknowledging a seam and acknowledging a 1.7-second gap have **identical trading
  consequences** — which is the design working: the acknowledgment governs *reading*, the
  force-flat rule governs *trading*.
- **Open-ended / terminal gaps** — `corpus_20260805` has none (`open_ended_count: 0`). A future
  corpus with a breaker trip **must not** be acknowledged blanket-wise: `accept_open_ended=True`
  should require its own deliberate act, exactly as the reader already enforces.

**On the failure mode the WO names:** an acknowledgment that accepts everything to make the backtest
run is the failure. I want to be precise that I am *not* reaching for it. Under this design the
acknowledgment list is not a convenience — it is **load-bearing documentation** of which
discontinuity classes were present and tolerated, and it appears in the calling code where a
reviewer sees it. The protection against "acknowledge everything" is that **acknowledgment does not
buy continuity**: force-flat at every boundary means acknowledging more classes never produces a
more continuous backtest, only permission to read more segments. That removes the incentive.

**UNRULED:** the duration bounds (I suggest ≤ 60 s for both gap classes) are declared engineering
judgement with no operational basis yet. The lead should set them or accept them as declared.

---

## §4 THE PROPOSAL

### Design

1. **A corpus frame loader** (new) — reads a run's `.jsonl` segments and yields `MarketState`
   objects **only within an acknowledged, reader-approved segment**. It takes a
   `CorpusReader`-issued `CorpusWindow` and cannot be pointed at raw files, so the default-deny
   boundary cannot be bypassed by reading the corpus directly. **Blocked on FINDING A** — it cannot
   construct a `MarketState` until the missing-fields question is ruled.
2. **A segmented runner path** — `BacktestRunner` gains a segment-aware entry point that, per
   segment: constructs a **fresh strategy instance**, starts flat, treats the first tick as
   observation-only, runs the existing loop unchanged, and **force-flattens at segment end**.
3. **Per-segment results plus a declared aggregate** — the report reuses WO-044's covered-vs-elapsed
   vocabulary and itemises excluded gap and seam time.
4. **`data_window` corrected** to report covered and elapsed separately (§2.4).

### Diff shape (NOT applied)

| File | Change |
|---|---|
| `src/trading/data/corpus_frames.py` | **NEW** — `iter_segment_frames(window: CorpusWindow) -> Iterator[MarketState]`; refuses a segment not issued by the reader |
| `src/trading/backtest/runner.py` | **NEW METHOD** `run_segmented(window: CorpusWindow, ...) -> Dict`; existing `run()` untouched |
| `src/trading/backtest/report.py` | `generate_report()` gains per-segment breakdown + covered/elapsed split |
| `src/trading/strategy/interface.py` | possibly a `reset()` contract, or the runner constructs a fresh instance per segment (**preferred** — no interface change, and "fresh object" is a stronger guarantee than "reset() was called correctly") |
| `tests/test_backtest_segmented.py` | **NEW** — the bite proof below |

### Cost

Moderate and mostly in the loader. The runner change is additive (`run()` untouched). The cost model
needs **no change at all** — it already transfers unmodified, which is the one piece of good news in
this investigation.

### What it forecloses

- **Cross-segment strategies.** Anything needing history longer than one segment (multi-hour
  indicators) is not expressible under force-flat + state-reset. That is a real restriction and it
  is the honest one for this data.
- **A single "the strategy made $X over the corpus" headline.** The deliverable is a distribution
  over 20 segments plus a declared sum.
- **Reusing `corpus_20260805` for a volume/last-price strategy** unless FINDING A is ruled toward
  substitution — which I recommend against.

### Acceptance criterion I would hold it to

- No `MarketState` is ever yielded outside a reader-approved segment.
- Strategy state at the first tick of segment N+1 is **identical** to a fresh instance — provable by
  identity, not by inspection.
- Position is flat at every segment start and end; Σ per-segment P&L == reported aggregate.
- Reported time is covered time; elapsed and excluded gap/seam time are separate fields.
- The corpus digest is unchanged after a full backtest run.

### THE ANTI-SPLICE BITE PROOF

**The property:** *the backtest cannot silently trade across a hole.*

- **BITE** — a two-segment fixture with a known gap, engineered so that a naive continuous run WOULD
  fire a signal on the first post-gap tick (a price jump across the hole exceeding the 1% threshold).
  Assert: **no fill occurs on that tick**, the position was flat across the boundary, and the
  segment-boundary event is recorded.
- **DUAL (local and direct, S13)** — the *same* price jump placed **inside** one segment fires the
  signal and fills normally. Without this, a runner that simply never trades would pass the bite.
- **NECESSITY MUTATION** — remove the per-segment state reset (or the force-flat) and re-run: the
  bite fails (a fill appears on the post-gap tick, computed against a pre-gap price) while the dual
  still passes. That asymmetry is what proves the boundary rule is doing the work.
- Four artifacts, sha256 exact-restore, per §0.3.

**Why the mutation is the load-bearing part:** a backtest that produces *no* trades trivially never
splices. Only the dual + mutation together show the machinery refuses the *specific* illegal trade
while permitting the legal one.

---

## §5 EVIDENCE

```
$ git diff --stat -- src/
(empty)
```

**Corpus digest** — 88 files, `a025db1ea224e6fdcbf519c747e05d6c51277ad73e8c5f7016d6f65049c29c45`,
unchanged (§5, snapshotted before any work and re-verified at close).

**Gates:** `lint-imports` 6 kept / 0 broken · ruff clean.

---

## EVERY ATTEMPT

1. Confirmed HEAD `592e19e`, `git diff -- src/` empty, corpus digest snapshotted.
2. Read the three surfaces in full; enumerated seven continuity assumptions (C1–C7).
3. Searched for elapsed-time arithmetic across runner / strategy / costs / paper / report —
   found the exposure is **one site** (`data_window`), materially smaller than anticipated.
4. Compared a real corpus frame against `MarketState`'s required fields → **FINDING A**.
5. Traced `CorpusReader`'s return type → **FINDING B** (segments are intervals, not frames).
6. Traced the staleness guard's clock source → it is **inert under replay**.
7. Wrote no code. `git diff -- src/` empty, as required.

## STOP

Per §0.2 and §4. **UNRULED questions for the lead**, in the order they block work:

| # | Question | Blocks |
|---|---|---|
| **U1** | **FINDING A** — the corpus lacks `last_price`, `total_volume`, `trade_count`, which are the strategy's only inputs. Substitute, re-capture, or change strategy? | **everything** |
| U2 | §2.1 — force-flat always (no free parameter) vs duration-dependent (tunable that moves P&L) vs refuse-across-gaps | the runner design |
| U3 | §2.2 — is a minimum segment length required for eligibility, and what is it? | segment selection |
| U4 | §2.3 — post-gap embargo of one tick, or a declared settling interval? | fill legality |
| U5 | §2.5 — report per-segment results individually as well as aggregated? | the report shape |
| U6 | §3 — the duration bounds on gap-class acknowledgments (I suggest ≤ 60 s; declared judgement, no operational basis) | the acknowledgment list |

**U1 is not a semantic question and cannot be resolved by ruling on the others.** Until it is
answered, the backtest over `corpus_20260805` cannot be built, whatever is decided about gaps.
