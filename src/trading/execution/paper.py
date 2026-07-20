"""
Paper Execution Client

Simulated execution for paper trading (no real money).

Constitutional Principles:
- VI. Risk Engine Is Sovereign: Kill switch semantics
- IX. Secrets and Safety Rails: No real-money orders
"""

from datetime import datetime, UTC, timedelta
from decimal import Decimal
from typing import AsyncIterator, Optional
import asyncio

from trading.execution.interface import ExchangeClient, KillSwitchEngagedError
from trading.execution.fill import Fill
from trading.execution.costs import compute_execution_costs
from trading.data.market_state import MarketState


class PaperExecutionClient(ExchangeClient):
    """
    Simulated (paper) execution client.

    All fills are simulated with realistic cost modeling:
    - Executed price reflects spread crossing (BUY pays ask, SELL gets bid)
    - Trading fees (default 0.1% taker per side, observed from venue)
    - Spread cost (observed from market state, included in executed price - WO-008a-R6)
    - Slippage adjustment (assumed 0.1% constant - WO-008a-R5)

    Constitutional requirements:
    - No real-money orders (simulated only)
    - Kill switch blocks new orders (Principle VI)
    - Cancellation succeeds even when kill switch engaged (Principle VI)
    """

    # Default cost parameters
    DEFAULT_FEE_RATE_PCT = Decimal("0.1")  # 0.1% taker fee per side (observed)
    # DEFAULT_SPREAD_PCT REMOVED (T028): No synthetic spread - pass observed spread
    DEFAULT_SLIPPAGE_FACTOR = Decimal("0.001")  # 0.1% slippage factor (ASSUMED CONSTANT - WO-008a-R5)

    # Staleness threshold (WO-008a-R6: guard against filling against stale market data)
    # Historical rate: ~10 MarketStates/min = 1 state every 6 seconds
    # Threshold: 18 seconds = 3x historical interval
    # Reasoning: Allows normal variance but detects genuine stalls within seconds
    # Not a round number: derived from 3 × (60 / 10) = 18
    DEFAULT_STALENESS_THRESHOLD_SECONDS = 18

    def __init__(
        self,
        fee_rate_pct: Decimal = DEFAULT_FEE_RATE_PCT,
        slippage_factor: Decimal = DEFAULT_SLIPPAGE_FACTOR,
        staleness_threshold_seconds: float = DEFAULT_STALENESS_THRESHOLD_SECONDS,
    ) -> None:
        """
        Initialize paper execution client.

        Args:
            fee_rate_pct: Trading fee rate as percentage (default 0.1%)
            slippage_factor: Slippage adjustment factor (default 0.001%)
            staleness_threshold_seconds: Maximum age of MarketState before
                it's considered stale (default 18 seconds, WO-008a-R6)

        Raises:
            ValueError: If TRADING_ENV is not 'paper' (constitutional guard)

        Constitutional requirements:
            - PaperExecutionClient can ONLY be used when TRADING_ENV=paper
            - This ensures no real-money orders can be placed in paper mode
            - When real-money adapters are added (Sprint 3), they will have
              an inverse check requiring TRADING_ENV=mainnet

        Note (T028):
            spread_pct parameter REMOVED: No synthetic spread allowed.
            Pass observed spread to _simulate_fill() instead.

        Note (WO-008a-R6):
            staleness_threshold_seconds prevents filling against stale data.
            Derived from 3x historical interval (60/10 × 3 = 18).
        """
        # CONSTITUTIONAL GUARD (Principle IX):
        # Verify this client is only used in paper trading mode
        from config.settings import Settings

        if not Settings.is_paper_trading():
            raise ValueError(
                f"PaperExecutionClient CANNOT be used when TRADING_ENV={Settings.TRADING_ENV}. "
                f"PaperExecutionClient is for paper trading only (TRADING_ENV=paper). "
                f"This is a constitutional guard preventing accidental real-money order placement. "
                f"See .specify/memory/constitution.md Principle IX."
            )

        self._fee_rate_pct = fee_rate_pct
        self._slippage_factor = slippage_factor
        self._staleness_threshold = timedelta(seconds=staleness_threshold_seconds)
        self._orders: dict[str, dict] = {}  # Simulated order book
        self._current_market_state: Optional[MarketState] = None  # Current market state for fill economics
        self._market_state_timestamp: Optional[datetime] = None  # When market_state was set (WO-008a-R6)

    def set_market_state(self, market_state: MarketState) -> None:
        """
        Register the current market state for computing fill economics.

        This method is specific to the paper venue simulator. Real venues
        (Kraken, Coinbase) determine fill economics from their own matching
        engine, so they don't need this method.

        The caller (live loop or backtest runner) must call this method before
        placing each order, so the paper venue can compute realistic fill
        economics from the observed bid/ask spread.

        Args:
            market_state: Current market state with observed bid/ask

        Constitutional requirements:
            - Paper venue uses observed spread only (no synthetic, T028)
            - Fill economics computed internally, not supplied by caller
            - Staleness guard prevents filling against stale data (WO-008a-R6)
        """
        self._current_market_state = market_state
        self._market_state_timestamp = datetime.now(UTC)  # Track when state was set (WO-008a-R6)

    async def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        kill_switch_engaged: bool,
    ) -> dict:
        """
        Place simulated order and return fill result.

        This method takes an ORDER INTENT ONLY: symbol, side, size, price, and
        kill switch state. The paper venue computes all fill economics internally
        from the current MarketState (registered via set_market_state()).

        Args:
            symbol: Trading pair
            side: "BUY" or "SELL"
            size: Order size (from ApprovedOrder)
            price: Order type/limit price from order intent (NOT fill price)
            kill_switch_engaged: If True, raise KillSwitchEngagedError

        Returns:
            Fill dict with all cost components: timestamp, symbol, side, size,
            fill_price, fees, spread_cost (attribution), slippage_cost,
            total_cost (fees + slippage only), cad_value

        Raises:
            KillSwitchEngagedError: When kill_switch_engaged=True
            ValueError: If MarketState not registered (set_market_state not called)

        Constitutional requirements:
            - Raises KillSwitchEngagedError when kill switch engaged (Principle VI)
            - No synthetic spread (T028): spread_cost computed from observed bid/ask
            - Fill economics computed internally by paper venue (WO-008a-R5)
        """
        if kill_switch_engaged:
            raise KillSwitchEngagedError()

        # Verify market state is registered (WO-008a-R6 staleness guard)
        if self._current_market_state is None:
            raise ValueError(
                "EXEC_NO_MARKET_STATE: MarketState not registered. "
                "Call set_market_state() before place_order(). "
                "The paper venue refuses to fill without current market data."
            )

        # Verify market state is not stale (WO-008a-R6 staleness guard)
        if self._market_state_timestamp is None:
            raise ValueError(
                "EXEC_MARKET_STATE_TIMESTAMP_MISSING: MarketState timestamp not recorded. "
                "This is a staleness guard invariant violation."
            )

        state_age = datetime.now(UTC) - self._market_state_timestamp
        if state_age > self._staleness_threshold:
            raise ValueError(
                f"EXEC_STALE_MARKET_STATE: MarketState is too old ({state_age.total_seconds():.1f}s). "
                f"Threshold: {self._staleness_threshold.total_seconds():.1f}s. "
                f"The paper venue refuses to fill against stale market data."
            )

        # Simulate fill with realistic costs (paper venue computes internally)
        fill = self._simulate_fill(symbol, side, size, price)
        return {
            "timestamp": fill.timestamp.isoformat(),
            "symbol": fill.symbol,
            "side": fill.side,
            "size": float(fill.size),
            "fill_price": float(fill.fill_price),  # Includes spread cost (ask for BUY, bid for SELL)
            "fees": float(fill.fees),  # Additive cost
            "spread_cost": float(fill.spread_cost),  # Attribution only (included in fill_price, NOT additive)
            "slippage_cost": float(fill.slippage_cost),  # Additive cost
            "total_cost": float(fill.total_cost),  # fees + slippage only (WO-008a-R6: spread not additive)
            "cad_value": float(fill.cad_value),
        }

    async def cancel_order(self, order_id: str, kill_switch_engaged: bool) -> bool:
        """
        Cancel simulated order.

        Args:
            order_id: Order identifier
            kill_switch_engaged: Ignored for cancellation

        Returns:
            True if cancelled, False if order not found

        Constitutional requirements:
            - Cancellation succeeds even when kill switch engaged (Principle VI)
        """
        # Simulated cancellation - ignore kill_switch_engaged
        if order_id in self._orders:
            del self._orders[order_id]
            return True
        return False

    async def get_market_data(self) -> AsyncIterator[dict]:
        """
        Stream simulated market data updates.

        Yields:
            Market data dicts

        Note:
            This is a placeholder. Real implementation in Task 106.
        """
        # Placeholder - will be implemented in Task 106
        yield {}
        return

    def _simulate_fill(
        self, symbol: str, side: str, size: float, price: float
    ) -> Fill:
        """
        Simulate fill with realistic cost modeling (computed internally).

        Fill economics come from the SINGLE unified cost model (WO-011 §1):
        trading.execution.costs.compute_execution_costs. The backtest CostModel
        calls the same function, so paper and backtest are identical by
        construction, not by two implementations agreeing.
        - Executed price reflects spread crossing (BUY pays ask, SELL gets bid)
        - Fees computed from executed notional (additive cost)
        - Spread cost from observed bid/ask (ATTRIBUTION, not additive - WO-008a-R6)
        - Slippage as assumed constant (additive cost - WO-008a-R5 labeling required)
        - Abnormal spread (>5%) is REJECTED (FR-015b / WO-011 RULING 3)

        Args:
            symbol: Trading pair
            side: "BUY" or "SELL"
            size: Order size
            price: Order type/limit price from order intent (NOT used for fill)

        Returns:
            Fill with all cost components

        Constitutional requirements:
            - All costs included (Principle I: Truth Before Profit)
            - No synthetic spread (T028): spread from observed bid/ask
            - Fill economics computed by paper venue (WO-008a-R5)

        Raises:
            ValueError: If MarketState not registered
            ValueError: ABNORMAL_SPREAD_REJECT if spread > 5% (FR-015b, WO-011 RULING 3)
        """
        if self._current_market_state is None:
            raise ValueError("MarketState not registered. Call set_market_state() first.")

        size_dec = Decimal(str(size))

        # Unified ruled cost model (WO-011 §1) — the SOLE implementation.
        costs = compute_execution_costs(
            side=side,
            size=size_dec,
            market_state=self._current_market_state,
            fee_rate_pct=self._fee_rate_pct,
            slippage_factor=self._slippage_factor,
        )

        # CAD value (assume 1 USD = 1.35 CAD for simplicity)
        notional = size_dec * costs.executed_price
        cad_value = notional * Decimal("1.35")

        return Fill(
            timestamp=datetime.now(UTC),
            symbol=symbol,
            side=side,
            size=size_dec,
            fill_price=costs.executed_price,  # Reflects spread crossing
            spread_cost=costs.spread_cost,
            slippage_cost=costs.slippage_cost,
            fees=costs.fees,
            total_cost=costs.total_cost,
            cad_value=cad_value,
        )
