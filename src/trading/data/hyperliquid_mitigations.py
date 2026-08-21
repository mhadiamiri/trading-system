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

import math
import statistics
from collections import deque
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



# ═══ 2.1 (WO-067) ROLLING RE-DERIVATION — THE REPAIR OF DEFECT #2 ════════════════════════════
#
# WHY THE FROZEN BAND FAILED, MEASURED RATHER THAN ASSERTED. Derived once and held, the band was
# consumed by drift alone. Measured over the WO-066 corpus, the hourly median basis moved:
#
#     leg 20260812025444 ( 5.09 h)   1.622 bps
#     leg 20260813015021 ( 7.16 h)   2.290 bps
#     leg 20260813105120 (15.13 h)   3.956 bps   <- right-CENSORED, so a LOWER BOUND
#     leg 20260814025236 ( 8.00 h)   3.167 bps
#
# against a half-width of only ~4.9 bps. A quantity that moves 3.2 bps in 8 h inside a +/-4.9 bps
# band leaves it in under a day, and it leaves in ONE DIRECTION — which is why the refusals were
# market-correlated rather than scattered. THIS IS THE FROZEN-BASELINE LESSON (D28/D29) ARRIVING
# AT BAND DERIVATION.
#
# THE CENSORING, DECLARED (0.12). Every leg above was captured THROUGH the frozen band, so the
# frames it refused are ABSENT FROM DISK. leg 20260813105120's maximum observed basis is
# +10.408 bps against that leg's ceiling of +10.41 — pinned within 0.002 bps, which is the
# truncation visible in the data. Measured drift is therefore a LOWER BOUND on true drift, and any
# refusal rate replayed over this corpus is OPTIMISTIC. The rolling-vs-frozen COMPARISON is
# unaffected: both replay the same censored stream.
#
# ── DERIVE FROM ARRIVALS, GATE ON EMISSION ────────────────────────────────────────────────────
#
# The trailing window is fed by every basis observation that ARRIVES, never by the frames the band
# chose to emit. A band re-derived from its own emitted output consumes its own filtered tail and
# ratchets tighter on every cycle — strictly WORSE than freezing, because the failure compounds
# instead of merely persisting. Structurally the same defect as the §4.3 latch, where the emit path
# returned before advancing the clock staleness was measured against: arrival must advance
# unconditionally, and the verdict must be diagnostic only.
#
# ── THE WINDOW: 120 min, derived, not tuned ───────────────────────────────────────────────────
#
#   FLOOR   — sample count. The slow feed publishes at 0.200/s, so BAND_MIN_SAMPLES=300 needs
#             1500 s = 25 min of slow-only arrivals. Round up (0.15): a 30 min floor.
#   CEILING — drift smearing. Drift <= 3.167 bps / 8 h = 0.396 bps/h; round up (0.15) to
#             0.5 bps/h. Over a window W the window's OWN spread is inflated by roughly
#             drift x W, and inflating a ~5 bps half-width by more than ~20% (1 bps) makes the
#             band describe its own drift rather than the basis distribution. W <= 1/0.5 = 2 h.
#   CHOICE  — 120 min sits at the ceiling, four times the sample floor. Wider windows buy a lower
#             refusal rate only by inflating the half-width toward inertness, which is the §4.2
#             failure mode arriving here (see WINDOW_SENSITIVITY below).
#
# ── THE CADENCE: 10 min, derived from how stale a centre may become ───────────────────────────
#
#   Between re-derivations the centre goes stale by drift x cadence. Holding that under 10% of the
#   half-width (0.5 bps of ~5 bps) gives cadence <= 0.5 / 0.5 = 1 h. 10 min is six times inside
#   that bound and re-derives twelve times per window, so the centre is never more than 1/12 of a
#   window behind.
#
# THIS IS A DERIVATION, NOT A TUNING. The numbers come from the sample floor, the measured drift
# rate and a staleness fraction — each stated above with its mechanism. The simulation below is
# reported as CORROBORATION and as the sensitivity the choice must survive, never as the search
# that produced it. Tuning a threshold until the refusal rate looks good is what §2.4 forbids for
# §4.2, and it is forbidden here for the same reason.
#
# WINDOW_SENSITIVITY — replayed over the real corpus, rolling vs frozen, refusal % (censored, so
# optimistic in absolute terms; the COMPARISON is the point):
#
#     leg              30m/5m   60m/5m  120m/5m  120m/10m | FROZEN 120m/10m
#     20260812025444    n/a      0.121    0.121    0.162  |   0.243   <- barely drifted: no gap
#     20260813015021    0.320    0.242    0.213    0.223  |   4.928
#     20260813105120    1.193    0.674    0.656    0.370  |  37.878
#     20260814025236    0.897    0.731    0.195    0.169  |  26.471
#
# The leg that barely drifted (1.622 bps) shows almost no rolling-vs-frozen gap; the legs that
# drifted 3+ bps show two orders of magnitude. THE FREEZE ONLY HURTS WHEN THE BASIS MOVES, which
# is the claimed mechanism and is what the mutation asserts.
#
# FALSIFIER (0.12): the window/cadence are wrong if a fresh window shows the rolling band refusing
# frames while kraken_dt is inside tolerance and the counterpart is publishing — the WO-067
# pre-registered condition. A drift rate materially above 0.5 bps/h would also falsify the ceiling
# derivation, since the 2 h window is computed directly from it.

