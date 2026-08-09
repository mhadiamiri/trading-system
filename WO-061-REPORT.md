# WO-061 — THE SANCTIONED BULK BASIS

## STOPPED at §3. Both acquisition routes are blocked by the environment's permission layer, not by any finding.

Two fetches this WO requires were **denied by the sandbox's permission classifier**:

| # | attempt | needed for | result |
|---|---|---|---|
| 1 | `drive.usercontent.google.com` — `Kraken_OHLCVT.zip` (7.3 GB) | **§3.1** primary basis; **§5.1** self-consistency | **DENIED by classifier** |
| 2 | `data.binance.vision` — the archive host's own page | **§2.1** — the licence gate the WO requires *before* a byte is fetched | **DENIED by classifier** |

These are not findings about Kraken, Binance, or the data. They are this environment refusing the
network action, and **I am not going to route around a denial** — the deliberate consequence is
that §3, §4, §5 and §6 cannot run. §2 was carried as far as the blocked check allows, and it
produced a real result plus one correction to my own first reading.

**I need permission for those two hosts to continue.** Nothing else is missing.

---

## §1 STATE CONFIRMED

**BASE discrepancy, reported not assumed (0.1e).** The WO names HEAD `329cb30`. Actual HEAD is
**`0c4f1f4`** — the WO-060 STOP report, committed after this WO was written. It touches
`WO-060-REPORT.md` only; `git diff 329cb30..0c4f1f4 -- src/ tests/` is empty, so the base is the
tree the WO describes. This is the second WO in a row where the stated base trails by exactly one
report commit.

| | |
|---|---|
| HEAD | `0c4f1f4` (base `329cb30` + report only) |
| `git diff -- src/` | **empty** |
| pytest 3.14.6 | **572 passed, 2 skipped** (316.45 s) |
| pytest 3.11.15 | **572 passed, 2 skipped** (313.68 s, throwaway uv venv) |
| import-linter | **6 contracts kept, 0 broken** |
| `corpus_20260805` | v1 `e3ab1aec…` · **38/38** verified, 0 mismatched, 0 missing |
| `validation_20260809` | v1 `884f9f00…` · **3/3** verified, 0 mismatched, 0 missing |
| CI | `31299001628` — success both legs. **No code changed in this WO.** |

**Test count arithmetic**: 572 passed + 2 skipped = 574 collected, identical on both interpreters
and unchanged from `67193e2`. No test was added or removed — this WO wrote no code.

### `phaseb_20260809`

| | segments | last frame | covered h | gaps |
|---|---|---|---|---|
| **OPEN** | 12 | `2026-08-09T17:58:15.845Z` | **11.432** | **0** |
| **CLOSE** | 13 | `2026-08-09T18:13:20.775Z` | **11.684** | **0** |

PID **22236** alive at both readings, 140 MB working set. Covered hours advanced, so it wrote
throughout. Gap ledger holds one line (`run_start`) — **0 gaps, 0 seams**.

**Running gap rate, accumulating information only**: **0.000 / covered hour** against
`corpus_20260805`'s **0.515** (19 gaps ÷ 36.903 covered h — gaps, not the 38 ledger entries).
At the reference rate, 11.684 covered hours would be expected to yield ~6.0 gaps; observing zero
has Poisson probability e^−6.02 ≈ **0.0024**. **The 556-hour window is NOT re-derived here.**
*Falsifier: gaps arriving at or above the reference rate as the run lengthens; one multi-hour
outage would overturn the apparent improvement.*

---

## §2 THE BINANCE LICENCE GATE — carried as far as the block allows

### 2.1 Documents examined — enumerated (0.11), retrieved 2026-08-09

| # | document | route | result |
|---|---|---|---|
| 1 | `data.binance.vision` — the archive host itself | — | **NOT EXAMINED — fetch DENIED by classifier.** The WO names this document specifically. |
| 2 | `github.com/binance/binance-public-data` (repo metadata, via GitHub API) | direct | owner `binance`, type **Organization**; 2,445 stars; pushed 2025-01-09 |
| 3 | The repo's file tree (via GitHub API) | direct | **no `LICENSE` file** — enumerated, not assumed |
| 4 | The repo's `README.md` (raw) | direct | **affirmative download instructions**; a `## Licence MIT` line |
| 5 | `binance.com/en/terms` | direct + WebFetch | body is JS-rendered; **no text retrievable** |
| 6 | `binance.com/en-JP/terms` | WebFetch | **§28 prohibitions retrieved.** Last updated **2026-07-16** |
| 7 | `binance.com/en-NG/terms` | WebFetch | definitions section **not retrievable** |
| 8 | Definition of "Platform" in the ToU | 3 routes | **truncated or absent in every route** — see below |

