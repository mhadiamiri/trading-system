"""
WO-066 §4 — THE FOUR MITIGATIONS for a checksumless feed.

Hyperliquid publishes **no checksum, no sequence number, no version**. Kraken's CRC32 answers
*"is my book byte-identical to the venue's?"* — a statement about CORRECTNESS, verified against the
venue's own authority. **Nothing here can answer that question**, because Hyperliquid publishes
nothing to check against.

**What these four establish is CONSISTENCY, not correctness** — see §4.5's verdict in the report.
They are named `book_consistency_failures_*`, never `checksum_failures_*`, because calling a
consistency counter a checksum counter would import a guarantee that does not exist. This project
has recorded that defect shape three times; it is not repeated here.

═══ 0.9 — EACH MITIGATION ASSERTS THE ECONOMIC EFFECT, NOT THE EVENT RECORD ═════════════════════

A mitigation that logs a divergence and lets the system act on suspect data is a log line, not a
guard. Every check here returns a **verdict whose REFUSE outcome suppresses emission** — the caller
is contractually required to drop the frame, and the capture tool does.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional


# ── the counter names. NOT checksum_*. ────────────────────────────────────────────────────────
COUNTERS = (
    "book_consistency_failures_total",
    "refused_cross_venue_band",
    "refused_tape_vs_book",
    "refused_staleness",
    "observed_levels_below_declared",
)

# The per-feed counters. §3.4 captures BOTH l2Book feeds, and a single set of totals would average
# a 0.52 s stream against a 5.4 s one — hiding exactly the difference the dual subscription exists
# to measure.
PER_FEED_COUNTERS = ("frames_emitted", "frames_refused", "refused_staleness",
                     "refused_tape_vs_book", "refused_cross_venue_band")


@dataclass(frozen=True)
class Verdict:
    """A mitigation's answer. `refuse=True` means the frame MUST NOT be emitted (0.9)."""

    refuse: bool
    reason: str = ""
    detail: dict = field(default_factory=dict)


# ═══ 4.1 CROSS-VENUE PRICE GUARD ═════════════════════════════════════════════════════════════
#
# 0.16 MECHANISM STATEMENT, AT DECLARATION — this is where the rule most applies in the project.
#
#   LEFT  : Kraken BTC/USD SPOT mid = (bid+ask)/2 from a continuous quote process on Kraken,
#           timestamped by OUR capture's wall clock.
#   RIGHT : Hyperliquid BTC-PERP mid = (bid+ask)/2 from a snapshot feed on Hyperliquid,
#           timestamped by the VENUE's own `time` field.
#
#   THEY ARE NOT THE SAME QUANTITY. A perpetual trades at a BASIS to spot — funding exists
#   precisely because the two prices differ and are pulled together. The basis is real, it is not
#   noise, and it VARIES.
#
#   THEY ARE NOT SIMULTANEOUS. Two venues, two clocks, and a >=0.5 s snapshot cadence on one side
#   against ~106 ms frames on the other. WO-061 measured OUR OWN wall clock running 0.848 s behind
#   Kraken's venue time, so a naive timestamp join is already known to be wrong by ~0.85 s.
#
#   THEREFORE: a band derived as if the two should MATCH is the F6 error — bounding two quantities
#   by a rule that only holds for simultaneous ones. The band is derived from the MEASURED basis
#   distribution over the concurrent window, plus a stated timestamp-alignment tolerance.
#
# THE BAND, and why it is built this way:
#   centre    = median of the measured log-basis  ->  the basis LEVEL, which is expected and is not
#               a defect. Centring on it means the guard tests DEVIATION FROM NORMAL BASIS, not the
#               existence of basis.
#   half-width= k * (p99.5 - p0.5)/2 of the measured log-basis, k declared below.
#   A band narrower than the ordinary excursion would refuse ordinary data — "worse than no guard".

BAND_K = 1.5                      # widening factor on the measured p0.5..p99.5 half-range
BAND_MIN_SAMPLES = 300            # below this the band is NOT DERIVED and the guard stays inactive
ALIGNMENT_TOLERANCE_S = 2.0       # timestamp-alignment tolerance, DERIVED below


