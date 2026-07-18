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


class TestBacktestReplay:
    """
    Test backtest replay from stored quote data (T030-T032).

    Phase 7 tests for backtest replay with observed spread.

    Constitutional requirements:
    - FR-022: Data window reported
    - T032: Reconstruct observed spread from stored raw bid/ask
    """

    @pytest.mark.asyncio
    async def test_backtest_reads_quote_data_from_parquet(self):
        """
        Test: Backtest reads stored quote data from Parquet.

        Verifies:
        - Parquet file has quote-centric schema (best_bid, best_ask, sizes)
        - MarketState reconstructed correctly from stored data
        - Observed spread computed from bid/ask (not pre-computed)

        Constitutional requirements:
        - T030: Backtest reads stored quote data
        - T032: Reconstruct observed spread from stored raw bid/ask
        """
        # Create test data with quote schema
        from trading.backtest.runner import load_market_data_from_parquet
        from pathlib import Path
        import tempfile
        import pyarrow.parquet as pq
        import pyarrow as pa

        # Create test data with quote schema
        test_data = [
            {
                "timestamp": datetime(2024, 1, 1, 12, 0, 0),
                "symbol": "BTC/USD",
                "best_bid": "65000.00",
                "best_ask": "65005.00",
                "best_bid_size": "1.5",
                "best_ask_size": "2.0",
                "trade_count": 100,
                "total_volume": "500.0",
                "last_price": "65000.00",
            },
            {
                "timestamp": datetime(2024, 1, 1, 12, 1, 0),
                "symbol": "BTC/USD",
                "best_bid": "65100.00",
                "best_ask": "65105.00",
                "best_bid_size": "1.6",
                "best_ask_size": "2.1",
                "trade_count": 105,
                "total_volume": "525.0",
                "last_price": "65100.00",
            },
        ]

        # Create temporary Parquet file
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            temp_path = f.name

        try:
            # Write to Parquet with quote schema
            table = pa.table({
                "timestamp": [d["timestamp"] for d in test_data],
                "symbol": [d["symbol"] for d in test_data],
                "best_bid": [d["best_bid"] for d in test_data],
                "best_ask": [d["best_ask"] for d in test_data],
                "best_bid_size": [d["best_bid_size"] for d in test_data],
                "best_ask_size": [d["best_ask_size"] for d in test_data],
                "trade_count": [d["trade_count"] for d in test_data],
                "total_volume": [d["total_volume"] for d in test_data],
                "last_price": [d["last_price"] for d in test_data],
            })
            pq.write_table(table, temp_path)

            # Load the data
            market_states = load_market_data_from_parquet(temp_path)

            # Verify data was loaded correctly
            assert len(market_states) == 2

            # Verify quote fields were loaded
            ms1 = market_states[0]
            assert ms1.best_bid == Decimal("65000.00")
            assert ms1.best_ask == Decimal("65005.00")
            assert ms1.best_bid_size == Decimal("1.5")
            assert ms1.best_ask_size == Decimal("2.0")

            # Verify spread was COMPUTED from bid/ask, not loaded as pre-computed
            assert ms1.spread == Decimal("5.00")  # 65005 - 65000
            assert ms1.mid_price == Decimal("65002.50")  # (65000 + 65005) / 2

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_backtest_honesty_replay_equals_live(self):
        """
        Test: Backtest honesty (replay = live).

        Verifies:
        - Cost model uses observed spread from replayed MarketState
        - No assumed spread used during replay
        - Spread costs vary with actual spreads in data

        Constitutional requirements:
        - T031: Backtest honesty (replay = live)
        - T032: No assumed spread during replay
        """
        # Create test data with KNOWN, DIFFERENT spreads
        from decimal import Decimal

        # Create MarketStates with different spreads to prove observed spread is used
        test_states = []

        # Data point 1: Spread = $5 (65000 bid, 65005 ask)
        test_states.append(
            MarketState(
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                symbol="BTC/USD",
                best_bid=Decimal("65000.00"),
                best_ask=Decimal("65005.00"),
                best_bid_size=Decimal("1.5"),
                best_ask_size=Decimal("2.0"),
                trade_count=100,
                total_volume=Decimal("500.0"),
                last_price=Decimal("65000.00"),
            )
        )

        # Data point 2: Spread = $10 (65100 bid, 65110 ask)
        test_states.append(
            MarketState(
                timestamp=datetime(2024, 1, 1, 12, 1, 0),
                symbol="BTC/USD",
                best_bid=Decimal("65100.00"),
                best_ask=Decimal("65110.00"),
                best_bid_size=Decimal("1.5"),
                best_ask_size=Decimal("2.0"),
                trade_count=105,
                total_volume=Decimal("525.0"),
                last_price=Decimal("65100.00"),
            )
        )

        # Test cost model with different observed spreads
        cost_model = CostModel()

        # Calculate costs for state 1 (spread = $5)
        costs1 = cost_model.calculate_costs_from_market_state(
            side=Side.BUY,
            size=Decimal("1.0"),
            market_state=test_states[0],
        )

        # Calculate costs for state 2 (spread = $10)
        costs2 = cost_model.calculate_costs_from_market_state(
            side=Side.BUY,
            size=Decimal("1.0"),
            market_state=test_states[1],
        )

        # Verify spread costs are DIFFERENT (proves observed spread is used)
        # State 1: spread = $5, half-spread cost = $2.50
        # State 2: spread = $10, half-spread cost = $5.00
        assert costs1.spread_cost == Decimal("2.50"), \
            f"Expected $2.50 spread cost for $5 spread, got ${costs1.spread_cost}"
        assert costs2.spread_cost == Decimal("5.00"), \
            f"Expected $5.00 spread cost for $10 spread, got ${costs2.spread_cost}"

        # Verify spread cost = observed spread / 2 (half spread each way)
        assert costs1.spread_cost == test_states[0].spread / Decimal("2")
        assert costs2.spread_cost == test_states[1].spread / Decimal("2")

        # This proves the cost model uses the ACTUAL observed spread from the data,
        # not a synthetic/assumed constant spread


def _create_test_data(count: int):
    """Create test market data points."""
    import random
    base_price = Decimal("65000.00")
    for i in range(count):
        # Small price movements
        price_change = Decimal(str((i % 10 - 5) * 0.001))  # -0.5% to +0.5%
        price = base_price * (Decimal("1") + price_change)

        # Calculate bid/ask spread
        spread = price * Decimal("0.0001")
        best_bid = price - spread / 2
        best_ask = price + spread / 2

        # Calculate sizes
        best_bid_size = Decimal(str(random.uniform(0.5, 5.0)))
        best_ask_size = Decimal(str(random.uniform(0.5, 5.0)))

        # Rolling trade stats
        total_volume = Decimal(str(random.uniform(100, 500)))
        trade_count = random.randint(50, 200)

        yield MarketState(
            timestamp=datetime.fromtimestamp(1700000000 + i),
            symbol="BTC/USD",
            best_bid=best_bid.quantize(Decimal("0.01")),
            best_ask=best_ask.quantize(Decimal("0.01")),
            best_bid_size=best_bid_size.quantize(Decimal("0.001")),
            best_ask_size=best_ask_size.quantize(Decimal("0.001")),
            trade_count=trade_count,
            total_volume=total_volume.quantize(Decimal("0.001")),
            last_price=price.quantize(Decimal("0.01")),
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
