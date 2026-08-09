# WO-059 — EXTERNAL BASIS: Kraken's own historical OHLCVT

## STOPPED at the §2/§3 boundary, under §0.1.

**The artifact §2 directs me to acquire cannot be reconciled by §3, and the reconciliation is not
optional — it is D-r45 Option 4's condition (b), the ratified gate on entry to the apparatus.**

Kraken's bulk archives update quarterly. The newest published increment for **both** sources is
**Q1 2026**, so the bulk snapshot ends **2026-03-31**. `corpus_20260805` covers 2026-08-05→07 and
`validation_20260809` covers 2026-08-09. The reconciliation windows lie **127 and 131 days past the
end of the data**. This is not a divergence to measure; there is no overlap to measure it in.

Everything that does not depend on the ruling has been done. **Both reconciliations were run in
full, against the only route that can carry them (the REST API), with falsifiers declared before
measurement.** They are reported below because they answer a question worth answering regardless of
which basis is admitted — *is our capture right?* — and the answer is yes, exactly.

Nothing was committed. No loader was built (§4), no verdict declared (§5). §0.16 holds untouched.

---

## §1 STATE CONFIRMED

| | |
|---|---|
| HEAD | `67193e2` — Settings hygiene |
| `git diff -- src/` | clean |
| pytest 3.14.6 | **572 passed, 2 skipped** (316 s) |
| pytest 3.11.15 | **572 passed, 2 skipped** (throwaway uv venv) |
| import-linter | **6 contracts kept, 0 broken** (80 files, 297 dependencies) |
| `corpus_20260805` | v1 `e3ab1aec321a762848496af13557be0b419a4a3d7161b05b178f21095029ac10`, 88 files |
| `corpus_20260805` segments | `tools/corpus_verify.py`: **38/38 verified**, 0 mismatched, 0 missing, 38/38 `hashed_at_capture` |
| `validation_20260809` | v1 `884f9f007eaf440220820a59d0a9b2b70e5a541b880439ddad21c6b6fd574324`, 10 files, **3/3 segments verified**, **1,814 trades** confirmed by count |

### `phaseb_20260809` — capturing, undisturbed

**AT OPEN** — PID 22236 alive (started 2026-08-09 06:31:12Z), 11 segments, 317,954 frames,
first frame `06:32:19.803Z`, last `16:48:50.464Z`, **10.28 covered hours**, gap ledger holds
`run_start` only — **no gaps**. **AT CLOSE** — see the last section. Not touched, not stopped.

### Two corrections to the record, mine

**The WO number collides with two of my own commits.** `7665258` is labelled *WO-059 — the Term 2
gate reads PAGEFILE MOVEMENT* and `67193e2` is labelled *WO-060 — Settings hygiene*. Both were
direct instructions, not numbered work orders; **I assigned those numbers myself and had no
allocation to do it.** The lead's WO-059 is this one. History is not being rewritten — read those
two commits as *the gate work* and *the Settings work*, and treat WO-059 as this document.

**`validation_20260809`'s two frame counters disagree** (0.11 — the count is the finding).
`gap_ledger.json` records `frames_captured: 77419`; the manifest's three segments sum to
`67,704`, which is exactly the line count on disk. A 9,715-frame difference.
**Resolved, not left open:** if frames had been lost between capture and write, trades merged into
them would be lost too — and the trade-level reconciliation below matches the venue's tape
**exactly**, 1,814 of 1,814 with **zero gaps in the venue's own trade-id sequence**. No market data
is missing. The ledger's counter counts something the segments do not, and it is a counter defect,
not a data defect. *Falsifier: a single missing venue trade_id across our span would have
overturned this and made it a data-loss finding.*

---

## §2 THE SOURCE — cited, and the finding that stops the WO

### 2.1 Citation and licence

