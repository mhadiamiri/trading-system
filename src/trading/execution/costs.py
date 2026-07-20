"""
Unified execution cost model (WO-011 §1).

ONE ruled cost implementation, called by BOTH callers that used to disagree:
- the paper execution venue (trading.execution.paper), and
- the backtest cost model (trading.backtest.costs.CostModel).

Before WO-011 these were two implementations that differed by exactly one spread
(and, more subtly, by notional basis and slippage formula). The paper venue was
correct per WO-008a-R6; backtest/costs.py carried a superseded additive-spread
formula. This module is the single home the fork is closed into: there is now one
model, not two that happen to agree.

The ruled model (WO-008a-R6, reaffirmed D11/D14):
- Executed price crosses the spread: BUY pays the ask, SELL receives the bid
  (notional basis = executed price, RULING 5 / R6 — never mid).
- Fees are charged on the executed notional (size x executed price).
- Spread cost is ATTRIBUTION of the executed price, which already embeds the
  spread crossing. It is reported for transparency, NEVER summed into the total.
- Slippage is an ASSUMED constant fraction of notional (WO-008a-R5): notional x
  factor. Volume-scaling is a discarded elaboration (WO-011 RULING 4;
  see docs/open-cleanup.md) and is deliberately NOT implemented here.
- total = fees + slippage_cost.

Abnormal spread (> 5% of mid) is REJECTED with the declared ABNORMAL_SPREAD_REJECT
reason code (WO-007 / FR-015b); no fill is priced against it. WO-011 RULING 3
propagated this guard to the paper venue, which previously lacked it.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid a runtime import cycle; MarketState is only a type here
    from trading.data.market_state import MarketState

# FR-015b: a spread wider than this fraction (percent) of mid price is abnormal
# and the trade is rejected rather than priced against synthetic economics.
ABNORMAL_SPREAD_PCT_THRESHOLD = Decimal("5")


@dataclass(frozen=True)
class ExecutionCosts:
    """
    Ruled cost breakdown for a single fill.

    Invariant: total_cost == fees + slippage_cost. spread_cost is attribution of
    executed_price (already embedded in it) and is NEVER part of total_cost.
    """

    executed_price: Decimal
    fees: Decimal
    spread_cost: Decimal  # attribution, embedded in executed_price; NOT additive
    slippage_cost: Decimal
    total_cost: Decimal  # fees + slippage_cost (WO-008a-R6)


def compute_execution_costs(
    side: str,
    size: Decimal,
    market_state: "MarketState",
    fee_rate_pct: Decimal,
    slippage_factor: Decimal,
) -> ExecutionCosts:
    """
    Compute the ruled execution costs for a single fill.

    This is the SOLE cost implementation (WO-011 §1). The paper venue and the
    backtest CostModel both call it, so their economics are identical by
    construction rather than by two implementations happening to agree.

    Args:
        side: "BUY" or "SELL".
        size: Order size in base currency.
        market_state: Observed market state; sole source of bid/ask and spread.
        fee_rate_pct: Taker fee rate as a percent of notional.
        slippage_factor: Assumed constant slippage fraction of notional (WO-008a-R5).

    Returns:
        ExecutionCosts with executed price and every cost component.

    Raises:
        ValueError: ABNORMAL_SPREAD_REJECT when spread > 5% of mid (FR-015b).
    """
    # FR-015b (RULING 3): reject an abnormal spread before pricing anything. The
    # spread is OBSERVED from the tick, never synthesized, so this rejects real
    # bad ticks rather than papering over them with an assumed spread.
    spread_pct = (market_state.spread / market_state.mid_price) * Decimal("100")
    if spread_pct > ABNORMAL_SPREAD_PCT_THRESHOLD:
        raise ValueError(
            f"ABNORMAL_SPREAD_REJECT: Spread {spread_pct:.2f}% exceeds "
            f"{ABNORMAL_SPREAD_PCT_THRESHOLD}% threshold. "
            f"Bid: {market_state.best_bid}, Ask: {market_state.best_ask}, "
            f"Spread: {market_state.spread}"
        )

    # Executed price crosses the spread (R6 / RULING 5): BUY pays ask, SELL takes bid.
    if side == "BUY":
        executed_price = market_state.best_ask
    else:  # SELL
        executed_price = market_state.best_bid

    # Notional on the EXECUTED price (RULING 5) — never mid.
    notional = size * executed_price

    # 1. Trading fee on executed notional (additive).
    fees = notional * (fee_rate_pct / Decimal("100"))

    # 2. Spread cost = half-spread x size, from the OBSERVED bid/ask. Attribution
    #    of executed_price (R6): reported, never added to total.
    spread_cost = (market_state.spread / Decimal("2")) * size

    # 3. Slippage = assumed constant fraction of notional (WO-008a-R5, RULING 4).
    slippage_cost = notional * slippage_factor

    # Ruled total: fees + slippage only. Spread is already inside executed_price.
    total_cost = fees + slippage_cost

    return ExecutionCosts(
        executed_price=executed_price,
        fees=fees,
        spread_cost=spread_cost,
        slippage_cost=slippage_cost,
        total_cost=total_cost,
    )
