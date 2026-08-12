"""WO-066 §3 — THE HYPERLIQUID CAPTURE SPIKE. Read-only. No order path.

    python tools/hyperliquid_capture.py --duration-hours 24 --corpus-id hlspike_YYYYMMDD

§3.2 DURATION, DERIVED (0.15): WO-065 took five instants and its fifth read misrepresented dYdX by
38x against the other four. Snapshots cannot be superseded by more snapshots — only by CONTINUOUS
observation long enough to contain the regimes they missed. BTC liquidity is diurnal (Asia, Europe,
US sessions), so the shortest window that contains every session once is **24 hours**. Rounded up
from "one full diurnal cycle" and declared here.

§3.3 CORPUS DISCIPLINE — per element, transfers or adapts:
  segments (hourly JSONL)          TRANSFERS UNCHANGED
  capture-time SHA-256 per segment TRANSFERS UNCHANGED — hashed at rotation, before anything reads
  MANIFEST.json                    TRANSFERS UNCHANGED (same shape; venue field differs)
  gap ledger                       ADAPTS — FOUR causes; CHECKSUM_RESYNC absent (ratified)
  default-deny reader              TRANSFERS — it reads the ledger, not the venue
  checksum_failures_total          ADAPTS — reported as None, never 0 (WO-054's count:0 vs null)

§4 MITIGATIONS ARE WIRED HERE (0.14 — this file is their production call site):
  4.1 cross-venue band    -> `_emit()` refuses when the band is exceeded
  4.2 tape-vs-book        -> `_emit()` refuses when a print cannot be reconciled
  4.3 staleness           -> `_emit()` refuses a snapshot older than the derived bound
  4.4 evidentiary bound   -> declared in the manifest; level count recorded per frame
An unwired mitigation is the WO-055 defect; each refusal SUPPRESSES THE FRAME (0.9), it does not
merely log.

**NO ORDER PATH.** This module sends only `subscribe` and `ping`.
"""

import argparse
import asyncio
import gzip
import hashlib
import json
import os
import pathlib
import sys
import time
from datetime import UTC, datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _ROOT)

import websockets                                                     # noqa: E402

from trading.data.adapters import hyperliquid_v1 as hl                # noqa: E402
from trading.data import hyperliquid_mitigations as mit               # noqa: E402

TICK = 1.0            # observed on the BTC perp book (WO-065: spread pinned at 1.0 USD)
CALIBRATION_MINUTES = 60


