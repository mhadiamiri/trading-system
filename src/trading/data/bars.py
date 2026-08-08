"""
WO-053 §3.1 — THE BAR LAYER. Fixed-interval mid-price bars, built WITHIN a segment, never across a
discontinuity.

THE ONE PROPERTY THIS MODULE EXISTS TO GUARANTEE
------------------------------------------------
**A bar is built from the frames of exactly one segment.** A bar that straddled a gap would average
a price from before a 2.1-hour hole with one from after it and report the result as a 60-second
observation — the splice defect (D20) reappearing one layer up, where the default-deny reader
cannot see it. The reader segments the corpus; nothing downstream may quietly re-join it.

TWO MECHANISMS, DELIBERATELY BELT AND BRACES:

1. **STRUCTURAL — segment-relative alignment.** Bar k covers
   `[segment_start + k·interval, segment_start + (k+1)·interval)`. Buckets are anchored to the
   segment's own first frame, NOT to the wall-clock epoch. Under epoch alignment a single bucket
   (say 14:07:00–14:08:00) could legitimately contain frames from both sides of a gap, and
   "bar spans a discontinuity" would be a real state that had to be detected. Anchoring per segment
   makes it unrepresentable: a builder has ONE segment and cannot see another's frames.

2. **ENFORCED — an explicit bounds check.** `add()` refuses any frame outside its segment's
   `[start_utc, end_utc]` with `BAR_FRAME_OUTSIDE_SEGMENT`. This is what catches a caller who
   constructs a builder for segment A and feeds it segment B's frames — the mechanism (1) alone
   would silently bucket them, because arithmetic on a timestamp never complains.

Mechanism 1 makes the defect hard to express; mechanism 2 makes it impossible to express silently.
The bite proof mutates (2) away and shows a gap-spanning bar appear.

PARTIAL BARS ARE DISCARDED (§2.2, registered)
---------------------------------------------
A segment does not end on a bar boundary, so its final bucket is nearly always short. That bucket
is **never emitted**. A 12-second bar reported as a completed 60-second bar is a small lie of
exactly the kind this project refuses — and it would land precisely at segment edges, i.e.
disproportionately at the boundaries where the data is least trustworthy. The count of discarded
partials is reported, not swallowed.

The same rule applies at the START of a segment: bar 0 begins at the segment's first frame, so it
is complete by construction under this alignment. There is no partial-open case.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterator, Optional

from trading.data.book_state import BookState
from trading.data.corpus_frames import iter_segment_frames
from trading.data.corpus_reader import CorpusWindow, Segment


class BarError(Exception):
    """Raised when a frame is offered to a builder that does not own it."""


@dataclass(frozen=True)
class Bar:
    """One completed fixed-interval bar of MID prices.

    `close` is what the registered signal consumes. OHLC is recorded because a bar that carried
    only its close would make any later question about intrabar range unanswerable without a
    re-run, and the cost of carrying three more Decimals is nil.

    There is deliberately no `complete` flag: an incomplete bar is never constructed, so a flag
    would only create the possibility of one being set wrongly.
    """

    segment_index: int
    bar_index: int
    start_utc: datetime
    end_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    frame_count: int

    def compute_snapshot_hash(self) -> str:
        """Provenance hash of the exact bar a decision acted on (Principle VIII).

        A bar-based decision's `feature_snapshot_hash` must identify the BAR, not some frame inside
        it — the strategy never sees a frame. Same shape as `BookState.compute_snapshot_hash`, so
        the two are interchangeable to any consumer that only needs "what did this act on".
        """
        import hashlib
        payload = "|".join([
            str(self.segment_index), str(self.bar_index),
            self.start_utc.isoformat(), self.end_utc.isoformat(),
            str(self.open), str(self.high), str(self.low), str(self.close),
            str(self.frame_count),
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SegmentBarBuilder:
    """Builds bars for ONE segment. Cannot span a discontinuity — see the module docstring.

    Usage is a stream: `add(state)` returns a completed `Bar` at the instant a bucket closes, else
    `None`. `discarded_partial` reports whether the trailing bucket was dropped.
    """

    def __init__(self, segment_index: int, segment: Segment, interval_seconds: int) -> None:
        if interval_seconds <= 0:
            raise ValueError(f"interval_seconds must be > 0, got {interval_seconds}")
        self._segment_index = segment_index
        self._segment = segment
        self._interval = timedelta(seconds=interval_seconds)
        self._anchor: Optional[datetime] = None   # this SEGMENT's first frame — the alignment origin
        self._bucket: Optional[int] = None
        self._open = self._high = self._low = self._close = None
        self._frames = 0
        self._bars_emitted = 0
        self.discarded_partial_frames = 0
        self.discarded_partial_bars = 0

    @property
    def bars_emitted(self) -> int:
        return self._bars_emitted

    def add(self, state: BookState) -> Optional[Bar]:
        """Offer one frame. Returns the bar that just CLOSED, if this frame started a new bucket.

        Raises:
            BarError: BAR_FRAME_OUTSIDE_SEGMENT — the frame does not belong to this segment.
        """
        ts = state.timestamp

        # ── MECHANISM 2: the enforced bounds check. ────────────────────────────────────────────
        # Bounds are INCLUSIVE, matching the reader's intersection semantics (WO-046 §2.3) and the
        # frame loader's. Without this, a builder for segment A fed segment B's frames would bucket
        # them by arithmetic and emit a bar whose frames straddle the hole between them.
        if ts < self._segment.start_utc or ts > self._segment.end_utc:
            raise BarError(
                f"BAR_FRAME_OUTSIDE_SEGMENT: frame at {ts.isoformat()} is outside segment "
                f"{self._segment_index} "
                f"[{self._segment.start_utc.isoformat()} .. {self._segment.end_utc.isoformat()}]. "
                f"A bar is built from the frames of exactly ONE segment; accepting this frame "
                f"would let a bar span a discontinuity the reader deliberately segmented at."
            )

        if self._anchor is None:
            self._anchor = ts                      # MECHANISM 1: alignment origin = THIS segment

        bucket = int((ts - self._anchor) // self._interval)

        if self._bucket is None:
            self._start_bucket(bucket, state)
            return None

        if bucket == self._bucket:
            self._accumulate(state)
            return None

        # A new bucket began: the previous one is COMPLETE and is emitted.
        closed = self._close_bucket()
        self._start_bucket(bucket, state)
        return closed

    def finish(self) -> None:
        """End of segment. The trailing bucket is DISCARDED, never emitted (§2.2, registered)."""
        if self._bucket is not None:
            self.discarded_partial_bars += 1
            self.discarded_partial_frames += self._frames
            self._bucket = None

    def _start_bucket(self, bucket: int, state: BookState) -> None:
        self._bucket = bucket
        price = state.mid_price
        self._open = self._high = self._low = self._close = price
        self._frames = 1

    def _accumulate(self, state: BookState) -> None:
        price = state.mid_price
        if price > self._high:
            self._high = price
        if price < self._low:
            self._low = price
        self._close = price
        self._frames += 1

    def _close_bucket(self) -> Bar:
        start = self._anchor + self._bucket * self._interval
        bar = Bar(
            segment_index=self._segment_index,
            bar_index=self._bars_emitted,
            start_utc=start,
            end_utc=start + self._interval,
            open=self._open, high=self._high, low=self._low, close=self._close,
            frame_count=self._frames,
        )
        self._bars_emitted += 1
        return bar


def iter_segment_bars(corpus_dir, segment_index: int, segment: Segment, window: CorpusWindow,
                      interval_seconds: int) -> Iterator[Bar]:
    """Stream the completed bars of ONE reader-approved segment.

    Reads through `iter_segment_frames`, so the loader's containment check still applies: this is a
    layer ON the default-deny path, never a way around it.
    """
    builder = SegmentBarBuilder(segment_index, segment, interval_seconds)
    for state in iter_segment_frames(corpus_dir, segment, _approved=window):
        bar = builder.add(state)
        if bar is not None:
            yield bar
    builder.finish()
