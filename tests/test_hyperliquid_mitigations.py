"""
WO-066 §4 — BITE PROOFS for the four mitigations that replace a checksum that does not exist.

EVERY PROOF DRIVES THE PRODUCTION CALL SITE (0.14). The mitigations live in
`trading.data.hyperliquid_mitigations`, but their only production consumer is
`tools.hyperliquid_capture.HyperliquidCapture._emit`, and that is what these tests call. A proof
that exercised the check functions directly would establish that a pure function returns a verdict
— it would say nothing about whether the capture ACTS on it, which is the entire question §0.14
and the WO-055 defect are about.

EVERY PROOF ASSERTS THE ECONOMIC EFFECT (0.9). The assertion is **the frame is not on disk**, not
that a counter moved or a line was logged. A mitigation that records a divergence and writes the
frame anyway is a log line, not a guard, and this file is written so that such a mitigation fails.

EVERY PROOF HAS A DISCRIMINATING MUTATION (§6). For each, the comparison is neutered and the BITE
is shown to fail while the DUAL still passes — which is what makes the bite an assertion about the
guard rather than about the fixture.
"""

from __future__ import annotations

import json
import math
import time
from decimal import Decimal

import pytest

from trading.data import hyperliquid_mitigations as mit
from trading.data.adapters.hyperliquid_v1 import BookLevel, BookSnapshot, TradePrint
from trading.data.corpus import CorpusLedger
from tools.hyperliquid_capture import HyperliquidCapture


# ── fixtures: the smallest thing that reaches the production emit path ────────────────────────

def make_capture(tmp_path, **kw) -> HyperliquidCapture:
    ledger = CorpusLedger(tmp_path, "hlspike_bite", host="test")
    return HyperliquidCapture(ledger, "run_bite", duration_s=60.0, kraken_dir=None, **kw)


def book(bid: float = 63_736.0, ask: float = 63_737.0, bid_sz: float = 1.0,
         ask_sz: float = 1.0, levels: int = 20, feed: str = "slow") -> BookSnapshot:
    bids = [BookLevel(Decimal(str(bid - i)), Decimal(str(bid_sz)), 1) for i in range(levels)]
    asks = [BookLevel(Decimal(str(ask + i)), Decimal(str(ask_sz)), 1) for i in range(levels)]
    return BookSnapshot(coin="BTC", bids=bids, asks=asks, venue_time_ms=1_786_503_285_533,
                        levels_published=levels, feed=feed)


def a_tape_bound(tolerance_abs: float = 1.0) -> mit.TapeBookBound:
    """A derived tape bound of declared width, so a proof does not need a calibration window."""
    return mit.TapeBookBound(tolerance_abs=tolerance_abs, observed_p995=tolerance_abs / 1.5,
                             n=1000, outside_fraction=0.02)


def frames_on_disk(cap: HyperliquidCapture) -> list:
    """What a reader would actually find. The only assertion that means anything here."""
    out = []
    for seg in sorted(cap.run_dir.glob("corpus_HL_*.jsonl")):
        for line in seg.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def a_band(centre_bps: float = 5.0, half_bps: float = 4.0):
    """A ROLLING band warmed to a declared centre and width (WO-067 §2.1 migration).

    WHY THESE PROOFS CHANGED SHAPE AND WHY THEY DID NOT WEAKEN. WO-066's §4.1 guard was a
    `CrossVenueBand` fitted once. WO-067 replaced it with `RollingCrossVenueBand`, and the frame
    path now feeds the band on every ARRIVAL before asking for a verdict — so a fitted-once object
    no longer satisfies the production interface at all. The proofs below are unchanged in what
    they assert: the same basis values, the same economic effect (frame absent from disk), the same
    counters.

    WARMED, NOT PINNED. The band is derived from real samples through the real `derive()` path
    rather than by writing into a private attribute, so the helper cannot drift away from how
    production actually builds a band. Uniform samples over +/-h with h = half/1.5 reproduce the
    requested half-width, because `derive` computes `1.5 * (p99.5 - p0.5) / 2`.

    ANCHORED TO `time.monotonic()` deliberately: `_emit` timestamps arrivals with the monotonic
    clock, and a window warmed at t=0 would be pruned entirely by the first real emit — leaving a
    band that happened to survive for the wrong reason.
    """
    h_bps = half_bps / mit.BAND_K
    rb = mit.RollingCrossVenueBand()
    # The samples must SPAN a cadence boundary, or the band never re-derives: the first
    #  derives with one sample (None) and nothing re-triggers inside 600 s. Stepping
    # 2 s over 600 samples spans 1200 s and crosses the boundary twice.
    n = mit.BAND_MIN_SAMPLES * 2
    step = 2.0
    t0 = time.monotonic() - n * step
    for i in range(n):
        frac = (i / (n - 1)) * 2.0 - 1.0                 # -1 .. +1, uniform
        bps = centre_bps + frac * h_bps
        rb.observe(t0 + i * step, 1e5, 1e5 * (1 + bps / 1e4))
    assert rb.derived, "the warmed band must have derived through the real path"
    return rb


