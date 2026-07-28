# WO-031 §3/§4 — BATCH B: per-race clock-read classification (the D39 method)

Derived at HEAD `29fb577`. Classification only — **no race converted, no seam threaded.**

Method: `docs/decisions/2026-07-27-a-residual-clock-read-is-classified-not-waived.md` (D39). For each
race: name the termination branch from the code; enumerate every real-clock read on its path; classify
each **OUTCOME-BEARING** (an assertion depends on its value or timing) or **INCIDENTAL** (interval read
against a fixed threshold, feeding no assertion, harmless in a ms-compressed run), **with the naming
evidence**; then a verdict.

---

## The shared read inventory (`get_live_market_data`, `kraken_v2_book.py`)

Every batch-B race runs this one loop, so the inventory is common; what differs per race is which
reads an assertion touches, and which thresholds the test overrides.

### INJECTABLE today (post-WO-023 / WO-030)

| Read | Site | Seam |
|---|---|---|
| `deadline = self._monotonic_clock() + duration_seconds` | `:2548` | `_monotonic_clock` |
| `while self._monotonic_clock() < deadline` | `:2594` | `_monotonic_clock` |
| `remaining = deadline - self._monotonic_clock()` | `:2727` | `_monotonic_clock` |
| `_wall = self._wall_clock or time.time` (suspend detector) | `:2562` | `_wall_clock` |

### NON-INJECTABLE (raw `time.monotonic()` / `time.time()`)

| Read | Site(s) | What it drives | Threshold |
|---|---|---|---|
| `last_frame` | `:2551, :2682, :2715, :2772, :2777` | **heartbeat-absence detection** | `_heartbeat_absence_timeout`, default **10.0 s** |
| `last_ping` | `:2552, :2683, :2716, :2718, :2773` | **application-ping interval** | `_app_ping_interval`, default **5.0 s** |
| `self._start_time = time.time()` | `:2514` | capture start wall stamp | — |
| `anchor_monotonic` | `:2558` | gap-ledger run anchor (atomic wall/mono pair) | — |
| gap `open_monotonic` / close stamps | `:1674, :1710, :1757, :2165` | gap record bounds | — |
| `mono` per-frame instrument stamp | `:2611, :2732` | lag/throughput samples | — |
| `done_mono` | `:2816` | receive→process latency | — |
| `_throughput_record.end_monotonic` | `:2861` | throughput window end | — |
| `_gap_ledger.run_end_monotonic` | `:2869` | ledger run end | — |
| breaker streak | `:2077, :2085` | duration breaker | `_reconnect_max_failure_seconds`, default **600.0 s** |
| pong-observer stamps | `:2243, :2248, :2256` | RTT distribution | — |
| app ping/pong observer stamps | `:2289, :2294, :2322, :2324` | ping bookkeeping | — |

**A fact that decides most of this classification.** `AdvancingClock` (and any future fake) drives only
`_monotonic_clock` / `_wall_clock`. Every read in the second table stays on the **real** clock, and a
converted run still completes in **milliseconds of real time**. So a 5 s / 10 s / 600 s threshold is
not merely unreached today — it cannot be reached by changing the injected clock's rate. That is what
makes these reads incidental rather than merely quiet.

---

## Per-race classification

Legend — **OB** = outcome-bearing, **INC** = incidental. "Branch" is the termination branch a later
conversion must KEEP (D39 item 1, now in the amended partition).

### `test_gap_recording.py` — races 6–11

#### Race 6 · `test_keepalive_reconnect_gap_recorded` (`:80`) — **NOT-YET-CONVERTIBLE**
- **Branch:** DEADLINE. Socket 2 is `on_drain="heartbeat"`, so after the reconnect the run survives to
  its deadline. `duration_seconds=0.25`.
- **Overrides:** `_heartbeat_absence_timeout = 0.05`, `_app_ping_interval = 100.0`.
- **OB · `last_frame` (NON-INJECTABLE)** — the test *is* the absence detector. Naming evidence:
  `assert ledger.gaps_detected == 1`, `assert g.cause == "KEEPALIVE_RECONNECT"`,
  `assert g.reason_code == "HEARTBEAT_ABSENCE"`, `assert g.resumed is True`. No gap exists at all
  unless `time.monotonic() - last_frame > 0.05` fires.
