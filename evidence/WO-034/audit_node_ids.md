# WO-034 §2 (D41) — the audit's 37 identifiers, regenerated as pytest NODE IDs

Derived at HEAD `ba75394`. **Classify/verify only — no race converted, no test edited.**

**These node IDs are now CANONICAL** for all future enumeration (the reverify tool, batch planning,
any WO that addresses a race). The historical audit `evidence/WO-023/wall_clock_race_audit.txt` is
**NOT rewritten** — its prose identifiers stay on the record as written, annotated here as superseded.

## How these were obtained

`tools/wo034_node_id_regeneration.py` runs **pytest's own collection**
(`pytest tests/ --collect-only -q -p no:randomly -o addopts=`) and matches each audit entry to a
collected node ID. **It never greps source text.** That is D41's whole point: the prose form has now
failed nine times across two mechanisms — name truncation, and blindness to class-bound methods.

Each audit entry is matched by `(file, test-name-prefix)`. A prose name that is a *prefix* of exactly
one collected test resolves, and the difference is reported as a MISMATCH.

---

## ⚠ THE HEADLINE: the mismatch population is NINE, not four

D41 recorded four known mismatches (entries **5, 28, 31, 36**). Regeneration finds **nine**. Five were
not previously known:

| Entry | Batch | Audit's prose name | Real name | Kind |
|---|---|---|---|---|
| **21** | **B** | `test_every_checksum_failure_captured_not_positionally` | `…_not_positionally_sampled` | truncation |
| **24** | **C** | `test_receive_to_process_latency_recorded` | `…_recorded_through_production_path` | truncation |
| **26** | **C** | `test_venue_close_unexpected_reconnects_expected_shuts` | `…_shuts_down_cleanly` | truncation |
| **27** | **C** | `test_transient_reopen_failure_retries_under_backoff` | `…_under_backoff_then_emission_resumes` | truncation |
| **35** | **C** | `test_incremental_persist_survives_unhandled_exception` | `…_mid_capture` | truncation |

Plus D41's four, reproduced exactly:

| Entry | Batch | Audit's prose name | Real name | Kind |
|---|---|---|---|---|
| 5 | A | `test_runner_resolves_live_adapter_from_data_source` | `…_via_factory` | truncation |
| 28 | — | `test_pong_observer_records_rtt_distribution` | `…_via_protocol_ping` | truncation |
| 31 | bound | `test_persistent_reopen_failure_trips_breaker_loud` | `…_with_forensic_tail` | truncation |
| 36 | bound | `test_connection_failure_raises_and_does_not_replay` | `…_fixtures`, and it is a **method on `TestNoSilentFallback`** | truncation + structure |

**Four of batch C's nine races (24, 26, 27, 35) carried a truncated identifier** — the batch this WO
was about to convert. Entry 21 is in batch B.

**Rate:** 6 of the 30 races (20%) and 9 of all 37 entries (24%) were misidentified.

### What this does NOT change

**No denominator movement, and no race lost.** Every one of the 37 resolves to **exactly one**
collected test — the truncations are strict prefixes with a unique completion, and the tool reports
`AMBIGUOUS` if a prefix matched more than one (none did). No entry is UNRESOLVED. Categories are
untouched: clock-injectable **27**, bounds **6**, total **30**.

The defect is in the *identifier*, not the *classification*. But an identifier is what every later WO
addresses a race by, which is why D41 promoted this to ruled work and why §2.2 makes a fifth mismatch
a STOP.

### Why the count was under-reported until now

The earlier passes diffed against `evidence/WO-029/batch_partition.md`, which **silently corrected
several of the audit's names** when it re-derived the table (races 5 and 28 were repaired there,
28 with a flag). Diffing against the corrected restatement measures the *restatement's* accuracy, not
the audit's. This regeneration transcribes the audit's prose **verbatim** from
`wall_clock_race_audit.txt` instead — and the population trebled.

---

## THE 30 RACES

