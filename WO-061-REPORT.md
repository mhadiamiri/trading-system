# WO-061 — THE SANCTIONED BULK BASIS (interim: Binance leg complete, Kraken leg blocked on the publisher's own quota)

**What landed:** the Binance licence gate is **resolved and passed**, the Binance snapshot is
**acquired, checksum-verified 229/229, enumerated, and certified by committed code**, and **§5.3
leg A — the bridge against our own captured book — PASSES at both intervals.**

**What did not:** `Kraken_OHLCVT.zip` and `Kraken_Trading_History.zip` are behind a **Google Drive
per-file download quota that is currently refusing every request**. It is not a permission problem
— the user granted the host, and a probe pulled the first 1,024 bytes of both archives with a valid
ZIP signature minutes earlier. The quota then closed again. A retry loop with backoff is running.
**§5.1 and §5.2 need those archives and cannot run until they arrive.**

**Also structural, and cited:** **§5.3 leg B cannot run today.** Binance publishes daily files *the
next day*, so `BTCUSDT-…-2026-08-09.zip` returns **404**. It becomes available 2026-08-10.

---

## §1 STATE CONFIRMED

**BASE discrepancy (0.1e), third WO in a row.** The WO names HEAD `329cb30`; actual HEAD at open
was **`b6dcc1b`** — the WO-061 STOP report from the blocked attempt. `git diff 329cb30..b6dcc1b --
src/ tests/` is empty.

| | |
|---|---|
| HEAD at open | `b6dcc1b` |
| `git diff -- src/` | **empty** |
| pytest 3.14.6 | **572 passed, 2 skipped** (316.45 s) |
| pytest 3.11.15 | **572 passed, 2 skipped** (313.68 s) |
| import-linter | **6 kept, 0 broken** |
| `corpus_20260805` | v1 `e3ab1aec…` · **38/38** verified |
| `validation_20260809` | v1 `884f9f00…` · **3/3** verified |
| CI | `31299001628` — the last green run; **no code changed** (only `.gitignore` and reports) |

**Test count arithmetic:** 572 + 2 = 574 collected, identical on both interpreters, unchanged.

### `phaseb_20260809` — the 12-hour leg COMPLETED CLEANLY during this WO

| | segments | last frame | covered h | gaps |
|---|---|---|---|---|
| **OPEN** | 12 | `2026-08-09T17:58:15.845Z` | 11.432 | 0 |
| **CLOSE** | 13 | `2026-08-09T18:32:19.513Z` | **12.000** | **0** |

**It was not stopped and not disturbed — it finished its scheduled `--duration-hours 12` leg.**
Verified as a clean shutdown rather than a death, because the two things a killed run cannot
produce are both present:

```
MANIFEST.json written : run 06:32:17.984Z -> 18:32:19.513Z, 13 segments, 356,728 frames
gap_ledger run_end    : gaps_detected 0 · incomplete 0 · checksum_failures_total 0
host_suspend_events   : 0
corpus_verify         : 13/13 segments match their capture-time SHA-256, 0 mismatched, 0 missing
digest (committed code): 3aeb35cc69e8aaa581b750c6ea1fe5b34fafde1547777737411826114083621c
```

**Whether to open the next leg is the lead's call** — it is resumable per corpus-id and a resume
needs a declared seam cause.

**Running gap rate, accumulating information only.** **0 gaps in 12.000 covered hours** against
`corpus_20260805`'s **0.515 / covered hour** (19 gaps ÷ 36.903 h — gaps, not the 38 ledger
entries). At the reference rate ~6.2 gaps were expected; Poisson probability of zero is
e^−6.18 ≈ **0.0021**. **The 556-hour window is NOT re-derived.** *Falsifier: gaps arriving at or
above the reference rate over later legs; one multi-hour outage would overturn it.*

