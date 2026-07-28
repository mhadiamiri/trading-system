"""WO-034 §2 (D41) — REGENERATE THE AUDIT'S 30 IDENTIFIERS AS PYTEST NODE IDs.

The WO-023 §1 audit identifies its 30 races by `file:line name` prose, typed by hand. That identifier
form has failed four times now, in two distinct ways:

  * TRUNCATION — race 5 (`..._via_factory`), race 28 (`..._via_protocol_ping`), entry 31
    (`..._with_forensic_tail`) were all recorded with their names cut short.
  * STRUCTURE-BLINDNESS — entry 36 is a METHOD on `class TestNoSilentFallback`. A `^def test_` scan
    over source text cannot see it, and the prose identifier records no class.

Line numbers have drifted too, every time a batch converted its own file.

D41 ruled the fix: migrate to **pytest NODE IDs**, obtained from **pytest's own collection** — never a
regex over source text. A node ID (`path::Class::method` or `path::function`) is what the runner itself
uses to address a test, so it is position-faithful, structure-faithful (classes appear natively), and
truncation-immune (it is read from the collected object, not retyped).

THIS SCRIPT COLLECTS, IT DOES NOT GREP. It runs `pytest --collect-only -q`, then matches each audit
entry to a collected node ID **by test-name suffix**, which is exactly the tolerance the truncations
require: a prose name that is a PREFIX of the real one resolves, and the mismatch is reported.

    python tools/wo034_node_id_regeneration.py

Writes to .artifacts/ (WO-032 §4.1 — a tools/ script never writes under evidence/).
"""
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo034_node_id_regeneration")

# The audit's 30 races, transcribed VERBATIM from evidence/WO-023/wall_clock_race_audit.txt — the
# ORIGINAL prose, not evidence/WO-029/batch_partition.md's later restatement.
#
# THIS DISTINCTION IS THE WHOLE MEASUREMENT. batch_partition.md silently CORRECTED several of the
# audit's names when it re-derived the table (race 5 and race 28 were repaired there, race 28 with a
# flag). Diffing node IDs against the corrected restatement would measure the restatement's accuracy,
# not the audit's, and would under-report the truncation population — which is exactly what a first
# pass of this script did before the source was checked. (num, file, audit_line, audit_name, category)
AUDIT = [
    (1, "test_live_capture.py", 59, "test_runner_drives_instrumented_transport_end_to_end", "CLOCK-INJECTABLE"),
    (2, "test_live_capture.py", 98, "test_runner_persistence_is_not_optional_on_the_adapter", "CLOCK-INJECTABLE"),
    (3, "test_live_capture.py", 114, "test_short_bounded_run_completes_with_readable_artifacts", "CLOCK-INJECTABLE"),
    (4, "test_live_capture.py", 140, "test_clean_deadline_close_does_not_reconnect_dual", "CLOCK-INJECTABLE"),
    (5, "test_live_capture.py", 197, "test_runner_resolves_live_adapter_from_data_source", "CLOCK-INJECTABLE"),
    (6, "test_gap_recording.py", 80, "test_keepalive_reconnect_gap_recorded", "CLOCK-INJECTABLE"),
    (7, "test_gap_recording.py", 115, "test_checksum_resync_gap_recorded", "CLOCK-INJECTABLE"),
    (8, "test_gap_recording.py", 143, "test_breaker_retry_ladder_recorded_on_reconnect_gap", "CLOCK-INJECTABLE"),
    (9, "test_gap_recording.py", 175, "test_venue_disconnect_gap_recorded", "CLOCK-INJECTABLE"),
    (10, "test_gap_recording.py", 237, "test_overlapping_gaps_union_and_collective_close", "CLOCK-INJECTABLE"),
    (11, "test_gap_recording.py", 281, "test_ledger_reports_incomplete_gap", "CLOCK-INJECTABLE"),
    (12, "test_ledger_persistence.py", 47, "test_gap_ledger_persisted_readable_from_disk", "CLOCK-INJECTABLE"),
    (13, "test_host_suspend.py", 46, "test_host_suspend_recorded_diagnostic_not_terminal", "ALREADY-CONVERTED"),
    (14, "test_host_suspend.py", 83, "test_no_host_suspend_under_normal_timing", "CLOCK-INJECTABLE"),
    (15, "test_keepalive.py", 42, "test_heartbeat_absence_triggers_reconnect", "CLOCK-INJECTABLE"),
    (16, "test_keepalive.py", 74, "test_application_ping_pong_keeps_a_quiet_link_alive", "CLOCK-INJECTABLE"),
    (17, "test_failure_cap.py", 45, "test_count_cap_keeps_first_n_counts_all_announces", "CLOCK-INJECTABLE"),
    (18, "test_failure_cap.py", 76, "test_byte_cap_binds_independently", "CLOCK-INJECTABLE"),
    (19, "test_failure_cap.py", 99, "test_capped_failures_get_one_line_summaries", "CLOCK-INJECTABLE"),
    (20, "test_failure_capture.py", 52, "test_checksum_failure_capture_has_every_ruled_field", "CLOCK-INJECTABLE"),
    (21, "test_failure_capture.py", 102, "test_every_checksum_failure_captured_not_positionally", "CLOCK-INJECTABLE"),
    (22, "test_protocol_ping.py", 53, "test_protocol_ping_params_set_deliberately", "CLOCK-INJECTABLE"),
    (23, "test_protocol_ping.py", 72, "test_protocol_level_close_recovers", "CLOCK-INJECTABLE"),
    (24, "test_throughput.py", 25, "test_receive_to_process_latency_recorded", "CLOCK-INJECTABLE"),
    (25, "test_reconnect_to_effect.py", 44, "test_five_real_failures_reconnect_and_emission_resumes", "CLOCK-INJECTABLE"),
    (26, "test_venue_close_path.py", 35, "test_venue_close_unexpected_reconnects_expected_shuts", "CLOCK-INJECTABLE"),
    (27, "test_backoff_breaker.py", 59, "test_transient_reopen_failure_retries_under_backoff", "CLOCK-INJECTABLE"),
    (28, "test_pong_observer.py", 25, "test_pong_observer_records_rtt_distribution", "ASYNCIO-SLEEP"),
    (29, "test_pong_observer.py", 49, "test_absent_pongs_are_a_signal_not_gappiness", "ASYNCIO-SLEEP"),
    (30, "test_lag_sampler.py", 27, "test_starved_lag_sampler_self_reports_degradation", "ASYNCIO-SLEEP"),
]