- **OB · deadline (INJECTABLE)** — the post-reconnect emit must land before the run ends.
- **INC** — `last_ping` (100 s, never fires; no assertion references a ping).
  `ledger.run_monotonic_anchor > 0` and `g.open_monotonic > 0` are **sign** assertions;
  `g.close_monotonic >= g.open_monotonic` and `g.duration_s >= 0` are **ordering** assertions — all
  hold for any monotonic source, at any rate. Breaker streak (600 s): no assertion, unreachable.
  Instruments: no assertion.
- **Read(s) to thread:** the `last_frame` absence comparison.

#### Race 7 · `test_checksum_resync_gap_recorded` (`:113`) — **CONVERTIBLE**
- **Branch:** DEADLINE (`on_drain="heartbeat"`, `duration_seconds=0.25`).
- **Overrides:** absence `100.0`, ping `100.0`.
- **OB · deadline (INJECTABLE)** — all three frames must drain. Naming evidence:
  `assert ledger.gaps_detected == 1`, `assert g.resumed is True`, `assert g.close_monotonic is not None`
  (the closing snapshot is frame 3).
- **INC** — absence/ping at 100 s against a 0.25 s window, no assertion. `assert factory.connect_count == 1`
  depends on absence **not** firing, which the 100 s threshold guarantees on the real clock.
  Gap stamps: ordering/sign only. Breaker: unreachable. Instruments: no assertion.
- Converts on the deadline path; the frozen `FakeClock` suffices if the script self-closes, but the
  branch to KEEP is the deadline, so `AdvancingClock` is the correct fixture.

#### Race 8 · `test_breaker_retry_ladder_recorded_on_reconnect_gap` (`:139`) — **CONVERTIBLE**
- **Branch:** DEADLINE (`duration_seconds=0.25`).
- **Overrides:** absence `100.0`, ping `100.0`; `_reconnect_sleep` collapsed, `_reconnect_jitter = 1.0`,
  backoff base `0.01` / cap `0.04`.
- **OB · deadline (INJECTABLE)** — six frames plus two failed reopens plus a successful reconnect must
  complete. Naming evidence: `assert factory.failed_attempts == 2`, `assert g.resumed is True`.
- **INC** — the ladder's `at` timestamp is asserted only for **key presence**
  (`assert {"attempt", "at", "delay_s", "error"} <= set(entry)`); `delay_s` comes from backoff
  arithmetic with jitter pinned to 1.0, not from a clock read. Breaker streak 600 s: the test requires
  the breaker NOT to trip, which is guaranteed by the threshold on the real clock, not by rate.

#### Race 9 · `test_venue_disconnect_gap_recorded` (`:169`) — **CONVERTIBLE**
- **Branch:** DEADLINE (`duration_seconds=0.25`).
- **Overrides: NONE** — this race runs on the **defaults** (absence 10 s, ping 5 s). Recorded
  explicitly because it is the only batch-B race that does.
- **OB · deadline (INJECTABLE)** — the scripted `ConnectionClosedError` drives the reconnect; the
  post-reconnect emit must land before the run ends. Naming evidence: `assert factory.connect_count == 2`,
  `assert g.resumed is True`, `assert g.close_monotonic is not None`.
- **INC** — absence 10 s and ping 5 s stay on the real clock in a ms-scale run, and no assertion
  references either.

#### Race 10 · `test_overlapping_gaps_union_and_collective_close` (`:229`) — **CONVERTIBLE**
- **Branch:** DEADLINE (`duration_seconds=0.25`).
- **Overrides:** absence `100.0`, ping `100.0`.
- **OB · deadline (INJECTABLE)** — three frames plus a reconnect. Naming evidence:
  `assert ledger.gaps_detected == 2`, both `resumed`.
- **INC — but the one place a non-injectable read's VALUE is compared**, so it is named rather than
  waved through: `assert checksum_gap.close_monotonic == venue_gap.close_monotonic` (exact equality —
  satisfied because collective close writes **one** read to both records, a structural property) and
  `assert max(open_monotonic...) <= close` (ordering; WO-022 deliberately loosened `<` to `<=` for
  coarse Windows monotonic resolution). Both hold for any monotonic source at any rate.

#### Race 11 · `test_ledger_reports_incomplete_gap` (`:272`) — **CONVERTIBLE** *(deadline-assertion)*
- **Branch:** DEADLINE — **and load-bearing.** `duration_seconds=0.15`; the socket blocks after the
  corrupted frame, so nothing can close the gap and the run must END with it still open.
