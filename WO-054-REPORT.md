# WO-054 — PHASE B BUILD

**NO SOCKET WAS OPENED.** Every validation is static or fixture-based.
**SHIP IMPACT: YES** (capture path). Corpus v1 `e3ab1aec…` unchanged, 38/38 capture hashes verify.

> ## ⛔ THE FINDING THAT OUTRANKS THE REST — §4
>
> **A 24-hour horizon cannot be evaluated at ANY capture length under the current segmentation
> rule.** The longest continuous segment ever observed is **7.73 hours**; the mean is 1.76; **zero**
> segments reach 12 h. Capturing 30 days produces ~410 more segments of the same length, not longer
> ones — because gaps arrive at a rate per *hour*, not per *capture*.
>
> The naive derivation (24 h × 30 obs = 720 covered hours) is not merely expensive. **It is
> unreachable in principle.** §4 below gives the arithmetic and three options; **the lead must rule
> the horizon ceiling before the long capture's target can be set.**

---

## §1 STATE CONFIRMED

| Check | Value |
|---|---|
| HEAD at open | `c4f40b9` — WO-053 close |
| Baseline | **475 passed, 2 skipped** (3.14) |
| `git diff -- src/` | clean |
| lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition | all green, **31/31** |
| corpus v1 digest | `e3ab1aec…`, 88 files — verified |
| corpus manifest | **38/38** segments match capture-time SHA-256 |

*Attempt noted:* the baseline run reported `474 passed, 1 failed` — the reason-code vocabulary guard,
which reads `src/` **at test time**, caught `trade_channel.py`'s new codes mid-run before
`decision.py` declared them. 474 + 1 = 475 confirms the baseline; re-running the guard after both
files landed gives 11/11. This has now bitten in five consecutive WOs and is a known property of a
guard that reads the working tree rather than an import snapshot.

---

## §2 THE TRADE CHANNEL

### §2.1 The citation

| | |
|---|---|
| **Source** | https://docs.kraken.com/api/docs/websocket-v2/trade |
| **Retrieved** | **2026-08-08** |
| Endpoint | `wss://ws.kraken.com/v2` — the socket the book channel already uses |
| Auth | none (public) |

Subscribe: `{"method":"subscribe","params":{"channel":"trade","symbol":["BTC/USD"],"snapshot":false}}`

Payload fields, as published: `symbol`, `side` (taker direction), `qty`, `price`, `ord_type`,
`trade_id`, `timestamp`. `type` distinguishes `snapshot` from `update`.

**We decline the snapshot deliberately.** With `snapshot: true` the channel delivers "the most
recent 50 trades" — activity from **before** capture began. Merging those into the first frame
would fabricate the opening frame's `count` and `volume` out of pre-capture trades. Declining costs
nothing, since we want only what happens inside the window.

### §2.3 Merge semantics — declared in the schema

Full contract: **`evidence/WO-054/trade_merge_schema.md`**, committed as a declarative schema so
this module and any future reader are both built to satisfy it — the WO-014c-2 precedent, rather
than the reader inheriting whatever the capture happened to write.

**Association: per book frame, as a delta over `(previous frame, this frame]`.**

- *Not per time bucket* — that would impose a bar interval **at capture time**, freezing a choice
  WO-053 showed belongs to the strategy layer. A corpus captured in 1-second buckets cannot later
  be read at 100 ms.
- *Not a separate stream* — that forces every reader to time-align two streams itself, and that
  alignment is exactly where splices get introduced (the D20 family), with nothing to segment it.

**Declared cost:** the interval length is the book's irregular update cadence. A consumer wanting
fixed intervals must aggregate, as `bars.py` already does.

### The three states — and why `null` is not `0`

| Situation | `observable` | `count` | `volume` | `last_price` |
|---|---|---|---|---|
| trades occurred | `true` | ≥1 | sum | the price |
| **listening, nothing traded** | `true` | **`0`** | **`"0"`** | **`null`** |
| **channel down** | **`false`** | **`null`** | **`null`** | `null` |

> **`count: 0` is a positive claim — *we were listening and nothing traded*.
> `count: null` is the absence of a claim — *we could not see*.**

