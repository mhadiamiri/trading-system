"""WO-066 §3 — THE HYPERLIQUID CAPTURE SPIKE. Read-only. No order path.

    python tools/hyperliquid_capture.py --corpus-id hlspike_20260812 --duration-hours 24 \
        --kraken-run-dir captures/phase_b/... [--seam-cause POLICY_SHUTDOWN]

§3.2 DURATION, DERIVED (0.15): WO-065 took five instants and its fifth read misrepresented dYdX by
38x against the other four. Snapshots cannot be superseded by more snapshots — only by CONTINUOUS
observation long enough to contain the regimes they missed. BTC liquidity is diurnal (Asia, Europe,
US sessions), so the shortest window that contains every session once is **24 hours**. Rounded up
from "one full diurnal cycle" and declared here.

§3.3 CORPUS DISCIPLINE — per element, transfers or adapts:
  segments (hourly JSONL)          TRANSFERS UNCHANGED
  capture-time SHA-256 per segment TRANSFERS — **and is now WRITE-THROUGH**, see below
  MANIFEST / corpus manifest       TRANSFERS — via `trading.data.corpus.CorpusLedger`
  legs + seams under one corpus-id TRANSFERS — ported from phase B, see below
  gap ledger                       ADAPTS — FOUR causes; CHECKSUM_RESYNC absent (ratified)
  default-deny reader              TRANSFERS — it reads the ledger, not the venue
  checksum_failures_total          ADAPTS — reported as None, never 0 (WO-054's count:0 vs null)

═══ WHAT THE 2026-08-12 LOSS CHANGED ════════════════════════════════════════════════════════════

The first attempt died 5 h 21 m into 24 h when Windows Update rebooted the host. Three separate
defects turned a survivable interruption into an unverifiable corpus, and all three are fixed here:

1. **THE CAPTURE-TIME HASHES WERE HELD IN MEMORY.** `_close_segment` appended each digest to a list
   and printed it; the manifest was written only at `run_end`. The process died, the list died with
   it, and six hashed segments became six files nobody could attest. **Now every segment record is
   appended to `segment_ledger.jsonl` the moment the segment closes** — write-through, exactly like
   the gap ledger, because *the event a ledger most needs to survive is the one that ends the
   process writing it.* A post-hoc hash is still obtainable (`reconcile_run_from_disk`) but it is
   marked `hashed_at_capture=False` and it attests something weaker; the two are never conflated.

2. **THE RUN WAS A SINGLE PROCESS WITH NO RESUME.** Phase B has solved this: one corpus-id, N runs,
   every seam a declared ledger record (D45 — *more honest than one unbroken process*). This tool
   now uses the same `CorpusLedger`, so a forced restart costs a **bounded, labeled seam** instead
   of the corpus. The seam's cause is **declared on the command line and never guessed** — the
   process cannot observe why it was killed, and a guessed cause is a smoothed seam.

3. **ONLY THE TOUCH WAS PERSISTED.** The frame carried `levels_published: 20` while writing just
   `bid/ask/bid_qty/ask_qty` — so the manifest's evidentiary bound promised twenty levels of depth
   that the corpus did not contain. **All published levels are now written.** A bound that
   overstates the corpus is worse than a narrow bound honestly declared.

§4 MITIGATIONS ARE WIRED HERE (0.14 — this file is their production call site):
  4.1 cross-venue band    -> `_emit()` refuses when the band is exceeded
  4.2 tape-vs-book        -> `_emit()` refuses when a print cannot be reconciled
  4.3 staleness           -> `_emit()` refuses a snapshot older than the derived bound
  4.4 evidentiary bound   -> declared in the manifest; level count recorded per frame
  term 11 reboot window   -> `_preflight_reboot_window()` REFUSES TO START inside one
An unwired mitigation is the WO-055 defect; each refusal SUPPRESSES THE FRAME (0.9), it does not
merely log.

**NO ORDER PATH.** This module sends only `subscribe` and `ping`.
"""

import argparse
import asyncio
import gzip
import hashlib
import json
import math
import os
import pathlib
import platform
import sys
import time
from datetime import UTC, datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _ROOT)

import websockets                                                     # noqa: E402

from trading.data.adapters import hyperliquid_v1 as hl                # noqa: E402
from trading.data import hyperliquid_mitigations as mit               # noqa: E402
from trading.data.corpus import (                                     # noqa: E402
    CorpusLedger,
    RunRecord,
    SeamCauseWithoutReferent,
    SegmentRecord,
    require_seam_referent,
    run_frame_bounds,
)
from trading.loop import reboot_window                                # noqa: E402

TICK = 1.0            # observed on the BTC perp book (WO-065: spread pinned at 1.0 USD)
CALIBRATION_MINUTES = 60

# In-flight liveness reporting. Not a guard — it refuses nothing. It exists because a latching
# staleness bound took the fast feed offline at 03:23:50Z on 2026-08-13 and the run continued for
# 5 h 39 m reporting healthy, then took the slow feed too. 120 s is well past the slow feed's
# measured 5.4 s cadence and its 34.59 s derived bound, so it cannot fire on ordinary quiet.
LIVENESS_CHECK_S = 60.0
LIVENESS_DARK_S = 120.0
CAPTURE_ROOT = pathlib.Path("captures/hyperliquid")

# Segment names deliberately match the shared `corpus_*.jsonl` scheme so `segment_paths`,
# `run_frame_bounds` and `reconcile_run_from_disk` work on this venue with NO change to code the
# Kraken corpus depends on. Reusing a proven reader beats a parallel one that drifts.
SEGMENT_PREFIX = "corpus_HL"
SEGMENT_LEDGER = "segment_ledger.jsonl"
PREFLIGHT_FILENAME = "PREFLIGHT.json"

