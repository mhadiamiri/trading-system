"""
Deterministic Risk Engine

Pure deterministic risk engine with no AI/ML dependencies.

Constitutional Principles:
- III. AI Proposes, Deterministic Code Disposes: No ML/AI imports
- VI. Risk Engine Is Sovereign: Final authority over all orders
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from trading.risk.interface import RiskEngine, RiskDecision
from trading.data.desired_position import DesiredPosition, Side
from trading.execution.approved_order import ApprovedOrder
from trading.risk.position_state import PositionState


class DeterministicRiskEngine(RiskEngine):
    """
    Pure deterministic risk engine.

    Hard limits enforced:
    - Maximum position size (default 1 BTC)
    - Maximum daily loss (default 5% of equity)
    - Kill switch (blocks all new orders when engaged)

    Constitutional requirements:
    - No ML/AI imports or dependencies (Principle III)
    - Clamp only reduces size toward zero (Principle VI)
    - Kill switch permits cancellations (Principle VI)
    """

    # Reason codes
    REASON_PASS = "RISK_PASS"
    REASON_CLAMP_MAX_POSITION = "RISK_CLAMP_MAX_POSITION"
    REASON_VETO_KILL_SWITCH = "RISK_VETO_KILL_SWITCH"
    REASON_VETO_DAILY_LOSS = "RISK_VETO_DAILY_LOSS"
    REASON_VETO_INVALID_INPUT = "RISK_VETO_INVALID_INPUT"
    REASON_VETO_INSUFFICIENT_BALANCE = "RISK_VETO_INSUFFICIENT_BALANCE"

    def __init__(
        self,
        max_position_btc: Decimal = Decimal("1.0"),
        max_daily_loss_pct: Decimal = Decimal("0.05"),
        account_equity_usd: Decimal = Decimal("10000"),
    ) -> None:
        """
        Initialize risk engine with limits.

        Args:
            max_position_btc: Maximum position size in BTC (default 1.0)
            max_daily_loss_pct: Maximum daily loss as % of equity (default 0.05 = 5%)
            account_equity_usd: Account equity in USD for daily loss calc
        """
        self._max_position_btc = max_position_btc
        self._max_daily_loss_pct = max_daily_loss_pct
        self._account_equity_usd = account_equity_usd
        self._kill_switch_engaged = False

    def check(
        self,
        desired: DesiredPosition,
        current_state: PositionState,
        utc_now: datetime,
    ) -> tuple[RiskDecision, Optional[ApprovedOrder], str]:
        """
        Evaluate desired position and return risk decision.

        This is a PURE function - no I/O, network, randomness, or clock reads.

        Constitutional requirements:
        - Clamp only reduces size toward zero (Principle VI)
        - Kill switch blocks new orders (Principle VI)
        """
        # Check kill switch first
        if self._kill_switch_engaged:
            return RiskDecision.VETO, None, self.REASON_VETO_KILL_SWITCH

        # Validate inputs
        if desired.quantity <= 0:
            return RiskDecision.VETO, None, self.REASON_VETO_INVALID_INPUT

        # Check daily loss limit
        if current_state.daily_pnl <= -(self._account_equity_usd * self._max_daily_loss_pct):
            return RiskDecision.VETO, None, self.REASON_VETO_DAILY_LOSS

        # Check position size limit
        approved_size = min(desired.quantity, self._max_position_btc)

        if approved_size < desired.quantity:
            # Clamp toward zero
            approved_order = ApprovedOrder(
                timestamp=utc_now,
                symbol=desired.symbol,
                side=desired.side.value,
                size=approved_size,
                price=Decimal("0"),  # Will be filled by execution layer
                reason_code=self.REASON_CLAMP_MAX_POSITION,
                original_size=desired.quantity,
            )
            return RiskDecision.CLAMP, approved_order, self.REASON_CLAMP_MAX_POSITION

        # Pass unchanged
        approved_order = ApprovedOrder(
            timestamp=utc_now,
            symbol=desired.symbol,
            side=desired.side.value,
            size=desired.quantity,
            price=Decimal("0"),  # Will be filled by execution layer
            reason_code=self.REASON_PASS,
            original_size=desired.quantity,
        )
        return RiskDecision.PASS, approved_order, self.REASON_PASS

    def get_kill_switch_state(self) -> bool:
        """Return True if kill switch is engaged."""
        return self._kill_switch_engaged

    def set_kill_switch(self, engaged: bool) -> None:
        """Set kill switch state (True = engaged, blocks new orders)."""
        self._kill_switch_engaged = engaged

    def get_max_position_size(self) -> Decimal:
        """Return maximum position size limit."""
        return self._max_position_btc

    def get_max_daily_loss_pct(self) -> Decimal:
        """Return maximum daily loss as percentage of equity."""
        return self._max_daily_loss_pct
