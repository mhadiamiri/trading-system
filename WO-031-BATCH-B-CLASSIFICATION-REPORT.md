# WO-031 (reissued) — PASS TWO, BATCH B CLASSIFICATION + one BOUND re-audit

**COMPLETE. No STOP.** This report **SUPERSEDES** the earlier WO-031 STOP report (the first issue
halted at §2 because D39's partition amendment and decision docs were ratified but never committed;
WO-032 committed them, so §2's precondition is now satisfied and this run proceeded through §3/§4).
The STOP itself remains on the record in `progress.md`'s **▶ WO-031** block and in WO-032's premise.

**SHIP IMPACT: NO.** Converts nothing, threads no seam, edits no test/src/fixture. Deliverables are
two evidence artifacts, one re-runnable probe under `tools/`, and a `progress.md` block.

| Item | Result |
|---|---|
| §1 HEAD / suite / partition integrity | **PASS** — 222 both interpreters; reverify PASS 30/30 by name; tree clean after the run |
| §2 amended B/C plan on the tree | **PASS** — the WO-031-first STOP is cleared |
| §3 batch-B classification (13 races) | **DONE** — `evidence/WO-031/batch_b_clock_read_classification.md` |
| §4 outcome-bearing aggregate | **DONE** — **N = 10 convertible, M = 3 not-yet**; the EXPECTED fork obtains |
| §3-bis bound re-audit | **DONE** — verdict **(a) a misfiled RACE**; denominator **26 → 27**, escalated |
| §5 scope fence | **HELD** |

---

## §1 — HEAD, SUITE, PARTITION INTEGRITY

**Actual HEAD: `29fb577`** — `WO-032 close: CI GREEN both legs (run 30304749145) + a FINDING for the
lead`. The WO names base `1b52c53`; `e7da7cf` (the §1.3 fix) and `29fb577` (the docs close) landed on
top of it. **Used `29fb577`, as §1 directs.**

| Interpreter | Result |
|---|---|
| 3.14.6 (ambient) | **222 passed** in 246.03 s, 0 f/xf/xp |
| 3.11.15 (strict uv venv) | **222 passed** in 244.84 s, 0 f/xf/xp |

**`tools/wo029_reverify_partition.py` → PASS, 30/30 by name**, exit 0, output written to
`.artifacts/wo029_reverify_partition/<stamp>.txt`. **`git status` after the run: clean** (only the
lead's own `instructions.md` edit) — **the WO-032 §4 fix held**; the instrument no longer dirties
`evidence/`. Under the old line-keyed verdict this same tree returned `25/30 · FAIL`.

**Batch B membership from the committed amended partition — 13 races, confirmed:**
`test_gap_recording.py` (6–11) · `test_keepalive.py` (15–16) · `test_failure_cap.py` (17–19) ·
`test_failure_capture.py` (20–21).

## §2 — THE AMENDED B/C PLAN IS ON THE TREE

Confirmed present in the committed `evidence/WO-029/batch_partition.md`:

- The struck phrase is **gone** — searching the committed file for `terminate via scripted clean-close`
  returns nothing; batch A's entry now records *"All five converted on their OWN termination branch —
  the DEADLINE — asserted, via `AdvancingClock`."*
- The requirement is **added** to B and C: *"each race must KEEP its own production termination branch
  … asserted, not assumed. No scripted-clean-close substitution."*
- A dated `## AMENDMENT — 2026-07-27 (WO-032 §2, implementing D39 item 1)` section is present.

**The WO-031-first STOP is cleared.** Proceeded.

---

## §3/§4 — BATCH-B CLASSIFICATION (full detail in the evidence artifact)

Full per-race work — termination branch, complete read enumeration with call sites and
injectable/non-injectable tags, per-read outcome/incidental classification with the naming evidence,
and per-race verdict — is in **`evidence/WO-031/batch_b_clock_read_classification.md`**. Summary:

| Race | Test | Branch | Verdict |
|---|---|---|---|
| 6 | `test_keepalive_reconnect_gap_recorded` | deadline | **NOT-YET** — `last_frame` |
| 7 | `test_checksum_resync_gap_recorded` | deadline | CONVERTIBLE |
| 8 | `test_breaker_retry_ladder_recorded_on_reconnect_gap` | deadline | CONVERTIBLE |
| 9 | `test_venue_disconnect_gap_recorded` | deadline | CONVERTIBLE *(runs on DEFAULT thresholds)* |
| 10 | `test_overlapping_gaps_union_and_collective_close` | deadline | CONVERTIBLE |
| 11 | `test_ledger_reports_incomplete_gap` | deadline *(load-bearing)* | CONVERTIBLE *(deadline-assertion)* |
| 15 | `test_heartbeat_absence_triggers_reconnect` | deadline | **NOT-YET** — `last_frame` |
| 16 | `test_application_ping_pong_keeps_a_quiet_link_alive` | deadline | **NOT-YET** — `last_ping` + `last_frame` |
| 17 | `test_count_cap_keeps_first_n_counts_all_announces` | deadline | CONVERTIBLE |
| 18 | `test_byte_cap_binds_independently` | deadline | CONVERTIBLE |
| 19 | `test_capped_failures_get_one_line_summaries` | deadline | CONVERTIBLE |
| 20 | `test_checksum_failure_capture_has_every_ruled_field` | deadline | CONVERTIBLE |
| 21 | `test_every_checksum_failure_captured_not_positionally_sampled` | deadline | CONVERTIBLE |

**All 13 terminate on the DEADLINE branch** — so the amended partition's keep-the-branch requirement
points every batch-B conversion at `AdvancingClock`, not at a scripted close.

### §4 counts

**N = 10 CONVERTIBLE now** (7, 8, 9, 10, 11, 17, 18, 19, 20, 21) · **M = 3 NOT-YET-CONVERTIBLE**
(6, 15, 16).

### The outcome-bearing NON-INJECTABLE set — exactly TWO reads

| Read | Threshold field | Convicted by | On which assertion |
|---|---|---|---|
| **`last_frame`** — heartbeat-absence clock (`:2551, :2682, :2715, :2772, :2777`) | `_heartbeat_absence_timeout` | race 6 | `gaps_detected == 1`, `cause == "KEEPALIVE_RECONNECT"`, `reason_code == "HEARTBEAT_ABSENCE"` |
| | | race 15 | `"HEARTBEAT_ABSENCE" in caplog.text`, `connect_count == 2`, `sockets[0].closed is True`, `len(emitted) == 2` |
| | | race 16 | `connect_count == 1`, `"HEARTBEAT_ABSENCE" not in caplog.text` |
| **`last_ping`** — application-ping interval (`:2552, :2683, :2716, :2718, :2773`) | `_app_ping_interval` | race 16 | `len(pings) >= 3` |

**This, and nothing more, is what the keepalive seam WO threads** (D39 seam-sized-to-measurement).

### The incidental-everywhere set — UNTHREADED BY DESIGN, recorded

`_start_time` · ledger `anchor_monotonic` · gap open/close stamps · per-frame instrument stamps ·
`done_mono` receive→process latency · throughput window end · ledger `run_end_monotonic` · the 600 s
duration-breaker streak · pong-observer stamps · app ping/pong observer stamps.

Where a batch-B assertion touches one of these it constrains **sign, ordering, type or key presence**
(`open_monotonic > 0`, `close_monotonic >= open_monotonic`, `close_a == close_b`,
`max(opens) <= close`, `isinstance(monotonic, float)`, `set(summary_keys) == {…}`) — true for any
monotonic source at any rate, so they survive conversion. This is a **ruled asymmetry, not a place
work stopped** (D39 / D37-D38).

**A fact that carries most of the classification:** a fake clock drives only `_monotonic_clock` /
`_wall_clock`; every non-injectable read stays on the **real** clock, and a converted run still
finishes in milliseconds of real time. So a 5 s / 10 s / 600 s threshold is not merely unreached today
— it cannot be reached by changing the injected clock's rate.

### Which fork obtains

**THE EXPECTED ONE.** The outcome-bearing set is two reads, both **keepalive/ping pacing** — precisely
the shape D39 predicted, naming `test_keepalive` in advance. It does **not** touch the
throughput/lag/pong **instruments** and it is not large. **No §4 STOP; Ops may scope the keepalive seam
WO on the existing D39 ruling, sized to exactly these two reads.**

### Fixture needs (3.4)

**None new.** Race 11 is a deadline-assertion race a frozen clock cannot terminate — but
`AdvancingClock` (WO-029 §2.0-bis) is already in the shared harness. Flagged, not built.

---

## §3-bis — THE BOUND RE-AUDIT (full detail in the second evidence artifact)

**`test_incremental_persist_survives_unhandled_exception_mid_capture`**
(`test_ledger_persistence.py:82`), filed by the audit among the **7 legitimate BOUNDS** as
*"dur=0.25, injected crash ends it"*.

**Verdict: (a) — a RACE the audit misfiled as a BOUND. The read is INJECTABLE, so it is
CLOCK-INJECTABLE / CONVERTIBLE. Denominator 26 → 27. ESCALATED, not folded into a batch.**

Classified by the D39 method, **not** from the symptom — §3-bis explicitly forbids reclassifying from
the differential observation, and the D39 doc says the category comes from the classification.

**Which read, pinned rather than guessed.** `AdvancingClock` advances on **monotonic** reads only, and
`_monotonic_clock` is routed to exactly three sites — `:2548` (deadline set), `:2594` (deadline guard),
`:2727` (recv timeout) — all the **deadline** seam. Every other read on the path is raw
`time.monotonic()`/`time.time()`, untouched by the fixture. A divergence under it cannot originate in a
non-injectable read.

**Which assertion observes it.** The test's central one:
`with pytest.raises(RuntimeError, match="injected unhandled crash"):` — it fails with
`Failed: DID NOT RAISE` exactly when the deadline wins, which is the CI symptom seen on run
`30304749145` (3.14, seed `2050525690`).

**The measurement** (`tools/wo031_bound_reaudit_probe.py`), showing the run ending progressively
earlier in the script as the deadline clock advances faster:

| Clock | emitted | frame 2 reached | gap opened | frame 3 reached (crash) |
|---|---|---|---|---|
| real clock | 1 | True | 1 | **True** |
| `AdvancingClock(delta=0.2)` | 0 | False | 0 | **False** |
| `AdvancingClock(delta=0.05)` | 1 | **True** | 1 | **False** |
| `AdvancingClock(delta=0.01)` | 1 | True | 1 | **True** |
| `AdvancingClock(delta=0.0001)` | 1 | True | 1 | **True** |

`delta=0.05` is the decisive row: frame 2 drains and opens the gap, then the deadline arrives and
frame 3 never does. The audit's justification holds only when the loop **wins a race** against the
deadline; it is not a property of the script.

**Consequence:** clock-injectable **26 → 27**, legitimate bounds **7 → 6**, audit total unchanged at 30.
**Escalated.** This WO did not amend `batch_partition.md`, did not assign the test to a batch, and did
not touch it. If ratified, its natural home is batch C (same file as race 12), which would become 9.

### The other 6 bounds — enumerated and scoped, not probed

| # | Bound | Deadline | Work before the terminator | Shares the shape? |
|---|---|---|---|---|
| 31 | `test_backoff_breaker.py:88 test_persistent_reopen_failure_trips_breaker_loud` | 30 s | breaker trip ~0.1 s | No — ~300× margin |
| 32 | `test_gap_recording.py:202 test_terminal_venue_disconnect_breaker_gap_recorded` | 30 s | breaker trip | No — ~300× margin |
| 33 | `test_live_capture.py:172 test_breaker_trip_terminates_run_with_forensic_tail` | 30 s | breaker trip | No — ~300× margin |
| 34 | `test_reconnect_to_effect.py:100 test_stranded_reconnect_flag_fails_loudly` | 30 s | flag raises | No — ~300× margin |
| 35 | **`test_ledger_persistence.py:82`** | **0.25 s** | **3 frames must drain** | **YES — reclassified** |
| 36 | `test_no_silent_fallback.py:25 test_connection_failure_raises_and_does_not_replay` | 5 s | raises during connect | No — before the loop |
| 37 | `test_no_silent_fallback.py:52 test_live_method_refuses_fixture_mode_adapter` | 1 s | refuses pre-loop | No — deadline never consulted |

Entry 35 is the sole outlier: the only bound whose deadline is the **same order of magnitude** as the
work it must cover.

**Honesty about that reasoning:** the margin argument is the *same form* of prose reasoning the audit
used and that this re-audit falsified. What separates the cases is the ratio, not the rhetoric. So
31–34 and 36–37 are recorded as **not-obviously-shaped-like-35**, *not* as proved safe.
**Recommendation:** one follow-on pass with the now-existing probe (it generalises by swapping script
and duration) turns that into a measurement — worth doing **before batch C is planned**, since entry 35
already lives in a batch-C file.

---

## §5 — SCOPE FENCE: HELD

| Fence | Held? |
|---|---|
| Converts NO race | **HELD** |
| Threads NO seam | **HELD** |
| Edits NO test/src/fixture | **HELD** — `git diff -- src/ tests/` empty |
| Scopes NO downstream WO | **HELD** — produced the measurement that sizes it; wrote no seam WO |
| Touches NO batch C race, none of the 3 asyncio.sleep races | **HELD** |
| Does NOT reclassify the bound unilaterally | **HELD** — reported, escalated; no artifact reclassified |

**Five production sha256, unchanged:** `kraken_v2_book.py` `b06c347e` · `factory.py` `103a8ba7` ·
`registry.py` `5bf833c7` · `live_capture.py` `dab18f67` · `logkit/decision.py` `3d153a11`.

---

## §6 — ACCEPTANCE

| Gate | Result |
|---|---|
| `pytest tests/ -p no:randomly -rX` → 222 both interpreters | **PASS** — 222/222 on 3.14.6 and 3.11.15, 0 f/xf/xp |
| `wo029_reverify_partition.py` → PASS 30/30 by name, writes `.artifacts/`, `git status` clean after | **PASS** |
| `git status --porcelain` shows only the artifacts + progress.md + instructions.md | **PASS** — plus this report and the probe tool, both §7/§0.3 deliverables |
| Five `src/` sha256 IDENTICAL; `git diff -- src/` empty | **PASS** |
| `test_evidence_write_boundary.py` PASSES (the probe writes to `.artifacts/`) | **PASS** — 4/4 |
| `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 · `preflight_path_check.py` | **PASS** |
| Both evidence artifacts committed | **PASS** |
| progress.md WO-031 block appended; commit, push, local == remote, CI green both legs (REAL run number) | **see §CI** |

---

## §Attempts — every one, including the failures

1. **Re-read `instructions.md` from disk before acting** — it has been replaced four times this
   session; verified by mtime and sha256 (`4540A0B0…`, 10382 bytes) rather than trusting a prior read.
2. **Launched both suite legs in the background first**, then did the read-only §1/§2 verification
   while they ran (~245 s each).
3. **Confirmed the WO-032 §4 fix mechanically, not by assertion** — ran the reverify tool and checked
   `git status` afterwards, because §1 makes a dirty `evidence/` a STOP condition. Clean.
4. **Read the four batch-B test files and the adapter's full clock-read inventory before classifying.**
   The classification is per-read against the source, not per-test by reputation.
5. **Looked up the adapter's threshold DEFAULTS** (`HEARTBEAT_ABSENCE_TIMEOUT_SECONDS = 10.0`,
   `APP_PING_INTERVAL_SECONDS = 5.0`, `RECONNECT_MAX_FAILURE_SECONDS = 600.0`) rather than assuming
   every race overrides them. **Race 9 turned out to override neither** — it is the only batch-B race
   running on defaults, which had to be checked before its absence/ping reads could be called
   incidental.
6. **First §3-bis probe failed with `TypeError: __init__() got an unexpected keyword argument
   'wall_clock'`.** The adapter takes `monotonic_clock` as a constructor kwarg but the wall is set as
   the `_wall_clock` attribute after construction (batch A's pattern). Fixed; recorded because getting
   this wrong silently produces a *non-coherent* injection that the gate would refuse, which could be
   misread as a finding about the test.
7. **Did not reclassify the bound from the symptom.** The differential observation already existed from
   WO-032; §3-bis and the D39 doc both require the classification to come from enumerating reads and
   naming the assertion. Built the frames-reached measurement so the claim "the divergence flows from
   the deadline read" is *pinned* (three `_monotonic_clock` sites, fixture touches nothing else) rather
   than asserted.
8. **Resisted probing all 7 bounds.** §3-bis says enumerate-then-scope. Entries 31–34/36–37 are
   recorded as *not obviously shaped like 35* with the ratio stated — and explicitly **not** as proved
   safe, because that would repeat the prose-reasoning error being corrected.
9. **The probe was written as a `tools/` script writing to `.artifacts/`** (§0.3), not a scratch file,
   so batch C or the bounds follow-up can re-run it. Verified it passes
   `test_evidence_write_boundary.py`.
10. **`PYTHONUTF8=1` on every invocation** — without it `contract_count_check.py` aborts the session at
    `pytest_sessionstart`. Environmental; CI is Linux/UTF-8.

---

## §CI

- **Commit:** `aef3166`
- **Local == remote:** `aef31668fdfee8ea32ef1c4fe4eed0efefc2c5db` == `origin/master`
- **CI run `30316789147`** — **`test (3.11)` success · `test (3.14)` success**, green both legs on the
  first attempt (both orders, including the randomized leg that surfaced the §3-bis bound).

**THEN STOP.** §4 convicts keepalive-shaped reads → the keepalive seam WO is next, sized to exactly
`last_frame` and `last_ping`. §3-bis's reclassification (26 → 27) escalates before it joins any batch.
