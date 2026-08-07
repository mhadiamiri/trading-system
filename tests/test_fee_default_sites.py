"""
WO-052 §3.4 — THE EXTENDED FEE-DEFAULT GUARD (D51 ruling 4a).

WHY THIS FILE REPLACES A PER-CLASS ASSERTION
--------------------------------------------
WO-050 fixed the identical-channels defect in `PaperExecutionClient` and guarded it *there*.
WO-051 cited the fee and routed `PaperExecutionClient` and pinned it *there*. Both guards were
correct and both were scoped to one class — so `CostModel` kept an uncited 0.1% fee, 8x below the
cited rate, with the WO-048 identical-channels coincidence still live, through two work orders that
each believed they had closed exactly that bug.

That is the incidental-coverage doctrine's newest specimen: **a guard that covers one of N sites
reports the same green as a guard that covers all N.**

So this guard is not written per-class. It **discovers** the sites by scanning `src/` and checks
each one, which means adding a new fee default without routing it FAILS — the failure mode that
actually happened. Per §0.11 the count is enumerated, never assumed.

THE REGISTRY BELOW IS A DECLARATION, NOT A CACHE. A site is either routed through
`fee_schedule` or declared independent WITH ITS REASON. There is no third state, and a site the
scanner finds that is not declared here is an error by construction.
"""

import ast
import re
from decimal import Decimal
from pathlib import Path

import pytest

from trading.backtest.costs import CostModel
from trading.execution import fee_schedule
from trading.execution.paper import PaperExecutionClient

SRC = Path(__file__).resolve().parents[1] / "src"

# ── THE DECLARED SITE REGISTRY ────────────────────────────────────────────────────────────────
#
# Every production FEE default in src/. `routed=True` means the value comes from the cited
# schedule; anything else must carry a reason.
FEE_SITES = [
    {
        "name": "trading.execution.paper.PaperExecutionClient.DEFAULT_FEE_RATE_PCT",
        "cls": PaperExecutionClient,
        "routed": True,
        "reason": "the live/paper venue's taker fee — cited, WO-051",
    },
    {
        "name": "trading.backtest.costs.CostModel.DEFAULT_FEE_RATE_PCT",
        "cls": CostModel,
        "routed": True,
        "reason": "the backtest cost model's taker fee — cited, WO-052 (was an uncited 0.1%)",
    },
]

# Every production SLIPPAGE default in src/. These are DELIBERATELY INDEPENDENT of the fee
# schedule: slippage is not a venue-published figure, it is measured. Declared, not ambiguous.
SLIPPAGE_SITES = [
    {
        "name": "trading.execution.paper.PaperExecutionClient.DEFAULT_SLIPPAGE_FACTOR",
        "cls": PaperExecutionClient,
        "expected": Decimal("0.0001"),
        "reason": (
            "DELIBERATELY INDEPENDENT of fee_schedule: measured against 50,000 frames of "
            "corpus_20260805 (mean spread 0.0806 bps of mid), not published by any venue. "
            "WO-050 §4; reused not re-derived per WO-052 §3.3."
        ),
    },
    {
        "name": "trading.backtest.costs.CostModel.DEFAULT_SLIPPAGE_FACTOR",
        "cls": CostModel,
        "expected": Decimal("0.0001"),
        "reason": "same measured 1 bp, so the two cost models agree at their defaults (WO-052)",
    },
]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE GUARD — parameterised over the site list (§3.4)
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("site", FEE_SITES, ids=lambda s: s["name"].split(".")[-2])
def test_every_fee_default_is_routed_through_the_cited_schedule(site):
    """§3.2: EVERY production fee default equals the cited rate for the declared tier.

    This is the assertion whose absence let CostModel sit 8x below the cited rate.
    """
    assert site["routed"], f"{site['name']} is declared unrouted: {site['reason']}"
    actual = getattr(site["cls"], "DEFAULT_FEE_RATE_PCT")
    assert actual == fee_schedule.taker_pct(), (
        f"{site['name']} = {actual}, but the cited {fee_schedule.ASSUMED_TIER} taker rate is "
        f"{fee_schedule.taker_pct()} ({fee_schedule.SCHEDULE_SOURCE_URL})"
    )