### A correction to my own first reading, before anything else

My first pass reported the repository as **MIT-licensed**, taken from a page summary. **That was
wrong and I checked it.** The GitHub API reports `license: null`, and the file tree contains **no
`LICENSE` file at all**. The string "MIT" appears in exactly one place: a `## Licence MIT` line at
the foot of the README.

And it would not matter if it were a proper LICENSE file, because **it licenses the wrong thing**.
That repository contains `download-kline.py`, `download-trade.py`, `download-klines.sh` — *scripts*.
An MIT grant on a repository of download scripts licenses the scripts. **It says nothing about the
data on `data.binance.vision`**, which is not in that repository. Treating a code licence as a data
licence because they share a page is the wrong-quantity error 0.16 exists to catch, and I nearly
filed it.

### 2.2 The narrow question: is *downloading published archive files* prohibited?

**The affirmative side — the publisher's own current instructions, quoted verbatim from the README:**

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
ships the automation, and ships per-file SHA-256 checksums for downloaders to verify against. This
is **not** silence — it is an affirmative, current, official instruction to perform the exact act
§3.2 would perform.

**The restrictive side — Binance ToU §28.i (en-JP, last updated 2026-07-16), quoted verbatim:**

> **"use any deep linking, web crawlers, bots, spiders or other automatic devices, programs,
> scripts, algorithms or methods, or any similar or equivalent manual processes to access, obtain,
> copy or monitor any part of the Platform"**

> *"bypass our robot exclusion headers, or interfere or attempt to interfere with our Sites or the
> Services"*

**The clause turns entirely on whether `data.binance.vision` is "the Platform" — and I could not
resolve it.** The definitions section was truncated or unreachable on all three locale routes I
tried, and the one document that would settle it directly — **the archive host's own page — is the
fetch the classifier denied.** So §2.1's required check is **UNPERFORMED**, and the gate is
**INCOMPLETE**, not passed and not failed.

### 2.3 Disposition — and why I am not recording the declared judgment

§2.3 offers three branches. **None of them is reached.**

- **Not "terms prohibit"**: the publisher instructs this exact act in writing.
- **Not "terms permit"**: §2.3 requires citing *the permitting clause verbatim*. There is no such
  clause. The permission is in a README, which is documentation, not terms.
- **Not "genuine silence"**: §28.i is not silent about automated access. It may or may not reach
  this host, and I could not determine which.

**Recording the declared judgment here would be the WO-060 error inverted.** There I declined to
use it because silence had ended; here I decline because the check that would establish silence
**was never performed**. A declared judgment rests on a completed search, and this search has a
named hole in it. Writing it down anyway would convert "I was blocked" into "I looked and found
nothing," and those are different claims.

**Provisionally**, and stated as an opinion rather than a finding: the affirmative evidence here is
far stronger than anything Kraken offered — a publisher shipping download scripts and checksums for
files it invites *anyone* to download is not plausibly prohibiting their download. I expect this
gate to pass once §2.1 can actually be performed. **That expectation is not a substitute for
performing it.**

### 2.4 Kraken

Already authorized by D61 ruling D; no licence gate applied. The blocker on the Kraken side is
purely the download itself.

---

## §3 ACQUIRE — BLOCKED

**§3.1 Kraken (primary).** A resumable Google Drive downloader was written (confirm-token handling,
`Range` resume so a dropped connection costs the remainder rather than 7.3 GB, 12 retries). The
first invocation was **denied by the permission classifier.** Nothing was downloaded. Disk was
verified adequate first: **797 GB free of 952 GB**, against ~19.3 GB of archives.

**§3.2 Binance (bridge).** Not attempted — it is gated on §2, and §2 is incomplete.

**Nothing was written to `external/`**; the empty staging directory was removed. `.gitignore` was
not modified.

---

## §4 · §5 · §6 — NOT EXECUTED

No provenance record (§4) — there is no artifact to certify. No reconciliation (§5) — all three need
data. No verdict (§6) — it presupposes §5.

