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
from typing import Optional, AsyncIterator

from trading.data.market_state import MarketState
from trading.data.desired_position import DesiredPosition
from trading.data.adapters.factory import create_feed, get_feed_type, is_using_live_feed
from trading.data.persistence import MarketDataPersistence
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
        strategy: Optional[Strategy] = None,
        risk_engine: Optional[RiskEngine] = None,
        execution_client: Optional[ExchangeClient] = None,
        decision_logger: Optional[DecisionLogger] = None,
        persistence: Optional[MarketDataPersistence] = None,
    ) -> None:
        """
        Initialize live trading loop.

        Args:
            strategy: Trading strategy (default: TrivialMomentumStrategy)
            risk_engine: Risk engine (default: DeterministicRiskEngine)
            execution_client: Execution client (default: PaperExecutionClient)
            decision_logger: Decision logger (default: get_logger())
            persistence: Data persistence (default: MarketDataPersistence)
        """
        self._strategy = strategy or TrivialMomentumStrategy()
        self._risk_engine = risk_engine or DeterministicRiskEngine()
        self._execution_client = execution_client or PaperExecutionClient()
        self._decision_logger = decision_logger or get_logger()
        self._persistence = persistence or MarketDataPersistence()

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
        self._feed_iterator: Optional[AsyncIterator] = None
        self._feed_stoppable = None

    async def run(self, max_updates: int = 100, duration_minutes: float = 10) -> dict:
        """
        Run the live trading loop.

        Args:
            max_updates: Maximum number of market data updates to process
            duration_minutes: Maximum duration to run (for live feed)

        Returns:
            Summary dict with processed count, trades count, final pnl, event breakdown

        Constitutional requirements:
            - End-to-end loop completes (Principle II)
            - Every decision logged (Principle VIII)
            - Raw data persisted append-only (Principle VIII)
        """
        self._running = True
        processed_count = 0
        trades_count = 0
        start_time = datetime.now(UTC)

        # Decision event tracking
        events_by_reason = {}
        feed_events = {"connected": 0, "disconnected": 0, "errors": 0}

        print("Starting live trading loop...")
        print(f"Strategy: {self._strategy.version}")
        print(f"Feed Type: {get_feed_type()} ({'LIVE TESTNET' if is_using_live_feed() else 'SIMULATED'})")
        print(f"Risk Engine: {self._risk_engine.__class__.__name__}")
        print(f"Execution: {self._execution_client.__class__.__name__}")
        print(f"Data Persistence: {self._persistence._data_dir}")
        print(f"Max updates: {max_updates}, Max duration: {duration_minutes} minutes")
        print("-" * 50)

        # Create feed from factory
        self._feed_iterator = create_feed(decision_logger=self._decision_logger)

        # Track feed stoppable if available (for Bybit feed)
        if is_using_live_feed():
            from trading.data.adapters.bybit_testnet import BybitTestnetFeed
            # We need to capture the feed instance to stop it later
            # This is handled by the factory returning the iterator

        async for market_state in self._feed_iterator:
            # Check stop conditions
            elapsed = (datetime.now(UTC) - start_time).total_seconds() / 60
            if not self._running or processed_count >= max_updates or elapsed >= duration_minutes:
                print(f"\nStop condition reached: "
                      f"running={self._running}, processed={processed_count}/{max_updates}, "
                      f"elapsed={elapsed:.1f}/{duration_minutes} minutes")
                break

            # Persist raw market event (append-only)
            try:
                self._persistence.write_event(market_state)
            except Exception as e:
                print(f"Warning: Failed to persist market event: {e}")

            # Track events by reason code
            venue = "bybit_testnet" if is_using_live_feed() else "simulated"

            # Log market data received
            self._decision_logger.log_decision(
                layer=Layer.EXECUTION,
                event_type="MARKET_DATA_RECEIVED",
                reason_code="DATA_RECEIVED",
                venue=venue,
                symbol=market_state.symbol,
            )

            events_by_reason["DATA_RECEIVED"] = events_by_reason.get("DATA_RECEIVED", 0) + 1

            # Strategy decides
            desired_position = self._strategy.decide(market_state)

            if desired_position is None:
                # No signal
                self._decision_logger.log_decision(
                    layer=Layer.STRATEGY,
                    event_type="NO_SIGNAL",
                    reason_code="STRAT_NO_SIGNAL",
                    venue=venue,
                    symbol=market_state.symbol,
                    strategy_version=self._strategy.version,
                    feature_snapshot_hash=market_state.compute_snapshot_hash(),
                )
                events_by_reason["STRAT_NO_SIGNAL"] = events_by_reason.get("STRAT_NO_SIGNAL", 0) + 1
                processed_count += 1
                continue

            # Log strategy signal
            signal_reason = "STRAT_SIGNAL_BUY" if desired_position.side.value == "BUY" else "STRAT_SIGNAL_SELL"
            self._decision_logger.log_decision(
                layer=Layer.STRATEGY,
                event_type="SIGNAL_GENERATED",
                reason_code=signal_reason,
                venue=venue,
                symbol=desired_position.symbol,
                side=desired_position.side.value,
                size=desired_position.quantity,
                strategy_version=self._strategy.version,
                feature_snapshot_hash=desired_position.feature_snapshot_hash,
            )
            events_by_reason[signal_reason] = events_by_reason.get(signal_reason, 0) + 1

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
                venue=venue,
                symbol=desired_position.symbol,
                side=desired_position.side.value,
                size=approved_order.size if approved_order else None,
                strategy_version=self._strategy.version,
                feature_snapshot_hash=desired_position.feature_snapshot_hash,
            )
            events_by_reason[reason_code] = events_by_reason.get(reason_code, 0) + 1

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
                    venue=venue,
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
                events_by_reason["EXEC_ORDER_FILLED"] = events_by_reason.get("EXEC_ORDER_FILLED", 0) + 1

            except KillSwitchEngagedError as e:
                # Log kill switch rejection
                self._decision_logger.log_decision(
                    layer=Layer.EXECUTION,
                    event_type="ORDER_REJECTED",
                    reason_code=e.reason_code,
                    venue=venue,
                    symbol=approved_order.symbol,
                    side=approved_order.side,
                    size=approved_order.size,
                )
                events_by_reason[e.reason_code] = events_by_reason.get(e.reason_code, 0) + 1

            processed_count += 1

        self._running = False

        # Close persistence layer
        try:
            self._persistence.close()
        except Exception as e:
            print(f"Warning: Error closing persistence: {e}")

        # Get persistence file info
        persistence_info = self._persistence.get_file_info()

        # Calculate elapsed time
        elapsed_minutes = (datetime.now(UTC) - start_time).total_seconds() / 60

        return {
            "processed_count": processed_count,
            "trades_count": trades_count,
            "final_pnl": float(self._position_state.realized_pnl),
            "elapsed_minutes": elapsed_minutes,
            "events_by_reason": events_by_reason,
            "feed_events": feed_events,
            "persistence_info": persistence_info,
            "venue": venue,
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
        # Run for 10 minutes or 1000 updates, whichever comes first
        result = await loop.run(max_updates=1000, duration_minutes=10)

        print("\n" + "=" * 60)
        print("LIVE TRADING LOOP COMPLETE")
        print("=" * 60)
        print(f"Venue: {result['venue']}")
        print(f"Elapsed: {result['elapsed_minutes']:.2f} minutes")
        print(f"Processed: {result['processed_count']} market events")
        print(f"Trades: {result['trades_count']}")
        print(f"Final P&L: ${result['final_pnl']:.2f}")
        print("-" * 60)

        # Print events by reason code
        print("Events by Reason Code:")
        for reason, count in sorted(result['events_by_reason'].items()):
            print(f"  {reason}: {count}")

        print("-" * 60)

        # Print persistence info
        persistence = result['persistence_info']
        print(f"Data Persistence:")
        print(f"  File: {persistence['path']}")
        print(f"  Exists: {persistence['exists']}")
        print(f"  Events written: {persistence['event_count']}")
        print(f"  Size: {persistence['size_bytes']} bytes")

        print("=" * 60)

    except KeyboardInterrupt:
        print("\nStopping...")
        loop.stop()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
