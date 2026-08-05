"""
WO-044 §3 — RESUME SUPPORT: corpus-id, inter-run seams, cumulative accounting.

D45: "Every seam is a declared ledger record — this is MORE honest than one unbroken process, not
less." These proofs assert the properties that claim rests on:

  §3.1 runs of a corpus group under one corpus-id, structurally
  §3.3 a seam carries a DECLARED cause and a MEASURED true duration — and REFUSES both an
       undeclared cause and an unmeasurable left bound, because a guessed cause is a smoothed seam
  §3.5 the manifest spans the corpus-id: every segment of every run, each hashed
  §3.6 a seam behaves like a gap for a default-deny reader — unresolved reads as +infinity
  §3.7 cumulative hours sum across runs, minus recorded in-run gap time

PRODUCIBILITY IS PROVED BY PRODUCTION, NOT BY DECLARATION. `test_every_seam_cause_is_genuinely
_producible` drives each of the three causes through the real writer and reads the code back off
DISK. The vocabulary guard's own docstring admits its weak half — "declared=>producible is satisfied
for a declared code by its CONSTANT DEFINITION, or even a COMMENT/DOCSTRING mention, not only by a
genuine emit" — and WO-037 §3 caught a code living in exactly that gap. A constant in a tuple would
satisfy the scan while emitting nothing; these tests close that for the seam vocabulary specifically.

NO NETWORK, NO SOCKET. Pure record/ledger machinery over tmp_path.
"""

import json

import pytest

from trading.data.corpus import (
    CORPUS_SEAM_CAUSES,
    CORPUS_TARGET_HOURS,
    CorpusLedger,
    RunRecord,
    SeamCauseUndeclared,
    SegmentRecord,
    gap_summary,
    reconcile_run_from_disk,
    run_frame_bounds,
)
from trading.logkit.decision import VALID_REASON_CODES


# ── helpers ───────────────────────────────────────────────────────────────────────────────────

def _write_segment(run_dir, name, stamps):
    """Write a .jsonl segment whose frames carry the given ISO timestamps."""
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / name
    path.write_text(
        "\n".join(json.dumps({"timestamp": s, "symbol": "BTC/USD", "bid": "1", "ask": "2"})
                  for s in stamps) + "\n",
        encoding="utf-8",
    )
    return path


def _write_gap_ledger(run_dir, gaps):
    """Write a gap ledger JSONL in the real runtime shape: run_start, then open/resolved pairs."""
    lines = [json.dumps({"event": "run_start", "run_wall_anchor": "2026-08-05T00:00:00+00:00"})]
    for gid, duration in enumerate(gaps):
        lines.append(json.dumps({"event": "open", "gap_id": gid, "cause": "VENUE_DISCONNECT",
                                 "reason_code": "VENUE_CONNECTION_CLOSED", "duration_s": None}))
        if duration is not None:
            lines.append(json.dumps({"event": "resolved", "gap_id": gid,
                                     "cause": "VENUE_DISCONNECT",
                                     "reason_code": "VENUE_CONNECTION_CLOSED",
                                     "duration_s": duration}))
    (run_dir / "gap_ledger.json").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── §3.3 the seam vocabulary ──────────────────────────────────────────────────────────────────

def test_seam_causes_are_the_declared_three():
    assert CORPUS_SEAM_CAUSES == ("PROCESS_RESTART", "POLICY_SHUTDOWN", "OPERATOR_STOP")
    declared = set(VALID_REASON_CODES["DATA"])
    assert set(CORPUS_SEAM_CAUSES) <= declared, (
        "every seam cause must be a DECLARED reason code — the corpus archives these records, and "
        "an undeclared code in the archive is permanent"
    )