@pytest.mark.parametrize("site", SLIPPAGE_SITES, ids=lambda s: s["name"].split(".")[-2])
def test_every_slippage_default_is_the_measured_value(site):
    """§3.2 dual: a default that stays independent is DECLARED as such, with its reason, and is
    still pinned. 'Independent' must not mean 'unchecked'."""
    actual = getattr(site["cls"], "DEFAULT_SLIPPAGE_FACTOR")
    assert actual == site["expected"], f"{site['name']} = {actual}, expected {site['expected']}"
    assert site["reason"], "an independent default must carry its reason"


@pytest.mark.parametrize("site", FEE_SITES, ids=lambda s: s["name"].split(".")[-2])
def test_r4_channels_are_distinct_at_every_site(site):
    """§3.4 — R4, EXTENDED. WO-050 asserted this for PaperExecutionClient only, which is exactly
    why CostModel kept `fee 0.1%` == `slippage 0.001` == the same 0.001 of notional for two more
    work orders. Two channels that always agree cannot be told apart in any output."""
    fee_fraction = getattr(site["cls"], "DEFAULT_FEE_RATE_PCT") / Decimal("100")
    slip_fraction = getattr(site["cls"], "DEFAULT_SLIPPAGE_FACTOR")
    assert fee_fraction != slip_fraction, (
        f"{site['name']}: fee and slippage defaults are numerically identical "
        f"({fee_fraction}) — the WO-048 coincidence has returned"
    )


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE COMPLETENESS GUARD — a NEW site cannot appear undeclared (§0.11)
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _discover_defaults(attr_name: str) -> set[str]:
    """Find every class attribute assignment named `attr_name` under src/, by AST.

    Regex would match the name inside comments and docstrings — both files carry long comments
    that mention these constants — so this parses instead.
    """
    found = set()
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == attr_name:
                        module = path.relative_to(SRC).with_suffix("").as_posix().replace("/", ".")
                        found.add(f"{module}.{node.name}.{attr_name}")
    return found


def test_no_undeclared_fee_default_exists_in_src():
    """§0.11 — ENUMERATE, DO NOT ASSUME THE COUNT.

    THE GUARD THAT WOULD HAVE CAUGHT THIS BUG. A new class with a `DEFAULT_FEE_RATE_PCT` that
    nobody routed does not quietly inherit a green build: it fails here, by name.
    """
    discovered = _discover_defaults("DEFAULT_FEE_RATE_PCT")
    declared = {s["name"] for s in FEE_SITES}
    assert discovered == declared, (
        f"fee-default sites in src/ do not match the declared registry.\n"
        f"  UNDECLARED (found in src, absent from FEE_SITES): {sorted(discovered - declared)}\n"
        f"  STALE (declared, no longer in src)              : {sorted(declared - discovered)}\n"
        f"Add the site to FEE_SITES and route it, or declare it independent with its reason."
    )


def test_no_undeclared_slippage_default_exists_in_src():
    """The same completeness check for the slippage channel."""
    discovered = _discover_defaults("DEFAULT_SLIPPAGE_FACTOR")
    declared = {s["name"] for s in SLIPPAGE_SITES}
    assert discovered == declared, (
        f"slippage-default sites in src/ do not match the declared registry.\n"
        f"  UNDECLARED: {sorted(discovered - declared)}\n"
        f"  STALE     : {sorted(declared - discovered)}"
    )


def test_the_two_cost_models_agree_at_their_defaults():
    """WO-011 unified the two cost implementations' ARITHMETIC. Their DEFAULTS then drifted apart
    anyway — 0.80% vs 0.1% — because nothing asserted they agreed. Now something does."""
    assert PaperExecutionClient.DEFAULT_FEE_RATE_PCT == CostModel.DEFAULT_FEE_RATE_PCT
    assert PaperExecutionClient.DEFAULT_SLIPPAGE_FACTOR == CostModel.DEFAULT_SLIPPAGE_FACTOR


def test_the_dead_env_knob_is_not_silently_reintroduced():
    """§3.1 FINDING: `.env.example` advertises `EXECUTION_FEE_RATE_PCT=0.1` — a knob implemented
    NOWHERE, naming a rate that is now 8x low. It is commented out, so it configures nothing; it
    only misinforms. This pins the fact that no code reads it, so that if someone ever wires it up
    they must confront the stale default rather than silently honouring it."""
    hits = [
        p for p in SRC.rglob("*.py")
        if re.search(r"EXECUTION_FEE_RATE_PCT", p.read_text(encoding="utf-8"))
    ]
    assert not hits, (
        f"EXECUTION_FEE_RATE_PCT is now read by {[str(p) for p in hits]} — it must resolve "
        f"through fee_schedule, not carry its own literal default"
    )
