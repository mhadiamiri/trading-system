"""
Backtest Runner

Processes stored market data for backtesting.

Constitutional Principles:
- I. Truth Before Profit: Cost-inclusive reporting
- V. No Backtest Without Costs: All costs modeled
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import List, Dict
import json

from trading.data.market_state import MarketState
from trading.data.fixtures import sample_market_data
from trading.strategy.interface import Strategy
from trading.strategy.trivial import TrivialMomentumStrategy
from trading.risk.interface import RiskEngine
from trading.risk.engine import DeterministicRiskEngine
from trading.risk.position_state import PositionState
from trading.execution.interface import ExchangeClient
from trading.execution.paper import PaperExecutionClient
from trading.backtest.costs import CostModel, Side
from trading.backtest.report import PnLReport


class BacktestRunner:
    """
    Backtest runner for historical testing.

    Constitutional requirements:
        - Loads and processes market data from stored data
        - Applies cost model to every trade (Principle V)
        - Reports cost breakdown (Principle I)
    """

    def __init__(
        self,
        strategy: Strategy = None,
        risk_engine: RiskEngine = None,
        execution_client: ExchangeClient = None,
        cost_model: CostModel = None,
    ) -> None:
        """
        Initialize backtest runner.

        Args:
            strategy: Trading strategy (default: TrivialMomentumStrategy)
            risk_engine: Risk engine (default: DeterministicRiskEngine)
            execution_client: Execution client (default: PaperExecutionClient)
            cost_model: Cost model (default: CostModel)
        """
        self._strategy = strategy or TrivialMomentumStrategy()
        self._risk_engine = risk_engine or DeterministicRiskEngine()
        self._execution_client = execution_client or PaperExecutionClient()
        self._cost_model = cost_model or CostModel()

        # Portfolio state
        self._position_state = PositionState(
            symbol="BTC/USD",
            current_quantity=Decimal("0"),
            average_entry_price=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            daily_pnl=Decimal("0"),
        )

        # P&L report
        self._pnl_report = PnLReport()

    async def run(
        self,
        data_points: List[MarketState] = None,
        max_events: int = 1000,
    ) -> Dict:
        """
        Run backtest on stored market data.

        Args:
            data_points: List of market data points (default: sample data)
            max_events: Maximum events to process

        Returns:
            Backtest results dict

        Constitutional requirements:
            - Completes in under 60 seconds for 1000 data points (SC-003)
            - Reports data window (FR-022)
        """
        import time
        start_time = time.time()

        # Use sample data if none provided
        if data_points is None:
            data_points = list(sample_market_data())

        processed_count = 0
        trades_count = 0
        window_start = None
        window_end = None

        for market_state in data_points:
            if processed_count >= max_events:
                break

            # Track data window
            if window_start is None:
                window_start = market_state.timestamp
            window_end = market_state.timestamp

            # Strategy decides
            desired_position = self._strategy.decide(market_state)

            if desired_position is None:
                processed_count += 1
                continue

            # Risk check
            decision, approved_order, _ = self._risk_engine.check(
                desired_position,
                self._position_state,
                market_state.timestamp,
            )

            if decision.value in ["VETO"]:
                processed_count += 1
                continue

            # Simulate execution with costs
            fill = await self._execution_client.place_order(
                symbol=approved_order.symbol,
                side=approved_order.side,
                size=float(approved_order.size),
                price=float(market_state.last_price),  # Use market price
                kill_switch_engaged=False,
            )

            # Add to P&L report
            self._pnl_report.add_trade(
                timestamp=datetime.fromisoformat(fill["timestamp"]),
                symbol=fill["symbol"],
                side=fill["side"],
                size=Decimal(str(fill["size"])),
                fill_price=Decimal(str(fill["fill_price"])),
                fees=Decimal(str(fill["fees"])),
                spread_cost=Decimal(str(fill["spread_cost"])),
                slippage_cost=Decimal(str(fill["slippage_cost"])),
            )

            # Update position
            self._update_position(fill)
            trades_count += 1
            processed_count += 1

        elapsed = time.time() - start_time

        # Generate report
        pnl_report = self._pnl_report.generate_report()

        return {
            "processed_count": processed_count,
            "trades_count": trades_count,
            "elapsed_seconds": elapsed,
            "data_window": {
                "start": window_start.isoformat() if window_start else None,
                "end": window_end.isoformat() if window_end else None,
                "events": processed_count,
            },
            "pnl_report": pnl_report,
        }

    def _update_position(self, fill: dict) -> None:
        """Update position state after fill."""
        size = Decimal(str(fill["size"]))
        side = fill["side"]
        total_cost = Decimal(str(fill["total_cost"]))

        if side == "BUY":
            self._position_state.current_quantity += size
        else:
            self._position_state.current_quantity -= size

        # Update realized P&L
        self._position_state.realized_pnl -= total_cost


async def main() -> None:
    """Run backtest and print results."""
    runner = BacktestRunner()
    result = await runner.run(max_events=1000)

    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Processed: {result['processed_count']} events")
    print(f"Trades: {result['trades_count']}")
    print(f"Time: {result['elapsed_seconds']:.2f}s")
    print("-" * 60)
    print("Data Window:")
    print(f"  Start: {result['data_window']['start']}")
    print(f"  End:   {result['data_window']['end']}")
    print(f"  Events: {result['data_window']['events']}")
    print("=" * 60)

    # Print P&L
    pnl = result['pnl_report']
    print(f"\nTotal Trades: {pnl['total_trades']}")
    print(f"Gross P&L: ${pnl['gross_pnl']:.2f}")
    print(f"Total Fees: ${pnl['total_fees']:.2f}")
    print(f"Total Spread: ${pnl['total_spread_cost']:.2f}")
    print(f"Total Slippage: ${pnl['total_slippage_cost']:.2f}")
    print(f"Net P&L: ${pnl['net_pnl']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