@dataclass
class CrossVenueBand:
    """The measured band. Constructed by `derive()` from a calibration window — never guessed."""

    centre_log: float
    half_width_log: float
    n: int
    p005: float
    p995: float
    median_basis_bps: float
    alignment_tolerance_s: float = ALIGNMENT_TOLERANCE_S

    @classmethod
    def derive(cls, log_bases: list, k: float = BAND_K) -> Optional["CrossVenueBand"]:
        """Derive the band from measured log-basis samples, or None if there are too few.

        Returning None rather than a default is deliberate: an undeived band must leave the guard
        INACTIVE and say so, not silently pass everything with a made-up width.
        """
        if len(log_bases) < BAND_MIN_SAMPLES:
            return None
        s = sorted(log_bases)
        centre = statistics.median(s)
        p005 = s[max(0, int(0.005 * len(s)))]
        p995 = s[min(len(s) - 1, int(0.995 * len(s)))]
        half = k * (p995 - p005) / 2.0
        return cls(centre_log=centre, half_width_log=half, n=len(s), p005=p005, p995=p995,
                   median_basis_bps=(pow(2.718281828459045, centre) - 1) * 1e4)

    def check(self, kraken_mid: float, hl_mid: float, dt_seconds: float) -> Verdict:
        """REFUSE when the observed basis leaves the band, or the two reads are too far apart."""
        import math
        if abs(dt_seconds) > self.alignment_tolerance_s:
            return Verdict(True, "CROSS_VENUE_STALE_PAIR",
                           {"dt_seconds": dt_seconds,
                            "tolerance_s": self.alignment_tolerance_s})
        if kraken_mid <= 0 or hl_mid <= 0:
            return Verdict(True, "CROSS_VENUE_NONPOSITIVE_MID",
                           {"kraken_mid": kraken_mid, "hl_mid": hl_mid})
        lb = math.log(hl_mid / kraken_mid)
        dev = abs(lb - self.centre_log)
        if dev > self.half_width_log:
            return Verdict(True, "CROSS_VENUE_BAND_EXCEEDED",
                           {"log_basis": lb, "centre": self.centre_log,
                            "half_width": self.half_width_log,
                            "basis_bps": (pow(2.718281828459045, lb) - 1) * 1e4})
        return Verdict(False, "", {"log_basis": lb})


# ═══ 4.2 TAPE-VS-BOOK RECONCILIATION ═════════════════════════════════════════════════════════
#
# WHAT CONSISTENCY MEANS HERE, stated precisely rather than left to intuition:
#   A trade print must lie within [best_bid - tol, best_ask + tol] of the book we HOLD, where tol
#   is one tick. Prints occur AT the touch or through it; a print far outside the held quotes means
#   the book we hold is not the book that traded.
#
# WHAT IT CANNOT DETECT — the WO-063 line, applied honestly:
#   * A UNIFORMLY STALE PAIR. If book and tape lag together, every print sits inside the held
#     quotes and the check passes while both are wrong.
#   * ANYTHING BEYOND THE TOUCH. Prints only ever touch one level, so this says nothing about
#     levels 2..20 — exactly the depth a slippage figure depends on.
#   * A SUBTLY SHIFTED BOOK. A book displaced by less than the tolerance passes trivially.
#   Integrity failures are loud; semantic mismatches are silent, and this catches only the loud kind.

TAPE_BOOK_TICK_TOLERANCE = 1.0    # in ticks; the FLOOR, never the derived bound itself

