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
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict
from dataclasses import dataclass, field
import enum
import binascii
import logging

from trading.data.market_state import MarketState


logger = logging.getLogger(__name__)


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
        self.is_paused = False
        # WO-008b-A1 §1: consecutive_failures is NOT cleared here. Under
        # apply-then-validate ordering, APPLYING a frame no longer means it was
        # VALID — validation happens afterwards, over the post-update ladder.
        # The counter is cleared only on a confirmed checksum match.

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
        # WO-008b-A1 §1: see apply_snapshot — applying is not validating.

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
        """
        Discard book state for resync.

        WO-008b-A1 §1 — consecutive_failures is DELIBERATELY PRESERVED.

        It previously reset to 0 here, which meant the recovery path wiped the
        very counter that gates it: every failure discarded the book, the discard
        zeroed the count, and FR-018's "5 consecutive failures trigger
        reconnection" could therefore NEVER fire. The threshold was unreachable
        by construction (rule 0.1d).

        The counter now survives the discard and is cleared only by a confirmed
        checksum match, which is what "consecutive" requires.
        """
        self.bids = []
        self.asks = []
        self.last_sequence = 0
        self.last_checksum = 0


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

    Represents ONE `data` element parsed from a raw Kraken v2 book frame.

    WO-008b-A1 §5 REDESIGN. Previously this held four top-of-book scalars plus a
    `sequence` field. Two problems:

      1. `sequence` modelled a protocol element the Kraken v2 PUBLIC book channel
         DOES NOT TRANSMIT. Fixtures supplied synthetic values, so "sequence-gap
         detection proven" was a guarantee attached to a fiction. Removed per
         amended FR-018a(a).
      2. Four scalars cannot represent a book frame. Kraken sends a LADDER of
         {price, qty} levels, and the CRC32 is computed over the top 10 per side.
         A top-of-book-only entity made a correct checksum impossible.

    Fields:
        symbol: Instrument, e.g. "BTC/USD"
        message_type: TYPE_SNAPSHOT or TYPE_UPDATE
        bids: [(Decimal price, Decimal qty), ...] as sent
        asks: [(Decimal price, Decimal qty), ...] as sent
        checksum: CRC32 over the top 10 levels per side of the POST-update book
        timestamp: SERVER-sent timestamp (never client-generated)

    Constitutional requirements:
        - FR-004 / FR-018a(c): checksum validated on EVERY update
        - FR-018a(b): checksum defined over the POST-update book state
    """

    TYPE_SNAPSHOT = "snapshot"
    TYPE_UPDATE = "update"

    symbol: str
    message_type: str
    bids: List[tuple]
    asks: List[tuple]
    checksum: int
    timestamp: datetime

    @property
    def is_snapshot(self) -> bool:
        """True when this frame replaces the book rather than amending it."""
        return self.message_type == self.TYPE_SNAPSHOT

    def validate_basic(self) -> bool:
        """
        Basic structural validation (excluding checksum).

        Validates:
            - message_type is snapshot or update
            - symbol present
            - every price > 0 and every qty >= 0 (qty == 0 is a DELETION, legal)
            - a snapshot carries at least one level per side
        """
        if self.message_type not in (self.TYPE_SNAPSHOT, self.TYPE_UPDATE):
            return False
        if not self.symbol:
            return False
        for price, qty in list(self.bids) + list(self.asks):
            if price <= 0:
                return False
            if qty < 0:
                return False
        if self.is_snapshot and (not self.bids or not self.asks):
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

    # WebSocket endpoint (WO-008b-A1 §6 D4: was "wss://ws.kraken.com", the v1
    # endpoint, in a module named kraken_v2_book. NO connection is opened here —
    # transport is WO-008b-A2.)
    WS_URL = "wss://ws.kraken.com/v2"

    # Book subscription parameters.
    # WO-008b-A1 §1: pinned to 10 per amended FR-018a(e). Kraken accepts only
    # 10/25/100/500/1000; the previous value of 1 was ILLEGAL at the venue and
    # could never hold the 10 levels per side the CRC32 is computed over.
    BOOK_DEPTH = 10

    # Checksum failure threshold
    CHECKSUM_FAILURE_THRESHOLD = 5

    # Venue-mode provenance values (WO-008b-A1 §4).
    MODE_FIXTURE = "fixture"
    MODE_LIVE = "live"
    VENUE_FIXTURE = "kraken_fixture"
    VENUE_LIVE = "kraken_mainnet"

    def __init__(self, mode: str = MODE_FIXTURE):
        """
        Initialize adapter.

        Args:
            mode: MODE_FIXTURE (default) or MODE_LIVE. Determines the venue
                  provenance reported to the decision log. WO-008b-A1 §4: a
                  fixture replay and a live run MUST be distinguishable in the
                  audit trail (Principle VIII).

        Note: MODE_LIVE only labels provenance. It opens NO connection —
        transport is WO-008b-A2.
        """
        if mode not in (self.MODE_FIXTURE, self.MODE_LIVE):
            raise ValueError(
                f"Unknown adapter mode {mode!r}. "
                f"Expected {self.MODE_FIXTURE!r} or {self.MODE_LIVE!r}."
            )
        self._local_book = LocalBookData()
        self._rolling_stats = RollingTradeStats()
        self._mode = mode
        # WO-008b-A1 §1: no-emission window. True from a checksum failure until a
        # fresh snapshot is applied AND its checksum validates (FR-018a(d)).
        self._awaiting_resync = False
        logger.info(
            "[kraken_v2_book] adapter initialised mode=%s venue=%s",
            self._mode, self.venue_name,
        )

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

    # ────────────────────────────────────────────────────────────────────
    # PARSE PATH (WO-008b-A1 §5). Raw Kraken v2 wire frame -> QuoteUpdate.
    # This code path had NEVER been under test: fixtures previously supplied
    # pre-parsed QuoteUpdate objects, so the parser was never exercised and the
    # fixtures drifted toward the implementation instead of the protocol.
    # NO NETWORK: this converts an already-received dict. Transport is A2.
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_levels(raw_levels) -> List[tuple]:
        """
        Convert Kraken v2 [{"price": ..., "qty": ...}, ...] into tuples.

        Parsed from STRING form to preserve exact decimal precision: the checksum
        is computed over the digits as sent, so a float round-trip would corrupt it.
        """
        levels = []
        for level in raw_levels or []:
            levels.append((Decimal(str(level["price"])), Decimal(str(level["qty"]))))
        return levels

    def _parse_book_frame(self, raw_frame: dict) -> List[QuoteUpdate]:
        """
        Parse a raw Kraken v2 book frame into QuoteUpdate objects.

        Kraken v2 envelope:
            {"channel": "book", "type": "snapshot"|"update",
             "data": [{"symbol": ..., "bids": [{"price","qty"}], "asks": [...],
                       "checksum": int, "timestamp": ...}]}

        Returns an EMPTY LIST for anything that is not a book frame — subscription
        acknowledgements, heartbeats, status messages. Transport chatter is not
        market data and must never reach the book.

        Cite: https://docs.kraken.com/api/docs/websocket-v2/book/
        """
        if not isinstance(raw_frame, dict):
            logger.debug("[kraken_v2_book] ignoring non-dict frame: %s", type(raw_frame))
            return []

        if raw_frame.get("channel") != "book":
            return []

        message_type = raw_frame.get("type")
        if message_type not in (QuoteUpdate.TYPE_SNAPSHOT, QuoteUpdate.TYPE_UPDATE):
            logger.debug("[kraken_v2_book] book frame with unknown type: %r", message_type)
            return []

        updates: List[QuoteUpdate] = []
        for element in raw_frame.get("data", []) or []:
            try:
                update = QuoteUpdate(
                    symbol=element["symbol"],
                    message_type=message_type,
                    bids=self._parse_levels(element.get("bids")),
                    asks=self._parse_levels(element.get("asks")),
                    checksum=int(element["checksum"]),
                    timestamp=element.get("timestamp"),
                )
            except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
                self._log_error(f"Malformed book frame element: {exc}")
                continue

            if not update.validate_basic():
                self._log_error(
                    f"Book frame element failed basic validation: "
                    f"symbol={update.symbol!r} type={update.message_type!r}"
                )
                continue

            updates.append(update)

        return updates

    def _current_ladder_strings(self) -> tuple:
        """Return (bid_levels, ask_levels) as strings for checksum computation."""
        bid_levels = [(str(p), str(q)) for p, q in self._local_book.bids[:10]]
        ask_levels = [(str(p), str(q)) for p, q in self._local_book.asks[:10]]
        return bid_levels, ask_levels

    def _enter_resync(self, reason: str) -> None:
        """
        Begin the no-emission window (FR-018a(d)).

        Discards the local book and requests a fresh snapshot. NO MarketState may
        be emitted until that snapshot is applied AND its checksum validates. An
        unverified book must not price anything (Principle V).
        """
        self._awaiting_resync = True
        self._log_error(
            f"CHECKSUM_RESYNC: {reason}. Book discarded; "
            f"no MarketState until resync validates."
        )
        self._discard_book()
        self._request_snapshot()

    async def _process_quote_update(self, quote_update: QuoteUpdate) -> Optional:
        """
        Process a quote update, validating the checksum AFTER applying it.

        WO-008b-A1 §1 — ORDERING IS THE GUARANTEE, not an implementation detail.
        Kraken defines the CRC32 over the POST-update book state, so the update is
        applied FIRST and the resulting ladder is what gets checksummed. The prior
        implementation validated the PRE-update book, which would have mismatched
        on every incremental against a real feed.

        On mismatch the APPLIED STATE is invalidated — not merely the incoming
        message — and the no-emission window opens.

        Constitutional requirements:
            - FR-018a(b): validate AFTER applying; mismatch invalidates applied state
            - FR-018a(c): validate on EVERY update, never periodically
            - FR-018a(d): emit nothing until a fresh snapshot validates
            - FR-017: reject AND LOG invalid checksums
        """
        if quote_update.is_snapshot:
            self._local_book.apply_snapshot(
                bid_levels=quote_update.bids,
                ask_levels=quote_update.asks,
                sequence=0,
                checksum=quote_update.checksum,
            )
        else:
            if self._awaiting_resync:
                # FR-018a(d): the book is unverified. Incremental updates cannot
                # be trusted to repair it, and nothing may be emitted from it.
                return None
            self._local_book.apply_incremental_update(
                bid_levels=quote_update.bids,
                ask_levels=quote_update.asks,
                sequence=0,
                checksum=quote_update.checksum,
            )

        # FR-018a(b),(c): checksum over the POST-update ladder, on EVERY update.
        bid_levels, ask_levels = self._current_ladder_strings()
        computed_checksum = self.compute_checksum(bid_levels, ask_levels)

        if computed_checksum != quote_update.checksum:
            self._local_book.record_failure()
            self._log_error(
                f"Checksum validation failed: symbol={quote_update.symbol} "
                f"type={quote_update.message_type} "
                f"expected={quote_update.checksum}, computed={computed_checksum}"
            )
            if self._local_book.consecutive_failures >= self.CHECKSUM_FAILURE_THRESHOLD:
                self._reconnect()
            self._enter_resync("post-update checksum mismatch")
            return None

        # Confirmed valid: this is the ONLY place the failure streak is cleared.
        self._local_book.consecutive_failures = 0

        # A validated SNAPSHOT is the only thing that closes the window.
        if quote_update.is_snapshot and self._awaiting_resync:
            self._awaiting_resync = False
            logger.info(
                "[kraken_v2_book] resync complete: fresh snapshot validated; "
                "emission resumed"
            )

        return MarketState(
            timestamp=(
                quote_update.timestamp
                if isinstance(quote_update.timestamp, datetime)
                else datetime.now(UTC)
            ),
            symbol=quote_update.symbol,
            best_bid=self._local_book.best_bid_price,
            best_ask=self._local_book.best_ask_price,
            best_bid_size=self._local_book.best_bid_size,
            best_ask_size=self._local_book.best_ask_size,
            trade_count=self._rolling_stats.count,
            total_volume=self._rolling_stats.total_volume,
            last_price=self._rolling_stats.last_price or self._local_book.best_bid_price,
        )

    async def process_raw_frame(self, raw_frame: dict) -> List:
        """
        Full parse path: raw Kraken v2 frame -> MarketStates.

        This is the shared entry point A2's WebSocket transport will hand frames
        to. Non-book frames yield an empty list rather than an error.
        """
        states = []
        for update in self._parse_book_frame(raw_frame):
            market_state = await self._process_quote_update(update)
            if market_state is not None:
                states.append(market_state)
        return states

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
        """
        Log an error message.

        WO-008b-A1 §2: this was shadowed by `self._log_error = Mock()` in
        __init__ from commit 71eb901 through 43ca600, so every checksum-failure
        log was swallowed by a test double — in FIXTURE mode as well as live.
        FR-017 ("reject AND LOG invalid checksums") was unfulfilled in the
        shipped system for that entire period. The Mock is gone; this is now the
        only definition and it writes to the real logger.
        """
        logger.error("[kraken_v2_book] %s", message)

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
        Stream market data updates from RAW KRAKEN v2 FRAMES.

        WO-008b-A1 §5: `fixture_data` is now a list of RAW v2 dict envelopes —
        what the WebSocket actually delivers — not pre-parsed QuoteUpdate objects.
        Every frame goes through the real parse path, so the parser is under test.

        NO NETWORK. Frames are supplied by the caller; transport is WO-008b-A2.

        Args:
            fixture_data: list of raw Kraken v2 frames (dicts).

        Yields:
            MarketState objects with quote-centric data.

        Counters (WO-008a-R2 §2.4, semantics preserved):
            - raw_messages_received: incremented at the feed boundary for EVERY
              raw frame, before any filtering, validation or pause check
            - market_states_emitted: incremented only at the yield boundary
            - the two sit at different layers so divergence is observable

        Constitutional requirements:
            - FR-019a: pause emits no MarketStates
            - FR-018a(d): an unverified book emits nothing until resync validates
        """
        import asyncio
        import time

        self._raw_received = 0
        self._market_states_emitted = 0
        self._start_time = time.time()

        if fixture_data is None:
            raise ValueError(
                "get_market_data requires fixture_data (raw Kraken v2 frames). "
                "Live transport is WO-008b-A2 and is deliberately not implemented "
                "here — this adapter will NOT silently fabricate market data."
            )

        for raw_frame in fixture_data:
            # LAYER 1: feed boundary — count EVERY raw frame received.
            self._raw_received += 1

            # LAYER 2: pause check (FR-019a). The frame was received and counted,
            # but nothing is emitted while paused — this is the divergence.
            if self._local_book.is_paused:
                await asyncio.sleep(0.01)
                continue

            # LAYER 3: parse boundary — raw frame through the REAL parse path.
            market_states = await self.process_raw_frame(raw_frame)

            # LAYER 4: yield boundary.
            for market_state in market_states:
                self._market_states_emitted += 1
                yield market_state

            await asyncio.sleep(0.01)

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
    def mode(self) -> str:
        """Return the adapter mode (fixture or live)."""
        return self._mode

    @property
    def venue_name(self) -> str:
        """
        Return venue name, distinguishing LIVE from FIXTURE provenance.

        WO-008b-A1 §4: this previously returned the constant "kraken_v2" for both
        modes, so a live mainnet run and a fixture replay were INDISTINGUISHABLE
        in the decision log. Captured data whose provenance cannot be established
        is not honest evidence (Principle VIII).
        """
        return self.VENUE_LIVE if self._mode == self.MODE_LIVE else self.VENUE_FIXTURE

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


# --- WO-010 §5: self-registration ---------------------------------------
from trading.data.adapters.registry import register  # noqa: E402


@register("kraken_v2")
def _build_kraken_v2(decision_logger=None) -> "KrakenV2BookAdapter":
    """Builder invoked by the registry when DATA_SOURCE=kraken_v2.

    FIXTURES ONLY — live WebSocket transport is held under WO-008b-A.
    """
    return KrakenV2BookAdapter()
