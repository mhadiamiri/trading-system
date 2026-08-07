"""
WO-050 §3 (R3) — POSITION-AWARE P&L.

WHAT THIS REPLACES. `PnLReport.generate_report` computes `+notional` for SELL, `−notional` for BUY,
with no position matching, no cost basis and no mark-to-market. `report.py:104` says so plainly:
*"Calculate gross P&L (simplified for walking skeleton)"*. That is honest at five trades and
meaningless at 3.5 million: WO-048's +$764,993,334.67 "gross P&L" is a sum of unmatched notionals
whose sign is an artefact of the BUY/SELL mix, not an economic result.

═══════════════════════════════════════════════════════════════════════════════════════════════
§3.1 THE DECLARED METHOD: **AVERAGE COST** (not FIFO).

Chosen, and the reason matters more than the choice:

  1. THE DATA MODEL ALREADY SAYS SO. `PositionState` carries `average_entry_price`
     (`position_state.py:22`) — a field that has existed since the walking skeleton and has never
     been populated. Average cost is the method this system's own state type was shaped for; FIFO
     would need a lot queue that `PositionState` cannot express, forcing a parallel structure and a
     second source of truth about the same position.
  2. IT IS PATH-INDEPENDENT for a single symbol: the realised P&L of a sequence depends only on
     quantities and prices, not on which lot is nominated. That removes an entire class of
     "why did the number change" questions from a system whose purpose is to be checkable.
  3. FIFO's advantage is tax-lot fidelity, which matters for tax reporting and not for measuring
     whether a strategy made money. This project already separates those concerns (`cad_value` is
     carried for tax records independently).

Declaring it is the requirement; leaving it ambiguous is what §3.1 forbids.
═══════════════════════════════════════════════════════════════════════════════════════════════

THE MECHANICS. A position carries `(quantity, average_cost)`.

  - INCREASING (same side, or opening from flat): the average cost is re-weighted. No P&L realises —
    buying more of what you hold is not a result, it is a bigger bet.
  - REDUCING (opposite side, up to the held size): P&L realises on the closed quantity, against the
    average cost. The average cost of the REMAINDER is unchanged — closing part of a position does
    not re-price what is left.
  - CROSSING ZERO: the held quantity closes at the average cost (realising), and the excess OPENS a
    new position on the other side at the trade price. Handled explicitly, because a sign flip that
    silently kept the old average cost would carry a long's basis into a short.

SIGN CONVENTION. Long is positive, short is negative, matching `PositionState.current_quantity`
("Positive=long, negative=short, zero=flat"). Realised P&L on closing a LONG is
`(exit − entry) × qty`; on closing a SHORT it is `(entry − exit) × qty`. Both fall out of the same
expression once quantity is signed.

COSTS ARE NOT NETTED HERE. `realised_pnl` is the pure price result. Fees and slippage are additive
costs tracked separately and subtracted once at the aggregate (§3.3), so the cost channels stay
attributable rather than being buried inside a single number.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal


@dataclass(frozen=True)
class Position:
    """A single-symbol position under AVERAGE-COST accounting.

    `quantity` is signed (long positive, short negative). `average_cost` is the volume-weighted
    entry price of the CURRENT holding; it is meaningless when flat and is held at zero there so a
    stale basis can never survive a round trip.
    """

    quantity: Decimal = Decimal("0")
    average_cost: Decimal = Decimal("0")
    realised_pnl: Decimal = Decimal("0")

    @property
    def is_flat(self) -> bool:
        return self.quantity == 0

    def unrealised_pnl(self, mark_price: Decimal) -> Decimal:
        """Mark-to-market of the OPEN position. Exactly zero when flat — which is the property
        §3.2 asserts at every segment boundary."""
        if self.quantity == 0:
            return Decimal("0")
        return (mark_price - self.average_cost) * self.quantity

    def apply(self, side: str, size: Decimal, price: Decimal) -> "Position":
        """Apply a fill and return the new position. Pure — no mutation, no I/O.

        `side` is "BUY"/"SELL" and `size` is an UNSIGNED MAGNITUDE, matching the convention the rest
        of the system actually uses (see the WO-049 §1 finding: `DesiredPosition`'s docstring claims
        signed quantities, but every real caller emits a magnitude and takes direction from `side`).
        """
        if size <= 0:
            return self
        signed = size if side == "BUY" else -size
        current = self.quantity

        # OPENING FROM FLAT, or INCREASING an existing position on the same side.
        if current == 0 or (current > 0) == (signed > 0):
            new_qty = current + signed
            # Volume-weighted average cost over the absolute sizes.
            total_cost = (abs(current) * self.average_cost) + (abs(signed) * price)
            new_avg = total_cost / abs(new_qty) if new_qty != 0 else Decimal("0")
            return replace(self, quantity=new_qty, average_cost=new_avg)

        # REDUCING, and possibly crossing zero.
        closing = min(abs(signed), abs(current))
        # Realised P&L on the closed quantity, against the average cost. The sign of `current`
        # makes this correct for both directions: closing a long realises (exit − entry), closing a
        # short realises (entry − exit).
        direction = Decimal("1") if current > 0 else Decimal("-1")
        realised = (price - self.average_cost) * closing * direction
        new_realised = self.realised_pnl + realised

        remaining = current + signed
        if remaining == 0:
            # FLAT. The average cost is cleared so no basis can survive into the next position.
            return replace(self, quantity=Decimal("0"), average_cost=Decimal("0"),
                           realised_pnl=new_realised)
        if (remaining > 0) == (current > 0):
            # Partially closed — the REMAINDER keeps its original average cost. Closing part of a
            # position does not re-price what is left.
            return replace(self, quantity=remaining, realised_pnl=new_realised)
        # CROSSED ZERO: the old position closed entirely and a NEW one opened on the other side at
        # the trade price. Explicit, because silently retaining the old average cost here would
        # carry a long's basis into a short.
        return replace(self, quantity=remaining, average_cost=price, realised_pnl=new_realised)


@dataclass
class PositionLedger:
    """Accumulates fills into a position and a realised-P&L figure, with costs kept separate.

    §3.3: net = realised P&L − total costs, with fees and slippage attributed individually. Spread
    is ATTRIBUTION of the executed price (WO-008a-R6) and is reported, never summed into costs.
    """

    position: Position = None
    fees: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    spread_attribution: Decimal = Decimal("0")
    trades: int = 0
    boundary_closes: int = 0

    def __post_init__(self):
        if self.position is None:
            self.position = Position()

    def apply_fill(self, fill: dict, is_boundary_close: bool = False) -> None:
        """Fold one fill into the ledger. `fill` is the paper venue's dict."""
        self.position = self.position.apply(
            side=fill["side"],
            size=Decimal(str(fill["size"])),
            price=Decimal(str(fill["fill_price"])),
        )
        self.fees += Decimal(str(fill["fees"]))
        self.slippage += Decimal(str(fill["slippage_cost"]))
        self.spread_attribution += Decimal(str(fill["spread_cost"]))
        self.trades += 1
        if is_boundary_close:
            self.boundary_closes += 1

    @property
    def total_costs(self) -> Decimal:
        """fees + slippage. Spread is NEVER included — it is already inside the executed price."""
        return self.fees + self.slippage

    @property
    def realised_pnl(self) -> Decimal:
        return self.position.realised_pnl

    def net_pnl(self) -> Decimal:
        """§3.3: realised P&L MINUS total costs."""
        return self.realised_pnl - self.total_costs

    def summary(self, mark_price: Decimal = None) -> dict:
        unrealised = (self.position.unrealised_pnl(mark_price)
                      if mark_price is not None else Decimal("0"))
        return {
            "method": "average_cost",
            "realised_pnl": str(self.realised_pnl),
            "unrealised_pnl": str(unrealised),
            "fees": str(self.fees),
            "slippage_cost": str(self.slippage),
            "spread_cost_attribution": str(self.spread_attribution),
            "total_costs": str(self.total_costs),
            "net_pnl": str(self.net_pnl()),
            "trades": self.trades,
            "boundary_closes": self.boundary_closes,
            "final_quantity": str(self.position.quantity),
            "final_average_cost": str(self.position.average_cost),
        }
