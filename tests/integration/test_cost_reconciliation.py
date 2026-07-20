"""
Cost reconciliation: the backtest path and the paper venue agree TO THE CENT
(WO-011 §4).

Before WO-011 these two paths were separate implementations that disagreed on the
total (additive vs ruled), the notional basis (mid vs executed price), and the
slippage formula (volume-scaled vs constant). WO-011 §1 unified them onto the
single trading.execution.costs.compute_execution_costs, so they now agree by
CONSTRUCTION rather than by two implementations happening to match.

This is the permanent regression test that keeps the fork from silently reopening:
drive IDENTICAL inputs through BOTH paths and assert every component — executed
price, fee, spread attribution, slippage, and total — is identical across all
three axes, for a BUY, a SELL, and an edge case (a wide but valid spread).

Constitutional requirements:
- Principle I: Truth Before Profit (one definition of cost, everywhere)
- WO-008a-R6 ruled model; WO-011 §1 unification
"""

from decimal import Decimal

import pytest
from datetime import datetime, UTC

from trading.backtest.costs import CostModel, Side
from trading.execution.costs import compute_execution_costs
from trading.execution.paper import PaperExecutionClient
from trading.data.market_state import MarketState

FEE_RATE = Decimal("0.1")
SLIPPAGE = Decimal("0.001")
CENT = Decimal("0.01")


def _ms(bid: str, ask: str) -> MarketState:
    return MarketState(
        timestamp=datetime.now(UTC),
        symbol="BTC/USD",
        best_bid=Decimal(bid),
        best_ask=Decimal(ask),
        best_bid_size=Decimal("10.0"),
        best_ask_size=Decimal("10.0"),
        trade_count=0,
        total_volume=Decimal("0"),
        last_price=Decimal(bid),
    )


async def _paper(side: str, ms: MarketState, size: Decimal) -> dict:
    """Fill economics as the paper venue reports them."""
    venue = PaperExecutionClient(fee_rate_pct=FEE_RATE, slippage_factor=SLIPPAGE)
    venue.set_market_state(ms)
    return await venue.place_order(
        symbol="BTC/USD", side=side, size=float(size), price=0.0, kill_switch_engaged=False
    )


def _backtest(side: str, ms: MarketState, size: Decimal):
    """Fill economics via the backtest CostModel + the unified executed price."""
    model = CostModel(fee_rate_pct=FEE_RATE, slippage_factor=SLIPPAGE)
    cb = model.calculate_costs_from_market_state(
        side=Side[side], size=size, market_state=ms
    )
    ec = compute_execution_costs(side, size, ms, FEE_RATE, SLIPPAGE)  # carries executed_price
    return cb, ec


def _cent(x) -> Decimal:
    return Decimal(str(x)).quantize(CENT)


CASES = [
    ("BUY", "64997.50", "65002.50", Decimal("1.0"), "buy, normal spread 5.00"),
    ("SELL", "64997.50", "65002.50", Decimal("2.5"), "sell, normal spread 5.00"),
    # Edge case: a WIDE but valid spread (~4.6% < 5% threshold) with a small size.
    ("BUY", "63000.00", "66000.00", Decimal("0.01"), "edge: wide spread ~4.6%, small size"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("side,bid,ask,size,label", CASES)
async def test_backtest_and_paper_reconcile_to_the_cent(side, bid, ask, size, label):
    """Every cost component agrees to the cent across all three axes."""
    ms = _ms(bid, ask)
    paper = await _paper(side, ms, size)
    cb, ec = _backtest(side, ms, size)

    # Executed price (notional-basis axis): BUY at ask, SELL at bid — same on both.
    assert _cent(paper["fill_price"]) == _cent(ec.executed_price), f"{label}: executed price"
    # Fee axis.
    assert _cent(paper["fees"]) == _cent(cb.fees), f"{label}: fees"
    # Spread attribution axis.
    assert _cent(paper["spread_cost"]) == _cent(cb.spread_cost), f"{label}: spread"
    # Slippage axis (constant, not volume-scaled).
    assert _cent(paper["slippage_cost"]) == _cent(cb.slippage_cost), f"{label}: slippage"
    # Total axis (ruled: fees + slippage).
    assert _cent(paper["total_cost"]) == _cent(cb.total_cost), f"{label}: total"

    # And the total really is the ruled sum on both sides.
    assert _cent(cb.total_cost) == _cent(cb.fees + cb.slippage_cost), f"{label}: ruled total"


@pytest.mark.asyncio
async def test_abnormal_spread_rejected_identically_on_both_paths():
    """RULING 3: a >5% spread is rejected the same way on both paths."""
    ms = _ms("50000.00", "60000.00")  # 20% spread
    with pytest.raises(ValueError, match="ABNORMAL_SPREAD_REJECT"):
        await _paper("BUY", ms, Decimal("1.0"))
    model = CostModel(fee_rate_pct=FEE_RATE, slippage_factor=SLIPPAGE)
    with pytest.raises(ValueError, match="ABNORMAL_SPREAD_REJECT"):
        model.calculate_costs_from_market_state(
            side=Side.BUY, size=Decimal("1.0"), market_state=ms
        )
