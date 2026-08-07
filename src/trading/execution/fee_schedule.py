"""
Kraken spot fee schedule — CITED, with its provenance attached (WO-051).

WHY THIS MODULE EXISTS
----------------------
Until WO-051 the taker fee lived in `PaperExecutionClient` as a bare
`DEFAULT_FEE_RATE_PCT = Decimal("0.26")`, annotated as DECLARED ENGINEERING JUDGEMENT — an
honest label, but still a number with no source. It was not a small assumption: in the only
strategy verdict this project has produced (WO-050, net −$2,223,991.19) fees were **96.3% of
total costs**. The figure that most determines the answer was the one figure nobody could
check.

Rule 0.1e: a rate that changes a verdict carries its source. So the rate is no longer typed
in — it is looked up from the published schedule recorded below, for a NAMED tier.

WHAT THIS BUYS
--------------
Changing the assumed fee is now a DECLARED ACT, the same discipline as the reason-code
vocabulary. You cannot quietly nudge a float: you change `ASSUMED_TIER` to another tier that
exists in the cited table, or you re-cite the schedule. A test (`test_fee_schedule.py`) pins
the wired constant to this table, so a constant that drifts from its citation fails the build.

WHAT THIS DOES *NOT* DO
-----------------------
It does not re-open WO-050. Per WO-051 §0.1 and D50, correcting a citation is not a licence to
re-derive a published number: **the cited rate applies to FUTURE runs only.** WO-050's verdict
stands as computed, at the 0.26% that was in force when it ran.
"""

from dataclasses import dataclass
from decimal import Decimal

# ── THE CITATION ──────────────────────────────────────────────────────────────────────────────
#
# Source page   : https://www.kraken.com/features/fee-schedule  ("Kraken Pro — Spot crypto")
# Retrieved     : 2026-08-07 (UTC)
# Effective date: the schedule page itself publishes NO effective date. The related change to how
#                 a tier is DETERMINED is dated: "Starting July 9, 2026" your tier is the best of
#                 your spot 30-day volume or your Assets on Platform (AoP).
#                 https://support.kraken.com/articles/cross-platform-fee-tier-changes
# Product       : Kraken Pro / advanced trading. NOT "Instant Buy", whose fees are higher and
#                 which is not the product a programmatic order path would use.
# Basis         : 30-day rolling volume — "measured and applicable for trades occurring in the
#                 last 30 days only".
SCHEDULE_SOURCE_URL = "https://www.kraken.com/features/fee-schedule"
SCHEDULE_RETRIEVED_UTC = "2026-08-07"
SCHEDULE_TIER_RULE_URL = "https://support.kraken.com/articles/cross-platform-fee-tier-changes"
SCHEDULE_TIER_RULE_EFFECTIVE = "2026-07-09"
SCHEDULE_PRODUCT = "Kraken Pro spot (advanced trading)"


@dataclass(frozen=True)
class FeeTier:
    """One published row of the schedule. Rates are PERCENT of notional, as published."""

    name: str
    min_30d_volume_usd: Decimal  # lower bound of the published volume band
    min_assets_on_platform_usd: Decimal | None  # AoP alternative; None where published "N/A"
    maker_pct: Decimal
    taker_pct: Decimal


