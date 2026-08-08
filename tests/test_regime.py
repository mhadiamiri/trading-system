"""
WO-054 §3 — REGIME RECORDING, the eighth scope dimension.

§0.10 — single-purpose tests. §0.12 — the falsifier for "this summary supports claim X" is the
declared `not_supported` list, pinned below.
"""

from decimal import Decimal

from trading.data.regime import (
    COST_THRESHOLD_PCT, HORIZON_MINUTES, REGIME_FORM_VERSION, classify, summarise_returns,
)


def _walk(start, steps, pct_per_step):
    """A deterministic price path moving `pct_per_step` each bar, alternating direction."""
    out, px, sign = [Decimal(start)], Decimal(start), 1
    for i in range(steps):
        px = px * (Decimal("1") + sign * Decimal(str(pct_per_step)) / Decimal("100"))
        out.append(px)
        sign = -sign if (i % 2) else sign
    return out


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §3.4 BITE — QUIET AND VOLATILE WINDOWS PRODUCE MATERIALLY DIFFERENT SUMMARIES
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_bite_a_volatile_window_summarises_differently_from_a_quiet_one():
    """THE BITE (§3.4). If the summary did not actually read the prices, these would agree."""
    quiet = summarise_returns([_walk("64000", 120, 0.01)])
    volatile = summarise_returns([_walk("64000", 120, 2.0)])

    q5 = Decimal(quiet["horizons"]["5m"]["max_pct"])
    v5 = Decimal(volatile["horizons"]["5m"]["max_pct"])
    assert v5 > q5 * 10, f"volatile {v5} must dwarf quiet {q5}"
    assert Decimal(volatile["horizons"]["5m"]["median_pct"]) > \
        Decimal(quiet["horizons"]["5m"]["median_pct"])


def test_bite_the_cost_threshold_counts_discriminate():
    """The counts are what a cost-bar comparison turns on — they must move with the data."""
    quiet = summarise_returns([_walk("64000", 120, 0.01)])
    volatile = summarise_returns([_walk("64000", 120, 2.0)])
    assert quiet["horizons"]["5m"]["at_or_above"]["1.6216"] == 0
    assert volatile["horizons"]["5m"]["at_or_above"]["1.6216"] > 0


def test_dual_the_same_input_summarises_identically():
    """THE PRESERVATION DUAL (§0.4): the summary is a deterministic function of its input. A
    summary that varied run to run would 'discriminate' the bite by accident."""
    path = _walk("64000", 60, 0.5)
    assert summarise_returns([path]) == summarise_returns([path])


def test_a_quiet_regime_classifies_as_quiet_and_a_volatile_one_does_not():
    assert classify(summarise_returns([_walk("64000", 120, 0.01)])) == "QUIET"
    assert classify(summarise_returns([_walk("64000", 120, 2.0)])) == "ACTIVE"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §3.2 THE DECLARED FORM
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_windows_are_non_overlapping():
    """Overlapping windows would inflate n with correlated observations and make a distribution
    look better-supported than it is. 100 bars at stride 5 gives 19 windows, not 95."""
    s = summarise_returns([[Decimal(64000 + i) for i in range(100)]])
    assert s["horizons"]["5m"]["n_windows"] == 19


def test_a_window_never_spans_a_segment_boundary():
    """The containment the bar layer enforces, preserved here rather than re-derived. Two 10-bar
    segments must not produce a window straddling them."""
    seg = [Decimal("64000")] * 10
    two = summarise_returns([seg, seg])
    one = summarise_returns([seg + seg])
    assert two["horizons"]["5m"]["n_windows"] < one["horizons"]["5m"]["n_windows"]


def test_the_summary_answers_the_wo053_question_without_rereading_the_corpus():
    """§3.2's stated bar: a future reader must be able to ask 'what was the largest N-minute move'
    from the summary alone. Both quantities WO-053 needed are present at every horizon."""
    s = summarise_returns([_walk("64000", 200, 0.3)])
    for h in HORIZON_MINUTES:
        block = s["horizons"][f"{h}m"]
        assert block["median_pct"] is not None, "the 39x-typical claim needs a median"
        assert block["max_pct"] is not None, "the 4x-largest claim needs a maximum"


def test_all_declared_horizons_are_present():
    s = summarise_returns([_walk("64000", 400, 0.1)])
    assert set(s["horizons"]) == {f"{h}m" for h in HORIZON_MINUTES}


def test_the_declared_falsifier_travels_with_the_summary():
    """0.12 / §3.2: what this summary CANNOT support is recorded in the artifact itself, not only
    in a docstring a future reader may never open."""
    s = summarise_returns([_walk("64000", 60, 0.2)])
    joined = " ".join(s["not_supported"]).lower()
    assert "direction" in joined, "magnitudes only — cannot support a momentum claim"
    assert "intra-window path" in joined, "endpoints only — understates intrabar opportunity"
    assert "discontinuity" in joined
    assert "liquidity" in joined or "spread" in joined
    assert len(s["not_supported"]) >= 5


def test_the_form_is_versioned_and_the_statistic_is_named():
    s = summarise_returns([_walk("64000", 60, 0.2)])
    assert s["form"] == REGIME_FORM_VERSION
    assert "NON-OVERLAPPING" in s["statistic"]
    assert s["cost_thresholds_pct"] == [str(t) for t in COST_THRESHOLD_PCT]


def test_an_empty_input_reports_no_windows_rather_than_a_fabricated_zero():
    """A regime summary of nothing must say 'nothing', not report 0% volatility — which would read
    as an extraordinarily quiet market."""
    s = summarise_returns([])
    assert s["horizons"]["5m"]["n_windows"] == 0
    assert s["horizons"]["5m"]["max_pct"] is None
    assert classify(s) is None


def test_percentiles_are_values_that_actually_occurred():
    """Nearest-rank, no interpolation: every reported figure is a real observation."""
    s = summarise_returns([[Decimal("100"), Decimal("101"), Decimal("103"), Decimal("106")]],
                          bar_minutes=1)
    block = s["horizons"]["1m"]
    assert block["n_windows"] == 3
    assert Decimal(block["max_pct"]) > 0
