# WORK ORDER — WO-008b-B-RERUN: 60-Minute Live Capture

**Status:** ACTIVE. Fresh session. **THE FIRST REAL VENUE SOCKET — authorized per-run.**
**READ FIRST:** `evidence/WO-014c-1/thresholds_and_branches.txt` — declared thresholds,
five branches, full cross-product. **The report interprets against that file and nothing
else.**
**Authority:** `.specify/memory/constitution.md`. Conflict → STOP and escalate.
**Baseline:** `6f9a036` — 190 passed both orders, 0 failed / 0 xfailed / 0 xpassed,
import-linter 6/6, contract 6/6, ruff clean.
**Standing rules 0.1–0.9 apply in full.**

## AUTHORIZATION — READ THIS FIRST
The project lead has authorized **ONE 60-minute read-only capture** under the ruled
parameters. **PER-RUN, NOT OPEN-ENDED.** A second attempt after a VOID or a failure is a
new socket under the same terms — no re-ruling needed, but its own preflight and its own
report. Do not silently retry.

**Where the operated things were built** (per the ratified authoring rule): the runner is
`src/trading/loop/live_capture.py` (WO-015, `6f9a036`); instruments are WO-014c-1
(`f74459f`); gap ledger and failure capture are WO-014c-2/3; connection lifecycle is
WO-014b (`8a430bb`). This order BUILDS NOTHING — it operates them.

## THREE JOBS
1. **The throughput verdict** — does the feed sustain **≥60 MarketStates/min**?
2. **First live confirmation of `ping_timeout=None`** — never observed under the library's
   real ping loop.
3. **First live exercise of the gap ledger and failure capture** — fixture-proven only.

## THE OUTCOME IS NOT PREDETERMINED
23/min is a successful work order. 600/min is a successful work order. VOID is a successful
work order. **Report what the feed gives.**

**FORBIDDEN:** re-running for a better number; adjusting measurement, window, counting, or
thresholds after seeing data; any code change to throughput, counting, or instruments once
the run begins; extrapolating a partial window; choosing the definition of "sustained"
after seeing data.

## §1 — PREFLIGHT GATE — paste ALL of it before any socket opens

1. **Repo state:** `git status --porcelain` classified; `git worktree list` main only;
   package path inside repo; both guards OK; baseline vs SHA. `instructions.md` is
   committed with its WO — modified means the WO text changed mid-flight.
2. **Full suite, RANDOMIZED order** — seed stated, summary line with duration, 0 failed /
   0 xfailed / 0 xpassed. Plus `lint-imports` 6/6, contract 6/6, `ruff` clean.
3. **HOST SUSPEND DISABLED** — sleep is set to 24h. Confirm and state how verified.
   Non-negotiable: a suspend mid-capture is indistinguishable from catastrophic starvation.
4. **Persistence:** `_gap_persist_path` SET (paste it); `_persistence_optional` NOT set;
   failure-capture path configured and writable.
5. **`DATA_SOURCE`** names the live-capable v2 book adapter — paste the value. The runner
   now resolves from config; confirm it resolves to the intended venue.
6. **Environment:** `TRADING_ENV=paper`; `venue_name` will record `kraken_mainnet`;
   **no credentials anywhere.** If any step appears to need one, STOP IMMEDIATELY.
7. **Bite proofs, four artifacts each, `sha256`:** order-capable path unreachable under
   paper **+ its dual** (paper execution still fills); `Settings.validate()` mainnet guard;
   staleness guard **+ its dual**; no-emission-while-unverified **+ its dual**.

**GATE:** state *"PREFLIGHT COMPLETE — proceeding to live connection."* If any item fails,
STOP. Do not connect on a partial preflight.
Evidence → `evidence/WO-008b-B-RERUN/preflight.txt`

## §2 — THE RUN
Kraken public WebSocket **v2**, channel **book**, **BTC/USD**, depth **10**,
`TRADING_ENV=paper`, **60 minutes continuous, single uninterrupted window**, full loop
Data → Strategy → Risk → Execution (paper), driven by `LiveCaptureRunner`.

**Throughput, reported SEPARATELY:** raw book messages RECEIVED at the parse boundary
(count + rate); MarketStates EMITTED (count + rate). Raw high + emitted low means our
pipeline; both low means the venue. Opposite remedies.

**THE PER-MINUTE SERIES IS THE DELIVERABLE** — all 60 values, not just an aggregate.

**Also record:** pong RTT per-ping with all four counters; lag samples with expected vs
actual and gap timestamps; receive-to-process latency; message-rate with silent-seconds;
checksums attempted/passed/failed; resyncs with cause, duration, and whether emission
RESUMED; reconnects; staleness firings; paper fills with one cost breakdown; sample
MarketStates with real bid/ask.
Evidence → `evidence/WO-008b-B-RERUN/live_run.txt`, `throughput_series.txt`

## §3 — THE VERDICT — all four definitions, chosen in advance
**minimum**, **median**, **mean**, **% of minutes ≥60**. PASS/FAIL each. If all four clear,
the verdict is unambiguous. **If they disagree, do NOT declare a verdict** — report the
disagreement and stop; that ruling is the project lead's.

If FAIL: venue-constrained or pipeline-constrained, from the two counters. **Do NOT attempt
to fix it here.** No tuning, coalescing, batching. Report and STOP.

