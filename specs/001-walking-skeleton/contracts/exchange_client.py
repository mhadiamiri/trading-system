"""
ExchangeClient Interface Contract

This module defines the ExchangeClient interface that all execution adapters must implement.

Constitutional Principles:
- VII. Venue Independence: Venue-specific code confined to adapter modules
- IX. Secrets and Safety Rails: Impossible to place real-money order by accident
"""

from typing import AsyncIterator
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import asyncio


class Side(Enum):
    """Order side direction."""
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class ApprovedOrder:
    """
    Risk-approved order ready for execution.

    Invariants:
    - size > 0 (risk engine ensures non-zero)
    - size <= original_size (clamp only reduces toward zero)
    - side does not flip from original DesiredPosition

    Constitutional requirements:
    - Result of risk engine check (Principle III: Deterministic Code Disposes)
    - Clamp may only reduce size, never flip side (Principle VI: Risk Engine Is Sovereign)
    """
    timestamp: datetime
    symbol: str
    side: Side
    size: Decimal
    price: Decimal
    reason_code: str
    original_size: Decimal


@dataclass(frozen=True)
class Fill:
    """
    Executed trade result (simulated or real).

    Invariants:
    - total_cost = spread_cost + slippage_cost + fees
    - All cost components are non-negative
    - cad_value is calculated for Canadian tax records

    Constitutional requirements:
    - Cost-inclusive (Principle I: Truth Before Profit)
    - CAD tax fields captured (Principle VIII: Total Observability & Provenance)
    """
    timestamp: datetime
    symbol: str
    side: Side
    size: Decimal
    fill_price: Decimal
    spread_cost: Decimal
    slippage_cost: Decimal
    fees: Decimal
    total_cost: Decimal
    cad_value: Decimal


@dataclass(frozen=True)
class MarketState:
    """Market data view (simplified for interface)."""
    timestamp: datetime
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    last_price: Decimal
    volume_24h: Decimal


class KillSwitchEngagedError(Exception):
    """
    Raised when place_order is called while kill switch is engaged.

    Constitutional requirement: Per Principle VI, the kill switch blocks new orders
    but must never disable cancellation. This exception is the distinct, logged outcome
    for blocked orders with reason code EXEC_BLOCKED_KILL_SWITCH.

    Tests must verify: kill switch engaged → place_order refused AND cancel_order still succeeds.
    """
    pass


class ExchangeClient:
    """
    Exchange client interface.

    All venue adapters must implement this interface.

    Constitutional requirements:
    - Venue-specific code MUST be confined to single adapter module (Principle VII)
    - MUST refuse live/mainnet connection without explicit TRADING_ENV override (Principle IX)
    - MUST implement operational defaults: idempotent order IDs, exponential backoff (Principle IX)
    - Kill switch semantics: place_order refuses, cancel_order remains callable (Principle VI)

    Implementation notes:
    - Bybit testnet is provisional venue (src/trading/execution/adapters/bybit_testnet.py)
    - Swapping to Canada-legal venue (Kraken/Coinbase) MUST be one-module change
    - No venue-specific types, payloads, enums, or error shapes may leak above adapter

    Reason codes for execution layer:
    - EXEC_ORDER_SUBMITTED: Order submitted to venue
    - EXEC_ORDER_FILLED: Order filled completely
    - EXEC_ORDER_CANCELLED: Order cancelled
    - EXEC_BACKOFF_RATE_LIMIT: Backing off due to rate limit
    - EXEC_BLOCKED_KILL_SWITCH: Order blocked due to kill switch engaged
    """

    async def place_order(self, order: ApprovedOrder, kill_switch_engaged: bool = False) -> Fill:
        """
        Place order and return fill.

        Args:
            order: Risk-approved order
            kill_switch_engaged: Current state of the kill switch (from RiskEngine)

        Returns:
            Fill with all cost components applied

        Behavioral contract:
        - MUST apply fees to every trade (Principle V: No Backtest Without Costs)
        - MUST apply bid/ask spread cost
        - MUST apply slippage/fill model
        - MUST use idempotent client order IDs (Principle IX)
        - For paper/testnet: simulated fill only (no real money)

        KILL SWITCH BEHAVIOR (Principle VI: The Risk Engine Is Sovereign):
        - When kill_switch_engaged=True: MUST refuse to place order
        - MUST raise KillSwitchEngagedError with reason code EXEC_BLOCKED_KILL_SWITCH
        - This refusal MUST be logged with reason code and timestamp
        - The distinct exception type enables logged outcome tracking

        Raises:
            KillSwitchEngagedError: If kill_switch_engaged=True (with EXEC_BLOCKED_KILL_SWITCH reason code)
            ConnectionError: Venue unavailable
            RateLimitError: Rate limited (implement exponential backoff)

        Test requirement (from Constitution Check):
        - tests/ must cover: kill switch engaged → place_order refused AND cancel_order still succeeds
        """
        raise NotImplementedError("ExchangeClient must implement place_order()")

    async def cancel_order(self, order_id: str, kill_switch_engaged: bool = False) -> bool:
        """
        Cancel order.

        Args:
            order_id: Order ID to cancel
            kill_switch_engaged: Current state of the kill switch (from RiskEngine)

        Returns:
            True if cancelled, False if not found

        Behavioral contract:
        - MUST permit cancellation even when kill switch engaged (Principle VI)
        - Kill switch blocks new orders only, never disables cancellation
        - This is the emergency stop: we can always close positions, even during kill switch

        KILL SWITCH BEHAVIOR (Principle VI: The Risk Engine Is Sovereign):
        - When kill_switch_engaged=True: MUST still process cancellation normally
        - MUST NOT raise KillSwitchEngagedError for cancellation
        - Cancellation remains fully functional regardless of kill switch state

        Raises:
            ConnectionError: Venue unavailable

        Test requirement (from Constitution Check):
        - tests/ must cover: kill switch engaged → place_order refused AND cancel_order still succeeds
        """
        raise NotImplementedError("ExchangeClient must implement cancel_order()")

    async def get_market_data(self) -> AsyncIterator[MarketState]:
        """
        Stream market data updates.

        Yields:
            MarketState for each update

        Behavioral contract:
        - MUST yield updates in real-time
        - MUST handle disconnections gracefully (log, pause, resume)
        - For testnet: WebSocket connection to venue's public feed

        Raises:
            ConnectionError: Feed unavailable
        """
        raise NotImplementedError("ExchangeClient must implement get_market_data()")

    def validate_trading_env(self, env: str, explicit_override: bool = False) -> None:
        """
        Validate trading environment before allowing operations.

        Args:
            env: TRADING_ENV value ("testnet" or "mainnet")
            explicit_override: Whether user explicitly confirmed mainnet access

        Behavioral contract:
        - MUST refuse mainnet connection without explicit_override=True (Principle IX)
        - This is the guardrail preventing accidental real-money orders

        Raises:
            PermissionError: If env=="mainnet" and explicit_override=False
        """
        if env == "mainnet" and not explicit_override:
            raise PermissionError(
                "Refusing to connect to connect to mainnet without explicit override. "
                "Set TRADING_ENV=testnet for paper trading, or explicitly confirm "
                "mainnet access with the --allow-mainnet flag."
            )