**The frame-counter discrepancy recurs, and the recurrence is informative.** Ledger
`frames_captured 415,734` vs manifest segment sum **356,728** — a ratio of **1.165**, against
`validation_20260809`'s 77,419/67,704 = **1.143**. A *systematic* inflation, not random loss, which
supports the WO-059 conclusion that this is a counter defect rather than data loss.

---

## §2 THE BINANCE LICENCE GATE — RESOLVED, and it passes

### 2.1 Documents examined — enumerated (0.11), all retrieved 2026-08-09

| # | document | result |
|---|---|---|
| 1 | **`https://data.binance.vision/`** — the archive host itself | **No terms, no licence, no copyright, no disclaimer.** Confirmed by direct fetch of the full 2,591-byte body: the strings *terms*, *licen*, *copyright*, *disclaim* do **not appear**. Content is a nav bar, a table shell, and one outbound link — to the GitHub repo below. |
| 2 | **`https://data.binance.vision/robots.txt`** | **HTTP 404 — there is no robots.txt.** |
| 3 | Response headers on the archive host | **No `X-Robots-Tag`.** Served from `AmazonS3` via CloudFront; bucket `s3-ap-northeast-1.amazonaws.com/data.binance.vision`. |
| 4 | `github.com/binance/binance-public-data` — repo metadata via GitHub API | Owner `binance`, type **Organization**; 2,445 stars |
| 5 | The repo's full file tree via GitHub API | **No `LICENSE` file**; API reports `license: null` |
| 6 | The repo's `README.md` (raw) | Affirmative download instructions (quoted below); a `## Licence MIT` line |
| 7 | `binance.com/en/terms` | JS-rendered; body not retrievable by any route tried |
| 8 | `binance.com/en-JP/terms` | **§28 prohibitions retrieved.** Last updated **2026-07-16** |
| 9 | `binance.com/en-NG/terms` | Definitions section not retrievable |

### 2.2 The narrow question — and the finding that settles it

**§28.i's own named mechanism is absent on this host.** The clause prohibits *"bypass our robot
exclusion headers"* — and `data.binance.vision` **publishes no robots.txt (404) and sends no
`X-Robots-Tag`**. There are no robot exclusion headers there to bypass. That is not an
interpretation; it is two HTTP responses.

**The publisher's own current instructions, quoted verbatim from the README:**

> **"The website [Binance Data Collection](https://data.binance.vision/) offers easy access for
> anyone to download Binance's public market data, which is aggregated into `daily` or `monthly`
> files."**

> **"## How to download programatically"** — followed by working `curl` and `wget` command lines
> against `data.binance.vision`.

> *"More examples are available in the form of helper scripts in both the `python` and `shell`
> folders of this repository for downloading from the website."*

> *"## CHECKSUM — Each zip file has a `.CHECKSUM` file together in the same folder to verify data
> integrity."*

Binance publishes the archives, publishes a section titled *how to download them programmatically*,
ships the automation (`download-kline.py`, `download-trade.py`, `download-klines.sh`), and ships a
per-file SHA-256 for downloaders to verify against. **This is the act §3.2 performs, described and
invited by the publisher.**

**Against it,** ToU §28.i (en-JP, 2026-07-16): *"use any deep linking, web crawlers, bots, spiders
or other automatic devices, programs, scripts, algorithms or methods… to access, obtain, copy or
monitor any part of the Platform."* Whether `data.binance.vision` is "the Platform" is undetermined
— the definitions section was truncated on every locale route. **But the host is a separate
publication endpoint that carries no terms of its own and no exclusion headers, and the clause's
named mechanism is the one thing demonstrably absent there.**

### A correction to my own earlier reading

I first reported the repo as **MIT-licensed**, taken from a page summary. The GitHub API reports
`license: null` and the tree holds **no LICENSE file**; "MIT" appears only as a README line.
**And it would not matter, because it licenses the wrong thing** — that repo contains download
*scripts*. An MIT grant there covers the scripts, not the data on a different host. Treating a code
licence as a data licence because they share a page is exactly the wrong-quantity error 0.16 exists
to catch.

