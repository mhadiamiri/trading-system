"""
WO-046 §4 — THE DEFAULT-DENY CORPUS READER.

D20, the ruling under test, verbatim:

    "The guarantee moves from 'every consumer remembers to check metadata' (vigilance, 0-for-4)
     to 'the only way to get gap-spanning data is to have written code that asked for it'
     (mechanical)."

FIXTURES ARE SYNTHETIC AND IN-REPO (§4 requirement): deterministic, always runnable, and with no
dependency on the 700 MB `corpus_20260805`. The real-corpus validation is EVIDENCE in the report,
never a committed test — a test that needs the artifact would be unrunnable for anyone who does not
have it, and would couple the suite to a file it must never write to.

Every fixture is built from the DECLARED WO-014c-2 schema (verified field-for-field against the real
ledger in §1), not from whatever the capture happened to write.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from trading.data.corpus_reader import (
    Acknowledge,
    CorpusReadRefused,
    CorpusReader,
    LedgerIncomplete,
)

UTC = timezone.utc
ANCHOR_WALL = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
ANCHOR_MONO = 1000.0


def _wall(offset_seconds):
    return ANCHOR_WALL + timedelta(seconds=offset_seconds)


def _build_corpus(tmp_path, gaps=(), seams=(), run_span=(0.0, 3600.0), incomplete=0,
                  run_id="run_a", corpus_id="corpus_test"):
    """Write a synthetic corpus in the DECLARED schema shape. Returns the corpus dir.

    `gaps` entries are (gap_id, cause, reason_code, open_offset_s, close_offset_s|None).
    A None close means UNRESOLVED/TERMINAL — read as +infinity by the reader.
    """
    corpus = tmp_path / corpus_id
    run = corpus / run_id
    run.mkdir(parents=True)

    lines = [json.dumps({
        "event": "run_start",
        "run_wall_anchor": ANCHOR_WALL.isoformat(),
        "run_monotonic_anchor": ANCHOR_MONO,
        "run_start_monotonic": ANCHOR_MONO + run_span[0],
        "venue": "kraken_mainnet", "mode": "live",
    })]
    for gid, cause, code, open_s, close_s in gaps:
        base = {
            "gap_id": gid, "cause": cause, "reason_code": code,
            "open_monotonic": ANCHOR_MONO + open_s,
            "close_monotonic": None if close_s is None else ANCHOR_MONO + close_s,
            "resumed": close_s is not None, "terminal": close_s is None,
            "duration_s": None if close_s is None else close_s - open_s,
            "last_validated_book": None, "retry_ladder": [], "detail": f"{cause} fixture",
            "open_server_ts": None,
        }
        lines.append(json.dumps({"event": "open", **base}))
        lines.append(json.dumps({
            "event": "terminal" if close_s is None else "resolved", **base}))
    lines.append(json.dumps({
        "event": "run_end",
        "run_end_monotonic": ANCHOR_MONO + run_span[1],
        "frames_captured": 1000, "gaps_detected": len(gaps), "incomplete": incomplete,
    }))
    (run / "gap_ledger.json").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if seams:
        seam_lines = []
        for sid, cause, start_s, end_s in seams:
            rec = {
                "seam_id": sid, "cause": cause, "reason_code": cause,
                "prior_run_id": run_id, "resumed_run_id": f"{run_id}_2",
                "prior_last_frame_utc": _wall(start_s).isoformat(),
                "resumed_first_frame_utc": _wall(end_s).isoformat() if end_s is not None else "",
                "resolved": end_s is not None,
                "duration_seconds": None if end_s is None else end_s - start_s,
                "detail": "fixture seam",
            }
            seam_lines.append(json.dumps({"event": "resolved", **rec}))
        (corpus / "seam_ledger.jsonl").write_text("\n".join(seam_lines) + "\n", encoding="utf-8")
    return corpus


# ── §4.1 THE D20 PROOF — refusal and preservation in ONE test (S13) ───────────────────────────

def test_d20_refusal_and_preservation_in_one_test(tmp_path):
    """S13: both halves local and direct, so neither can drift from the other.

    REFUSAL      — a window spanning a KNOWN gap, unacknowledged, REFUSES and NAMES the gap.
    PRESERVATION — the same window WITH the matching acknowledgment SERVES.
    """
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "KEEPALIVE_RECONNECT", "HEARTBEAT_ABSENCE", 100.0, 110.0),
    ])
    reader = CorpusReader(corpus)

    # ── REFUSAL half ─────────────────────────────────────────────────────────────────────
    with pytest.raises(CorpusReadRefused) as exc:
        reader.read_window(_wall(50), _wall(200))

    msg = str(exc.value)
    assert "CORPUS_READ_REFUSED" in msg
    # The refusal NAMES the gap's IDENTITY — a bare "denied" teaches nothing.
    assert "run:run_a/gap:0" in msg
    assert "KEEPALIVE_RECONNECT" in msg
    assert "HEARTBEAT_ABSENCE" in msg
    assert "10.000000s" in msg, f"the refusal must state the gap's duration; got:\n{msg}"
    assert len(exc.value.discontinuities) == 1
    assert exc.value.discontinuities[0].identity == "run:run_a/gap:0"

    # ── PRESERVATION half (the dual, same window, same reader) ───────────────────────────
    window = reader.read_window(_wall(50), _wall(200), acknowledging=[
        Acknowledge("KEEPALIVE_RECONNECT", max_duration_seconds=30.0,
                    reason="sub-minute reconnects are acceptable for this analysis"),
    ])
    assert len(window.segments) == 2, "an acknowledged read is SEGMENTED, never spliced"
    assert window.continuous is False
    assert [s.duration_seconds for s in window.segments] == [50.0, 90.0]
    # Coverage counts the SEGMENTS, not the requested span — the gap is absence of data.
    assert window.covered_seconds == 140.0
    assert (window.requested_end_utc - window.requested_start_utc).total_seconds() == 150.0


def test_continuous_data_across_a_gap_is_not_expressible(tmp_path):
    """The D20 mechanism itself: even an ACKNOWLEDGED window offers no concatenated series.

    A caller who wants one series must join the segments in its OWN code, visibly, where a reviewer
    can see the splice. If `CorpusWindow` grew a `.frames`/`.series`/`.concat()`, the guarantee
    would be gone — so the absence is asserted, not assumed.
    """
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "VENUE_DISCONNECT", "VENUE_CONNECTION_CLOSED", 100.0, 110.0),
    ])
    window = CorpusReader(corpus).read_window(_wall(50), _wall(200), acknowledging=[
        Acknowledge("VENUE_DISCONNECT"),
    ])
    for forbidden in ("frames", "series", "concat", "flatten", "as_continuous"):
        assert not hasattr(window, forbidden), (
            f"CorpusWindow.{forbidden} would make gap-spanning data expressible in one call"
        )


def test_a_window_clear_of_every_gap_serves_without_acknowledgment(tmp_path):
    """The dual at the API level: default-deny must not mean default-refuse."""
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "KEEPALIVE_RECONNECT", "HEARTBEAT_ABSENCE", 100.0, 110.0),
    ])
    window = CorpusReader(corpus).read_window(_wall(200), _wall(300))
    assert window.continuous is True
    assert len(window.segments) == 1
    assert window.covered_seconds == 100.0
    assert window.acknowledged == ()


# ── §4.2 ZERO-DURATION FIXTURE (precondition 5, hard spec) ────────────────────────────────────

def test_a_zero_duration_gap_is_a_real_gap_and_refuses(tmp_path):
    """A gap whose open == close. It has no width; it is still a REAL gap.

    WO-022 §3.2 / precondition 5: a zero-duration entry is NEVER filtered as noise. A reader that
    launders an honest ledger is default-deny's failure mode arriving one layer downstream.
    """
    corpus = _build_corpus(tmp_path, gaps=[
        (7, "CHECKSUM_RESYNC", "CHECKSUM_RESYNC", 100.0, 100.0),   # open == close
    ])
    reader = CorpusReader(corpus)
    assert reader.gaps[0].duration_seconds == 0.0

    with pytest.raises(CorpusReadRefused) as exc:
        reader.read_window(_wall(50), _wall(150))
    assert "run:run_a/gap:7" in str(exc.value)


@pytest.mark.parametrize("start_s,end_s,label", [
    (50.0, 100.0, "window END equals the gap instant"),
    (100.0, 150.0, "window START equals the gap instant"),
    (100.0, 100.0, "window IS the gap instant (degenerate)"),
])
def test_inclusive_bounds_a_boundary_touching_the_gap_still_refuses(tmp_path, start_s, end_s,
                                                                    label):
    """INCLUSIVE bounds, proved at the boundary (§4.2).

    Under the STRICT half-open test sketched in WO-014c-2 §1.3 (`t0 < close AND open < t1`) none of
    these would intersect a zero-width gap, and a window touching the gap's exact instant would be
    served as continuous. The later hard spec rules inclusive; this pins it at each boundary.
    """
    corpus = _build_corpus(tmp_path, gaps=[
        (7, "CHECKSUM_RESYNC", "CHECKSUM_RESYNC", 100.0, 100.0),
    ])
    with pytest.raises(CorpusReadRefused):
        CorpusReader(corpus).read_window(_wall(start_s), _wall(end_s))


def test_inclusive_bounds_hold_for_a_nonzero_gap_too(tmp_path):
    """The boundary rule is not a zero-width special case: touching either edge refuses."""
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "VENUE_DISCONNECT", "VENUE_CONNECTION_CLOSED", 100.0, 110.0),
    ])
    reader = CorpusReader(corpus)
    for start_s, end_s in ((50.0, 100.0), (110.0, 200.0)):
        with pytest.raises(CorpusReadRefused):
            reader.read_window(_wall(start_s), _wall(end_s))
    # Strictly clear of both edges -> serves.
    assert reader.read_window(_wall(111), _wall(200)).continuous is True


# ── §4.3 SEAM-SPANNING (D45: a seam is a gap with a bigger cause code) ────────────────────────

def test_a_seam_refuses_by_default_and_serves_when_acknowledged(tmp_path):
    """D45 proved by DEMONSTRATION: the seam goes through the identical machinery.

    No seam-specific branch exists in the refusal path — the reader normalises gaps and seams onto
    one wall-clock timeline and then cannot tell them apart except by provenance.
    """
    corpus = _build_corpus(tmp_path, gaps=[], seams=[
        (0, "PROCESS_RESTART", 500.0, 1000.0),
    ])
    reader = CorpusReader(corpus)
    assert len(reader.seams) == 1
    assert reader.seams[0].duration_seconds == 500.0

    with pytest.raises(CorpusReadRefused) as exc:
        reader.read_window(_wall(400), _wall(1100))
    assert "corpus/seam:0" in str(exc.value)
    assert "PROCESS_RESTART" in str(exc.value)

    window = reader.read_window(_wall(400), _wall(1100), acknowledging=[
        Acknowledge("PROCESS_RESTART", max_duration_seconds=600.0,
                    reason="a declared inter-run seam is acceptable for this analysis"),
    ])
    assert len(window.segments) == 2
    assert [s.duration_seconds for s in window.segments] == [100.0, 100.0]


def test_seams_and_gaps_share_one_refusal_path(tmp_path):
    """Both kinds in one window: one refusal naming both, no separate handling."""
    corpus = _build_corpus(tmp_path,
                           gaps=[(0, "VENUE_DISCONNECT", "VENUE_CONNECTION_CLOSED", 100.0, 110.0)],
                           seams=[(0, "OPERATOR_STOP", 500.0, 600.0)])
    with pytest.raises(CorpusReadRefused) as exc:
        CorpusReader(corpus).read_window(_wall(50), _wall(700))
    msg = str(exc.value)
    assert "run:run_a/gap:0" in msg and "corpus/seam:0" in msg
    assert len(exc.value.discontinuities) == 2


# ── §4.4 CLASS-AWARENESS ─────────────────────────────────────────────────────────────────────

def test_acknowledging_class_a_does_not_admit_class_b(tmp_path):
    """The core of §2.2. An acknowledgment is a statement about a CAUSE CLASS, not a mute button."""
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "KEEPALIVE_RECONNECT", "HEARTBEAT_ABSENCE", 100.0, 110.0),
        (1, "HOST_SUSPEND", "HOST_SUSPEND", 300.0, 400.0),
    ])
    reader = CorpusReader(corpus)

    # Acknowledging keepalive does NOT admit the host suspend.
    with pytest.raises(CorpusReadRefused) as exc:
        reader.read_window(_wall(50), _wall(500),
                           acknowledging=[Acknowledge("KEEPALIVE_RECONNECT")])
    remaining = [d.cause for d in exc.value.discontinuities]
    assert remaining == ["HOST_SUSPEND"], f"only the unacknowledged class should remain: {remaining}"

    # Both named -> serves, segmented into three.
    window = reader.read_window(_wall(50), _wall(500), acknowledging=[
        Acknowledge("KEEPALIVE_RECONNECT"), Acknowledge("HOST_SUSPEND"),
    ])
    assert len(window.segments) == 3


def test_a_duration_bound_is_part_of_the_acknowledgment(tmp_path):
    """Acknowledging a class up to N seconds does not admit a longer instance of that class."""
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "KEEPALIVE_RECONNECT", "HEARTBEAT_ABSENCE", 100.0, 400.0),   # 300 s
    ])
    reader = CorpusReader(corpus)
    with pytest.raises(CorpusReadRefused):
        reader.read_window(_wall(50), _wall(500), acknowledging=[
            Acknowledge("KEEPALIVE_RECONNECT", max_duration_seconds=5.0),
        ])
    assert reader.read_window(_wall(50), _wall(500), acknowledging=[
        Acknowledge("KEEPALIVE_RECONNECT", max_duration_seconds=600.0),
    ]).covered_seconds == 150.0


def test_an_acknowledgment_naming_an_impossible_class_fails_loudly(tmp_path):
    """A typo'd or invented cause accepts nothing while LOOKING like it accepts something."""
    with pytest.raises(ValueError, match="ACKNOWLEDGMENT_CAUSE_UNDECLARED"):
        Acknowledge("KEEPALIVE_RECONNET")            # transposed letters
    with pytest.raises(ValueError, match="ACKNOWLEDGMENT_CAUSE_UNDECLARED"):
        Acknowledge("*")                              # no wildcard exists