# THE FIRST ATTEMPT'S NAMING, CARRIED DELIBERATELY. The 2026-08-12 run wrote `hl_BTC_*.jsonl`
# before this scheme existed. Its 5.35 h is real captured data and stays in the corpus under
# WO-044 run 3's disposition — visible in the accounting, reconciled with `hashed_at_capture:
# false` because its capture-time digests died with the process. Dropping the pattern would make
# those hours invisible while the files sat on disk, which is the coverage-query defect; renaming
# the files would edit the record. So the reader is told both names and reads what is there.
SEGMENT_PATTERNS = (f"{SEGMENT_PREFIX}_*.jsonl", "hl_BTC_*.jsonl")


class HyperliquidCapture:
    def __init__(self, ledger: CorpusLedger, run_id: str, duration_s: float,
                 kraken_dir: pathlib.Path | None, feeds: tuple = (hl.FEED_SLOW, hl.FEED_FAST)):
        self.ledger = ledger
        self.run_id = run_id
        self.run_dir = ledger.run_dir(run_id)
        self.duration_s = duration_s
        self.kraken_dir = kraken_dir
        self.feeds = tuple(feeds)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.segments: list = []
        self.gaps: list = []
        self.counters = {k: 0 for k in mit.COUNTERS}
        self.counters["frames_emitted"] = 0
        self.counters["frames_refused"] = 0
        # WO-067 §2.2/§2.3 — unguarded frames are COUNTED, not silently mixed in with guarded ones.
        self.counters["unguarded_frames"] = 0
        self.counters["unguarded_counterpart_stale"] = 0
        self.counters["unguarded_band_underived"] = 0
        self.counters["counterpart_stale_transitions"] = 0
        # PER FEED, because a 0.52 s stream and a 5.4 s stream are different observations and one
        # set of totals would average away the difference the dual subscription exists to measure.
        self.per_feed = {f: {k: 0 for k in mit.PER_FEED_COUNTERS} for f in self.feeds}
        # WO-067 §2.1 — ROLLING, not fitted-once. Constructed immediately and self-warming:
        # `observe()` feeds it on every arrival and it becomes active the moment the trailing
        # window holds enough samples. There is no longer a calibration instant at which the band
        # is frozen, because that instant is what made the guard market-correlated.
        self.band = mit.RollingCrossVenueBand()
        # WO-067 §2.2 — the counterpart dependency, DECLARED and tracked with its own liveness
        # bound. WO-066 assumed a live Kraken feed and could not report the assumption.
        self.counterpart = mit.CounterpartLiveness()
        self.stale: dict = {f: None for f in self.feeds}      # §4.3 cadence differs 10x per feed
        self.tape: mit.TapeBookBound | None = None
        self._log_bases: list = []
        self._gaps_s: dict = {f: [] for f in self.feeds}
        self._tape_distances: list = []
        # TWO CLOCKS, BECAUSE THEY ARE TWO DIFFERENT QUANTITIES.
        #
        # `_last_book_mono` — when we last SAW a book on this feed. Advances on EVERY arrival,
        #   refused or not. Staleness is a statement about whether THE VENUE has gone quiet, so
        #   this is what §4.3 must measure against.
        # `_last_emitted_mono` — when we last WROTE a frame. Diagnostic only.
        #
        # Conflating them is what took the fast feed offline for five and a half hours on
        # 2026-08-13: staleness measured against a clock that only advanced on a SUCCESSFUL emit,
        # so the first refusal froze the reference instant, the measured age then grew without
        # bound, and the guard could never accept another frame. A latching guard is
        # indistinguishable from a dead feed, and the process reported healthy throughout.
        self._last_book_mono: dict = {f: None for f in self.feeds}
        self._last_emitted_mono: dict = {f: None for f in self.feeds}
        self._latest_touch: tuple | None = None   # freshest touch from EITHER feed, for §4.2
        self._seg_path: pathlib.Path | None = None
        self._seg_fh = None
        self._seg_hour: str | None = None
        self._seg_frames = 0
        # WO-067 §2.3 — counters for the CURRENT segment only, reset at every rotation. The
        # aggregate cannot show that a blackout ran for six consecutive hours; this can.
        self._seg_counters: dict = {}
        self._seg_start_utc = ""
        self._seg_last_utc = ""
        self._first_frame_utc = ""
        self._last_frame_utc = ""
        # WO-067 — the twelve-term record, written INTO the run directory and hashed at capture.
        self._preflight_digest: str | None = None
        self._preflight_all_green: bool | None = None

    # ── segment rotation with WRITE-THROUGH capture-time hashing ───────────────────────────────
    def _rotate(self, ts: datetime):
        hour = ts.strftime("%Y%m%dT%HZ")
        if hour == self._seg_hour:
            return
        self._close_segment()
        self._seg_hour = hour
        self._seg_path = self.run_dir / f"{SEGMENT_PREFIX}_{hour}.jsonl"
        self._seg_fh = open(self._seg_path, "a", encoding="utf-8")
        self._seg_frames = 0
        self._seg_counters = {}          # WO-067 §2.3 — per SEGMENT, so reset at rotation
        self._seg_start_utc = ts.isoformat()

    def _close_segment(self):
        if self._seg_fh is None:
            return
        self._seg_fh.close()
        h = hashlib.sha256()
        with open(self._seg_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        digest = h.hexdigest()
        with open(self._seg_path, "rb") as fi, gzip.open(
                str(self._seg_path) + ".gz", "wb") as fo:
            fo.writelines(fi)
        rec = SegmentRecord(
            filename=self._seg_path.name, sha256=digest, frame_count=self._seg_frames,
            size_bytes=self._seg_path.stat().st_size, compressed=True,
            start_utc=self._seg_start_utc, end_utc=self._seg_last_utc,
            run_id=self.run_id, hashed_at_capture=True,
            # WO-067 §2.3 — the counters reach the RECORD, not just the object. WO-055's
            # `raw_text_trim_events` reached the object and never the record, and a count that
            # lives outside the corpus cannot be audited from it. Written even when every value is
            # zero: for a segment the capture actually counted, zero is a claim we can make.
            guard_counters=dict(self._seg_counters),
        )
        self.segments.append(rec)
        # WRITE-THROUGH. This line is the whole repair from the 2026-08-12 loss: the digest reaches
        # disk before the next frame is read, so a kill at any later instant still leaves an
        # at-capture attestation for every closed segment.
        with open(self.run_dir / SEGMENT_LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "segment_closed", **rec.to_dict()}) + "\n")
        print(f"[segment] {self._seg_path.name}  {self._seg_frames} frames  "
              f"sha256 {digest[:16]}…  (ledgered)", flush=True)
        self._seg_fh = None

    # ── the emission path — every mitigation gates it (0.9/0.14) ──────────────────────────────
    def _emit(self, book, trades, kraken_mid, kraken_dt):
        now_mono = time.monotonic()
        wall = datetime.now(UTC)
        feed = getattr(book, "feed", hl.FEED_SLOW)
        pf = self.per_feed.setdefault(feed, {k: 0 for k in mit.PER_FEED_COUNTERS})
        bid = float(book.bids[0].px) if book.bids else 0.0
        ask = float(book.asks[0].px) if book.asks else 0.0
        mid = (bid + ask) / 2 if bid and ask else 0.0

        refusals = []

        # WO-067 §2.2 — the counterpart's own liveness, tracked BEFORE any per-frame comparison.
        # `kraken_dt` answers "are these two reads close enough to compare?"; this answers "is the
        # counterpart process still alive?". WO-066 conflated them and read one dead dependency as
        # 4,549 separate price anomalies.
        if kraken_mid:
            self.counterpart.observe(time.time() - (kraken_dt or 0.0))
        counterpart_live = self.counterpart.live(time.time())

        # WO-067 §2.1 — ARRIVALS FEED THE BAND, whatever the verdict turns out to be. A band
        # re-derived from its own emitted output consumes its own filtered tail and ratchets
        # tighter every cycle — strictly worse than freezing. Same shape as the §4.3 latch.
        if kraken_mid and mid:
            self.band.observe(now_mono, kraken_mid, mid)

        state = mit.guard_state(counterpart_live, self.band.derived)

        # 4.3 staleness — PER FEED. One bound across both would be derived from a bimodal cadence
        # and would describe neither: 5.4 s and 0.52 s are 10x apart.
        stale = self.stale.get(feed)
        last_arrival = self._last_book_mono.get(feed)
        if stale is not None and last_arrival is not None:
            v = stale.check(now_mono - last_arrival)
            if v.refuse:
                refusals.append(v)
                self.counters["refused_staleness"] += 1
                pf["refused_staleness"] += 1

        # THE ARRIVAL CLOCK ADVANCES WHATEVER THE VERDICT, and it must be set BEFORE the refusal
        # return below. A frame we refused is still a frame the venue sent; forgetting that is
        # exactly what latched this guard. Note this does NOT disarm staleness — a feed that stays
        # silent still produces one refusal per arrival, because each arrival is measured against
        # the previous ARRIVAL, not against the last acceptance.
        self._last_book_mono[feed] = now_mono

        # 4.1 cross-venue band — ONLY when the state is GUARDED. The other two states do not
        # refuse: a stale counterpart or a warming band means we cannot CHECK the frame, not that
        # the frame is wrong. Refusing on a dependency failure is the WO-066 blackout, and it
        # deletes data for a reason that has nothing to do with the data.
        if state == mit.GUARD_STATE_GUARDED and kraken_mid:
            v = self.band.check(kraken_mid, mid, kraken_dt)
            if v.refuse:
                refusals.append(v)
                self.counters["refused_cross_venue_band"] += 1
                pf["refused_cross_venue_band"] += 1
                self._seg_bump("refused_cross_venue_band")
                # THE FALSIFIER'S EXACT CONDITION (WO-067 §4.2), counted at the moment it applies
                # rather than reconstructed afterwards: a refusal while the pair was well aligned
                # AND the counterpart was publishing is what falsifies the repair.
                if abs(kraken_dt or 0.0) <= mit.ALIGNMENT_TOLERANCE_S:
                    self.counters["refused_band_while_pair_aligned"] = (
                        self.counters.get("refused_band_while_pair_aligned", 0) + 1)
                    self._seg_bump("refused_band_while_pair_aligned")
        else:
            self.counters["unguarded_frames"] += 1
            self._seg_bump("unguarded_frames")
            if state == mit.GUARD_STATE_UNGUARDED_COUNTERPART_STALE:
                self.counters["unguarded_counterpart_stale"] += 1
                self._seg_bump("unguarded_counterpart_stale")
            else:
                self.counters["unguarded_band_underived"] += 1
                self._seg_bump("unguarded_band_underived")

        # 4.2 tape vs book — reconciled against the FRESHEST touch from EITHER feed, and only once
        # the tolerance has been DERIVED. Until then the distances are measured, not acted on: a
        # guard running on a guessed constant refused 33.3% of ordinary slow-feed frames, and the
        # refusals correlated with price movement, which would have biased the corpus toward calm.
        touch = self._latest_touch or ((bid, ask) if bid and ask else None)
        if touch:
            for t in trades:
                d = mit.reconciliation_distance(float(t.px), touch[0], touch[1])
                self._tape_distances.append(d)
            if self.tape is not None:
                for t in trades:
                    v = self.tape.check(float(t.px), touch[0], touch[1])
                    if v.refuse:
                        refusals.append(v)
                        self.counters["refused_tape_vs_book"] += 1
                        pf["refused_tape_vs_book"] += 1
                        break

        # 4.4 evidentiary bound — flags, never refuses. Judged against THIS feed's published depth,
        # not the corpus maximum: a 5-level frame from the fast feed is not a short 20-level book.
        lv = mit.check_declared_levels(book.levels_published,
                                       declared=hl.FEED_LEVELS.get(feed, mit.DECLARED_LEVELS))
        if lv.reason:
            self.counters["observed_levels_below_declared"] += 1

        if refusals:
            self.counters["book_consistency_failures_total"] += 1
            self.counters["frames_refused"] += 1
            pf["frames_refused"] += 1
            self._seg_bump("frames_refused")
            return                       # THE FRAME IS SUPPRESSED — not merely logged (0.9)

        self._rotate(wall)
        stamp = wall.isoformat()
        rec = {
            "timestamp": stamp, "symbol": hl.SYMBOL, "venue": "hyperliquid_mainnet",
            "bid": str(book.bids[0].px) if book.bids else None,
            "ask": str(book.asks[0].px) if book.asks else None,
            "bid_qty": str(book.bids[0].sz) if book.bids else None,
            "ask_qty": str(book.asks[0].sz) if book.asks else None,
            # ALL PUBLISHED LEVELS. The evidentiary bound (§4.4) claims depth to level 20; writing
            # only the touch would make that claim false in the corpus it describes.
            "bids": [[str(x.px), str(x.sz), x.n] for x in book.bids],
            "asks": [[str(x.px), str(x.sz), x.n] for x in book.asks],
            "levels_published": book.levels_published,
            # WHICH feed produced this frame, from the venue's own `fast` field. Without it the
            # corpus would interleave two different observations of the venue under one label.
            "feed": feed,
            "venue_time_ms": book.venue_time_ms,
            "trades": [{"px": str(t.px), "sz": str(t.sz), "side": t.side} for t in trades],
            "kraken_mid": kraken_mid, "kraken_dt_s": kraken_dt,
            # WO-067 §2.2 — every frame says which of the three states it was written under, so a
            # reader can separate a guarded corpus from an unguarded one WITHOUT re-deriving
            # anything. An unguarded frame is a true observation of Hyperliquid that we could not
            # check; conflating it with a checked one is the count:0 / count:null error.
            "guard_state": state,
        }
        self._seg_fh.write(json.dumps(rec) + "\n")
        # WRITE-THROUGH. An open buffered handle over a 24-hour run holds frames in memory,
        # and a process death loses them — the capture-time hash would then certify a file
        # that never contained what the run observed. The feed is >=0.5 s cadence, so a
        # per-frame flush costs nothing.
        self._seg_fh.flush()
        self._seg_frames += 1
        self._seg_last_utc = stamp
        self._last_frame_utc = stamp
        if not self._first_frame_utc:
            self._first_frame_utc = stamp
        self.counters["frames_emitted"] += 1
        self._seg_bump("frames_emitted")
        pf["frames_emitted"] += 1
        self._last_emitted_mono[feed] = now_mono
        if bid and ask:
            self._latest_touch = (bid, ask)

    # ── the twelve-term preflight, RUN FRESH AND RECORDED IN THE CORPUS ───────────────────
    def _write_preflight_record(self) -> bool:
        """Execute all twelve terms now, write PREFLIGHT.json into the run dir, hash it at capture.

        WHY THIS EXISTS (WO-067). Every Kraken run carries a PREFLIGHT.json in its run directory.
        The Hyperliquid legs carried NONE: the twelve-term record went to `.artifacts/wo066/`,
        which is git-ignored and outside the corpus entirely. A capture whose opening record cannot
        be read back FROM the corpus cannot be audited from it — the same defect as WO-055's
        `raw_text_trim_events`, which reached the object and never the record. It surfaced
        concretely when the Hyperliquid grant expiry had to be recovered from a scratch file
        because no corpus artifact held it.

        RUN FRESH, NEVER COPIED. Re-executing every term is the point: the record must attest the
        preflight that gated THIS run, on this host, at this instant. Copying the artifact from an
        earlier standalone run would attest a different machine-instant while looking identical —
        and term 8 is EXECUTED, not printed, so a copy would smuggle a printed guard back in by
        another route (the WO-044 §3.7 scar).

        HASHED AT CAPTURE, like a segment. The digest is written through to the segment ledger
        before the socket opens, so a process killed at any later instant still leaves an
        at-capture attestation of the conditions it started under. A hash computed later attests
        only what the file contains NOW, and the whole value of the record is that it witnesses a
        moment that has passed.
        """
        from tools import hyperliquid_preflight as pf          # deferred: pf reads this module

        record, all_green = pf.evaluate()
        record["run_id"] = self.run_id
        record["corpus_id"] = self.ledger.corpus_id
        record["duration_hours_requested"] = self.duration_s / 3600.0
        record["kraken_run_dir"] = str(self.kraken_dir) if self.kraken_dir else None

        path = self.run_dir / PREFLIGHT_FILENAME
        path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")

        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        self._preflight_digest = h.hexdigest()
        self._preflight_all_green = all_green

        with open(self.run_dir / SEGMENT_LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "event": "preflight_recorded",
                "filename": PREFLIGHT_FILENAME,
                "sha256": self._preflight_digest,
                "hashed_at_capture": True,
                "all_green": all_green,
                "utc": record["utc"],
            }) + "\n")

        print(f"[preflight] recorded {path}  sha256 {self._preflight_digest[:16]}…  "
              f"all_green={all_green}  (in the CORPUS, hashed at capture)", flush=True)
        return all_green

    def _seg_bump(self, name: str, n: int = 1) -> None:
        """WO-067 §2.3 — count into the CURRENT segment. Written into its record at close."""
        self._seg_counters[name] = self._seg_counters.get(name, 0) + n

    # ── the Kraken side: read the LIVE leg-3 segment tail ─────────────────────────────────────
    def _kraken_mid(self):
        """Most recent Kraken mid from the concurrently running leg 3, with its age.

        Measured at 0.87 ms mean over a live socket, so it does not pace the loop: the ~5.4 s
        inter-frame gap is the VENUE's slow-feed cadence, established by an l2Book-only probe.
        """
        if not self.kraken_dir:
            return None, None
        try:
            segs = sorted(self.kraken_dir.glob("*.jsonl"))
            if not segs:
                return None, None
            with open(segs[-1], "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 8192))
                lines = f.read().decode("utf-8", "replace").strip().split("\n")
            for ln in reversed(lines):
                ln = ln.strip()
                if not ln.startswith("{"):
                    continue
                d = json.loads(ln)
                m = (float(d["bid"]) + float(d["ask"])) / 2
                age = (datetime.now(UTC)
                       - datetime.fromisoformat(d["timestamp"])).total_seconds()
                return m, age
        except Exception:                                             # noqa: BLE001
            return None, None
        return None, None

    def _finalize(self, started: datetime):
        """Write everything a reader needs. Called from `finally` — and everything important here
        has ALREADY been written incrementally, because a finally block is exactly what a forced
        reboot does not reach."""
        self._close_segment()
        self.gaps.append({"event": "run_end", "utc": datetime.now(UTC).isoformat(),
                          **self.counters})
        (self.run_dir / "gap_ledger.json").write_text(
            "\n".join(json.dumps(g) for g in self.gaps) + "\n", encoding="utf-8")
        manifest = {
            "run_id": self.run_id, "corpus_id": self.ledger.corpus_id,
            "venue": "hyperliquid_mainnet", "symbol": hl.SYMBOL,
            "feeds": list(self.feeds),
            "feed_levels": {f: hl.FEED_LEVELS[f] for f in self.feeds},
            "per_feed_counters": self.per_feed,
            "start_utc": started.isoformat(), "end_utc": datetime.now(UTC).isoformat(),
            "segments": [s.to_dict() for s in self.segments],
            "gap_causes_declared": list(hl.GAP_CAUSES),
            "gap_cause_absent": hl.CAUSE_ABSENT_FROM_THIS_VENUE,
            "checksum_failures_total": None,
            "checksum_absent_reason": hl.CAUSE_ABSENT_FROM_THIS_VENUE["CHECKSUM_RESYNC"],
            "EVIDENTIARY_BOUND": mit.EVIDENTIARY_BOUND,
            "declared_levels": mit.DECLARED_LEVELS,
            "counters": self.counters,
            # WO-067 §2.1/§2.2 — the band is a ROLLING object, so the manifest reports its
            # configuration and its current state, never a single frozen tuple presented as
            # "the band" for the whole run. There was no single band.
            "band_rolling": {
                "window_s": self.band.window_s,
                "cadence_s": self.band.cadence_s,
                "k": self.band.k,
                "min_samples": self.band.min_samples,
                "alignment_tolerance_s": self.band.alignment_tolerance_s,
                "derivations": self.band.derivations,
                "derived_at_end": self.band.derived,
                "final_band": self.band.band.__dict__ if self.band.derived else None,
                "measured_drift_bps_per_h_ceiling": mit.BAND_MEASURED_DRIFT_BPS_PER_H,
            },
            "counterpart": {
                "declared_dependency": True,
                "liveness_bound_s": self.counterpart.bound_s,
                "ever_seen": self.counterpart.ever_seen,
                "stale_transitions": self.counterpart.stale_transitions,
            },
            "tape_bound": self.tape.__dict__ if self.tape else None,
            "staleness_bound": {f: (b.__dict__ if b else None)
                                for f, b in self.stale.items()},
            # Which guards were ARMED. A reader must be able to tell a corpus that was guarded
            # from one whose bounds never derived — they are different evidence.
            "guards_active": {
                # THREE STATES, not a boolean. A reader must be able to tell a guarded corpus
                # from an unguarded one from one whose guard never derived — the count:0 /
                # count:null doctrine applied to the guard itself.
                "cross_venue_band": {
                    "states": list(mit.GUARD_STATES),
                    "derived_at_end": self.band.derived,
                    "frames_guarded": self.counters.get("frames_emitted", 0)
                                      - self.counters.get("unguarded_frames", 0),
                    "frames_unguarded": self.counters.get("unguarded_frames", 0),
                    "unguarded_counterpart_stale":
                        self.counters.get("unguarded_counterpart_stale", 0),
                    "unguarded_band_underived":
                        self.counters.get("unguarded_band_underived", 0),
                },
                "tape_vs_book": self.tape is not None,
                "staleness": {f: self.stale[f] is not None for f in self.feeds},
            },
        }
        (self.run_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2),
                                                    encoding="utf-8")
        first, last = run_frame_bounds(self.run_dir, SEGMENT_PATTERNS)
        self.ledger.add_run(RunRecord(
            run_id=self.run_id, start_utc=started.isoformat(),
            end_utc=datetime.now(UTC).isoformat(),
            first_frame_utc=first or self._first_frame_utc,
            last_frame_utc=last or self._last_frame_utc,
            segments=self.segments,
            # The run record NAMES its preflight and its digest, so the manifest alone is enough
            # to find and verify the conditions this run started under.
            preflight={
                "venue": "hyperliquid_mainnet",
                "filename": PREFLIGHT_FILENAME,
                "sha256": self._preflight_digest,
                "hashed_at_capture": self._preflight_digest is not None,
                "all_green": self._preflight_all_green,
                "terms": 12,
            },
            finalized=True,
        ))
        print(f"[run] finalized — {self.counters}", flush=True)

    async def run(self, seam=None):
        deadline = time.monotonic() + self.duration_s
        calib_until = time.monotonic() + CALIBRATION_MINUTES * 60
        started = datetime.now(UTC)
        adapter = hl.HyperliquidBookAdapter(mode=hl.HyperliquidBookAdapter.MODE_LIVE,
                                            feeds=self.feeds)
        calibrated = False
        last_liveness = time.monotonic()
        print(f"[run] connecting {hl.WS_URL}  duration {self.duration_s/3600:.1f} h", flush=True)
        print(f"[run] CALIBRATION for {CALIBRATION_MINUTES} min — mitigations 4.1/4.3 MEASURE "
              f"ONLY until their bounds are derived from data (a band that has not been measured "
              f"cannot refuse anything honestly)", flush=True)
        self.gaps.append({"event": "run_start", "utc": started.isoformat(),
                          "venue": "hyperliquid_mainnet", "mode": "live",
                          "run_id": self.run_id, "corpus_id": self.ledger.corpus_id})
        gap_id = 0
        try:
            while time.monotonic() < deadline:
                try:
                    async with websockets.connect(hl.WS_URL, ping_interval=20,
                                                  ping_timeout=20) as ws:
                        for sub in adapter.subscriptions():
                            await ws.send(json.dumps(sub))
                        pending_trades: list = []
                        while time.monotonic() < deadline:
                            raw = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
                            kind = adapter.process_raw_frame(raw)
                            if kind["kind"] == "trades":
                                pending_trades.extend(kind["trades"])
                                continue
                            if kind["kind"] != "book":
                                continue
                            book = kind["book"]
                            bfeed = getattr(book, "feed", hl.FEED_SLOW)
                            now = time.monotonic()
                            prev_mono = self._last_book_mono.get(bfeed)
                            if prev_mono is not None:
                                self._gaps_s.setdefault(bfeed, []).append(now - prev_mono)
                            km, kdt = self._kraken_mid()

                            # Always MEASURE the basis — the band is derived from it.
                            bid0 = float(book.bids[0].px) if book.bids else 0
                            ask0 = float(book.asks[0].px) if book.asks else 0
                            if km and bid0 and ask0:
                                self._log_bases.append(math.log(((bid0 + ask0) / 2) / km))

                            # CALIBRATION ENDS -> derive every bound ONCE, from measured data.
                            # Each `derive` returns None below its sample floor, which leaves that
                            # guard INACTIVE and says so. A bound that was never measured cannot
                            # refuse anything honestly, and defaulting one would be a guess wearing
                            # a measurement's authority.
                            if time.monotonic() >= calib_until and not calibrated:
                                calibrated = True
                                # WO-067 §2.1 — THE BAND IS NO LONGER DERIVED HERE. It rolls,
                                # fed by `observe()` on every arrival, so there is no instant at
                                # which it is fitted and frozen. Deriving it once here is exactly
                                # the defect this WO repairs; the line is deliberately absent
                                # rather than left assigning a value nothing reads.
                                self.tape = mit.TapeBookBound.derive(self._tape_distances, TICK)
                                for f in self.feeds:
                                    self.stale[f] = mit.StalenessBound.derive(
                                        self._gaps_s.get(f, []))
                                print(f"[calib] band=ROLLING window={self.band.window_s:.0f}s "
                                      f"cadence={self.band.cadence_s:.0f}s "
                                      f"derived={self.band.derived} "
                                      f"derivations={self.band.derivations} "
                                      f"samples={self.band.sample_count}", flush=True)
                                print(f"[calib] tape={self.tape}", flush=True)
                                for f in self.feeds:
                                    print(f"[calib] staleness[{f}]={self.stale[f]}", flush=True)
                                inactive = ([n for n, b in (
                                                ("cross_venue_band",
                                                 self.band.band if self.band.derived else None),
                                                ("tape_vs_book", self.tape))
                                             if b is None]
                                            + [f"staleness[{f}]" for f in self.feeds
                                               if self.stale[f] is None])
                                if inactive:
                                    print(f"[calib] INSUFFICIENT SAMPLES for {inactive} — those "
                                          f"guards remain INACTIVE and the manifest will say so.",
                                          flush=True)

                            # EMIT ALWAYS. During calibration band/stale are None so no check
                            # fires, but the FRAMES ARE STILL WRITTEN — discarding the calibration
                            # hour would leave a hole in the corpus, which is a worse defect than
                            # a late guard.
                            self._emit(book, pending_trades, km, kdt)
                            pending_trades = []

                            # ── IN-FLIGHT LIVENESS. A guard took a feed offline for 5 h 39 m on
                            # 2026-08-13 and nothing said so: the refusal counters exist but are
                            # written only at run end, so a 24-hour run could not observe its own
                            # suppression until it was over. This is NOT a guard — it refuses
                            # nothing and changes no data. It exists so that a feed which has gone
                            # dark is LOUD while there is still time to act on it.
                            if now - last_liveness >= LIVENESS_CHECK_S:
                                last_liveness = now
                                for f in self.feeds:
                                    em = self._last_emitted_mono.get(f)
                                    dark = (now - em) if em is not None else None
                                    if dark is not None and dark >= LIVENESS_DARK_S:
                                        print(f"[LIVENESS] *** FEED {f.upper()} HAS WRITTEN NO "
                                              f"FRAME FOR {dark:.0f}s *** arrivals are still "
                                              f"reaching us, so this is SUPPRESSION, not silence. "
                                              f"refused_staleness={self.per_feed[f]['refused_staleness']} "
                                              f"refused_band={self.per_feed[f]['refused_cross_venue_band']} "
                                              f"refused_tape={self.per_feed[f]['refused_tape_vs_book']}",
                                              flush=True)

                            # The seam's right bound is THIS run's first frame — close it the
                            # moment one exists, so an unresumed seam stays loud.
                            if seam is not None and not seam.resolved and self._first_frame_utc:
                                self.ledger.close_seam(seam, self._first_frame_utc)
                                print(f"[seam] closed on first frame {self._first_frame_utc} "
                                      f"— width {seam.duration_seconds:.3f} s", flush=True)
                except Exception as exc:                              # noqa: BLE001
                    self.gaps.append({"event": "open", "gap_id": gap_id,
                                      "cause": "VENUE_DISCONNECT",
                                      "reason_code": "VENUE_DISCONNECT",
                                      "utc": datetime.now(UTC).isoformat(),
                                      "detail": f"{type(exc).__name__}: {str(exc)[:120]}"})
                    print(f"[gap {gap_id}] VENUE_DISCONNECT {type(exc).__name__}", flush=True)
                    gap_id += 1
                    await asyncio.sleep(2)
        finally:
            self._finalize(started)