A corpus that wrote `0` during an outage would say "no trades occurred" when it meant "the trade
channel dropped" — the misattribution family (host problem as venue problem) one channel over.

**`last_price` is never fabricated.** No substitution from mid, from the previous trade, or from
anything else. That is the D48 substitution moved to *capture* time, where it is **harder** to
catch because the reader has no way to tell an invented price from an observed one.

`running_last_price` (carried forward) is a **separately named** field with
`running_last_price_age_ms`. It is retained *through* an outage, because the last price we saw
genuinely is the last price we saw and the age states exactly how stale it is; `observable: false`
is what stops a reader treating it as current. Nulling it would discard true information.

### §2.4 Partial outage — and a ruled set I did NOT extend

`GAP_CAUSES` is **RULED AND EXHAUSTIVE** (`evidence/WO-014c-2/gap_schema.txt` §1.1: *"The taxonomy
is RULED and EXHAUSTIVE. It is not extended here."*). Its fifth member, `HOST_SUSPEND`, came from an
explicit **lead ruling** (WO-015 addendum A).

**I did not add a sixth.** Two reasons, the second decisive:

1. Extending a ruled closed set is the lead's call, not mine (§0.1).
2. **It would be semantically wrong.** That schema defines a gap as *"an interval during which NO
   validated `MarketState` is emitted"*. During a trade outage **the book keeps flowing and states
   keep being emitted — there is no gap.** Recording one would corrupt the gap ledger and,
   downstream, the covered-hours accounting: a trade outage would subtract book coverage that was
   never lost.

So it is a **separate `TradeChannelOutage` ledger** with two declared, producible, prefix-free
causes: `TRADE_CHANNEL_SUBSCRIBE_FAILED`, `TRADE_CHANNEL_DROPPED` (plus
`TRADE_CHANNEL_CAUSE_UNDECLARED` for the refusals).

### ⚠ SILENCE IS DELIBERATELY NOT A CAUSE — the honest limit

A subscribed channel that stops producing is **indistinguishable from a market in which nothing
traded**. Both look identical on the wire. Inventing a `TRADE_CHANNEL_SILENT` on a timeout would be
the same misattribution running *backwards* — fabricating outages on every quiet night. WO-053's
corpus makes that concrete: it was genuinely quiet.

**So this corpus cannot distinguish a silently-wedged trade channel from a quiet market.** Stated
here rather than papered over with a threshold. The detectable failures (socket death, explicit
unsubscribe, failed ack) are covered.

### §2.5 Bite proof — `tools/wo054_trade_merge_bite_proof.py`, **VERDICT: PASS**

| Artifact | Result |
|---|---|
| 1 — PRISTINE | rc 0, 34 passed |
| 2 — **MUTATION FABRICATE** (outage reports `count: 0` + carried price) | rc 1 — misattribution **bite fails**; dual **4/4 holds**; regime untouched |
| 3 — **MUTATION HARDCODE** (regime ignores input) | rc 1 — regime bite fails; trade sets untouched |
| 4 — RESTORED | rc 0, 34 passed |
| 5 — **DIRECT DEMONSTRATION** | the two records printed side by side |

```
LISTENING, NOTHING TRADED  ->  observable=True  count=0     volume=0     last_price=None
CHANNEL DOWN, CANNOT SEE   ->  observable=False count=None  volume=None  last_price=None
outage ledger              ->  [{'cause': 'TRADE_CHANNEL_DROPPED', 'resolved': False, ...}]

trade_channel.py sha256 BEFORE/AFTER : 056212ae…  IDENTICAL: True
regime.py        sha256 BEFORE/AFTER : b3317100…  IDENTICAL: True
FABRICATE discriminates (bite fails, dual 4/4, regime untouched) : True
HARDCODE  discriminates (regime bite fails, trade sets untouched): True
```

Artifact 5 asserts the **economic object** (§0.9): the difference between a claim of zero and the
absence of a claim, visible without reading a test name.

---

## §3 REGIME RECORDING — THE EIGHTH DIMENSION

### The declared form

A **percentile distribution of absolute returns over non-overlapping windows**, at horizons
**1 / 5 / 15 / 60 minutes**, computed within segments only, with counts at the cited cost
thresholds (0.5%, 1.0%, 1.6216%, 3.2432%).

**Why a distribution, not a single σ.** A lone realized-vol figure would not have supported WO-053's
finding, which needed the **median** (cost is 39× typical) *and* the **maximum** (cost is 4× the
largest thing that happened). σ also compresses a fat tail into the same number as a uniform wiggle,
and the whole question — *could any move have paid the round trip* — lives in the tail. This form
lets a future reader ask "what was the largest N-minute move" **without re-reading the corpus**,
which is §3.2's stated bar.

### §3.2 The falsifier — what this summary CANNOT support

Carried **in the artifact itself** (`not_supported`), not only in a docstring:

1. **Direction or autocorrelation** — magnitudes only. Supports "a move of size X was available",
   never "a momentum strategy would have caught it".
2. **Intra-window path** — endpoints only. A window that went +2% and returned reports ~0%, so the
   summary **understates** intrabar opportunity.
3. **Horizons outside the declared list** — do not interpolate; volatility does not scale as √t at
   fine horizons in practice.
4. **Moves spanning a discontinuity** — never observed, by construction.
5. **Liquidity, depth or spread regime** — this is a *price* summary.

### §3.3 Computed by committed code in the tree it certifies

`src/trading/data/regime.py`, in `src/`, under 12 tests, bite-proved. This satisfies the D51
standing rule that `a025db1e…` violated.

---

## §4 THE WINDOW DERIVATION — AND WHY IT DOES NOT TERMINATE

### §4.1 Declared horizon range

**1 hour to 24 hours.** These are the horizons the fee bar leaves alive: WO-053 killed everything
below, and this corpus's regime data now extends that to the hourly scale (max 60-minute move
0.5388% against a 1.6216% round trip).

