# WO-014c-2 — FINAL REPORT (Gap Recording: Schema + Taxonomy + Failure-Targeted Capture)

**Status:** COMPLETE. STOP for review (do NOT proceed to 014c-3 or the re-run).
**Baseline:** `f74459f`. **Final HEAD:** see §7. **Authority:** `.specify/memory/constitution.md`.
**Venue connection:** NO. Simulated transport only.

Commits (in order):
- `12e39f7` — §1 gap schema + cause taxonomy (declarative, standalone).
- `348461b` — Probe 1 + Probe 2 answers (schema refinement: `gap_id`).
- `fb61d2c` — §2 gap recording implementation + bite proofs.
- `e602cb5` — §3 failure-targeted checksum capture + bite proof.
- (this report commit) — §5 final report + progress status refresh.

---

## 1. TAXONOMY — all four causes mapped to emission sites

| Cause (ruled) | Emission site @ current tree | Reason code |
|---|---|---|
| `KEEPALIVE_RECONNECT` | `get_live_market_data` heartbeat-absence branch (`if mono - last_frame >= self._heartbeat_absence_timeout`) | `HEARTBEAT_ABSENCE` |
| `CHECKSUM_RESYNC` | `_enter_resync` (False→True transition, idempotent) | `CHECKSUM_RESYNC` |
| `BREAKER_RETRY_LADDER` | `_attach_ladder_to_open_gaps` → the `retry_ladder` FIELD of the reconnect gap | (rides on the trigger's code) |
| `VENUE_DISCONNECT` | venue-close on recv (4c) + app-ping-send-fail (4b) open the gap; breaker trip (4a) marks it terminal | `VENUE_CONNECTION_CLOSED` / terminal `RECONNECT_CIRCUIT_BREAKER_TRIPPED` |

**Any path fitting none of the four?** NO. Every no-emission window in the live transport was
enumerated (evidence/WO-014c-2/gap_schema.txt §1.1 "Ruled Question A"). `PAUSE_ON_BOOK_UNAVAILABLE`
is FIXTURE-PATH ONLY (`pause()`/`is_paused` are touched only in `get_market_data` and
`_trigger_pause_for_test`, never in the live loop) — not a fifth live cause.
`RECONNECT_FLAG_STRANDED` is a loud integrity guard, not a silent gap. Leading/trailing edges
(connect→first-snapshot; clean close / deadline) are BOUNDARY conditions carried by
`run_start_monotonic`/`run_end_monotonic`, not interior gaps. No STOP-AND-REPORT condition.

**Is `capture_terminated` distinct, or an instance of `BREAKER_RETRY_LADDER`?** DISTINCT — it is
the **terminal instance of `VENUE_DISCONNECT`** with the retry ladder as an *embedded field*, NOT
an instance of `BREAKER_RETRY_LADDER`. The ladder is the mechanism that RAN; `capture_terminated`
is the conclusion "venue gone," reached ONLY when the ladder EXHAUSTS T=600s. A ladder that
succeeds resumes emission and terminates nothing — **only ladder exhaustion is terminal, not
ladder existence.** (Approved by the lead in the instructions.md UPDATE block.)

## 2. SCHEMA (see evidence/WO-014c-2/gap_schema.txt for the full declaration)

`GapRecord`: `gap_id` (per-occurrence identity, probe 1), `cause`, `reason_code`,
`open_monotonic`, `close_monotonic` (None ⇒ +∞), `resumed`, `terminal`, `last_validated_book`,
`retry_ladder`, `detail`, `open_server_ts` (corroboration only); `duration_s`/`complete`
properties. `GapLedger`: `run_wall_anchor` + `run_monotonic_anchor` (the ONCE-per-run pair),
`run_start_monotonic`/`run_end_monotonic`, `gaps`, `frames_captured`, `evidentiary_bounds`;
`gaps_detected`/`incomplete` properties.

**Monotonic clock + once-per-run wall anchor — CONFIRMED.** Every gap bound is `time.monotonic()`
(WO-014c-1 §A.2 shared clock, same as lag/pong/throughput). The ledger carries exactly ONE
`(wall, monotonic)` pair, captured ATOMICALLY (two adjacent reads, no `await` between — cooperative
scheduling cannot interleave). Calendar location: `wall(t) = run_wall_anchor + (t −
run_monotonic_anchor)`. No gap record ever holds two clock bases.

**Interval-intersection query support.** One clock ⇒ query interval and gaps compare directly.
`intersects([t0,t1]) == any g: t0 < (g.close_monotonic or +∞) and g.open_monotonic < t1` — a UNION
(disjunction), total and cheap (O(#gaps), records appended in open order so already sorted),
overlap-safe (proven in `test_overlapping_gaps`). `None`-close = +∞ makes default-deny STRUCTURAL:
an unclosed gap intersects every later query, so "opened but never closed" is loud by construction.
Reader also needs the completeness accounting (below) so a "no gap" answer is only trusted against
a known-complete ledger. **The reader is OUT OF SCOPE and NOT built.**

## 3. GAP RECORDING — bite proof per cause (4 artifacts each, real trigger)

evidence/WO-014c-2/gap_recording_bite_{keepalive,checksum,breaker_retry_ladder,venue_disconnect}.txt.
Each drives the REAL production trigger through `get_live_market_data` (0.1h) and ends in the
observable effect — a `GapRecord` written with its fields (0.1i).

| Cause | A1 PASS | A2 ACTUAL FAIL (recorder weakened) | A3 PASS | A4 sha256 |
|---|---|---|---|---|
| keepalive | ✓ | `"exactly one keepalive gap; got 0"` | ✓ | exact |
| checksum | ✓ | `assert 0 == 1` (gaps_detected) | ✓ | exact |
| breaker_retry_ladder | ✓ | `"the retry ladder records each failed reopen; got []"` | ✓ | exact |
| venue_disconnect | ✓ | `assert 0 == 1` (gaps_detected) | ✓ | exact |

Each weakening reintroduces the exact defect the WO prevents — a silent unrecorded gap — and
produces a REAL failure with real assertion text. sha256(before)==sha256(after) for every cause.

## 4. LEDGER COMPLETENESS — can it report a gap whose record could not be completed?

YES. A gap DETECTED (opened) but neither closed (emission resumed) nor terminal (breaker trip)
is `incomplete`: retained as open-ended (close=None ⇒ +∞ ⇒ default-deny from open onward) and
reported LOUDLY at capture end as `GAP_LEDGER_INCOMPLETE`, never dropped
(`test_ledger_reports_incomplete_gap`). A terminal breaker gap is COMPLETE (a known open-ended
gap), NOT an integrity deficit (`test_terminal_venue_disconnect_breaker_gap_recorded`).
`GapLedger.gaps_detected` (= len(gaps)) and `.incomplete` make the ledger self-reporting, in the
WO-014c-1 instrument style.

## 5. FAILURE CAPTURE — a synthetic artifact with every field; what N and why

Full artifact pasted in evidence/WO-014c-2/failure_capture_bite.txt. Fields (populated):
`sequence_position_in_run`, `utc`, `monotonic`, `symbol`, `message_type`, `expected_checksum`
(Kraken's) and `computed_checksum` (ours, differ), `failing_frame_raw_text` (VERBATIM wire text,
with `"connection_id": "<REDACTED>"` — mechanical redaction bit), `preceding_frames_n=20` +
`preceding_frames_raw_text`, `local_book_bids`/`local_book_asks` (both ladders at depth 10).
Captured on EVERY failure (`test_every_checksum_failure_captured_not_positionally_sampled`: 3
failures → 3 captures), NEVER positionally sampled.

**N = 20, justified:** the checksum validates on EVERY update and the streak resets on every good
checksum, so the book was checksum-GOOD immediately before the failing frame — the **failing frame
is the prime suspect**, and it + the last-good book (both captured in full) localize the fault.
The book truncates to depth 10, so no latent error hides in a never-checksummed deep level. The
preceding 20 frames are CORROBORATING run-up: at the WO-008b-B anchor ~26 msg/s (~38 ms/frame),
20 frames ≈ 0.76 s — generous over the handful of recent updates touching the top-of-book, while
BOUNDED so retention stays small. Declared engineering judgment (Kraken publishes nothing; 0.1e),
instance-overridable, revisable once the live re-run shows real failure clustering.

## 6. REASON CODES declared in the same commit?

YES. `GAP_LEDGER_INCOMPLETE` was added to `VALID_REASON_CODES["DATA"]` in the SAME commit as its
emission (`fb61d2c`, §2). Prefix-free (`GAP_` stem unique) and producible (emitted as a
`"GAP_LEDGER_INCOMPLETE:"` string) — the vocabulary-completeness guard stays green (8/8). All four
cause reason codes reuse EXISTING declared codes. §3 added no reason code (capture is not a logged
decision code).

## 7. VERIFICATION

| Run | Command | Result | Duration |
|---|---|---|---|
| Deterministic | `pytest tests/ -p no:randomly -rX` | 167 passed, 0 failed/xfailed/xpassed | 242.67s |
| Randomized | `pytest tests/ --randomly-seed=20260725 -rX` | 167 passed, 0 failed/xfailed/xpassed | 242.38s |

**DELTA vs `f74459f` (158 → 167):** +9 tests, all NEW — `test_gap_recording.py` (7) +
`test_failure_capture.py` (2). No existing test changed count, state, or outcome; no xfail/xpass
introduced or cleared.

import-linter **6 kept / 0 broken**; `tools/contract_count_check.py` **6/6**; `ruff check .` clean.

**HEADs:** local == remote == `e602cb5` before this report; after the report commit, pasted at push.

## 8. Venue connection? **NO.** HTTPS doc fetch? **NO** (this WO reused already-cited
WO-014c-1/§1.3 documentation; the one library-behavior claim — `time.monotonic` — cites the Python
docs URL at the point of claim, no fetch needed).

## 9. Prose standing in for output? **NO.** Every claim is backed by executed evidence
(redirected bite-proof files, pasted test summaries with durations, the dumped artifact).

## 10. Changed but not asked?

- `instructions.md` — the lead's `UPDATE:` block committed with its WO (the committed-with-its-WO
  convention the UPDATE itself ratified). Disclosed.
- `progress.md` — a MINIMAL status-header refresh (the authoritative block was stale at `9fbc522`)
  pointing to this WO's completion. Historical body untouched. Disclosed here.
- No other unrequested change. `src/trading/logkit/redaction.py` was READ and imported, not modified.

## 11. What could not be completed, and why?

Nothing in WO-014c-2 was left incomplete. Explicitly OUT OF SCOPE and NOT done (by ruling): the
corpus READER and its default-deny acknowledgment API (the corpus WO — §1.3 specifies its contract
only); stub-lint and the widened-precondition sweep (014c-3); the 60-minute live re-run. Honest
fixture limits (stated at each site): the close/reopen, backoff, breaker trip, venue closes, and
the raw wire text / run position exist under SIMULATED transport — only the isolated live re-run
confirms Kraken's real reopen/close behavior and the residual checksum-failure nature.

**STOP for review.**