def hl_mid_at_basis(kraken_mid: float, basis_bps: float) -> tuple:
    """A Hyperliquid book sitting at a chosen basis to a given Kraken mid."""
    mid = kraken_mid * (1 + basis_bps / 1e4)
    return book(bid=mid - 0.5, ask=mid + 0.5)


# ═══ 4.1 CROSS-VENUE PRICE GUARD ═════════════════════════════════════════════════════════════

class TestCrossVenueBand:
    """The checksum's replacement. The mitigation D56's conditional actually rests on."""

    KRAKEN_MID = 63_710.65

    def test_bite_mid_outside_band_suppresses_the_frame(self, tmp_path):
        """BITE — a synthetic Hyperliquid mid outside the band: NO FRAME IS WRITTEN."""
        cap = make_capture(tmp_path)
        cap.band = a_band(centre_bps=5.0, half_bps=4.0)     # accepts 1..9 bps
        cap._emit(hl_mid_at_basis(self.KRAKEN_MID, 60.0), [], self.KRAKEN_MID, 0.3)

        assert frames_on_disk(cap) == [], (
            "a mid 60 bps from a band centred at 5 +/- 4 bps was EMITTED — the guard logged a "
            "divergence and let the system act on suspect data anyway (0.9)")
        assert cap.counters["refused_cross_venue_band"] == 1
        assert cap.counters["book_consistency_failures_total"] == 1
        assert cap.counters["frames_emitted"] == 0

    def test_dual_ordinary_basis_excursion_is_not_refused(self, tmp_path):
        """DUAL — a normal basis excursion INSIDE the band is emitted.

        This is the half that matters most. Spot and perp are different instruments and a perp
        trades at a real, varying basis; a band that refused ordinary basis would be worse than no
        guard at all, and would refuse the venue on the strength of its own miscalibration.
        """
        cap = make_capture(tmp_path)
        cap.band = a_band(centre_bps=5.0, half_bps=4.0)
        for basis in (1.6, 3.0, 4.9, 5.0, 7.4, 8.1):        # the measured p0.5..p99.5 range
            cap._last_book_mono = {f: None for f in cap.feeds}
            cap._emit(hl_mid_at_basis(self.KRAKEN_MID, basis), [], self.KRAKEN_MID, 0.3)

        assert len(frames_on_disk(cap)) == 6, (
            "an ordinary spot-perp basis excursion was REFUSED — the band is narrower than the "
            "basis it was derived from")
        assert cap.counters["refused_cross_venue_band"] == 0

    def test_bite_stale_pair_suppresses_the_frame(self, tmp_path):
        """BITE — the 0.16 half: two reads too far apart are not a comparable pair at all."""
        cap = make_capture(tmp_path)
        cap.band = a_band()
        cap._emit(hl_mid_at_basis(self.KRAKEN_MID, 5.0), [], self.KRAKEN_MID, 9.0)

        assert frames_on_disk(cap) == [], (
            "a Kraken read 9 s away from the Hyperliquid snapshot was compared and emitted; two "
            "non-simultaneous quantities were bounded as if they were simultaneous (F6)")
        assert cap.counters["refused_cross_venue_band"] == 1

    def test_mutation_removing_the_comparison_breaks_the_bite_not_the_dual(self, tmp_path,
                                                                          monkeypatch):
        """MUTATION — neuter the band comparison: the BITE fails, the DUAL still passes."""
        # The rolling band delegates its verdict to the derived `CrossVenueBand`, so neutering
        # that comparison is still the smallest edit that removes the check and nothing else —
        # which is what makes this mutation discriminating rather than a rewrite.
        monkeypatch.setattr(mit.CrossVenueBand, "check",
                            lambda self, k, h, dt: mit.Verdict(False))

        bite = make_capture(tmp_path / "bite")
        bite.band = a_band(centre_bps=5.0, half_bps=4.0)
        bite._emit(hl_mid_at_basis(self.KRAKEN_MID, 60.0), [], self.KRAKEN_MID, 0.3)
        assert len(frames_on_disk(bite)) == 1, "mutation did not reach the guard"
        assert bite.counters["refused_cross_venue_band"] == 0

        dual = make_capture(tmp_path / "dual")
        dual.band = a_band(centre_bps=5.0, half_bps=4.0)
        dual._emit(hl_mid_at_basis(self.KRAKEN_MID, 5.0), [], self.KRAKEN_MID, 0.3)
        assert len(frames_on_disk(dual)) == 1, "the dual must be indifferent to the mutation"

    def test_underived_band_leaves_the_guard_inactive_and_says_so(self):
        """A bound that was never measured cannot refuse anything honestly.

        `derive` returns None below the sample floor rather than defaulting to a width nobody
        measured — an invented band would refuse or admit frames on the strength of a guess.
        """
        assert mit.CrossVenueBand.derive([0.0005] * (mit.BAND_MIN_SAMPLES - 1)) is None
        assert mit.CrossVenueBand.derive([0.0005] * mit.BAND_MIN_SAMPLES) is not None

    def test_band_is_centred_on_measured_basis_not_on_zero(self):
        """0.16 at the declaration: the band tests DEVIATION FROM NORMAL BASIS, not basis itself.

        Derived from samples all sitting near +5 bps, a band centred on zero would refuse every
        one of them — the F6 error the WO names, caught here rather than in production.
        """
        samples = [math.log(1 + (5.0 + (i % 7) * 0.1) / 1e4) for i in range(1000)]
        band = mit.CrossVenueBand.derive(samples)
        assert band is not None
        assert band.median_basis_bps == pytest.approx(5.3, abs=0.4), (
            "the band's centre is not the measured basis level")
        v = band.check(63_710.65, 63_710.65 * (1 + 5.0 / 1e4), 0.3)
        assert not v.refuse, "a band derived from +5 bps samples refuses +5 bps"


