"""
WO-067 §2 — BITE PROOFS for the three repairs, each with a discriminating mutation.

§2.1 ROLLING RE-DERIVATION. The band was fitted once and frozen while the basis drifted
+4.94 -> +9.40 bps across four calibrations. It refused 2,723 of 2,740 frames (99.4%) in a
market-correlated way, because a high positive basis is exactly when the perp runs hot against
spot. The claim under test is narrow and falsifiable: THE FAILURE WAS THE FREEZING, NOT THE
COMPARISON. The mutation is what proves it — freeze the band and the DUAL fails while the BITE
still passes.

§2.2 THE COUNTERPART DEPENDENCY. §4.1 silently assumed a live Kraken feed. Three states must be
distinguishable, and the middle one is the whole point: a stale counterpart means we cannot CHECK
the frame, not that the frame is wrong. Refusing on a dependency failure is the WO-066 blackout.

§2.3 PER-SEGMENT COUNTERS. A run-level total cannot show that a blackout ran for six consecutive
hours; the shape lived entirely in the distribution over time. And the counters must reach the
RECORD, not just the object — WO-055's `raw_text_trim_events` reached the object and never the
record, so it could not be audited from the corpus.

0.9 THROUGHOUT: the assertions are about the economic effect — whether a frame is refused, whether
a guard is active, what a segment record contains — never about a log line.
"""

from __future__ import annotations

import math

import pytest

from trading.data import hyperliquid_mitigations as mit
from trading.data.corpus import SegmentRecord


# ── helpers ───────────────────────────────────────────────────────────────────────────────────

KRAKEN_MID = 63000.0


def hl_mid_at(basis_bps: float, kraken_mid: float = KRAKEN_MID) -> float:
    """The Hyperliquid mid that sits `basis_bps` above the given Kraken spot mid."""
    return kraken_mid * math.exp(basis_bps / 1e4)


def drifting_stream(hours: float, start_bps: float, drift_bps_per_h: float,
                    rate_per_s: float = 2.0, jitter_bps: float = 0.35, seed: int = 20260821):
    """A basis that DRIFTS linearly, with small deterministic jitter. No band involved.

    Deterministic by construction — a seeded LCG, not `random` — so the proof does not depend on
    interpreter or platform RNG behaviour. Every sample here is ORDINARY: linear drift at a
    measured rate plus sub-bps jitter. There are no outliers to find.
    """
    state = seed
    step = 1.0 / rate_per_s
    out = []
    for i in range(int(hours * 3600 * rate_per_s)):
        ts = i * step
        state = (1103515245 * state + 12345) % (1 << 31)
        jitter = ((state / (1 << 31)) - 0.5) * 2.0 * jitter_bps
        bps = start_bps + drift_bps_per_h * (ts / 3600.0) + jitter
        out.append((ts, hl_mid_at(bps), bps))
    return out


def replay(band, stream, warmup_fraction: float = 0.25):
    """Stream arrivals through the band the way `_emit` does: OBSERVE, then CHECK, at each instant.

    ⚠ THE INSTRUMENT MUST NOT BE FROZEN EITHER. Judging every historical sample against the band's
    FINAL state measures a frozen band no matter how the band is implemented — the same error the
    WO is repairing, committed in the measuring apparatus. This was caught by the dual failing at
    38.3% on data whose true refusal rate is zero.

    Returns (refusal_rate_after_warmup, n_judged).
    """
    refused = judged = 0
    cut = int(len(stream) * warmup_fraction)
    for i, (ts, mid, _bps) in enumerate(stream):
        band.observe(ts, KRAKEN_MID, mid)          # arrival first — always
        v = band.check(KRAKEN_MID, mid, 0.0)       # then the verdict, against the band AS OF NOW
        if i < cut or not band.derived:
            continue
        judged += 1
        if v.refuse:
            refused += 1
    return (refused / judged if judged else float("nan")), judged


# ═══ 2.1 ROLLING RE-DERIVATION ════════════════════════════════════════════════════════════════

def test_bite_2_1_a_mid_outside_the_rolling_band_is_refused():
    """BITE — a genuinely dislocated mid refuses. The repair must not have disarmed the guard."""
    band = mit.RollingCrossVenueBand()
    for ts, mid, _ in drifting_stream(hours=1.0, start_bps=+6.0, drift_bps_per_h=0.0):
        band.observe(ts, KRAKEN_MID, mid)
    assert band.derived, "the band must have derived from an hour of arrivals"

    far = hl_mid_at(+400.0)          # 400 bps of basis — not an ordinary excursion
    v = band.check(KRAKEN_MID, far, 0.0)
    assert v.refuse, "a mid 400 bps from the measured basis must be REFUSED"
    assert v.reason == "CROSS_VENUE_BAND_EXCEEDED"


