# WORK ORDER — WO-008b-B-RERUN: 60-Minute Live Capture (Throughput Verdict + Discrimination)

**Status:** ACTIVE. Fresh session. **THE MEASUREMENT SPRINT 2 WAS BUILT TO EARN.**
**READ FIRST:** `evidence/WO-014c-1/thresholds_and_branches.txt` — the declared thresholds,
five branches, and full cross-product. **The report interprets against that file and
nothing else.**
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.
**Baseline:** the WO-014c-3 addendum commit — 177 passed both orders, 0 failed / 0 xfailed /
0 xpassed, import-linter 6/6, contract 6/6, ruff clean.
**Standing rules 0.1–0.9 apply in full.**

## THIS RUN HAS THREE JOBS
1. **The throughput verdict** — does the L2 book feed sustain **≥60 MarketStates/min**?
2. **First live confirmation of `ping_timeout=None`** — its behavior under the library's
   real ping loop has never been observed.
3. **First live exercise of the gap ledger and failure-targeted capture** — everything
   about them is fixture-proven only.

## THE OUTCOME IS NOT PREDETERMINED
A run reporting 23/min is a SUCCESSFUL work order. A run reporting 600/min is a
successful work order. A VOID run is a successful work order. **Report what the feed gives.**

**FORBIDDEN:**
- Re-running for a better number. If you run more than once for ANY reason, report EVERY
  run with its result and why the earlier ended.
- Adjusting measurement, window, counting, or thresholds after seeing data.
- Any code change affecting throughput, counting, or instruments once the run begins.
- Extrapolating a partial window into a result.
- **Choosing the definition of "sustained" after seeing the data** — all four are reported.

## §1 — PREFLIGHT GATE — complete and paste ALL of it before any socket opens

### 1.1 Repo state
`git status --porcelain` with every line classified; `git worktree list` showing ONLY main;
package path inside the repo; both preflight guards OK; test-count baseline vs its SHA.
Note: `instructions.md` is now committed with its WO — a modified one means the WO text
changed mid-flight.

### 1.2 Full suite, RANDOMIZED order
State the seed, paste the summary line **with duration**. Required: 0 failed / 0 xfailed /
0 xpassed. Plus `lint-imports` 6/6, `contract_count_check` 6/6, `ruff` clean.

### 1.3 **HOST SUSPEND MUST BE DISABLED** — new, non-negotiable
The WO-014c-3 deterministic suite recorded `24063.39s (6:41:03)` because the machine
suspended mid-run. **A suspend during a live capture drops the WebSocket, registers an
enormous lag reading, and contaminates both the throughput series and the starvation
discrimination — a suspend is indistinguishable from catastrophic starvation.**
- Confirm sleep/hibernate/display-suspend are disabled for the run's duration, and state
  how you verified it.
- If you cannot verify it, **STOP AND REPORT.** Do not run a 60-minute capture on a
  machine that may suspend.

### 1.4 Persistence is configured — the item C guard
- Confirm `_gap_persist_path` IS set, and paste the path.
- Confirm `_persistence_optional` is **NOT** set. A live run with it set would produce
  exactly the unrecorded ledger the guard exists to prevent.
- Confirm the failure-capture path is configured and writable.

### 1.5 Environment
`TRADING_ENV=paper`; `DATA_SOURCE` = the v2 book adapter on **mainnet**; `venue_name` will
record `kraken_mainnet`; **no credentials present anywhere** — Kraken's public feed needs
none, and if any step appears to need one, STOP IMMEDIATELY.

### 1.6 Bite proofs — four artifacts each, `sha256` exact-restore
- order-capable path unreachable under `TRADING_ENV=paper` **and its preservation dual**
  (paper execution must still fill)
- `Settings.validate()` mainnet guard
- staleness guard **and its dual** (a fresh MarketState must still price)
- no-emission-while-unverified **and its dual** (emission resumes once a fresh snapshot
  validates)

**GATE:** state *"PREFLIGHT COMPLETE — proceeding to live connection."* If any item fails,
STOP. Do not connect on a partial preflight.
Evidence → `evidence/WO-008b-B-RERUN/preflight.txt`

## §2 — THE RUN
Kraken public WebSocket **v2**, channel **book**, symbol **BTC/USD**, depth **10**,
`TRADING_ENV=paper`, **60 minutes continuous, single uninterrupted window**. Loop runs
end-to-end: Data → Strategy → Risk → Execution (paper).

### 2.1 Throughput — reported SEPARATELY
- **raw book update messages RECEIVED** at the parse boundary: count + rate
- **MarketStates EMITTED**: count + rate
Raw high + emitted low means our pipeline; both low means the venue. Opposite remedies.

### 2.2 **THE PER-MINUTE SERIES IS THE DELIVERABLE**
All 60 values for MarketStates emitted, not just the aggregate. A feed averaging 70/min via
one burst and 55 quiet minutes is NOT "sustained ≥60."

### 2.3 Discrimination instruments
Pong RTT distribution (per-ping, with `PINGS_ATTEMPTED` / `PINGS_SENT` / `PONGS_RECEIVED` /
`PONGS_ABSENT`), event-loop lag samples with `expected` vs `actual` and gap timestamps,
receive-to-process latency, message-rate record with its silent-seconds accounting — all on
the shared `time.monotonic()` clock.

### 2.4 Feed health
Checksums attempted / passed / failed. Resync events with cause, duration, and **whether
emission RESUMED**. Reconnects with cause. Staleness firings. Paper fills with one cost
breakdown. Sample MarketStates with real bid/ask. `venue_name` as recorded.

Evidence → `evidence/WO-008b-B-RERUN/live_run.txt`, `throughput_series.txt`