# ═══ 4.2 TAPE-VS-BOOK RECONCILIATION ═════════════════════════════════════════════════════════

class TestTapeVsBook:

    def test_bite_print_outside_the_held_book_suppresses_the_frame(self, tmp_path):
        """BITE — a print far through the held quotes: the book we hold is not the book that traded."""
        cap = make_capture(tmp_path)
        cap.tape = a_tape_bound(1.0)
        b = book(bid=63_736.0, ask=63_737.0)
        cap._emit(b, [TradePrint("BTC", "B", Decimal("63900.0"), Decimal("0.01"), 1)], None, None)

        assert frames_on_disk(cap) == [], (
            "a print 163 USD through the held ask was emitted with the book it contradicts")
        assert cap.counters["refused_tape_vs_book"] == 1
        assert cap.counters["book_consistency_failures_total"] == 1

    def test_dual_print_at_the_touch_is_not_refused(self, tmp_path):
        """DUAL — prints occur AT the touch and one tick through it. Those are ordinary."""
        cap = make_capture(tmp_path)
        cap.tape = a_tape_bound(1.0)
        b = book(bid=63_736.0, ask=63_737.0)
        for px in ("63736.0", "63737.0", "63736.5", "63735.5", "63738.0"):
            cap._last_book_mono = {f: None for f in cap.feeds}
            cap._emit(b, [TradePrint("BTC", "B", Decimal(px), Decimal("0.01"), 1)], None, None)

        assert len(frames_on_disk(cap)) == 5, "an ordinary print at the touch was refused"
        assert cap.counters["refused_tape_vs_book"] == 0

    def test_an_underived_bound_refuses_nothing_and_the_frames_survive(self, tmp_path):
        """The 33.3% defect, asserted so it cannot come back.

        Before the tolerance is derived the guard MUST NOT run. A one-tick constant refused a
        third of ordinary slow-feed frames, and because the refusals tracked price movement the
        surviving corpus was systematically calmer than the venue — a selection effect correlated
        with volatility, which is the one bias a market-data corpus must not carry.
        """
        cap = make_capture(tmp_path)
        assert cap.tape is None, "the tape bound must start underived"
        cap._emit(book(), [TradePrint("BTC", "B", Decimal("63900.0"), Decimal("0.01"), 1)],
                  None, None)

        assert len(frames_on_disk(cap)) == 1, (
            "a guard whose bound was never measured suppressed a frame")
        assert cap.counters["refused_tape_vs_book"] == 0
        assert cap._tape_distances, "the distance must still be MEASURED — that is the calibration"

    def test_the_bound_is_derived_from_measurement_not_declared(self):
        """§4.2 now follows §4.1's discipline: measured, floored, and None below the sample floor."""
        assert mit.TapeBookBound.derive([0.0] * (mit.TAPE_BOOK_MIN_SAMPLES - 1), 1.0) is None

        # A feed whose ordinary reconciliation error reaches ~14 ticks (the measured slow feed)
        # must produce a WIDE bound. Narrower would refuse ordinary data; that it is wide is the
        # feed's cadence showing through, and §4.5 carries it as a residual.
        distances = [0.0] * 640 + [float(i % 14 + 1) for i in range(360)]
        bound = mit.TapeBookBound.derive(distances, 1.0)
        assert bound is not None
        assert bound.tolerance_abs >= mit.TAPE_BOOK_TICK_TOLERANCE
        assert bound.outside_fraction == pytest.approx(0.36, abs=0.01)

    def test_mutation_removing_the_comparison_breaks_the_bite_not_the_dual(self, tmp_path,
                                                                          monkeypatch):
        """MUTATION — neuter the reconciliation: the BITE fails, the DUAL still passes."""
        monkeypatch.setattr(mit, "check_tape_vs_book",
                            lambda px, bid, ask, tick, tolerance_abs=None: mit.Verdict(False))

        bite = make_capture(tmp_path / "bite")
        bite.tape = a_tape_bound(1.0)
        bite._emit(book(), [TradePrint("BTC", "B", Decimal("63900.0"), Decimal("0.01"), 1)],
                   None, None)
        assert len(frames_on_disk(bite)) == 1, "mutation did not reach the guard"

        dual = make_capture(tmp_path / "dual")
        dual.tape = a_tape_bound(1.0)
        dual._emit(book(), [TradePrint("BTC", "B", Decimal("63736.5"), Decimal("0.01"), 1)],
                   None, None)
        assert len(frames_on_disk(dual)) == 1

    def test_what_it_cannot_detect_is_a_property_of_the_check_not_a_caveat(self):
        """The WO-063 line, asserted rather than only written in a docstring.

        A UNIFORMLY STALE PAIR passes: if book and tape lag together, every print sits inside the
        held quotes and the check is satisfied while both are wrong. This test exists so that the
        limit is a fact about the code and cannot silently stop being true.
        """
        stale_but_self_consistent = mit.check_tape_vs_book(
            print_px=50_000.0, best_bid=49_999.5, best_ask=50_000.5, tick=1.0)
        assert not stale_but_self_consistent.refuse, (
            "the check claims to catch a uniformly stale pair; it cannot, and §4.5's residual "
            "depends on that being stated honestly")


