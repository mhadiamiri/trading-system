# WO-029 — PASS TWO: the 26-race A/B/C partition (§2.0), re-derived at HEAD `9c084c3`

Mechanically re-derived from `evidence/WO-023/wall_clock_race_audit.txt` (the 30 STRUCTURAL RACES),
each matched file+line **at this HEAD** (not prior line numbers — WO-030 moved production lines).

**Totals:** 30 audit races = **26 CLOCK-INJECTABLE** + **3 ASYNCIO-SLEEP** (excluded, D35) +
**1 ALREADY-CONVERTED** (foundation). Confirmed = 26. Race #5 is CLOCK-INJECTABLE (WO-030 seam;
verified runner+factory+builder accept `monotonic_clock`/`wall_clock`). Race #5 is the **only**
FACTORY-BUILT race; all other 25 are DIRECT.

## The full 30 at HEAD

> **⚠ IDENTIFIERS SUPERSEDED (WO-035 §2.2, D42).** The `file:line` + prose-name columns below are the
> ORIGINAL derivation and are **retained as the historical record, not deleted**. They are **no longer
> canonical**: line numbers drift with every batch's conversion, and the prose names were found to be
> **truncated in 9 of 37 entries** (WO-034 §2). The canonical identifiers are the pytest NODE IDs in
> **`evidence/WO-034/audit_node_ids.md`**, obtained from pytest's own collection. The node-ID column
> below is restated from that artifact; read it, not the prose.

| # | NODE ID (canonical, D42) | file:line + prose name (superseded, historical) | category | path |
|---|---|---|---|---|
Node IDs below omit the common `tests/integration/` prefix. Prose names in the third column are the
audit's ORIGINAL text; **bold** marks the 9 the regeneration found truncated (WO-034 §2).

