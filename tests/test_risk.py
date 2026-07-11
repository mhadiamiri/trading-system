"""
Risk Engine Tests

Comprehensive tests for risk engine including clamp and kill switch.

Constitutional Principles:
- III. AI Proposes, Deterministic Code Disposes: No ML/AI imports
- VI. Risk Engine Is Sovereign: Clamp only reduces toward zero
"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal

from trading.risk.engine import DeterministicRiskEngine
from trading.risk.position_state import PositionState
from trading.data.desired_position import DesiredPosition, Side


class TestRiskEngine:
    """Test suite for DeterministicRiskEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        # Risk engine with small limit for clamp testing
        self.risk_engine = DeterministicRiskEngine(
            max_position_btc=Decimal("0.5"),  # Small limit to trigger clamp
            max_daily_loss_pct=Decimal("0.05"),
            account_equity_usd=Decimal("10000"),
        )

        # Current position state
        self.position_state = PositionState(
            symbol="BTC/USD",
            current_quantity=Decimal("0"),
            average_entry_price=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            daily_pnl=Decimal("0"),
        )

    def test_pass_when_within_limits(self):
        """Test order passes when within all limits."""
        desired = DesiredPosition(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            side=Side.BUY,
            quantity=Decimal("0.3"),  # Under 0.5 BTC limit
            feature_snapshot_hash="test_hash",
        )

        decision, approved_order, reason_code = self.risk_engine.check(
            desired, self.position_state, datetime.now(UTC)
        )

        assert decision.value == "PASS"
        assert approved_order is not None
        assert approved_order.size == Decimal("0.3")
        assert reason_code == "RISK_PASS"

    def test_clamp_reduces_size_toward_zero(self):
        """
        Test clamp reduces order size toward zero.

        Constitutional requirement (Principle VI):
        - Clamp MAY only reduce order size toward zero
        - SC-010: Clamp test uses small enough limit that clamp actually fires
        """
        # Request larger than max position
        desired = DesiredPosition(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            side=Side.BUY,
            quantity=Decimal("1.0"),  # Exceeds 0.5 BTC limit
            feature_snapshot_hash="test_hash",
        )

        decision, approved_order, reason_code = self.risk_engine.check(
            desired, self.position_state, datetime.now(UTC)
        )

        assert decision.value == "CLAMP"
        assert approved_order is not None
        assert approved_order.size == Decimal("0.5")  # Clamped to max
        assert approved_order.original_size == Decimal("1.0")
        assert reason_code == "RISK_CLAMP_MAX_POSITION"

    def test_clamp_does_not_increase_size(self):
        """
        Test clamp never increases size.

        Constitutional requirement (Principle VI):
        - Clamp MUST NOT increase size
        """
        desired = DesiredPosition(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            side=Side.BUY,
            quantity=Decimal("0.3"),
            feature_snapshot_hash="test_hash",
        )

        decision, approved_order, _ = self.risk_engine.check(
            desired, self.position_state, datetime.now(UTC)
        )

        # Size should never increase
        assert approved_order.size <= desired.quantity

    def test_veto_when_daily_loss_exceeded(self):
        """Test veto when daily loss limit exceeded."""
        # Create position state with daily loss exceeding limit (5% of $10000 = $500)
        loss_state = PositionState(
            symbol="BTC/USD",
            current_quantity=Decimal("0"),
            average_entry_price=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            daily_pnl=Decimal("-600"),  # Exceeds 5% limit
        )

        desired = DesiredPosition(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            side=Side.BUY,
            quantity=Decimal("0.1"),
            feature_snapshot_hash="test_hash",
        )

        decision, approved_order, reason_code = self.risk_engine.check(
            desired, loss_state, datetime.now(UTC)
        )

        assert decision.value == "VETO"
        assert approved_order is None
        assert reason_code == "RISK_VETO_DAILY_LOSS"

    def test_kill_switch_blocks_new_orders(self):
        """
        Test kill switch blocks new orders.

        Constitutional requirement (Principle VI):
        - Kill switch MUST block all new orders
        """
        # Engage kill switch
        self.risk_engine.set_kill_switch(True)

        desired = DesiredPosition(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            side=Side.BUY,
            quantity=Decimal("0.1"),
            feature_snapshot_hash="test_hash",
        )

        decision, approved_order, reason_code = self.risk_engine.check(
            desired, self.position_state, datetime.now(UTC)
        )

        assert decision.value == "VETO"
        assert approved_order is None
        assert reason_code == "RISK_VETO_KILL_SWITCH"

    def test_veto_for_invalid_input(self):
        """Test veto for invalid input (zero or negative quantity)."""
        desired = DesiredPosition(
            timestamp=datetime.now(UTC),
            symbol="BTC/USD",
            side=Side.BUY,
            quantity=Decimal("0"),  # Invalid
            feature_snapshot_hash="test_hash",
        )

        decision, approved_order, reason_code = self.risk_engine.check(
            desired, self.position_state, datetime.now(UTC)
        )

        assert decision.value == "VETO"
        assert approved_order is None
        assert reason_code == "RISK_VETO_INVALID_INPUT"

    def test_get_kill_switch_state(self):
        """Test get_kill_switch_state returns correct state."""
        assert self.risk_engine.get_kill_switch_state() is False

        self.risk_engine.set_kill_switch(True)
        assert self.risk_engine.get_kill_switch_state() is True

    def test_get_max_position_size(self):
        """Test get_max_position_size returns configured limit."""
        assert self.risk_engine.get_max_position_size() == Decimal("0.5")

    def test_get_max_daily_loss_pct(self):
        """Test get_max_daily_loss_pct returns configured limit."""
        assert self.risk_engine.get_max_daily_loss_pct() == Decimal("0.05")


class TestImportRestrictions:
    """Test that risk layer has no ML/AI imports."""

    def test_no_ml_imports_in_risk_layer(self):
        """
        Test risk layer has no ML/AI imports.

        Constitutional requirement (Principle III):
        - Risk layer MUST NOT depend on any ML/AI libraries
        """
        import trading.risk.engine
        import trading.risk.interface
        import trading.risk.limits

        # Check that torch, tensorflow, sklearn are not imported
        import sys
        ml_modules = ["torch", "tensorflow", "sklearn", "transformers"]

        for module in ml_modules:
            assert module not in sys.modules, f"Risk layer imported ML module: {module}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
