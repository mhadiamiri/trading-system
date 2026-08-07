"""
WO-051 §3.3 — THE CITATION PIN.

The taker fee is 96.3% of total costs in the only strategy verdict this project has produced.
Before WO-051 it was a bare float annotated "DECLARED ENGINEERING JUDGEMENT". These tests exist
so that it cannot silently become one again: if the wired constant ever stops equalling the
published rate for the declared tier, the build fails.

§0.10 — every test here is single-purpose, so a mutation can attribute its failure.
"""

from decimal import Decimal

import pytest

from trading.execution import fee_schedule
from trading.execution.paper import PaperExecutionClient


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §3.3 — THE WIRED CONSTANT EQUALS THE CITED SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_wired_taker_rate_equals_the_cited_schedule_for_the_declared_tier():
    """THE PIN (§3.3). The venue's default fee IS the published rate for the declared tier —
    not a number that happens to resemble it. If someone edits either side, this fails."""
    published = fee_schedule.tier(fee_schedule.ASSUMED_TIER).taker_pct
    assert PaperExecutionClient.DEFAULT_FEE_RATE_PCT == published, (
        f"wired fee {PaperExecutionClient.DEFAULT_FEE_RATE_PCT} has drifted from the cited "
        f"{fee_schedule.ASSUMED_TIER} taker rate {published} "
        f"({fee_schedule.SCHEDULE_SOURCE_URL}, retrieved {fee_schedule.SCHEDULE_RETRIEVED_UTC})"
    )


def test_the_declared_tier_is_the_base_tier_the_account_can_substantiate():
    """§2.2: a system that has never traded has $0 of 30-day volume. Any better tier would be an
    assumption wearing a fact's clothing, so the declared tier's volume floor must be zero."""
    assert fee_schedule.tier(fee_schedule.ASSUMED_TIER).min_30d_volume_usd == Decimal("0")


def test_the_declared_tier_is_the_most_expensive_taker_row_published():
    """Independent of the tier's NAME: no published row may be costlier than the one assumed.
    This catches a re-cite that renames tiers or reorders the table."""
    worst = max(row.taker_pct for row in fee_schedule.KRAKEN_SPOT_SCHEDULE)
    assert fee_schedule.taker_pct() == worst


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §3.2 — CHANGING TIER IS A DECLARED ACT, NOT A FLOAT EDIT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_an_unpublished_tier_cannot_be_selected():
    """§3.2: the rate is looked up BY NAME from the recorded schedule. You may choose a row that
    was published; you may not invent one. A wished-for tier raises rather than resolving."""
    with pytest.raises(KeyError):
        fee_schedule.taker_pct("Tier 0")


def test_every_published_row_carries_both_rates_and_a_volume_floor():
    """A citation with a missing cell is not a citation."""
    assert len(fee_schedule.KRAKEN_SPOT_SCHEDULE) == 17
    for row in fee_schedule.KRAKEN_SPOT_SCHEDULE:
        assert row.name and row.min_30d_volume_usd >= 0
        assert row.taker_pct >= 0 and row.maker_pct >= 0


def test_taker_is_never_cheaper_than_maker_in_the_cited_table():
    """A transcription sanity check on the citation itself: on every published row the taker pays
    at least what the maker pays. A swapped column would break this."""
    for row in fee_schedule.KRAKEN_SPOT_SCHEDULE:
        assert row.taker_pct >= row.maker_pct, f"{row.name}: maker/taker columns look swapped"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.3 — THE MAKER RATE IS RECORDED BUT NOT WIRED
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_maker_rate_is_recorded_for_the_declared_tier():
    """D51's parked research track will need a cited maker figure. Citing it after seeing what it
    would save is citing to a conclusion, so it is declared now."""
    assert fee_schedule.maker_pct() == Decimal("0.40")


def test_maker_rate_is_not_wired_into_execution():
    """§2.3: RECORDED, NOT WIRED. Every fill this system prices crosses the spread and is a taker
    fill (WO-008a-R6), so no execution default may carry the maker rate."""
    assert PaperExecutionClient.DEFAULT_FEE_RATE_PCT != fee_schedule.maker_pct()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PROVENANCE IS ATTACHED, NOT REMEMBERED
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_the_citation_record_carries_url_and_retrieval_date():
    """§3.1: a cited constant carries its source in code, so the next person to touch it knows
    where it came from without reading a report."""
    c = fee_schedule.citation()
    assert c["source_url"].startswith("https://www.kraken.com/")
    assert c["retrieved_utc"] == "2026-08-07"
    assert c["assumed_tier"] == fee_schedule.ASSUMED_TIER
    assert c["taker_pct"] == str(PaperExecutionClient.DEFAULT_FEE_RATE_PCT)