BAND_WINDOW_S = 7200.0            # 120 min — between the 30 min sample floor and the 2 h ceiling
BAND_CADENCE_S = 600.0            # 10 min — six times inside the 1 h staleness bound
BAND_MEASURED_DRIFT_BPS_PER_H = 0.5   # measured <=0.396, rounded UP (0.15)


@dataclass
class RollingCrossVenueBand:
    """A band that re-derives against a trailing window instead of being fitted once and frozen.

    Holds no opinion about which frames were emitted: `observe()` is called on every arrival, and
    `check()` reports a verdict without feeding it back.
    """

    window_s: float = BAND_WINDOW_S
    cadence_s: float = BAND_CADENCE_S
    k: float = BAND_K
    min_samples: int = BAND_MIN_SAMPLES
    alignment_tolerance_s: float = ALIGNMENT_TOLERANCE_S

    def __post_init__(self):
        self._samples = deque()        # (ts, log_basis) — ARRIVALS, never emissions
        self._band = None
        self._last_derive_ts = None
        self._derivations = 0

    # ── arrivals ──────────────────────────────────────────────────────────────────────────────
    def observe(self, ts: float, kraken_mid: float, hl_mid: float) -> None:
        """Record one basis ARRIVAL and re-derive if the cadence has elapsed.

        Called for every frame that arrives, including frames `check` goes on to refuse. That is
        the whole point: a band fed only its own survivors ratchets tighter every cycle.
        """
        if kraken_mid > 0 and hl_mid > 0:
            self._samples.append((ts, math.log(hl_mid / kraken_mid)))
        while self._samples and ts - self._samples[0][0] > self.window_s:
            self._samples.popleft()
        if self._last_derive_ts is None or ts - self._last_derive_ts >= self.cadence_s:
            candidate = CrossVenueBand.derive([b for _, b in self._samples], k=self.k)
            self._last_derive_ts = ts
            if candidate is not None:
                self._band = candidate
                self._derivations += 1

    # ── state, for the three-way guards_active and for the segment record ─────────────────────
    @property
    def derived(self) -> bool:
        return self._band is not None

    @property
    def band(self):
        return self._band

    @property
    def derivations(self) -> int:
        return self._derivations

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    def check(self, kraken_mid: float, hl_mid: float, dt_seconds: float) -> Verdict:
        """Verdict against the CURRENT band. Warm-up returns a non-refusing UNDERIVED verdict.

        Warm-up does NOT refuse and does NOT silently pass: it reports CROSS_VENUE_BAND_UNDERIVED
        with refuse=False, and the caller marks the frame UNGUARDED in the segment record. That is
        the derive()->None precedent — measured-but-not-acted-on beats a guessed bound — and the
        count:0 / count:null doctrine: an unguarded frame is not a guarded one.
        """
        if self._band is None:
            return Verdict(False, "CROSS_VENUE_BAND_UNDERIVED",
                           {"samples": len(self._samples), "min_samples": self.min_samples})
        return self._band.check(kraken_mid, hl_mid, dt_seconds)