class HyperliquidCapture:
    def __init__(self, run_dir: pathlib.Path, duration_s: float, kraken_dir: pathlib.Path | None):
        self.run_dir = run_dir
        self.duration_s = duration_s
        self.kraken_dir = kraken_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        self.segments: list = []
        self.gaps: list = []
        self.counters = {k: 0 for k in mit.COUNTERS}
        self.counters["frames_emitted"] = 0
        self.counters["frames_refused"] = 0
        self.band: mit.CrossVenueBand | None = None
        self.stale: mit.StalenessBound | None = None
        self._log_bases: list = []
        self._gaps_s: list = []
        self._last_book_mono: float | None = None
        self._seg_path: pathlib.Path | None = None
        self._seg_fh = None
        self._seg_hour: str | None = None
        self._seg_frames = 0

    # ── segment rotation with capture-time hashing ────────────────────────────────────────────
    def _rotate(self, ts: datetime):
        hour = ts.strftime("%Y%m%dT%HZ")
        if hour == self._seg_hour:
            return
        self._close_segment()
        self._seg_hour = hour
        self._seg_path = self.run_dir / f"hl_BTC_{hour}.jsonl"
        self._seg_fh = open(self._seg_path, "a", encoding="utf-8")
        self._seg_frames = 0

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
        self.segments.append({"filename": self._seg_path.name, "sha256": digest,
                              "frame_count": self._seg_frames,
                              "size_bytes": self._seg_path.stat().st_size,
                              "hashed_at_capture": True})
        print(f"[segment] {self._seg_path.name}  {self._seg_frames} frames  sha256 {digest[:16]}…",
              flush=True)
        self._seg_fh = None

    # ── the emission path — every mitigation gates it (0.9/0.14) ──────────────────────────────
    def _emit(self, book, trades, kraken_mid, kraken_dt):
        now_mono = time.monotonic()
        wall = datetime.now(UTC)
        bid = float(book.bids[0].px) if book.bids else 0.0
        ask = float(book.asks[0].px) if book.asks else 0.0
        mid = (bid + ask) / 2 if bid and ask else 0.0

        refusals = []

        # 4.3 staleness
        if self.stale is not None and self._last_book_mono is not None:
            v = self.stale.check(now_mono - self._last_book_mono)
            if v.refuse:
                refusals.append(v)
                self.counters["refused_staleness"] += 1

        # 4.1 cross-venue band
        if self.band is not None and kraken_mid:
            v = self.band.check(kraken_mid, mid, kraken_dt)
            if v.refuse:
                refusals.append(v)
                self.counters["refused_cross_venue_band"] += 1

        # 4.2 tape vs book
        for t in trades:
            v = mit.check_tape_vs_book(float(t.px), bid, ask, TICK)
            if v.refuse:
                refusals.append(v)
                self.counters["refused_tape_vs_book"] += 1
                break

        # 4.4 evidentiary bound — flags, never refuses
        lv = mit.check_declared_levels(book.levels_published)
        if lv.reason:
            self.counters["observed_levels_below_declared"] += 1

        if refusals:
            self.counters["book_consistency_failures_total"] += 1
            self.counters["frames_refused"] += 1
            return                       # THE FRAME IS SUPPRESSED — not merely logged (0.9)

        self._rotate(wall)
        rec = {
            "timestamp": wall.isoformat(), "symbol": hl.SYMBOL, "venue": "hyperliquid_mainnet",
            "bid": str(book.bids[0].px) if book.bids else None,
            "ask": str(book.asks[0].px) if book.asks else None,
            "bid_qty": str(book.bids[0].sz) if book.bids else None,
            "ask_qty": str(book.asks[0].sz) if book.asks else None,
            "levels_published": book.levels_published,
            "venue_time_ms": book.venue_time_ms,
            "trades": [{"px": str(t.px), "sz": str(t.sz), "side": t.side} for t in trades],
            "kraken_mid": kraken_mid, "kraken_dt_s": kraken_dt,
        }
        self._seg_fh.write(json.dumps(rec) + "\n")
        # WRITE-THROUGH. An open buffered handle over a 24-hour run holds frames in memory,
        # and a process death loses them — the capture-time hash would then certify a file
        # that never contained what the run observed. The feed is >=0.5 s cadence, so a
        # per-frame flush costs nothing.
        self._seg_fh.flush()
        self._seg_frames += 1
        self.counters["frames_emitted"] += 1
        self._last_book_mono = now_mono

    # ── the Kraken side: read the LIVE leg-3 segment tail ─────────────────────────────────────
    def _kraken_mid(self):
        """Most recent Kraken mid from the concurrently running leg 3, with its age."""
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

    async def run(self):
        deadline = time.monotonic() + self.duration_s
        calib_until = time.monotonic() + CALIBRATION_MINUTES * 60
        started = datetime.now(UTC)
        print(f"[run] connecting {hl.WS_URL}  duration {self.duration_s/3600:.1f} h", flush=True)
        print(f"[run] CALIBRATION for {CALIBRATION_MINUTES} min — mitigations 4.1/4.3 MEASURE "
              f"ONLY until their bounds are derived from data (a band that has not been measured "
              f"cannot refuse anything honestly)", flush=True)
        self.gaps.append({"event": "run_start", "utc": started.isoformat(),
                          "venue": "hyperliquid_mainnet", "mode": "live"})
        gap_id = 0
        while time.monotonic() < deadline:
            try:
                async with websockets.connect(hl.WS_URL, ping_interval=20,
                                              ping_timeout=20) as ws:
                    for sub in hl.HyperliquidBookAdapter().subscriptions():
                        await ws.send(json.dumps(sub))
                    pending_trades: list = []
                    while time.monotonic() < deadline:
                        raw = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
                        kind = HL_ADAPTER.process_raw_frame(raw)
                        if kind["kind"] == "trades":
                            pending_trades.extend(kind["trades"])
                            continue
                        if kind["kind"] != "book":
                            continue
                        book = kind["book"]
                        now = time.monotonic()
                        if self._last_book_mono is not None:
                            self._gaps_s.append(now - self._last_book_mono)
                        km, kdt = self._kraken_mid()

                        # Always MEASURE the basis — the band is derived from it.
                        bid0 = float(book.bids[0].px) if book.bids else 0
                        ask0 = float(book.asks[0].px) if book.asks else 0
                        if km and bid0 and ask0:
                            import math
                            self._log_bases.append(math.log(((bid0 + ask0) / 2) / km))

                        # CALIBRATION ENDS -> derive the bounds ONCE, from measured data.
                        if time.monotonic() >= calib_until and self.band is None:
                            self.band = mit.CrossVenueBand.derive(self._log_bases)
                            self.stale = mit.StalenessBound.derive(self._gaps_s)
                            print(f"[calib] band={self.band}", flush=True)
                            print(f"[calib] staleness={self.stale}", flush=True)
                            if self.band is None or self.stale is None:
                                print("[calib] INSUFFICIENT SAMPLES — guards remain INACTIVE and "
                                      "the manifest will say so. A bound that was never measured "
                                      "cannot refuse anything honestly.", flush=True)

                        # EMIT ALWAYS. During calibration band/stale are None so no check fires,
                        # but the FRAMES ARE STILL WRITTEN — discarding the calibration hour would
                        # leave a hole in the corpus, which is a worse defect than a late guard.
                        self._emit(book, pending_trades, km, kdt)
                        pending_trades = []
            except Exception as exc:                                  # noqa: BLE001
                self.gaps.append({"event": "open", "gap_id": gap_id,
                                  "cause": "VENUE_DISCONNECT",
                                  "reason_code": "VENUE_DISCONNECT",
                                  "utc": datetime.now(UTC).isoformat(),
                                  "detail": f"{type(exc).__name__}: {str(exc)[:120]}"})
                print(f"[gap {gap_id}] VENUE_DISCONNECT {type(exc).__name__}", flush=True)
                gap_id += 1
                await asyncio.sleep(2)
        self._close_segment()
        self.gaps.append({"event": "run_end", "utc": datetime.now(UTC).isoformat(),
                          **self.counters})
        (self.run_dir / "gap_ledger.json").write_text(
            "\n".join(json.dumps(g) for g in self.gaps) + "\n", encoding="utf-8")
        manifest = {
            "run_id": self.run_dir.name, "venue": "hyperliquid_mainnet", "symbol": hl.SYMBOL,
            "start_utc": started.isoformat(), "end_utc": datetime.now(UTC).isoformat(),
            "segments": self.segments,
            "gap_causes_declared": list(hl.GAP_CAUSES),
            "gap_cause_absent": hl.CAUSE_ABSENT_FROM_THIS_VENUE,
            "checksum_failures_total": None,
            "checksum_absent_reason": hl.CAUSE_ABSENT_FROM_THIS_VENUE["CHECKSUM_RESYNC"],
            "EVIDENTIARY_BOUND": mit.EVIDENTIARY_BOUND,
            "declared_levels": mit.DECLARED_LEVELS,
            "counters": self.counters,
            "band": self.band.__dict__ if self.band else None,
            "staleness_bound": self.stale.__dict__ if self.stale else None,
        }
        (self.run_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2),
                                                    encoding="utf-8")
        print(f"[run] complete — {self.counters}", flush=True)


HL_ADAPTER = hl.HyperliquidBookAdapter(mode=hl.HyperliquidBookAdapter.MODE_LIVE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration-hours", type=float, default=24.0)
    ap.add_argument("--corpus-id", required=True)
    ap.add_argument("--kraken-run-dir", default="")
    args = ap.parse_args()
    if os.environ.get("TRADING_ENV") != "paper":
        raise SystemExit("HL_CAPTURE_ENV_REFUSED: TRADING_ENV must be 'paper'")
    run_dir = (pathlib.Path("captures/hyperliquid") / args.corpus_id
               / datetime.now(UTC).strftime("%Y%m%d%H%M%S"))
    kd = pathlib.Path(args.kraken_run_dir) if args.kraken_run_dir else None
    asyncio.run(HyperliquidCapture(run_dir, args.duration_hours * 3600, kd).run())


if __name__ == "__main__":
    main()