- **Overrides:** absence `100.0` (explicitly, so absence does not reconnect and close the gap), ping `100.0`.
- **OB · deadline (INJECTABLE)** — the incompleteness *is* the deadline arriving first. Naming evidence:
  `assert g.resumed is False`, `assert g.close_monotonic is None`, `assert g.complete is False`,
  `assert len(ledger.incomplete) == 1`, `assert "GAP_LEDGER_INCOMPLETE" in caplog.text`.
- **INC** — absence/ping 100 s; gap open stamp sign-only.
- **FIXTURE NOTE (3.4):** like batch A's race 4, a **frozen** clock can never end this run — it needs the
  self-advancing fixture. `AdvancingClock` already exists (WO-029 §2.0-bis, shared harness). **No new
  fixture is needed for batch B.**

### `test_keepalive.py` — races 15–16

#### Race 15 · `test_heartbeat_absence_triggers_reconnect` (`:42`) — **NOT-YET-CONVERTIBLE**
- **Branch:** DEADLINE (socket 2 heartbeats; `duration_seconds=0.25`).
- **Overrides:** `_heartbeat_absence_timeout = 0.05`, `_app_ping_interval = 100.0` ("disable the app
  ping so §1.1 is isolated").
- **OB · `last_frame` (NON-INJECTABLE)** — the absence detector is the subject. Naming evidence:
  `assert "HEARTBEAT_ABSENCE" in caplog.text`, `assert factory.connect_count == 2`,
  `assert factory.sockets[0].closed is True`, `assert len(emitted) == 2`.
- **INC** — `last_ping` (disabled at 100 s); `assert adapter.capture_terminated is None` depends on the
  breaker not tripping (600 s, unreachable).
- **Read(s) to thread:** the `last_frame` absence comparison.

#### Race 16 · `test_application_ping_pong_keeps_a_quiet_link_alive` (`:72`) — **NOT-YET-CONVERTIBLE**
- **Branch:** DEADLINE (`duration_seconds=0.25`).
- **Overrides:** `_app_ping_interval = 0.02`, `_heartbeat_absence_timeout = 0.08`.
- **OB · `last_ping` (NON-INJECTABLE)** — naming evidence: `assert len(pings) >= 3, "the app ping must
  fire on its interval"`. This assertion is a **count of interval firings in a real-time window**: it is
  outcome-bearing on the ping-interval read in the strictest sense.
- **OB · `last_frame` (NON-INJECTABLE)** — naming evidence: `assert factory.connect_count == 1` and
  `assert "HEARTBEAT_ABSENCE" not in caplog.text`. The test's own comment makes the dependence explicit:
  absence at 80 ms is "well inside the 250 ms window, so WITHOUT the pong the link would be declared
  dead; the pong refreshing the absence clock is therefore load-bearing."
- **Read(s) to thread:** `last_ping` **and** `last_frame`.
- This is the collision D39 predicted by name: a race whose SUBJECT is keepalive pacing cannot have
  "feeds no assertion" hold by construction.

### `test_failure_cap.py` — races 17–19 · all **CONVERTIBLE**

All three share `_live_adapter`: absence `100.0`, ping `100.0`, `CHECKSUM_FAILURE_THRESHOLD = 1000`
(so the reconnect/breaker path is deliberately excluded), `duration_seconds=0.25`, one socket of
7 frames, `on_drain="heartbeat"`.

- **Branch:** DEADLINE for all three.
- **OB · deadline (INJECTABLE)** — all 7 frames must drain. Naming evidence:
  race 17 `assert adapter.get_checksum_failure_count() == 6` and `assert positions == [2, 3, 4]`;
  race 18 `assert adapter.get_checksum_failure_count() == 6`;
  race 19 `assert adapter.get_checksum_failure_count() == 6`, `len(summaries) == 4`.
- **INC** — absence/ping at 100 s, no assertion. Race 19 asserts the summary **key set** includes
  `"monotonic"` and `"utc"` (`assert set(s) == {...}`) — key presence, not value. `capture_terminated is
  None` (races 17, 18) depends on the breaker not tripping: threshold raised to 1000 deliberately.

### `test_failure_capture.py` — races 20–21 · both **CONVERTIBLE**

Shared `_live_adapter`: absence `100.0`, ping `100.0`, `duration_seconds=0.2`, `on_drain="heartbeat"`.

- **Branch:** DEADLINE for both.
- **OB · deadline (INJECTABLE)** — every scripted frame must drain. Naming evidence:
  race 20 `assert len(caps) >= 1`; race 21 `assert len(caps) == 3, "every failure captured (not sampled)"`.
- **INC** — absence/ping 100 s. Race 20's `assert isinstance(art["monotonic"], float) and
  art["monotonic"] > 0` is a **type + sign** assertion. Race 20's other assertions are on wire text,
  book ladders, checksums and redaction — not on any clock.

---

## §4 THE AGGREGATE — the measurement that sizes the keepalive seam WO

### Counts

| | Count | Races |
|---|---|---|
| **N — CONVERTIBLE now** (all non-injectable reads incidental) | **10** | 7, 8, 9, 10, 11, 17, 18, 19, 20, 21 |
| **M — NOT-YET-CONVERTIBLE** (an outcome-bearing non-injectable read) | **3** | 6, 15, 16 |
| Total batch B | **13** | |

### The outcome-bearing NON-INJECTABLE set — what the seam WO threads, and NOTHING more

Exactly **two reads**:

| # | Read | Sites | Threshold field | Convicted by | On which assertion |
|---|---|---|---|---|---|
| 1 | **`last_frame` — the heartbeat-absence clock** | `:2551, :2682, :2715, :2772, :2777` (compared against `_heartbeat_absence_timeout`) | `_heartbeat_absence_timeout` | **race 6** | `gaps_detected == 1`, `cause == "KEEPALIVE_RECONNECT"`, `reason_code == "HEARTBEAT_ABSENCE"` |
| | | | | **race 15** | `"HEARTBEAT_ABSENCE" in caplog.text`, `connect_count == 2`, `sockets[0].closed is True`, `len(emitted) == 2` |
| | | | | **race 16** | `connect_count == 1`, `"HEARTBEAT_ABSENCE" not in caplog.text` |
| 2 | **`last_ping` — the application-ping interval** | `:2552, :2683, :2716, :2718, :2773` (compared against `_app_ping_interval`) | `_app_ping_interval` | **race 16** | `len(pings) >= 3` |

### The INCIDENTAL-everywhere set — stays UNTHREADED **by design** (recorded, not omitted)

Per D39's seam-sized-to-measurement constraint, these are a **ruled asymmetry**, not a place work
stopped. No batch-B assertion rests on any of them:

`self._start_time` (`:2514`) · gap-ledger `anchor_monotonic` (`:2558`) · gap open/close stamps
(`:1674, :1710, :1757, :2165`) · per-frame instrument stamps `mono` (`:2611, :2732`) · `done_mono`
receive→process latency (`:2816`) · throughput window end (`:2861`) · ledger `run_end_monotonic`
(`:2869`) · the duration-breaker streak (`:2077, :2085`, 600 s) · pong-observer stamps
(`:2243, :2248, :2256`) · app ping/pong observer stamps (`:2289, :2294, :2322, :2324`).

Where a batch-B assertion touches one of these it constrains **sign, ordering, type or key presence**
(`open_monotonic > 0`, `close_monotonic >= open_monotonic`, `duration_s >= 0`,
`close_a == close_b`, `max(opens) <= close`, `isinstance(monotonic, float)`, `set(summary_keys) == {…}`)
— properties that hold for **any** monotonic source at any rate, and therefore survive conversion.

### Which §4 fork obtains

**THE EXPECTED FORK — not the surprising one.** The outcome-bearing set is **two reads, both
keepalive/ping pacing**: the heartbeat-absence clock and the application-ping interval. It does **not**
touch the throughput / lag / pong **instruments**, and it is not large.

Per §4, Ops may proceed to scope the keepalive clock-seam WO on the existing D39 ruling, sized to
exactly these two reads. **No §4 STOP.**

### Fixture needs (3.4)

**None new.** Race 11 is a deadline-assertion race that a frozen clock cannot terminate, but
`AdvancingClock` (WO-029 §2.0-bis, already in the shared harness) is exactly that fixture. Flagged,
not built.

### A note for whoever converts the 10

All 10 convertible races terminate on the **DEADLINE** branch, and the amended partition requires the
branch be kept and asserted. Their `duration_seconds` (0.15–0.25) must each drain a specific number of
scripted frames, so the `AdvancingClock` delta must be chosen per race with margin — batch A measured
its firing point rather than deriving it on paper (WO-029 §9 attempt 3, an off-by-one on race 1), and
the same discipline applies here.
