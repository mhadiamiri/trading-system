# WO-008b-B-RERUN — FINAL REPORT — 60-Minute Live Kraken v2 Book Capture

**The first real venue socket.** Single uninterrupted 60-minute read-only capture of Kraken's
public WebSocket v2 `book` channel, BTC/USD, depth 10, `TRADING_ENV=paper`. Interpreted against
`evidence/WO-014c-1/thresholds_and_branches.txt` and nothing else. Authority: the constitution.

**Headline:** Throughput verdict = **PASS, unanimous under all four definitions** (feed sustains
~1,843 MarketStates/min, ≫ 60). Discrimination = **Branch 1 (protocol/venue); starvation
FALSIFIED**, on **clean (non-gappy) instruments that convict**. Two unexpected venue closes and
**234 checksum failures (0.198%, ~10× the prior baseline)** are reported faults — the checksum
failures are **NOT presumed benign**; per the §5 pre-ruling they are assumed our defect first and
flagged for **offline** diagnosis (captured, not tuned).

> **ATTEMPTS (§7 — every attempt reported; no silent retry).**
> - **Attempt 1 — FAILED at ~38 min (operational, not venue).** 17:13:23Z→~15:51 local, killed at
>   elapsed 2281s with no `[run] END`/exception. Cause: the `LiveTradingLoop` prints 2 verbose
>   lines/update; stdout reached 6.6 MB and the harness background task was killed for output
>   volume. The feed was healthy throughout (78,726 emitted in 38 min, 0 terminal gaps, 0
>   HOST_SUSPEND). Its in-memory lag/pong records were lost (extraction never ran); the gap ledger
>   persisted. Preserved: `gap_ledger.attempt1.jsonl`, `attempt1_forensics.txt`. **Not restarted
>   silently** — reported here.
> - **Attempt 2 — COMPLETE (this report).** Hardened driver: loop stdout swallowed, full-instrument
>   checkpoint every 120 s, separate `gap_ledger.attempt2.jsonl`. Ran the full uninterrupted hour.
>   A retry is a new socket under the same per-run authorization; it received its own preflight
>   re-confirmation (clean tree, suspend AC=DC=0x0, on AC).

---

## 1. Preflight (full detail: `evidence/WO-008b-B-RERUN/preflight.txt`, `bite_proofs.txt`)

