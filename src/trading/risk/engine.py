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
    # WO-049 §3.4 (D49): a NEW code was genuinely needed. The existing veto codes name a kill
    # switch, a daily-loss breach and malformed input — none of them describes "the aggregate
    # position is already at its cap". REASON_CLAMP_MAX_POSITION is reused unchanged for the clamp
    # (it fits exactly); only the zero-headroom VETO had no home. Prefix-free against the union.
    REASON_VETO_MAX_POSITION = "RISK_VETO_MAX_POSITION"

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

        # ── WO-049 §3 (D49): `max_position_btc` IS THE AGGREGATE POSITION CAP ─────────────────
        #
        # D49, verbatim: "A limit that bounds each order but not the position is not a position
        # limit; it's a rate limiter wearing one's name."
        #
        # THE DEFECT THIS REPLACES: this was `approved_size = min(desired.quantity,
        # self._max_position_btc)` — a per-ORDER clamp that never read `current_state`. Every
        # 0.1 BTC order passed a 1.0 BTC "limit" unchanged, so position accumulated without bound.
        # WO-048's corpus run placed 738,510 orders in a single segment and nothing objected. The
        # defect was present since the engine was built and green through every prior run; only a
        # strategy firing on 90.9% of 3.85 M real frames made it visible.
        #
        # AN ORDER IS NOW EVALUATED AGAINST THE POSITION IT WOULD PRODUCE, not against its own size.
        #
        # SIGN CONVENTION (code wins, §0.1). `DesiredPosition`'s docstring claims "quantity < 0 if
        # side == Side.SELL", but the validation above VETOES any quantity <= 0, both strategies
        # emit a positive magnitude for both sides, and every position-update site derives direction
        # from `side` (`+size if BUY else -size`). So quantity is an UNSIGNED MAGNITUDE and `side`
        # carries direction. The stale docstring invariant is reported, not obeyed.
        #
        # The cap is a MAGNITUDE, so the permitted band is [-cap, +cap]: a 1.5 BTC short violates a
        # 1.0 BTC cap exactly as a 1.5 BTC long does.
        current = current_state.current_quantity
        cap = self._max_position_btc
        direction = Decimal("1") if desired.side.value == "BUY" else Decimal("-1")

        # INCREASING vs REDUCING exposure. `direction * current >= 0` is true when the order pushes
        # further from zero (same sign), and when the position is flat (any order adds exposure).
        increasing = (direction * current) >= 0

        if increasing:
            # Headroom is what remains before |position| reaches the cap.
            headroom = cap - abs(current)
            if headroom <= 0:
                # ZERO HEADROOM -> VETO. At or beyond the cap there is no room to add exposure.
                # This branch can NEVER block a reducing order: it is inside `if increasing`.
                return RiskDecision.VETO, None, self.REASON_VETO_MAX_POSITION
            allowed = min(desired.quantity, headroom)
        else:
            # REDUCING — THE DANGEROUS HALF (§4.2). A reducing order must pass even at or BEYOND
            # the cap. A position limit that traps you in a position is strictly more dangerous
            # than the accumulation bug it replaces: it would prevent the system from ever getting
            # flat. So the only bound here is the point at which the order would overshoot zero and
            # build a NEW position past the cap on the opposite side — `|current| + cap`. Reduction
            # itself is never restricted.
            allowed = min(desired.quantity, abs(current) + cap)

        # CLAMP-ONLY-REDUCES-TOWARD-ZERO (§3.3), guaranteed STRUCTURALLY rather than by inspection:
        #   - `allowed` is always `min(desired.quantity, ...)`, so it can never EXCEED the request;
        #   - `side` is passed through untouched, so a side can never flip;
        #   - shrinking a reducing order leaves it reducing (any positive magnitude in the opposite
        #     direction still moves toward zero), so a reducing order can never become increasing.
        if allowed < desired.quantity:
            approved_order = ApprovedOrder(
                timestamp=utc_now,
                symbol=desired.symbol,
                side=desired.side.value,
                size=allowed,
                price=Decimal("0"),  # Market order: venue determines fill price from MarketState
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
