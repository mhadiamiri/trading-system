"""
RiskEngine Interface Contract

This module defines the Risk Engine interface and decision types.

Constitutional Principles:
- III. AI Proposes, Deterministic Code Disposes: Risk engine has final authority
- VI. The Risk Engine Is Sovereign: Returns pass/clamp/veto with hard limits
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


class Layer(Enum):
    """System layer for decision records."""
    STRATEGY = "STRATEGY"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    BACKTEST = "BACKTEST"


class RiskDecision(Enum):
    """Risk engine decision types."""
    PASS = "PASS"      # Order approved unchanged
    CLAMP = "CLAMP"    # Order reduced toward zero
    VETO = "VETO"      # Order rejected entirely


@dataclass(frozen=True)
class DesiredPosition:
    """Strategy's desired position (simplified)."""
    timestamp: datetime
    symbol: str
    side: str  # "BUY", "SELL", "HOLD"
    quantity: Decimal
    feature_snapshot_hash: str  # Hash of MarketState this decision acted on


@dataclass(frozen=True)
class ApprovedOrder:
    """Risk-approved order."""
    timestamp: datetime
    symbol: str
    side: str
    size: Decimal
    price: Decimal
    reason_code: str
    original_size: Decimal


@dataclass(frozen=True)
class PositionState:
    """Current portfolio state."""
    symbol: str
    current_quantity: Decimal
    average_entry_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    daily_pnl: Decimal


@dataclass(frozen=True)
class DecisionRecord:
    """
    Auditable decision record.

    Constitutional requirements:
    - Every decision logged with reason code (Principle VIII)
    - No secrets in logs (Principle IX)
    - Includes all required fields for provenance
    """
    timestamp: datetime
    layer: Layer
    event_type: str
    reason_code: str
    venue: str
    symbol: str
    side: Optional[str]
    size: Optional[Decimal]
    intended_price: Optional[Decimal]
    executed_price: Optional[Decimal]
    fees: Optional[Decimal]
    strategy_version: str
    feature_snapshot_hash: str


class RiskEngine:
    """
    Risk engine interface.

    The risk engine has FINAL AUTHORITY over every order (Principle III).

    Constitutional requirements:
    - MUST be pure and deterministic (no I/O, network, randomness, clock reads in logic)
    - MUST NOT depend on any ML/AI library (Principle III, enforced by import-linter)
    - MUST return exactly one of: PASS, CLAMP, or VETO (Principle VI)
    - CLAMP may only reduce size toward zero, never increase or flip side (Principle VI)
    - Hard limits: max position size, max daily loss, kill switch (Principle VI)

    Implementation notes:
    - Time must be passed in as a parameter (no clock reads inside logic)
    - All limits are configurable via environment
    - Reason codes follow LAYER_VERB_DETAIL format
    """

    def check(
        self,
        desired: DesiredPosition,
        current_state: PositionState,
        utc_now: datetime
    ) -> tuple[RiskDecision, Optional[ApprovedOrder], str]:
        """
        Evaluate desired position against risk limits.

        Args:
            desired: Strategy's desired position
            current_state: Current portfolio state
            utc_now: Current UTC time (passed in, no clock reads)

        Returns:
            Tuple of (decision, approved_order, reason_code):
            - decision: RiskDecision (PASS, CLAMP, or VETO)
            - approved_order: ApprovedOrder if PASS or CLAMP, None if VETO
            - reason_code: Controlled vocabulary code

        Behavioral contract:
        - MUST be deterministic (same inputs → same output)
            - No I/O, no network calls, no randomness, no clock reads
            - All state comes from parameters
        - MUST NOT import ML/AI libraries (enforced by import-linter in CI)
        - CLAMP outcome:
            - MAY only reduce size toward zero
            - MUST NOT increase size
            - MUST NOT flip side or direction
        - VETO outcomes:
            - Return None for approved_order
            - Include reason code explaining veto

        Hard limits (enforced):
        - Max position size (configurable, default 1 BTC)
        - Max daily loss (configurable as % of equity, default 5%)
        - Kill switch (blocks all new orders, permits cancellations)

        Reason codes (LAYER_VERB_DETAIL format):
        - RISK_PASS: Order passed unchanged
        - RISK_CLAMP_MAX_POSITION: Clamped due to position limit
        - RISK_VETO_DAILY_LOSS: Rejected due to daily loss limit
        - RISK_VETO_KILL_SWITCH: Rejected due to kill switch engaged
        - RISK_VETO_INVALID_INPUT: Rejected due to invalid input
        - RISK_VETO_INSUFFICIENT_BALANCE: Rejected due to insufficient balance

        Example:
            # Position limit exceeded
            if current_state.current_quantity + desired.quantity > MAX_POSITION:
                clamped_size = MAX_POSITION - current_state.current_quantity
                return (RiskDecision.CLAMP, ApprovedOrder(...), "RISK_CLAMP_MAX_POSITION")

            # Kill switch engaged
            if kill_switch_engaged:
                return (RiskDecision.VETO, None, "RISK_VETO_KILL_SWITCH")
        """
        raise NotImplementedError("RiskEngine must implement check()")

    def get_kill_switch_state(self) -> bool:
        """
        Get current kill switch state.

        Returns:
            True if kill switch is engaged (blocking new orders)

        Behavioral contract:
        - When True: block all new orders, still permit cancellations (Principle VI)
        """
        raise NotImplementedError("RiskEngine must implement get_kill_switch_state()")

    def set_kill_switch(self, engaged: bool) -> None:
        """
        Set kill switch state.

        Args:
            engaged: True to engage (block new orders), False to disengage

        Behavioral contract:
        - When engaged: block all new orders, still permit cancellations (Principle VI)
        - This is the emergency stop for the trading system
        """
        raise NotImplementedError("RiskEngine must implement set_kill_switch()")

    def get_max_position_size(self) -> Decimal:
        """
        Get maximum position size limit.

        Returns:
            Maximum position size in base currency (e.g., BTC)

        Behavioral contract:
        - Configurable via environment
        - Default: 1 BTC
        """
        raise NotImplementedError("RiskEngine must implement get_max_position_size()")

    def get_max_daily_loss_pct(self) -> Decimal:
        """
        Get maximum daily loss limit as percentage of equity.

        Returns:
            Maximum daily loss as percentage (e.g., 0.05 for 5%)

        Behavioral contract:
        - Configurable via environment
        - Default: 5% (0.05)
        - Scales correctly regardless of account equity size
        """
        raise NotImplementedError("RiskEngine must implement get_max_daily_loss_pct()")
