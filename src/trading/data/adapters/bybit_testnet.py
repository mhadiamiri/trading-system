"""
Bybit Testnet Market Data Feed

Live WebSocket connection to Bybit testnet for real market data.

Constitutional Principles:
- VII. Venue Independence: Strict abstraction, no Bybit types leak
- IX. Secrets and Safety Rails: Credentials from .env only
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from decimal import Decimal
from typing import AsyncIterator, Optional
import os
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

from trading.data.market_state import MarketState
from trading.logkit.decision import DecisionLogger


logger = logging.getLogger(__name__)


class BybitTestnetFeed:
    """
    Live Bybit testnet WebSocket feed for BTC/USD market data.

    Connects to wss://stream-testnet.bybit.com/v5/public/linear
    Subscribes to BTCUSDT trades for real-time market data.

    Constitutional requirements:
    - No Bybit-specific types leak above adapter (Principle VII)
    - Credentials read from .env only (Principle IX)
    - All failures logged with reason codes
    """

    # Bybit testnet WebSocket endpoint
    WS_URL = "wss://stream-testnet.bybit.com/v5/public/linear"

    # Symbol for BTC/USD on Bybit (BTCUSDT perpetual)
    SYMBOL = "BTCUSDT"

    # Standardized symbol for our system
    STANDARD_SYMBOL = "BTC/USD"

    # Subscribe to trades
    SUBSCRIPTION_MSG = {
        "op": "subscribe",
        "args": ["publicTrade.BTCUSDT"]
    }

    def __init__(
        self,
        decision_logger: Optional[DecisionLogger] = None,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 60.0,
    ) -> None:
        """
        Initialize Bybit testnet feed.

        Args:
            decision_logger: Optional logger for decision events
            reconnect_base_delay: Base delay for exponential backoff (seconds)
            reconnect_max_delay: Maximum delay for reconnect attempts (seconds)
        """
        self._decision_logger = decision_logger
        self._reconnect_base_delay = reconnect_base_delay
        self._reconnect_max_delay = reconnect_max_delay
        self._running = False
        self._websocket = None
        self._reconnect_delay = reconnect_base_delay

    async def get_market_data(self) -> AsyncIterator[MarketState]:
        """
        Stream live market data from Bybit testnet.

        Yields:
            MarketState objects with real-time data

        Raises:
            ConnectionError: If connection fails after retries
        """
        self._running = True
        reconnect_attempts = 0

        while self._running:
            try:
                async with websockets.connect(self.WS_URL) as websocket:
                    self._websocket = websocket
                    self._reconnect_delay = self._reconnect_base_delay
                    reconnect_attempts = 0

                    # Subscribe to trades
                    await websocket.send(json.dumps(self.SUBSCRIPTION_MSG))

                    # Log successful connection
                    self._log_decision(
                        layer="data",
                        event_type="feed_connected",
                        reason_code="FEED_CONNECTED",
                        venue="bybit_testnet",
                        symbol=self.STANDARD_SYMBOL,
                    )

                    # Process messages
                    async for message in websocket:
                        if not self._running:
                            break

                        try:
                            market_state = self._parse_message(message)
                            if market_state:
                                yield market_state

                        except json.JSONDecodeError as e:
                            self._log_decision(
                                layer="data",
                                event_type="payload_error",
                                reason_code="FEED_MALFORMED_PAYLOAD",
                                details=f"JSON decode error: {e}",
                            )
                            logger.warning(f"Malformed JSON: {e}")

                        except Exception as e:
                            self._log_decision(
                                layer="data",
                                event_type="payload_error",
                                reason_code="FEED_UNEXPECTED_PAYLOAD",
                                details=f"Parse error: {e}",
                            )
                            logger.warning(f"Parse error: {e}")

            except ConnectionClosedError as e:
                reconnect_attempts += 1
                self._log_decision(
                    layer="data",
                    event_type="feed_disconnected",
                    reason_code="FEED_CONNECTION_CLOSED",
                    details=f"Connection closed: {e}",
                )
                logger.warning(f"Connection closed: {e}")

                if not self._running:
                    break

                # Exponential backoff
                delay = min(self._reconnect_delay * (2 ** reconnect_attempts), self._reconnect_max_delay)
                logger.info(f"Reconnecting in {delay}s... (attempt {reconnect_attempts})")
                await asyncio.sleep(delay)

            except Exception as e:
                reconnect_attempts += 1
                self._log_decision(
                    layer="data",
                    event_type="feed_error",
                    reason_code="FEED_CONNECTION_ERROR",
                    details=f"Connection error: {e}",
                )
                logger.error(f"Connection error: {e}")

                if not self._running:
                    break

                # Exponential backoff
                delay = min(self._reconnect_delay * (2 ** reconnect_attempts), self._reconnect_max_delay)
                logger.info(f"Reconnecting in {delay}s... (attempt {reconnect_attempts})")
                await asyncio.sleep(delay)

    def _parse_message(self, message: str) -> Optional[MarketState]:
        """
        Parse WebSocket message into MarketState.

        Args:
            message: Raw WebSocket message string

        Returns:
            MarketState object or None if not a trade message

        Raises:
            json.JSONDecodeError: If message is not valid JSON
        """
        data = json.loads(message)

        # Handle subscription confirmation
        if data.get("success") is True:
            logger.info(f"Subscription confirmed: {data.get('ret_msg')}")
            return None

        # Extract trade data
        if "topic" not in data or "data" not in data:
            return None

        topic = data["topic"]
        if topic != "publicTrade.BTCUSDT":
            return None

        # Parse trades (comes as array)
        trades = data["data"]
        if not trades or not isinstance(trades, list):
            return None

        # Use the most recent trade
        trade = trades[0] if isinstance(trades[0], dict) else trades[0]

        # Extract fields (Bybit specific names stay here)
        price = Decimal(trade.get("p", "0"))
        size = Decimal(trade.get("v", "0"))
        side = trade.get("S", "")  # 'Buy' or 'Sell'

        # Calculate bid/ask spread (simplified - we'd need orderbook for real spread)
        spread = price * Decimal("0.0001")  # 0.01% spread estimate
        bid_price = price - spread / 2
        ask_price = price + spread / 2

        # Create MarketState (no Bybit types leak out)
        return MarketState(
            timestamp=datetime.now(UTC),
            symbol=self.STANDARD_SYMBOL,
            bid_price=bid_price.quantize(Decimal("0.01")),
            ask_price=ask_price.quantize(Decimal("0.01")),
            last_price=price.quantize(Decimal("0.01")),
            volume_24h=Decimal("0"),  # Not provided in trade stream
        )

    def _log_decision(
        self,
        layer: str,
        event_type: str,
        reason_code: str,
        venue: str = "bybit_testnet",
        symbol: str = "BTC/USD",
        details: str = "",
    ) -> None:
        """Log feed events with reason codes."""
        if self._decision_logger:
            self._decision_logger.log_feed_event(
                layer=layer,
                event_type=event_type,
                reason_code=reason_code,
                venue=venue,
                symbol=symbol,
                details=details,
            )

    async def stop(self) -> None:
        """Stop the feed and close connection."""
        self._running = False
        if self._websocket:
            await self._websocket.close()
            logger.info("Bybit testnet feed stopped")

    def is_running(self) -> bool:
        """Check if feed is running."""
        return self._running
