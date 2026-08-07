"""
WO-048 §3 / D-d — THE CORPUS FRAME LOADER.

Turns a reader-approved `CorpusWindow` into a STREAM of `BookState` objects. Three properties, each
load-bearing:

1. **STREAMING.** `corpus_20260805` holds 3,847,540 frames. Materialising them as objects is a
   multi-GB allocation, and `BacktestRunner.run()`'s `List[MarketState]` shape does not survive
   corpus scale (WO-047 C4). This yields one at a time and holds no history.

2. **CONTAINMENT — the enforcement point (D48).** The loader takes a `CorpusWindow` **issued by
   `CorpusReader.read_window()`** and cannot be pointed at raw files. That is what makes default-deny
   UNBYPASSABLE rather than merely impolite: without it, a consumer could skip the reader entirely,
   `open()` the JSONL itself, and splice across every gap in the corpus with nothing to stop it. The
   reader's refusal only means something if the data path runs through it.

   A frame is yielded ONLY if its timestamp falls inside one of the window's segments. Frames in the
   gaps between segments are read from disk and DISCARDED — they are on the far side of a
   discontinuity the window did not merely tolerate but explicitly segmented at.

3. **NO SUBSTITUTION.** Frames become `BookState` (see `book_state.py`), which has no
   `last_price` / `total_volume` / `trade_count` attributes at all. The absent trade channel cannot
   be filled in here because there is nowhere to put it.

WHY SEGMENT MEMBERSHIP IS TESTED PER FRAME rather than by seeking to offsets: the corpus is JSONL
with variable-length lines and no index, so there is no seek target. Reading and filtering is the
honest implementation; the cost is one timestamp parse per frame, which the §7 run absorbs.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Optional

from trading.data.book_state import BookState
from trading.data.corpus_reader import CorpusWindow, Segment


class CorpusFrameError(Exception):
    """Raised when the loader is asked to read outside the reader's approval."""


def _parse_ts(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _segment_files(corpus_dir: Path, run_id: str) -> list:
    """The .jsonl segment files of one run, in chronological order (the naming scheme sorts)."""
    run_dir = Path(corpus_dir) / run_id
    if not run_dir.is_dir():
        return []
    return sorted(run_dir.glob("corpus_*.jsonl"))


def iter_window_frames(corpus_dir, window: CorpusWindow) -> Iterator[BookState]:
    """Yield every `BookState` inside `window`'s APPROVED SEGMENTS, in time order.

    `window` must be a `CorpusWindow` returned by `CorpusReader.read_window()`. Passing anything
    else — a bare tuple of datetimes, a hand-built segment list — is refused: the type IS the
    approval, and accepting a lookalike would reopen the bypass this loader exists to close.
    """
    if not isinstance(window, CorpusWindow):
        raise CorpusFrameError(
            "CORPUS_FRAMES_UNAPPROVED_WINDOW: iter_window_frames requires a CorpusWindow issued by "
            "CorpusReader.read_window(). A hand-built window would bypass default-deny, which is "
            "the one thing this loader exists to prevent. Obtain a window from the reader — and if "
            "the reader refuses it, that refusal is the answer."
        )
    for segment in window.segments:
        yield from iter_segment_frames(corpus_dir, segment, _approved=window)


def iter_segment_frames(corpus_dir, segment: Segment, _approved: CorpusWindow = None
                        ) -> Iterator[BookState]:
    """Yield the frames of ONE approved segment.

    `_approved` is the issuing window and is REQUIRED — the underscore marks it as internal wiring,
    not an option. It exists so this function cannot be called directly with a fabricated `Segment`
    to read an arbitrary interval: the segment must be one the window actually contains.
    """
    if not isinstance(_approved, CorpusWindow) or segment not in _approved.segments:
        raise CorpusFrameError(
            "CORPUS_FRAMES_UNAPPROVED_WINDOW: this segment was not issued by the CorpusWindow "
            "supplied. Segments are read only as members of the window the reader approved."
        )
    corpus_dir = Path(corpus_dir)

    # WO-048 §3 — REFUSE AN UNRESOLVABLE SEGMENT RATHER THAN YIELD NOTHING.
    #
    # `CorpusReader._run_at()` returns "" when a segment's start falls outside every run's emission
    # window — e.g. a window requested from before the first run began. Globbing with an empty
    # run_id finds no files, so the loader would stream ZERO frames and the backtest would report a
    # clean, empty, entirely wrong result. A silent empty read is indistinguishable from "this
    # window genuinely had no data", which is the silent-truncation family this project keeps
    # closing. Refuse loudly instead, and say what to do about it.
    if not segment.run_id:
        raise CorpusFrameError(
            f"CORPUS_FRAMES_UNRESOLVED_RUN: the segment "
            f"[{segment.start_utc.isoformat()} .. {segment.end_utc.isoformat()}] resolves to no "
            f"run, so there are no frames to read and an empty stream would look like an honest "
            f"empty window. This normally means the requested window extends beyond the corpus's "
            f"own emission bounds. Request a window inside the corpus's runs."
        )

    files = _segment_files(corpus_dir, segment.run_id)
    if not files:
        raise CorpusFrameError(
            f"CORPUS_FRAMES_UNRESOLVED_RUN: run {segment.run_id!r} has no .jsonl segment files "
            f"under {corpus_dir}. Refusing to yield an empty stream that would read as an honest "
            f"empty window."
        )
    for path in files:
        for state in _iter_file_frames(path, segment.start_utc, segment.end_utc):
            yield state


def _iter_file_frames(path: Path, start, end) -> Iterator[BookState]:
    """Stream one .jsonl file, yielding only frames within [start, end].

    Bounds are INCLUSIVE, matching the reader's intersection semantics (WO-046 §2.3). A torn
    trailing line (the capture died mid-write) is skipped, never guessed — the same treatment the
    corpus tooling gives it everywhere else.
    """
    try:
        handle = open(path, "r", encoding="utf-8")
    except OSError:
        return
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                frame = json.loads(line)
            except json.JSONDecodeError:
                continue                      # torn write — not data
            ts = _parse_ts(frame.get("timestamp", ""))
            if ts is None:
                continue
            if ts < start:
                continue
            if ts > end:
                return                        # frames are ordered; past the segment, stop reading
            state = _frame_to_book_state(frame, ts)
            if state is not None:
                yield state


def _frame_to_book_state(frame: dict, ts: datetime) -> Optional[BookState]:
    """Build a BookState from one corpus frame, or None if the frame cannot be trusted.

    A frame that fails BookState's validation (crossed book, non-positive quote) is DROPPED rather
    than repaired. Repairing it would be substitution at a smaller scale, and the corpus's own
    CRC32-validated capture path means such a frame should not exist — if one does, that is a
    finding, not something for the loader to paper over.
    """
    try:
        return BookState(
            timestamp=ts,
            symbol=frame["symbol"],
            best_bid=Decimal(frame["bid"]),
            best_ask=Decimal(frame["ask"]),
            best_bid_size=Decimal(frame["bid_qty"]),
            best_ask_size=Decimal(frame["ask_qty"]),
        )
    except (KeyError, ValueError, ArithmeticError):
        return None


def count_window_frames(corpus_dir, window: CorpusWindow) -> dict:
    """Frame counts per segment WITHOUT building states — for eligibility checks (§4.3).

    Returns {segment_index: frame_count}. Streams and counts; holds nothing.
    """
    counts = {}
    for i, segment in enumerate(window.segments):
        n = 0
        for _ in iter_segment_frames(corpus_dir, segment, _approved=window):
            n += 1
        counts[i] = n
    return counts
