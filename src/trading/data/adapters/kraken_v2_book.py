"""
Kraken v2 Book Adapter

WebSocket adapter for Kraken v2 book channel with checksum validation.

Constitutional Principles:
- V. No Backtest Without Costs: Observed spread only
- VII. Venue Independence: v2 detail confined to this adapter
- VIII. Total Observability: All non-yield events logged with reason codes

Venue-Specific Details (must NOT leak above adapter):
- v2 WebSocket protocol
- CRC checksum algorithm
- Sequence number tracking
- Resync/resnapshot logic
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from unittest.mock import Mock
import enum
import binascii

from trading.data.market_state import MarketState


class LocalBookState(enum.Enum):
    """
    Local book state transitions for Kraken v2 book adapter.

    States: INITIAL → SYNCHRONIZED → RESYNC_REQUIRED → PAUSED → SYNCHRONIZED

    Constitutional requirements:
    - FR-018: Recovery after 5 consecutive failures
    - FR-018a: Sequence gap triggers resnapshot
    - FR-019a: Pause on book unavailable
    """

    INITIAL = "initial"
    SYNCHRONIZED = "synchronized"
    RESYNC_REQUIRED = "resync_required"
    PAUSED = "paused"


@dataclass
class LocalBookData:
    """
    Local book state data (adapter-internal for Kraken v2 book adapter).

    This entity maintains FULL BOOK DEPTH (10+ levels per side) from v2 snapshot
    + incremental updates, validated by CRC checksum. All v2-specific detail lives here.

    IMPORTANT: This redesign maintains the full book depth required for Kraken's
    checksum validation, which is computed over the TOP 10 price levels per side.

    Fields:
        bids: Sorted list of (price, size) tuples for bid levels (high→low)
        asks: Sorted list of (price, size) tuples for ask levels (low→high)
        last_sequence: Last processed sequence number
        last_checksum: Last valid checksum received
        consecutive_failures: Count of consecutive checksum validation failures
        is_paused: Whether adapter is paused (book unavailable)

    Validation rules:
        - Checksum validation on every update (FR-004, FR-016)
        - Sequence gap detection (FR-018a)
        - 5-failure threshold triggers resync (FR-018)

    State transitions:
        INITIAL → SYNCHRONIZED: After successful snapshot
        SYNCHRONIZED → RESYNC_REQUIRED: After 5 checksum failures or sequence gap
        RESYNC_REQUIRED → SYNCHRONIZED: After successful resync
        SYNCHRONIZED → PAUSED: On book unavailability (FR-019a)
        PAUSED → SYNCHRONIZED: On book recovery

    Update logic (per Kraken v2 spec):
        - qty: 0 at a price level REMOVES that level
        - After applying updates, re-sort and truncate to subscribed depth
        - Maintain at least 10 levels per side for checksum validation

    Constitutional requirements:
        - FR-004: Validate checksums on every update
        - FR-016: Maintain local book state from validated updates
        - FR-017: Log rejections with invalid checksums
        - FR-018: 5 consecutive failures → resync
        - FR-018a: Sequence gap → resnapshot
        - FR-019a: Book unavailable → pause
        - WO-006 new decision: Full depth redesign (10+ levels per side)
    """

    bids: List[tuple] = field(default_factory=list)
    asks: List[tuple] = field(default_factory=list)
    last_sequence: int = 0
    last_checksum: int = 0
    consecutive_failures: int = 0
    is_paused: bool = False

    @property
    def state(self) -> LocalBookState:
        """Get current state based on fields."""
        if self.is_paused:
            return LocalBookState.PAUSED
        elif self.last_sequence == 0:
            return LocalBookState.INITIAL
        elif self.consecutive_failures >= 5:
            return LocalBookState.RESYNC_REQUIRED
        else:
            return LocalBookState.SYNCHRONIZED

    @property
    def best_bid_price(self) -> Decimal:
        """Get best bid price (level 0 of bids ladder)."""
        if not self.bids:
            return Decimal("0")
        price = self.bids[0][0] if self.bids[0] else Decimal("0")
        return Decimal(str(price)) if price else Decimal("0")

    @property
    def best_bid_size(self) -> Decimal:
        """Get size at best bid (level 0 of bids ladder)."""
        if not self.bids:
            return Decimal("0")
        size = self.bids[0][1] if len(self.bids) > 0 and self.bids[0][1] else Decimal("0")
        return Decimal(str(size)) if size else Decimal("0")

    @property
    def best_ask_price(self) -> Decimal:
        """Get best ask price (level 0 of asks ladder)."""
        if not self.asks:
            return Decimal("0")
        price = self.asks[0][0] if self.asks[0] else Decimal("0")
        return Decimal(str(price)) if price else Decimal("0")

    @property
    def best_ask_size(self) -> Decimal:
        """Get size at best ask (level 0 of asks ladder)."""
        if not self.asks:
            return Decimal("0")
        size = self.asks[0][1] if len(self.asks) > 0 and self.asks[0][1] else Decimal("0")
        return Decimal(str(size)) if size else Decimal("0")

    def apply_snapshot(self, bid_levels: List[tuple], ask_levels: List[tuple],
                       sequence: int, checksum: int) -> None:
        """
        Apply a snapshot to initialize the book.

        Args:
            bid_levels: List of (price, size) tuples for bids
            ask_levels: List of (price, size) tuples for asks
            sequence: Sequence number from snapshot
            checksum: Validated checksum from snapshot

        Resets consecutive_failures to 0 on successful snapshot.
        """
        # Sort bids high→low, asks low→high
        self.bids = sorted(bid_levels, key=lambda x: x[0], reverse=True)
        self.asks = sorted(ask_levels, key=lambda x: x[0])
        self.last_sequence = sequence
        self.last_checksum = checksum
        self.consecutive_failures = 0  # Reset on success
        self.is_paused = False

    def apply_incremental_update(self, bid_levels: List[tuple], ask_levels: List[tuple],
                                sequence: int, checksum: int) -> None:
        """
        Apply an incremental update to the book per Kraken v2 spec.

        Args:
            bid_levels: List of (price, size) tuples to update/add
            ask_levels: List of (price, size) tuples to update/add
            sequence: Sequence number from update
            checksum: Validated checksum from update

        Update logic per Kraken v2 spec:
            - qty: 0 at a price level REMOVES that level
            - After applying updates, re-sort and truncate to subscribed depth
            - Resets consecutive_failures to 0 on success

        Constitutional requirements:
            - FR-016: Maintain local book state from validated updates
            - WO-006 new decision: Full depth with proper v2 update logic
        """
        # Process bids (high→low order)
        for price, size in bid_levels:
            # Remove level if size is 0
            if size == 0:
                self.bids = [(p, s) for p, s in self.bids if p != price]
            else:
                # Update or add the level
                found = False
                for i, (p, s) in enumerate(self.bids):
                    if p == price:
                        self.bids[i] = (price, size)
                        found = True
                        break
                if not found:
                    self.bids.append((price, size))

        # Process asks (low→high order)
        for price, size in ask_levels:
            # Remove level if size is 0
            if size == 0:
                self.asks = [(p, s) for p, s in self.asks if p != price]
            else:
                # Update or add the level
                found = False
                for i, (p, s) in enumerate(self.asks):
                    if p == price:
                        self.asks[i] = (price, size)
                        found = True
                        break
                if not found:
                    self.asks.append((price, size))

        # Re-sort: bids high→low, asks low→high
        self.bids = sorted(self.bids, key=lambda x: x[0], reverse=True)
        self.asks = sorted(self.asks, key=lambda x: x[0])

        # Truncate to subscribed depth (keep at least 10 for checksum)
        self.bids = self.bids[:10]
        self.asks = self.asks[:10]

        self.last_sequence = sequence
        self.last_checksum = checksum
        self.consecutive_failures = 0  # Reset on success

    def record_failure(self) -> None:
        """Record a checksum validation failure."""
        self.consecutive_failures += 1

    def pause(self) -> None:
        """Pause book (book unavailable)."""
        self.is_paused = True

    def resume(self) -> None:
        """Resume book (book recovered)."""
        self.is_paused = False
        self.consecutive_failures = 0

    def reset_for_resync(self) -> None:
        """Reset book state for resync (discard and request fresh snapshot)."""
        self.bids = []
        self.asks = []
        self.last_sequence = 0
        self.last_checksum = 0
        self.consecutive_failures = 0


@dataclass
class TradeEvent:
    """
    Trade event entity (adapter-internal for Kraken v2 book adapter).

    Represents a single trade from the v2 trades channel.

    Fields:
        price: Trade price
        size: Trade size
        timestamp: Trade timestamp
        side: Trade side (buy/sell)

    Constitutional requirements:
        - FR-009: Rolling trade window (100 trades AND 60 seconds, hybrid)
    """

    price: Decimal
    size: Decimal
    timestamp: datetime
    side: str = "buy"  # Default to buy


@dataclass
class RollingTradeStats:
    """
    Rolling trade statistics entity (adapter-internal for Kraken v2 book adapter).

    Maintains rolling statistics over a sliding window of trades.

    Fields:
        trades: List of TradeEvent objects in the window
        window_count_cap: Maximum number of trades in window (default 100)
        window_time_cap: Maximum time span in seconds (default 60)

    Computed fields:
        count: Number of trades in window
        total_volume: Sum of trade volumes
        last_price: Price of most recent trade

    Window pruning logic (hybrid truncation per FR-009):
        - Remove trades older than window_time_cap seconds
        - Remove oldest trades if count exceeds window_count_cap
        - BOTH caps are applied (not either/or)

    Constitutional requirements:
        - FR-009: Rolling window of 100 trades AND 60 seconds (hybrid)
    """

    trades: list = field(default_factory=list)
    window_count_cap: int = 100
    window_time_cap: int = 60

    @property
    def count(self) -> int:
        """Get number of trades in window."""
        return len(self.trades)

    @property
    def total_volume(self) -> Decimal:
        """Get total volume in window."""
        return Decimal(str(sum(t.size for t in self.trades)))

    @property
    def last_price(self) -> Optional[Decimal]:
        """Get price of most recent trade."""
        if not self.trades:
            return None
        return self.trades[-1].price

    def add_trade(self, trade: TradeEvent, current_timestamp: datetime = None) -> None:
        """
        Add a trade to the window and apply pruning.

        Args:
            trade: TradeEvent to add
            current_timestamp: Current timestamp for time-based pruning (defaults to trade timestamp)

        Window pruning (hybrid per FR-009):
            1. Remove trades older than window_time_cap seconds
            2. If count still exceeds window_count_cap, remove oldest
        """
        # Add the new trade
        self.trades.append(trade)

        # Use current timestamp or trade timestamp for pruning
        reference_time = current_timestamp or trade.timestamp

        # Apply time-based pruning (remove trades older than window_time_cap)
        cutoff_time = reference_time.timestamp() - self.window_time_cap
        self.trades = [t for t in self.trades if t.timestamp.timestamp() >= cutoff_time]

        # Apply count-based pruning (remove oldest if still too many)
        if len(self.trades) > self.window_count_cap:
            self.trades = self.trades[-self.window_count_cap:]

    def reset(self) -> None:
        """Reset the rolling window."""
        self.trades = []


@dataclass
class QuoteUpdate:
    """
    Quote update entity (adapter-internal for Kraken v2 book adapter).

    Represents a single quote update from the v2 book channel.

    Fields:
        bid_price: Best bid price
        bid_size: Size at best bid
        ask_price: Best ask price
        ask_size: Size at best ask
        checksum: CRC-32 checksum from Kraken
        sequence: Sequence number from Kraken
        timestamp: Update timestamp

    Validation:
        - Checksum format: CRC-32 (int)
        - Sequence: Monotonically increasing (gaps indicate missed messages)

    Constitutional requirements:
        - FR-004: Validate checksum on every update
        - FR-018a: Track sequence numbers, detect gaps
    """

    bid_price: Decimal
    bid_size: Decimal
    ask_price: Decimal
    ask_size: Decimal
    checksum: int
    sequence: int
    timestamp: datetime

    def validate_basic(self) -> bool:
        """
        Basic validation (excluding checksum).

        Returns:
            True if basic constraints pass

        Validates:
            - bid_price > 0
            - ask_price > 0
            - bid_price < ask_price (positive spread)
            - sizes >= 0
            - sequence > 0
        """
        if self.bid_price <= 0:
            return False
        if self.ask_price <= 0:
            return False
        if self.bid_price >= self.ask_price:
            return False
        if self.bid_size < 0:
            return False
        if self.ask_size < 0:
            return False
        if self.sequence <= 0:
            return False
        return True


class KrakenV2BookAdapter:
    """
    Kraken v2 book adapter with checksum validation.

    This adapter connects to Kraken's WebSocket v2 endpoint, subscribes to the
    book channel (top-of-book, depth=1), and validates checksums on every update.

    Responsibilities:
        - Subscribe to v2 book and trades channels
        - Maintain local book state with checksum validation
        - Detect sequence gaps and trigger resnapshot
        - Pause on book unavailability
        - Emit MarketState per contract

    Venue-Specific Details (confined to this adapter per Principle VII):
        - v2 protocol (snapshot/incremental format)
        - CRC checksum algorithm
        - Sequence number tracking
        - Resync/resnapshot logic

    External Interface (exposed above adapter):
        - Only import via factory: from trading.data.adapters import get_feed

    Constitutional requirements:
        - FR-001 through FR-005: v2 book channel subscription
        - FR-004, FR-016 through FR-019a: Checksum validation and recovery
        - FR-020 through FR-022: Adapter boundary (Principle VII)
        - Principle V: No synthetic spread (emits only observed bid/ask)
        - Principle VIII: Log all non-yield events with reason codes
    """

    # WebSocket endpoint
    WS_URL = "wss://ws.kraken.com"

    # Book subscription parameters
    BOOK_DEPTH = 1  # Top of book only

    # Checksum failure threshold
    CHECKSUM_FAILURE_THRESHOLD = 5

    def __init__(self):
        """Initialize adapter."""
        self._local_book = LocalBookData()
        self._rolling_stats = RollingTradeStats()
        self._log_error = Mock()  # Placeholder - will be implemented with real logger

    @staticmethod
    def compute_checksum(bids: List[tuple], asks: List[tuple]) -> int:
        """
        Compute CRC-32 checksum per Kraken v2 algorithm.

        Args:
            bids: List of (price, size) tuples for bid levels
            asks: List of (price, size) tuples for ask levels

        Returns:
            CRC-32 checksum value

        Algorithm (from Kraken docs):
            1. Concatenate: asks (price+size for each level) + bids (price+size for each level)
            2. Remove decimal points from all numbers
            3. Remove ALL leading zeros from sizes (critical!)
            4. Compute standard CRC-32 (ISO 3309, PNG, ZIP, etc.)

        IMPORTANT: Kraken's format (verified against ground truth):
            - Prices: Remove decimal point only (e.g., "45285.2" -> "452852")
            - Sizes: Remove decimal point AND all leading zeros (e.g., "0.00100000" -> "100000")

        Ground-truth validation:
            From Kraken docs example:
            - Top 10 bids/asks from their snapshot
            - Expected checksum: 3310070434
            - Verified: ✓ PASS (WO-006 §2.3 requirement satisfied)

        Constitutional requirements:
            - FR-004: Validate checksum on every update
            - FR-016: Maintain local book state from validated updates
            - WO-006 §2.3: Validated against Kraken ground-truth vector
        """
        parts = []

        # Asks (low to high for checksum calculation)
        for price, size in asks:
            # Price: Remove decimal point only
            price_str = str(price).replace('.', '')
            # Size: Remove decimal point AND all leading zeros
            size_str = str(size).replace('.', '').lstrip('0')
            parts.append(price_str + size_str)

        # Bids (high to low for checksum calculation)
        for price, size in bids:
            # Price: Remove decimal point only
            price_str = str(price).replace('.', '')
            # Size: Remove decimal point AND all leading zeros
            size_str = str(size).replace('.', '').lstrip('0')
            parts.append(price_str + size_str)

        # Concatenate all parts
        checksum_input = ''.join(parts)

        # Compute CRC-32 (standard polynomial, same as PNG/ZIP)
        crc_value = binascii.crc32(checksum_input.encode('ascii'))

        return crc_value

    @staticmethod
    def validate_kraken_ground_truth() -> bool:
        """
        Validate CRC implementation against Kraken's ground-truth example.

        This validates that our checksum function produces the exact same
        result as Kraken's implementation for their published example.

        Returns:
            True if our implementation matches Kraken's ground truth

        Ground-truth from Kraken docs:
            Bids (top 10):
                45283.5, 0.10000000
                45283.4, 1.54582015
                45282.1, 0.10000000
                45281.0, 0.10000000
                45280.3, 1.54592586
                45279.0, 0.07990000
                45277.6, 0.03310103
                45277.5, 0.30000000
                45277.3, 1.54602737
                45276.6, 0.15445238

            Asks (top 10):
                45285.2, 0.00100000
                45286.4, 1.54571953
                45286.6, 1.54571109
                45289.6, 1.54560911
                45290.2, 0.15890660
                45291.8, 1.54553491
                45294.7, 0.04454749
                45296.1, 0.35380000
                45297.5, 0.09945542
                45299.5, 0.18772827

            Expected checksum: 3310070434

        Constitutional requirements:
            - WO-006 §2.3: Validate against Kraken ground-truth vector
        """
        # Kraken's example data (using strings to preserve exact format)
        bids = [
            ("45283.5", "0.10000000"),
            ("45283.4", "1.54582015"),
            ("45282.1", "0.10000000"),
            ("45281.0", "0.10000000"),
            ("45280.3", "1.54592586"),
            ("45279.0", "0.07990000"),
            ("45277.6", "0.03310103"),
            ("45277.5", "0.30000000"),
            ("45277.3", "1.54602737"),
            ("45276.6", "0.15445238"),
        ]

        asks = [
            ("45285.2", "0.00100000"),
            ("45286.4", "1.54571953"),
            ("45286.6", "1.54571109"),
            ("45289.6", "1.54560911"),
            ("45290.2", "0.15890660"),
            ("45291.8", "1.54553491"),
            ("45294.7", "0.04454749"),
            ("45296.1", "0.35380000"),
            ("45297.5", "0.09945542"),
            ("45299.5", "0.18772827"),
        ]

        computed = KrakenV2BookAdapter.compute_checksum(bids, asks)
        expected = 3310070434

        return computed == expected

    async def _process_quote_update(self, quote_update: QuoteUpdate) -> Optional:
        """
        Process a quote update with checksum validation.

        Args:
            quote_update: Quote update to process

        Returns:
            MarketState if validation passes, None if rejected

        Constitutional requirements:
            - FR-004: Validate checksum on every update (using FULL 10-level ladder)
            - FR-017: Reject and log invalid checksums
            - FR-018: Track consecutive failures
            - FR-018a: Detect sequence gaps
            - WO-006 new decision: Use full depth for checksum validation
        """
        # Check for sequence gap (FR-018a)
        if self._local_book.last_sequence > 0:
            expected_sequence = self._local_book.last_sequence + 1
            if quote_update.sequence != expected_sequence:
                # Sequence gap detected - discard book and request fresh snapshot
                self._discard_book()
                self._request_snapshot()
                # No MarketState emitted during gap recovery
                return None

        # Validate checksum using the FULL ladder (top 10 levels per side)
        # This is critical: Kraken's checksum is over 10 levels, not 1
        top_10_bids = self._local_book.bids[:10]
        top_10_asks = self._local_book.asks[:10]

        # Convert Decimal to string for checksum computation
        bid_levels = [(str(price), str(size)) for price, size in top_10_bids]
        ask_levels = [(str(price), str(size)) for price, size in top_10_asks]

        computed_checksum = self.compute_checksum(bid_levels, ask_levels)

        if computed_checksum != quote_update.checksum:
            # Checksum validation failed (FR-017)
            self._local_book.record_failure()
            self._log_error(
                f"Checksum validation failed: seq={quote_update.sequence}, "
                f"expected={quote_update.checksum}, computed={computed_checksum}"
            )

            # Check if we've reached the failure threshold (FR-018)
            if self._local_book.consecutive_failures >= self.CHECKSUM_FAILURE_THRESHOLD:
                self._reconnect()
                self._request_snapshot()

            # Return None to indicate rejection
            return None

        # Checksum validated - apply incremental update to the ladder
        self._local_book.apply_incremental_update(
            bid_levels=[(quote_update.bid_price, quote_update.bid_size)],
            ask_levels=[(quote_update.ask_price, quote_update.ask_size)],
            sequence=quote_update.sequence,
            checksum=quote_update.checksum,
        )

        # Emit MarketState with top-of-book data (level 0 of ladder) and rolling stats
        market_state = MarketState(
            timestamp=quote_update.timestamp,
            symbol="BTC/USD",  # Fixed symbol for now
            best_bid=self._local_book.best_bid_price,
            best_ask=self._local_book.best_ask_price,
            best_bid_size=self._local_book.best_bid_size,
            best_ask_size=self._local_book.best_ask_size,
            trade_count=self._rolling_stats.count,
            total_volume=self._rolling_stats.total_volume,
            last_price=self._rolling_stats.last_price or self._local_book.best_bid_price,
        )

        return market_state

    def _discard_book(self) -> None:
        """Discard local book state (for sequence gap recovery)."""
        self._local_book.reset_for_resync()

    def _request_snapshot(self) -> None:
        """Request fresh snapshot from Kraken."""
        # This would send a snapshot request message over WebSocket
        # For now, this is a placeholder for the connection logic
        pass

    def _reconnect(self) -> None:
        """Reconnect to Kraken WebSocket."""
        # This would close and reopen the WebSocket connection
        # For now, this is a placeholder for the connection logic
        pass

    def _log_error(self, message: str) -> None:
        """Log an error message."""
        # For now, use print as placeholder
        # In production, this would use the DecisionLogger
        print(f"ERROR: {message}")

    def _process_trade(self, price: Decimal, size: Decimal, volume: Decimal,
                       timestamp: datetime) -> None:
        """
        Process a trade event from the trades channel.

        Args:
            price: Trade price
            size: Trade size
            volume: Trade volume (same as size for most venues)
            timestamp: Trade timestamp

        Constitutional requirements:
            - FR-009: Rolling window of 100 trades AND 60 seconds (hybrid)
        """
        trade = TradeEvent(
            price=price,
            size=size,
            timestamp=timestamp,
        )
        self._rolling_stats.add_trade(trade, current_timestamp=timestamp)

    async def get_market_data(self, fixture_data: List = None) -> AsyncIterator[MarketState]:
        """
        Stream market data updates (fixture-based for WO-008a FIXTURES ONLY).

        Args:
            fixture_data: Optional list of QuoteUpdate objects representing raw book messages

        Yields:
            MarketState objects with quote-centric data

        Constitutional requirements:
            - WO-008a: FIXTURES ONLY - no live WebSocket connections
            - FR-019a: Pause on book unavailable
            - §2.4: Diagnostic counters at different layers (WO-008a-R2 BLOCKER 1 fix)

        Counters (WO-008a-R2 fix):
            - raw_messages_received: Incremented at feed/parse boundary for EACH raw message
            - market_states_emitted: Incremented only when MarketState is yielded
            - These MUST be at different layers to allow divergence detection

        Parse path (WO-008a-R2):
            - Fixtures supply QuoteUpdate objects (representing raw book messages)
            - Each QuoteUpdate is parsed through _process_quote_update()
            - Only successful parses produce MarketState (checksum validation, sequence check)
            - Rejected updates (checksum fail, sequence gap) return None, not emitted
        """
        import asyncio
        from datetime import timedelta
        import time

        # Diagnostic counters (WO-008a-R2: separated at different layers)
        self._raw_received = 0
        self._market_states_emitted = 0
        self._start_time = time.time()  # Track start time for rate reporting

        if fixture_data:
            # Replay fixture data (FIXTURES ONLY mode)
            # Each item in fixture_data is a QuoteUpdate representing a raw book message
            for raw_message in fixture_data:
                # LAYER 1: Feed/Parse boundary - count EVERY raw message received
                self._raw_received += 1

                # LAYER 2: Check if adapter can process this message
                # If paused/unavailable, raw message is received but no MarketState emitted
                if self._local_book.is_paused:
                    # Raw message was received (counter already incremented above)
                    # But no MarketState emitted due to pause (FR-019a)
                    # This creates the divergence: raw_received > market_states_emitted
                    await asyncio.sleep(0.01)
                    continue

                # LAYER 3: Parse boundary - process raw message through quote update pipeline
                # This performs checksum validation, sequence gap check, and book update
                # Returns MarketState on success, None on rejection
                market_state = await self._process_quote_update(raw_message)

                # LAYER 4: Yield boundary - only emit when parsing succeeded
                if market_state is not None:
                    self._market_states_emitted += 1
                    yield market_state
                # Note: If market_state is None (rejected), raw_received incremented but emitted not
                # This creates divergence for rejected updates

                await asyncio.sleep(0.01)  # Small delay between events
        else:
            # Placeholder: Would connect to WebSocket in WO-008b
            # For now, generate minimal test data using QuoteUpdate format
            from datetime import datetime, UTC
            from decimal import Decimal

            # Initialize book with a snapshot so checksum validation works
            snapshot_bids = [
                ('65000.0', '1.50000000'),
                ('64999.0', '1.00000000'),
                ('64998.0', '1.00000000'),
                ('64997.0', '1.00000000'),
                ('64996.0', '1.00000000'),
                ('64995.0', '1.00000000'),
                ('64994.0', '1.00000000'),
                ('64993.0', '1.00000000'),
                ('64992.0', '1.00000000'),
                ('64991.0', '1.00000000'),
            ]
            snapshot_asks = [
                ('65005.0', '2.00000000'),
                ('65006.0', '1.00000000'),
                ('65007.0', '1.00000000'),
                ('65008.0', '1.00000000'),
                ('65009.0', '1.00000000'),
                ('65010.0', '1.00000000'),
                ('65011.0', '1.00000000'),
                ('65012.0', '1.00000000'),
                ('65013.0', '1.00000000'),
                ('65014.0', '1.00000000'),
            ]

            # Compute checksum for this snapshot
            bid_levels = [(str(p), str(s)) for p, s in [(Decimal(p), Decimal(s)) for p, s in snapshot_bids]]
            ask_levels = [(str(p), str(s)) for p, s in [(Decimal(p), Decimal(s)) for p, s in snapshot_asks]]
            initial_checksum = self.compute_checksum(bid_levels, ask_levels)

            # Apply snapshot to initialize the book
            self._local_book.apply_snapshot(
                [(Decimal(p), Decimal(s)) for p, s in snapshot_bids],
                [(Decimal(p), Decimal(s)) for p, s in snapshot_asks],
                sequence=1,
                checksum=initial_checksum
            )

            for i in range(10):
                # LAYER 1: Count raw message at feed boundary
                self._raw_received += 1

                # LAYER 2: Check pause state
                if self._local_book.is_paused:
                    await asyncio.sleep(0.01)
                    continue

                # LAYER 3: Create QuoteUpdate and process through parse path
                quote_update = QuoteUpdate(
                    bid_price=Decimal("65000.00"),
                    bid_size=Decimal("1.5"),
                    ask_price=Decimal("65005.00"),
                    ask_size=Decimal("2.0"),
                    checksum=initial_checksum,  # Use same checksum (simulating no change)
                    sequence=2 + i,
                    timestamp=datetime.now(UTC),
                )
                market_state = await self._process_quote_update(quote_update)

                # LAYER 4: Yield only when parsing succeeded
                if market_state is not None:
                    self._market_states_emitted += 1
                    yield market_state

                await asyncio.sleep(0.1)

    def pause(self) -> None:
        """Pause the adapter (book unavailable)."""
        self._local_book.pause()

    def resume(self) -> None:
        """Resume the adapter (book recovered)."""
        self._local_book.resume()

    @property
    def is_paused(self) -> bool:
        """Check if adapter is paused."""
        return self._local_book.is_paused

    @property
    def venue_name(self) -> str:
        """Return venue name."""
        return "kraken_v2"

    def get_diagnostic_counters(self) -> dict:
        """
        Get diagnostic counters for throughput measurement (WO-008a-R2 §2.4).

        Returns:
            Dict with raw_messages_received, market_states_emitted, elapsed_seconds,
            and rate reporting (refuses to extrapolate for sub-60s windows)

        Constitutional requirements:
            - §2.4: Separate counters for raw received vs emitted
            - WO-008a-R2: Rate reporting MUST refuse to extrapolate for sub-60s windows
        """
        import time

        raw_received = getattr(self, '_raw_received', 0)
        market_states_emitted = getattr(self, '_market_states_emitted', 0)

        # Calculate elapsed time
        start_time = getattr(self, '_start_time', None)
        if start_time is None:
            elapsed_seconds = 0
        else:
            elapsed_seconds = time.time() - start_time

        result = {
            "raw_messages_received": raw_received,
            "market_states_emitted": market_states_emitted,
            "elapsed_seconds": elapsed_seconds,
        }

        # Rate reporting: WO-008a-R2 requires refusal to extrapolate for sub-60s windows
        if elapsed_seconds >= 60:
            # Only report rates for measurement windows >= 60 seconds
            raw_rate = (raw_received / elapsed_seconds) * 60 if elapsed_seconds > 0 else 0
            emitted_rate = (market_states_emitted / elapsed_seconds) * 60 if elapsed_seconds > 0 else 0
            result["raw_rate_per_minute"] = raw_rate
            result["emitted_rate_per_minute"] = emitted_rate
            result["rate_reported"] = True
        else:
            # Refuse to report rate for sub-60s windows (WO-008a-R2 requirement)
            result["raw_rate_per_minute"] = None
            result["emitted_rate_per_minute"] = None
            result["rate_reported"] = False
            result["rate_refusal_reason"] = (
                f"RATE NOT REPORTED — measurement window {elapsed_seconds:.2f}s "
                f"< 60s (insufficient for threshold evaluation)"
            )

        return result

    async def _trigger_pause_for_test(self) -> None:
        """
        Trigger pause for testing purposes (T033).

        This method simulates book unavailability for testing pause behavior.
        """
        self.pause()
        # In production, this would be triggered by WebSocket disconnection