def test_bite_2_1_b_warm_up_leaves_the_guard_inactive_rather_than_defaulting():
    """BITE — before the window has samples the band is UNDERIVED: not refusing, not passing.

    Returning a made-up width would give a guessed bound a measurement's authority. Returning
    `refuse=True` would blackout the warm-up. Neither: it reports UNDERIVED and the caller marks
    the frame unguarded.
    """
    band = mit.RollingCrossVenueBand()
    assert not band.derived
    v = band.check(KRAKEN_MID, hl_mid_at(+6.0), 0.0)
    assert not v.refuse, "warm-up must NOT refuse — that is the blackout being repaired"
    assert v.reason == "CROSS_VENUE_BAND_UNDERIVED"
    assert v.detail["samples"] < v.detail["min_samples"]


def test_dual_2_1_the_load_bearing_half_no_ordinary_frame_is_refused_across_real_drift():
    """DUAL — across 8 h of genuine drift the rolling band refuses NO ordinary frame.

    §0.4 names this the load-bearing dual: a band that refuses ordinary data is the failure being
    repaired, so "does not refuse a normal excursion" must be ASSERTED. The drift rate is the one
    measured on leg 20260814025236 — 3.167 bps over 8.00 h.
    """
    band = mit.RollingCrossVenueBand()
    stream = drifting_stream(hours=8.0, start_bps=+7.4, drift_bps_per_h=3.167 / 8.0)
    rate, judged = replay(band, stream)

    assert judged > 40_000, f"only {judged} frames judged — the replay is not exercising the band"
    assert rate == 0.0, (
        f"the rolling band refused {rate:.4%} of ORDINARY drifting data. A repair whose refusal "
        f"rate is not zero on ordinary data has not repaired anything — this is the exact failure "
        f"mode of the frozen band, reappearing in the repair.")


def test_mutation_2_1_freezing_the_band_breaks_the_dual_while_the_bite_still_passes():
    """MUTATION — freeze at first derivation. THE ASYMMETRY IS THE PROOF.

    The mutant keeps the comparison bit-for-bit and changes only WHEN the band is derived. If the
    dual fails under the mutant while the bite still passes, the defect was the freezing and not
    the comparison — which is the entire claim of §2.1.
    """
    class Frozen(mit.RollingCrossVenueBand):
        def observe(self, ts, kraken_mid, hl_mid):
            if self.derived:
                return                      # <- the freeze: never re-derive
            super().observe(ts, kraken_mid, hl_mid)

    drift = 3.167 / 8.0
    stream = drifting_stream(hours=8.0, start_bps=+7.4, drift_bps_per_h=drift)

    # THE SAME STREAM through both, replayed identically. The only difference is when the band
    # re-derives, which is the single variable this mutation isolates.
    rolling_rate, _ = replay(mit.RollingCrossVenueBand(), stream)
    frozen = Frozen()
    frozen_rate, _ = replay(frozen, stream)

    # The BITE still passes under the mutant — the comparison itself is untouched.
    assert frozen.check(KRAKEN_MID, hl_mid_at(+400.0), 0.0).refuse, (
        "the mutant must still refuse a genuinely dislocated mid; if it did not, this mutation "
        "would be testing the comparison rather than the freezing")

    # The DUAL fails under the mutant. This is the asymmetry.
    assert frozen_rate > rolling_rate, (
        f"freezing must make the dual worse: frozen {frozen_rate:.4%} vs rolling "
        f"{rolling_rate:.4%}")
    assert rolling_rate == 0.0
    assert frozen_rate > 0.20, (
        f"the frozen band refused only {frozen_rate:.4%} of drifting data; the WO-066 run measured "
        f"26-38% on legs that drifted 3+ bps, so a mutant showing near-zero would mean this test "
        f"is not reproducing the field failure at all")