# ── WHY THE TOLERANCE IS DERIVED AND NOT DECLARED ────────────────────────────────────────────
#
# A ONE-TICK tolerance was the first specification, and MEASURED against the live feed it refused
# **33.3% of slow-feed frames** (5 min, 57 book frames, 652 prints). The mechanism is the cadence:
# the slow feed publishes every ~5.4 s while the tape prints ~11 times in that interval, so the
# price walks and prints land where the book was at instants that were never published. The same
# measurement on the fast feed refuses 2.5%.
#
# **A guard that refuses a third of ordinary data is worse than no guard** — and worse here than
# elsewhere, because the refusals are not random: a frame is dropped precisely when price MOVED, so
# the surviving corpus is systematically calmer than the venue. A selection effect correlated with
# volatility is the one bias a market-data corpus must not have.
#
# So the bound is derived the way §4.1's band is: from the MEASURED reconciliation-distance
# distribution over the calibration window, returning None below the sample floor so that an
# underived bound leaves the guard INACTIVE and says so. Widening a guessed constant until the
# refusals stop would be tuning a bound to its data; deriving it states what ordinary
# reconciliation error on this feed actually is, and refuses what lies beyond it.
#
# WHAT THIS COSTS, STATED PLAINLY: the wider the ordinary error, the less the guard can detect. On
# the slow feed ordinary error reaches ~14 ticks, so a derived bound there catches only grossly
# dislocated prints. That is not a defect in the derivation — it is the feed's cadence showing
# through, and §4.5's residual must carry it rather than hide it behind a tighter-looking constant.

TAPE_BOOK_K = 1.5                 # widening factor on the measured p99.5 reconciliation distance
TAPE_BOOK_MIN_SAMPLES = 300


@dataclass
class TapeBookBound:
    """The measured tape-vs-book tolerance. Constructed by `derive()` — never guessed."""

    tolerance_abs: float          # price units, not ticks
    observed_p995: float
    n: int
    outside_fraction: float       # how often a print sat outside the touch at ONE tick

    @classmethod
    def derive(cls, distances: list, tick: float, k: float = TAPE_BOOK_K
               ) -> Optional["TapeBookBound"]:
        """Derive from measured per-print reconciliation distances (0.0 when inside the touch)."""
        if len(distances) < TAPE_BOOK_MIN_SAMPLES:
            return None
        s = sorted(distances)
        p995 = s[min(len(s) - 1, int(0.995 * len(s)))]
        return cls(tolerance_abs=max(TAPE_BOOK_TICK_TOLERANCE * tick, k * p995),
                   observed_p995=p995, n=len(s),
                   outside_fraction=sum(1 for d in s if d > 0) / len(s))

    def check(self, print_px: float, best_bid: float, best_ask: float) -> Verdict:
        return check_tape_vs_book(print_px, best_bid, best_ask, tick=1.0,
                                  tolerance_abs=self.tolerance_abs)


def reconciliation_distance(print_px: float, best_bid: float, best_ask: float,
                            tolerance_abs: float = 0.0) -> float:
    """How far a print lies BEYOND [bid - tol, ask + tol]. 0.0 means reconcilable.

    The quantity the bound is derived from, defined once so the derivation and the check cannot
    drift apart — measuring one thing and refusing on another is how a bound stops describing
    what it was derived from.
    """
    if print_px < best_bid - tolerance_abs:
        return (best_bid - tolerance_abs) - print_px
    if print_px > best_ask + tolerance_abs:
        return print_px - (best_ask + tolerance_abs)
    return 0.0


def check_tape_vs_book(print_px: float, best_bid: float, best_ask: float,
                       tick: float, tolerance_abs: Optional[float] = None) -> Verdict:
    """REFUSE when a print cannot be reconciled with the book we hold.

    `tolerance_abs` is the DERIVED bound when one exists. Falling back to one tick is deliberate
    for the invalid-quote case and for callers with no calibration window; the capture path never
    relies on it, because until the bound is derived it does not run this check at all.
    """
    if best_bid <= 0 or best_ask <= 0 or best_ask < best_bid:
        return Verdict(True, "TAPE_BOOK_INVALID_QUOTES",
                       {"bid": best_bid, "ask": best_ask})
    tol = TAPE_BOOK_TICK_TOLERANCE * tick if tolerance_abs is None else tolerance_abs
    d = reconciliation_distance(print_px, best_bid, best_ask, tol)
    if d > 0:
        return Verdict(True, "TAPE_OUTSIDE_HELD_BOOK",
                       {"print": print_px, "bid": best_bid, "ask": best_ask, "tol": tol,
                        "distance": d})
    return Verdict(False)