# ═══ 4.3 STALENESS AND LIVENESS ══════════════════════════════════════════════════════════════

class TestStaleness:

    def test_bite_stale_snapshot_suppresses_the_frame(self, tmp_path):
        cap = make_capture(tmp_path)
        cap.stale["slow"] = mit.StalenessBound(max_age_s=30.0, observed_p99_s=5.0, n=1000)
        cap._last_book_mono["slow"] = time.monotonic() - 300.0
        cap._emit(book(feed="slow"), [], None, None)

        assert frames_on_disk(cap) == [], "a 300 s old snapshot was emitted against a 30 s bound"
        assert cap.counters["refused_staleness"] == 1

    def test_dual_ordinary_cadence_is_not_refused(self, tmp_path):
        """DUAL — the measured cadence is ~5.4 s on the slow feed. That must pass."""
        cap = make_capture(tmp_path)
        cap.stale["slow"] = mit.StalenessBound(max_age_s=30.0, observed_p99_s=5.0, n=1000)
        cap._last_book_mono["slow"] = time.monotonic() - 5.4
        cap._emit(book(feed="slow"), [], None, None)

        assert len(frames_on_disk(cap)) == 1, (
            "the venue's own ordinary cadence was refused as stale")
        assert cap.counters["refused_staleness"] == 0

    def test_the_bound_is_per_feed_because_the_cadences_are_10x_apart(self, tmp_path):
        """A single bound across both feeds would be derived from a bimodal cadence.

        5.41 s and 0.52 s are an order of magnitude apart. One bound fitted to both would be too
        loose to catch a stalled fast feed and too tight for an ordinary slow one — describing
        neither, which is how a bound stops being a measurement of anything.
        """
        cap = make_capture(tmp_path)
        cap.stale["fast"] = mit.StalenessBound(max_age_s=3.0, observed_p99_s=0.5, n=1000)
        cap.stale["slow"] = mit.StalenessBound(max_age_s=30.0, observed_p99_s=5.0, n=1000)

        cap._last_book_mono["slow"] = time.monotonic() - 5.4
        cap._emit(book(feed="slow"), [], None, None)
        cap._last_book_mono["fast"] = time.monotonic() - 5.4
        cap._emit(book(feed="fast", levels=5), [], None, None)

        assert len(frames_on_disk(cap)) == 1, (
            "5.4 s is ordinary on the slow feed and a stall on the fast one; both were judged "
            "the same way")
        assert cap.per_feed["fast"]["refused_staleness"] == 1
        assert cap.per_feed["slow"]["refused_staleness"] == 0

    def test_dual_a_guard_that_has_refused_must_be_able_to_accept_again(self, tmp_path):
        """RECOVERY DUAL — the test whose absence cost the fast feed 5 h 39 m of a 24 h run.

        On 2026-08-13 the fast feed went dark at 03:23:50Z and wrote nothing for the rest of the
        run. `_emit` returned on refusal BEFORE updating the clock staleness measured against, so
        the first refusal froze the reference instant, every later frame was measured against it,
        and the age could only grow. The guard could never accept another frame.

        Every other §4.3 test emits ONE frame and asserts refuse-or-emit. **A latching guard passes
        all of them.** This is the assertion that does not.
        """
        cap = make_capture(tmp_path)
        cap.stale["fast"] = mit.StalenessBound(max_age_s=5.32, observed_p99_s=0.887, n=1000)

        cap._last_book_mono["fast"] = time.monotonic() - 300.0
        cap._emit(book(levels=5, feed="fast"), [], None, None)
        assert frames_on_disk(cap) == [], "the stale frame should have been refused"

        # The feed resumes at its ordinary cadence. This frame MUST be written.
        cap._emit(book(levels=5, feed="fast"), [], None, None)

        assert len(frames_on_disk(cap)) == 1, (
            "the guard refused a frame arriving at the venue's ordinary cadence, because refusing "
            "the previous one froze its reference clock — it can never accept another frame, and "
            "a latched guard is indistinguishable from a dead feed")

    def test_the_recovery_fix_does_not_disarm_the_guard(self, tmp_path):
        """COUNTER-DUAL — advancing the arrival clock must not stop staleness firing.

        The wrong fix is to advance the clock only on emission (latches) or to treat every arrival
        as fresh regardless of the silence before it (never fires). A persistently silent feed must
        keep producing refusals, one per arrival, because each arrival is measured against the
        previous ARRIVAL and the silence between them is real.
        """
        cap = make_capture(tmp_path)
        cap.stale["fast"] = mit.StalenessBound(max_age_s=5.32, observed_p99_s=0.887, n=1000)

        for _ in range(3):
            cap._last_book_mono["fast"] = time.monotonic() - 60.0
            cap._emit(book(levels=5, feed="fast"), [], None, None)

        assert frames_on_disk(cap) == [], "a persistently silent feed stopped being refused"
        assert cap.per_feed["fast"]["refused_staleness"] == 3

    def test_a_refusal_on_one_feed_does_not_latch_the_other(self, tmp_path):
        """The dual-feed corollary: the slow feed survived 5 h only because its bound is wider.

        Both feeds latched in the end. This pins that a refusal is scoped to the feed it happened
        on, so one feed stalling can never take the other with it.
        """
        cap = make_capture(tmp_path)
        cap.stale["fast"] = mit.StalenessBound(max_age_s=5.32, observed_p99_s=0.887, n=1000)
        cap.stale["slow"] = mit.StalenessBound(max_age_s=34.59, observed_p99_s=5.77, n=1000)

        cap._last_book_mono["fast"] = time.monotonic() - 300.0
        cap._emit(book(levels=5, feed="fast"), [], None, None)
        cap._last_book_mono["slow"] = time.monotonic() - 5.4
        cap._emit(book(levels=20, feed="slow"), [], None, None)

        frames = frames_on_disk(cap)
        assert len(frames) == 1 and frames[0]["feed"] == "slow", (
            "a stale fast feed suppressed a healthy slow frame")

    def test_mutation_restoring_the_latch_breaks_the_recovery_dual(self, tmp_path, monkeypatch):
        """MUTATION — put the clock update back behind the refusal return: recovery fails.

        Expressed as the real defect rather than an invented one: this IS the code that ran.
        """
        cap = make_capture(tmp_path)
        cap.stale["fast"] = mit.StalenessBound(max_age_s=5.32, observed_p99_s=0.887, n=1000)

        real_check = mit.StalenessBound.check
        frozen = {"at": time.monotonic() - 300.0}

        def latching_check(self, age_s):
            # Emulate measuring against a clock that never advances past the first refusal.
            return real_check(self, time.monotonic() - frozen["at"])

        monkeypatch.setattr(mit.StalenessBound, "check", latching_check)

        # A prior arrival must exist or the check is skipped entirely and the first frame emits
        # for a reason that has nothing to do with the mutation.
        cap._last_book_mono["fast"] = time.monotonic() - 300.0
        cap._emit(book(levels=5, feed="fast"), [], None, None)
        cap._emit(book(levels=5, feed="fast"), [], None, None)

        assert frames_on_disk(cap) == [], (
            "the mutation did not reproduce the latch; the recovery dual is not discriminating")

    def test_mutation_removing_the_bound_breaks_the_bite_not_the_dual(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mit.StalenessBound, "check", lambda self, age: mit.Verdict(False))

        bite = make_capture(tmp_path / "bite")
        bite.stale["slow"] = mit.StalenessBound(max_age_s=30.0, observed_p99_s=5.0, n=1000)
        bite._last_book_mono["slow"] = time.monotonic() - 300.0
        bite._emit(book(feed="slow"), [], None, None)
        assert len(frames_on_disk(bite)) == 1, "mutation did not reach the guard"

        dual = make_capture(tmp_path / "dual")
        dual.stale["slow"] = mit.StalenessBound(max_age_s=30.0, observed_p99_s=5.0, n=1000)
        dual._last_book_mono["slow"] = time.monotonic() - 5.4
        dual._emit(book(feed="slow"), [], None, None)
        assert len(frames_on_disk(dual)) == 1

    def test_bound_is_derived_from_observation_never_from_the_documented_floor(self):
        """The doc says ">= 0.5 s", which is a FLOOR and cannot bound staleness.

        Derived from a cadence whose p99 is ~21 s — what the killed run actually measured on the
        slow feed — the bound must sit well above the documented figure, or it would refuse the
        venue's ordinary behaviour every few minutes.
        """
        gaps = [5.4] * 990 + [21.5] * 10
        bound = mit.StalenessBound.derive(gaps)
        assert bound is not None
        assert bound.max_age_s > 0.5 * 6, "a bound ported from the documented floor"
        assert bound.max_age_s >= mit.STALENESS_FLOOR_S
        assert mit.StalenessBound.derive([5.4] * (mit.STALENESS_MIN_SAMPLES - 1)) is None


