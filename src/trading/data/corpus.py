"""
WO-044 §3 — CORPUS RESUME SUPPORT: one corpus-id, N runs, every seam labeled.

D45: "Every seam is a declared ledger record — this is MORE honest than one unbroken process, not
less." An in-run venue disconnect and an inter-run policy shutdown are the same epistemic object: a
bounded window with no data, a declared cause, and a TRUE duration. This module owns the half the
adapter's GapLedger cannot see — the window BETWEEN two processes — and the accounting that turns a
pile of runs into a single answerable question: how many labeled continuous hours do we have?

WHY THIS LIVES IN `src/` AND NOT IN `tools/`. The three seam causes are DECLARED reason codes
(`VALID_REASON_CODES["DATA"]`), and both vocabulary guards — `test_reason_code_vocabulary.py` and
`test_archive_readiness.py` — scan `src/` ONLY (`SRC = parents[1] / "src"`). A seam code emitted from
`tools/` would be declared-but-not-producible: invisible to the guard that exists to catch exactly
that, and WO-037 already caught one dead constant living in that blind spot. The seam writer is
production code because the vocabulary it emits is governed production vocabulary.

THE SEAM IS A GAP WITH A BIGGER CAUSE CODE (§3.6). Deliberately shaped to mirror `GapRecord`:
OPEN → RESOLVED, persisted write-through as JSONL events, an unresolved seam reading as +infinity so
it denies every later query by construction. A default-deny reader that already refuses across an
in-run gap needs NO new logic to refuse across a seam — it is the same object with a wider cause.

MEASURED, NEVER ESTIMATED (§3.3 / §0.4). A seam's duration is
    (first frame of the resumed run) − (last frame of the prior run)
and BOTH endpoints are read off real frames. The prior end comes from the last line of the prior
run's newest segment — which survives a `SIGKILL`, unlike a manifest written in a `finally` block
(runs `20260729044021` and `20260730152029` both died with no MANIFEST.json, and both still carry a
readable last frame). Reading a written frame is measurement. Interpolating from a run's intended
duration would be estimation, and §0.4 forbids it.

THE CAUSE IS DECLARED BY THE OPERATOR, NEVER INFERRED. A process cannot observe why it died: a
`SIGKILL` from a security policy, a manual stop, and a host crash are byte-identical from inside.
`CorpusLedger.open_seam` therefore REFUSES an undeclared cause rather than guessing one, because a
guessed cause is a smoothed seam and §0.4 forbids that too.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Optional


# The closed set of INTER-RUN seam causes (§3.3). Declared in VALID_REASON_CODES["DATA"] and
# prefix-free against the union of both governed vocabularies. These literals are what make the
# codes PRODUCIBLE to the src-only vocabulary scan; `open_seam` below is what makes them genuinely
# EMITTED, which is the property that actually matters (a constant alone is what WO-037 caught).
#   PROCESS_RESTART  — the capture process ended but the HOST stayed up (crash, kill, breaker STOP).
#   POLICY_SHUTDOWN  — the host was shut down or slept by a policy outside the run's control. This is
#                      the cause that ate two runs before the operator prerequisite was written.
#   OPERATOR_STOP    — a deliberate human stop. Honest and unremarkable; still a seam.
CORPUS_SEAM_CAUSES = (
    "PROCESS_RESTART",
    "POLICY_SHUTDOWN",
    "OPERATOR_STOP",
)

# The corpus target (§3.7 / §5.2). Cumulative, across every run of the corpus-id.
CORPUS_TARGET_HOURS = 24.0

# Directory layout (§3.1): captures/<root>/<corpus_id>/<run_id>/<segments + gap_ledger + PREFLIGHT>
# with the corpus-level manifest and seam ledger at the corpus_id level, one directory above the
# runs they span. Grouping is STRUCTURAL: a run cannot be written into a corpus without landing
# inside that corpus's directory, so "which corpus does this run belong to" is never a judgement.
CORPUS_MANIFEST_FILENAME = "CORPUS_MANIFEST.json"
SEAM_LEDGER_FILENAME = "seam_ledger.jsonl"
PREFLIGHT_FILENAME = "PREFLIGHT.json"

# The default segment naming. A corpus whose runs predate this scheme passes its own patterns —
# see `segment_paths`. Defined up here rather than beside that function because it is a default
# ARGUMENT of both `CorpusLedger.__init__` and the readers, and Python binds default arguments at
# definition time: declared below the class, the name does not exist when the class body runs.
DEFAULT_SEGMENT_PATTERNS = ("corpus_*.jsonl",)


class SeamCauseUndeclared(ValueError):
    """Raised when a resume is attempted without declaring WHY the prior run ended.

    Not a convenience default: see the module docstring. The process cannot know, so it must ask.
    """


def _parse_utc(value: str) -> Optional[datetime]:
    """Parse an ISO-8601 UTC stamp, tolerating the trailing-Z form Kraken sends."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── RECORDS ───────────────────────────────────────────────────────────────────────────────────