# ═══ 4.3 STALENESS AND LIVENESS BOUNDS — RE-DERIVED, NOT PORTED ══════════════════════════════
#
# The existing doctrine assumes Kraken's ~106 ms frame cadence. Hyperliquid publishes
# "on each block that is at least 0.5 since last push" — roughly 5x coarser — so a bound ported
# from Kraken would fire constantly on an ordinary Hyperliquid feed.
#
# THE BOUND IS DERIVED FROM THE OBSERVED CADENCE DISTRIBUTION, not the documented figure: the doc
# states a floor (">= 0.5 s"), not a ceiling, and a floor cannot bound staleness.

STALENESS_K = 6.0                 # multiple of the observed p99 inter-frame gap
STALENESS_MIN_SAMPLES = 300
STALENESS_FLOOR_S = 5.0           # never tighter than this, whatever the sample says


@dataclass
class StalenessBound:
    max_age_s: float
    observed_p99_s: float
    n: int

    @classmethod
    def derive(cls, gaps_s: list, k: float = STALENESS_K) -> Optional["StalenessBound"]:
        if len(gaps_s) < STALENESS_MIN_SAMPLES:
            return None
        s = sorted(gaps_s)
        p99 = s[min(len(s) - 1, int(0.99 * len(s)))]
        return cls(max_age_s=max(STALENESS_FLOOR_S, k * p99), observed_p99_s=p99, n=len(s))

    def check(self, age_s: float) -> Verdict:
        if age_s > self.max_age_s:
            return Verdict(True, "SNAPSHOT_STALE",
                           {"age_s": age_s, "max_age_s": self.max_age_s})
        return Verdict(False)


# ═══ 4.4 THE EVIDENTIARY BOUND — DECLARED, NOT MITIGATED ═════════════════════════════════════
#
# 5 or 20 levels is what the feed gives. This is NOT a defect to be guarded against; it is a
# LIMIT ON WHAT THE CORPUS CAN EVER SUPPORT, and the honest treatment is to declare it where a
# future reader will hit it rather than to pretend a mitigation closes it.

DECLARED_LEVELS = 20

EVIDENTIARY_BOUND = (
    "This corpus is captured from BOTH of Hyperliquid's l2Book feeds, and the two are NOT "
    "interchangeable. The SLOW feed publishes at most "
    f"{DECLARED_LEVELS} levels per side at a MEASURED ~5.41 s cadence; the FAST feed publishes 5 "
    "levels at ~0.52 s. Every frame carries a `feed` field taken from the venue's own `fast` "
    "marker, and a figure computed across both without separating them would average two "
    "different observations of the venue. "
    f"DEPTH BEYOND LEVEL {DECLARED_LEVELS} IS UNOBSERVED BY CONSTRUCTION on either feed, and "
    "depth beyond level 5 is unobserved at the fast cadence. Any figure requiring deeper book — "
    "slippage for an order larger than the cumulative 20-level notional, full-depth imbalance, or "
    "resting size beyond the top 20 — is UNAVAILABLE from this corpus and must not be estimated "
    "from it. Any figure requiring sub-5-second book resolution is available ONLY from the fast "
    "feed, and therefore only to level 5. "
    "The corpus's integrity property is CONSISTENCY, not correctness: the venue publishes no "
    "checksum, no sequence number and no version, so no mechanism here establishes that a "
    "snapshot matches the book Hyperliquid matched against."
)


def check_declared_levels(levels_published: int, declared: int = DECLARED_LEVELS) -> Verdict:
    """A feed that silently returns 5 where 20 was requested must be DETECTABLE.

    This does not refuse the frame — fewer levels is still true data about the touch. It flags,
    so `observed_levels_below_declared` can move and the corpus's own bound is auditable.

    `declared` is per-FEED (§3.4 subscribes both): the fast feed publishes 5 by contract, so
    judging its frames against 20 would report a short book on every one of them and the counter
    would stop meaning "the venue gave us less than it promised".
    """
    if levels_published < declared:
        return Verdict(False, "LEVELS_BELOW_DECLARED",
                       {"observed": levels_published, "declared": declared})
    return Verdict(False)