def test_there_is_no_blanket_acknowledgment(tmp_path):
    """Every declared cause must be named individually — no single Acknowledge admits them all."""
    from trading.data.corpus_reader import ALL_DISCONTINUITY_CAUSES
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "KEEPALIVE_RECONNECT", "HEARTBEAT_ABSENCE", 100.0, 110.0),
        (1, "VENUE_DISCONNECT", "VENUE_CONNECTION_CLOSED", 200.0, 210.0),
    ])
    reader = CorpusReader(corpus)
    for cause in ALL_DISCONTINUITY_CAUSES:
        acks = [Acknowledge(cause)]
        hits = reader.intersecting(_wall(50), _wall(300))
        admitted = [d for d in hits if any(a.accepts(d) for a in acks)]
        assert len(admitted) <= 1, f"Acknowledge({cause!r}) admitted more than its own class"


# ── open-ended discontinuities (default-deny falling out of None-means-+inf) ──────────────────

def test_an_open_ended_gap_denies_every_window_from_its_open_onward(tmp_path):
    """WO-014c-2 §1.3(3): close=None reads as +infinity, so a breaker-terminal run denies
    everything after the trip until a human explicitly acknowledges the truncation."""
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "VENUE_DISCONNECT", "RECONNECT_CIRCUIT_BREAKER_TRIPPED", 100.0, None),
    ])
    reader = CorpusReader(corpus)
    assert reader.gaps[0].open_ended is True
    assert reader.gaps[0].duration_seconds is None, "open-ended has NO duration — not zero"

    for start_s, end_s in ((50.0, 200.0), (5000.0, 6000.0), (100.0, 100.0)):
        with pytest.raises(CorpusReadRefused):
            reader.read_window(_wall(start_s), _wall(end_s))
    # A window entirely BEFORE the open still serves.
    assert reader.read_window(_wall(10), _wall(99)).continuous is True