# ═══ 2.2 (WO-067) THE COUNTERPART-FEED DEPENDENCY — THE REPAIR OF DEFECT #3 ═══════════════════
#
# WHAT WAS WRONG. The cross-venue guard silently assumed a live Kraken feed. Nothing expressed the
# dependency, so nothing could report it, and it was invisible until it bit: when the Kraken leg
# ended at its declared deadline, kraken_dt grew past tolerance and EVERY Hyperliquid frame was
# refused. The capture reads a DIRECTORY, and a directory that stops growing is indistinguishable
# from a venue that went quiet.
#
# 0.16 AT DECLARATION, FOR THE LIVENESS BOUND ITSELF. Two quantities, and they are not the same:
#   LEFT  : the age of the newest Kraken observation available to us, measured on OUR wall clock
#           against OUR capture's own file writes. It measures the COUNTERPART PROCESS, not Kraken.
#   RIGHT : COUNTERPART_LIVENESS_S, a bound on how stale that observation may be before the basis
#           it anchors stops being a basis.
#   They are NOT simultaneous with the Hyperliquid frame being judged: the Hyperliquid snapshot
#   carries the venue's own time, the Kraken reading carries ours, and WO-061 measured our wall
#   clock running 0.848 s behind Kraken's venue time. That known offset is why the bound is set
#   well above the ~106 ms Kraken cadence rather than near it.
#
# THE BOUND. Kraken's measured cadence is ~106 ms (WO-040 baseline). A counterpart reading older
# than a few seconds is not a live quote, it is a memory. Set at 30 s: ~283x the cadence, so
# ordinary jitter, a keepalive reconnect and a bounded VENUE_DISCONNECT gap (the two measured on
# phaseb_20260809 were 3.88 s and 1.90 s) all pass, while a process that has actually stopped is
# caught within half a minute. Round up (0.15) — 30 s is the rounded figure, not a fitted one.
#
# ⚠ THE BOUND IS DELIBERATELY LOOSER THAN ALIGNMENT_TOLERANCE_S (2.0 s), AND THEY ARE DIFFERENT
# QUESTIONS. The alignment tolerance asks "are these two observations close enough in time to be
# compared at all?" and gates ONE comparison. The liveness bound asks "is the counterpart process
# still alive?" and gates THE GUARD ITSELF. Conflating them is what produced the WO-066 blackout:
# a dead counterpart failed the per-frame alignment test over and over, and the system read a
# dependency failure as 4,549 separate price anomalies.
#
# ── THE THREE STATES, DISTINGUISHED (the count:0 / count:null doctrine) ───────────────────────
#
#   GUARDED    — counterpart live AND the band derived. The frame is judged; a refusal means the
#                price was genuinely outside a live, current band.
#   UNGUARDED  — counterpart stale/absent, or the band still in warm-up. The frame is EMITTED and
#                MARKED, never silently passed and never refused wholesale. A reader must be able
#                to tell an unguarded frame from a guarded one, because a corpus of unguarded
#                frames supports different claims.
#   REFUSE-TO-START — the counterpart was NEVER available. Not a degraded mode: if there was never
#                a counterpart, there is no basis to derive from and no window to warm up, so the
#                run must not begin. This is the one case that is a STOP rather than a marking.
#
# WHY UNGUARDED IS NOT "REFUSE". Refusing every frame while the counterpart is down is precisely
# the WO-066 blackout, and it deletes data for a reason that has nothing to do with the data. The
# frames are still true observations of Hyperliquid; what is missing is our ability to CHECK them.
# Marking says exactly that, and a later reader can filter on it. Refusing says the venue misbehaved,
# which is false.

