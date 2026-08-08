"""
WO-054 §3 — REGIME RECORDING: the EIGHTH declared scope dimension (D53 ruling 1).

The seven existing dimensions — host, load, source, duration, resolution, instrument, interpreter —
say what the apparatus was. None says **what the market was doing.** WO-053 produced an emphatic
verdict (0 trades, cost 4x the largest move) that is only interpretable against the fact that its
corpus was a QUIET market. Without a recorded regime, a future reader takes that verdict as
universal, which it is not.

WHY A DISTRIBUTION AND NOT A SINGLE NUMBER (§3.2)
-------------------------------------------------
A lone realized-volatility figure would NOT have supported WO-053's finding. That finding needed
two specific quantities — the MEDIAN move (to say cost is 39x typical) and the MAXIMUM move (to say
cost is 4x the largest thing that happened) — and a single σ gives neither. σ also compresses a
fat tail into the same number as a uniform wiggle, and the whole question "could any move have paid
the round trip" lives in the tail.

So the recorded form is a **percentile distribution of absolute returns, at several horizons**:

    for each horizon H in HORIZON_MINUTES:
        over every non-overlapping H-minute window WITHIN A SEGMENT:
            r = |close_end - close_start| / close_start * 100
        record: n, median, p90, p99, max, and counts over declared cost thresholds

This lets a future reader answer "what was the largest N-minute move" — the WO-053 question —
**without re-reading the corpus**, which is §3.2's stated bar.

THE FALSIFIER (§3.2 / 0.12): WHAT THIS SUMMARY CANNOT SUPPORT
--------------------------------------------------------------
Stated so nobody reads more into it than it holds:

  1. **Direction and autocorrelation.** Returns are stored as ABSOLUTE magnitudes. The summary
     cannot say whether moves trended or mean-reverted, so it can support "a move of size X was
     available" but never "a momentum strategy would have caught it".
  2. **Intra-window path.** A window's endpoints are recorded, not its route. A window that went
     +2% then back to 0% reports ~0%. So the summary UNDERSTATES the opportunity available to a
     strategy trading inside the horizon, and cannot support any claim about intrabar excursions.
  3. **Horizons not in the list.** Only the declared horizons are computed. A claim about a 37-minute
     move is not supported and must not be interpolated — volatility does not scale as sqrt(t) at
     fine horizons in practice.
  4. **Cross-segment moves.** Windows never span a discontinuity (the bar layer refuses it), so a
     move that happened ACROSS a gap is invisible here. The summary describes what was observable,
     not what the market did.
  5. **Volume/liquidity regime.** This is a PRICE summary. It says nothing about depth, spread or
     traded volume, so it cannot support "the market was liquid".

Any claim of those five kinds needs different evidence, and this summary is not it.

COMPUTED BY COMMITTED CODE IN THE TREE IT CERTIFIES (§3.3)
-----------------------------------------------------------
This module is in `src/`, under test, and the summary it produces is written into the corpus's own
metadata and hashed like everything else — satisfying the D51 standing rule that an
integrity-certifying figure must be computed by committed code, which `a025db1e…` did not.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

# ── DECLARED FORM (§3.2) ──────────────────────────────────────────────────────────────────────
#
# HORIZONS. 1/5/15/60 minutes: a geometric ladder spanning the horizons the fee bar leaves open.
# 5 is included because it is the horizon WO-053 registered, so its finding stays directly
# comparable against any future corpus. 60 is the top because beyond an hour a single segment
# rarely supplies enough non-overlapping windows to say anything (the corpus's longest continuous
# stretch is ~7 hours).
HORIZON_MINUTES = (1, 5, 15, 60)

# PERCENTILES. Median for "typical", p90/p99 for the shoulder, and the MAXIMUM always — the
# maximum is the quantity a cost-bar comparison actually turns on, and no percentile substitutes
# for it.
PERCENTILES = (50, 90, 99)

# COST THRESHOLDS, in percent of notional. Counting windows at or above each makes the regime
# summary directly answerable to the question that matters: could any move have paid the round
# trip? The values are the CITED Tier 1 round trip and its neighbours, not arbitrary levels.
COST_THRESHOLD_PCT = (Decimal("0.5"), Decimal("1.0"), Decimal("1.6216"), Decimal("3.2432"))

REGIME_FORM_VERSION = "regime-v1"


def _percentile(sorted_values: list, p: int) -> Decimal:
    """The p-th percentile of a sorted list, nearest-rank. Exact on Decimals — no interpolation,
    so the reported figure is always a value that actually occurred."""
    if not sorted_values:
        return Decimal("0")
    idx = min(len(sorted_values) - 1, int(len(sorted_values) * p / 100))
    return sorted_values[idx]


def summarise_returns(closes_by_segment: Iterable[Iterable[Decimal]],
                      bar_minutes: int = 1) -> dict:
    """Build the regime summary from per-segment sequences of bar closes.

    Args:
        closes_by_segment: one iterable of bar closes PER SEGMENT. Segments are kept separate so a
            window can never span a discontinuity — the same containment the bar layer enforces,
            preserved here rather than re-derived.
        bar_minutes: minutes per input bar, so horizons convert to a stride.

    Returns a dict keyed by horizon, plus provenance.
    """
    segments = [list(s) for s in closes_by_segment]
    horizons = {}

    for horizon in HORIZON_MINUTES:
        stride = max(1, horizon // bar_minutes)
        moves: list = []
        for closes in segments:
            # NON-OVERLAPPING windows: step by `stride`, not by 1. Overlapping windows would
            # inflate n with correlated observations and make a distribution look better-supported
            # than it is — the same "count the same thing twice" defect the seam ledger avoids.
            for i in range(0, len(closes) - stride, stride):
                first, last = closes[i], closes[i + stride]
                if first > 0:
                    moves.append(abs((last - first) / first * Decimal("100")))
        moves.sort()
        horizons[f"{horizon}m"] = _horizon_block(moves)

    return {
        "form": REGIME_FORM_VERSION,
        "statistic": ("percentile distribution of ABSOLUTE returns over NON-OVERLAPPING windows, "
                      "computed within segments only so no window spans a discontinuity"),
        "bar_minutes": bar_minutes,
        "horizons_minutes": list(HORIZON_MINUTES),
        "cost_thresholds_pct": [str(t) for t in COST_THRESHOLD_PCT],
        "not_supported": [
            "direction or autocorrelation (magnitudes only)",
            "intra-window path (endpoints only; understates intrabar opportunity)",
            "horizons outside the declared list (do not interpolate)",
            "moves spanning a discontinuity (never observed)",
            "liquidity, depth or spread regime (this is a PRICE summary)",
        ],
        "horizons": horizons,
    }


def _horizon_block(moves: list) -> dict:
    n = len(moves)
    block = {
        "n_windows": n,
        "median_pct": str(_percentile(moves, 50)) if n else None,
        "max_pct": str(moves[-1]) if n else None,
    }
    for p in PERCENTILES:
        block[f"p{p}_pct"] = str(_percentile(moves, p)) if n else None
    block["at_or_above"] = {
        str(t): sum(1 for m in moves if m >= t) for t in COST_THRESHOLD_PCT
    }
    return block


def classify(summary: dict, horizon: str = "5m") -> Optional[str]:
    """A one-word regime label for the given horizon, from the DECLARED thresholds.

    A label is a convenience for humans reading a manifest; the distribution above is the evidence.
    The bands are stated in code so the word is never a judgement call:

        QUIET       max move  <  0.5%      — no window reached even the loosest cost threshold
        MODERATE    max move  <  1.6216%   — moves occurred but none paid the cited round trip
        ACTIVE      max move  >= 1.6216%   — at least one window cleared the round-trip cost
    """
    block = summary.get("horizons", {}).get(horizon)
    if not block or block.get("max_pct") is None:
        return None
    mx = Decimal(block["max_pct"])
    if mx < Decimal("0.5"):
        return "QUIET"
    if mx < Decimal("1.6216"):
        return "MODERATE"
    return "ACTIVE"