def test_an_open_ended_gap_needs_its_own_deliberate_acknowledgment(tmp_path):
    """A duration bound cannot speak to a window with no measured width, so accepting one is a
    separate, explicit act — not something a generous max_duration_seconds sweeps up."""
    corpus = _build_corpus(tmp_path, gaps=[
        (0, "VENUE_DISCONNECT", "RECONNECT_CIRCUIT_BREAKER_TRIPPED", 100.0, None),
    ])
    reader = CorpusReader(corpus)
    with pytest.raises(CorpusReadRefused):
        reader.read_window(_wall(50), _wall(200), acknowledging=[
            Acknowledge("VENUE_DISCONNECT", max_duration_seconds=10_000_000.0),
        ])
    window = reader.read_window(_wall(50), _wall(200), acknowledging=[
        Acknowledge("VENUE_DISCONNECT", accept_open_ended=True,
                    reason="the truncated tail is understood and accepted"),
    ])
    assert len(window.segments) == 1, "nothing after an open-ended gap exists to serve"
    assert window.segments[0].duration_seconds == 50.0


# ── ledger completeness (WO-014c-2 §1.3(4)) ──────────────────────────────────────────────────

def test_an_incomplete_ledger_denies_everything(tmp_path):
    """"No gap here" is only trustworthy against a ledger known to hold EVERY gap of the run."""
    corpus = _build_corpus(tmp_path, gaps=[], incomplete=1)
    reader = CorpusReader(corpus)
    assert reader.incomplete_runs == ("run_a",)
    with pytest.raises(LedgerIncomplete) as exc:
        reader.read_window(_wall(10), _wall(20))
    assert "not known-COMPLETE" in str(exc.value)