## §4 — DISCRIMINATION — against the declared branches ONLY
Thresholds from `thresholds_and_branches.txt`: late pong > 250ms; absent > 5s; elevated lag
> 100ms on > 5% of samples; gappy > 10% missed **sends**. **Do not adjust after seeing data.**

Report the cell (pong × lag) and its branch. Reminders:
- **Branch 5 (GAPPY) overrides.** VOID attaches to the QUANTITATIVE discrimination; the
  gappiness itself is a reported finding, and lag gaps coinciding with message-rate peaks
  is admissible evidence for starvation — **a nomination, never a verdict.** *Gappy
  instruments nominate; only clean instruments convict.*
- **Branch 4 requires on-time + normal + NO FAULT.** With `ping_timeout=None` there is no
  1011; a venue close arrives via the venue-close path. **A close means it is NOT Branch 4
  — it is an unexplained fault to report.**
- **`PONGS_ABSENT` is a SIGNAL (Branch 1/3), never gappiness.** Gappiness is failed SENDS.
- State whether the message-rate record is complete at any gap timestamps, so a nomination
  can say whether its own data is trustworthy.
Evidence → `evidence/WO-008b-B-RERUN/discrimination.txt`

## §5 — GAP LEDGER AND FAILURE CAPTURE — first live exercise
- Paste the ledger: every gap with cause, bounds, duration, resumed/terminal, plus the
  once-per-run `(wall, monotonic)` anchor. Any `GAP_LEDGER_INCOMPLETE`?
- **Any `HOST_SUSPEND` records?** If yes the run is contaminated — report it, do not
  interpret the discrimination.
- **Reconnects vs the ~116/24h expectation** — that came from an hour with no working
  keepalive and should drop substantially. **Do not tune toward it.** If it does not drop,
  that is the starvation discrimination's moment.
- **Every checksum failure captured.** The 3-of-14,251 rate is **undiagnosed and not
  presumed benign**. Paste each artifact: raw wire text, both ladders, expected vs computed,
  preceding 20 frames. Cap approached? Any one-line summaries?
- **PRE-RULED:** repeated checksum failures → **assume a defect on our side first.** Do NOT
  retry, tune, or adjust validation. Stop, capture, diagnose offline.

## §6 — RETAIN THE FRAMES
Raw wire text verbatim, mechanically redacted, retained as an **additional immutable**
ground-truth fixture with its own UTC timestamp and run ID. **Do not overwrite A2's or
A3's** — ground truth accretes. State the size; if the full window is impractical, retain a
labeled subset **plus the complete checksum ledger**, and say exactly what was kept and
dropped. Label with evidentiary bounds.

## §7 — IF THE RUN FAILS OR DISCONNECTS
Report it. Do not silently restart. Every attempt, its duration, why it ended. A retry is a
new socket under the same per-run authorization — new preflight, new report.

## §8 — VERIFY, COMMIT, PUSH
Both suite orders, linter, contract count, ruff. Explain any delta. **Secret scan including
every captured frame and ledger line.** Push, paste local vs remote HEAD.

## §9 — FINAL REPORT — then STOP
1. **Preflight**, all of it — randomized suite with seed, suspend disabled and how verified,
   persistence configured, `DATA_SOURCE` value, four bite-proof pairs, gate statement.
2. **Run summary** — start/end UTC, duration, symbol, endpoint, uninterrupted?
3. **THROUGHPUT** — raw and emitted SEPARATELY. **The full 60-value per-minute series.**
4. **VERDICT under all four definitions.** Do they agree?
5. **If FAIL** — venue or pipeline, with analysis.
6. **DISCRIMINATION** — pong distribution, lag with expected/actual, latency. Which cell,
   which branch? Any instrument gappy? If VOID, the nomination and whether the message
   record supports it.
7. **`ping_timeout=None` live behavior** — any close? Any 1011?
8. **Gap ledger** — pasted. Reconnects vs ~116/24h. Incomplete gaps? **HOST_SUSPEND?**
9. **Failure capture** — every artifact. **Wire-level anomalies or our residual bug?**
10. **Feed health** — checksums, resyncs and resumption, staleness firings, fills with costs.
11. **Frames retained** — fixture header, size, kept/dropped. A2/A3 untouched?
12. **Any credential, token, session, or connection ID anywhere?** YES/NO.
13. **Was any order placed at any venue?** YES/NO.
14. §8 verification with deltas and HEADs.
15. **Prose standing in for output?** YES/NO.
16. **Changed but not asked?** Every file, or "none."
17. **What could not be completed, and why?**

STOP for human review. The project lead reviews this regardless of outcome.


----


§1.3 correction — replace the existing line:

3. **HOST SUSPEND DISABLED.** Standby and hibernate timeouts have been set to 0 (never) on
   BOTH AC and DC. Verify with `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` and
   PASTE THE OUTPUT — both AC and DC power setting indexes must read 0x00000000. Do not
   accept a nonzero timeout on the grounds that it exceeds the run duration; §1.3 requires
   suspend DISABLED, not merely deferred. Confirm the host is on AC power.
   Non-negotiable: a suspend mid-capture is indistinguishable from catastrophic starvation,
   and the runner's HOST_SUSPEND detection only catches divergences beyond ~43s.