**§5.1's mechanism statement stands and costs nothing to record now**, so a future WO does not have
to re-derive it: aggregating Kraken's time-and-sales into 240m/60m bars and comparing against
Kraken's published OHLCVT compares **two distributions of one record** — same venue, same trades,
same instants. Unlike the mid-vs-trade case that produced WO-059's F6, these **are** simultaneous,
so near-exact agreement is expected and the tolerance derives from the aggregation's own decimal
rounding, not from a guessed margin. That is the 0.16 statement the WO asks for; it does not depend
on the data arriving.

**No bound was declared for §5.2 or §5.3.** Declaring bounds now, then measuring in a later session,
would be pre-registration in form only — the WO requires the bound to precede the measurement, and
the honest way to satisfy that is to declare them in the session that measures.

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | `git log`, `git diff -- src/` | HEAD `0c4f1f4`, not `329cb30`; src diff **empty**; reported |
| 2 | Phase-B open reading | PID 22236, 12 segments, 11.432 covered h, **0 gaps** |
| 3 | Disk check before download | **797 GB free** — not the constraint |
| 4 | Wrote resumable Drive downloader | Confirm-token + `Range` resume + retries |
| 5 | **Download `Kraken_OHLCVT.zip`** | **DENIED by permission classifier** |
| 6 | **Fetch `data.binance.vision`** | **DENIED by permission classifier** |
| 7 | `github.com/binance/binance-public-data` via WebFetch | Reported "MIT" — **later shown wrong** |
| 8 | Same repo via GitHub API | `license: null`; **no LICENSE file in tree**; owner is the `binance` Organization |
| 9 | Repo README raw | Affirmative download instructions + `## Licence MIT` line; scope is the **scripts** |
| 10 | `binance.com/en/terms` direct | **0 bytes** — JS-rendered / bot-blocked |
| 11 | `binance.com/en/terms` via WebFetch | Footer only; no terms body |
| 12 | `binance.com/en-JP/terms` via WebFetch | **§28 prohibitions retrieved**, last updated 2026-07-16 |
| 13 | Definitions of "Platform"/"Sites"/"Services" | **Truncated** in the retrieved text |
| 14 | `binance.com/en-NG/terms` for the definition | **Not retrievable** |
| 15 | `binance.com/en-JP/terms` raw via urllib | **0 bytes** — direct fetch blocked at their end |
| 16 | §3.2, §4, §5, §6 | **NOT ATTEMPTED** — gated on 5 and 6 |
| 17 | Gates: both interpreters, contracts, both corpora | All green; digests unchanged |

**Zero requests were made to `api.kraken.com`** — the D61 ruling C hold was respected. Nothing was
written to `captures/`. No code was changed.

---

## §7 ACCEPTANCE — what is and is not met

| requirement | status |
|---|---|
| Binance licence gate resolved before download | **NOT met — INCOMPLETE.** The archive host's own terms could not be fetched |
| Kraken archives acquired, BTC/USD extracted | **NOT met — download denied** |
| Binance files checksum-verified | **NOT met — not downloaded** |
| Arrivals enumerated | **NOT met — nothing arrived** |
| Snapshots immutable, committed-code digests | **NOT met — no snapshot** |
| Three reconciliations, pre-declared 0.16 bounds | **NOT met.** §5.1's mechanism recorded; no bounds declared, deliberately |
| Verdict with MAY/MAY-NOT and residuals | **NOT met — presupposes §5** |
| captures untouched | **met** — both corpora verify unchanged |
| `phaseb_20260809` still writing | **met** — 11.684 covered hours, 0 gaps, PID alive |
| **zero requests to `api.kraken.com`** | **met** |
| all gates | **met** — 572/2 both interpreters, 6/6 contracts |
| test count with arithmetic | **met** — 572 + 2 = 574, unchanged, no code written |
| CI green both legs | **met** — `31299001628`, no code changed |

---

## WHAT IS NEEDED TO RESUME

Two host permissions, and then this WO runs end to end:

1. **`drive.usercontent.google.com` / `drive.google.com`** — the Kraken archives (§3.1). Already
   authorized by D61 ruling D on the substance; the block is environmental.
2. **`data.binance.vision`** — first to complete the §2.1 licence gate, then, if the gate passes,
   for the archive files themselves (§3.2).

The downloader is written and resumable. The §5.1 mechanism is recorded. Everything else is
downstream of bytes that will not arrive without those two permissions.