### 2.3 Disposition — §2.3 branch 3, the declared judgment, recorded

The archive host is **genuinely silent on terms** — and unlike WO-060, that is now a *performed
check*, not an assumption: the body was fetched in full and contains no terms text, robots.txt is a
404, and there is no `X-Robots-Tag`. So the declared-judgment form applies, in the D61 framing:

> Consuming a public, documented, published-for-download archive for internal research is the use
> the publication invites — the publisher's own documentation describes programmatic download for
> exactly this pattern and ships the scripts and checksums to do it.
> **SCOPE**: internal research only; no redistribution of the data in any form; the snapshot stays
> private to this project; no representation of the data as ours; published checksums verified as
> cited.
> **RESIDUAL, NAMED**: Binance could later assert restrictions, or the ToU's "Platform" definition
> could be shown to reach this host, in which case the basis is quarantined and any suite re-runs
> on whatever basis survives. Acceptable for internal research at this scale; **not** acceptable
> for anything published or commercial.

**"Silence is not a grant"** — which is why this is a declared judgment with a named residual and
not a cleared right. **GATE PASSED. Binance admitted for acquisition.**

### 2.4 Kraken — already authorized by D61 D. No licence gate applied.

---

## §3 ACQUIRE

### 3.1 Kraken — BLOCKED on the publisher's Drive quota, retrying

Both archives were located and **their identities confirmed by direct probe**:

```
Kraken_OHLCVT.zip           7,885,068,519 bytes (7.34 GiB)   magic PK\x03\x04  ✓
Kraken_Trading_History.zip 12,554,214,086 bytes (11.69 GiB)  magic PK\x03\x04  ✓
```

Minutes later every request returned **"Google Drive — Quota exceeded / Sorry, you can't view or
download this file at this time."** The quota is **per-file, rolling, and shared with every
downloader on the internet**; it flaps on a scale of minutes. All 13 OHLCVT and 3 time-and-sales
quarterly increments were also enumerated by Drive file-id and probed — **Q1 2026 is refused on
both**, so there is no smaller substitute route open either. A backoff loop is running with a
4-hour budget. Disk is not a constraint: **797 GB free**.

**Two defects in my own downloader, found and fixed — the first one is the serious one.**

1. **It wrote Google's "Quota exceeded" HTML page into `Kraken_OHLCVT.zip` and exited 0, printing
   `DONE 2009 bytes`.** A tool whose failure is indistinguishable from its success is worse than no
   tool — and this one would have handed a 2 KB HTML file to §5.1 as the primary basis. Fixed: an
   HTML content-type is never written to the destination, and the finished file must begin with
   `PK` or it is deleted and the run fails.
2. **Then I made an HTML response terminal**, which was the opposite error: "the server said no
   right now" is not "the file is unavailable". Fixed: HTML is retryable with backoff, and the
   confirm token is re-derived every attempt because it expires.

### 3.2 Binance — ACQUIRED, every file checksum-verified

**229 requested · 229 verified against the publisher's own SHA-256 · 0 checksum failures · 0
absent.** Verification happens *before* the file is written, so a mismatch cannot leave a bad
archive on disk.

### 3.3 What arrived — enumerated, not assumed (0.11)

| group | files | rows | first (UTC) | last (UTC) |
|---|---|---|---|---|
| monthly klines 4h | 108 | 19,608 | 2017-08-17 04:00 | 2026-07-31 20:00 |
| monthly klines 1h | 108 | 78,373 | 2017-08-17 04:00 | 2026-07-31 23:00 |
| daily klines 4h | 5 | 30 | 2026-08-04 00:00 | 2026-08-08 20:00 |
| daily klines 1h | 5 | 120 | 2026-08-04 00:00 | 2026-08-08 23:00 |
| daily trades | 3 | **6,773,561** | 2026-08-05 00:00 | 2026-08-07 23:59 |