### §4.2 The naive derivation

Required observations: **30 non-overlapping**, the same conventional small-sample floor WO-053
declared and justified.

```
longest_horizon × required_observations = minimum cumulative covered hours
        24 h     ×        30            =        720 covered hours  (30 days)
```

### §4.3 The sanity check against the machinery — **and it fails**

§4.3 says that if the derivation yields weeks, that is the answer, and not to shorten it for
convenience. **The problem is not that 720 hours is too long. It is that 720 hours yields zero
24-hour observations.**

A 24-hour window must lie **inside one continuous segment** — windows never span a discontinuity.
Measured from `corpus_20260805`:

| continuous segment length | |
|---|---:|
| min | 0.056 h |
| median | 0.866 h |
| mean | 1.757 h |
| **max ever observed** | **7.733 h** |
| segments ≥ 12 h | **0** |
| segments ≥ 24 h | **0** |

Empirical observation yield, per horizon, from the real segment distribution:

| horizon | obs in this corpus | obs per covered hour | covered hours for 30 obs |
|---:|---:|---:|---:|
| 15 min | 138 | 3.741 | **8** |
| 30 min | 64 | 1.735 | **17** |
| 1 h | 24 | 0.651 | **46** |
| 2 h | 9 | 0.244 | **123** |
| 4 h | 2 | 0.054 | **553** |
| 6 h | 1 | 0.027 | **1,107** |
| 8 h | 0 | 0.000 | **IMPOSSIBLE** |
| 12 h | 0 | 0.000 | **IMPOSSIBLE** |
| **24 h** | **0** | **0.000** | **IMPOSSIBLE** |

**Gaps arrive at 0.515 per covered hour, a rate per hour and not per capture.** Capturing longer
adds segments, not longer segments. Treating gaps as Poisson at that rate, the chance of a
24-hour gap-free stretch is `e^(−0.515×24) ≈ 4×10⁻⁶`; the expected capture needed to see one is on
the order of **millions of hours**.

### §4.5 So: operationally implausible, and what would have to change

Three options. **The ruling is the lead's; I state the costs.**