- **§1.1 Repo state:** clean tree (a working-tree edit to `instructions.md` that folded the
  committed §1.3 correction into the body verbatim was **reverted** to a clean tree, at the
  operator's choice). HEAD `5911eb0` (== remote); baseline `6f9a036` is an ancestor; worktree
  main-only; `trading` package resolves inside the repo; both conftest session guards OK.
- **§1.2 Suite, both orders, seed stated:** **190 passed** deterministic (`-p no:randomly`) **and**
  randomized (`--randomly-seed=20260725`), 0 failed / 0 xfailed / 0 xpassed, ~4:06 each. `lint-imports`
  **6 kept / 0 broken**; `contract_count_check` **6/6**; `ruff` clean.
- **§1.3 Host suspend DISABLED (how verified):** `powercfg /query SCHEME_CURRENT SUB_SLEEP
  STANDBYIDLE` → **AC 0x00000000, DC 0x00000000**; hibernate idle **AC/DC 0x00000000**; PowerLine
  **Online**. Disabled, not merely deferred. (Confirmed by the run itself: **0 HOST_SUSPEND records**.)
- **§1.4 Persistence configured:** `_gap_persist_path = evidence/WO-008b-B-RERUN/gap_ledger.attempt2.jsonl`
  (append-only, redacted, fsync at gap-open; the same stream carries failure summaries + the run
  anchor). `_persistence_optional` = **False**. Runner refuses an unset path (`GAP_PERSIST_UNCONFIGURED`,
  verified). Writable: yes.
- **§1.5 DATA_SOURCE value:** `kraken_v2` — the only live-capable adapter (`is_live_capable` True;
  `kraken_public`/`simulated` refused via `LIVE_CAPTURE_UNSUPPORTED`, verified with no socket).
- **§1.6 Environment:** `TRADING_ENV=paper`; `venue_name=kraken_mainnet`; **no credentials anywhere**
  (`.env` holds only `DATA_SOURCE`/`TRADING_ENV`; credential-name scan = none).
- **§1.7 Four bite-proof pairs (four artifacts each, sha256):** all **OK** — A1 PASS / A2 real-FAIL
  when the guard is weakened / A3 PASS restored / A4 sha256 byte-identical (git-`checkout` restore;
  `core.autocrlf=true`, so `git diff`==empty is the authoritative restore check). Subjects:
  (1) order-capable path unreachable under paper (+dual: paper fills); (2) `Settings.validate()`
  mainnet guard; (3) staleness guard (+dual: fresh accepted); (4) no-emission-while-unverified
  (+dual: resumes on fresh snapshot). Tree clean after.
- **GATE:** *PREFLIGHT COMPLETE — proceeding to live connection* (issued; operator gave explicit go
  before the socket opened).

## 2. Run summary

| | |
|---|---|
| Start / End (UTC) | **2026-07-21 17:09:43Z → 18:09:58Z** |
| Duration | **3614.6 s (≈ 60.24 min)** — single uninterrupted window |
| Symbol / endpoint | BTC/USD — Kraken public WebSocket **v2**, channel `book`, depth 10 |
| Env / venue | `TRADING_ENV=paper` / `venue_name=kraken_mainnet` |
| Uninterrupted? | **YES** (`uninterrupted=True`, breaker `terminated=None`, 0 HOST_SUSPEND) |
| Run anchor | wall `2026-07-21T17:09:44.971957Z`, monotonic `336912.6055432` |

## 3. Throughput (raw and emitted reported SEPARATELY; full per-minute series)

- **RAW book messages RECEIVED** (parse boundary): **118,043** → **1,959.4 / min** aggregate.
- **MarketStates EMITTED** (yield boundary): **111,010** → **1,842.7 / min** aggregate.
- Both counters are HIGH (≫ 60): the venue supplies data **and** the pipeline emits it. The
  raw−emitted difference (~7,000) is frames arriving during the 97 gaps, where an unverified book
  correctly emits nothing (FR-018a(d)) — not a pipeline throughput loss.

**Full EMITTED per-minute series** (61 buckets; minute 60 is a **14.6 s partial tail bucket**):
```
m0..m9 :  995 2397 1237 1173  861 1025 1103 1270 1453 2338
m10..19: 1484 1327 1864  811 1537  903 2161 1952 1114  714
m20..29:  980  824 1111 1303  926 1260 1982 2015  859 1284
m30..39: 1494 1487 1494 2355 1220 1531 1546 4538 3185 1194
m40..49: 2111 3001 3737 2351 2232 2258 2452 1457 1904 1647
m50..59: 3188 3059 2597 3138 2881 3050 2673 2396 2707 1799
m60    :   65   (partial 14.6 s tail — NOT a full minute; shown for completeness, not extrapolated)
```
(Raw per-minute series in `evidence/WO-008b-B-RERUN/throughput_series.txt` / `analysis.txt`.)

## 4. Verdict — all four definitions (chosen in advance)

| Definition | Value | Threshold ≥60 | PASS |
|---|---|---|---|
| **minimum** | 714 (of the 60 complete minutes; 65 if the 14.6 s partial tail is counted) | ≥60 | **PASS** |
| **median** | 1537 | ≥60 | **PASS** |
| **mean** | 1819.8 (≈1849 over the 60 complete minutes) | ≥60 | **PASS** |
| **% of minutes ≥60** | **100%** | — | **PASS** |

**All four agree → the verdict is UNAMBIGUOUS: PASS.** The feed sustains ≥60 MarketStates/min with
enormous margin (worst complete minute 714; typical ~1,500–3,000). This is a successful work order.

## 5. If FAIL — N/A

Throughput did not fail. (Were it to fail, the two counters would localize it: raw-high+emitted-low
⇒ pipeline; both-low ⇒ venue. Here both are high.) **No tuning/coalescing/batching was applied.**

## 6. Discrimination — against the declared branches ONLY (full: `discrimination.txt`)

- **Instruments CLEAN (not gappy):** lag missed-fraction **8.16%** (<10%), pong missed-send-fraction
  **2.53%** (<10%). **NOT a Branch-5 VOID** — the instruments **convict**, not merely nominate. (The
  8.16% missed lag samples are attributable to the 218.8 s of gaps, not to starvation-induced sampler
  death; during connected time the loop sampled continuously.)
- **PONG (four counters):** attempted 3557 / sent 3467 / received 3466 / **absent 6**. RTT median
  **150 ms**, p95 **381 ms**, max **1020 ms**; **late (>250 ms) = 938 (27.1%)**. → not clean on-time.
- **LAG:** 33,062 samples, median **8.97 ms**, elevated (>100 ms) = 12 (**0.04%**) → **NORMAL**.
- **Receive→process latency:** median **0.089 ms**, p95 0.179 ms, max 3.45 ms → loop **not starved**.
- **CELL (pong × lag) = (LATE/ABSENT, NORMAL) → BRANCH 1: protocol/venue.** A healthy loop did not
  cause the late/absent pongs (one-way causal logic), so the delay is **not ours**. **Starvation is
  FALSIFIED; the original 1011 (protocol/venue) hypothesis SURVIVES.** The message-rate record is
  complete except 60 silent seconds (coinciding with gaps), so this reading rests on trustworthy data.

## 7. `ping_timeout=None` live behavior — any close? any 1011?

- **Any 1011?** **NO.** With `ping_timeout=None` the library's ping-timeout 1011 path is disabled, as
  designed — and none was observed.
- **Any close?** **YES — 2 venue-initiated closes** (`VENUE_DISCONNECT` / `VENUE_CONNECTION_CLOSED`,
  "venue closed the connection unexpectedly — no close frame"): at **17:11:28Z** (recovered 4.67 s)
  and **17:55:32Z** (recovered 4.49 s), both with emission **RESUMED**. Per the thresholds file these
  closes arrived via the venue-close path and are **faults ⇒ this is NOT Branch 4** — consistent with
  the Branch-1 reading, reported as faults, not a clean falsification.

## 8. Gap ledger (full: `gap_ledger.attempt2.jsonl`)

- **97 gaps, ALL resolved & resumed, 0 terminal** (no breaker trip). Causes: **95 CHECKSUM_RESYNC +
  2 VENUE_DISCONNECT**. Once-per-run anchor present. **`GAP_LEDGER_INCOMPLETE`: none.**
- **HOST_SUSPEND records: 0** → the run is **not** contaminated; the discrimination stands.
- Resync durations: n=95, min 0.179 s, median 0.625 s, **max 17.398 s** (one long resync; emission
  paused then RESUMED). Total gap time 218.8 s (~3.6 min of 60).
- **Reconnects vs the ~116/24h expectation:** **2 reconnects this hour** (both venue-initiated). That
  ~116/24h figure came from an hour with no working keepalive (recurring 1011s); this run had a
  working keepalive, **no 1011s**, and ~2/hr → a **substantial drop** (comparison only — not tuned
  toward). Reconnect ladder empty ⇒ each recovered on the first attempt.

## 9. Failure capture — every artifact; wire anomaly or our residual bug?

- **234 checksum failures** (0.198% of raw). **200 full captures kept** + **34 one-line summaries**
  (cap bound at 200 by count, WO-014c-3 §0.2) ⇒ the checksum ledger is **complete** (all 234
  accounted for; count never truncated). Each full capture: verbatim failing frame, 20 preceding
  frames, expected vs computed checksum, local book ladders, UTC+monotonic+sequence position
  (`instruments_dump.json → checksum_failure_captures`).
- **Wire anomaly or our bug?** **Not yet decided — and per the §5 PRE-RULING, assume our defect
  first; do NOT tune/adjust validation; diagnose OFFLINE.** A concrete lead: sampled failing frames
  carry **multiple bid levels at the identical price in one update** (e.g. 4× `66452.7` with
  different qty), suggesting an apply-order / same-price-coalescing issue in our book+checksum path.
  This is **captured, not fixed**. The 0.198% rate is **~10× the WO-008b-B baseline (3/14,251 =
  0.02%)** and is **not presumed benign**.

## 10. Feed health

- **Checksums:** attempted on every update; 234 failed (0.198%), each resync resolved and emission
  resumed. **Resyncs:** 95, all resumed (median 0.625 s, max 17.4 s). **Staleness firings: 0** (no
  order was placed, so `place_order`'s staleness guard was never invoked). **Fills:** **0** — the
  trivial-momentum strategy produced no signal all hour (`STRAT_NO_SIGNAL` ×111,010; trades 0; PnL
  0.0). A truthful null, not an omission — hence no cost breakdown to report.

## 11. Frames retained (full: `frames_retained.txt`)

- **Run ID** `WO-008b-B-RERUN-20260721T170944Z`. Kept: **200 failure captures** (verbatim wire +20
  preceding, redacted) **+ 34 summaries + complete gap ledger + full instrument records**
  (`instruments_dump.json`, **7.57 MB**). Dropped: the full ~118k-frame stream (instruments don't
  buffer it; a full sink would be a forbidden mid-run instrument change / a build). Failure-targeted
  subset, bounds 17:09:44Z–18:09:58Z. **A2/A3 fixtures NOT overwritten** (git clean) — ground truth
  accretes as a new artifact.

## 12. Any credential, token, session, or connection ID anywhere? **NO.**

`.env` holds only `DATA_SOURCE`/`TRADING_ENV`. Secret-pattern scan of `instruments_dump.json` (every
captured frame) and the gap ledger: **0 hits**. Persisted text passes `redact()`.

## 13. Was any order placed at any venue? **NO.**

Paper mode; the order-capable path is bite-proved unreachable under paper (§1.7). 0 orders, 0 fills.

## 14. §8 verification (deltas + HEADs)

- Post-run re-verify (`post_run_verify.txt`): **190 passed** deterministic **and** randomized
  (seed 20260725), 0 failed/xfailed/xpassed; `lint-imports` **6 kept / 0 broken**; contract **6/6**;
  `ruff` clean. **No delta** from §1.2 (the tree is byte-unchanged; only new evidence files added).
- **Secret scan** (§8, every captured frame + ledger line): **0 hits** — no credential/token/session/
  connection ID.
- **Commit + push:** this report + `evidence/WO-008b-B-RERUN/*` + `progress.md` committed to `master`
  and pushed; **local HEAD == remote HEAD** (SHA reported in the session hand-off).

## 15. Prose standing in for output? **NO.**

Every claim traces to a persisted artifact: `preflight.txt`, `bite_proofs.txt`, `suite_*.txt`,
`throughput_series.txt`, `analysis.txt`, `discrimination.txt`, `live_run.txt`, `frames_retained.txt`,
`gap_ledger.attempt2.jsonl`, `instruments_dump.json`, `attempt2_progress.log`.

## 16. Changed but not asked? 

**No source/test/config change.** The WO builds nothing; the git tree is clean for `src/`, `config/`,
`tests/`, `tools/`, `pyproject.toml`. Only **new evidence files** and this report were added. The run
also wrote `data/market_events_20260721.parquet` (220 MB, gitignored data path) as a normal loop
side-effect. My run drivers live in the session scratchpad (not committed).

## 17. What could not be completed, and why?

- **Attempt 1 lost (operational)** — recovered by the hardened attempt 2; both reported (§7).
- **Checksum-failure root cause NOT diagnosed here** — correctly deferred to OFFLINE diagnosis per
  the §5 pre-ruling (do not tune during the run). Captured in full for that work.
- Everything the WO asked to *measure* was measured; nothing else is outstanding.

---

**STOP for human review.** The project lead reviews this regardless of outcome. Two items warrant the
lead's attention: (a) the **234 checksum failures (0.198%, ~10× baseline)** — assume-our-defect-first,
diagnose offline; (b) the discrimination result **Branch 1 (protocol/venue), starvation falsified**,
with 2 venue closes and no 1011 under `ping_timeout=None`.