def test_2_1_derives_from_arrivals_not_from_its_own_emitted_output():
    """The ratchet. A band fed only its own survivors consumes its filtered tail every cycle.

    Not a stylistic preference: re-deriving from emissions makes the failure COMPOUND rather than
    merely persist, so it is strictly worse than freezing. Same shape as the §4.3 latch, where the
    emit path returned before advancing the clock staleness was measured against.
    """
    band = mit.RollingCrossVenueBand()
    for ts, mid, _ in drifting_stream(hours=1.0, start_bps=+6.0, drift_bps_per_h=0.0):
        band.observe(ts, KRAKEN_MID, mid)
    width_before = band.band.half_width_log
    n_before = band.sample_count

    # Arrivals the band WOULD refuse are still observed.
    for i in range(400):
        band.observe(3600 + i * 0.5, KRAKEN_MID, hl_mid_at(+400.0))

    assert band.sample_count >= n_before, "refused arrivals must still enter the window"
    assert band.band.half_width_log > width_before, (
        "the window absorbed 400 extreme arrivals and the half-width did not move — the band is "
        "being fed something other than arrivals, which is the ratchet this test exists to catch")


# ═══ 2.2 THE COUNTERPART DEPENDENCY ═══════════════════════════════════════════════════════════

def test_bite_2_2_a_counterpart_never_available_refuses_to_start():
    """BITE — the third state. Never available is a STOP, not a degraded mode (0.9)."""
    cp = mit.CounterpartLiveness()
    with pytest.raises(mit.CounterpartNeverAvailable) as exc:
        cp.require_available_at_start()
    assert "COUNTERPART_NEVER_AVAILABLE" in str(exc.value)


def test_bite_2_2_b_a_stale_counterpart_disables_the_band_instead_of_blacking_out():
    """BITE — the WO-066 blackout, and the assertion that it no longer happens.

    When Kraken leg 3 ended at its deadline, `kraken_dt` grew past tolerance and EVERY Hyperliquid
    frame was refused — one dead dependency read as 4,549 separate price anomalies. The repair is
    that a stale counterpart yields UNGUARDED, not refusal.
    """
    cp = mit.CounterpartLiveness()
    cp.observe(1000.0)
    assert cp.live(1010.0), "10 s inside a 30 s bound is live"
    assert not cp.live(1000.0 + mit.COUNTERPART_LIVENESS_S + 1), "past the bound it is stale"

    state = mit.guard_state(counterpart_live=False, band_derived=True)
    assert state == mit.GUARD_STATE_UNGUARDED_COUNTERPART_STALE
    assert state != "REFUSED", "a dependency failure must never be expressed as a refusal"


def test_2_2_the_three_states_are_distinguishable_and_cause_beats_consequence():
    """0.11 — THREE states, enumerated, and the ordering is load-bearing.

    A stale counterpart is reported even when the band is also underived, because the counterpart
    is the CAUSE and the underived band is its consequence — a band cannot warm up on a feed that
    is not arriving. Reporting the consequence would send a reader to fix the wrong thing.
    """
    assert len(mit.GUARD_STATES) == 3, mit.GUARD_STATES
    assert mit.guard_state(True, True) == mit.GUARD_STATE_GUARDED
    assert mit.guard_state(True, False) == mit.GUARD_STATE_UNGUARDED_BAND_UNDERIVED
    assert mit.guard_state(False, True) == mit.GUARD_STATE_UNGUARDED_COUNTERPART_STALE
    assert mit.guard_state(False, False) == mit.GUARD_STATE_UNGUARDED_COUNTERPART_STALE, (
        "with both failing, the CAUSE (stale counterpart) must be reported, not the consequence")
    assert len(set(mit.GUARD_STATES)) == 3, "the three states must be distinguishable"


def test_2_2_liveness_bound_is_looser_than_the_alignment_tolerance_and_they_differ():
    """They answer different questions, and conflating them produced the WO-066 blackout.

    Alignment tolerance gates ONE comparison ("are these reads close enough to compare?").
    The liveness bound gates THE GUARD ("is the counterpart process still alive?").
    """
    assert mit.COUNTERPART_LIVENESS_S > mit.ALIGNMENT_TOLERANCE_S
    # 30 s against Kraken's measured ~106 ms cadence, and above the two bounded VENUE_DISCONNECT
    # gaps actually measured on phaseb_20260809 (3.88 s and 1.90 s).
    assert mit.COUNTERPART_LIVENESS_S >= 3.88 * 2


def test_mutation_2_2_collapsing_the_states_to_a_boolean_loses_the_distinction():
    """MUTATION — report guarded/not-guarded only. The reader can no longer tell WHY."""
    def mutant(counterpart_live, band_derived):
        return "GUARDED" if (counterpart_live and band_derived) else "NOT_GUARDED"

    assert mutant(False, True) == mutant(True, False), (
        "the mutant collapses a dead counterpart and a warming band into one label")
    assert (mit.guard_state(False, True) != mit.guard_state(True, False)), (
        "the real implementation must keep them apart — one is a broken dependency needing "
        "operator action, the other is a capture that simply has not warmed up yet")


