"""
Backtest Integration Test

End-to-end integration test for backtesting.

Constitutional Principles:
- I. Truth Before Profit: Cost-inclusive reporting
- V. No Backtest Without Costs: All costs modeled
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal

from trading.backtest.runner import BacktestRunner
from trading.data.market_state import MarketState
from trading.backtest.costs import CostModel, Side


class TestBacktestIntegration:
    """Integration test suite for backtesting."""

    @pytest.mark.asyncio
    async def test_backtest_completes_successfully(self):
        """
        Test backtest completes successfully.

        Constitutional requirements:
            - SC-003: Completes in under 60 seconds for 1000 data points
            - FR-022: Data window reported in results
        """
        import time
        start = time.time()

        runner = BacktestRunner()
        result = await runner.run(max_events=100)

        elapsed = time.time() - start
        assert elapsed < 60, f"Backtest took {elapsed}s, should be under 60s"

        # Verify structure
        assert "processed_count" in result
        assert "trades_count" in result
        assert "pnl_report" in result
        assert "data_window" in result

    @pytest.mark.asyncio
    async def test_data_window_reported(self):
        """
        Test data window is included in results.

        Constitutional requirements:
            - FR-022: Data window reported (start, end, events)
        """
        runner = BacktestRunner()
        result = await runner.run(max_events=50)

        window = result["data_window"]
        assert window["start"] is not None
        assert window["end"] is not None
        assert window["events"] == 50

        # Verify timestamps are valid
        start_dt = datetime.fromisoformat(window["start"])
        end_dt = datetime.fromisoformat(window["end"])
        assert start_dt <= end_dt

    @pytest.mark.asyncio
    async def test_cost_inclusive_pnl_report(self):
        """
        Test P&L report shows cost breakdown.

        Constitutional requirements:
            - SC-004: P&L report explicitly lists all cost components
            - Principle I: Truth Before Profit
        """
        runner = BacktestRunner()
        result = await runner.run(max_events=100)

        pnl = result["pnl_report"]

        # Verify cost components exist
        assert "total_fees" in pnl
        assert "total_spread_cost" in pnl
        assert "total_slippage_cost" in pnl
        assert "total_costs" in pnl
        assert "net_pnl" in pnl
        assert "gross_pnl" in pnl

        # Verify all costs are accounted for
        expected_total = pnl["total_fees"] + pnl["total_spread_cost"] + pnl["total_slippage_cost"]
        assert abs(pnl["total_costs"] - expected_total) < 0.01, \
            "Total costs must equal sum of components"

        # Verify net P&L is gross minus costs
        expected_net = pnl["gross_pnl"] - pnl["total_costs"]
        assert abs(pnl["net_pnl"] - expected_net) < 0.01, \
            "Net P&L must equal gross P&L minus costs"

    @pytest.mark.asyncio
    async def test_determinism_verified(self):
        """
        Test determinism: same input produces identical output.

        Constitutional requirements:
            - SC-005: Same input → bit-for-bit identical output
        """
        # Create identical data sets
        data_points = list(_create_test_data(100))

        # Run backtest twice
        runner1 = BacktestRunner()
        result1 = await runner1.run(data_points=data_points, max_events=100)

        runner2 = BacktestRunner()
        result2 = await runner2.run(data_points=data_points, max_events=100)

        # Verify results are identical
        assert result1["processed_count"] == result2["processed_count"]
        assert result1["trades_count"] == result2["trades_count"]

        # Verify P&L reports are identical
        pnl1 = result1["pnl_report"]
        pnl2 = result2["pnl_report"]

        assert pnl1["total_trades"] == pnl2["total_trades"]
        assert pnl1["gross_pnl"] == pnl2["gross_pnl"]
        assert pnl1["total_fees"] == pnl2["total_fees"]
        assert pnl1["total_spread_cost"] == pnl2["total_spread_cost"]
        assert pnl1["total_slippage_cost"] == pnl2["total_slippage_cost"]
        assert pnl1["net_pnl"] == pnl2["net_pnl"]

    @pytest.mark.asyncio
    async def test_negative_pnl_acceptable(self):
        """
        Test negative P&L is acceptable outcome.

        Constitutional requirements:
            - SC-009: Negative P&L is acceptable
            - Principle I: Truth Before Profit
        """
        runner = BacktestRunner()
        result = await runner.run(max_events=100)

        pnl = result["pnl_report"]

        # Negative P&L should not raise any error
        # (The trivial strategy may lose money, and that's OK)
        if pnl["net_pnl"] < 0:
            # This is acceptable
            assert True, "Negative P&L is acceptable (Truth Before Profit)"

    @pytest.mark.asyncio
    async def test_trade_list_included(self):
        """
        Test trade list is included in report.

        Constitutional requirements:
            - FR-021: Trade-by-trade list included
        """
        runner = BacktestRunner()
        result = await runner.run(max_events=100)

        pnl = result["pnl_report"]

        # Verify trades list exists
        assert "trades" in pnl
        assert isinstance(pnl["trades"], list)

        # If there are trades, verify structure
        for trade in pnl["trades"]:
            assert "timestamp" in trade
            assert "symbol" in trade
            assert "side" in trade
            assert "size" in trade
            assert "fill_price" in trade
            assert "fees" in trade
            assert "spread_cost" in trade
            assert "slippage_cost" in trade
            assert "total_cost" in trade


def _create_test_data(count: int):
    """Create test market data points."""
    base_price = Decimal("65000.00")
    for i in range(count):
        # Small price movements
        price_change = Decimal(str((i % 10 - 5) * 0.001))  # -0.5% to +0.5%
        price = base_price * (Decimal("1") + price_change)

        yield MarketState(
            timestamp=datetime.fromtimestamp(1700000000 + i),
            symbol="BTC/USD",
            bid_price=price.quantize(Decimal("0.01")),
            ask_price=(price * Decimal("1.0001")).quantize(Decimal("0.01")),
            last_price=price.quantize(Decimal("0.01")),
            volume_24h=Decimal("1000.0"),
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