# The audit's 7 BOUNDS (entries 31-37). Entry 35 was reclassified BOUND -> RACE by D41; the other six
# were MEASURED as genuine bounds by WO-033. Regenerated here too: identifiers must be canonical for
# the whole taxonomy, not only for the part currently being converted.
BOUNDS = [
    (31, "test_backoff_breaker.py", 88, "test_persistent_reopen_failure_trips_breaker_loud", "BOUND-measured"),
    (32, "test_gap_recording.py", 202, "test_terminal_venue_disconnect_breaker_gap_recorded", "BOUND-measured"),
    (33, "test_live_capture.py", 172, "test_breaker_trip_terminates_run_with_forensic_tail", "BOUND-measured"),
    (34, "test_reconnect_to_effect.py", 100, "test_stranded_reconnect_flag_fails_loudly", "BOUND-measured"),
    (35, "test_ledger_persistence.py", 82, "test_incremental_persist_survives_unhandled_exception", "RACE (D41, was BOUND)"),
    (36, "test_no_silent_fallback.py", 25, "test_connection_failure_raises_and_does_not_replay", "BOUND-measured"),
    (37, "test_no_silent_fallback.py", 52, "test_live_method_refuses_fixture_mode_adapter", "BOUND-measured"),
]

# The four mismatches D41 already knows about. A FIFTH is a finding (§2.2) and a STOP.
KNOWN_MISMATCHES = {5, 28, 31, 36}


