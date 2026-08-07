"""
Fill (Trade) Data Model

Constitutional Principles:
- I. Truth Before Profit: All cost components included
- VIII. Total Observability & Provenance: CAD tax fields captured
"""

from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Fill:
    """
    Executed trade result (simulated or real).

    Invariants:
    - total_cost = fees + slippage_cost (WO-008a-R6, reaffirmed D14; unified WO-011 §1)
    - spread_cost is ATTRIBUTION of fill_price (already embedded), NOT part of total_cost
    - All cost components are non-negative
    - cad_value is calculated for Canadian tax records

    Constitutional requirements:
    - Cost-inclusive (Principle I: Truth Before Profit)
    - CAD tax fields captured (Principle VIII: Total Observability & Provenance)
    """
    # WO-048 §5.1 (D-a): `timestamp` is MARKET TIME — the timestamp of the MarketState/BookState the
    # fill was priced from. Before WO-048 it was `datetime.now(UTC)`, i.e. replay wall-clock, so a
    # backtested trade could not be reconciled against the data it replayed and Principle VIII
    # (Total Observability & Provenance) failed at the backtest boundary. The frame's time IS the
    # time. `replay_timestamp` below carries the wall-clock of the replaying process as a SECONDARY
    # field — useful for debugging a run, never the trade's time.
    timestamp: datetime
    symbol: str
    side: str  # "BUY", "SELL"
    size: Decimal
    fill_price: Decimal
    spread_cost: Decimal
    slippage_cost: Decimal
    fees: Decimal
    total_cost: Decimal  # fees + slippage_cost (spread is attribution, WO-008a-R6)
    cad_value: Decimal  # For Canadian tax records
    # SECONDARY, never authoritative. Optional so every existing construction site is unaffected.
    replay_timestamp: Optional[datetime] = None