def _preflight_reboot_window(hours: float) -> None:
    """WO-066 §2 term 11, EXECUTED — the run refuses to start inside a permitted reboot window.

    0.14: this is term 11's production call site. It was an operator declaration read from an
    environment variable, which is a statement that cannot be false; it read GREEN while the host
    was five hours from a Windows Update restart that destroyed the run. It now MEASURES.

    THERE IS NO OVERRIDE FLAG, AND THAT IS DELIBERATE. A first draft carried
    `--accept-reboot-risk`, which recorded an override rather than granting a pass. It was removed
    before the gate ever ran in anger: **a flag whose only function is to walk past a RED gate is
    a documented path around the guard**, and this project's record is that gates die exactly that
    way — the declaration this gate replaced was itself a documented way of asserting safety
    without measuring it. Pausing Windows Update is the remedy; the gate then goes GREEN on its
    own, by reading `PauseUpdatesExpiryTime`, with nobody's word involved.
    """
    policy = reboot_window.read_host_policy()
    verdict = reboot_window.evaluate(policy, datetime.now().astimezone(), hours)
    print("=" * 96)
    print("[term 11] shutdown_policy_disabled — MEASURED, not declared")
    print(f"[term 11] {'GREEN' if verdict.green else 'RED'}  {verdict.reason}")
    for a, b in verdict.permitted_windows:
        print(f"[term 11]   permitted reboot window inside this run: "
              f"{a.strftime('%Y-%m-%d %H:%M')} -> {b.strftime('%Y-%m-%d %H:%M')} local")
    print(f"[term 11] falsifier: {verdict.falsifier}")
    print("=" * 96, flush=True)
    if verdict.green:
        return
    raise SystemExit(
        "HL_CAPTURE_REBOOT_WINDOW_REFUSED: the run window overlaps a window in which Windows is "
        "permitted to restart this host. Pause Windows Update past the end of the run. There is "
        "no override: a run that a forced restart can end is not a 24-hour observation."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration-hours", type=float, default=24.0)
    ap.add_argument("--corpus-id", required=True)
    ap.add_argument("--kraken-run-dir", default="")
    ap.add_argument("--seam-cause", default="",
                    help="REQUIRED when resuming a corpus that already has runs. One of "
                         "PROCESS_RESTART / POLICY_SHUTDOWN / OPERATOR_STOP — declared, never "
                         "guessed, because the process cannot observe why it was killed.")
    ap.add_argument("--feeds", default="slow,fast",
                    help="which l2Book feeds to subscribe. Default BOTH (ratified §3.4): slow "
                         "carries the 20-level evidentiary bound at a MEASURED 5.41 s cadence, "
                         "fast carries 5 levels at 0.52 s and is the only feed against which "
                         "tape-vs-book reconciles (2.5 vs 33.3 pct refusal).")
    args = ap.parse_args()
    if os.environ.get("TRADING_ENV") != "paper":
        raise SystemExit("HL_CAPTURE_ENV_REFUSED: TRADING_ENV must be 'paper'")

    _preflight_reboot_window(args.duration_hours)

    ledger = CorpusLedger(CAPTURE_ROOT, args.corpus_id, host=platform.node(),
                          segment_patterns=SEGMENT_PATTERNS)
    reconciled = ledger.reconcile()
    if reconciled:
        print(f"[corpus] reconciled {len(reconciled)} run(s) found on disk but not finalized: "
              f"{reconciled}  (hashes recomputed at rest -> hashed_at_capture=False)", flush=True)

    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    seam = None
    prior = ledger.prior_run()
    # WO-066 queue item (a): validate the DECLARED cause before the branch that consumes it.
    # `open_seam` checks the cause against the closed set, but it is only reached when a prior
    # run exists — so a cause declared against an empty corpus directory was dropped in silence
    # and the run started as a first run. See `SeamCauseWithoutReferent`.
    try:
        require_seam_referent(prior, args.seam_cause, corpus_id=args.corpus_id,
                              corpus_root=CAPTURE_ROOT)
    except SeamCauseWithoutReferent as exc:
        # SystemExit, not a traceback: this file reports every operator-facing refusal that way
        # (see SEAM_CAUSE_UNDECLARED below), and a traceback reads as a crash rather than a gate.
        raise SystemExit(str(exc)) from exc
    if prior is not None:
        if not args.seam_cause:
            raise SystemExit(
                f"SEAM_CAUSE_UNDECLARED: corpus {args.corpus_id!r} already holds run "
                f"{prior.run_id!r}. A resume must DECLARE why the prior run ended "
                f"(--seam-cause POLICY_SHUTDOWN|PROCESS_RESTART|OPERATOR_STOP). The process "
                f"cannot observe it and a guessed cause is a smoothed seam."
            )
        seam = ledger.open_seam(cause=args.seam_cause, prior_run_id=prior.run_id,
                                resumed_run_id=run_id,
                                prior_last_frame_utc=prior.last_frame_utc,
                                detail="Hyperliquid spike resume")
        print(f"[seam] OPEN  cause={args.seam_cause}  left bound {prior.last_frame_utc} "
              f"(prior run {prior.run_id}) — stays open, denying every query, until this run's "
              f"first frame", flush=True)

    p = ledger.progress()
    print(f"[corpus] {args.corpus_id}: {p.get('cumulative_covered_hours', 0):.4f} covered h "
          f"across {len(ledger.manifest.runs)} run(s), {p.get('seam_count', 0)} seam(s)",
          flush=True)

    feeds = tuple(f.strip() for f in args.feeds.split(",") if f.strip())
    unknown = [f for f in feeds if f not in hl.FEED_LEVELS]
    if unknown:
        raise SystemExit(f"HL_CAPTURE_FEED_UNKNOWN: {unknown} — choose from "
                         f"{sorted(hl.FEED_LEVELS)}")
    print(f"[feeds] {list(feeds)}  levels={[hl.FEED_LEVELS[f] for f in feeds]}", flush=True)

    kd = pathlib.Path(args.kraken_run_dir) if args.kraken_run_dir else None
    cap = HyperliquidCapture(ledger, run_id, args.duration_hours * 3600, kd, feeds=feeds)

    # ── WO-067 — THE TWELVE-TERM PREFLIGHT, EXECUTED AND RECORDED IN THE CORPUS ──────────────
    #
    # Before the counterpart probe and long before the socket. A RED term stops the run here, with
    # the record already on disk and hashed: a refused launch is exactly the case where you most
    # want to know which conditions were RED, and WO-066's four failed launches left no corpus
    # artifact saying so.
    if not cap._write_preflight_record():
        raise SystemExit(
            "HL_PREFLIGHT_RED: one or more of the twelve terms is RED — see "
            f"{cap.run_dir / PREFLIGHT_FILENAME} for which. No socket opened. The record is "
            "written and hashed regardless of the verdict, because a refused launch is worth "
            "auditing too."
        )

    # ── WO-067 §2.2 — THE COUNTERPART DEPENDENCY, ENFORCED BEFORE THE SOCKET OPENS ────────────
    #
    # The third state. A counterpart that goes stale MID-RUN degrades the guard to UNGUARDED and
    # the capture continues, marking frames — those are still true observations of Hyperliquid.
    # A counterpart that was NEVER there is different in kind: there is no basis to derive a band
    # from and no window to warm up, so the cross-venue guard could never become active and every
    # frame of the whole run would be unguarded. Declaring a dependency is worth nothing if the
    # process starts anyway and finds out hours later — which is precisely how WO-066 discovered
    # it. So this is checked HERE, before the socket, and it REFUSES (0.9).
    probe_mid, probe_dt = cap._kraken_mid()
    if probe_mid:
        cap.counterpart.observe(time.time() - (probe_dt or 0.0))
    try:
        cap.counterpart.require_available_at_start()
    except mit.CounterpartNeverAvailable as exc:
        raise SystemExit(
            f"{exc}\n"
            f"           --kraken-run-dir = {kd if kd else '(not passed)'}\n"
            f"           Probed for the newest Kraken frame and found none. Start the counterpart "
            f"capture and point --kraken-run-dir at its RUN directory."
        ) from exc
    print(f"[counterpart] LIVE — newest Kraken frame {probe_dt:.3f}s old, liveness bound "
          f"{cap.counterpart.bound_s:.0f}s. Declared dependency satisfied at start; if it goes "
          f"stale mid-run the band drops to UNGUARDED and frames are MARKED, not refused.",
          flush=True)

    asyncio.run(cap.run(seam=seam))

    p = ledger.progress()
    print(f"[corpus] {args.corpus_id}: {p.get('cumulative_covered_hours', 0):.4f} covered h "
          f"of {args.duration_hours:g} target", flush=True)


if __name__ == "__main__":
    main()
