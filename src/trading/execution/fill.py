"""
Fill (Trade) Data Model

Constitutional Principles:
- I. Truth Before Profit: All cost components included
- VIII. Total Observability & Provenance: CAD tax fields captured
"""

from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


@dataclass(frozen=True)
class Fill:
    """
    Executed trade result (simulated or real).

    Invariants:
    - total_cost = spread_cost + slippage_cost + fees
    - All cost components are non-negative
    - cad_value is calculated for Canadian tax records

    Constitutional requirements:
    - Cost-inclusive (Principle I: Truth Before Profit)
    - CAD tax fields captured (Principle VIII: Total Observability & Provenance)
    """
    timestamp: datetime
    symbol: str
    side: str  # "BUY", "SELL"
    size: Decimal
    fill_price: Decimal
    spread_cost: Decimal
    slippage_cost: Decimal
    fees: Decimal
    total_cost: Decimal  # spread_cost + slippage_cost + fees
    cad_value: Decimal  # For Canadian tax records
