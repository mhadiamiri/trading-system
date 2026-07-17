"""
Kraken Public Market Data Feed

Live WebSocket connection to Kraken mainnet for public market data.
Unauthenticated, read-only, public trade data only.

Constitutional Principles:
- VII. Venue Independence: Strict abstraction, no Kraken types leak
- IX. Secrets and Safety Rails: No credentials required (public feed only)
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from decimal import Decimal
from typing import AsyncIterator, Optional
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

from trading.data.market_state import MarketState
from trading.logkit.decision import DecisionLogger


logger = logging.getLogger(__name__)


class KrakenPublicFeed:
    """
    Live Kraken mainnet WebSocket feed for BTC/USD market data.

    Connects to wss://ws.kraken.com for public trade data.
    Unauthenticated - no API key required.

    Constitutional requirements:
    - No Kraken-specific types leak above adapter (Principle VII)
    - No credentials required (public feed only)
    - All failures logged with reason codes
    """

    # Kraken public WebSocket endpoint
    WS_URL = "wss://ws.kraken.com"

    # Symbol for BTC/USD on Kraken (XBT/USD)
    KRAKEN_SYMBOL = "XBT/USD"

    # Standardized symbol for our system
    STANDARD_SYMBOL = "BTC/USD"

    # Subscribe to trades
    SUBSCRIPTION_MSG = {
        "event": "subscribe",
        "pair": [KRAKEN_SYMBOL],
        "subscription": {
            "name": "trade"
        }
    }

    def __init__(
        self,
        decision_logger: Optional[DecisionLogger] = None,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 60.0,
    ) -> None:
        """
        Initialize Kraken public feed.

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

        # Diagnostic counters
        self._raw_messages_received = 0
        self._subscription_confirmations = 0
        self._market_states_emitted = 0
        self._parse_errors = 0
        self._filtered_messages = 0
        self._heartbeat_messages = 0

    async def get_market_data(self) -> AsyncIterator[MarketState]:
        """
        Stream live market data from Kraken mainnet.

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
                        venue="kraken_mainnet",
                        symbol=self.STANDARD_SYMBOL,
                    )

                    # Process messages
                    async for message in websocket:
                        if not self._running:
                            break

                        # Count raw messages
                        self._raw_messages_received += 1

                        try:
                            market_state = self._parse_message(message)
                            if market_state:
                                self._market_states_emitted += 1
                                yield market_state
                            else:
                                # Message was filtered (heartbeat, system status, etc.)
                                self._filtered_messages += 1

                        except json.JSONDecodeError as e:
                            self._parse_errors += 1
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

        Kraken message format:
        - System events: {"event": "..."}
        - Trade data: [channelID, [[price, volume, time, side, ...]], channelName, pair]

        Raises:
            json.JSONDecodeError: If message is not valid JSON
        """
        data = json.loads(message)

        # Handle system events (subscription confirmation, heartbeat, etc.)
        if isinstance(data, dict) and "event" in data:
            event_type = data.get("event")

            if event_type == "subscriptionStatus":
                logger.info(f"Subscription status: {data.get('status')} for {data.get('pair')}")
                self._subscription_confirmations += 1
            elif event_type == "heartbeat":
                self._heartbeat_messages += 1

            return None

        # Handle trade data (array format)
        if not isinstance(data, list) or len(data) < 4:
            return None

        # Kraken trade format: [channelID, [[price, volume, time, side, ...]], channelName, pair]
        trades = data[1]
        channel_name = data[2] if len(data) > 2 else None
        pair = data[3] if len(data) > 3 else None

        # Verify this is a trade message for our pair
        if channel_name != "trade" or pair != self.KRAKEN_SYMBOL:
            return None

        # Parse trades (comes as array of arrays)
        if not trades or not isinstance(trades, list):
            return None

        # Use the most recent trade (last in array)
        trade = trades[-1] if isinstance(trades[-1], list) else trades[0]

        # Extract fields (Kraken specific names stay here)
        # Format: [price, volume, time, side, ...]
        price = Decimal(str(trade[0])) if len(trade) > 0 else Decimal("0")
        size = Decimal(str(trade[1])) if len(trade) > 1 else Decimal("0")
        side = trade[3] if len(trade) > 3 else ""  # 'b' (buy) or 's' (sell)

        # Calculate bid/ask spread (simplified - we'd need orderbook for real spread)
        # Using 0.01% spread estimate for BTC/USD
        spread = price * Decimal("0.0001")
        bid_price = price - spread / 2
        ask_price = price + spread / 2

        # Create MarketState (no Kraken types leak out)
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
        venue: str = "kraken_mainnet",
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
            logger.info("Kraken public feed stopped")

    def is_running(self) -> bool:
        """Check if feed is running."""
        return self._running

    @property
    def venue_name(self) -> str:
        """Return the venue name for this feed adapter."""
        return "kraken_mainnet"

    def get_diagnostic_counters(self) -> dict:
        """
        Get diagnostic counters for message flow analysis.

        Returns:
            Dict with raw message counts and pipeline metrics
        """
        return {
            "raw_messages_received": self._raw_messages_received,
            "subscription_confirmations": self._subscription_confirmations,
            "market_states_emitted": self._market_states_emitted,
            "parse_errors": self._parse_errors,
            "filtered_messages": self._filtered_messages,
            "heartbeat_messages": self._heartbeat_messages,
            "message_type_breakdown": {
                "subscription_confirmations": self._subscription_confirmations,
                "trade_messages": self._market_states_emitted,
                "heartbeats": self._heartbeat_messages,
                "filtered": self._filtered_messages,
                "errors": self._parse_errors,
            },
        }

    def reset_counters(self) -> None:
        """Reset diagnostic counters."""
        self._raw_messages_received = 0
        self._subscription_confirmations = 0
        self._market_states_emitted = 0
        self._parse_errors = 0
        self._filtered_messages = 0
        self._heartbeat_messages = 0