**Option 1 — a horizon-relative discontinuity policy.** Today *any* acknowledged gap segments the
window. For a 24-hour horizon a 17-second reconnect is 0.02% of it. Refusing to evaluate a daily
return because of a 17-second book gap makes daily evaluation impossible **forever, at any capture
length**. A declared rule — *a gap shorter than X% of the evaluation horizon does not segment it* —
would open the horizons the fee bar leaves alive.
**Cost, stated plainly:** this reintroduces the splice D20 forbids, in bounded form. The bound must
be declared and defended, and it is a genuine loosening, not a bookkeeping change. Note that U6's
existing structure already separates these concerns — *acknowledgment governs reading, force-flat
governs trading* — so this is an extension of an existing distinction rather than a new one.

**Option 2 — reduce the gap rate.** Most gaps are sub-minute reconnects. Reaching a useful 24-hour
yield needs roughly a **50× reduction** (to ~0.01 gaps/hour). Some gaps are venue-side and not ours
to fix. **Not plausible as the sole remedy.**

**Option 3 — cap the horizon at what segments support.** Honest and immediately actionable:

| ceiling | derived capture | |
|---|---:|---|
| 1 h | **46 covered hours** (~2 days) | comfortably achievable |
| 2 h | **123 covered hours** (~5 days) | achievable |
| 4 h | **553 covered hours** (~23 days) | achievable but long |
| 6 h | **1,107 covered hours** (~46 days) | at the edge |

**My recommendation:** Option 1 is *required* for genuinely daily horizons, and it is a real ruling
with a real cost. If the lead declines it, phase B's honest ceiling is **4 hours at 553 covered
hours (~23 days)**, and the suite's pre-registration must say so rather than claiming to test daily
momentum. **I did not quietly pick a smaller number** — that is §4.5's instruction, and the numbers
above are why the choice cannot be made by an executor.

### §4.4 The recomputed budget, at 720 covered hours

All figures **measured**, not estimated, except where the basis is stated.

| | measured |
|---|---:|
| corpus_20260805 on disk | 697.68 MB / 36.8867 covered hours |
| compression, book only | **26.7 : 1** (12.282 MB → 0.459 MB, one real segment) |
| **trade channel, raw** | **×1.86** |
| **trade channel, compressed** | **×1.50** (compression *improves* to 33.2 : 1 — the added fields are highly repetitive) |
| compressed, with trades | **0.730 MB per covered hour** → **0.53 GB** at 720 h |
| raw `.jsonl`, if retained | 24.2 MB/h → **17.4 GB** at 720 h |
| **free disk now** | **858.1 GB** |

*Basis for the trade-channel measurement:* one real 70,187-frame segment was re-serialised with the
`trades` sub-object at an assumed **1 trade per 8 book frames** and gzipped at level 9. The trade
rate is an assumption (BTC/USD trade rate was not measured — no socket); the **byte cost per frame
is measured**, and the compressed multiplier is dominated by the always-present field names rather
than by the values, so it is insensitive to that assumption.

**Retention caps (WO-045: 50,000 frames / 64 MiB) — CONFIRMED to hold at this scale**, and D53 is
right that they were built for exactly this. They bound **retained volume**, not run length, so they
are invariant to a 30-day capture. The trade channel raises the message rate, which means the caps
trim *sooner in wall-time* — the 64 MiB byte cap binds before the 50,000-frame count cap, and the
declared precedence (FLOOR > BYTE CAP > COUNT CAP) already handles that. **Abort condition 4 of the
proposed validation run watches this specifically.**

**Expected shape at 720 covered hours**, scaled from measured rates: **~39 runs, ~20 seams, ~371
in-run gaps**.

---

## §5 RETROACTIVE ANNOTATION

`docs/decisions/2026-08-08-corpus-20260805-regime.md` — **outside the ratified corpus** (WO-052's
lesson applied, not relearned: writing inside would change the v1 digest).

| horizon | n | median | p99 | max |
|---|---:|---:|---:|---:|
| 1m | 2,166 | 0.0123% | 0.1091% | 0.2197% |
| **5m** | 427 | **0.0402%** | 0.2714% | **0.4076%** |
| 15m | 135 | 0.0695% | 0.2610% | 0.3535% |
| **60m** | 23 | 0.1352% | 0.5388% | **0.5388%** |