def test_a_torn_ledger_line_marks_the_run_incomplete(tmp_path):
    """A half-written JSONL line (the capture died mid-write) is not data, and it means the ledger
    cannot be called total — so the run is denied rather than partially trusted."""
    corpus = _build_corpus(tmp_path, gaps=[])
    ledger = corpus / "run_a" / "gap_ledger.json"
    with open(ledger, "a", encoding="utf-8") as f:
        f.write('{"event": "open", "gap_id": 9, "open_mono')      # torn
    reader = CorpusReader(corpus)
    assert "run_a" in reader.incomplete_runs
    with pytest.raises(LedgerIncomplete):
        reader.read_window(_wall(10), _wall(20))


# ── §4.5 READ-ONLY ───────────────────────────────────────────────────────────────────────────

def test_the_reader_writes_nothing(tmp_path):
    """Construction, querying and reading must not create, modify or delete anything."""
    import hashlib

    corpus = _build_corpus(tmp_path,
                           gaps=[(0, "KEEPALIVE_RECONNECT", "HEARTBEAT_ABSENCE", 100.0, 110.0)],
                           seams=[(0, "PROCESS_RESTART", 500.0, 600.0)])

    def digest():
        h = hashlib.sha256()
        for p in sorted(corpus.rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(corpus)).encode())
                h.update(p.read_bytes())
        return h.hexdigest()

    before = digest()
    reader = CorpusReader(corpus)
    reader.coverage()
    reader.intersecting(_wall(0), _wall(3600))
    with pytest.raises(CorpusReadRefused):
        reader.read_window(_wall(50), _wall(700))
    reader.read_window(_wall(50), _wall(700), acknowledging=[
        Acknowledge("KEEPALIVE_RECONNECT"), Acknowledge("PROCESS_RESTART"),
    ])
    assert digest() == before, "the reader must not modify the corpus it reads"


