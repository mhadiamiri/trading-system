"""
Position State Data Model
"""

from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionState:
    """
    Current portfolio state.

    Invariants:
    - current_quantity can be negative (short selling allowed in paper trading)
    - unrealized_pnl is calculated from current market prices
    - realized_pnl accumulates from closed trades
    """
    symbol: str
    current_quantity: Decimal  # Positive=long, negative=short, zero=flat
    average_entry_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    daily_pnl: Decimal