**Classification: `QUIET`.** Windows at or above 1.6216% (the cited round trip): **zero, at every
horizon.**

**Corroboration with a real falsifier (0.12).** WO-053 measured the 5-minute maximum as
**0.4076%** using **overlapping** windows (n = 2,084). This summary uses **non-overlapping** windows
(n = 427) and reaches **0.4076%** — same value, different code path, different sample. The
non-overlapping scheme could easily have *missed* the peak window and reported lower; it did not.
The medians *do* differ (0.0412% vs 0.0402%), confirming the two samples are genuinely different
rather than the same computation twice.

**The 60-minute row extends WO-053 usefully:** even hourly moves peaked at 0.5388%, still **3×
below** the round trip. The death certificate is not narrowly about *minutes* — in this regime it
covers everything up to an hour. And it is **scoped to a quiet market**; a future reader must not
take it as universal.

---

## §6 THE CHECKLIST — `evidence/WO-054/phase_b_preconditions.md`

**GO/NO-GO: 🔴 NO-GO as it stands.**

| # | Term | Status |
|---|---|---|
| 1 | Host-suspend verification | 🟢 |
| 2 | **Capture-loop baseline fingerprint-matched to the host** | 🔴 **RED — blocking** |
| 3 | Checksum machinery green at HEAD | 🟢 |
| 4 | Gap-ledger integrity end-to-end | 🟢 |
| 5 | Disk budget + rotation | 🟡 AMBER — needs a retention ruling |
| 6 | Paper-env + no-credential preflight | 🟢 |
| 7 | TRADING_ENV guard + kill-switch bite proofs | 🟢 |
| **8** | **Regime recording armed** (new) | 🟢 |

**TERM 2 is RED because re-verification found the host changed**, which is exactly what
non-inheriting verification is for:

| | at the WO-044 capture | **now (2026-08-08)** |
|---|---:|---:|
| CPU load | 1.0% | 4.1% |
| **free memory** | **12.33 GB** | **3.26 GB** |

This is not pedantry. **D46**: memory pressure → swap → event-loop starvation → `HEARTBEAT_ABSENCE`
— *a host problem recorded as a venue disconnect*. A 30-day capture is precisely the duration over
which that misattribution compounds, and it would silently inflate the gap count that §4's whole
derivation rests on. WO-045's caps bound *our* memory use; they do nothing about 9 GB consumed by
something else on the box. **Operator action, not a code change.**

**TERM 5 is AMBER:** the corpus retains **both** raw `.jsonl` (673 MB) and `.jsonl.gz` (24 MB) for
every closed segment — 27.7:1 duplication, ~17.4 GB redundant at 30 days. 858 GB free absorbs it,
so it is not a capacity risk; the question is whether the duplication is deliberate (forensic
replay) or an artifact. **Not changed unilaterally — deleting raw capture data needs the operator's
word.**

### The grant's shape — proposed, not assumed (D24)

**PROPOSAL A — a short live validation run first. Ops's read is yes, and I agree.** Fixtures prove
the merge *logic*; they cannot prove Kraken's live trade channel behaves as documented, that the
subscribe is acked on the same socket as the book, or that inter-channel ordering matches what the
merge assumes. **Discovering a broken merge at week two of a 30-day capture is far worse than
spending one short grant now.**

- **Duration: 2 covered hours** — long enough to cross an hourly rotation and, at 0.515
  gaps/covered-hour, to meet ~1 reconnect, so both the rotation and gap paths are exercised live.
  Short enough that nothing is lost if it fails.
- **Product: a throwaway validation corpus** — explicitly *not* phase B data.
- **Six abort conditions**, each blocking the long capture; full text in the checklist. The sharpest
  is #2: any frame written with `observable: true` and a **fabricated** `last_price` — the D48
  substitution reaching production.

**PROPOSAL B — the long capture.** Resumable under one corpus-id, seams per D45, `TRADING_ENV=paper`,
detached. **Its target cannot be set until the lead rules the §4 horizon ceiling.** Also: the
WO-044 grant expiry anchor (2026-08-19) leaves **13 days**, which does not cover a 30-day capture —
**a new expiry must be issued.**