**52 MiB on disk, 458 files** (each zip plus its checksum).

**The microsecond cutover was DETECTED, not assumed — and it corroborates exactly.** The README
states SPOT timestamps switch to microseconds on 2025-01-01. Rather than trusting that date, each
row was classified by magnitude. The split lands on:

```
4h : 16,146 ms + 3,462 us      2025-01-01..2026-07-31 = 577 days x  6 bars =  3,462   EXACT
1h : 64,525 ms + 13,848 us     577 days x 24 bars                        = 13,848   EXACT
```

*Falsifier, which could have failed and did not: a magnitude classifier disagreeing with the
publisher's stated cutover would have produced a non-integer number of days.*

**MISSING BARS, counted (the §2.5 discipline carried to this source):**

| interval | expected | present | **missing** |
|---|---|---|---|
| 4h | 19,625 | 19,608 | **17** |
| 1h | 78,500 | 78,373 | **170** |

**Every one is pre-2018-06** — 2017-09-06, and a multi-day cluster around 2018-02-08/09. **And the
semantics differ from Kraken's, which matters.** Kraken *states* a missing bar means no trades
occurred. Binance states no such thing, and a multi-day cluster in February 2018 is far more
plausibly **venue downtime** than four days of no BTC trading. **So a missing Binance bar is
ambiguous between "no trades" and "venue was down" — it is the `count: 0` vs `count: null`
distinction arriving a third time, and this time the publisher does not resolve it.** A loader must
not interpolate them and must not read them as zero-activity.

**What I did NOT take, and why (§3.1's "state what you discarded"):** monthly *trades* for the full
2017–2026 span. One month is **630 MB**; the span is ~68 GB. No declared check needs it — §5.2 is
bars against bars, and §5.3's trade-level work is confined to the capture windows. **Flagging
rather than silently narrowing: if the lead wants trade-level cross-venue history, that is a
separate ~68 GB acquisition.**

**A structural limit on §5.2, cited:** **Binance's first BTCUSDT observation is 2017-08-17
04:00 UTC.** §5.2 asks for "the same 2013–2025 span" — **no cross-venue comparison is possible
before 2017-08-17**, because the pair did not exist. Kraken's archive reaches back further alone.

---

## §4 PROVENANCE (D51)

**Binance — recorded.** `external/binance/PROVENANCE.json` holds source URL, S3 bucket, publisher
documentation, retrieval date, the host's own `Last-Modified`, licence disposition (§2.3 declared
judgment), contents, declared end date, first observation, integrity result, and the digest.

```
digest scheme : tools/corpus_digest.py v1 — COMMITTED CODE IN THE TREE IT CERTIFIES (D51)
digest        : a8cca9b13743b4059cb2f13dd0ebd137b8c856db3681a4ff642a6959498706b6
files         : 458 (at digest time; PROVENANCE.json is written after and is not inside it)
```

`/external/` was added to `.gitignore` with the same reasoning as `/captures/`: acquired archives
are not source, and nothing committed there could later be removed from history.

**Kraken — pending acquisition.**

---

## §5 THE RECONCILIATIONS

### 5.1 KRAKEN INTERNAL SELF-CONSISTENCY — **not run** (needs both archives)

The 0.16 mechanism statement stands and is recorded so a future session does not re-derive it:
aggregating Kraken's time-and-sales into 240m/60m bars and comparing against Kraken's published
OHLCVT compares **two distributions of ONE record** — same venue, same trades, same instants.
Unlike the mid-vs-trade case that produced WO-059's F6, these **are** simultaneous, so near-exact
agreement is expected and the tolerance derives from **the aggregation's own decimal rounding**,
not a guessed margin.

### 5.2 CROSS-VENUE HISTORICAL — **not run** (needs the Kraken archive)

