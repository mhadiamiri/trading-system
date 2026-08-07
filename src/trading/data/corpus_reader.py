"""
WO-046 — THE DEFAULT-DENY CORPUS READER (008c validation phase).

D20, the ruling this module exists to satisfy, verbatim:

    "The guarantee moves from 'every consumer remembers to check metadata' (vigilance, 0-for-4)
     to 'the only way to get gap-spanning data is to have written code that asked for it'
     (mechanical)."

So the refusal is not a warning a caller may ignore, and not a flag a caller may forget to set. A
consumer that writes the obvious thing — "give me this window" — over data containing a recorded
discontinuity gets a REFUSAL naming what it hit. Continuous-looking data across a gap is not
expressible through this API at all: even an ACKNOWLEDGED read returns explicitly SEGMENTED data,
so there is no call that concatenates across a gap. Acknowledgment buys permission to read, never
permission to pretend the gap was not there.

WHAT THIS MODULE CONFORMS TO. The gap-record schema declared in WO-014c-2 §1.2/§1.3 — read and
verified against the real corpus before this was written. That declaration also specified the
reader's own contract (§1.3): one clock, total interval intersection, None-close read as +infinity,
and "no intersection" trustworthy only against a ledger known to be COMPLETE.

── TWO CLOCK BASES, AND WHY NORMALISATION IS NOT SEAM-SPECIAL ────────────────────────────────
Gap bounds are `time.monotonic()` floats, valid only WITHIN one run: corpus_20260805's two runs
carry monotonic anchors 115471.34 and 169506.05, which are not comparable to each other. Seam
bounds are wall-clock UTC strings, because a seam spans two processes and monotonic has no meaning
across them.

The reader therefore normalises everything onto ONE wall-clock timeline using the once-per-run
anchor the schema declared for exactly this purpose:

        wall(t_mono) = run_wall_anchor + (t_mono - run_monotonic_anchor)

D45 ruled that "a seam is a gap with a bigger cause code" and needs no separate reader logic. That
HOLDS, and this module is the demonstration: after normalisation a seam is an interval with a cause,
refused and acknowledged by the identical machinery. The normalisation step is NOT seam-specific —
a multi-run corpus needs it for GAPS regardless, since raw monotonic cannot be compared across runs.

── INCLUSIVE BOUNDS (and a declared conflict between two rulings) ────────────────────────────
WO-014c-2 §1.3 sketched the intersection test with STRICT inequalities on a half-open interval:

        t0 < (g.close or +inf)  AND  g.open < t1

Corpus precondition 5 (WO-022 §3.2), the `GapLedger` docstring, and WO-046 §2.3 all rule the
opposite: **overlap tests use INCLUSIVE bounds, and a ZERO-DURATION GAP IS A REAL GAP.** Under the
strict form a zero-width gap at instant `c` would NOT intersect a window whose boundary equals `c`,
so a query touching the gap's exact instant would be served as continuous.

This module implements the INCLUSIVE form. The later ruling is explicit, is a hard spec, is stated
in production (`GapLedger`'s docstring: "a zero-width gap still intersects a query spanning its
instant"), and is the safer direction — a reader that launders an honest ledger is default-deny's
failure mode arriving one layer downstream. The conflict is reported rather than silently resolved.

── READ-ONLY ────────────────────────────────────────────────────────────────────────────────
This module NEVER writes. It opens files for reading only and creates no directories. The corpus is
a ratified reference artifact; a reader that mutates what it reads is not a reader.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional, Sequence

from trading.data.corpus import (
    CORPUS_MANIFEST_FILENAME,
    CORPUS_SEAM_CAUSES,
    SEAM_LEDGER_FILENAME,
    _parse_utc,
)


# The closed set of discontinuity causes the reader understands: the five ruled gap causes plus the
# three seam causes. Imported rather than restated where possible — a hand-copied taxonomy is a
# second source of truth waiting to diverge from the one that produced the records.
GAP_CAUSES_READ = (
    "KEEPALIVE_RECONNECT",
    "CHECKSUM_RESYNC",
    "BREAKER_RETRY_LADDER",
    "VENUE_DISCONNECT",
    "HOST_SUSPEND",
)
ALL_DISCONTINUITY_CAUSES = tuple(GAP_CAUSES_READ) + tuple(CORPUS_SEAM_CAUSES)


class CorpusReadRefused(Exception):
    """Raised when a requested window spans a discontinuity the caller did not acknowledge.

    Carries the offending discontinuities so the refusal NAMES what it hit — a refusal that says
    only "denied" teaches the caller nothing and invites a blanket override.
    """

    def __init__(self, message: str, discontinuities: Sequence["Discontinuity"]):
        super().__init__(message)
        self.discontinuities = list(discontinuities)


class LedgerIncomplete(CorpusReadRefused):
    """Raised when the ledger is not known-COMPLETE for the queried span.

    WO-014c-2 §1.3(4): "no intersection" is only trustworthy against a ledger known to hold EVERY
    gap of the run. A run with a detected-but-uncompleted gap cannot answer "no gap here", so the
    reader default-denies across it rather than returning a silence it cannot stand behind.
    """


# ── the normalised discontinuity ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Discontinuity:
    """A gap OR a seam, normalised onto the corpus wall-clock timeline.

    One type for both is the point (D45): after normalisation the reader has no branch on which it
    is, so the refusal semantics cannot drift apart between them.
    """

    kind: str                       # "gap" | "seam" — provenance, not behaviour
    identity: str                   # e.g. "run:20260805220327/gap:3" or "corpus/seam:0"
    cause: str
    reason_code: str
    start_utc: datetime
    end_utc: Optional[datetime]     # None => OPEN-ENDED, read as +infinity
    run_id: str
    detail: str = ""

    @property
    def duration_seconds(self) -> Optional[float]:
        """None while open-ended. NOT zero — an unresolved discontinuity has no measured width,
        and reporting zero would be the smoothing the ledger doctrine forbids."""
        if self.end_utc is None:
            return None
        return (self.end_utc - self.start_utc).total_seconds()

    @property
    def open_ended(self) -> bool:
        return self.end_utc is None

    def intersects(self, start: datetime, end: datetime) -> bool:
        """INCLUSIVE interval intersection (§2.3, corpus precondition 5).

        `self.end_utc is None` reads as +infinity, so an unresolved or terminal discontinuity
        intersects every query at or after its open — default-deny falling straight out of the
        None-means-open-ended rule rather than being bolted on.

        Inclusive on BOTH sides: a ZERO-DURATION discontinuity (start == end) still intersects a
        window whose boundary equals its instant. Under strict inequalities it would not, and a
        real gap would be served as continuous.
        """
        if self.end_utc is None:
            return end >= self.start_utc
        return start <= self.end_utc and self.start_utc <= end

    def describe(self) -> str:
        dur = self.duration_seconds
        dur_s = "OPEN-ENDED (+inf)" if dur is None else f"{dur:.6f}s"
        return (f"{self.identity} kind={self.kind} cause={self.cause} "
                f"reason_code={self.reason_code} [{self.start_utc.isoformat()} .. "
                f"{self.end_utc.isoformat() if self.end_utc else 'OPEN'}] duration={dur_s}")


# ── the acknowledgment ────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Acknowledge:
    """An EXPLICIT, PER-REQUEST, CLASS-AWARE statement of what the caller accepts (§2.2).

    Deliberately NOT a boolean, NOT a global flag, NOT a config default, and NOT omission. It names
    the CAUSE CLASS being tolerated, and optionally a duration bound, so someone reading the CALLING
    code can see exactly what was accepted and judge whether that was reasonable for its purpose:

        reader.read_window(t0, t1, acknowledging=[
            Acknowledge("KEEPALIVE_RECONNECT", max_duration_seconds=5.0),
        ])

    A cause outside the closed set raises at construction: an acknowledgment naming a class that
    cannot occur is either a typo or a misunderstanding, and both should fail loudly at the call
    site rather than silently accept nothing (or, worse, read as a blanket allow).

    OPEN-ENDED discontinuities require `accept_open_ended=True` on top of the cause match. An
    unresolved or breaker-terminal window has NO measured width, so a duration bound cannot speak
    to it; accepting it must be its own deliberate act.
    """

    cause: str
    max_duration_seconds: Optional[float] = None
    accept_open_ended: bool = False
    reason: str = ""                # free text: WHY this is acceptable for this consumer's purpose

    def __post_init__(self) -> None:
        if self.cause not in ALL_DISCONTINUITY_CAUSES:
            raise ValueError(
                f"ACKNOWLEDGMENT_CAUSE_UNDECLARED: {self.cause!r} is not one of "
                f"{list(ALL_DISCONTINUITY_CAUSES)}. An acknowledgment naming a class that cannot "
                f"occur accepts nothing while looking like it accepts something."
            )
        if self.max_duration_seconds is not None and self.max_duration_seconds < 0:
            raise ValueError("ACKNOWLEDGMENT_CAUSE_UNDECLARED: max_duration_seconds must be >= 0")

    def accepts(self, d: Discontinuity) -> bool:
        """CLASS-AWARE: the cause must match exactly. There is no wildcard."""
        if d.cause != self.cause:
            return False
        if d.open_ended:
            return self.accept_open_ended
        if self.max_duration_seconds is None:
            return True
        return (d.duration_seconds or 0.0) <= self.max_duration_seconds


# ── the served window ─────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Segment:
    """One CONTINUOUS stretch of the requested window — no recorded discontinuity inside it."""

    start_utc: datetime
    end_utc: datetime
    run_id: str

    @property
    def duration_seconds(self) -> float:
        return (self.end_utc - self.start_utc).total_seconds()


@dataclass(frozen=True)
class CorpusWindow:
    """The result of a permitted read: EXPLICITLY SEGMENTED (§2.1).

    THERE IS DELIBERATELY NO `.frames` / `.concat()` / `.series` HERE. Acknowledging a gap buys
    permission to READ across it, never permission to render it as continuous. If a caller wants
    one series it must join the segments itself — visibly, in its own code, where a reviewer can
    see the splice. That is the whole D20 mechanism: the only way to get gap-spanning data is to
    have written the code that asked for it.
    """

    requested_start_utc: datetime
    requested_end_utc: datetime
    segments: tuple                                  # Segment, in time order
    acknowledged: tuple = field(default_factory=tuple)   # Discontinuity actually crossed

    @property
    def continuous(self) -> bool:
        """True only when the window contained no recorded discontinuity at all."""
        return len(self.segments) == 1 and not self.acknowledged

    @property
    def covered_seconds(self) -> float:
        """Sum of the SEGMENTS — never the requested span. The difference is the acknowledged
        discontinuity time, which is absence of data and must not be counted as coverage."""
        return sum(s.duration_seconds for s in self.segments)


# ── the reader ────────────────────────────────────────────────────────────────────────────────

class CorpusReader:
    """READ-ONLY default-deny access to a captured corpus.

    Never writes, never creates directories. Construction reads the corpus manifest, every run's
    gap ledger, and the seam ledger, and normalises all discontinuities onto one wall-clock
    timeline.
    """

    def __init__(self, corpus_dir) -> None:
        self.corpus_dir = Path(corpus_dir)
        if not self.corpus_dir.is_dir():
            raise FileNotFoundError(f"corpus directory not found: {self.corpus_dir}")
        self._discontinuities: list = []
        self._runs: dict = {}
        self._incomplete_runs: list = []
        self._load()

    # ── loading (read-only) ───────────────────────────────────────────────────────────────
    def _load(self) -> None:
        for run_dir in sorted(p for p in self.corpus_dir.iterdir() if p.is_dir()):
            self._load_run(run_dir)
        self._load_seams()
        self._discontinuities.sort(key=lambda d: d.start_utc)

    def _load_run(self, run_dir: Path) -> None:
        ledger = run_dir / "gap_ledger.json"
        if not ledger.exists():
            return
        run_id = run_dir.name
        anchor_wall = anchor_mono = None
        run_start = run_end = None
        opens: dict = {}
        closes: dict = {}
        terminals: set = set()
        declared_incomplete = 0

        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                # A torn trailing line (the capture died mid-write) is NOT data. It also means the
                # ledger cannot be called complete, so the run is marked and default-denied.
                self._incomplete_runs.append(run_id)
                continue
            ev = rec.get("event")
            if ev == "run_start":
                anchor_wall = _parse_utc(rec.get("run_wall_anchor", ""))
                anchor_mono = rec.get("run_monotonic_anchor")
                run_start = rec.get("run_start_monotonic")
            elif ev == "run_end":
                run_end = rec.get("run_end_monotonic")
                declared_incomplete = int(rec.get("incomplete", 0) or 0)
            elif ev == "open":
                opens[rec.get("gap_id")] = rec
            elif ev == "resolved":
                closes[rec.get("gap_id")] = rec
            elif ev == "terminal":
                terminals.add(rec.get("gap_id"))
                closes.setdefault(rec.get("gap_id"), rec)

        if anchor_wall is None or anchor_mono is None:
            # No anchor => monotonic bounds cannot be located in calendar time => nothing about
            # this run can be trusted for intersection. Deny across it rather than guess.
            self._incomplete_runs.append(run_id)
            return

        def to_wall(mono):
            if mono is None:
                return None
            return anchor_wall + timedelta(seconds=float(mono) - float(anchor_mono))

        self._runs[run_id] = {
            "anchor_wall": anchor_wall,
            "anchor_mono": anchor_mono,
            "start_utc": to_wall(run_start),
            "end_utc": to_wall(run_end),
        }
        if declared_incomplete:
            self._incomplete_runs.append(run_id)

        for gap_id, rec in sorted(opens.items(), key=lambda kv: (kv[0] is None, kv[0])):
            close_rec = closes.get(gap_id)
            terminal = gap_id in terminals or bool((close_rec or {}).get("terminal"))
            close_mono = None if terminal else (close_rec or {}).get("close_monotonic")
            self._discontinuities.append(Discontinuity(
                kind="gap",
                identity=f"run:{run_id}/gap:{gap_id}",
                cause=rec.get("cause", "UNKNOWN"),
                reason_code=rec.get("reason_code", ""),
                start_utc=to_wall(rec.get("open_monotonic")),
                end_utc=to_wall(close_mono),
                run_id=run_id,
                detail=rec.get("detail", ""),
            ))

    def _load_seams(self) -> None:
        seam_path = self.corpus_dir / SEAM_LEDGER_FILENAME
        if not seam_path.exists():
            return
        latest: dict = {}
        for line in seam_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            latest[rec.get("seam_id")] = rec       # write-through JSONL: last state wins
        for seam_id, rec in sorted(latest.items(), key=lambda kv: (kv[0] is None, kv[0])):
            end = _parse_utc(rec.get("resumed_first_frame_utc", "")) if rec.get("resolved") else None
            self._discontinuities.append(Discontinuity(
                kind="seam",
                identity=f"corpus/seam:{seam_id}",
                cause=rec.get("cause", "UNKNOWN"),
                reason_code=rec.get("reason_code", ""),
                start_utc=_parse_utc(rec.get("prior_last_frame_utc", "")),
                end_utc=end,
                run_id=rec.get("resumed_run_id", ""),
                detail=rec.get("detail", ""),
            ))

    # ── query surface ─────────────────────────────────────────────────────────────────────
    @property
    def discontinuities(self) -> tuple:
        return tuple(self._discontinuities)

    @property
    def gaps(self) -> tuple:
        return tuple(d for d in self._discontinuities if d.kind == "gap")

    @property
    def seams(self) -> tuple:
        return tuple(d for d in self._discontinuities if d.kind == "seam")

    @property
    def incomplete_runs(self) -> tuple:
        return tuple(sorted(set(self._incomplete_runs)))

    def intersecting(self, start_utc: datetime, end_utc: datetime) -> tuple:
        """Every recorded discontinuity intersecting [start, end], INCLUSIVE."""
        return tuple(d for d in self._discontinuities if d.intersects(start_utc, end_utc))

    def read_window(self, start_utc: datetime, end_utc: datetime,
                    acknowledging: Iterable[Acknowledge] = ()) -> CorpusWindow:
        """DEFAULT-DENY read of [start_utc, end_utc].

        Refuses unless EVERY intersecting discontinuity is covered by an explicit, class-aware
        acknowledgment. A permitted read returns SEGMENTED data — acknowledgment never yields a
        continuous series across a discontinuity.
        """
        if end_utc < start_utc:
            raise ValueError("end_utc must not precede start_utc")
        acks = list(acknowledging)

        if self._incomplete_runs:
            raise LedgerIncomplete(
                "CORPUS_READ_REFUSED: the gap ledger is not known-COMPLETE for run(s) "
                f"{sorted(set(self._incomplete_runs))}. A 'no gap here' answer is only trustworthy "
                f"against a ledger holding EVERY gap of the run (WO-014c-2 §1.3), so the reader "
                f"denies across the affected span rather than returning a silence it cannot stand "
                f"behind.",
                [],
            )

        hits = self.intersecting(start_utc, end_utc)
        unacknowledged = [d for d in hits if not any(a.accepts(d) for a in acks)]
        if unacknowledged:
            listing = "\n  ".join(d.describe() for d in unacknowledged)
            raise CorpusReadRefused(
                "CORPUS_READ_REFUSED: the requested window "
                f"[{start_utc.isoformat()} .. {end_utc.isoformat()}] spans "
                f"{len(unacknowledged)} recorded discontinuit"
                f"{'y' if len(unacknowledged) == 1 else 'ies'} that this request did not "
                f"acknowledge:\n  {listing}\n"
                "Acknowledge each by CAUSE CLASS at the call site, e.g. "
                "acknowledging=[Acknowledge('KEEPALIVE_RECONNECT', max_duration_seconds=5.0)]. "
                "Acknowledgment permits the read; the data is still returned SEGMENTED.",
                unacknowledged,
            )

        return CorpusWindow(
            requested_start_utc=start_utc,
            requested_end_utc=end_utc,
            segments=self._segment(start_utc, end_utc, hits),
            acknowledged=tuple(hits),
        )

    def _segment(self, start: datetime, end: datetime, hits: Sequence[Discontinuity]) -> tuple:
        """Cut [start, end] at every intersecting discontinuity. The pieces are the only data the
        caller ever receives — the splice, if any, has to happen in the caller's own code."""
        segments = []
        cursor = start
        for d in sorted(hits, key=lambda x: x.start_utc):
            if d.start_utc > cursor:
                segments.append(Segment(cursor, min(d.start_utc, end),
                                        run_id=self._run_at(cursor)))
            if d.end_utc is None:
                return tuple(segments)          # open-ended: nothing after it exists
            cursor = max(cursor, d.end_utc)
        if cursor < end:
            segments.append(Segment(cursor, end, run_id=self._run_at(cursor)))
        return tuple(segments)

    def _run_at(self, when: datetime) -> str:
        for run_id, meta in self._runs.items():
            s, e = meta.get("start_utc"), meta.get("end_utc")
            if s and e and s <= when <= e:
                return run_id
        return ""

    # ── §6: the READ-ONLY coverage query ──────────────────────────────────────────────────
    def coverage(self) -> dict:
        """Corpus coverage / seams / gaps WITHOUT WRITING ANYTHING (WO-046 §6).

        The replacement for `--progress`, which calls reconcile() and SAVES CORPUS_MANIFEST.json
        and therefore races a live capture. This reads the same artifacts and writes none, so it is
        safe against a run in progress: a live run's in-flight ledger is simply read as it stands.
        """
        manifest_path = self.corpus_dir / CORPUS_MANIFEST_FILENAME
        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {}

        gap_seconds = sum(d.duration_seconds or 0.0 for d in self.gaps)
        seam_seconds = sum(d.duration_seconds or 0.0 for d in self.seams)
        covered = 0.0
        for run_id, meta in self._runs.items():
            s, e = meta.get("start_utc"), meta.get("end_utc")
            if s and e:
                covered += (e - s).total_seconds()
        covered -= gap_seconds

        return {
            "corpus_id": manifest.get("corpus_id", self.corpus_dir.name),
            "read_only": True,
            "runs_seen": len(self._runs),
            "metric": (
                "cumulative_covered_hours = per-run emission span MINUS in-run gap seconds. "
                "Seams are EXCLUDED from coverage and reported separately. DATA COVERAGE, not "
                "elapsed wall-clock time."
            ),
            # WHICH BOUNDS — stated, because two honest numbers exist and they differ.
            # The reader measures the LEDGER's declared emission window (run_start_monotonic ->
            # run_end_monotonic, normalised via the run anchor). CORPUS_MANIFEST.json measures
            # FIRST FRAME -> LAST FRAME. The ledger window is slightly WIDER: its anchor is stamped
            # at capture start before the first frame arrives, and run_end in the finally block
            # after the last one. On corpus_20260805 the difference is 1.080 s over 36.9 h.
            # The reader uses ledger bounds because reading frame timestamps would mean opening
            # every segment (~700 MB) — the manifest's frame-based figure remains the ratified one.
            "bounds_basis": "ledger emission window (run_start_monotonic -> run_end_monotonic)",
            "manifest_bounds_basis": "first frame -> last frame (the RATIFIED figure)",
            "cumulative_covered_hours": round(covered / 3600.0, 4),
            "excluded_in_run_gap_hours": round(gap_seconds / 3600.0, 4),
            "excluded_seam_hours": round(seam_seconds / 3600.0, 4),
            "gap_count": len(self.gaps),
            "seam_count": len(self.seams),
            "open_ended_count": sum(1 for d in self._discontinuities if d.open_ended),
            "gap_causes": sorted({d.cause for d in self.gaps}),
            "seam_causes": sorted({d.cause for d in self.seams}),
            "incomplete_runs": list(self.incomplete_runs),
        }