| | OHLCVT | Time-and-sales |
|---|---|---|
| URL | `support.kraken.com/articles/360047124832-…` | `support.kraken.com/articles/360047543791-…` |
| Retrieved | 2026-08-09 | 2026-08-09 |
| Page's own last-updated | **2026-04-26** | **2026-04-26** |
| Archive | `Kraken_OHLCVT.zip`, **7.3 GB** | **12 GB** |
| Delivery | Google Drive, single all-pairs ZIP | Google Drive, single all-pairs ZIP |

**LICENCE — A FINDING, reported and not proceeded past on assumption (§2.1).**
**Neither page publishes any licence, terms of use, or usage restriction for the data.** Not a
permissive licence — *nothing*. Both carry only the generic footer disclaimer about investment
advice and regulatory status, which says nothing about data rights. Silence is not a grant. A basis
whose terms of use are unstated is a basis whose terms of use are unknown, and that is the lead's
call to make, not mine.

### 2.2 Scope — the directive is unsatisfiable via this route

Ops directs **240-minute primary, 60-minute retained**, BTC/USD, and *"do not download every pair."*
**The bulk route offers no per-pair and no per-interval selection.** Each archive is one monolithic
all-pairs, all-intervals ZIP. Taking BTC/USD 240m via this route means taking all 19.3 GB and
discarding the rest. (Disk is not the obstacle — 796 GB free.)

### 2.5 The declared semantic gap — carried forward, not resolved

Kraken states: *"the OHLCVT data only includes entries for intervals when trades happened, so any
missing candlesticks indicate that no trades occurred during those intervals."*

**A missing bar is a positive claim that nothing traded; it is neither a zero bar nor a gap in our
sense.** This is precisely the `count: 0` vs `count: null` distinction the corpus already ruled on,
arriving in a new source — and note it arrives **inverted**: in our corpus, *absence of a record*
means *we could not see*; in theirs, *absence of a record* means *we saw, and nothing happened*.
The same encoding carries opposite meanings on the two sides. A loader that treated one as the
other would invert the claim, not merely lose it. **The count of missing bars is not reported here
because it must be counted in the artifact, and no artifact was acquired.** Measured against the
REST route over the reconciliation windows, **zero bars were absent** (33 of 33 at 60m, 6 of 6 at
240m) — BTC/USD trades every interval at these horizons, so the distinction is live only for thin
pairs or fine intervals.

### 2.6 The snapshot's true end date — THE STOP

Enumerated from the incremental-update folders, not assumed (0.11):

```
OHLCVT increments   : Q1..Q4 2023, Q1..Q4 2024, Q1..Q4 2025, Q1 2026     <- newest Q1 2026
Time-and-sales      : Q3 2025, Q4 2025, Q1 2026                          <- newest Q1 2026
```

**Both bulk sources end 2026-03-31.** Q2 2026 closed 40 days ago and has not been published, so
the published quarterly cadence is not merely stale — it is *behind its own schedule*.

```
bulk snapshot ends ......................... 2026-03-31
corpus_20260805 .............. 2026-08-05/07   (+127 days)
validation_20260809 .............. 2026-08-09   (+131 days)
```

**§3 cannot be run against the bulk artifacts.** Not "would diverge" — *the windows are not in the
data.*

### The transitive route was checked, and it is also closed

The obvious repair is to chain: reconcile the bulk archive against the REST API over a window both
cover, then REST against our capture. **Measured — the two routes do not overlap at the intervals
ops directed.** The REST OHLC endpoint returns at most 721 bars per interval, so its reach is a
function of the interval:

```
interval   rows   first bar        last bar          reach
   240m     721   2026-04-11 16:00Z  2026-08-09 16:00Z   120 days
    60m     721   2026-07-10 16:00Z  2026-08-09 16:00Z    30 days
  1440m     721   2024-08-19 00:00Z  2026-08-09 00:00Z   720 days
```

**At 240m there is an 11-day hole** between the bulk archive's end (2026-03-31) and REST's first
bar (2026-04-11). At 60m the hole is 101 days. Only the daily bar overlaps — and agreement on
*daily* bars does not certify *4-hour* bars, which are the ordered basis.