No bound is declared here. Declaring one now and measuring in a later session would be
pre-registration in form only. One input is already measured and will feed it: the USDT basis and
its dispersion must be derived **out of sample**, from a historical period that does not overlap
§5.3's test window.

### 5.3 THE BRIDGE — **LEG A RUN AND PASSED**; leg B blocked by publication lag

**Mechanism, declared before measuring (0.16).** Ours is **mid-price from a Kraken book** — a
continuous quote process sampled at the bar edge, generated by resting limit orders. Theirs is the
**last trade inside the bar on Binance** — a discrete execution process, generated by an aggressor.
**Simultaneity, stated precisely:** closes are both labelled with the bar edge, but ours *is* at
the edge while theirs is the last trade *before* it — **not simultaneous**. Highs and lows are
extrema of two different processes attained at **different instants** — also not simultaneous,
**which is why no containment bound was declared at all.** That is WO-059's F6 not being repeated.
Two independent divergence sources compound: **quantity** (mid vs last-trade) and **venue**
(Kraken BTC/USD vs Binance BTC/USDT — a *multiplicative* basis, since USDT is not USD).

**F10 RETURNS — the load-bearing bound.** Pearson correlation of bar-to-bar **log** returns ≥ 0.99.
*Derivation, and why it is strong:* a constant multiplicative basis **cancels exactly** in log
returns, so F10 is immune to the venue basis **by construction**. Nothing fitted, no allowance
guessed. *Falsifier: r < 0.99 means the venues are not tracking and the bridge cannot carry a
reconciliation at all.*

**F11 LEVEL — reported, NOT tested, and said so.** Bounding the USDT basis needs an independent
USDT/USD reference and **the tree has none**. Declaring a judgment-derived number and then calling
its satisfaction a "check" is precisely how F6 and F7 went wrong, so it is not done here.

**Exclusions counted, per §5.3's explicit instruction:** 5 partially-covered bars excluded at each
interval — the corpus's `PROCESS_RESTART` seam.

| | 240m | 60m |
|---|---|---|
| bars touched / fully covered / **excluded** | 11 / 6 / **5** | 38 / 33 / **5** |
| Binance bars absent | 0 of 6 | 0 of 33 |
| **F10 log-return correlation** | **0.999103** (n=5) — **PASS** | **0.997110** (n=32) — **PASS** |
| F11 median BINANCE/KRAKEN ratio | 1.000871 → **+8.7 bps** | 1.000915 → **+9.2 bps** |
| F11 dispersion (median / p95 / max) | 0.72 / 2.17 / 2.17 bps | 0.93 / 2.74 / **3.53 bps** |

**LEG A VERDICT: the bridge tracks**, on the one bound that is basis-invariant by construction. The
two venues' 4-hour and 1-hour closes co-move at r > 0.997, and the USDT basis sits at **~+9 bps**
with dispersion **under 4 bps** across the window. *n = 5 at 240m is small and is stated as such.*

**LEG B — 2026-08-09 vs `validation_20260809` — CANNOT RUN TODAY.** Enumerated, not assumed:

```
2026-08-04  4h OK   1h OK   trades OK (16.9 MB)
2026-08-05  4h OK   1h OK   trades OK (16.8 MB)
2026-08-06  4h OK   1h OK   trades OK (14.3 MB)
2026-08-07  4h OK   1h OK   trades OK (15.8 MB)
2026-08-08  4h OK   1h OK   trades OK ( 4.9 MB)
2026-08-09  4h 404  1h 404  trades 404     <- NOT PUBLISHED
```