| # | NODE ID (canonical, D42) | file:line + prose name (superseded, historical) | category | path |
|---|---|---|---|---|
| 1 | `test_live_capture.py::test_runner_drives_instrumented_transport_end_to_end` | :59 test_runner_drives_instrumented_transport_end_to_end | CLOCK-INJECTABLE | DIRECT |
| 2 | `test_live_capture.py::test_runner_persistence_is_not_optional_on_the_adapter` | :98 test_runner_persistence_is_not_optional_on_the_adapter | CLOCK-INJECTABLE | DIRECT |
| 3 | `test_live_capture.py::test_short_bounded_run_completes_with_readable_artifacts` | :114 test_short_bounded_run_completes_with_readable_artifacts | CLOCK-INJECTABLE | DIRECT |
| 4 | `test_live_capture.py::test_clean_deadline_close_does_not_reconnect_dual` | :140 test_clean_deadline_close_does_not_reconnect_dual | CLOCK-INJECTABLE | DIRECT (deadline-assertion — needs AdvancingClock, §2.0-bis) |
| 5 | `test_live_capture.py::test_runner_resolves_live_adapter_from_data_source_via_factory` | :197 **test_runner_resolves_live_adapter_from_data_source** (truncated) | CLOCK-INJECTABLE | **FACTORY-BUILT** |
| 6 | `test_gap_recording.py::test_keepalive_reconnect_gap_recorded` | :80 test_keepalive_reconnect_gap_recorded | CLOCK-INJECTABLE | DIRECT |
| 7 | `test_gap_recording.py::test_checksum_resync_gap_recorded` | :115 test_checksum_resync_gap_recorded | CLOCK-INJECTABLE | DIRECT |
| 8 | `test_gap_recording.py::test_breaker_retry_ladder_recorded_on_reconnect_gap` | :143 test_breaker_retry_ladder_recorded_on_reconnect_gap | CLOCK-INJECTABLE | DIRECT |
| 9 | `test_gap_recording.py::test_venue_disconnect_gap_recorded` | :175 test_venue_disconnect_gap_recorded | CLOCK-INJECTABLE | DIRECT |
| 10 | `test_gap_recording.py::test_overlapping_gaps_union_and_collective_close` | :237 test_overlapping_gaps_union_and_collective_close | CLOCK-INJECTABLE | DIRECT |
| 11 | `test_gap_recording.py::test_ledger_reports_incomplete_gap` | :281 test_ledger_reports_incomplete_gap | CLOCK-INJECTABLE | DIRECT |
| 12 | `test_ledger_persistence.py::test_gap_ledger_persisted_readable_from_disk` | :47 test_gap_ledger_persisted_readable_from_disk | CLOCK-INJECTABLE | DIRECT |
| 13 | `test_host_suspend.py::test_host_suspend_recorded_diagnostic_not_terminal` | :46 test_host_suspend_recorded_diagnostic_not_terminal | **ALREADY-CONVERTED** (foundation, WO-023 §6) | DIRECT |
| 14 | `test_host_suspend.py::test_no_host_suspend_under_normal_timing` | :83 test_no_host_suspend_under_normal_timing | CLOCK-INJECTABLE | DIRECT |
| 15 | `test_keepalive.py::test_heartbeat_absence_triggers_reconnect` | :42 test_heartbeat_absence_triggers_reconnect | CLOCK-INJECTABLE | DIRECT |
| 16 | `test_keepalive.py::test_application_ping_pong_keeps_a_quiet_link_alive` | :74 test_application_ping_pong_keeps_a_quiet_link_alive | CLOCK-INJECTABLE | DIRECT |
| 17 | `test_failure_cap.py::test_count_cap_keeps_first_n_counts_all_announces` | :45 test_count_cap_keeps_first_n_counts_all_announces | CLOCK-INJECTABLE | DIRECT |
| 18 | `test_failure_cap.py::test_byte_cap_binds_independently` | :76 test_byte_cap_binds_independently | CLOCK-INJECTABLE | DIRECT |
| 19 | `test_failure_cap.py::test_capped_failures_get_one_line_summaries` | :99 test_capped_failures_get_one_line_summaries | CLOCK-INJECTABLE | DIRECT |
| 20 | `test_failure_capture.py::test_checksum_failure_capture_has_every_ruled_field` | :52 test_checksum_failure_capture_has_every_ruled_field | CLOCK-INJECTABLE | DIRECT |
| 21 | `test_failure_capture.py::test_every_checksum_failure_captured_not_positionally_sampled` | :102 **test_every_checksum_failure_captured_not_positionally** (truncated) | CLOCK-INJECTABLE | DIRECT |
| 22 | `test_protocol_ping.py::test_protocol_ping_params_set_deliberately` | :53 test_protocol_ping_params_set_deliberately | CLOCK-INJECTABLE | DIRECT |
| 23 | `test_protocol_ping.py::test_protocol_level_close_recovers` | :72 test_protocol_level_close_recovers | CLOCK-INJECTABLE | DIRECT |
| 24 | `test_throughput.py::test_receive_to_process_latency_recorded_through_production_path` | :25 **test_receive_to_process_latency_recorded** (truncated) | CLOCK-INJECTABLE | DIRECT |
| 25 | `test_reconnect_to_effect.py::test_five_real_failures_reconnect_and_emission_resumes` | :44 test_five_real_failures_reconnect_and_emission_resumes | CLOCK-INJECTABLE | DIRECT |
| 26 | `test_venue_close_path.py::test_venue_close_unexpected_reconnects_expected_shuts_down_cleanly` | :35 **test_venue_close_unexpected_reconnects_expected_shuts** (truncated) | CLOCK-INJECTABLE | DIRECT |
| 27 | `test_backoff_breaker.py::test_transient_reopen_failure_retries_under_backoff_then_emission_resumes` | :59 **test_transient_reopen_failure_retries_under_backoff** (truncated) | CLOCK-INJECTABLE | DIRECT |
| 28 | `test_pong_observer.py::test_pong_observer_records_rtt_distribution_via_protocol_ping` | :25 **test_pong_observer_records_rtt_distribution** (truncated) | ASYNCIO-SLEEP (excluded) | — |
| 29 | `test_pong_observer.py::test_absent_pongs_are_a_signal_not_gappiness` | :49 test_absent_pongs_are_a_signal_not_gappiness | ASYNCIO-SLEEP (excluded) | — |
| 30 | `test_lag_sampler.py::test_starved_lag_sampler_self_reports_degradation` | :27 test_starved_lag_sampler_self_reports_degradation | ASYNCIO-SLEEP (excluded) | — |
| **35** | `test_ledger_persistence.py::test_incremental_persist_survives_unhandled_exception_mid_capture` | :82 **test_incremental_persist_survives_unhandled_exception** (truncated) | **CLOCK-INJECTABLE** (was BOUND; D40/D41) | DIRECT |

**Totals after the D42 amendment:** the table lists 31 rows = the audit's 30 races + **entry 35**,
promoted from the bounds block. Clock-injectable **27** (26 + entry 35), asyncio-sleep **3**,
already-converted **1**; bounds now **6**. Batch A 5 + B 13 + C **9** = **27**.

