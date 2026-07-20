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
import json
import random

from trading.data.market_state import MarketState


logger = logging.getLogger(__name__)


class CircuitBreakerTripped(RuntimeError):
    """
    WO-014b-2 §2. Raised when reconnect reopen attempts exceed the circuit-breaker
    threshold within its rolling window: the venue is presumed gone and the capture
    STOPS LOUDLY (Ruling B) rather than retrying forever into an undisclosed multi-hour
    hole — the dishonest-evidence failure this project refuses. Carries its own forensic
    tail so the artifact explains itself: .trip_time, .reconnect_ladder (every attempt with
    timestamp + delay + error), and .last_validated_book (last checksum-good top-of-book).
    """

    def __init__(self, message, *, trip_time=None, reconnect_ladder=None,
                 last_validated_book=None):
        super().__init__(message)
        self.trip_time = trip_time
        self.reconnect_ladder = reconnect_ladder or []
        self.last_validated_book = last_validated_book


@dataclass
class LagSampleRecord:
    """
    WO-014c-1 §B.1. Self-reporting record for the event-loop LAG sampler — the PRIMARY
    starvation discriminator. All timestamps are time.monotonic() (WO-014c-1 §A.2 shared
    clock; never wall clock — the whole discrimination is a cross-record correlation).

    The record is designed so a STARVED-QUIET sampler SELF-REPORTS: silence becomes a
    POSITIVE signal, never "healthy because quiet." It carries not just the samples but the
    completeness accounting — expected vs actual sample count, missed count, and the gap
    timestamps where the sampler itself was starved — so a gappy run is legible as gappy
    (WO-014c-1 §A.3 / branch 5: gappy -> VOID for the quantitative verdict, while the gaps
    remain reported evidence that can NOMINATE the starvation hypothesis).

    Fields:
        interval_s          : intended sampling cadence (s)
        started_monotonic   : monotonic() at first sample loop entry
        ended_monotonic     : monotonic() at sampler stop/cancel
        samples             : list of (monotonic_ts, lag_s) — lag_s is the sleep OVERRUN
                              (actual_interval - interval_s); > 0 means the loop scheduled
                              the sentinel late.
        gaps                : list of (gap_start_ts, gap_end_ts, gap_duration_s) — wake
                              intervals that overran by >= LAG_GAP_FACTOR, i.e. WHERE
                              intended wakes were missed, identifiable by timestamp.
    """

    interval_s: float
    started_monotonic: float = 0.0
    ended_monotonic: float = 0.0
    samples: list = field(default_factory=list)
    gaps: list = field(default_factory=list)

    @property
    def actual_samples(self) -> int:
        return len(self.samples)

    @property
    def expected_samples(self) -> int:
        span = self.ended_monotonic - self.started_monotonic
        return int(span / self.interval_s) if self.interval_s > 0 and span > 0 else 0

    @property
    def missed_samples(self) -> int:
        return max(0, self.expected_samples - self.actual_samples)

    @property
    def missed_fraction(self) -> float:
        exp = self.expected_samples
        return (self.missed_samples / exp) if exp > 0 else 0.0


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

    # WO-008b-A2 §2.2: Kraken v2 uses slash-separated ISO-style symbols.
    # (v1 used "XBT/USD"; v2 documents "BTC/USD".)
    # Cite: https://docs.kraken.com/api/docs/websocket-v2/book/
    BOOK_SYMBOL = "BTC/USD"

    # Checksum failure threshold
    CHECKSUM_FAILURE_THRESHOLD = 5

    # ── WO-014b-2 §2: reconnect backoff + circuit breaker ────────────────────
    # Figures are DECLARED ENGINEERING JUDGMENT, not a citation: Kraken's WS
    # connection/subscription rate limits are DOCUMENTED SILENCE on the reachable
    # official pages (evidence/WO-014b-2/rate_limits_research.txt; rule 0.1e). All are
    # instance-overridable (see __init__) so tests can drive them at ms scale.
    RECONNECT_BACKOFF_BASE_SECONDS = 1.0     # first retry delay
    RECONNECT_BACKOFF_FACTOR = 2.0           # 1, 2, 4, 8, 16, ... before the cap
    RECONNECT_BACKOFF_CAP_SECONDS = 30.0     # capped so a recovered venue reconnects promptly
    # Circuit breaker: a DURATION breaker (WO-014b-2, Proposal B, ruled). It trips when the
    # continuous-failure streak exceeds this many seconds of elapsed wall-clock from the
    # first failed reopen — the venue is presumed gone, the run STOPS loudly. T directly
    # expresses the only question the breaker answers — "how long do we try before
    # concluding the venue is gone?" — instead of encoding it indirectly through an attempt
    # count, expected delay, and jitter (the count/rolling-window form had a WINDOW >= MAX x
    # cap subtlety that made its own worst case marginal-by-construction, so it was rejected).
    #
    # T = 600s (10 min) is DECLARED ENGINEERING JUDGMENT — Kraken publishes no keepalive/
    # reconnect limit (documented silence, evidence/WO-014b-2/rate_limits_research.txt, rule
    # 0.1e). Derivation: routine unplanned Kraken interruptions (network events, brief WS
    # drops) resolve in seconds to a few minutes; ~10 min clears ordinary hiccups with margin
    # while bounding a truly-gone venue to a DISCLOSED ~10-20 min gap (carried by the forensic
    # tail + retained partial capture) rather than a silent multi-hour hole. Unknown without
    # operational history; conservative and revisable once the 24h run yields data.
    # Attempt rate is now EMERGENT from T: at cap 30s with full jitter the expected delay is
    # ~15s, so ~40 attempts across 600s ~= 4/min — well under any plausible venue limit.
    RECONNECT_MAX_FAILURE_SECONDS = 600.0

    # ── WO-014b-2 §1.1 / §1.2: keepalive (application layer) ─────────────────
    # Kraken emits a heartbeat ~1/s (observed: 10 in a 70-frame sample, WO-008b-B) but
    # DOCUMENTS NO mandatory application ping interval or keepalive timeout (the ping page
    # is silent — rule 0.1e; evidence/WO-014/lifecycle_proposal.txt). These are therefore
    # DECLARED ENGINEERING JUDGMENT, not cited limits, and are instance-overridable.
    #   - Probe every 5s with an application ping ({"method":"ping"} -> pong): active
    #     liveness independent of data flow; the pong is a frame that refreshes the
    #     absence clock below.
    #   - Declare the connection dead after 10s with NO frame of any kind (heartbeat,
    #     data, or pong): ~10x the observed ~1s heartbeat cadence and two ping cycles —
    #     enough to tolerate scheduling jitter, and detected at the APPLICATION layer
    #     rather than waiting on the library's ~20s PROTOCOL ping whose timeout threw the
    #     1011. (The protocol-layer ping params are §1.3 — the checkpoint seam.)
    APP_PING_INTERVAL_SECONDS = 5.0
    HEARTBEAT_ABSENCE_TIMEOUT_SECONDS = 10.0

    # ── WO-014b-2 §1.3: PROTOCOL-LEVEL ping (the websockets library's own WS PING/PONG
    # keepalive — the layer BELOW the application ping of §1.2, and the one that threw the
    # 742s `1011 keepalive ping timeout` that ended WO-008b-B). Library defaults (20s/20s)
    # produced that 1011. Kraken's docs are SILENT on protocol-ping expectations — the ping
    # page documents ONLY the application ping and explicitly calls it "an application level
    # ping, distinct from the protocol-level ping in the WebSockets standard"
    # (evidence/WO-014/lifecycle_proposal.txt; rule 0.1e) — so these are DECLARED ENGINEERING
    # JUDGMENT, same standard as T=600s.
    #   WS_PING_INTERVAL = 20s: keep SENDING WS-level pings (cheap; keeps proxies/intermediaries
    #     from idling a long-lived connection). We do NOT disable the ping.
    #   WS_PING_TIMEOUT = None: do NOT let the LIBRARY close the connection on a missed/late
    #     PONG. That library close (1011) is the exact mechanism that ended WO-008b-B, and BOTH
    #     open hypotheses — Kraken not PONGing WS-level pings, and event-loop starvation at
    #     ~1544 msg/min delaying pong servicing — make a fixed protocol timeout fire spuriously.
    #     Connection LIVENESS is instead decided at the APPLICATION layer by heartbeat-absence
    #     detection (§1.1: 10s over Kraken's own ~1/s server heartbeat + data + our app pongs)
    #     and the app ping/pong (§1.2) — that is the named replacing signal, not an implied one.
    #     Belt-and-suspenders: if a protocol-level close still arrives (venue/proxy-initiated),
    #     §1.3's venue-close path routes it into reconnect, not a capture-ending crash.
    WS_PING_INTERVAL_SECONDS = 20.0
    WS_PING_TIMEOUT = None

    # ── WO-014c-1 §B.1: event-loop LAG sampler (PRIMARY starvation discriminator) ──
    # Figures declared in WO-014c-1 Phase A (evidence/WO-014c-1/thresholds_and_branches.txt),
    # declared engineering judgment under documented silence, anchored to ~26 msg/s (~38ms/frame).
    LAG_SAMPLE_INTERVAL_SECONDS = 0.1   # 100ms: ~10 samples/s; fine enough for sub-second bursts
    LAG_GAP_FACTOR = 2.0                # a wake overrunning to >= 2x the interval missed >=1 wake
    # "Gappy -> VOID" (branch 5): >10% of expected samples missing means the sampler was itself
    # starved enough that its surviving record is a biased sample — the quantitative verdict is
    # VOID (the gap timestamps remain reported evidence).
    INSTRUMENTS_GAPPY_VOID_FRACTION = 0.10

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
        # WO-014b-1: full-reconnect request flag. Set by _reconnect() (reached at 5
        # consecutive checksum failures, FR-018) and consumed by the transport, which
        # closes/reopens the socket. Mirrors _request_snapshot's committed flag
        # pattern (design B). A set-but-never-consumed flag is silent non-action and
        # the transport fails loudly on it (RECONNECT_FLAG_STRANDED).
        self._pending_reconnect = False
        # WO-014b-2 §2: reconnect backoff + circuit-breaker state. Constants copied to
        # instance attributes so tests can override them at ms scale without monkeypatching.
        self._reconnect_backoff_base = self.RECONNECT_BACKOFF_BASE_SECONDS
        self._reconnect_backoff_factor = self.RECONNECT_BACKOFF_FACTOR
        self._reconnect_backoff_cap = self.RECONNECT_BACKOFF_CAP_SECONDS
        self._reconnect_max_failure_seconds = self.RECONNECT_MAX_FAILURE_SECONDS  # duration breaker T
        self._reconnect_ladder = []          # forensic: per-attempt {attempt,at,delay_s,error}
        self._last_validated_book = None     # forensic: last checksum-validated top-of-book
        self._reconnect_sleep = None         # test hook; defaults to asyncio.sleep
        self._reconnect_jitter = None        # test hook; defaults to random.random
        self.capture_terminated = None       # set when the breaker STOPS a live capture
        # WO-014b-2 §1.1/§1.2: keepalive (instance-overridable for ms-scale tests).
        self._heartbeat_absence_timeout = self.HEARTBEAT_ABSENCE_TIMEOUT_SECONDS
        self._app_ping_interval = self.APP_PING_INTERVAL_SECONDS
        self._ping_seq = 0                   # req_id for application pings
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
            # WO-008b-A3 §1.1: values arriving as Decimal (parse_float/parse_int)
            # are used AS-IS so the venue's digits survive. Decimal(str(x)) on a
            # float would re-render and corrupt the checksum input.
            price, qty = level["price"], level["qty"]
            levels.append((
                price if isinstance(price, Decimal) else Decimal(str(price)),
                qty if isinstance(qty, Decimal) else Decimal(str(qty)),
            ))
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
        # WO-014b-2 §2: remember the last checksum-VALIDATED top-of-book, for the circuit
        # breaker's forensic tail (the last-known-good state before a fatal disconnect).
        self._last_validated_book = {
            "best_bid": str(self._local_book.best_bid_price),
            "best_ask": str(self._local_book.best_ask_price),
            "last_checksum": self._local_book.last_checksum,
            "at": datetime.now(UTC).isoformat(),
        }

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
        """
        Signal the transport to obtain a FRESH book snapshot by RESUBSCRIBING.

        WO-014 §2.1 (design B). The v2 book channel documents NO snapshot re-request
        method (https://docs.kraken.com/api/docs/websocket-v2/book/ is silent on it);
        the documented path is unsubscribe+subscribe, which delivers a fresh snapshot.
        This sets a flag the transport (get_live_market_data) consumes to send that
        resubscribe on the live socket. Setting the flag is a REAL action, not a no-op
        (rule 0.1g — this method was `pass` and latched emission off for 48 of
        WO-008b-B's 60 minutes). Fixture-level only; the isolated live re-run confirms
        Kraken actually responds with a snapshot.
        """
        self._pending_resubscribe = True

    def _reconnect(self) -> None:
        """
        Request a full transport reconnect: close the live socket and reopen it,
        then resubscribe for a fresh snapshot.

        WO-014b-1 (rule 0.1i). This was `pass` from Phases 1-3 through WO-008b-A1b.
        The FR-018 5-consecutive-checksum-failure recovery therefore CALLED this and
        NOTHING HAPPENED — WO-008b-B ran sixty minutes with a no-op reconnect. The
        A1b certification proved the counter reaches five and this method is CALLED;
        it did not — could not — prove recovery, because the callee did nothing. The
        proof terminated at a call-site. That gap is exactly why rule 0.1i exists.

        Design mirrors _request_snapshot's committed flag pattern (approved design B):
        setting a flag the transport (get_live_market_data) consumes is a REAL action,
        not a no-op (rule 0.1g). _reconnect is called synchronously from
        _process_quote_update (the checksum-failure branch), which holds no socket —
        only the transport does. The transport closes/reopens and hands off to
        _maybe_resubscribe (the committed Phase 2.1 producer) for the fresh
        subscription. Setting a flag keeps this method synchronous: no private-method
        async signature change (0.1a).

        WATCHDOG: a flag the transport never consumes is silent non-action — the very
        defect this method's history embodies, in a new costume. The transport raises
        RECONNECT_FLAG_STRANDED if the flag survives a loop boundary unconsumed
        (threshold: zero-iteration latency; see get_live_market_data).

        HONEST FIXTURE LIMIT: the close/reopen and the resubscribe SEND are exercised
        by simulated transport (evidence/WO-014b/reconnect_to_effect.txt). Only the
        isolated live re-run confirms Kraken responds to a fresh connection + subscribe
        with a fresh snapshot.
        """
        self._pending_reconnect = True

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

    # ────────────────────────────────────────────────────────────────────
    # TRANSPORT (WO-008b-A2). The WebSocket layer's ONLY job is transport.
    #
    # Receive frame -> json.loads -> hand the raw dict to process_raw_frame(),
    # the SAME entry point the raw-frame fixtures feed. There is NO live-only
    # parsing branch: parsing, checksum validation, book application, the
    # no-emission window and MarketState construction are all the shared code
    # proven in WO-009 and WO-008b-A1. If transport forked the parse path, every
    # one of those proofs would silently detach from the running system.
    # ────────────────────────────────────────────────────────────────────

    def _build_subscribe_message(self) -> dict:
        """
        Kraken v2 book subscription. Unauthenticated — no key, no token, no auth.

        Cite: https://docs.kraken.com/api/docs/websocket-v2/book/
        """
        return {
            "method": "subscribe",
            "params": {
                "channel": "book",
                "symbol": [self.BOOK_SYMBOL],
                "depth": self.BOOK_DEPTH,
                "snapshot": True,
            },
        }

    def _build_unsubscribe_message(self) -> dict:
        """
        Kraken v2 book unsubscribe (WO-014 §2.1).

        Cite (verbatim): https://docs.kraken.com/api/docs/websocket-v2/book/
          {"method":"unsubscribe","params":{"channel":"book","symbol":[...]}}
        """
        return {
            "method": "unsubscribe",
            "params": {
                "channel": "book",
                "symbol": [self.BOOK_SYMBOL],
                "depth": self.BOOK_DEPTH,
            },
        }

    async def _maybe_resubscribe(self, websocket) -> None:
        """
        WO-014 §2.1 PRODUCER: if a checksum failure requested a fresh snapshot
        (`_request_snapshot` set the flag), send unsubscribe+subscribe on the live
        socket. Kraken then delivers a fresh snapshot, which the EXISTING consumer
        branch (_process_quote_update) validates to clear the no-emission window and
        resume emission. This supplies the producer that S10's certified consumer was
        hand-fed (rule 0.1h). It runs in the transport so the checksum/emission
        consumer path stays byte-for-byte unchanged (approved design B).
        """
        if not getattr(self, "_pending_resubscribe", False):
            return
        self._pending_resubscribe = False
        await websocket.send(json.dumps(self._build_unsubscribe_message()))
        await websocket.send(json.dumps(self._build_subscribe_message()))
        logger.info("[kraken_v2_book] resync: resubscribed on live socket for a fresh snapshot")

    async def _perform_reconnect(self, websocket, reason="5 consecutive checksum failures (FR-018)"):
        """
        WO-014b-1 EFFECT + WO-014b-2 §2 (backoff + circuit breaker).

        Close the current socket and reopen a FRESH one, resubscribing via the committed
        Phase 2.1 producer (`_maybe_resubscribe` — one code path serves "get a fresh
        snapshot onto a socket"; on a fresh socket the unsubscribe is a harmless no-op).

        WO-014b-2 §2 hardens the reopen against the two §0 hazards:
        - A FAILED reopen no longer propagates on the first failure (the hard-stop that
          ended a 24h run on one transient blip). It RETRIES under full-jitter exponential
          backoff (base×factor^attempt, capped), so a transient venue interruption is
          ridden out rather than fatal.
        - A DURATION CIRCUIT BREAKER bounds how long we try before concluding the venue is
          gone: when the continuous-failure streak exceeds RECONNECT_MAX_FAILURE_SECONDS of
          elapsed wall-clock (from the first failed reopen) it TRIPS — fails loud with reason
          code RECONNECT_CIRCUIT_BREAKER_TRIPPED, carrying a forensic tail, and STOPS the
          capture (Ruling B: STOP, never continue-with-a-silent-gap). The retained partial
          capture is labeled a truncated-honest window.

        Backoff/breaker figures are DECLARED ENGINEERING JUDGMENT: Kraken's WS rate limits
        are documented silence (evidence/WO-014b-2/rate_limits_research.txt; rule 0.1e).

        HONEST FIXTURE LIMIT: the close/reopen, the backoff retries, and the breaker trip
        are exercised by simulated transport (evidence/WO-014b-2/backoff_breaker.txt). Only
        the isolated live re-run confirms Kraken's real reopen behavior and rate tolerance.

        Returns the NEW socket for the transport to swap in.
        """
        import asyncio
        import time

        self._pending_reconnect = False
        sleep = self._reconnect_sleep or asyncio.sleep
        jitter = self._reconnect_jitter or random.random

        logger.info(
            "[kraken_v2_book] RECONNECT: closing and reopening the live socket after %s",
            reason,
        )
        try:
            await websocket.close()
        except Exception as exc:
            # A close failure on an already-dead socket must not block the reopen.
            logger.warning("[kraken_v2_book] error closing socket during reconnect: %s", exc)

        # New reconnect operation: reset the per-operation forensic ladder. streak_start is
        # stamped at the FIRST failed reopen; the duration breaker measures elapsed from it.
        self._reconnect_ladder = []
        streak_start = None
        attempt = 0
        while True:
            # DURATION circuit breaker: trip once the continuous-failure streak has run
            # longer than T seconds — the venue is presumed gone (Proposal B, ruled).
            if (streak_start is not None
                    and time.monotonic() - streak_start > self._reconnect_max_failure_seconds):
                raise self._trip_circuit_breaker(reason)

            try:
                new_websocket = await self._connect()
            except ConnectionError as exc:
                # Transient reopen failure -> back off and RETRY (do not propagate).
                if streak_start is None:
                    streak_start = time.monotonic()  # the continuous-failure streak begins
                delay = min(
                    self._reconnect_backoff_cap,
                    self._reconnect_backoff_base * (self._reconnect_backoff_factor ** attempt),
                )
                delay = delay * jitter()  # full jitter in [0, delay)
                self._reconnect_ladder.append({
                    "attempt": attempt,
                    "at": datetime.now(UTC).isoformat(),
                    "delay_s": round(delay, 4),
                    "error": str(exc),
                })
                logger.warning(
                    "[kraken_v2_book] reconnect reopen attempt %d failed; backing off %.3fs: %s",
                    attempt, delay, exc,
                )
                attempt += 1
                await sleep(delay)
                continue

            # Reopen succeeded -> fresh subscription via the committed producer.
            self._pending_resubscribe = True
            await self._maybe_resubscribe(new_websocket)
            logger.info(
                "[kraken_v2_book] RECONNECT complete after %d failed attempt(s); "
                "fresh socket subscribed; awaiting fresh snapshot",
                attempt,
            )
            return new_websocket

    def _trip_circuit_breaker(self, reason):
        """
        WO-014b-2 §2 / Ruling B. Build the RECONNECT_CIRCUIT_BREAKER_TRIPPED exception with
        a complete forensic tail, LABEL the retained partial capture as a truncated-honest
        window (two-window doctrine), log loudly, and return the exception for the caller to
        raise. The capture STOPS; it never continues silently with a gap.
        """
        trip_time = datetime.now(UTC).isoformat()
        ladder = list(self._reconnect_ladder)
        ladder_str = "; ".join(
            f"#{e['attempt']}@{e['at']} delay={e['delay_s']}s err={e['error']}" for e in ladder
        ) or "(no per-attempt errors recorded)"
        last_book = self._last_validated_book
        frames = len(getattr(self, "captured_raw_text", []) or [])
        message = (
            f"RECONNECT_CIRCUIT_BREAKER_TRIPPED: reconnect ({reason}) kept failing for more "
            f"than {self._reconnect_max_failure_seconds:.0f}s of continuous retry; venue "
            f"presumed gone. Capture STOPPED (no silent gap). Trip {trip_time}. Retry ladder: "
            f"[{ladder_str}]. Last validated book: {last_book}. Partial capture retained: "
            f"{frames} frames."
        )
        # Ruling B condition 2: retain + LABEL the partial capture (two-window doctrine).
        self.capture_terminated = {
            "reason_code": "RECONNECT_CIRCUIT_BREAKER_TRIPPED",
            "trip_time": trip_time,
            "trigger": reason,
            "retry_ladder": ladder,
            "last_validated_book": last_book,
            "frames_captured": frames,
            "evidentiary_bounds": (
                "TRUNCATED-HONEST WINDOW: the captured frames are real observed data up to "
                "the disconnect; NO data exists after the trip. A truncated run is still real "
                "data about a real hour (two-window doctrine) — retained, not discarded. Bound "
                "any analysis to [capture start .. trip_time]."
            ),
        }
        self._log_error(message)
        return CircuitBreakerTripped(
            message, trip_time=trip_time, reconnect_ladder=ladder,
            last_validated_book=last_book,
        )

    async def _connect(self):
        """
        Open the public v2 WebSocket. Raises on failure — NEVER falls back.

        No credentials of any kind are sent: no headers, no key, no token. The
        Kraken public book channel requires none, and needing one would signal
        something deeply wrong (rule 0.5).
        """
        import websockets

        logger.info("[kraken_v2_book] connecting to %s (public, unauthenticated)", self.WS_URL)
        try:
            # WO-014b-2 §1.3: deliberate PROTOCOL-level ping params (see WS_PING_* constants).
            # ping_timeout=None -> the library never closes on a missed pong; heartbeat-absence
            # (§1.1) + app ping (§1.2) decide liveness. We still SEND WS pings (interval) so we
            # are not silently disabling the protocol ping.
            return await websockets.connect(
                self.WS_URL,
                open_timeout=15,
                close_timeout=5,
                ping_interval=self.WS_PING_INTERVAL_SECONDS,
                ping_timeout=self.WS_PING_TIMEOUT,
            )
        except Exception as exc:
            # RAISE. A failed connection must never silently replay fixtures.
            raise ConnectionError(
                f"Kraken v2 connection FAILED: {type(exc).__name__}: {exc}. "
                f"Refusing to continue — a live run must never fall back to fixtures."
            ) from exc

    async def _sample_event_loop_lag(self, record: "LagSampleRecord") -> None:
        """
        WO-014c-1 §B.1 — PRIMARY starvation discriminator. A sentinel task that measures how
        late the event loop schedules a fixed-cadence sleep: lag = actual_interval - interval.
        A healthy loop yields lag ~0; a STARVED loop overruns the sleep (high lag) and, when
        badly starved, fails to wake the task at all — so the sample COUNT itself drops.

        SELF-REPORTING (WO-014c-1 §A.2/§A.3): this task only appends; the completeness deficit
        (expected vs actual, missed, gaps) is derived from the record on the SAME monotonic
        clock all instruments share. That is what turns the sampler's own silence under load
        into a POSITIVE signal instead of a false "healthy because quiet." Runs until cancelled
        by the transport's finally; the finally stamps ended_monotonic even on cancellation.
        """
        import asyncio
        import time

        interval = record.interval_s
        record.started_monotonic = time.monotonic()
        prev = record.started_monotonic
        try:
            while True:
                await asyncio.sleep(interval)
                now = time.monotonic()
                actual = now - prev
                record.samples.append((now, actual - interval))  # lag = sleep overrun
                if actual >= interval * self.LAG_GAP_FACTOR:
                    # This wake overran by >= one interval: intended wakes were missed here.
                    record.gaps.append((prev, now, actual))
                prev = now
        finally:
            record.ended_monotonic = time.monotonic()

    def _check_instruments_gappy(self, record: "LagSampleRecord") -> bool:
        """
        WO-014c-1 branch 5. If the lag sampler missed more than the VOID fraction of its
        expected samples, the quantitative discrimination is VOID — but the gap timestamps
        stay REPORTED evidence (they can NOMINATE the starvation hypothesis; only clean
        instruments CONVICT). Emits the declared reason code so the run's own report carries
        its VOID reason. Returns True when gappy.
        """
        if record.missed_fraction > self.INSTRUMENTS_GAPPY_VOID_FRACTION:
            self._log_error(
                f"INSTRUMENTS_GAPPY: lag sampler missed {record.missed_samples} of "
                f"{record.expected_samples} expected samples "
                f"({record.missed_fraction:.0%} > {self.INSTRUMENTS_GAPPY_VOID_FRACTION:.0%}); "
                f"quantitative discrimination VOID. {len(record.gaps)} gap(s) retained as "
                f"reported evidence (may NOMINATE starvation; only clean instruments convict)."
            )
            return True
        return False

    async def get_live_market_data(self, duration_seconds: float) -> AsyncIterator[MarketState]:
        """
        Stream MarketStates from the LIVE Kraken v2 public book channel.

        Transport only. Every frame goes to process_raw_frame() unmodified.

        Args:
            duration_seconds: hard wall-clock bound on the capture window.

        Raises:
            ValueError: if called on a fixture-mode adapter (no silent switching).
            ConnectionError: if the socket cannot be opened or drops.
        """
        import asyncio
        import time
        # WO-014b-2 §1.3: the library surfaces a PROTOCOL-level close on recv as these.
        from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

        if self._mode != self.MODE_LIVE:
            raise ValueError(
                f"get_live_market_data requires mode={self.MODE_LIVE!r}, "
                f"got {self._mode!r}. Mode is explicit and never inferred."
            )

        self._raw_received = 0
        self._market_states_emitted = 0
        self._start_time = time.time()
        self.captured_frames = []
        self.captured_raw_text = []
        # WO-014c-1 §B.1: the event-loop LAG sampler (PRIMARY starvation discriminator) runs
        # concurrently for this capture on the shared time.monotonic() clock (§A.2).
        self._lag_record = LagSampleRecord(interval_s=self.LAG_SAMPLE_INTERVAL_SECONDS)
        lag_task = None

        websocket = await self._connect()
        logger.info(
            "[kraken_v2_book] CONNECTED mode=%s venue=%s url=%s",
            self._mode, self.venue_name, self.WS_URL,
        )

        try:
            subscribe = self._build_subscribe_message()
            await websocket.send(json.dumps(subscribe))
            logger.info("[kraken_v2_book] subscribed: %s", json.dumps(subscribe))
            lag_task = asyncio.create_task(self._sample_event_loop_lag(self._lag_record))

            deadline = time.time() + duration_seconds
            # WO-014b-2 §1.1/§1.2 keepalive clocks (monotonic). last_frame is refreshed by
            # ANY received frame (book, heartbeat, or pong); last_ping paces the app ping.
            last_frame = time.monotonic()
            last_ping = time.monotonic()
            while time.time() < deadline:
                # WO-014b-1 WATCHDOG. _reconnect() sets _pending_reconnect from inside
                # process_raw_frame (the FR-018 checksum-failure branch); the servicing
                # step below consumes it in the SAME iteration. THRESHOLD: zero-iteration
                # latency — a correctly plumbed flag is cleared before the loop returns
                # here. If it is still set at this boundary, a reconnect was requested
                # and NOT effected: silent non-action, the WO-008b-B defect class this
                # WO exists to kill. Fail loudly rather than press on against a discarded
                # book (rule 0.1i / 0.1g).
                if self._pending_reconnect:
                    raise RuntimeError(
                        "RECONNECT_FLAG_STRANDED: a reconnect was requested "
                        "(_pending_reconnect set by _reconnect() at 5 consecutive "
                        "checksum failures) but the transport did not effect it before "
                        "the next loop boundary. Recovery must never silently no-op."
                    )

                mono = time.monotonic()

                # WO-014b-2 §1.1: HEARTBEAT-ABSENCE DETECTION -> reconnect. Kraken's
                # heartbeat (~1/s) is the venue's own liveness signal; a data-quiet-but-
                # alive link is also kept warm by our pong (below). If NO frame of any kind
                # has arrived within the threshold, the connection is presumed dead and we
                # reconnect (through the §2 backoff/breaker). This is why the capture ends
                # ONLY at the deadline: a silent link is reconnected, never quietly ended.
                if mono - last_frame >= self._heartbeat_absence_timeout:
                    self._log_error(
                        f"HEARTBEAT_ABSENCE: no frame for {mono - last_frame:.2f}s "
                        f"(>= {self._heartbeat_absence_timeout:.0f}s threshold); "
                        f"connection presumed dead"
                    )
                    websocket = await self._perform_reconnect(
                        websocket,
                        reason=f"heartbeat absence ({mono - last_frame:.1f}s without a frame)",
                    )
                    last_frame = time.monotonic()
                    last_ping = time.monotonic()
                    continue

                # WO-014b-2 §1.2: APPLICATION-LEVEL PING. Kraken's documented keepalive is a
                # CLIENT-INITIATED application ping ({"method":"ping"} -> pong), DISTINCT
                # from the WS PROTOCOL ping (§1.3). Probe on an interval so a data-quiet link
                # is actively tested; the pong Kraken returns is a frame that refreshes
                # last_frame above. A failed SEND means a dead socket -> reconnect.
                if mono - last_ping >= self._app_ping_interval:
                    self._ping_seq += 1
                    try:
                        await websocket.send(
                            json.dumps({"method": "ping", "req_id": self._ping_seq})
                        )
                    except Exception as exc:
                        logger.warning(
                            "[kraken_v2_book] application ping send failed (%s); reconnecting",
                            exc,
                        )
                        websocket = await self._perform_reconnect(
                            websocket, reason="application ping send failed",
                        )
                        last_frame = time.monotonic()
                        last_ping = time.monotonic()
                        continue
                    last_ping = time.monotonic()

                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                # Bound recv so we wake to re-check absence/ping/deadline before either
                # would fire. A recv timeout is a tick, NOT the end of the capture.
                mono = time.monotonic()
                recv_timeout = max(0.0, min(
                    remaining,
                    self._heartbeat_absence_timeout - (mono - last_frame),
                    self._app_ping_interval - (mono - last_ping),
                ))
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=recv_timeout)
                except asyncio.TimeoutError:
                    continue
                except ConnectionClosedOK:
                    # WO-014b-2 §1.3 (4c): a CLEAN/EXPECTED close (normal-closure code 1000/
                    # 1001) — a graceful, intentional shutdown. Do NOT reconnect into it (that
                    # would hammer a venue that closed on purpose); end the capture cleanly.
                    logger.info(
                        "[kraken_v2_book] venue closed the connection cleanly (normal closure); "
                        "ending capture without reconnect"
                    )
                    break
                except ConnectionClosedError as exc:
                    # WO-014b-2 §1.3 (4c): an UNEXPECTED venue-initiated close (abnormal code —
                    # e.g. 1011, the protocol-level keepalive-ping timeout that ended WO-008b-B).
                    # This is the same hazard class as §0's hard-stop; ROUTE IT INTO THE EXISTING
                    # recovery (reconnect + backoff + duration breaker) rather than propagating
                    # and ending the capture. Reuse — no parallel recovery path.
                    self._log_error(
                        f"VENUE_CONNECTION_CLOSED: unexpected close ({exc}); reconnecting"
                    )
                    websocket = await self._perform_reconnect(
                        websocket, reason=f"venue closed the connection unexpectedly ({exc})",
                    )
                    last_frame = time.monotonic()
                    last_ping = time.monotonic()
                    continue

                # A frame arrived (book, heartbeat, or pong) -> the link is alive.
                last_frame = time.monotonic()

                # LAYER 1: feed boundary. Count EVERY raw frame received, before
                # any filtering, validation or pause check — the same semantic
                # position proven on fixtures in WO-008a-R2.
                self._raw_received += 1

                try:
                    # WO-008b-A3 §1.1: PRESERVE the venue's transmitted digits.
                    # parse_float/parse_int receive the RAW TEXT of each number,
                    # so Kraken's "0.00005100" stays "0.00005100". Plain
                    # json.loads would float it and Decimal(str(float)) would
                    # render "0.000051", dropping the trailing zeros the CRC32
                    # digits require. We do NOT re-render into an assumed format
                    # (e.g. fixed 8dp): that would encode an uncited assumption
                    # about venue behaviour (rule 0.1e) that holds for BTC/USD
                    # today and breaks silently on the first symbol Kraken
                    # renders differently.
                    raw_frame = json.loads(
                        message, parse_float=Decimal, parse_int=Decimal
                    )
                except json.JSONDecodeError as exc:
                    self._log_error(f"Non-JSON frame from venue: {exc}")
                    continue

                # Retain the RAW WIRE TEXT for the durable ground-truth fixture.
                # WO-008b-A3: A2 stored the POST-parse structure, which had
                # already lost trailing zeros — the exact information the
                # checksum depends on. Store the text as received.
                self.captured_raw_text.append(message)

                # LAYER 3: the SHARED entry point. Identical to the fixture path.
                logger.debug(
                    "[kraken_v2_book] live frame -> process_raw_frame() "
                    "(SHARED entry point, no live-only branch)"
                )
                market_states = await self.process_raw_frame(raw_frame)

                # WO-014b-1: RECONNECT takes priority over same-socket resubscribe.
                # Five consecutive checksum failures (FR-018) set _pending_reconnect via
                # _reconnect(); we close/reopen the socket and resubscribe on the FRESH
                # one, swapping it in for the rest of the capture. This is the effect
                # WO-008b-B's `pass` never produced.
                #
                # Otherwise (WO-014 §2.1) a single checksum failure's resync request is
                # served on the SAME socket by the committed Phase 2.1 producer; without
                # it the no-emission window latched off forever (WO-008b-B). Reconnect
                # SUBSUMES resubscribe — the fresh socket already gets a fresh
                # subscription — so we never also resubscribe the socket being replaced.
                # The consumer path above is untouched (design B).
                if self._pending_reconnect:
                    websocket = await self._perform_reconnect(websocket)
                else:
                    await self._maybe_resubscribe(websocket)

                # LAYER 4: yield boundary.
                for market_state in market_states:
                    self._market_states_emitted += 1
                    yield market_state

        finally:
            self._running = False
            # WO-014c-1 §B.1: stop the lag sampler, finalize its record, and report gappiness
            # (branch 5). Cancelling stamps ended_monotonic in the sampler's own finally.
            if lag_task is not None:
                lag_task.cancel()
                try:
                    await lag_task
                except asyncio.CancelledError:
                    pass
                self._check_instruments_gappy(self._lag_record)
            try:
                await websocket.close()
                logger.info(
                    "[kraken_v2_book] DISCONNECTED cleanly. raw=%d emitted=%d",
                    self._raw_received, self._market_states_emitted,
                )
            except Exception as exc:
                logger.error("[kraken_v2_book] error during close: %s", exc)

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