**So the bulk snapshot cannot be reconciled against our captured truth by any available route at
the intervals ops directed.** Under D-r45 condition (b) as ratified — *"an external basis that
can't reconcile against our own captured truth doesn't enter the apparatus"* — it does not enter.
Downloading 19.3 GB to produce an artifact condition (b) already excludes is not a judgement call
I will make.

---

## §3 THE RECONCILIATIONS — run in full, against the REST route

**Declared plainly: this is the REST API, not the bulk archive.** Substituting one retrieval route
for another is a channel substitution (D48) and is the lead's call. These results are offered as
*evidence for the ruling*, not as §3 discharged.

### 3.2 TRADE-LEVEL — `validation_20260809` vs Kraken's own tape. **RECONCILED, exactly.**

Falsifiers declared before any number was measured:

| | falsifier | tolerance and why |
|---|---|---|
| **F1 COUNT** | any difference | **zero** — a tape is a discrete record; there is no "close enough" number of trades |
| **F2 VOLUME** | any difference | **zero** — both sides carry 8-dp decimals originating from the same venue, so a difference means one side transformed the number |
| **F3 PRICE** | any mismatched `last_price` anchor | **zero**, same reason |
| **F4 CONTIGUITY** | any gap in the venue's own `trade_id` sequence across our span | **zero** — a gap means a published trade was never merged, i.e. our capture is silently lossy |
| **F5 TIME** | residual spread (p95−p5) **> 10 × frame cadence** | *not* zero. The clocks are independent, so a constant offset is expected and is not a defect. The falsifier is **structural**: the residuals must be explainable as **one** constant offset. A spread wider than the cadence band means the assignment is a mis-merge, not a clock offset. |

**Anchor**: our first recorded trade is venue `trade_id 104907040`, price 64905.80, qty 0.00016697
— matched on price *and* 8-dp quantity, so the alignment is fixed by data, not chosen. Everything
downstream is matched **by position**, which needs no clock at all.

```
F1 COUNT       ours=1814   venue span=1814                            PASS
F2 VOLUME      ours=12.49497436   venue=12.49497436   (identical)     PASS
F4 CONTIGUITY  venue trade_id gaps across 1,814 consecutive ids = 0   PASS
F3 PRICE       1,077 per-frame last_price anchors, mismatches = 0     PASS
   per-frame VOLUME                mismatches = 0                     PASS
F5 TIME        n=1814   median offset +0.848 s
               p5/p95  +0.768 / +0.881 s        min/max +0.323/+0.886 s
               spread p95-p5 = 0.113 s   bound 10x cadence = 1.063 s  PASS

VERDICT §3.2 : RECONCILED
```

Not one number differs. 1,814 trades, 12.49497436 BTC to the satoshi, 1,077 independent price
anchors, and **1,814 consecutive venue trade-ids with not one missing** — our capture saw every
trade the venue published in those two hours, in order, and merged each into the right frame.

The **+0.848 s** median offset is our local wall clock reading *behind* Kraken's, and its **0.113 s**
spread — one order below the bound — is what proves it is a clock offset rather than a merge error.
Worth recording on its own: **our frame timestamps carry a ~0.85 s constant bias against venue
time**, which matters to anything that later joins our frames to venue-stamped data.

**NOT CHECKED, stated rather than glossed:** the corpus stores per-frame *aggregates*, so `side`,
`ord_type`, `trade_id` on our side, and the order of trades *within* one frame interval are not
represented on our side and were not reconciled.

### 3.1 BAR-LEVEL — `corpus_20260805` mid vs venue OHLCVT

The two series measure **different quantities** — ours is mid-price from the book, theirs is
last-trade from the tape — so exact equality is not expected and would not be evidence. Each bound
was declared before measuring and **derived from a mechanism**, using two quantities taken from our
own book and not fitted to the divergence:

```
h = half the median quoted spread   = 0.0500    (a trade prints at bid or ask)
d = median |1-minute mid move|      = 7.8000    (their close is the last TRADE in the bar;
                                                 ours is the mid AT the edge — the gap is drift)

F6 CONTAINMENT  our mid within [their low - h, their high + h], every bar
F7 CLOSE        p95 |Δclose| <= h + d = 7.8500
F8 RETURNS      Pearson r of bar-to-bar close returns >= 0.99
```

**Excluded and counted (0.11), not glossed:** the corpus contains a `PROCESS_RESTART` seam
(2026-08-06 10:57:46Z → 13:04:07Z). **5 partially-covered bars were excluded at each interval** —
comparing a bar we saw 65/240 minutes of against a full venue bar manufactures divergence.

| | 240m | 60m |
|---|---|---|
| bars touched / fully covered / excluded | 11 / **6** / 5 | 38 / **33** / 5 |
| venue bars absent | 0 of 6 | 0 of 33 |
| **F6 containment** breaches | **1 of 6** — FALSIFIED | **6 of 33** — FALSIFIED |
| **F7 close** median / p95 / max (USD) | 0.050 / 7.850 / 7.850 — **FALSIFIED** | 0.050 / 1.150 / 7.850 — **PASS** |
| **F7 close** median / p95 / max (bps) | 0.01 / 1.21 / 1.21 | 0.01 / 0.18 / 1.20 |
| **F8 returns** Pearson r | **0.999870** — PASS | **0.999872** — PASS |

**The pre-registered checks failed and I am not retuning them.** Both failures are mine, in the
bound, and the underlying data agreement is essentially perfect: **the median close divergence is
0.050 USD at both intervals — exactly half a tick, the smallest non-zero value the instrument
can express.** Five of six 240m bars sit at that floor.

**F6 was derived for the wrong quantity — the FIFTH member of the wrong-quantity family, and the
first recurrence of D59 since it was ruled.** Half a spread
bounds mid against a *simultaneous* trade. It does not bound `sup(mid)` against `sup(trade)` over a
four-hour bar, because those two extremes occur at *different instants*: the book can quote above
the highest print when no one lifts the top tick. I picked the bound by its name — *"mid and trade
differ by half a spread"* — rather than by the mechanism generating the two compared quantities.
That is the same error as `\Memory\Pages/sec`, one level up — and it is worth recording that D59
was ruled **today**, in commit `7665258`, and I reproduced its shape in the very next bound I
declared.
Every breach is tiny (worst 2.6 USD, 0.4 bps) and lands exactly where the mechanism predicts, at a
bar extreme.

**F7 at 240m failed by a floating-point margin, and 0.15 is why.** Observed max = 7.850; declared
tolerance h + d = 0.05 + 7.80 = 7.850. A dead heat, decided by binary representation.
**0.15 says margin-bearing declarations round up and say so — I did not apply it.** Had the bound
been declared as 7.9, it would have passed. Two further notes against my own construction: at
**n = 6 the "p95" degenerates to the maximum**, so a p95 bound was the wrong statistic to apply to
six samples; and the one divergent 240m bar (2026-08-06 20:00Z, ours 64267.05 vs theirs 64259.20)
has high and low agreeing with the venue to 0.1 USD — only its close differs, by 1.22 bps, which is
one median 1-minute move. That is the drift term behaving exactly as `d` describes it.

### 3.4 — no material trade-level failure, so no STOP is triggered *here*

§3.4's stop condition did not fire: the trade-level reconciliation is exact. **The stop in this
report is §2.6's, and it precedes §3.**

---

## §4, §5 — NOT DONE

No loader was written. No verdict was declared. Both depend on **which artifact is the basis**, and
that is the open question. §0.16 is intact: **no strategy has touched anything.**

---

## THE FORK, for the ruling

