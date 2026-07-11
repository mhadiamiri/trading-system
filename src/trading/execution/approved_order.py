"""
Approved Order Data Model

Constitutional Principles:
- III. AI Proposes, Deterministic Code Disposes: Result of risk engine
- VI. Risk Engine Is Sovereign: Clamp only reduces toward zero
"""

from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovedOrder:
    """
    Risk-approved order ready for execution.

    Invariants:
    - size > 0 (risk engine ensures non-zero)
    - size <= original_size (clamp only reduces toward zero)
    - side does not flip from original DesiredPosition

    Constitutional requirements:
    - Result of risk engine check (Principle III: Deterministic Code Disposes)
    - Clamp may only reduce size, never flip side (Principle VI: Risk Engine Is Sovereign)
    """
    timestamp: datetime
    symbol: str
    side: str  # "BUY", "SELL", "HOLD"
    size: Decimal
    price: Decimal
    reason_code: str  # e.g., "RISK_PASS", "RISK_CLAMP_MAX_POSITION"
    original_size: Decimal  # For audit trail