# ═══ 2.3 PER-SEGMENT COUNTERS ═════════════════════════════════════════════════════════════════

def test_bite_2_3_counters_reach_the_segment_record_and_survive_a_round_trip():
    """BITE — the counters must be IN the record, and readable back out of it.

    WO-055's `raw_text_trim_events` reached the object and never the record. A count that cannot
    be recomputed from what was preserved is a claim, not evidence.
    """
    counters = {"frames_emitted": 900, "frames_refused": 12,
                "refused_cross_venue_band": 9, "unguarded_frames": 40}
    rec = SegmentRecord(filename="s.jsonl", sha256="a" * 64, frame_count=900, size_bytes=1,
                        compressed=True, start_utc="t0", end_utc="t1",
                        guard_counters=counters)

    d = rec.to_dict()
    assert d["guard_counters"] == counters, "the counters must be written into the record"
    back = SegmentRecord.from_dict(d)
    assert back.guard_counters == counters, "and must survive the round trip"


def test_dual_2_3_a_segment_that_predates_the_counters_reads_UNKNOWN_not_zero():
    """DUAL — absence is `{}` (unknown), never zeros.

    Zeros would manufacture "we counted and found none" out of silence — the
    `checksum_failures_total` error one directory over. WO-066 already ruled that a venue with no
    checksum reports `null`, never `0`; the same distinction applies to a segment nobody counted.
    """
    legacy = SegmentRecord.from_dict({"filename": "old.jsonl", "sha256": "b" * 64,
                                      "frame_count": 10, "size_bytes": 1, "compressed": True})
    assert legacy.guard_counters == {}, "an uncounted segment must not claim zero refusals"
    assert legacy.guard_counters is not None


def test_2_3_per_segment_resolves_a_blackout_the_aggregate_hides():
    """The reason it is per-SEGMENT. Six consecutive dark hours vs one survivable-looking total.

    WO-066's band truncated six consecutive hours while the run-level counter showed a single
    number. The shape of the failure lived entirely in its distribution over time, and an
    aggregate destroys exactly that.
    """
    hourly = [{"frames_emitted": 6000, "refused_cross_venue_band": 5} for _ in range(6)]
    blackout = [{"frames_emitted": 10, "refused_cross_venue_band": 5990} for _ in range(6)]
    segs = hourly + blackout

    total_refused = sum(s["refused_cross_venue_band"] for s in segs)
    total_frames = sum(s["frames_emitted"] + s["refused_cross_venue_band"] for s in segs)
    aggregate_rate = total_refused / total_frames

    dark = [s for s in segs
            if s["refused_cross_venue_band"] > s["frames_emitted"]]
    assert len(dark) == 6, "per-segment counters localise the blackout to six consecutive segments"
    assert aggregate_rate < 0.51, (
        f"the aggregate rate is {aggregate_rate:.1%} — a single number that does not reveal that "
        f"half the run was dark in one contiguous block, which is the shape a reader acts on")


# ═══ REACHABILITY (0.14) — every repair names its production call site ════════════════════════

def test_reachability_all_three_repairs_are_wired_into_the_capture():
    """0.14 — an unwired mitigation is the WO-055 defect and this WO's likeliest failure mode."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "tools" / "hyperliquid_capture.py").read_text(
        encoding="utf-8")

    assert "mit.RollingCrossVenueBand()" in src, "§2.1 not constructed in the capture"
    assert "self.band.observe(" in src, "§2.1 never fed arrivals — the band would never re-derive"
    assert "mit.CounterpartLiveness()" in src, "§2.2 not constructed"
    assert "require_available_at_start()" in src, "§2.2's refuse-to-start never called"
    assert "mit.guard_state(" in src, "§2.2's three states never computed"
    assert "guard_counters=dict(self._seg_counters)" in src, "§2.3 never reaches the record"
    assert "self._seg_bump(" in src, "§2.3 counters never incremented"

    # The frozen derivation must be GONE, not merely unused — a line still assigning a frozen band
    # would be one edit away from being read again.
    assert "mit.CrossVenueBand.derive(self._log_bases)" not in src, (
        "the one-shot frozen derivation is still present in the capture; §2.1 is the repair of "
        "exactly that line")