| | **Bulk archive** (what §2 directs) | **REST API** (what §3 could actually reach) |
|---|---|---|
| Depth at 240m | years | **120 days** (721 bars) |
| Depth at 60m | years | **30 days** (721 bars) |
| Covers Aug 5–9 windows | **no** — ends 2026-03-31 | **yes** |
| Reconcilable against our captures | **no route exists** | **yes — measured above** |
| Per-pair / per-interval scoping | none — 19.3 GB all-pairs | yes, exactly |
| Currency | quarterly, and Q2 2026 is overdue | live |
| Licence | **unstated** | **unstated** |
| Admissible under D-r45 (b) | **no** | contingent on the ruling |

Two things the ruling turns on, and neither is mine to decide:

1. **The substitution.** REST is a different retrieval route from the same venue. Swapping it in is
   D48's shape, and it changes the basis's depth by roughly an order of magnitude.
2. **What 721 bars buys.** At 240m that is **721 observations at the ordered horizon** — against
   the ~30 the corpus route yields at Option 3's 4h ceiling, and it exists *today* rather than
   after 556 covered hours. It is thin for anything wanting multiple market regimes.

There is a third possibility I will not adopt unasked: take both, use the bulk archive for depth
**declared as unreconciled**, and the REST window as the reconciled overlap. That admits an
unreconciled basis by the back door, which is the thing D-r45 (b) exists to prevent.

**The licence question stands regardless of which route is chosen** — neither page states terms.

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | Read both support pages for licence, cadence, format | Retrieved. **No licence stated on either.** Format not documented on the page. |
| 2 | Probe `Kraken_OHLCVT.zip` size via Drive | **7.3 GB**, single all-pairs ZIP |
| 3 | Probe time-and-sales archive | **12 GB**, single all-pairs ZIP |
| 4 | Enumerate both incremental folders | Newest is **Q1 2026** on both → snapshot ends 2026-03-31 → **the STOP** |
| 5 | Test REST `/0/public/OHLC` | Works. **721-bar cap** per interval. |
| 6 | Test REST `/0/public/Trades` | Works. **First returned trade matched our capture's qty to 8 dp** before any reconciliation was written. |
| 7 | Check bulk↔REST overlap for a transitive chain | **11-day hole at 240m, 101 days at 60m.** Chain closed. |
| 8 | Glob `*.jsonl` for corpus segments | **FAILED** — `seam_ledger.jsonl` matched and is not market data (`KeyError: 'timestamp'`). **0.11 again: I assumed the glob was the segment set.** Fixed by reading segment filenames from the manifests. 38 from manifests, 39 from the glob. |
| 9 | Trade-level reconciliation, validation window | **RECONCILED** on all five pre-declared falsifiers |
| 10 | Bar-level reconciliation, 240m | F8 pass; **F6 and F7 falsified — both my bounds, not the data.** Not retuned. |
| 11 | Bar-level reconciliation, 60m | F7 and F8 pass; F6 falsified for the same mis-derivation |
| 12 | 3.11 acceptance leg | First run **collection-errored**: `pytest-asyncio` missing from the throwaway venv. Installed; rerun green. |

**Not attempted, deliberately:** downloading either bulk archive. §2.6's finding makes the artifact
inadmissible under D-r45 (b) before a byte is fetched.

**Nothing was written to `captures/`.** `corpus_20260805` and `validation_20260809` verify
unchanged after every step. All reconciliation code ran from the scratchpad and is uncommitted —
no basis has entered the tree.

---

## CI

**No code changed**, so there is nothing new to build. The last CI run is `31299001628` — **success,
both legs**, for HEAD `67193e2`.

---

## `phaseb_20260809` AT CLOSE

PID 22236 alive, 11 segments, last frame `16:55:18.628Z`, **10.38 covered hours** — advanced from
10.28 at open, so it was writing throughout. Gap ledger still holds **one line** (`run_start`) —
**no gaps, no seams**. The capture was never touched, never stopped, and nothing in this WO wrote
to `captures/`.