**Rename flag:** race 28's audit name `..._records_rtt_distribution` was TRUNCATED; the real name is
`..._records_rtt_distribution_via_protocol_ping` (same file+line, same asyncio.sleep content). The
asyncio-sleep **set is unchanged** (28/29/30) — a truncation artifact, not a denominator change. (Same
truncation the audit applied to race 5's `..._via_factory`.)

## The A/B/C partition (by test file — no file split across batches)

- **BATCH A (this WO):** `test_live_capture.py` — races **1, 2, 3, 4, 5**. 1–3 DIRECT; **4** DIRECT
  deadline-assertion (uses the new `AdvancingClock`, §2.0-bis, to fire the deadline deterministically);
  **5** FACTORY-BUILT (inject the coherent pair + transport THROUGH the runner). **All five converted
  on their OWN termination branch — the DEADLINE — asserted, via `AdvancingClock`.** Sizing: the WO
  highlights this file as "converts whole"; it is the one file exercising both the DIRECT and
  FACTORY-BUILT paths plus the deadline fixture, so it is the natural, self-contained batch A.
- **BATCH B (named, not touched):** `test_gap_recording.py` (6: races 6–11), `test_keepalive.py`
  (2: 15–16), `test_failure_cap.py` (3: 17–19), `test_failure_capture.py` (2: 20–21) = **13 races**.
  **Conversion requirement (D39 item 1, ratified):** each race must KEEP its own production
  termination branch (deadline / venue-close / failure-cap / breaker), and the branch exercised
  before and after is part of acceptance — **asserted, not assumed**. No scripted-clean-close
  substitution.
- **BATCH C:** `test_ledger_persistence.py` (**2**: races 12 and **35**), `test_host_suspend.py`
  (1: race 14 — the non-foundation one), `test_protocol_ping.py` (2: 22–23), `test_throughput.py`
  (1: 24), `test_reconnect_to_effect.py` (1: 25), `test_venue_close_path.py` (1: 26),
  `test_backoff_breaker.py` (1: 27) = **9 races**.
  **Same conversion requirement as batch B (D39 item 1):** keep the race on its own termination
  branch; the branch exercised before and after is asserted, not assumed.
  **Entry 35 joins here (D40/D41):** it was filed by the WO-023 audit among the 7 legitimate BOUNDS
  (*"dur=0.25, injected crash ends it"*) and **reclassified BOUND → RACE** after WO-031 §3-bis measured
  the outcome flipping on the injected clock's rate. Its read is the DEADLINE, which is INJECTABLE, so
  it is CLOCK-INJECTABLE/CONVERTIBLE. It lands in batch C because it lives in `test_ledger_persistence.py`
  alongside race 12, and a file does not split across batches.

Batch A (5) + B (13) + C (8) = **26**. Later batches re-read THIS artifact and re-enumerate against it.

---

## AMENDMENT — 2026-07-27 (WO-032 §2, implementing D39 item 1)

**Annotated, not silently rewritten.** This artifact was committed at `d0450fa`, BEFORE batch A ran
and before D39 was ratified. Two things above have been amended; the record of why is here.

1. **Batch A's entry no longer reads "inject FakeClock at construction, terminate via scripted
   clean-close."** That was the *plan*; it is not what WO-029 did. All five races converted on the
   DEADLINE branch using the self-advancing `AdvancingClock`. The frozen-clock plan would have kept
   every assertion green while moving races 1–3 off the deadline branch onto the `ConnectionClosedOK`
   branch — a coverage loss no assertion could report. The entry now records what happened.

2. **Batches B and C carry the ratified conversion requirement** (D39 item 1): a conversion must keep
   the race on its own production termination branch, and the branch exercised before and after is
   part of acceptance — asserted, not assumed.

Ratified after `d0450fa`; committed here in WO-032. See
`docs/decisions/2026-07-27-a-conversion-preserves-the-path-not-just-the-assertions.md`.

**Note on the line numbers in the table above.** They were derived at base `9c084c3` and are NOT
refreshed after each batch converts — batch A's conversion moved races 1–5 in `test_live_capture.py`.
This is expected and harmless: `tools/wo029_reverify_partition.py` keys its verdict on the test NAME
(WO-032 §1), reports a moved line as informational, and hard-FAILS only on a name that no longer
resolves. The line numbers remain useful as a starting point, not as identity.

---

## AMENDMENT — 2026-07-28 (WO-035 §2, implementing D42)

Three ratified amendments landed here, annotated rather than silently applied.

1. **Batch C is 9, not 8** (§2.1). **Entry 35** —
   `test_ledger_persistence.py::test_incremental_persist_survives_unhandled_exception_mid_capture` —
   was filed by the WO-023 audit among the 7 legitimate BOUNDS and **reclassified BOUND → RACE** once
   WO-031 §3-bis measured its outcome flipping on the injected clock's rate. Its read is the DEADLINE,
   which is INJECTABLE, so it is clock-injectable and convertible. WO-031 escalated rather than
   amending (correctly — a denominator change is the lead's), D40/D41 ratified, and **this is the
   commit where the ruling reaches the tree.** Clock-injectable 26 → **27**; bounds 7 → **6**.

2. **Race identifiers are now pytest NODE IDs** (§2.2), restated from
   `evidence/WO-034/audit_node_ids.md`, which was obtained from pytest's own collection and resolves
   37/37. The prose `file:line` + name columns are **retained as the historical record, marked
   superseded** — not deleted. Nine of the audit's 37 identifiers were found truncated (WO-034 §2),
   six of them races: **5, 21, 24, 26, 27, 28**. Those six are marked in the table.

3. **The standing artifact-ruling check** (§2.3) is recorded as doctrine in
   `docs/decisions/2026-07-27-a-ruling-is-not-in-force-until-its-artifact-is-committed.md`:
   every WO's §1 confirms the artifacts it reads reflect all rulings made since they were written.
   **This file is the specimen** — it sat at "batch C = 8" through two WOs after the ruling that made
   it 9, and WO-031's original §2 STOP was the same failure one artifact earlier.