@dataclass
class SegmentRecord:
    """One rotated hourly segment, hashed at close (§3.5). Mirrors WO-043's SegmentManifest so a
    per-run manifest lifts into the corpus manifest without a translation layer."""

    filename: str
    sha256: str
    frame_count: int
    size_bytes: int
    compressed: bool
    start_utc: str
    end_utc: str
    run_id: str = ""          # which run produced it — the corpus manifest spans runs, so it must say
    # PROVENANCE, not decoration. True = the hash was computed AT SEGMENT CLOSE by the capturing
    # process, so it attests the bytes as written. False = the hash was computed LATER, by
    # reconciliation over a file already at rest, and therefore attests only what the file contains
    # NOW — it cannot witness the interval between capture and hashing. A post-hoc hash is still
    # useful (it pins the file from here on) but it is NOT at-capture provenance, and conflating the
    # two is how an archive quietly loses the ability to say which of its own claims are witnessed.
    hashed_at_capture: bool = True

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "sha256": self.sha256,
            "frame_count": self.frame_count,
            "size_bytes": self.size_bytes,
            "compressed": self.compressed,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "run_id": self.run_id,
            "hashed_at_capture": self.hashed_at_capture,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SegmentRecord:
        return cls(
            filename=d["filename"], sha256=d["sha256"], frame_count=d["frame_count"],
            size_bytes=d["size_bytes"], compressed=d["compressed"],
            start_utc=d.get("start_utc", ""), end_utc=d.get("end_utc", ""),
            run_id=d.get("run_id", ""),
            hashed_at_capture=d.get("hashed_at_capture", True),
        )