def test_every_seam_cause_is_genuinely_producible(tmp_path):
    """Each of the three causes is driven through the REAL writer and read back off DISK.

    This is the property a constant cannot satisfy. The vocabulary scan would pass on the tuple
    alone; WO-037 §3 found a code that passed exactly that way while being unreachable. Here every
    cause is produced by `open_seam` and recovered from the persisted seam ledger.
    """
    produced = {}
    for i, cause in enumerate(CORPUS_SEAM_CAUSES):
        ledger = CorpusLedger(root=tmp_path, corpus_id=f"c{i}", host="TESTHOST")
        ledger.add_run(RunRecord(run_id="run_a", start_utc="2026-08-05T00:00:00+00:00",
                                 last_frame_utc="2026-08-05T01:00:00+00:00"))
        ledger.open_seam(cause=cause, prior_run_id="run_a", resumed_run_id="run_b",
                         prior_last_frame_utc="2026-08-05T01:00:00+00:00")
        # Read the code back off the DURABLE record, not the object we just built.
        events = [json.loads(line) for line in
                  ledger.seam_ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        produced[cause] = [e["reason_code"] for e in events]

    for cause in CORPUS_SEAM_CAUSES:
        assert produced[cause] == [cause], (
            f"{cause} must be EMITTED into a durable seam record, not merely declared. "
            f"Got {produced[cause]}"
        )


def test_undeclared_seam_cause_is_refused(tmp_path):
    """A resume that does not declare a cause is REFUSED — the process cannot infer why it died."""
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    for bogus in (None, "", "CRASHED", "process_restart", "POLICY_SHUTDOWN_EXTRA"):
        with pytest.raises(SeamCauseUndeclared, match="SEAM_CAUSE_UNDECLARED"):
            ledger.open_seam(cause=bogus, prior_run_id="a", resumed_run_id="b",
                             prior_last_frame_utc="2026-08-05T01:00:00+00:00")
    assert ledger.manifest.seams == [], "a refused seam must not be recorded"


def test_seam_without_measured_left_bound_is_refused(tmp_path):
    """No measured last frame => no true left bound => REFUSE rather than estimate one (§0.4)."""
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    with pytest.raises(SeamCauseUndeclared, match="could only be estimated"):
        ledger.open_seam(cause="OPERATOR_STOP", prior_run_id="a", resumed_run_id="b",
                         prior_last_frame_utc="")


# ── §3.3 / §3.6 the seam behaves like a gap ───────────────────────────────────────────────────

def test_open_seam_has_no_duration_and_denies(tmp_path):
    """An OPEN seam reports duration None — read as +infinity, exactly like an unclosed GapRecord.

    §3.6 asks whether the default-deny reader needs new logic for seams. It does not: the refusal
    shape is identical. A reader that denies across `duration is None` denies across both.
    """
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    seam = ledger.open_seam(cause="PROCESS_RESTART", prior_run_id="a", resumed_run_id="b",
                            prior_last_frame_utc="2026-08-05T01:00:00+00:00")
    assert seam.resolved is False
    assert seam.duration_seconds is None, "an open seam has NO measured width — never zero"
    assert ledger.manifest.open_seams == [seam]
    assert ledger.progress()["open_seams"] == 1


def test_seam_duration_is_the_measured_true_duration(tmp_path):
    """Duration = resumed first frame − prior last frame. Measured at both ends, never estimated."""
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    seam = ledger.open_seam(cause="POLICY_SHUTDOWN", prior_run_id="a", resumed_run_id="b",
                            prior_last_frame_utc="2026-08-05T01:00:00+00:00")
    ledger.close_seam(seam, "2026-08-05T01:42:30+00:00")

    assert seam.resolved is True
    assert seam.duration_seconds == pytest.approx(42 * 60 + 30)
    # And it survives a reload from disk — the record, not the object, is the evidence.
    reloaded = CorpusLedger(root=tmp_path, corpus_id="c")
    assert reloaded.manifest.seams[0].duration_seconds == pytest.approx(2550.0)
    assert reloaded.manifest.seams[0].cause == "POLICY_SHUTDOWN"


# ── §3.7 cumulative accounting ────────────────────────────────────────────────────────────────

def test_cumulative_hours_sum_across_runs_and_subtract_gap_time(tmp_path):
    """Coverage is frame-span MINUS recorded in-run gap time, summed over runs.

    A gap is a window with no data; crediting it as coverage would claim hours the corpus does not
    have. The seam between runs is excluded by construction — it was never inside anyone's span.
    """
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    ledger.add_run(RunRecord(
        run_id="r1", start_utc="2026-08-05T00:00:00+00:00",
        first_frame_utc="2026-08-05T00:00:00+00:00",
        last_frame_utc="2026-08-05T02:00:00+00:00",     # 2h span
        gap_seconds=600.0,                               # minus 10 min of recorded gap
        finalized=True,
    ))
    ledger.add_run(RunRecord(
        run_id="r2", start_utc="2026-08-05T03:00:00+00:00",
        first_frame_utc="2026-08-05T03:00:00+00:00",
        last_frame_utc="2026-08-05T04:00:00+00:00",     # 1h span, no gaps
        finalized=True,
    ))
    seam = ledger.open_seam(cause="PROCESS_RESTART", prior_run_id="r1", resumed_run_id="r2",
                            prior_last_frame_utc="2026-08-05T02:00:00+00:00")
    ledger.close_seam(seam, "2026-08-05T03:00:00+00:00")

    # 2h span − 10 min gap = 6600 s, plus a clean 1h = 3600 s  ->  10200 s = 2.8333… h.
    # The 10 minutes are NOT coverage: they are a recorded window with no data.
    expected = (2 * 3600 - 600) + 3600           # 10200 s
    assert ledger.manifest.cumulative_seconds == pytest.approx(expected)
    assert ledger.manifest.cumulative_hours == pytest.approx(10200 / 3600)

    prog = ledger.progress()
    assert prog["cumulative_covered_hours"] == pytest.approx(10200 / 3600, abs=1e-4)
    assert prog["remaining_covered_hours"] == pytest.approx(
        CORPUS_TARGET_HOURS - 10200 / 3600, abs=1e-4)
    assert prog["seam_count"] == 1
    assert prog["seam_causes"] == ["PROCESS_RESTART"]
    assert prog["complete"] is False
    # The seam's own hour is reported but NOT counted as coverage.
    assert prog["seam_seconds"] == pytest.approx(3600.0)


def test_covered_hours_are_labelled_distinctly_from_elapsed_wall_hours(tmp_path):
    """The target is COVERED data time, not elapsed wall-clock — and the two must never be
    confusable by a later reader.

    Reaching 24 COVERED hours always takes MORE than 24 wall-clock hours, by exactly the excluded
    gap + seam time. A reader who mistook one for the other would declare the corpus complete
    early — the most damaging misreading available here — so the distinction is carried in the KEY
    NAMES and in strings that travel with the data, not only in documentation.
    """
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    ledger.add_run(RunRecord(
        run_id="r1", start_utc="2026-08-05T00:00:00+00:00",
        first_frame_utc="2026-08-05T00:00:00+00:00",
        last_frame_utc="2026-08-05T01:00:00+00:00",      # 1h span
        gap_seconds=600.0,                                # minus 10 min gap -> 50 min covered
        finalized=True,
    ))
    ledger.add_run(RunRecord(
        run_id="r2", start_utc="2026-08-05T02:00:00+00:00",
        first_frame_utc="2026-08-05T02:00:00+00:00",
        last_frame_utc="2026-08-05T03:00:00+00:00",      # 1h span, clean
        finalized=True,
    ))
    seam = ledger.open_seam(cause="OPERATOR_STOP", prior_run_id="r1", resumed_run_id="r2",
                            prior_last_frame_utc="2026-08-05T01:00:00+00:00")
    ledger.close_seam(seam, "2026-08-05T02:00:00+00:00")   # a 1h seam

    prog = ledger.progress()

    # COVERED: 50 min + 60 min = 1.8333 h
    assert prog["cumulative_covered_hours"] == pytest.approx(110 / 60, abs=1e-4)
    # ELAPSED: 00:00 -> 03:00 = 3.0 h wall clock
    assert prog["elapsed_wall_hours"] == pytest.approx(3.0, abs=1e-4)
    # The difference is fully accounted for, not hand-waved: 10 min gap + 60 min seam.
    assert prog["excluded_in_run_gap_hours"] == pytest.approx(10 / 60, abs=1e-4)
    assert prog["excluded_seam_hours"] == pytest.approx(1.0, abs=1e-4)
    assert (prog["cumulative_covered_hours"] + prog["excluded_in_run_gap_hours"]
            + prog["excluded_seam_hours"]) == pytest.approx(prog["elapsed_wall_hours"], abs=1e-3)

    # COVERED is strictly LESS than elapsed whenever any gap or seam exists.
    assert prog["cumulative_covered_hours"] < prog["elapsed_wall_hours"]

    # The old ambiguous key names must be GONE — a stale reader should KeyError loudly rather than
    # silently read the wrong number.
    assert "cumulative_hours" not in prog
    assert "remaining_hours" not in prog
    assert "target_hours" not in prog

    # And the distinction travels WITH the data.
    assert "not elapsed wall-clock" in prog["metric"].lower()
    assert "not the target" in prog["not_the_metric"].lower()


def test_a_partial_trailing_segment_counts_by_its_measured_span(tmp_path):
    """An hour boundary is an ARCHIVAL artifact, not an epistemic one.

    A run that ends 40 minutes into its segment contributes 40 minutes, not zero. Refusing to count
    it would UNDERSTATE real captured data, which §0.4 forbids as firmly as overstating.
    """
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    ledger.add_run(RunRecord(
        run_id="r1", start_utc="2026-08-05T00:00:00+00:00",
        first_frame_utc="2026-08-05T00:00:00+00:00",
        last_frame_utc="2026-08-05T00:40:00+00:00",
        finalized=True,
    ))
    assert ledger.manifest.cumulative_hours == pytest.approx(40 / 60)


def test_target_completion_is_reported(tmp_path):
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    ledger.add_run(RunRecord(
        run_id="r1", start_utc="2026-08-05T00:00:00+00:00",
        first_frame_utc="2026-08-05T00:00:00+00:00",
        last_frame_utc="2026-08-06T00:00:00+00:00",       # exactly 24h
        finalized=True,
    ))
    assert ledger.manifest.complete is True
    assert ledger.progress()["remaining_covered_hours"] == pytest.approx(0.0)


# ── §3.5 the manifest spans the corpus ────────────────────────────────────────────────────────

def test_manifest_spans_every_run_and_hashes_every_segment(tmp_path):
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    for run_id in ("r1", "r2"):
        ledger.add_run(RunRecord(
            run_id=run_id, start_utc="2026-08-05T00:00:00+00:00",
            first_frame_utc="2026-08-05T00:00:00+00:00",
            last_frame_utc="2026-08-05T01:00:00+00:00",
            segments=[SegmentRecord(
                filename=f"corpus_H_{run_id}.jsonl", sha256="a" * 64, frame_count=10,
                size_bytes=100, compressed=True, start_utc="", end_utc="", run_id=run_id,
            )],
            finalized=True,
        ))
    data = json.loads(ledger.manifest_path.read_text(encoding="utf-8"))
    assert [r["run_id"] for r in data["runs"]] == ["r1", "r2"]
    all_segments = [s for r in data["runs"] for s in r["segments"]]
    assert len(all_segments) == 2
    assert all(len(s["sha256"]) == 64 for s in all_segments)
    assert all(s["run_id"] for s in all_segments), "each segment names the run that produced it"
    assert data["progress"]["cumulative_covered_hours"] == pytest.approx(2.0)


# ── reconciliation: what a killed process leaves behind ───────────────────────────────────────

def test_reconciled_run_is_marked_unfinalized_with_post_hoc_hashes(tmp_path):
    """A run whose process was SIGKILLed is recovered from disk — and LABELED as recovered.

    Its hours are real and must be counted (runs `20260729044021` and `20260730152029` both died
    this way with every frame on disk). But its segment hashes were computed at reconciliation, not
    at close, so they attest only what the file contains NOW. `hashed_at_capture=False` and
    `finalized=False` keep that distinction visible instead of laundering it into at-capture
    provenance.
    """
    run_dir = tmp_path / "c" / "r_killed"
    _write_segment(run_dir, "corpus_H_20260805T00Z.jsonl",
                   ["2026-08-05T00:00:00+00:00", "2026-08-05T00:30:00+00:00"])
    _write_gap_ledger(run_dir, [12.5])

    rec = reconcile_run_from_disk(run_dir, "r_killed")
    assert rec.finalized is False, "a reconciled run must never claim to have finalized itself"
    assert rec.segments and all(s.hashed_at_capture is False for s in rec.segments)
    assert all(len(s.sha256) == 64 for s in rec.segments)
    assert rec.first_frame_utc == "2026-08-05T00:00:00+00:00"
    assert rec.last_frame_utc == "2026-08-05T00:30:00+00:00"
    assert rec.gap_seconds == pytest.approx(12.5)
    assert rec.covered_seconds == pytest.approx(30 * 60 - 12.5)


def test_reconcile_folds_killed_runs_into_the_meter_but_keeps_finalized_ones(tmp_path):
    """Reconciliation must not overwrite a self-finalized record with a weaker reconstruction."""
    ledger = CorpusLedger(root=tmp_path, corpus_id="c", host="H")
    good_dir = ledger.dir / "r_good"
    _write_segment(good_dir, "corpus_H_20260805T00Z.jsonl", ["2026-08-05T00:00:00+00:00"])
    ledger.add_run(RunRecord(
        run_id="r_good", start_utc="2026-08-05T00:00:00+00:00",
        first_frame_utc="2026-08-05T00:00:00+00:00",
        last_frame_utc="2026-08-05T01:00:00+00:00", finalized=True,
    ))
    killed_dir = ledger.dir / "r_killed"
    _write_segment(killed_dir, "corpus_H_20260805T02Z.jsonl",
                   ["2026-08-05T02:00:00+00:00", "2026-08-05T02:30:00+00:00"])

    reconciled = ledger.reconcile()
    assert reconciled == ["r_killed"], "only the unfinalized run is rebuilt"
    assert ledger.get_run("r_good").finalized is True
    assert ledger.get_run("r_good").last_frame_utc == "2026-08-05T01:00:00+00:00"
    assert ledger.progress()["unfinalized_runs"] == ["r_killed"]
    assert ledger.manifest.cumulative_hours == pytest.approx(1.5)


def test_incomplete_gap_is_counted_as_a_deficit_not_smoothed(tmp_path):
    """An opened-but-never-closed gap contributes no duration but IS reported as incomplete."""
    run_dir = tmp_path / "r"
    run_dir.mkdir(parents=True)
    _write_gap_ledger(run_dir, [5.0, None])       # one closed, one left open
    summary = gap_summary(run_dir / "gap_ledger.json")
    assert summary["gap_count"] == 2
    assert summary["gap_seconds"] == pytest.approx(5.0)
    assert summary["incomplete_gaps"] == 1
    assert summary["terminal_gaps"] == 0


def test_a_terminal_gap_is_complete_not_a_ledger_deficit(tmp_path):
    """A breaker-tripped gap is COMPLETE by construction — a KNOWN open-ended gap.

    Real case: run `20260729190849` ended on a breaker trip, so its gap is terminal. Counting that
    as an "incomplete ledger" would report the breaker doing its job as a fault, and would make a
    genuinely deficient ledger indistinguishable from a clean STOP. It contributes no duration
    either — a terminal gap has no measured width, and inventing one would smooth it.
    """
    run_dir = tmp_path / "r"
    run_dir.mkdir(parents=True)
    (run_dir / "gap_ledger.json").write_text("\n".join([
        json.dumps({"event": "run_start", "run_wall_anchor": "2026-08-05T00:00:00+00:00"}),
        json.dumps({"event": "open", "gap_id": 0, "cause": "VENUE_DISCONNECT",
                    "reason_code": "VENUE_CONNECTION_CLOSED", "duration_s": None}),
        json.dumps({"event": "terminal", "gap_id": 0, "cause": "VENUE_DISCONNECT",
                    "reason_code": "RECONNECT_CIRCUIT_BREAKER_TRIPPED", "duration_s": None}),
    ]) + "\n", encoding="utf-8")

    summary = gap_summary(run_dir / "gap_ledger.json")
    assert summary["gap_count"] == 1
    assert summary["terminal_gaps"] == 1
    assert summary["incomplete_gaps"] == 0, (
        "a breaker-terminal gap is a KNOWN open-ended gap, not a ledger integrity deficit"
    )
    assert summary["gap_seconds"] == pytest.approx(0.0)


def test_torn_trailing_frame_is_skipped_not_guessed(tmp_path):
    """A half-written final line (the process died mid-write) is NOT a measurement.

    The reader steps back to the last intact frame rather than inventing a bound from a torn line.
    """
    run_dir = tmp_path / "r"
    run_dir.mkdir(parents=True)
    path = _write_segment(run_dir, "corpus_H_20260805T00Z.jsonl",
                          ["2026-08-05T00:00:00+00:00", "2026-08-05T00:10:00+00:00"])
    with open(path, "a", encoding="utf-8") as f:
        f.write('{"timestamp": "2026-08-05T00:20:00+0')      # torn write

    first, last = run_frame_bounds(run_dir)
    assert first == "2026-08-05T00:00:00+00:00"
    assert last == "2026-08-05T00:10:00+00:00", "the torn line must not become the measured bound"


# ── §3.1 the layout ───────────────────────────────────────────────────────────────────────────

def test_corpus_id_groups_runs_structurally(tmp_path):
    """A run cannot belong to a corpus without living inside that corpus's directory."""
    ledger = CorpusLedger(root=tmp_path, corpus_id="corpus_X", host="H")
    assert ledger.dir == tmp_path / "corpus_X"
    assert ledger.run_dir("run_1") == tmp_path / "corpus_X" / "run_1"
    assert ledger.manifest_path.parent == ledger.dir
    assert ledger.seam_ledger_path.parent == ledger.dir