| # | Audit prose (verbatim) | Canonical node ID | |
|---|---|---|---|
| 1 | `test_live_capture.py:59 test_runner_drives_instrumented_transport_end_to_end` | `tests/integration/test_live_capture.py::test_runner_drives_instrumented_transport_end_to_end` | exact |
| 2 | `test_live_capture.py:98 test_runner_persistence_is_not_optional_on_the_adapter` | `tests/integration/test_live_capture.py::test_runner_persistence_is_not_optional_on_the_adapter` | exact |
| 3 | `test_live_capture.py:114 test_short_bounded_run_completes_with_readable_artifacts` | `tests/integration/test_live_capture.py::test_short_bounded_run_completes_with_readable_artifacts` | exact |
| 4 | `test_live_capture.py:140 test_clean_deadline_close_does_not_reconnect_dual` | `tests/integration/test_live_capture.py::test_clean_deadline_close_does_not_reconnect_dual` | exact |
| **5** | `test_live_capture.py:197 test_runner_resolves_live_adapter_from_data_source` | `tests/integration/test_live_capture.py::test_runner_resolves_live_adapter_from_data_source_via_factory` | **MISMATCH** |
| 6 | `test_gap_recording.py:80 test_keepalive_reconnect_gap_recorded` | `tests/integration/test_gap_recording.py::test_keepalive_reconnect_gap_recorded` | exact |
| 7 | `test_gap_recording.py:115 test_checksum_resync_gap_recorded` | `tests/integration/test_gap_recording.py::test_checksum_resync_gap_recorded` | exact |
| 8 | `test_gap_recording.py:143 test_breaker_retry_ladder_recorded_on_reconnect_gap` | `tests/integration/test_gap_recording.py::test_breaker_retry_ladder_recorded_on_reconnect_gap` | exact |
| 9 | `test_gap_recording.py:175 test_venue_disconnect_gap_recorded` | `tests/integration/test_gap_recording.py::test_venue_disconnect_gap_recorded` | exact |
| 10 | `test_gap_recording.py:237 test_overlapping_gaps_union_and_collective_close` | `tests/integration/test_gap_recording.py::test_overlapping_gaps_union_and_collective_close` | exact |
| 11 | `test_gap_recording.py:281 test_ledger_reports_incomplete_gap` | `tests/integration/test_gap_recording.py::test_ledger_reports_incomplete_gap` | exact |
| 12 | `test_ledger_persistence.py:47 test_gap_ledger_persisted_readable_from_disk` | `tests/integration/test_ledger_persistence.py::test_gap_ledger_persisted_readable_from_disk` | exact |
| 13 | `test_host_suspend.py:46 test_host_suspend_recorded_diagnostic_not_terminal` | `tests/integration/test_host_suspend.py::test_host_suspend_recorded_diagnostic_not_terminal` | exact |
| 14 | `test_host_suspend.py:83 test_no_host_suspend_under_normal_timing` | `tests/integration/test_host_suspend.py::test_no_host_suspend_under_normal_timing` | exact |
| 15 | `test_keepalive.py:42 test_heartbeat_absence_triggers_reconnect` | `tests/integration/test_keepalive.py::test_heartbeat_absence_triggers_reconnect` | exact |
| 16 | `test_keepalive.py:74 test_application_ping_pong_keeps_a_quiet_link_alive` | `tests/integration/test_keepalive.py::test_application_ping_pong_keeps_a_quiet_link_alive` | exact |
| 17 | `test_failure_cap.py:45 test_count_cap_keeps_first_n_counts_all_announces` | `tests/integration/test_failure_cap.py::test_count_cap_keeps_first_n_counts_all_announces` | exact |
| 18 | `test_failure_cap.py:76 test_byte_cap_binds_independently` | `tests/integration/test_failure_cap.py::test_byte_cap_binds_independently` | exact |
| 19 | `test_failure_cap.py:99 test_capped_failures_get_one_line_summaries` | `tests/integration/test_failure_cap.py::test_capped_failures_get_one_line_summaries` | exact |
| 20 | `test_failure_capture.py:52 test_checksum_failure_capture_has_every_ruled_field` | `tests/integration/test_failure_capture.py::test_checksum_failure_capture_has_every_ruled_field` | exact |
| **21** | `test_failure_capture.py:102 test_every_checksum_failure_captured_not_positionally` | `tests/integration/test_failure_capture.py::test_every_checksum_failure_captured_not_positionally_sampled` | **MISMATCH** |
| 22 | `test_protocol_ping.py:53 test_protocol_ping_params_set_deliberately` | `tests/integration/test_protocol_ping.py::test_protocol_ping_params_set_deliberately` | exact |
| 23 | `test_protocol_ping.py:72 test_protocol_level_close_recovers` | `tests/integration/test_protocol_ping.py::test_protocol_level_close_recovers` | exact |
| **24** | `test_throughput.py:25 test_receive_to_process_latency_recorded` | `tests/integration/test_throughput.py::test_receive_to_process_latency_recorded_through_production_path` | **MISMATCH** |
| 25 | `test_reconnect_to_effect.py:44 test_five_real_failures_reconnect_and_emission_resumes` | `tests/integration/test_reconnect_to_effect.py::test_five_real_failures_reconnect_and_emission_resumes` | exact |
| **26** | `test_venue_close_path.py:35 test_venue_close_unexpected_reconnects_expected_shuts` | `tests/integration/test_venue_close_path.py::test_venue_close_unexpected_reconnects_expected_shuts_down_cleanly` | **MISMATCH** |
| **27** | `test_backoff_breaker.py:59 test_transient_reopen_failure_retries_under_backoff` | `tests/integration/test_backoff_breaker.py::test_transient_reopen_failure_retries_under_backoff_then_emission_resumes` | **MISMATCH** |
| **28** | `test_pong_observer.py:25 test_pong_observer_records_rtt_distribution` | `tests/integration/test_pong_observer.py::test_pong_observer_records_rtt_distribution_via_protocol_ping` | **MISMATCH** |
| 29 | `test_pong_observer.py:49 test_absent_pongs_are_a_signal_not_gappiness` | `tests/integration/test_pong_observer.py::test_absent_pongs_are_a_signal_not_gappiness` | exact |
| 30 | `test_lag_sampler.py:27 test_starved_lag_sampler_self_reports_degradation` | `tests/integration/test_lag_sampler.py::test_starved_lag_sampler_self_reports_degradation` | exact |