# ═══ 4.4 THE EVIDENTIARY BOUND ═══════════════════════════════════════════════════════════════

class TestEvidentiaryBound:
    """4.4 is a DECLARATION, not a mitigation — so its proof is shaped differently on purpose.

    A feed silently returning 5 levels where 20 were requested is still true data about the touch;
    refusing it would discard good observations. What must not happen is that it becomes
    INDISTINGUISHABLE from a 20-level frame. So the assertion is that the frame IS written and the
    detection counter DOES move.
    """

    def test_a_short_book_is_flagged_and_still_written(self, tmp_path):
        cap = make_capture(tmp_path)
        cap._emit(book(levels=5, feed="slow"), [], None, None)

        frames = frames_on_disk(cap)
        assert len(frames) == 1, "a 5-level frame is real data about the touch and was discarded"
        assert frames[0]["levels_published"] == 5
        assert cap.counters["observed_levels_below_declared"] == 1

    def test_a_full_book_does_not_move_the_counter(self, tmp_path):
        cap = make_capture(tmp_path)
        cap._emit(book(levels=20, feed="slow"), [], None, None)
        assert cap.counters["observed_levels_below_declared"] == 0

    def test_the_declared_depth_is_per_feed_not_per_corpus(self, tmp_path):
        """The fast feed publishes 5 BY CONTRACT. Judging it against 20 would fire on every frame.

        A counter that moves on every frame reports nothing — it would stop meaning "the venue
        gave us less than it promised", which is the only thing §4.4 exists to detect.
        """
        cap = make_capture(tmp_path)
        cap._emit(book(levels=5, feed="fast"), [], None, None)

        assert len(frames_on_disk(cap)) == 1
        assert cap.counters["observed_levels_below_declared"] == 0, (
            "a 5-level fast-feed frame was flagged as short; the bound was read from the corpus "
            "rather than from the subscription that produced the frame")

    def test_mutation_removing_the_check_loses_the_detection(self, tmp_path, monkeypatch):
        """MUTATION — a feed silently returning 5 becomes indistinguishable from one returning 20."""
        monkeypatch.setattr(mit, "check_declared_levels",
                            lambda n, declared=20: mit.Verdict(False))
        cap = make_capture(tmp_path)
        cap._emit(book(levels=5, feed="slow"), [], None, None)
        assert cap.counters["observed_levels_below_declared"] == 0, "mutation did not reach it"
        assert len(frames_on_disk(cap)) == 1

    def test_every_frame_carries_the_levels_and_the_levels_themselves(self, tmp_path):
        """§3.4 + the 2026-08-12 repair: the bound is only true if the depth is actually there.

        The first attempt wrote `levels_published: 20` while persisting the touch alone, so the
        manifest promised twenty levels the corpus did not contain.
        """
        cap = make_capture(tmp_path)
        cap._emit(book(levels=20, feed="slow"), [], None, None)
        frame = frames_on_disk(cap)[0]
        assert frame["levels_published"] == 20
        assert len(frame["bids"]) == 20 and len(frame["asks"]) == 20, (
            "the evidentiary bound claims 20 levels; the corpus holds fewer")

    def test_every_frame_says_which_feed_produced_it(self, tmp_path):
        """§3.4 captures two feeds on one socket. Untagged, the corpus would interleave them.

        A 5-level 0.52 s stream and a 20-level 5.4 s stream are different observations of the
        venue; a figure computed across both without separating them averages two things.
        """
        cap = make_capture(tmp_path)
        cap._emit(book(levels=20, feed="slow"), [], None, None)
        cap._emit(book(levels=5, feed="fast"), [], None, None)

        assert [f["feed"] for f in frames_on_disk(cap)] == ["slow", "fast"]


# ═══ THE COUNTER'S NAME ══════════════════════════════════════════════════════════════════════

def test_no_counter_is_called_a_checksum_counter():
    """Naming a consistency counter `checksum_*` would import a guarantee that does not exist.

    Hyperliquid publishes no checksum, no sequence number and no version. CRC32 answers "is my
    book byte-identical to the venue's?"; nothing in this module can answer that. The name is the
    place that distinction is either kept or lost.
    """
    assert "book_consistency_failures_total" in mit.COUNTERS
    assert not [c for c in mit.COUNTERS if "checksum" in c]
