"""
Risk Engine Interface Contract

This module defines the Risk Engine interface.

Constitutional Principles:
- III. AI Proposes, Deterministic Code Disposes: Risk engine is deterministic
- VI. Risk Engine Is Sovereign: Final authority over all orders
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum

from trading.data.market_state import MarketState
from trading.data.desired_position import DesiredPosition, Side
from trading.execution.approved_order import ApprovedOrder
from trading.risk.position_state import PositionState


class RiskDecision(Enum):
    """Risk engine decision types."""
    PASS = "PASS"  # Order approved unchanged
    CLAMP = "CLAMP"  # Order size reduced toward zero
    VETO = "VETO"  # Order rejected entirely


class RiskEngine(ABC):
    """
    Risk Engine interface.

    Constitutional requirements:
    - Pure deterministic function (no I/O, network, randomness, clock reads)
    - Final authority over all orders (Principle VI)
    - Clamp may only reduce size toward zero (Principle VI)
    - Kill switch blocks new orders, permits cancellations (Principle VI)
    """

    @abstractmethod
    def check(
        self,
        desired: DesiredPosition,
        current_state: PositionState,
        utc_now: datetime,
    ) -> tuple[RiskDecision, Optional[ApprovedOrder], str]:
        """
        Evaluate desired position and return risk decision.

        Args:
            desired: Strategy's desired position
            current_state: Current portfolio state
            utc_now: Current UTC time (for daily loss calculations)

        Returns:
            Tuple of (decision, approved_order_or_none, reason_code):
            - decision: RiskDecision.PASS, CLAMP, or VETO
            - approved_order: ApprovedOrder if PASS or CLAMP, None if VETO
            - reason_code: String describing the decision (e.g., "RISK_PASS",
              "RISK_CLAMP_MAX_POSITION", "RISK_VETO_DAILY_LOSS")

        Behavioral contract:
            - MUST be pure (no I/O, network, randomness, or clock reads in logic)
            - CLAMP only reduces size toward zero, never flips side (Principle VI)
            - VETO returns None for approved_order
            - Reason codes follow controlled vocabulary
        """
        pass

    @abstractmethod
    def get_kill_switch_state(self) -> bool:
        """Return True if kill switch is engaged."""
        pass

    @abstractmethod
    def set_kill_switch(self, engaged: bool) -> None:
        """Set kill switch state (True = engaged, blocks new orders)."""
        pass

    @abstractmethod
    def get_max_position_size(self) -> Decimal:
        """Return maximum position size limit."""
        pass

    @abstractmethod
    def get_max_daily_loss_pct(self) -> Decimal:
        """Return maximum daily loss as percentage of equity."""
        pass