@dataclass
class SeamRecord:
    """One INTER-RUN seam: the window between the prior run's last frame and this run's first.

    Shaped as GapRecord's sibling (§3.6). `resumed_first_frame_utc` empty and `resolved` False mean
    the seam is still OPEN — read as +infinity, so it intersects every later query and a default-deny
    reader denies across it. That makes "resumed but never emitted" LOUD BY CONSTRUCTION rather than
    by anyone remembering to check, which is the property the lead named best in the gap schema.
    """

    seam_id: int
    cause: str                       # one of CORPUS_SEAM_CAUSES — operator-declared, never inferred
    prior_run_id: str
    resumed_run_id: str
    prior_last_frame_utc: str        # measured: last line of the prior run's newest segment
    resumed_first_frame_utc: str = ""  # measured: first frame the resumed run writes
    resolved: bool = False
    detail: str = ""

    @property
    def duration_seconds(self) -> Optional[float]:
        """TRUE duration, or None while the seam is open. None is NOT zero: an open seam has no
        measured width yet, and reporting zero would be the smoothing §0.4 forbids."""
        start = _parse_utc(self.prior_last_frame_utc)
        end = _parse_utc(self.resumed_first_frame_utc)
        if start is None or end is None:
            return None
        return (end - start).total_seconds()

    def to_dict(self) -> dict:
        return {
            "seam_id": self.seam_id,
            "cause": self.cause,
            "reason_code": self.cause,      # the seam IS its reason code — one governed vocabulary
            "prior_run_id": self.prior_run_id,
            "resumed_run_id": self.resumed_run_id,
            "prior_last_frame_utc": self.prior_last_frame_utc,
            "resumed_first_frame_utc": self.resumed_first_frame_utc,
            "resolved": self.resolved,
            "duration_seconds": self.duration_seconds,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SeamRecord:
        return cls(
            seam_id=d["seam_id"], cause=d["cause"], prior_run_id=d["prior_run_id"],
            resumed_run_id=d["resumed_run_id"],
            prior_last_frame_utc=d.get("prior_last_frame_utc", ""),
            resumed_first_frame_utc=d.get("resumed_first_frame_utc", ""),
            resolved=d.get("resolved", False), detail=d.get("detail", ""),
        )


@dataclass
class RunRecord:
    """One run of the corpus. Carries its OWN preflight (§3.2) — no run inherits another's."""

    run_id: str
    start_utc: str
    end_utc: str = ""
    first_frame_utc: str = ""
    last_frame_utc: str = ""
    segments: list = field(default_factory=list)      # SegmentRecord
    gap_seconds: float = 0.0        # summed CLOSED in-run gap durations (from the gap ledger)
    gap_count: int = 0
    terminal_gaps: int = 0          # breaker-tripped: open-ended by construction, COMPLETE
    incomplete_gaps: int = 0        # opened but never closed — the ledger's own integrity deficit
    preflight: dict = field(default_factory=dict)     # this run's opening record (§3.2)
    finalized: bool = False         # False when the process died before writing its manifest

    @property
    def covered_seconds(self) -> float:
        """LABELED CONTINUOUS seconds this run contributes (§3.7).

        Measured frame-to-frame, MINUS the in-run gap time the ledger recorded. A gap is a window
        with no data; counting it as coverage would credit the corpus for hours it does not have.

        MEASURED FROM FRAMES, NOT FROM SEGMENT COMPLETENESS. An hourly segment boundary is an
        ARCHIVAL artifact (a rotation policy), not an epistemic one, so a partial trailing segment
        contributes its real measured span. Refusing to count a genuine 55-minute partial would
        UNDERSTATE real captured data, which §0.4 forbids in the same breath as overstating it.
        What disqualifies a run is missing PROVENANCE, never a tidy hour boundary — and provenance
        is judged in the manifest, not here.
        """
        start = _parse_utc(self.first_frame_utc)
        end = _parse_utc(self.last_frame_utc)
        if start is None or end is None:
            return 0.0
        span = (end - start).total_seconds()
        return max(0.0, span - self.gap_seconds)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "first_frame_utc": self.first_frame_utc,
            "last_frame_utc": self.last_frame_utc,
            "segments": [s.to_dict() for s in self.segments],
            "gap_seconds": self.gap_seconds,
            "gap_count": self.gap_count,
            "terminal_gaps": self.terminal_gaps,
            "incomplete_gaps": self.incomplete_gaps,
            "preflight": self.preflight,
            "finalized": self.finalized,
            "covered_seconds": self.covered_seconds,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RunRecord:
        return cls(
            run_id=d["run_id"], start_utc=d.get("start_utc", ""), end_utc=d.get("end_utc", ""),
            first_frame_utc=d.get("first_frame_utc", ""), last_frame_utc=d.get("last_frame_utc", ""),
            segments=[SegmentRecord.from_dict(s) for s in d.get("segments", [])],
            gap_seconds=d.get("gap_seconds", 0.0), gap_count=d.get("gap_count", 0),
            terminal_gaps=d.get("terminal_gaps", 0),
            incomplete_gaps=d.get("incomplete_gaps", 0), preflight=d.get("preflight", {}),
            finalized=d.get("finalized", False),
        )


@dataclass
class CorpusManifest:
    """The corpus-spanning manifest (§3.5): every segment of every run, each with its SHA-256, plus
    every inter-run seam as a first-class record. One file answers "what is this corpus made of"."""

    corpus_id: str
    host: str
    created_utc: str
    target_hours: float = CORPUS_TARGET_HOURS
    runs: list = field(default_factory=list)      # RunRecord
    seams: list = field(default_factory=list)     # SeamRecord

    # ── §3.7 cumulative-hours accounting: the progress meter ──────────────────────────────────
    @property
    def cumulative_seconds(self) -> float:
        return sum(r.covered_seconds for r in self.runs)

    @property
    def cumulative_hours(self) -> float:
        return self.cumulative_seconds / 3600.0

    @property
    def seam_count(self) -> int:
        return len(self.seams)

    @property
    def open_seams(self) -> list:
        """Seams with no measured close. Reported, never dropped — the same treatment
        `GapLedger.incomplete` gives an unclosed gap."""
        return [s for s in self.seams if not s.resolved]

    @property
    def seam_seconds(self) -> float:
        """Total measured seam time. NOT subtracted from cumulative (seams sit BETWEEN runs, so
        they were never inside anyone's covered span) — reported so the corpus's real wall-clock
        footprint is visible next to its labeled coverage."""
        return sum(s.duration_seconds or 0.0 for s in self.seams)

    @property
    def remaining_hours(self) -> float:
        return max(0.0, self.target_hours - self.cumulative_hours)

    @property
    def complete(self) -> bool:
        return self.cumulative_hours >= self.target_hours

    @property
    def gap_seconds(self) -> float:
        """Total in-run gap time EXCLUDED from coverage — reported, never hidden."""
        return sum(r.gap_seconds for r in self.runs)

    @property
    def elapsed_wall_seconds(self) -> float:
        """WALL-CLOCK span of the whole corpus: earliest first frame -> latest last frame.

        Includes every seam and every in-run gap. This is the number a human means by "how long has
        this been running", and it is NOT what the 24-hour target is measured against — which is
        precisely why it is reported alongside, under its own name.
        """
        firsts = [_parse_utc(r.first_frame_utc) for r in self.runs if r.first_frame_utc]
        lasts = [_parse_utc(r.last_frame_utc) for r in self.runs if r.last_frame_utc]
        firsts = [t for t in firsts if t is not None]
        lasts = [t for t in lasts if t is not None]
        if not firsts or not lasts:
            return 0.0
        return (max(lasts) - min(firsts)).total_seconds()

    def progress(self) -> dict:
        """The §3.7 answer, computable at ANY time from the committed artifacts alone.

        THE TARGET IS COVERED HOURS, NOT ELAPSED HOURS. Every key is named so the two cannot be
        confused by a later reader:

            cumulative_covered_hours = Σ over runs of (last_frame − first_frame) − in-run gap secs
            elapsed_wall_hours       = earliest first frame → latest last frame, seams included

        `covered` is what the 24-hour grant is measured against, and it is strictly LESS than
        elapsed whenever the corpus has any gap or seam at all — so reaching 24 COVERED hours
        always takes MORE than 24 wall-clock hours. A reader who mistakes one for the other would
        declare the corpus complete early, which is the single most damaging misreading available
        here. The `metric` and `not_the_metric` strings travel WITH the data so the distinction
        survives being copied into a report, a ticket, or a chat message.
        """
        covered = self.cumulative_hours
        elapsed = self.elapsed_wall_seconds / 3600.0
        return {
            "corpus_id": self.corpus_id,
            "runs": len(self.runs),

            # ── THE METRIC THE 24-HOUR TARGET IS MEASURED AGAINST ────────────────────────────
            "metric": (
                "cumulative_covered_hours = SUM over runs of (last_frame - first_frame) MINUS "
                "in-run gap seconds. Seams BETWEEN runs are excluded from coverage and reported "
                "separately. This is DATA COVERAGE, not elapsed wall-clock time."
            ),
            "cumulative_covered_hours": round(covered, 4),
            "target_covered_hours": self.target_hours,
            "remaining_covered_hours": round(self.remaining_hours, 4),
            "complete": self.complete,

            # ── WALL-CLOCK, REPORTED SO IT IS NEVER MISTAKEN FOR THE METRIC ──────────────────
            "not_the_metric": (
                "elapsed_wall_hours is NOT the target. Reaching the target always takes MORE "
                "wall-clock time than covered time, by exactly the excluded gap + seam time below."
            ),
            "elapsed_wall_hours": round(elapsed, 4),
            "excluded_in_run_gap_hours": round(self.gap_seconds / 3600.0, 4),
            "excluded_seam_hours": round(self.seam_seconds / 3600.0, 4),

            # ── SEAMS AND LEDGER INTEGRITY ───────────────────────────────────────────────────
            "seam_count": self.seam_count,
            "open_seams": len(self.open_seams),
            "seam_seconds": round(self.seam_seconds, 3),
            "seam_causes": sorted({s.cause for s in self.seams}),
            "unfinalized_runs": [r.run_id for r in self.runs if not r.finalized],
        }

    def to_dict(self) -> dict:
        return {
            "corpus_id": self.corpus_id,
            "host": self.host,
            "created_utc": self.created_utc,
            "target_hours": self.target_hours,
            "runs": [r.to_dict() for r in self.runs],
            "seams": [s.to_dict() for s in self.seams],
            "progress": self.progress(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> CorpusManifest:
        m = cls(
            corpus_id=d["corpus_id"], host=d.get("host", ""),
            created_utc=d.get("created_utc", ""),
            target_hours=d.get("target_hours", CORPUS_TARGET_HOURS),
        )
        m.runs = [RunRecord.from_dict(r) for r in d.get("runs", [])]
        m.seams = [SeamRecord.from_dict(s) for s in d.get("seams", [])]
        return m


# ── THE LEDGER ────────────────────────────────────────────────────────────────────────────────

class CorpusLedger:
    """Owns a corpus directory: its runs, its seams, its manifest, its progress meter.

    Write-through, like the gap ledger (WO-014c-3 §0.1): a seam is persisted the instant it opens,
    because the event a ledger most needs to survive is the one that ends the process writing it.
    """

    def __init__(self, root: Path, corpus_id: str, host: str = "",
                 segment_patterns: tuple = DEFAULT_SEGMENT_PATTERNS) -> None:
        self.root = Path(root)
        self.corpus_id = corpus_id
        self.segment_patterns = tuple(segment_patterns)
        self.dir = self.root / corpus_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.dir / CORPUS_MANIFEST_FILENAME
        self.seam_ledger_path = self.dir / SEAM_LEDGER_FILENAME
        self.manifest = self._load_or_create(host)

    def _load_or_create(self, host: str) -> CorpusManifest:
        if self.manifest_path.exists():
            return CorpusManifest.from_dict(json.loads(self.manifest_path.read_text()))
        return CorpusManifest(
            corpus_id=self.corpus_id, host=host,
            created_utc=datetime.now(UTC).isoformat(),
        )

    def save(self) -> Path:
        self.manifest_path.write_text(json.dumps(self.manifest.to_dict(), indent=2))
        return self.manifest_path

    def _append_seam_event(self, event: str, seam: SeamRecord) -> None:
        """Write-through seam persistence — one JSONL line per state change, never a rewrite."""
        payload = {"event": event, **seam.to_dict()}
        with open(self.seam_ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    def run_dir(self, run_id: str) -> Path:
        return self.dir / run_id

    def prior_run(self) -> Optional[RunRecord]:
        """The most recent run of this corpus, by start time. The seam's left endpoint lives here."""
        if not self.manifest.runs:
            return None
        return sorted(self.manifest.runs, key=lambda r: r.start_utc)[-1]

    # ── §3.3 the seam ─────────────────────────────────────────────────────────────────────────
    def open_seam(self, cause: str, prior_run_id: str, resumed_run_id: str,
                  prior_last_frame_utc: str, detail: str = "") -> SeamRecord:
        """Open an inter-run seam with a DECLARED cause. Refuses an undeclared one (see module doc).

        This is the genuine EMISSION site for the three seam reason codes: `cause` is validated
        against the closed set and then written, as `reason_code`, into a durable record. It is not
        a constant sitting one line of wiring away from being emitted — it is the wiring.
        """
        if cause not in CORPUS_SEAM_CAUSES:
            raise SeamCauseUndeclared(
                f"SEAM_CAUSE_UNDECLARED: {cause!r} is not one of {list(CORPUS_SEAM_CAUSES)}. A "
                f"resume must DECLARE why the prior run ended — the process cannot observe it, and "
                f"a guessed cause is a smoothed seam. Refusing to open an unlabeled seam."
            )
        if not prior_last_frame_utc:
            raise SeamCauseUndeclared(
                "SEAM_CAUSE_UNDECLARED: no measured last frame for the prior run, so the seam has "
                "no true left bound. Refusing to open a seam whose duration could only be estimated."
            )
        seam = SeamRecord(
            seam_id=len(self.manifest.seams),
            cause=cause,
            prior_run_id=prior_run_id,
            resumed_run_id=resumed_run_id,
            prior_last_frame_utc=prior_last_frame_utc,
            detail=detail,
        )
        self.manifest.seams.append(seam)
        self._append_seam_event("open", seam)
        self.save()
        return seam

    def close_seam(self, seam: SeamRecord, resumed_first_frame_utc: str) -> SeamRecord:
        """Close the seam on the resumed run's FIRST frame — the measured right bound."""
        seam.resumed_first_frame_utc = resumed_first_frame_utc
        seam.resolved = True
        self._append_seam_event("resolved", seam)
        self.save()
        return seam

    # ── runs ──────────────────────────────────────────────────────────────────────────────────
    def add_run(self, run: RunRecord) -> RunRecord:
        self.manifest.runs = [r for r in self.manifest.runs if r.run_id != run.run_id]
        self.manifest.runs.append(run)
        self.save()
        return run

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        for r in self.manifest.runs:
            if r.run_id == run_id:
                return r
        return None

    def reconcile(self) -> list:
        """Fold any on-disk run the manifest does not already hold FINALIZED into the manifest.

        Called at the start of every resume so the progress meter reflects what is actually on disk,
        including runs whose process was killed before it could finalize. A run already recorded as
        `finalized=True` is left alone — a self-finalized record is the stronger evidence and must
        not be overwritten by a weaker post-hoc reconstruction.

        Returns the run_ids reconciled, so the caller can report them rather than absorb them.
        """
        reconciled = []
        for child in sorted(self.dir.iterdir()):
            if not child.is_dir():
                continue
            existing = self.get_run(child.name)
            if existing is not None and existing.finalized:
                continue
            if not segment_paths(child, self.segment_patterns):
                continue          # no frames — nothing to account for
            self.add_run(reconcile_run_from_disk(child, child.name, self.segment_patterns))
            reconciled.append(child.name)
        return reconciled

    def progress(self) -> dict:
        return self.manifest.progress()


# ── READING BACK WHAT A KILLED PROCESS LEFT BEHIND ────────────────────────────────────────────

def last_frame_utc_in_segment(segment_path: Path) -> str:
    """The `timestamp` of the LAST frame in a .jsonl segment, or "" if unreadable.

    Reads the file rather than a manifest ON PURPOSE: a manifest is written in a `finally` block and
    does not survive a SIGKILL, but the frames already on disk do. A partially-written trailing line
    (the process died mid-write) is skipped — a torn line is not a measurement.
    """
    try:
        lines = segment_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line).get("timestamp", "")
        except json.JSONDecodeError:
            continue  # torn trailing write — step back one frame, do not guess
    return ""


def first_frame_utc_in_segment(segment_path: Path) -> str:
    """The `timestamp` of the FIRST frame in a .jsonl segment, or "" if unreadable."""
    try:
        with open(segment_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line).get("timestamp", "")
                except json.JSONDecodeError:
                    return ""
    except OSError:
        return ""
    return ""


def segment_paths(run_dir: Path, patterns: tuple = DEFAULT_SEGMENT_PATTERNS) -> list:
    """Uncompressed segments of a run, in chronological order (the naming scheme sorts that way).

    `patterns` exists because a corpus can outlive its own file-naming convention. WO-066's first
    Hyperliquid attempt wrote `hl_BTC_*.jsonl`; the resumable rewrite writes `corpus_HL_*.jsonl` so
    that this reader works unchanged. Without a way to name BOTH, the 5.35 h that attempt captured
    would be **invisible to the accounting** — present on disk, absent from every total, which is
    the coverage-query defect this corpus machinery exists to prevent. Under-counting is as
    forbidden as over-counting (§0.4), so the old name is carried rather than dropped or renamed:
    renaming captured files after the fact edits the record, and this reads it instead.

    NOT sorted across patterns by name alone — a mixed-scheme run would interleave wrongly — but
    each run in practice uses one scheme, and the sort within a scheme is chronological.
    """
    out: list = []
    for pat in patterns:
        out.extend(Path(run_dir).glob(pat))
    return sorted(set(out))


def run_frame_bounds(run_dir: Path, patterns: tuple = DEFAULT_SEGMENT_PATTERNS) -> tuple:
    """(first_frame_utc, last_frame_utc) measured across a run's segments on disk."""
    segments = segment_paths(run_dir, patterns)
    if not segments:
        return "", ""
    first = ""
    for seg in segments:
        first = first_frame_utc_in_segment(seg)
        if first:
            break
    last = ""
    for seg in reversed(segments):
        last = last_frame_utc_in_segment(seg)
        if last:
            break
    return first, last


def sha256_file(path: Path) -> str:
    """SHA-256 of a file, streamed."""
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def reconcile_run_from_disk(run_dir: Path, run_id: str,
                            patterns: tuple = DEFAULT_SEGMENT_PATTERNS) -> RunRecord:
    """Rebuild a RunRecord for a run whose process died before writing its manifest.

    THE CASE THIS EXISTS FOR: the capture runner finalizes in a `finally` block, which a SIGKILL
    (the security-policy shutdown that ate two runs) never reaches. Without reconciliation those
    hours are invisible to the progress meter even though every frame is on disk — the accounting
    would understate the corpus, and §0.4 forbids understating as firmly as overstating.

    WHAT IT CAN AND CANNOT ATTEST. Frame bounds and gap summary are read from artifacts the capture
    process itself wrote, so they are as good as any other measurement. Segment HASHES are computed
    NOW, over files at rest, and are marked `hashed_at_capture=False` — they pin the bytes going
    forward but cannot witness the interval since capture. The run is left `finalized=False` so a
    reader can always tell a reconciled run from a self-finalized one; the distinction is preserved,
    never smoothed.
    """
    run_dir = Path(run_dir)
    first, last = run_frame_bounds(run_dir, patterns)
    gaps = gap_summary(run_dir / "gap_ledger.json")

    segments = []
    for seg in segment_paths(run_dir, patterns):
        try:
            frame_count = sum(1 for line in seg.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError:
            continue
        segments.append(SegmentRecord(
            filename=seg.name,
            sha256=sha256_file(seg),
            frame_count=frame_count,
            size_bytes=seg.stat().st_size,
            compressed=False,
            start_utc=first_frame_utc_in_segment(seg),
            end_utc=last_frame_utc_in_segment(seg),
            run_id=run_id,
            hashed_at_capture=False,     # computed at reconciliation, NOT at close
        ))

    preflight_path = run_dir / PREFLIGHT_FILENAME
    preflight = {}
    if preflight_path.exists():
        try:
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            preflight = {}

    return RunRecord(
        run_id=run_id,
        start_utc=preflight.get("run_start_utc", first),
        end_utc=last,
        first_frame_utc=first,
        last_frame_utc=last,
        segments=segments,
        gap_seconds=gaps["gap_seconds"],
        gap_count=gaps["gap_count"],
        terminal_gaps=gaps["terminal_gaps"],
        incomplete_gaps=gaps["incomplete_gaps"],
        preflight=preflight,
        finalized=False,             # reconciled, not self-finalized — the distinction is preserved
    )


def gap_summary(gap_ledger_path: Path) -> dict:
    """Summarise a run's gap ledger JSONL: closed gap seconds, gap count, terminal, incomplete.

    THREE OUTCOMES, NOT TWO — the distinction GapRecord.complete already draws, preserved here
    rather than flattened:
      RESOLVED  — closed by a validated emit; contributes its measured duration.
      TERMINAL  — the breaker tripped on it; the venue was presumed gone, so it NEVER closes.
                  close stays None (+infinity => default-deny from open onward). It is COMPLETE
                  by construction — a known open-ended gap — NOT a ledger deficit.
      INCOMPLETE — opened, and the run ended with it neither closed nor terminal. THIS is the
                  deficit a reader must default-deny across.
    Collapsing terminal into incomplete would report the breaker doing its job as a ledger fault,
    and would make a genuinely deficient ledger indistinguishable from a clean breaker STOP.

    A terminal gap contributes NO duration: it has no measured width, and inventing one would be
    the smoothing §0.4 forbids.
    """
    out = {"gap_seconds": 0.0, "gap_count": 0, "terminal_gaps": 0, "incomplete_gaps": 0}
    try:
        lines = Path(gap_ledger_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    opened: dict = {}
    closed: dict = {}
    terminal: set = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = rec.get("event")
        gid = rec.get("gap_id")
        if event == "open":
            opened[gid] = rec
        elif event == "resolved":
            closed[gid] = rec
        elif event == "terminal":
            terminal.add(gid)
    out["gap_count"] = len(opened)
    for gid in opened:
        if gid in terminal:
            out["terminal_gaps"] += 1
            continue
        rec = closed.get(gid)
        duration = rec.get("duration_s") if rec else None
        if duration is None:
            out["incomplete_gaps"] += 1
        else:
            out["gap_seconds"] += float(duration)
    return out