## §3 — THE VERDICT — report ALL definitions, do not pick one
- **minimum** per-minute value across 60 minutes
- **median**
- **mean**
- **percentage of minutes at or above 60**

PASS/FAIL under each. If all four clear ≥60, the verdict is unambiguous. **If they
disagree, do NOT declare a verdict** — report the disagreement and stop; which definition
governs is the project lead's ruling, and making it after seeing data is what this
instruction prevents.

If FAIL: venue-constrained (raw low) or pipeline-constrained (raw high, emitted low)?
**Do NOT attempt to fix a failing throughput result here.** No tuning, coalescing, or
batching. Report and STOP.

## §4 — THE DISCRIMINATION — interpret against the declared branches ONLY
Compare against the thresholds in `thresholds_and_branches.txt` — late pong > 250ms; absent
> 5s; elevated lag > 100ms on > 5% of samples; gappy > 10% missed sends. **Do not adjust a
threshold after seeing data.**

Report the cell (pong state × lag state) and the branch it maps to. Reminders:
- **Branch 5 (instruments GAPPY) OVERRIDES all others.** VOID attaches to the QUANTITATIVE
  discrimination; **the gappiness itself is a reported finding**, and if lag gaps coincide
  with message-rate peaks on the shared clock, that correlation is admissible evidence for
  starvation — **a nomination, never a verdict.** *Gappy instruments can nominate a
  hypothesis; only clean instruments can convict one.*
- **Branch 4 requires on-time + normal + NO FAULT.** With `ping_timeout=None` there is no
  1011; a venue-initiated close arrives via the venue-close path. **If a close occurred, it
  is NOT Branch 4 — it is an unexplained fault to report.**
- **`PONGS_ABSENT` is a SIGNAL (Branch 1/3), never gappiness.** Gappiness is failed SENDS only.
- Confirm the message-rate record's completeness at any gap timestamps, so a nomination can
  state whether its own data is trustworthy.

Evidence → `evidence/WO-008b-B-RERUN/discrimination.txt`

## §5 — GAP LEDGER AND FAILURE CAPTURE — first live exercise
- Paste the ledger: every gap with cause, bounds, duration, resumed/terminal, and the
  once-per-run `(wall, monotonic)` anchor. Any `incomplete` gaps → `GAP_LEDGER_INCOMPLETE`?
- **Compare observed reconnects against the ~116/24h expectation** — that figure came from an
  hour with **no working keepalive** and should now drop substantially. **Do not tune toward
  it.** If it does NOT drop, that is the starvation discrimination's moment, not a keepalive
  failure.
- **Every checksum failure captured** — the 3-of-14,251 rate from WO-008b-B is **undiagnosed
  and not presumed benign**. Paste each artifact: raw wire text, both ladders, expected vs
  computed, preceding 20 frames. Was the cap approached? Any one-line summaries?
- **PRE-RULED:** if checksums fail repeatedly, **assume a defect on our side first.** Do NOT
  retry, tune, or adjust validation. Stop, capture, diagnose offline.

## §6 — RETAIN THE FRAMES
Capture the window's **raw wire text** verbatim, redacted mechanically. Retain as an
additional **immutable** ground-truth fixture with its own UTC timestamp and run ID —
**do not overwrite A2's or A3's.** Ground truth accretes.
State the size; if retaining the full window is impractical, retain a labeled representative
subset **plus the complete checksum ledger**, and say exactly what was kept and dropped.
Label with evidentiary bounds (raw wire → witnesses everything downstream, including
rendering).

## §7 — IF THE RUN FAILS OR DISCONNECTS
Report it. Do not silently restart and report only the clean run. Every attempt, its
duration, and why it ended.

## §8 — VERIFY, COMMIT, PUSH
Both suite orders, linter, contract count, ruff. Explain any delta. **Secret scan including
every captured frame and ledger line** — confirm no credential, token, session, or
connection identifier survives. Push, paste local vs remote HEAD.

## §9 — FINAL REPORT — then STOP
1. **Preflight** — all of it, including the randomized run with seed, **suspend disabled and
   how verified**, persistence configured and `_persistence_optional` unset, and all four
   bite-proof pairs. Confirm the gate statement preceded the connection.
2. **Run summary** — start/end UTC, duration, symbol, endpoint, uninterrupted?
3. **THROUGHPUT** — raw and emitted, SEPARATELY. **Paste the full 60-value per-minute series.**
4. **VERDICT under all four definitions.** Do they agree?
5. **If FAIL** — venue or pipeline, with analysis.
6. **DISCRIMINATION** — pong distribution, lag samples with expected/actual, latency. Which
   cell, which branch? Is any instrument gappy? If VOID, state the nomination and whether the
   message record supports it.
7. **`ping_timeout=None`** — how did it behave live? Any close? Any 1011?
8. **Gap ledger** — pasted. Reconnect count vs ~116/24h. Any incomplete gaps?
9. **Failure capture** — every failure's artifact. Cap approached? **Are the failures
   wire-level anomalies or our residual bug?**
10. **Feed health** — checksums attempted/passed/failed, resyncs and whether emission resumed,
    staleness firings, fills with cost breakdown.
11. **Frames retained** — fixture header, size, kept/dropped. A2's and A3's untouched?
12. **Did any credential, token, session, or connection ID appear ANYWHERE** — output, log,
    evidence, ledger, or captured frame? YES/NO.
13. **Was any order placed at any venue?** YES/NO.
14. §8 verification with deltas and HEADs.
15. **Prose standing in for output?** YES/NO.
16. **Changed but not asked?** Every file, or "none."
17. **What could not be completed, and why?**

STOP for human review. The project lead reviews this regardless of outcome.