COUNTERPART_LIVENESS_S = 30.0     # ~283x Kraken's ~106 ms cadence; see the derivation above

GUARD_STATE_GUARDED = "GUARDED"
GUARD_STATE_UNGUARDED_COUNTERPART_STALE = "UNGUARDED_COUNTERPART_STALE"
GUARD_STATE_UNGUARDED_BAND_UNDERIVED = "UNGUARDED_BAND_UNDERIVED"
GUARD_STATES = (GUARD_STATE_GUARDED,
                GUARD_STATE_UNGUARDED_COUNTERPART_STALE,
                GUARD_STATE_UNGUARDED_BAND_UNDERIVED)


class CounterpartNeverAvailable(RuntimeError):
    """Raised at startup when the counterpart feed was never available at all.

    Distinct from staleness on purpose. A counterpart that goes stale mid-run degrades the guard
    to UNGUARDED and the capture continues, marking frames. A counterpart that was NEVER there
    means the cross-venue guard cannot warm up at all, so the run must not start — declaring the
    dependency is worth nothing if the process starts anyway and discovers it later.
    """


@dataclass
class CounterpartLiveness:
    """The counterpart feed's own liveness, tracked separately from any single comparison."""

    bound_s: float = COUNTERPART_LIVENESS_S

    def __post_init__(self):
        self._last_seen_ts = None
        self._ever_seen = False
        self._stale_transitions = 0
        self._was_stale = False

    def observe(self, ts: float) -> None:
        """Record that a counterpart observation of wall-time `ts` is available."""
        self._last_seen_ts = ts
        self._ever_seen = True

    def require_available_at_start(self) -> None:
        """Third state: never available at all -> refuse to start (0.9 — refuse, do not warn)."""
        if not self._ever_seen:
            raise CounterpartNeverAvailable(
                "COUNTERPART_NEVER_AVAILABLE: the cross-venue guard declares a hard dependency on "
                "a live counterpart feed and none was found. This is not a degraded mode: with no "
                "counterpart there is no basis to derive a band from and no window to warm up, so "
                "the guard could never become active and every frame would be UNGUARDED for the "
                "whole run. Start the counterpart capture first."
            )

    def age_s(self, now_ts: float):
        """Age of the newest counterpart observation, or None if there has never been one."""
        if self._last_seen_ts is None:
            return None
        return now_ts - self._last_seen_ts

    def live(self, now_ts: float) -> bool:
        age = self.age_s(now_ts)
        stale = age is None or age > self.bound_s
        if stale and not self._was_stale:
            self._stale_transitions += 1
        self._was_stale = stale
        return not stale

    @property
    def stale_transitions(self) -> int:
        """How many times the counterpart went from live to stale. A count, not a log line."""
        return self._stale_transitions

    @property
    def ever_seen(self) -> bool:
        return self._ever_seen


def guard_state(counterpart_live: bool, band_derived: bool) -> str:
    """The three-way state a reader needs, computed in one place rather than inferred downstream.

    Order matters: a stale counterpart is reported even when the band also happens to be underived,
    because the counterpart is the CAUSE and the underived band is then its consequence — a band
    cannot warm up on a feed that is not arriving.
    """
    if not counterpart_live:
        return GUARD_STATE_UNGUARDED_COUNTERPART_STALE
    if not band_derived:
        return GUARD_STATE_UNGUARDED_BAND_UNDERIVED
    return GUARD_STATE_GUARDED


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
