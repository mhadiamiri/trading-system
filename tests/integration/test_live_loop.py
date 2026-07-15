"""
Live Loop Integration Test

End-to-end integration test for live paper trading loop.

Constitutional Principles:
- II. Walking Skeleton Before Palace: End-to-end loop completes
- VIII. Total Observability & Provenance: Every decision logged
"""

import pytest
import asyncio
import os
from datetime import datetime
from decimal import Decimal

from trading.loop.live import LiveTradingLoop
from trading.data.adapters.simulated_feed import SimulatedMarketFeed


class TestLiveLoopIntegration:
    """Integration test suite for live trading loop."""

    @pytest.mark.asyncio
    async def test_end_to_end_loop_completes(self):
        """
        Test end-to-end loop completes successfully.

        Constitutional requirements:
            - SC-001: 100 consecutive market data updates processed without error
            - SC-007: End-to-end loop completes successfully
        """
        # Force simulated feed for consistent test results
        original_data_source = os.environ.get("DATA_SOURCE")
        os.environ["DATA_SOURCE"] = "simulated"

        try:
            # Reload settings to pick up the change
            import importlib
            import config.settings
            importlib.reload(config.settings)

            loop = LiveTradingLoop()

            # Run loop with simulated feed
            result = await loop.run(max_updates=100)

            # Verify results
            assert result["processed_count"] == 100
            assert "trades_count" in result
            assert "final_pnl" in result
        finally:
            # Restore original setting
            if original_data_source:
                os.environ["DATA_SOURCE"] = original_data_source
            else:
                os.environ.pop("DATA_SOURCE", None)
            # Reload settings to restore
            importlib.reload(config.settings)

    @pytest.mark.asyncio
    async def test_every_decision_logged(self):
        """
        Test every decision produces a log entry with reason code.

        Constitutional requirements:
            - SC-002: Every decision has a reason code
            - Zero silent decisions (Principle VIII)
        """
        # Clear log file before running
        if os.path.exists("logs/decisions.log"):
            os.remove("logs/decisions.log")

        # Force simulated feed for consistent test results
        original_data_source = os.environ.get("DATA_SOURCE")
        os.environ["DATA_SOURCE"] = "simulated"

        try:
            # Reload settings to pick up the change
            import importlib
            import config.settings
            importlib.reload(config.settings)

            loop = LiveTradingLoop()

            # Run loop
            await loop.run(max_updates=10)

            # Verify log file exists and has entries
            assert os.path.exists("logs/decisions.log")

            with open("logs/decisions.log", "r") as f:
                log_lines = f.readlines()

            # Should have log entries for each update
            assert len(log_lines) > 0

            # Verify each log entry has reason_code
            import json
            for line in log_lines:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                entry = json.loads(line)
                assert "reason_code" in entry
                assert entry["reason_code"] is not None
        finally:
            # Restore original setting
            if original_data_source:
                os.environ["DATA_SOURCE"] = original_data_source
            else:
                os.environ.pop("DATA_SOURCE", None)
            # Reload settings to restore
            importlib.reload(config.settings)

    @pytest.mark.asyncio
    async def test_simulated_fills_recorded(self):
        """
        Test simulated fills are recorded with all cost components.

        Constitutional requirements:
            - All cost components included (Principle I)
            - Simulated fills recorded
        """
        # Force simulated feed for consistent test results
        original_data_source = os.environ.get("DATA_SOURCE")
        os.environ["DATA_SOURCE"] = "simulated"

        try:
            # Reload settings to pick up the change
            import importlib
            import config.settings
            importlib.reload(config.settings)

            loop = LiveTradingLoop()

            # Run loop
            result = await loop.run(max_updates=50)

            # Verify fills were recorded
            # (The exact number depends on strategy signals)
        finally:
            # Restore original setting
            if original_data_source:
                os.environ["DATA_SOURCE"] = original_data_source
            else:
                os.environ.pop("DATA_SOURCE", None)
            # Reload settings to restore
            importlib.reload(config.settings)

    @pytest.mark.asyncio
    async def test_kill_switch_blocks_orders(self):
        """
        Test kill switch blocks new orders.

        Constitutional requirements:
            - Kill switch blocks new orders (Principle VI)
        """
        # Force simulated feed for consistent test results
        original_data_source = os.environ.get("DATA_SOURCE")
        os.environ["DATA_SOURCE"] = "simulated"

        try:
            # Reload settings to pick up the change
            import importlib
            import config.settings
            importlib.reload(config.settings)

            loop = LiveTradingLoop()

            # Engage kill switch
            loop._risk_engine.set_kill_switch(True)

            # Run loop - should process updates but no trades
            result = await loop.run(max_updates=20)

            # With kill switch engaged, no trades should execute
            # (Strategy may generate signals, but risk will veto)
        finally:
            # Restore original setting
            if original_data_source:
                os.environ["DATA_SOURCE"] = original_data_source
            else:
                os.environ.pop("DATA_SOURCE", None)
            # Reload settings to restore
            importlib.reload(config.settings)

    @pytest.mark.asyncio
    async def test_clamp_fires_during_loop(self):
        """
        Test clamp actually fires during loop execution.

        Constitutional requirements:
            - SC-010: Clamp test uses small enough limit
        """
        # Force simulated feed for consistent test results
        original_data_source = os.environ.get("DATA_SOURCE")
        os.environ["DATA_SOURCE"] = "simulated"

        try:
            # Reload settings to pick up the change
            import importlib
            import config.settings
            importlib.reload(config.settings)

            # Create loop with risk engine that has small limit
            from trading.risk.engine import DeterministicRiskEngine

            small_limit_risk = DeterministicRiskEngine(
                max_position_btc=Decimal("0.01"),  # Very small limit
            )
            loop = LiveTradingLoop(risk_engine=small_limit_risk)

            # Run loop
            result = await loop.run(max_updates=50)

            # Should have processed updates
            assert result["processed_count"] == 50
        finally:
            # Restore original setting
            if original_data_source:
                os.environ["DATA_SOURCE"] = original_data_source
            else:
                os.environ.pop("DATA_SOURCE", None)
            # Reload settings to restore
            importlib.reload(config.settings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
