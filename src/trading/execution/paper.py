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

    # ── WO-050 §4 (R4): DISTINCT COST CHANNELS ────────────────────────────────────────────────
    #
    # THE DEFECT THIS CLOSES. These were `fee_rate_pct = 0.1` (a PERCENT) and
    # `slippage_factor = 0.001` (a FRACTION) — arithmetically the SAME 0.1% of notional. WO-048's
    # run reported total_fees == total_slippage_cost == 22,572,628.06 to the cent. Two independent
    # cost channels that always produce identical numbers cannot be told apart in any output, and a
    # genuine divergence between them would be invisible. The units differ, which is exactly how the
    # coincidence survived: one reads "0.1" and the other "0.001" and they look unrelated.
    #
    # §4.3: this changes the DEFAULTS ONLY. `compute_execution_costs` remains the one ruled
    # implementation and its arithmetic is untouched, so the WO-011 cent-level reconciliation
    # between the paper venue and the backtest CostModel still holds (both call the same function
    # and `test_cost_reconciliation` passes its own explicit rates, insulated from these defaults).
    #
    # FEE — 0.26% taker. DECLARED ENGINEERING JUDGEMENT, not a citation: a typical spot taker fee at
    # the base (lowest-volume) tier of a major crypto venue. I did not verify a published schedule
    # from here, so it is declared rather than cited (rule 0.1e). It is deliberately the LARGER
    # channel, which is realistic for liquid top-of-book trading where fees dominate.
    #
    # SLIPPAGE — 0.01% (1 bp). ANCHORED TO THE CORPUS, MEASURED not assumed. Over 50,000 frames of
    # `corpus_20260805`: mean spread 0.521 on a mean mid of 64,635.87 = **0.0806 bps** of mid
    # (half-spread 0.000403%), with mean resting depth 0.34 BTC bid / 0.90 BTC ask. A 0.1 BTC order
    # consumes ~16% of mean touch depth, so it does NOT exhaust level 1 and incurs essentially no
    # price impact beyond the spread — and the spread is ALREADY accounted for separately, since the
    # executed price crosses it (WO-008a-R6). 1 bp is therefore a deliberately generous allowance:
    # ~12x the entire observed spread, for an order that should slip almost nothing.
    #
    # ⚠ FINDING (§0.5): the OLD 0.1% slippage default was ~124x the corpus's mean full spread.
    # For this instrument at this size that figure was not conservative, it was wrong by two orders
    # of magnitude — and it silently dominated WO-048's cost total.
    DEFAULT_FEE_RATE_PCT = Decimal("0.26")      # PERCENT of notional -> 0.26%
    # DEFAULT_SPREAD_PCT REMOVED (T028): No synthetic spread - pass observed spread
    DEFAULT_SLIPPAGE_FACTOR = Decimal("0.0001")  # FRACTION of notional -> 0.01% (1 bp)

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

        # ── WO-048 §5.2 (D-b) — DECLARED LIMIT: THIS GUARD IS INERT UNDER REPLAY ────────────────
        # `_market_state_timestamp` is stamped with `datetime.now(UTC)` at set_market_state(), so
        # `state_age` measures WALL-CLOCK TIME SINCE REGISTRATION IN THIS PROCESS — not the age of
        # the data. In a backtest, set_market_state() is followed immediately by place_order(), so
        # state_age is ~0 microseconds however old the frame is and however large the gap preceding
        # it. A 2.1-hour-old price passes this guard untouched.
        #
        #   - PROTECTS: the LIVE path, where registration time and market time coincide and a
        #     genuinely stale feed shows up as elapsed wall-clock. That is what it was built for
        #     (WO-008a-R6) and there it works.
        #   - DOES NOT PROTECT: any replay. It cannot — nothing here can distinguish "the feed
        #     stalled" from "we are replaying history quickly".
        #
        # THE ANALOGOUS PROTECTION UNDER REPLAY is the segmented runner's boundary machinery
        # (WO-048 §4.3/§4.4): a fresh strategy instance per segment, and the first tick of every
        # segment observation-only. The equivalence: this guard refuses to price against data that
        # got old while we waited; the segment machinery refuses to trade on the first tick after a
        # hole we could not see across. Both refuse a fill the system had no right to make — one on
        # the live path, one on the replay path. Neither substitutes for the other, and the replay
        # path must NOT be given a fake staleness signal to make this guard appear to work.
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
            # WO-048 §5.1 (D-a): MARKET time — the timestamp of the state this fill was priced from.
            "timestamp": fill.timestamp.isoformat(),
            # SECONDARY, never the trade's time. Carried so a run can be debugged against the clock
            # it executed on without that clock ever being mistaken for the market's.
            "replay_timestamp": (
                fill.replay_timestamp.isoformat() if fill.replay_timestamp else None),
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

        # WO-048 §5.1 (D-a): MARKET TIME is the trade's time. This was `datetime.now(UTC)`, which
        # under replay stamped every historical trade with the moment the backtest ran — so no trade
        # could be reconciled against the frame it was priced from. The state's own timestamp is
        # authoritative; the replay wall-clock rides along as a secondary field.
        #
        # A state with no timestamp is a defect, not something to paper over with now(): that would
        # silently restore the behaviour this fixes. Fall back only when the attribute is absent
        # entirely (a non-conforming test double), and never when it is present.
        market_time = getattr(self._current_market_state, "timestamp", None)
        if market_time is None:
            raise ValueError(
                "EXEC_MARKET_STATE_TIMESTAMP_MISSING: the registered market state carries no "
                "timestamp, so the fill has no market time to be stamped with. Refusing to "
                "substitute the replay clock (WO-048 §5.1 / D-a)."
            )

        return Fill(
            timestamp=market_time,
            replay_timestamp=datetime.now(UTC),
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