---

## EVERY ATTEMPT

1. **Cited the trade channel rather than implementing from recall** (0.1e, the fee lesson), and
   checked the subscribe shape against the book adapter's existing cited pattern for consistency.
2. **Read the gap taxonomy's governing document before touching it** — found it RULED and
   EXHAUSTIVE with its fifth member added by a lead ruling, and did not extend it. Verified the
   semantic argument independently: a trade outage produces no no-emission window.
3. **Considered and rejected `TRADE_CHANNEL_SILENT`.** Silence is indistinguishable from a quiet
   market; a timeout would fabricate outages nightly. Recorded as a stated limit, with a test
   pinning its absence so it cannot be added without confronting the reasoning.
4. **Measured rather than estimated the budget** — real compression ratio (26.7:1) from a real
   segment, real byte cost of the `trades` sub-object, real disk free. The one assumption (trade
   rate) is declared, with why the result is insensitive to it.
5. **Checked the derivation against the machinery instead of stopping at the arithmetic.**
   720 covered hours is the correct product of 24 × 30 and is *useless*, because no 24-hour segment
   exists. Enumerating the actual segment-length distribution is what surfaced it.
6. **Re-verified host terms afresh rather than inheriting**, which is the only reason the 9 GB
   memory change was found. It would have been invisible in a copied checklist.
7. **The vocabulary guard raced my edits again** (fifth consecutive WO) — counts reconciled to 475.
8. **Did not open a socket**, and did not measure the live trade rate, which is why that one budget
   input is a declared assumption rather than a measurement.

---

## §7 ACCEPTANCE

- [x] Trade channel built, **fixture-validated**, spec **cited** (URL + retrieval date)
- [x] Merge semantics declared **in the schema**, not only in code
- [x] Partial-outage handling declared — separate ledger, ruled set **not** extended, with reasoning
- [x] Regime summary built, **bite-proved**, computed by committed code in the tree it certifies
- [x] Window length derived **with the arithmetic shown** — and the derivation's failure reported
      rather than smoothed over
- [x] Budget recomputed at scale, measured; retention caps confirmed
- [x] `corpus_20260805` annotated **outside itself**
- [x] Checklist produced with the **eighth term** and the grant-shape proposal
- [x] Corpus v1 `e3ab1aec…` unchanged; 38/38 capture hashes verify
- [x] All gates: lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

### Test count arithmetic

```
  475  baseline at HEAD c4f40b9 (WO-053 close, CI 31233356291)
+  22  tests/test_trade_channel.py (new)
+  12  tests/test_regime.py (new)
─────
  509  expected  (+ 2 skipped)
```

| Leg | Order A | Order B (seed 54054) |
|---|---|---|
| Python 3.14.6 | **509 passed, 2 skipped** (309.35s) | **509 passed, 2 skipped** (308.97s) |
| Python 3.11.15 | **509 passed, 2 skipped** (308.06s) | **509 passed, 2 skipped** (307.92s) |

### CI

_pending — filled in on the close commit_

---

## FILES

| File | Disposition |
|---|---|
| `evidence/WO-054/trade_merge_schema.md` | **NEW** — the declarative contract |
| `evidence/WO-054/phase_b_preconditions.md` | **NEW** — the deliverable; 8 terms + grant shape |
| `src/trading/data/trade_channel.py` | **NEW** — subscribe, parse, merge, availability ledger |
| `src/trading/data/regime.py` | **NEW** — the eighth scope dimension |
| `src/trading/logkit/decision.py` | **CHANGED** — 3 trade-channel codes declared |
| `tests/test_trade_channel.py` | **NEW** — 22 tests |
| `tests/test_regime.py` | **NEW** — 12 tests |
| `tools/wo054_trade_merge_bite_proof.py` | **NEW** — PASS, two discriminating mutations |
| `docs/decisions/2026-08-08-corpus-20260805-regime.md` | **NEW** — §5 annotation |
| `captures/corpus_24h/corpus_20260805/` | **READ-ONLY — untouched**, verified twice |