## THE 7 BOUNDS (entries 31–37)

Regenerated too — identifiers must be canonical for the whole taxonomy, not only the part currently
being converted.

| # | Audit prose (verbatim) | Canonical node ID | |
|---|---|---|---|
| **31** | `test_backoff_breaker.py:88 test_persistent_reopen_failure_trips_breaker_loud` | `tests/integration/test_backoff_breaker.py::test_persistent_reopen_failure_trips_breaker_loud_with_forensic_tail` | **MISMATCH** |
| 32 | `test_gap_recording.py:202 test_terminal_venue_disconnect_breaker_gap_recorded` | `tests/integration/test_gap_recording.py::test_terminal_venue_disconnect_breaker_gap_recorded` | exact |
| 33 | `test_live_capture.py:172 test_breaker_trip_terminates_run_with_forensic_tail` | `tests/integration/test_live_capture.py::test_breaker_trip_terminates_run_with_forensic_tail` | exact |
| 34 | `test_reconnect_to_effect.py:100 test_stranded_reconnect_flag_fails_loudly` | `tests/integration/test_reconnect_to_effect.py::test_stranded_reconnect_flag_fails_loudly` | exact |
| **35** | `test_ledger_persistence.py:82 test_incremental_persist_survives_unhandled_exception` | `tests/integration/test_ledger_persistence.py::test_incremental_persist_survives_unhandled_exception_mid_capture` | **MISMATCH** — and reclassified BOUND→RACE (D41) |
| **36** | `test_no_silent_fallback.py:25 test_connection_failure_raises_and_does_not_replay` | `tests/integration/test_no_silent_fallback.py::TestNoSilentFallback::test_connection_failure_raises_and_does_not_replay_fixtures` | **MISMATCH** — truncation **+ class method** |
| 37 | `test_no_silent_fallback.py:52 test_live_method_refuses_fixture_mode_adapter` | `tests/integration/test_no_silent_fallback.py::TestNoSilentFallback::test_live_method_refuses_fixture_mode_adapter` | exact |

Note entries 36 and 37 are the only two that carry a **class** segment. A `^def test_` source scan
cannot see either; node IDs render them natively.

---

## Status

Regeneration **PASSES on resolution** (37/37 resolve, 0 unresolved, 0 ambiguous) and **FAILS §2.2's
diff gate** (nine mismatches against D41's four). Per §2.2 this WO **STOPPED before converting
anything**; batch C's 9 races are untouched. See `WO-034-REPORT.md`.