def test_the_reader_module_opens_nothing_for_writing():
    """Mechanical read-only enforcement (the WO-032 evidence-write-boundary precedent).

    Scans the module source for write-mode file access. A reader that acquires a write path later
    fails here rather than being discovered by a corrupted corpus.
    """
    import re
    from pathlib import Path as _P
    import trading.data.corpus_reader as mod

    src = _P(mod.__file__).read_text(encoding="utf-8")
    # Strip the docstrings/comments so prose about writing does not trip the scan.
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for forbidden in (r'open\([^)]*["\'][waxr]?\+', r'open\([^)]*["\']w', r'open\([^)]*["\']a',
                      r'\.write_text\(', r'\.write_bytes\(', r'\.mkdir\(', r'\.unlink\(',
                      r'\.rmdir\(', r'shutil\.'):
        assert not re.search(forbidden, code), (
            f"corpus_reader.py contains a WRITE path matching {forbidden!r} — the reader must "
            f"never write to the corpus it reads"
        )


def test_the_readonly_coverage_query_reports_without_writing(tmp_path):
    """§6: the read-only replacement for --progress (which calls reconcile() and SAVES)."""
    corpus = _build_corpus(tmp_path,
                           gaps=[(0, "KEEPALIVE_RECONNECT", "HEARTBEAT_ABSENCE", 100.0, 110.0)],
                           seams=[(0, "PROCESS_RESTART", 500.0, 600.0)])
    cov = CorpusReader(corpus).coverage()
    assert cov["read_only"] is True
    assert cov["gap_count"] == 1 and cov["seam_count"] == 1
    assert cov["gap_causes"] == ["KEEPALIVE_RECONNECT"]
    assert cov["seam_causes"] == ["PROCESS_RESTART"]
    assert "not elapsed wall-clock time" in cov["metric"]
    assert not (corpus / "CORPUS_MANIFEST.json").exists(), "coverage() must not create a manifest"