# The published table, transcribed as-is. Do not "tidy" these numbers — they are a citation.
KRAKEN_SPOT_SCHEDULE: tuple[FeeTier, ...] = (
    FeeTier("Tier 1", Decimal("0"), None, Decimal("0.40"), Decimal("0.80")),
    FeeTier("Tier 2", Decimal("2500"), None, Decimal("0.30"), Decimal("0.60")),
    FeeTier("Tier 3", Decimal("10000"), Decimal("20000"), Decimal("0.22"), Decimal("0.38")),
    FeeTier("Tier 4", Decimal("25000"), Decimal("50000"), Decimal("0.20"), Decimal("0.35")),
    FeeTier("Tier 5", Decimal("50000"), Decimal("100000"), Decimal("0.15"), Decimal("0.30")),
    FeeTier("Tier 6", Decimal("100000"), Decimal("200000"), Decimal("0.12"), Decimal("0.25")),
    FeeTier("Tier 7", Decimal("250000"), Decimal("400000"), Decimal("0.10"), Decimal("0.22")),
    FeeTier("Tier 8", Decimal("500000"), Decimal("600000"), Decimal("0.08"), Decimal("0.20")),
    FeeTier("Tier 9", Decimal("1000000"), Decimal("1000000"), Decimal("0.06"), Decimal("0.18")),
    FeeTier("Tier 10", Decimal("2500000"), Decimal("2500000"), Decimal("0.04"), Decimal("0.15")),
    FeeTier("Tier 11", Decimal("5000000"), Decimal("5000000"), Decimal("0.02"), Decimal("0.12")),
    FeeTier("Tier 12", Decimal("10000000"), Decimal("10000000"), Decimal("0.0"), Decimal("0.10")),
    FeeTier("Pro 1", Decimal("50000000"), Decimal("20000000"), Decimal("0.0"), Decimal("0.09")),
    FeeTier("Pro 2", Decimal("100000000"), Decimal("25000000"), Decimal("0.0"), Decimal("0.08")),
    FeeTier("Pro 3", Decimal("250000000"), Decimal("50000000"), Decimal("0.0"), Decimal("0.07")),
    FeeTier("Pro 4", Decimal("400000000"), Decimal("80000000"), Decimal("0.0"), Decimal("0.06")),
    FeeTier("Pro 5", Decimal("500000000"), Decimal("100000000"), Decimal("0.0"), Decimal("0.05")),
)

# ── THE DECLARED ASSUMPTION ───────────────────────────────────────────────────────────────────
#
# TIER 1 — the base tier, $0+ 30-day volume, no AoP requirement.
#
# REASONING (WO-051 §2.2). This system has never placed an order. Its 30-day spot volume is
# exactly $0 and it holds no assets on the platform, so Tier 1 is not a conservative choice —
# it is the only tier the account can substantiate. Every better tier would be a cost
# assumption wearing a fact's clothing: assuming Tier 6 buys a 3.2x cheaper fee by asserting
# $100K of monthly volume that does not exist.
#
# This tier is also SELF-CORRECTING in the right direction. A strategy that cannot survive
# Tier 1 might survive Tier 6 — but it only reaches Tier 6 by trading enough to get there,
# which means paying Tier 1 first. Tier 1 is the fee you pay on the way in.
ASSUMED_TIER = "Tier 1"


def tier(name: str = ASSUMED_TIER) -> FeeTier:
    """
    Look up a published tier BY NAME.

    Raises:
        KeyError: the name is not a row of the cited schedule. This is the point of the
            function — you cannot invent a tier, only select one that was published.
    """
    for row in KRAKEN_SPOT_SCHEDULE:
        if row.name == name:
            return row
    raise KeyError(
        f"{name!r} is not a tier in the cited Kraken spot schedule "
        f"({SCHEDULE_SOURCE_URL}, retrieved {SCHEDULE_RETRIEVED_UTC}). "
        f"Published tiers: {', '.join(r.name for r in KRAKEN_SPOT_SCHEDULE)}"
    )


def taker_pct(name: str = ASSUMED_TIER) -> Decimal:
    """The published TAKER rate, percent of notional, for a named tier."""
    return tier(name).taker_pct


def maker_pct(name: str = ASSUMED_TIER) -> Decimal:
    """
    The published MAKER rate, percent of notional, for a named tier.

    RECORDED, NOT WIRED (WO-051 §2.3). No execution path uses this: every fill this system
    prices crosses the spread and is therefore a taker fill (WO-008a-R6 / RULING 5). It is
    declared here because the parked maker-rebate research track (D51) will need a cited
    figure the moment it wakes up, and citing it then — after seeing what it would save —
    would be citing to a conclusion.
    """
    return tier(name).maker_pct


def citation() -> dict:
    """The provenance record, for reports and run artifacts."""
    row = tier()
    return {
        "source_url": SCHEDULE_SOURCE_URL,
        "retrieved_utc": SCHEDULE_RETRIEVED_UTC,
        "product": SCHEDULE_PRODUCT,
        "tier_rule_url": SCHEDULE_TIER_RULE_URL,
        "tier_rule_effective": SCHEDULE_TIER_RULE_EFFECTIVE,
        "assumed_tier": row.name,
        "assumed_tier_min_30d_volume_usd": str(row.min_30d_volume_usd),
        "taker_pct": str(row.taker_pct),
        "maker_pct_recorded_not_wired": str(row.maker_pct),
    }