The README states daily files appear **the next day**. Leg B becomes runnable **2026-08-10**.
*(2026-08-08's 4.9 MB against ~16 MB for neighbours is not assumed to be a partial file — it is a
Saturday, and the file's own last timestamp will settle it when leg B runs.)*

### 5.4 Falsifiers

Every bound above was written before its measurement. **No bound was retuned.** F10 passed as
declared; F11 was deliberately left untested rather than given a guessed threshold.

---

## §6 VERDICT — partial, because one source has not arrived

**BINANCE: ADMITTED as the bridge**, on the §2.3 declared judgment and §5.3 leg A's evidence, with
these residuals declared where a future WO will read them:

- **MAY**: bar-horizon (≥1h) signal evaluation, with costs from the validated model.
- **MAY NOT**: anything finer than its bars — no spread, no depth, no microstructure, no sub-bar
  execution assumptions. The corpus remains the only basis for those.
- **VENUE AND QUOTE-ASSET BASIS**: this is Binance BTC/**USDT**, not the Kraken BTC/**USD** we would
  trade. The measured basis is **~+9 bps** with **<4 bps** dispersion over 2026-08-05..07. Any suite
  evaluated on it says so in its header.
- **PRE-2026 IS UNRECONCILABLE AGAINST OUR APPARATUS BY CONSTRUCTION** — we did not exist.
- **NO CROSS-VENUE HISTORY BEFORE 2017-08-17** — BTCUSDT did not exist.
- **MISSING BARS ARE AMBIGUOUS** on this source between "no trades" and "venue down", and must never
  be interpolated or read as zero activity.

**KRAKEN: NO VERDICT.** The archives have not been acquired. §5.1, the self-consistency check that
D61 substituted for the impossible one, has not run. **Nothing is admitted on the strength of a
file that has not arrived.**

**Primary-source assignment is deferred** until the Kraken leg completes: Kraken is intended as
primary (it is the venue we would trade) with Binance as the bridge, and confirming that ordering
requires §5.1.

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | `git log`, `git diff -- src/` | HEAD `b6dcc1b`, not `329cb30`; src diff empty |
| 2 | Gates: both interpreters, contracts | 572/2 and 572/2; 6/6 |
| 3 | Phase-B open reading | 12 segments, 11.432 covered h, 0 gaps |
| 4 | **Download `Kraken_OHLCVT.zip`** (1st) | Wrote a **2,009-byte quota HTML page** and reported DONE — **my defect** |
| 5 | Fixed downloader: reject HTML, require `PK` | Re-run → correctly REFUSED, exit 3, nothing on disk |
| 6 | Probe all 4 Drive archives + 16 increments | COMPLETE archives **served 1,024 bytes each with valid ZIP magic**; Q1-2026 increments refused |
| 7 | **Download `Kraken_OHLCVT.zip`** (2nd) | Quota closed again between probe and download |
| 8 | Rewrote downloader: HTML retryable, token re-derived per attempt | Running; 10+ attempts, all refused so far |
| 9 | `data.binance.vision` index, full body | **No terms text at all** |
| 10 | `data.binance.vision/robots.txt` | **404 — no robot exclusion headers exist** |
| 11 | Archive-host response headers | **No `X-Robots-Tag`**; AmazonS3 via CloudFront |
| 12 | `binance-public-data` via GitHub API | `license: null`, **no LICENSE file** — corrects my earlier "MIT" |
| 13 | Repo README raw | Affirmative programmatic-download instructions, quoted |
| 14 | Binance ToU: `/en`, `/en-JP`, `/en-NG` | §28 retrieved from JP; **"Platform" definition truncated on all three** |
| 15 | S3 listing for BTCUSDT | Monthly 4h: 216 keys; daily listings truncated at 1,000 (S3 page limit) |
| 16 | Daily availability probe, 2026-08-04..10 | **2026-08-09 and later: 404** — leg B blocked |
| 17 | Binance download + checksum verify | **229/229 verified, 0 failures, 0 absent** |
| 18 | Enumerate arrivals | Table above; µs cutover corroborated **exactly** |
| 19 | Missing-bar count | 17 of 19,625 (4h); 170 of 78,500 (1h); **all pre-2018-06** |
| 20 | Binance digest + PROVENANCE.json | `a8cca9b1…`, 458 files |
| 21 | §5.3 leg A, 240m and 60m | **F10 PASS both**; F11 reported not tested |
| 22 | Phase-B close | **Leg completed cleanly** — MANIFEST + `run_end` + 13/13 verify |
| 23 | §5.1, §5.2, Kraken §4, §6 Kraken verdict | **NOT RUN — archives absent** |

**Zero requests to `api.kraken.com`** — D61 ruling C respected throughout. Nothing written to
`captures/`. No `src/` change.

---

## §7 ACCEPTANCE

| requirement | status |
|---|---|
| Binance licence gate resolved **before** download | **met** — gate ran first, passed, declared judgment recorded |
| Both Kraken archives acquired, BTC/USD extracted | **NOT met — publisher quota** |
| Binance files checksum-verified against published `.CHECKSUM` | **met — 229/229** |
| Arrivals enumerated | **met** for Binance |
| Snapshots immutable with committed-code digests | **met** for Binance (`a8cca9b1…`) |
| Three reconciliations with pre-declared 0.16 bounds | **1 of 3** — §5.3 leg A run and passed; §5.1/§5.2 blocked |
| Failures reported not retuned | **met** — F11 left untested rather than given a guessed bound |
| Verdict with MAY/MAY-NOT and residuals | **met for Binance**; **no verdict for Kraken** |
| captures untouched | **met** |
| `phaseb_20260809` still writing | **completed its scheduled leg cleanly** — verified, not stopped by me |
| zero requests to `api.kraken.com` | **met** |
| all gates | **met** |
| test count with arithmetic | **met** — 572 + 2 = 574, unchanged |
| CI green both legs | **met** — `31299001628`; no code changed |

---

## ADDENDUM — the retry loops were STOPPED, and the reason is a correction to my own diagnosis

I called the Drive quota **per-file** on the strength of one observation: both complete archives
served bytes while the Q1-2026 increments were refused. **A later enumeration overturns that.**

**All 18 files — both complete archives and all 16 quarterly increments — were probed in one pass
and every single one was REFUSED:**

```
OHLCVT  Q1..Q4 2023, Q1..Q4 2024, Q1..Q4 2025, Q1 2026   13 files   all REFUSED
T&S     Q3 2025, Q4 2025, Q1 2026                          3 files   all REFUSED
OHLCVT COMPLETE (7.34 GiB) · T&S COMPLETE (11.69 GiB)      2 files   all REFUSED
```

Two hypotheses fit the earlier evidence; only one fits this:

- **Per-file, globally shared.** Explains the first probe. Does **not** explain 18-for-18.
- **Per-requester.** Explains both — including that the refusal became total *after* my loop had
  made 20+ attempts and started two aborted transfers.

**I cannot rule out that my own retry loop caused the total refusal, and the timing points at it.**
A 2-minute backoff sustained across 17 attempts is not polite behaviour toward a publisher whose
archives we were authorized to download — D61 authorized *downloading published files*, not
hammering the host that serves them. **Both loops are stopped.**

**The distinguishing test, declared before running it (0.12):** a single probe after a multi-hour
pause with no intervening requests. If it opens, the limit was requester-side and my loop was the
cause — which makes the fix "wait, then one attempt", not "retry harder". If it is still refused,
the limit is file-side and global, and the wait is on other downloaders worldwide.
**I did not run that probe, because running it immediately would destroy the thing it measures.**

## WHAT RESUMES THIS

1. **A long pause, then ONE probe** — not a loop. If open, download immediately; the transfer
   itself is a single sustained request, which is not what a rate limiter objects to.
2. **2026-08-10** for §5.3 leg B, when Binance publishes 2026-08-09.

Everything downstream is written and waiting: the BTC/USD extractor (reads the central directory,
never expands the 19 GB) and the §5.1 self-consistency reconciliation with its F12/F13/F14 bounds
already declared.
