"""
Live Trading Loop Orchestrator

Coordinates all components for end-to-end trading loop.

Constitutional Principles:
- II. Walking Skeleton Before Palace: Complete loop first
- VIII. Total Observability & Provenance: Every decision logged
"""

import asyncio
from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional

from trading.data.market_state import MarketState
from trading.data.desired_position import DesiredPosition
from trading.data.adapters.simulated_feed import SimulatedMarketFeed
from trading.strategy.interface import Strategy
from trading.strategy.trivial import TrivialMomentumStrategy
from trading.risk.interface import RiskEngine
from trading.risk.engine import DeterministicRiskEngine
from trading.risk.position_state import PositionState
from trading.execution.interface import ExchangeClient, KillSwitchEngagedError
from trading.execution.paper import PaperExecutionClient
from trading.logkit.decision import DecisionLogger, Layer, get_logger


class LiveTradingLoop:
    """
    Live trading loop orchestrator.

    Wires together all components:
    - Market data feed
    - Strategy
    - Risk engine
    - Execution client
    - Decision logger

    Constitutional requirements:
        - End-to-end loop must complete (Principle II)
        - Every decision logged (Principle VIII)
    """

    def __init__(
        self,
        feed: Optional[SimulatedMarketFeed] = None,
        strategy: Optional[Strategy] = None,
        risk_engine: Optional[RiskEngine] = None,
        execution_client: Optional[ExchangeClient] = None,
        decision_logger: Optional[DecisionLogger] = None,
    ) -> None:
        """
        Initialize live trading loop.

        Args:
            feed: Market data feed (default: SimulatedMarketFeed)
            strategy: Trading strategy (default: TrivialMomentumStrategy)
            risk_engine: Risk engine (default: DeterministicRiskEngine)
            execution_client: Execution client (default: PaperExecutionClient)
            decision_logger: Decision logger (default: get_logger())
        """
        self._feed = feed or SimulatedMarketFeed()
        self._strategy = strategy or TrivialMomentumStrategy()
        self._risk_engine = risk_engine or DeterministicRiskEngine()
        self._execution_client = execution_client or PaperExecutionClient()
        self._decision_logger = decision_logger or get_logger()

        # Portfolio state
        self._position_state = PositionState(
            symbol="BTC/USD",
            current_quantity=Decimal("0"),
            average_entry_price=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            daily_pnl=Decimal("0"),
        )

        self._running = False

    async def run(self, max_updates: int = 100) -> dict:
        """
        Run the live trading loop.

        Args:
            max_updates: Maximum number of market data updates to process

        Returns:
            Summary dict with processed count, trades count, final pnl

        Constitutional requirements:
            - End-to-end loop completes (Principle II)
            - Every decision logged (Principle VIII)
        """
        self._running = True
        processed_count = 0
        trades_count = 0

        print("Starting live trading loop...")
        print(f"Strategy: {self._strategy.version}")
        print(f"Feed: {self._feed.__class__.__name__}")
        print(f"Risk Engine: {self._risk_engine.__class__.__name__}")
        print(f"Execution: {self._execution_client.__class__.__name__}")
        print("-" * 50)

        async for market_state in self._feed.get_market_data():
            if not self._running or processed_count >= max_updates:
                break

            # Log market data received
            self._decision_logger.log_decision(
                layer=Layer.EXECUTION,
                event_type="MARKET_DATA_RECEIVED",
                reason_code="DATA_RECEIVED",
                venue="simulated",
                symbol=market_state.symbol,
            )

            # Strategy decides
            desired_position = self._strategy.decide(market_state)

            if desired_position is None:
                # No signal
                self._decision_logger.log_decision(
                    layer=Layer.STRATEGY,
                    event_type="NO_SIGNAL",
                    reason_code="STRAT_NO_SIGNAL",
                    venue="simulated",
                    symbol=market_state.symbol,
                    strategy_version=self._strategy.version,
                    feature_snapshot_hash=market_state.compute_snapshot_hash(),
                )
                processed_count += 1
                continue

            # Log strategy signal
            self._decision_logger.log_decision(
                layer=Layer.STRATEGY,
                event_type="SIGNAL_GENERATED",
                reason_code="STRAT_SIGNAL_BUY" if desired_position.side.value == "BUY" else "STRAT_SIGNAL_SELL",
                venue="simulated",
                symbol=desired_position.symbol,
                side=desired_position.side.value,
                size=desired_position.quantity,
                strategy_version=self._strategy.version,
                feature_snapshot_hash=desired_position.feature_snapshot_hash,
            )

            # Risk check
            decision, approved_order, reason_code = self._risk_engine.check(
                desired_position,
                self._position_state,
                datetime.now(UTC),
            )

            # Log risk decision
            self._decision_logger.log_decision(
                layer=Layer.RISK,
                event_type=decision.value,
                reason_code=reason_code,
                venue="simulated",
                symbol=desired_position.symbol,
                side=desired_position.side.value,
                size=approved_order.size if approved_order else None,
                strategy_version=self._strategy.version,
                feature_snapshot_hash=desired_position.feature_snapshot_hash,
            )

            if decision.value in ["VETO"]:
                # Order rejected
                processed_count += 1
                continue

            # Execute order
            try:
                kill_switch_engaged = self._risk_engine.get_kill_switch_state()
                fill = await self._execution_client.place_order(
                    symbol=approved_order.symbol,
                    side=approved_order.side,
                    size=float(approved_order.size),
                    price=float(approved_order.price),
                    kill_switch_engaged=kill_switch_engaged,
                )

                # Log execution
                self._decision_logger.log_decision(
                    layer=Layer.EXECUTION,
                    event_type="ORDER_FILLED",
                    reason_code="EXEC_ORDER_FILLED",
                    venue="simulated",
                    symbol=fill["symbol"],
                    side=fill["side"],
                    size=Decimal(str(fill["size"])),
                    intended_price=approved_order.price,
                    executed_price=Decimal(str(fill["fill_price"])),
                    fees=Decimal(str(fill["fees"])),
                    strategy_version=self._strategy.version,
                    feature_snapshot_hash=desired_position.feature_snapshot_hash,
                )

                # Update position state
                self._update_position(fill)
                trades_count += 1

            except KillSwitchEngagedError as e:
                # Log kill switch rejection
                self._decision_logger.log_decision(
                    layer=Layer.EXECUTION,
                    event_type="ORDER_REJECTED",
                    reason_code=e.reason_code,
                    venue="simulated",
                    symbol=approved_order.symbol,
                    side=approved_order.side,
                    size=approved_order.size,
                )

            processed_count += 1

        self._running = False

        return {
            "processed_count": processed_count,
            "trades_count": trades_count,
            "final_pnl": float(self._position_state.realized_pnl),
        }

    def _update_position(self, fill: dict) -> None:
        """Update position state after fill."""
        # Simplified position update for walking skeleton
        size = Decimal(str(fill["size"]))
        side = fill["side"]
        total_cost = Decimal(str(fill["total_cost"]))

        if side == "BUY":
            self._position_state.current_quantity += size
        else:
            self._position_state.current_quantity -= size

        # Update realized P&L (simplified)
        self._position_state.realized_pnl -= total_cost

    def stop(self) -> None:
        """Stop the trading loop."""
        self._running = False
        if hasattr(self._feed, 'stop'):
            self._feed.stop()


async def main() -> None:
    """Main entry point for live trading loop."""
    loop = LiveTradingLoop()
    try:
        result = await loop.run(max_updates=100)
        print("\n" + "=" * 50)
        print("Live Trading Loop Complete")
        print(f"Processed: {result['processed_count']} updates")
        print(f"Trades: {result['trades_count']}")
        print(f"Final P&L: ${result['final_pnl']:.2f}")
        print("=" * 50)
    except KeyboardInterrupt:
        print("\nStopping...")
        loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