def collect_node_ids():
    """pytest's OWN collection. Not a regex over source text — that is the whole point (D41)."""
    # `-o addopts=` CLEARS pytest.ini's `addopts = -v ...`. Without it, ini verbosity wins over the
    # `-q` here and collection prints its indented TREE (<Module>/<Class>/<Function>) instead of flat
    # node IDs — which would silently yield zero matches rather than an error.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q",
         "-p", "no:randomly", "-o", "addopts="],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONUTF8": "1"})
    ids = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if "::" in line and line.startswith("tests/"):
            ids.append(line.split(" ")[0])
    if not ids:
        raise SystemExit(f"collection produced no node IDs; pytest said:\n{proc.stdout}\n{proc.stderr}")
    return ids


def match(entry_file, prose_name, node_ids):
    """Resolve one audit entry to a collected node ID.

    Matching is by (file, test-name) where the collected name STARTS WITH the prose name — precisely
    the tolerance the truncations need. Returns (node_id, exact) or (None, False).
    """
    hits = []
    for nid in node_ids:
        path, _, rest = nid.partition("::")
        if os.path.basename(path) != entry_file:
            continue
        leaf = rest.split("::")[-1]
        if leaf == prose_name:
            return nid, True
        if leaf.startswith(prose_name):
            hits.append(nid)
    if len(hits) == 1:
        return hits[0], False
    if len(hits) > 1:
        return f"AMBIGUOUS: {hits}", False
    return None, False


def main():
    node_ids = collect_node_ids()
    out = ["WO-034 §2 (D41) — THE AUDIT'S IDENTIFIERS, REGENERATED AS PYTEST NODE IDs",
           f"Collected via pytest's own collection: {len(node_ids)} node IDs.",
           "NOT grepped from source text — that form failed 4 times (3 truncations + 1 class method).",
           ""]
    mismatches, unresolved = [], []

    for label, rows in (("THE 30 RACES", AUDIT), ("THE 7 BOUNDS (entries 31-37)", BOUNDS)):
        out += ["=" * 100, label, "=" * 100,
                f"  {'#':>3}  {'audit prose identifier':<74} {'match'}"]
        for num, fname, line, prose, cat in rows:
            nid, exact = match(fname, prose, node_ids)
            if nid is None:
                unresolved.append((num, fname, prose))
                status = "UNRESOLVED"
            elif exact:
                status = "exact"
            else:
                mismatches.append((num, fname, prose, nid))
                status = "MISMATCH"
            out.append(f"  {num:>3}  {fname}:{line} {prose:<40} {status}")
            out.append(f"       -> {nid}")
        out.append("")

    out += ["=" * 100, "§2.2 DIFF AGAINST THE PROSE LIST", "=" * 100,
            f"  entries whose collected node ID differs from the prose identifier: "
            f"{sorted(m[0] for m in mismatches)}",
            f"  D41's known set (truncations + the class method)                : "
            f"{sorted(KNOWN_MISMATCHES)}"]
    for num, fname, prose, nid in mismatches:
        out.append(f"    #{num:<3} prose {prose!r}")
        out.append(f"          real  {nid}")

    extra = sorted(set(m[0] for m in mismatches) - KNOWN_MISMATCHES)
    missing = sorted(KNOWN_MISMATCHES - set(m[0] for m in mismatches))
    ok = not extra and not missing and not unresolved
    out += ["",
            f"  UNRESOLVED (no collected test matches)  : {unresolved or 'none'}",
            f"  mismatches BEYOND D41's known four      : {extra or 'none'}",
            f"  D41 mismatches NOT reproduced           : {missing or 'none'}",
            ""]
    if ok:
        out.append("VERDICT: PASS — every audit entry resolves to a collected node ID, and the diff is "
                   "EXACTLY D41's known four (5, 28, 31, 36). No fifth misidentification exists.")
    else:
        why = []
        if unresolved:
            why.append(f"{len(unresolved)} entr(ies) resolve to NO collected test: {unresolved}")
        if extra:
            why.append(f"a FIFTH+ misidentification exists (§2.2 STOP): entries {extra}")
        if missing:
            why.append(f"D41 expected a mismatch at {missing} but the identifier matched exactly")
        out.append("VERDICT: FAIL — " + "; ".join(why))

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
