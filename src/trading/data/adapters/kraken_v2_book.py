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
# WO-021 §2: AsyncIterator is used in return annotations (get_live_market_data, get_market_data) and
# was never imported. Python 3.11 evaluates annotations eagerly -> NameError at class definition
# (masked on 3.14 by PEP 649). Targeted import from collections.abc (the canonical home since 3.9;
# typing.AsyncIterator is the deprecated alias) — NOT `from __future__ import annotations`, which would
# suppress the symptom project-wide and hide the next instance everywhere (WO-021 §2 ruling).
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
import enum
import binascii
import logging
import json
import random

import websockets

from trading.data.market_state import MarketState
from trading.logkit.redaction import redact
# ^ WO-014c-2 §3: the MECHANICAL redaction module (WO-011 §6.2). data->logkit is an
#   established dependency (factory.py, kraken_public.py import logkit.decision) and no
#   import-linter contract forbids it. Failure captures are redacted BY DEFAULT.

# WO-023 §2b (RULING D34-2, corrected): the GENUINE transport callable, captured at IMPORT — before
# any test can monkeypatch `websockets.connect`. The pre-connection coupling gate compares the
# resolved transport against THIS by IDENTITY (`resolved is _REAL_CONNECT`), NOT against the live
# module attribute (which a module-patching test replaces, so a fake would read as real and refuse
# the currently-green module-patching tests). The ruled invariant is "a REAL transport with a fake
# clock refuses" — REAL is an identity fact about the callable, not the sentinel fact of whether
# _connect_fn was injected. A transport that is non-default by CONFIG (connect_fn=websockets.connect
# passed explicitly) but REAL by IDENTITY must still refuse; keying on the sentinel let it through.
_REAL_CONNECT = websockets.connect


logger = logging.getLogger(__name__)


class WireDecimal(Decimal):
    """WO-017 §1.1/§1.2: a Decimal that ALSO carries the venue's transmitted token text.

    FR-018a(f) requires the checksum to be computed over the venue's TRANSMITTED
    representation, never a re-render. ``json.loads(parse_float=WireDecimal,
    parse_int=WireDecimal)`` invokes this constructor with the RAW TOKEN TEXT of each
    number (e.g. the string ``"0.00000010"``, not the float 1e-7), and it retains that
    text on ``.wire``. The numeric identity is the Decimal itself and is used everywhere
    a value is compared, sorted, or compared to zero.

    Why the wire string survives from parse to checksum: arithmetic on a Decimal subclass
    returns a PLAIN Decimal (dropping ``.wire``), but the local book NEVER does arithmetic
    on a ladder level — apply REPLACES the (price, qty) tuple, delete FILTERS it, sort
    REORDERS it, truncate SLICES it (WO-017 §1.5 enumeration). None of those touch the
    value, so the WireDecimal instance reaches ``_current_ladder_strings`` intact.

    ``.wire`` is the transmitted string ONLY when constructed from a str. A WireDecimal
    built from a non-str (int, float, or an arithmetic result) has ``.wire is None``: it
    carries NO transmitted string and MUST NOT be used as checksum input — the no-fallback
    guard (WO-017 §1.4) raises CHECKSUM_WIRE_STRING_MISSING rather than synthesize one.
    """

    def __new__(cls, value):
        self = super().__new__(cls, value)
        self._wire = value if isinstance(value, str) else None
        return self

    @property
    def wire(self):
        """The venue's transmitted token text, or None if this value never carried one."""
        return self._wire


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

    # ── WO-016 §B (D27): the three-component VOID quantities ──────────────────────────────
    @property
    def mean_cycle_s(self) -> float:
        """OBSERVED mean sleep-wake-record cycle = span / actual samples (per-cycle overhead
        included). The drift metric's baseline is derived from THIS, so overhead is IN the
        baseline and only a CHANGE in cycle time registers (component 3, UNIFORM degradation)."""
        span = self.ended_monotonic - self.started_monotonic
        n = self.actual_samples
        return (span / n) if n > 0 and span > 0 else 0.0

    @property
    def recorded_gap_fraction(self) -> float:
        """Σ(recorded missed-wake gap durations) / window — the DISCRETE-failure quantity
        (component 1). Time the sampler was actually stalled >= LAG_GAP_FACTOR × interval, NOT the
        overhead-biased span/interval deficit."""
        span = self.ended_monotonic - self.started_monotonic
        return (sum(d for (_s, _e, d) in self.gaps) / span) if span > 0 else 0.0

    def elevated_lag_fraction(self, threshold_s: float) -> float:
        """Fraction of samples whose lag (wake overrun) exceeds threshold_s — the SPIKY-degradation
        quantity (component 2)."""
        n = len(self.samples)
        return (sum(1 for (_ts, lag) in self.samples if lag > threshold_s) / n) if n else 0.0


@dataclass
class PongRecord:
    """
    WO-014c-1 §B.2. Protocol-level pong-latency record — the RTT distribution from the
    sanctioned ws.ping() (RFC 6455 §5.5.2 control frame). Same time.monotonic() clock as the
    lag sampler and message counters (§A.2), so pong latency is a TIME SERIES correlatable
    against them, not a sparse health check.

    THE RULED DISTINCTION (carryover #1): a MISSED SEND and an ABSENT PONG are NOT merged.
      - a ping the observer FAILED TO SEND (its task was starved) is INSTRUMENT GAPPINESS —
        it counts toward the VOID fraction: gappy = (pings_expected - pings_sent).
      - a ping SENT with no pong within the absent timeout is an ABSENT PONG — a SIGNAL
        feeding Branch 1/3, NEVER gappiness. Conflating them would VOID the strongest
        protocol-side evidence (genuine venue silence) as instrument failure.

    Fields: samples = list of (sent_monotonic_ts, rtt_s) for received pongs, (ts, None) for
    absent. Four counters kept separately: pings_sent, pongs_received, pongs_absent, and the
    expected send count (derived from the window span).
    """

    interval_s: float
    absent_timeout_s: float
    started_monotonic: float = 0.0
    ended_monotonic: float = 0.0
    pings_attempted: int = 0   # send points the observer REACHED (one per loop iteration)
    pings_sent: int = 0        # ws.ping() calls that actually issued
    pongs_received: int = 0
    pongs_absent: int = 0
    samples: list = field(default_factory=list)

    @property
    def missed_sends(self) -> int:
        """A ping the observer REACHED but FAILED to send (ws.ping raised) — the only thing
        that is gappiness. Uses attempted - sent (carryover #1), NOT span/interval, so it is
        immune to sampling-interval overhead and never conflated with an absent pong."""
        return max(0, self.pings_attempted - self.pings_sent)

    @property
    def missed_send_fraction(self) -> float:
        return (self.missed_sends / self.pings_attempted) if self.pings_attempted > 0 else 0.0


@dataclass
class ThroughputRecord:
    """
    WO-014c-1 §B.3. Per-second receive-to-process latency AND message rate, on the shared
    time.monotonic() clock (§A.2). Carries its OWN expected-vs-actual completeness accounting:
    Branch 5's nomination correlates lag-sampler gaps against message-rate peaks, and if the
    loop was starved enough to gap the sampler the message-counting path is degraded at exactly
    those timestamps — so the record must be able to STATE which seconds hold trustworthy data.
    A SILENT second (no messages) is either genuinely quiet or starvation-suppressed; the record
    reports it explicitly (silent_seconds), so a correlation can say "nomination unmakeable —
    message record also degraded at the relevant timestamps" rather than silently trusting it.

    per_second: {second_index -> {messages, lat_sum, lat_max, lat_n}}. Latencies in seconds.
    """

    bucket_seconds: float = 1.0
    start_monotonic: float = 0.0
    end_monotonic: float = 0.0
    per_second: dict = field(default_factory=dict)

    def record(self, recv_ts: float, done_ts: float) -> None:
        """One frame: recv_ts (recv returned) -> done_ts (process_raw_frame returned)."""
        idx = int((recv_ts - self.start_monotonic) / self.bucket_seconds)
        b = self.per_second.setdefault(
            idx, {"messages": 0, "lat_sum": 0.0, "lat_max": 0.0, "lat_n": 0}
        )
        b["messages"] += 1
        lat = done_ts - recv_ts
        b["lat_sum"] += lat
        b["lat_max"] = max(b["lat_max"], lat)
        b["lat_n"] += 1

    @property
    def expected_seconds(self) -> int:
        span = self.end_monotonic - self.start_monotonic
        return int(span / self.bucket_seconds) + 1 if span > 0 else 0

    @property
    def observed_seconds(self) -> int:
        return len(self.per_second)

    @property
    def silent_seconds(self) -> list:
        """Expected second-indices with NO message data — the completeness deficit, made
        explicit so trustworthiness at gap timestamps is statable (never silently trusted)."""
        return [i for i in range(self.expected_seconds) if i not in self.per_second]

    def mean_latency(self, idx: int) -> float:
        b = self.per_second.get(idx)
        return (b["lat_sum"] / b["lat_n"]) if b and b["lat_n"] else 0.0


# ── WO-014c-2 §1/§2: DATA-GAP RECORDING ──────────────────────────────────────────
# The ruled cause taxonomy (evidence/WO-014c-2/gap_schema.txt §1.1). Closed set — not
# extended in code. BREAKER_RETRY_LADDER is cross-cutting: it manifests as the
# retry_ladder FIELD of whichever reconnect gap triggered it (a duration component), not
# as a standalone interval — so a GapRecord's `cause` is one of the three TRIGGERS
# (keepalive / checksum / venue disconnect) and the ladder rides along as a field.
GAP_CAUSES = (
    "KEEPALIVE_RECONNECT",
    "CHECKSUM_RESYNC",
    "BREAKER_RETRY_LADDER",
    "VENUE_DISCONNECT",
    # WO-015 addendum A: the RULED fifth cause (a lead ruling, not an invented fifth — so it
    # does NOT trip WO-014c-2's exhaustiveness STOP). A host SUSPEND detected by wall-vs-
    # monotonic divergence beyond the drift bound. Fits the GapRecord schema UNCHANGED: the
    # divergence magnitude rides in `detail` (a structured field is the corpus WO's call, when
    # the role turns from diagnostic to window-invalidating).
    "HOST_SUSPEND",
)


@dataclass
class GapRecord:
    """
    WO-014c-2 §1.2. One recorded data gap: a half-open interval [open_monotonic,
    close_monotonic) during which NO validated MarketState was emitted. Shaped to match
    capture_terminated's already-assembled fields (the richest emission site) rather than
    invented and retrofitted. ALL BOUNDS ARE time.monotonic() — the WO-014c-1 §A.2 shared
    clock (same as the lag/pong/throughput records), so continuity is checkable by direct
    interval comparison and gaps correlate with those records without mixing clock bases.
    Calendar location comes from the ledger's once-per-run (wall, monotonic) anchor, never
    from a per-gap wall timestamp.

    close_monotonic is None while UNRESOLVED or TERMINAL: read as +infinity, so an unclosed
    gap intersects EVERY later interval query and the default-deny reader denies it. That
    makes "opened but never closed" LOUD BY CONSTRUCTION, not by anyone remembering to check
    (the property the lead named the best in the schema).
    """

    gap_id: int                              # per-run OPEN sequence — per-OCCURRENCE identity
    cause: str                               # one of GAP_CAUSES (a TRIGGER; see note above)
    reason_code: str                         # the DECLARED audit code emitted (links to vocab)
    open_monotonic: float                    # gap OPEN = last frame received / failing frame
    close_monotonic: Optional[float] = None  # first validated emit after recovery; None=+inf
    resumed: bool = False                    # True once a validated MarketState closed it
    terminal: bool = False                   # True if this gap ENDS the capture (breaker trip)
    last_validated_book: Optional[dict] = None  # {best_bid,best_ask,last_checksum,at} at OPEN
    retry_ladder: list = field(default_factory=list)  # BREAKER_RETRY_LADDER detail; [] if none
    detail: str = ""                         # human trigger text
    open_server_ts: Optional[str] = None     # CORROBORATION only; monotonic is the bound

    @property
    def duration_s(self) -> Optional[float]:
        # None while unresolved/terminal: an open-ended gap has no closed duration yet.
        if self.close_monotonic is None:
            return None
        return self.close_monotonic - self.open_monotonic

    @property
    def complete(self) -> bool:
        """A record is COMPLETE if it either RESUMED (closed) or is a known TERMINAL gap.
        Anything else — opened, but the capture ended with it neither closed nor tripped —
        is INCOMPLETE and the ledger reports it, never drops it (WO §2 completeness)."""
        return self.resumed or self.terminal


@dataclass
class GapLedger:
    """
    WO-014c-2 §1.2/§1.3. Run-level gap ledger. Carries the ONCE-per-run (wall, monotonic)
    anchor — the ONLY wall clock in the gap records — so any monotonic bound is calendar-
    locatable via  wall(t) = run_wall_anchor + (t - run_monotonic_anchor)  without ever
    putting two clock bases inside a gap record. Also carries the completeness accounting the
    default-deny corpus reader needs: a "no gap here" answer is only trustworthy against a
    ledger known to hold EVERY gap of the run, so a detected-but-uncompleted gap is STATED.

    WALL/MONOTONIC DRIFT LIMIT (WO-014c-3 §0.3; declared, not a defect). The mapping above is
    exact at the anchor instant; over a run the true wall clock diverges from it by the net NTP
    correction, because time.monotonic() is not NTP-adjusted
    (https://docs.python.org/3/library/time.html#time.monotonic) while the wall clock is slewed.
    Expected error over a 24h run: < ~5 s typical (oscillator ~10-50 ppm, slewed out by NTP);
    worst case bounded by the standard 500 ppm NTP slew ceiling at <= ~43 s/24h (pathological
    continuous slew only). ACCEPTABLE: relative timing (every gap bound, inter-gap interval, and
    cross-record correlation) is on monotonic and is UNAFFECTED — only the single absolute
    calendar anchor drifts, and locating a gap to the right minute (to line it up with venue
    maintenance / network events) tolerates seconds of error. A per-record wall timestamp would
    instead import NTP steps into the sub-second correlation §A.2 protects; the single anchor is
    strictly better and the drift is its declared cost.

    DECLARED LIMIT — GAP-DURATION RESOLUTION (WO-022 §3.2, standing form). All bounds are
    time.monotonic(), whose RESOLUTION is host-dependent (coarse on Windows: two calls close in time
    can return the SAME value). The same tick that can make two gaps share an open timestamp (WO-022 §2)
    can make ONE gap share its own open and close: duration_s == 0, a real gap with no measured width.
      - CAUGHT: gaps longer than the host's monotonic tick — recorded with accurate duration.
      - NOT CAUGHT: a gap shorter than one tick records duration ZERO (it is still a REAL gap; only its
        width is unmeasured). Overlap/continuity is by INCLUSIVE interval bounds, not by width, so a
        zero-width gap still intersects a query spanning its instant and is never filtered as noise.
      - THE UNCAUGHT CASE LOOKS LIKE: total gap time UNDER-estimates by up to one tick per gap —
        negligible at observed reconnect rates (a handful of gaps/hour), but it is a floor on
        duration precision, not zero.
      - SCOPE: this matters most on the CORPUS HOST — the Windows machine with the coarser tick — which
        is why this is a declaration, not pedantry. A default-deny reader MUST treat a zero-duration
        gap as a real gap (see progress.md corpus preconditions).
    """

    run_wall_anchor: str                     # ISO-8601 UTC, captured ONCE at capture start
    run_monotonic_anchor: float              # time.monotonic() at the SAME instant (atomic)
    run_start_monotonic: float               # emission-window start bound (leading boundary)
    run_end_monotonic: float = 0.0           # emission-window end bound (deadline/close/trip)
    gaps: list = field(default_factory=list)  # GapRecord, in OPEN order (so sorted by open)
    frames_captured: int = 0                 # for the terminal evidentiary tail (4a)
    evidentiary_bounds: str = ""             # two-window doctrine label when terminal

    @property
    def gaps_detected(self) -> int:
        """Every OPEN creates a record, so detected == len(gaps). Named explicitly so the
        ledger reports its own integrity (WO §2)."""
        return len(self.gaps)

    @property
    def incomplete(self) -> list:
        """Detected gaps that were neither closed nor terminal at capture end — retained and
        reported, never dropped. A non-empty list means the run's continuity ledger has a
        deficit the reader must default-deny across."""
        return [g for g in self.gaps if not g.complete]


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

    # ── WO-014c-2 §3: failure-targeted checksum capture ──────────────────────
    # On EVERY checksum failure, persist the preceding N raw frames for reconstruction.
    # N = 20 is DECLARED ENGINEERING JUDGMENT (Kraken publishes nothing on this; rule 0.1e),
    # instance-overridable. DERIVATION:
    #   - The checksum validates on EVERY update (FR-018a(c)) and the streak resets on every
    #     GOOD checksum, so the book was checksum-GOOD immediately before this frame: the
    #     FAILING FRAME ITSELF is the prime suspect (the update that produced the mismatch).
    #     Diagnosis does not depend on deep history; it depends on the failing frame + the
    #     last-good book state (both captured in full).
    #   - The book is truncated to BOOK_DEPTH=10 per side, so no latent error can hide in a
    #     never-checksummed deep level — the fault is localized to the retained top-of-book.
    #   - The preceding N frames are CORROBORATING run-up (did a recent update shape the level
    #     that now mismatches?). At the WO-008b-B anchor ~26 msg/s (~38 ms/frame), 20 frames
    #     ~= 0.76 s of the most recent history — generous margin over the "handful of recent
    #     updates that touched the top-of-book," while BOUNDED so retention stays small and the
    #     window is principled, not positional. NOT positional sampling — this is the exact
    #     window around each failure, which is what WO-008b-B's positional sampling LOST.
    CHECKSUM_CAPTURE_PRECEDING_FRAMES = 20

    # ── WO-014c-3 §0.2: failure-capture RETENTION CAP (keep-first-N; count all) ──
    # Bounds disk/RAM growth if failures cluster pathologically, so the instrument cannot end
    # the run it documents. Declared engineering judgment (same standard as T=600s), instance-
    # overridable. The cap binds on COUNT or TOTAL BYTES, whichever comes first (a cluster of
    # large frames and one of small frames fail differently). KEEP THE FIRST N, not the last:
    # the ONSET is the most diagnostic part (the first failures show what changed) — ruled §0.2(a).
    # Anchor: ~21 frames/capture at the WO-008b-B profile (~900 B/frame) ~= ~19 KB/capture, so
    # 200 captures ~= ~3.8 MB; the 8 MB byte cap gives headroom yet binds first if frames are large.
    MAX_FAILURE_CAPTURES = 200
    MAX_FAILURE_CAPTURE_BYTES = 8 * 1024 * 1024  # 8 MiB

    # ── WO-015 addendum A: HOST_SUSPEND detection threshold ──────────────────
    # A single loop iteration whose WALL-clock delta and MONOTONIC-clock delta diverge by more
    # than this is a host SUSPEND (one clock counted the suspend, the other did not), not drift:
    # legitimate wall/monotonic drift is ~5s TYPICAL and <=43s WORST over a FULL 24h run
    # (WO-014c-3 §0.3), so a per-iteration divergence beyond the worst-case whole-run bound
    # cannot be drift. Set to the 43s worst-case bound — conservative (an NTP step is <<43s, so
    # no false positive) while catching any real suspend (which is seconds-to-hours). Declared
    # engineering judgment, instance-overridable for ms-scale tests.
    #
    # DECLARED DETECTION FLOOR (WO-015 review; a declared limit, not a defect). A suspend SHORTER
    # than this threshold (~43s) is NOT detected — it presents as an enormous lag spike,
    # INDISTINGUISHABLE from catastrophic starvation, the exact misreading this detection exists to
    # prevent. The threshold MUST sit above the worst-case whole-run drift or it fires on drift, so
    # the floor is the unavoidable cost of separating suspend from drift by magnitude. A sub-floor
    # suspend therefore still risks a wrong discrimination verdict — mitigated operationally: the
    # re-run disables host sleep (a 2h setting >> the 60-min window), so no suspend should occur.
    HOST_SUSPEND_DIVERGENCE_SECONDS = 43.0

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
    # Pong observer gappiness (missed SENDS) keeps the single-fraction gate — a discrete failure
    # mode with no overhead bias (attempted-vs-sent, not span/interval).
    INSTRUMENTS_GAPPY_VOID_FRACTION = 0.10

    # ── WO-016 §B (D27): the lag-sampler VOID gate is a THREE-COMPONENT OR-GATE. ─────────────
    # The old single gate used missed_fraction = (span/interval − actual)/expected, which measures
    # against an IDEALIZED instantaneous cycle: it was ~8.9% biased on a healthy loop (per-cycle
    # overhead) AND sensitive to degradation — the same property (D27). Replaced by three
    # components, each OWNING one failure mode by construction, declared per rule 0.1j (per-sample
    # bound + aggregation window + verdict fraction). 0.4 pre-released on this complete declaration.
    #
    # (1) RECORDED GAPS — owns DISCRETE failure ("did the sampler stop recording").
    #     per-sample bound: a wake is MISSED when its interval >= LAG_GAP_FACTOR × interval = 0.200s.
    #     window: the capture window.   verdict fraction: VOID if Σ(recorded-gap durations)/window
    #     > 0.10. Derivation: 10% of the window lost to >=200ms stalls is severe discrete starvation
    #     (same magnitude as the retired gate, now over the CORRECT quantity — real missed wakes).
    RECORDED_GAP_VOID_FRACTION = 0.10
    # (2) ELEVATED-LAG — owns SPIKY degradation.
    #     per-sample bound: lag (wake overrun) > 0.100s.  window: samples.  verdict fraction: VOID
    #     if fraction of samples with lag>100ms > 0.05. Adopted VERBATIM from WO-014c-1's declared
    #     "ELEVATED = >100ms on >5% of samples" (thresholds_and_branches.txt).
    ELEVATED_LAG_THRESHOLD_SECONDS = 0.10
    ELEVATED_LAG_VOID_FRACTION = 0.05
    # (3) MEAN-CYCLE-TIME DRIFT — owns UNIFORM degradation (the mode that escapes (1) and (2): a
    #     uniform 199ms cycle records ZERO gaps (<200ms) and ZERO elevated samples (lag 99ms<100ms)
    #     yet has doubled cycle time / halved temporal resolution). Immunity is STRUCTURAL: the
    #     baseline is OBSERVED, so per-cycle overhead is already IN it and only CHANGE registers.
    #     bound: VOID if (mean_cycle − baseline)/baseline > 0.50 (SIGNED — only SLOWDOWN fires; a
    #     faster cycle is health, not degradation). Derivation: below the doubling-point (100% =
    #     unambiguous starvation; the 199ms counterfactual reads +83%), above benign run-to-run
    #     variation (≪50%). BASELINE PROTOCOL (RULED): FROZEN, re-declared ONLY on a pipeline change
    #     that touches the loop, and that re-declaration is a 0.4 event (a self-re-deriving baseline
    #     is the drift metric's own 0.1d — "the instrument got slower and we re-baselined around
    #     it"). THE STANDING BASELINE is this run's OBSERVED mean cycle: span/actual =
    #     3600.00s / 33,062 = 0.108886 s (WO-008b-B-RERUN, run WO-008b-B-RERUN-20260721T170944Z).
    #     ABSOLUTE TOLERANCE (D27 acceptance A — the declared sensitivity, stated like the
    #     100ms-lag-on-100ms-interval and the HOST_SUSPEND ~43s floors): at the 108.886ms baseline,
    #     F=0.50 means a mean cycle UP TO ~163.3ms (108.886 x 1.50) READS CLEAN — a ~50% sustained
    #     slowdown / 50% temporal-resolution loss, tolerated by construction and chosen deliberately.
    #       CAUGHT     : mean cycle > ~163.3ms (uniform slowdown beyond 1.5x the baseline cadence).
    #       NOT CAUGHT : a uniform slowdown within 108.886–163.3ms.
    #       UNCAUGHT CASE looks like: the loop servicing frames up to 1.5x slower, every cycle, with
    #       zero gaps (<200ms) and zero elevated samples (<100ms lag) — clean under all three gates.
    #     HOST-SPECIFIC (D27 acceptance B — a corpus precondition): 0.108886s is THIS HOST's mean
    #     cycle, a property of the MACHINE, not the pipeline. ANY CHANGE OF HOST is a re-declaration
    #     trigger on the SAME footing as a pipeline change touching the loop — a 0.4 event requiring
    #     a FRESH baseline measurement BEFORE the run. The 24h corpus may run on a different no-sleep
    #     host (dedicated/cloud); on it this figure is WRONG (a faster/slower machine registers as
    #     drift that is not starvation, or reads clean while genuinely degraded). Measure first.
    # WO-017 follow-up B (no orphan figures): this is the TEST/DEFAULT SEED only. The LIVE gate is
    # HOST-SCOPED and reads the per-host store (config/mean_cycle_baselines.json), which is the
    # AUTHORITATIVE live figure (D28); the runner overrides self._mean_cycle_baseline_s from it at
    # preflight. SUPERSEDED as a live figure on 2026-07-21 by WO-017's re-baseline (0.107923s,
    # -0.9%, attributed to wire-string retention) — see the store's `rebaseline`/`superseded` ledger.
    # Left as the seed (not deleted) so tests/adapter defaults have a value without reading the store;
    # do NOT read this as the live baseline.
    MEAN_CYCLE_BASELINE_SECONDS = 0.108886
    MEAN_CYCLE_DRIFT_VOID_FRACTION = 0.50
    # RESIDUAL / FLOOR LIMIT (named, not papered over): the mode that still escapes all three is
    # DEGRADATION OF THE SAMPLER'S OWN MEASUREMENT such that drift reads normal while truth does not
    # (e.g. the monotonic clock itself skews, or the whole process slows uniformly so the baseline
    # comparison is fooled in lockstep). This is the in-the-failure-domain floor: every in-process
    # detector shares its process's domain and cannot certify below it. Declared, not closed.

    # ── WO-014c-1 §B.2: protocol-level PONG observer (sanctioned ws.ping() RTT) ──
    # Declared engineering judgment (Phase A, documented silence). 1 ping/s is a control
    # frame, ~20x the samples the library's 20s keepalive yields, negligible against ~26 msg/s.
    PING_SAMPLE_INTERVAL_SECONDS = 1.0
    PONG_ABSENT_SECONDS = 5.0   # a ping SENT with no pong within this = ABSENT pong (a SIGNAL)

    # Venue-mode provenance values (WO-008b-A1 §4).
    MODE_FIXTURE = "fixture"
    MODE_LIVE = "live"
    VENUE_FIXTURE = "kraken_fixture"
    VENUE_LIVE = "kraken_mainnet"

    def __init__(self, mode: str = MODE_FIXTURE, *, monotonic_clock=None, connect_fn=None):
        """
        Initialize adapter.

        Args:
            mode: MODE_FIXTURE (default) or MODE_LIVE. Determines the venue
                  provenance reported to the decision log. WO-008b-A1 §4: a
                  fixture replay and a live run MUST be distinguishable in the
                  audit trail (Principle VIII).
            monotonic_clock: WO-023 §2 (RULING D34-1) test seam for the DEADLINE
                  clock. Defaults to time.monotonic. A duration is an INTERVAL, and
                  D25 puts intervals on the monotonic clock — so this, NOT _wall_clock,
                  is the deadline clock (see line 1136 and the pre-connection gate).

        Note: MODE_LIVE only labels provenance. It opens NO connection —
        transport is WO-008b-A2.
        """
        import time

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
        # WO-014c-1 §B.2: pong-observer config (instance-overridable for ms-scale tests).
        self._ping_sample_interval = self.PING_SAMPLE_INTERVAL_SECONDS
        self._pong_absent_timeout = self.PONG_ABSENT_SECONDS
        # WO-014c-2 §2: data-gap ledger. None outside a live capture — gap recording is a
        # LIVE-continuity concern (like the §B instruments), so the fixture path records no
        # gaps. Created per capture in get_live_market_data. _gap_seq assigns per-occurrence
        # gap_id (probe 1). _last_frame_server_ts is the corroborating venue wall-clock of the
        # last validated frame, used for GapRecord.open_server_ts.
        self._gap_ledger = None
        self._gap_seq = 0
        self._open_gaps = []                 # GapRecords still open (not yet closed/terminal)
        self._last_frame_server_ts = None
        # WO-014c-2 §3: failure-targeted checksum capture. On EVERY checksum failure, a full
        # artifact is appended here (redacted). This is the corpus's blessing gate: the A3
        # 1254/1254 rate is UNDIAGNOSED, so no run is blessed until a capture shows whether
        # residual failures are wire anomalies or our parse/apply bug.
        self._checksum_capture_preceding = self.CHECKSUM_CAPTURE_PRECEDING_FRAMES
        self._checksum_failure_captures = []
        # WO-014c-3 §0.2: retention cap state. COUNT every failure (a finding in itself);
        # KEEP only the first N (or byte budget). _capped announces ONCE; no run-termination.
        self._checksum_failure_count = 0
        self._checksum_capture_bytes = 0
        self._checksum_capture_capped = False
        self._max_failure_captures = self.MAX_FAILURE_CAPTURES
        self._max_failure_capture_bytes = self.MAX_FAILURE_CAPTURE_BYTES
        # WO-014c-3 addendum A: beyond the capture cap, a ONE-LINE summary per subsequent
        # failure (utc, expected/computed checksum, sequence position; NO raw frames) so a
        # cluster's PHASES are visible at negligible cost where the count alone cannot show them.
        self._checksum_failure_summaries = []
        # WO-014c-3 §0.1: gap-ledger persistence. EXPLICIT opt-in (like mode — never inferred):
        # set _gap_persist_path to enable append-only redacted JSONL. A capture then flushes each
        # gap event as it happens (incremental — survives a process kill), plus a terminal flush
        # on a breaker trip and a finalize summary. Default None = no persistence (fixture tests).
        self._gap_persist_path = None
        self._gap_persist_fh = None
        # WO-014c-3 addendum C: a LIVE capture with persistence UNSET refuses to run (an opt-in
        # durability feature that silently no-ops when unset is a vigilance-enforced guarantee).
        # Fixture/test paths opt out EXPLICITLY by setting this True; a real capture must set a
        # path instead. Default False = the safe default (refuse rather than silently not persist).
        self._persistence_optional = False
        # WO-016 §D28: the UNIFORM drift gate's baseline is HOST-SCOPED. Defaults to the class
        # constant (this host's / tests' value); the live-capture runner overrides it from the
        # per-host store (config/mean_cycle_baselines.json) after verifying the fingerprint.
        self._mean_cycle_baseline_s = self.MEAN_CYCLE_BASELINE_SECONDS
        # WO-015 addendum A: host-suspend detection threshold (instance-overridable for tests).
        self._host_suspend_divergence = self.HOST_SUSPEND_DIVERGENCE_SECONDS
        # Injectable wall clock (test seam, like _reconnect_sleep); defaults to time.time. Used
        # ONLY for the suspend detector's wall sampling, so a test can simulate a wall jump
        # (a suspend) without touching the deadline. NOT used for the deadline/start_time.
        self._wall_clock = None
        # WO-023 §2 (RULING D34-1): the injectable DEADLINE clock. A duration is an INTERVAL and
        # D25 puts intervals on MONOTONIC, so the capture deadline runs on THIS, not on _wall_clock
        # (which is the suspend detector's wall and CAN jump — line 1136). Default time.monotonic;
        # a jumped _wall_clock therefore never touches the deadline. The pre-connection gate (§4)
        # permits a non-default clock only paired with a non-default transport (_connect_fn).
        self._monotonic_clock = monotonic_clock or time.monotonic
        # WO-023 §2 (RULING D34-2): the injectable TRANSPORT factory. Stored as the RAW injection
        # (None == default) — the OR-resolution to websockets.connect happens at the CALL SITE in
        # _connect() (LATE binding). Two reasons (Checkpoint B): (1) existing tests monkeypatch
        # websockets.connect AFTER constructing the adapter, so a default resolved here at __init__
        # time would capture the UNPATCHED callable and the patch would never take — late resolution
        # honours the module patch, keeping the suite green; (2) the pre-connection gate (§4) must be
        # able to NAME whether the caller injected a transport, and keying on `self._connect_fn is
        # None` (the injection sentinel) gives it exactly that. A module-level patch with NO injected
        # clock is still a DEFAULT transport to the gate — the "real transport" case that, paired with
        # a fake clock, must refuse. So the object can finally name its own transport (decision log 1).
        self._connect_fn = connect_fn
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

        # WO-016 §A (D27) REGRESSION SENTINEL (rule 0.1d): reject synthesized notation in the
        # ASSEMBLED input. Scientific notation ('E'/'e') corrupts the CRC — str(Decimal('1.0E-7'))
        # -> '1.0E-7' -> '10E-7' was the WO-008b-B-RERUN defect (234 failures). The fixed-point
        # render (_current_ladder_strings) guards ONE site; this one character-class check guards
        # ALL of them, turning any future render regression into a LOUD NAMED failure instead of a
        # silent mismatch. Its trigger CANNOT occur while the fix holds — a sentinel, not a
        # data-path guard. It stays load-bearing after the wire-string WO: it then guards the
        # invariant ("no synthesized notation reaches the CRC"), not the implementation.
        if 'e' in checksum_input or 'E' in checksum_input:
            raise ValueError(
                "CHECKSUM_INPUT_SYNTHESIZED_NOTATION: assembled checksum input contains "
                "scientific notation; a formatting regression re-entered the render path. "
                f"fragment={checksum_input[:64]!r}"
            )

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
    def _retain_wire(value) -> "WireDecimal":
        """WO-017 §1.1-1.4: yield a WireDecimal carrying the venue's TRANSMITTED token.

        This is the single point where a ladder value acquires (or is proven to already
        carry) its wire string. Every ladder level originates here (§1.5: _parse_levels is
        the sole origin; the two writers only route these tuples through).

        - str  -> WireDecimal(str): the token AS SENT is retained on .wire. This is the
          live path's ``parse_float`` output routed back through here, and the fixture
          path's wire-form string frames.
        - WireDecimal WITH a wire string -> passed through unchanged (idempotent).
        - anything else (plain Decimal, WireDecimal with .wire is None, int, float):
          there is NO recoverable transmitted string, so we RAISE. NO FALLBACK to a
          render (§1.4, load-bearing) — a synthesized string is the exact defect class
          this WO closes structurally, and it must fail LOUDLY (0.1g), never quietly.
        """
        if isinstance(value, str):
            return WireDecimal(value)
        if isinstance(value, WireDecimal) and value.wire is not None:
            return value
        raise ValueError(
            "CHECKSUM_WIRE_STRING_MISSING: ladder level value carries no transmitted "
            "wire string; refusing to synthesize one (FR-018a(f) / WO-017 §1.4). "
            f"value={value!r} type={type(value).__name__}"
        )

    @staticmethod
    def _parse_levels(raw_levels) -> List[tuple]:
        """
        Convert Kraken v2 [{"price": ..., "qty": ...}, ...] into (price, qty) tuples of
        WireDecimal — each carrying the venue's transmitted token text (WO-017 §1.1-1.2).

        The live path delivers these values as WireDecimal (json.loads(parse_float=
        WireDecimal, parse_int=WireDecimal) retained the raw token); the fixture path
        delivers them as strings. Either way _retain_wire yields a WireDecimal whose
        .wire is the transmitted representation, or RAISES if none exists (§1.4, no
        fallback). Precision is preserved by construction — nothing is ever re-rendered.
        """
        levels = []
        for level in raw_levels or []:
            levels.append((
                KrakenV2BookAdapter._retain_wire(level["price"]),
                KrakenV2BookAdapter._retain_wire(level["qty"]),
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

    @staticmethod
    def _wire_pair(price, qty) -> tuple:
        """WO-017 §1.3/§1.4: return (price.wire, qty.wire) — the transmitted text, NO
        formatting, NO str(), NO format(). If EITHER value lacks a wire string the level
        cannot be checksummed over the venue's representation, so we RAISE the declared
        code rather than fall back to a render (the load-bearing no-fallback guard).

        This is the consumption-point twin of _retain_wire's origin-point guard: together
        they make it structurally impossible for a synthesized string to reach the CRC.
        """
        pw = getattr(price, "wire", None)
        qw = getattr(qty, "wire", None)
        if pw is None or qw is None:
            raise ValueError(
                "CHECKSUM_WIRE_STRING_MISSING: a local-book ladder level has no retained "
                "wire string; refusing to re-render for the checksum (FR-018a(f) / WO-017 "
                f"§1.4). price={price!r} ({type(price).__name__}) qty={qty!r} "
                f"({type(qty).__name__})"
            )
        return (pw, qw)

    def _current_ladder_strings(self) -> tuple:
        """Return (bid_levels, ask_levels) as the venue's TRANSMITTED strings for the checksum.

        WO-017 §1.3: the checksum consumes the wire string EXCLUSIVELY. Each ladder level is a
        (price, qty) tuple of WireDecimal retained at parse (WO-017 §1.1), and this returns their
        `.wire` text verbatim — no `str()`, no `format()`, no rendering of any kind. FR-018a(f) is
        satisfied LITERALLY: checksum input derives from the venue's transmitted representation,
        never re-rendered, so the scientific-notation defect (WO-008b-B-RERUN: `str(Decimal("1.0E-7"))`
        -> `"1.0E-7"` -> CRC fragment `"10E-7"` instead of `"10"`, 234 failures) is structurally
        impossible — there is no rendering step left to be wrong for ANY input the venue can send.

        NO FALLBACK (WO-017 §1.4, load-bearing): a level lacking its wire string RAISES
        CHECKSUM_WIRE_STRING_MISSING via _wire_pair; it does not silently re-render. The
        200-capture fixture (tests/integration/test_checksum_capture_replay.py) remains the standing
        regression guard, and compute_checksum's 'E'-sentinel (WO-016 D27) guards the invariant that
        no synthesized notation ever reaches the CRC.
        """
        bid_levels = [self._wire_pair(p, q) for p, q in self._local_book.bids[:10]]
        ask_levels = [self._wire_pair(p, q) for p, q in self._local_book.asks[:10]]
        return bid_levels, ask_levels

    # ── WO-014c-2 §2: gap-ledger primitives ─────────────────────────────────────
    # Active ONLY during a live capture (self._gap_ledger is not None). Each is a no-op on
    # the fixture path, so fixture replay records no gaps and existing fixture tests are
    # untouched. All bounds are time.monotonic() (§A.2 shared clock).
    def _open_gap(self, cause: str, reason_code: str, open_monotonic: float,
                  detail: str) -> Optional["GapRecord"]:
        """Open a gap at `open_monotonic`, assign a per-occurrence gap_id, snapshot the last
        validated top-of-book, and track it as open. Returns the record (None off-capture)."""
        if self._gap_ledger is None:
            return None
        record = GapRecord(
            gap_id=self._gap_seq,
            cause=cause,
            reason_code=reason_code,
            open_monotonic=open_monotonic,
            last_validated_book=self._last_validated_book,
            detail=detail,
            open_server_ts=self._last_frame_server_ts,
        )
        self._gap_seq += 1
        self._gap_ledger.gaps.append(record)
        self._open_gaps.append(record)
        # WO-014c-3 §0.1: INCREMENTAL persist at OPEN — the load-bearing write. If the process
        # is killed before the gap resolves, this "open" line is already durable on disk, so the
        # gap is not lost (default-deny: an open with no resolve reads as open-ended).
        self._persist_gap_event(record, "open")
        return record

    def _close_open_gaps(self, close_monotonic: float) -> None:
        """Probe-1 collective close: the first validated emit resumes emission for EVERY
        open gap at once (a nested child cannot close while its parent stays open — the emit
        gate proof), so all open gaps share this close instant. This IS the keepalive-absence
        close hook (probe 2a): one mechanism closes keepalive, checksum, and venue-disconnect
        gaps, so the most-frequent cause is no longer the one that cannot close."""
        if self._gap_ledger is None or not self._open_gaps:
            return
        for record in self._open_gaps:
            record.close_monotonic = close_monotonic
            record.resumed = True
            self._persist_gap_event(record, "resolved")  # WO-014c-3 §0.1: incremental
        self._open_gaps = []

    def _attach_ladder_to_open_gaps(self) -> None:
        """Attach the just-completed reconnect's retry ladder (BREAKER_RETRY_LADDER) to every
        gap open across it — the ladder is that gap's DURATION/forensic detail (§1.1)."""
        if self._gap_ledger is None:
            return
        ladder = list(self._reconnect_ladder)
        for record in self._open_gaps:
            record.retry_ladder = ladder

    # ── WO-014c-3 §0.1: gap-ledger persistence (append-only, redacted, crash-durable) ──
    @staticmethod
    def _gap_record_to_dict(record: "GapRecord", event: str) -> dict:
        return {
            "event": event,               # "open" | "resolved" | "terminal"
            "gap_id": record.gap_id,
            "cause": record.cause,
            "reason_code": record.reason_code,
            "open_monotonic": record.open_monotonic,
            "close_monotonic": record.close_monotonic,
            "resumed": record.resumed,
            "terminal": record.terminal,
            "duration_s": record.duration_s,
            "last_validated_book": record.last_validated_book,
            "retry_ladder": record.retry_ladder,
            "detail": record.detail,
            "open_server_ts": record.open_server_ts,
        }

    def _persist_write(self, obj: dict) -> None:
        """Append ONE redacted JSONL line and fsync it, so the record is durable the instant it
        is written — BEFORE any clean shutdown. This is what makes the ledger survive a process
        kill: 'the mechanism that records the terminal event must survive the terminal event.'
        Best-effort and NON-fatal: a persist error must never end the capture it documents (that
        would be the disk-exhaustion hazard §0.2 guards) — it is logged (lowercase, so it is not
        a reason-code-shaped string) and the run continues."""
        if self._gap_persist_fh is None:
            return
        try:
            self._gap_persist_fh.write(redact(json.dumps(obj, default=str)) + "\n")
            self._gap_persist_fh.flush()
            import os
            os.fsync(self._gap_persist_fh.fileno())
        except Exception as exc:  # noqa: BLE001 — durability is best-effort, never fatal
            logger.warning("[kraken_v2_book] gap ledger persist write failed: %s", exc)

    def _persist_gap_event(self, record: "GapRecord", event: str) -> None:
        self._persist_write(self._gap_record_to_dict(record, event))

    def _open_gap_persistence(self) -> None:
        """Open the append-only ledger file for this capture (if a path is configured). Mode
        'a' (append) never truncates an existing file — the raw path is append-only (Principle
        VIII). Best-effort: a failure to open disables persistence for the run but never ends it."""
        self._gap_persist_fh = None
        path = self._gap_persist_path
        if not path:
            return
        try:
            import os
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            self._gap_persist_fh = open(path, "a", encoding="utf-8")
            logger.info("[kraken_v2_book] gap ledger persisting (append-only) to %s", path)
        except Exception as exc:  # noqa: BLE001 — persistence is opt-in and never fatal
            logger.warning("[kraken_v2_book] could not open gap ledger file %s: %s", path, exc)
            self._gap_persist_fh = None

    def _close_gap_persistence(self) -> None:
        fh = self._gap_persist_fh
        self._gap_persist_fh = None
        if fh is not None:
            try:
                fh.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[kraken_v2_book] error closing gap ledger file: %s", exc)

    def _capture_checksum_failure(self, quote_update, computed_checksum) -> Optional[dict]:
        """
        WO-014c-2 §3 + WO-014c-3 §0.2. Persist the FULL forensic artifact for one checksum
        failure. Called on EVERY failure (never positionally sampled — positional sampling is
        exactly what lost WO-008b-B's three failures). Every field the WO rules is present:
          - the RAW WIRE TEXT of the failing frame, verbatim (self.captured_raw_text[-1] — the
            transport appends the untouched wire text before process_raw_frame; §B preserved it);
          - the LOCAL BOOK at failure, BOTH ladders at subscribed depth (post-apply state);
          - EXPECTED (Kraken's) and COMPUTED checksums;
          - the preceding N frames for reconstruction (N justified at CHECKSUM_CAPTURE_PRECEDING_
            FRAMES); - UTC AND monotonic timestamps, plus the sequence POSITION in the run.
        Text fields are redacted via the MECHANICAL redaction module (redact) so a session/
        connection identifier can never ship in the clear (WO-011 §6.2); scan() over the
        artifact is empty by construction.

        HONEST LIMIT: the raw wire text and the run position exist only in a LIVE capture (the
        transport retains them); a bare process_raw_frame call outside the transport leaves them
        empty — the same fixture boundary as capture_terminated. The bite proof drives the LIVE
        path so every field is populated.

        WO-014c-3 §0.2 RETENTION CAP: COUNT every failure (never capped — the count is a finding);
        KEEP only the FIRST N (or byte budget) — the onset is the most diagnostic part. When the
        cap binds, announce ONCE (FAILURE_CAPTURE_CAPPED) and stop KEEPING (never stop counting,
        never silently truncate). The cap guards disk exhaustion; it does NOT terminate the run
        (the breaker owns termination). Returns the artifact when kept, else None.
        """
        import time

        # COUNT every failure (uncapped) — "3 failures" and "40,000 failures" are different
        # worlds and both must stay reportable (§0.2(b)).
        self._checksum_failure_count += 1
        if self._checksum_capture_capped:
            # Beyond the cap: count + a ONE-LINE summary (addendum A), no full artifact.
            self._record_failure_summary(quote_update, computed_checksum)
            return None
        # COUNT cap — keep the FIRST N (§0.2(a): the onset shows what changed).
        if len(self._checksum_failure_captures) >= self._max_failure_captures:
            self._announce_capture_capped(f"count cap {self._max_failure_captures} reached")
            self._record_failure_summary(quote_update, computed_checksum)
            return None

        raw_texts = getattr(self, "captured_raw_text", None) or []
        failing_raw = raw_texts[-1] if raw_texts else ""
        n = self._checksum_capture_preceding
        preceding = raw_texts[-(n + 1):-1] if len(raw_texts) > 1 else []
        # The RENDERED (str) view of each ladder level. Kept because it is the checksum-MATH form
        # the 200-capture regression fixture (WO-016 §2) replays. It is str(Decimal), so it renders
        # small quantities in SCIENTIFIC notation and CANNOT witness the wire-retention path — that
        # is why the wire fields below exist (WO-017 follow-up A).
        bids = [(str(p), str(q)) for p, q in self._local_book.bids[:self.BOOK_DEPTH]]
        asks = [(str(p), str(q)) for p, q in self._local_book.asks[:self.BOOK_DEPTH]]
        # WO-017 follow-up A: persist the venue's TRANSMITTED text per level (WireDecimal.wire) so a
        # FUTURE capture can witness the wire path END-TO-END — a replay seeds WireDecimal(wire) and
        # validates through production with NO reconstruction. A level that lacks a wire string is
        # recorded as None (honest — the blindness is VISIBLE), never re-rendered: a silent render
        # here would recreate the exact defect class WO-017 closed.
        bids_wire = [(getattr(p, "wire", None), getattr(q, "wire", None))
                     for p, q in self._local_book.bids[:self.BOOK_DEPTH]]
        asks_wire = [(getattr(p, "wire", None), getattr(q, "wire", None))
                     for p, q in self._local_book.asks[:self.BOOK_DEPTH]]
        artifact = {
            "sequence_position_in_run": getattr(self, "_raw_received", None),
            "utc": datetime.now(UTC).isoformat(),
            "monotonic": time.monotonic(),
            "symbol": quote_update.symbol,
            "message_type": quote_update.message_type,
            "expected_checksum": quote_update.checksum,   # Kraken's, off the wire
            "computed_checksum": computed_checksum,        # ours, over the applied ladder
            "failing_frame_raw_text": redact(failing_raw),
            "preceding_frames_n": n,
            "preceding_frames_raw_text": [redact(t) for t in preceding],
            "local_book_bids": bids,                       # RENDERED view (checksum math) at depth
            "local_book_asks": asks,
            "local_book_bids_wire": bids_wire,             # WO-017 A: TRANSMITTED text per level (or None)
            "local_book_asks_wire": asks_wire,
        }
        # BYTE cap — binds independently of the count cap (whichever comes first). A cluster of
        # large frames exhausts bytes before count; a cluster of small ones exhausts count first.
        size = len(json.dumps(artifact, default=str).encode("utf-8"))
        if self._checksum_capture_bytes + size > self._max_failure_capture_bytes:
            self._announce_capture_capped(
                f"byte cap {self._max_failure_capture_bytes} B reached"
            )
            self._record_failure_summary(quote_update, computed_checksum)
            return None
        self._checksum_capture_bytes += size
        self._checksum_failure_captures.append(artifact)
        return artifact

    def _record_failure_summary(self, quote_update, computed_checksum) -> dict:
        """WO-014c-3 addendum A: a ONE-LINE summary for a failure BEYOND the capture cap —
        utc, expected/computed checksums, sequence position; NO raw frames. Reveals a cluster's
        PHASES (a failure mode shifting at failure 12,000) at negligible cost, where the count
        alone cannot. Persisted to the append-only ledger when persistence is on (durable, like
        the gap records; redact() is a harmless no-op on a summary that carries no identifiers)."""
        import time
        summary = {
            "sequence_position_in_run": getattr(self, "_raw_received", None),
            "utc": datetime.now(UTC).isoformat(),
            "monotonic": time.monotonic(),
            "expected_checksum": quote_update.checksum,
            "computed_checksum": computed_checksum,
        }
        self._checksum_failure_summaries.append(summary)
        self._persist_write({"event": "failure_summary", **summary})
        return summary

    def _announce_capture_capped(self, why: str) -> None:
        """WO-014c-3 §0.2(b): announce the retention cap ONCE, never silently truncate. Counting
        continues; the run is NOT terminated (the breaker owns termination — §0.2(c))."""
        if self._checksum_capture_capped:
            return
        self._checksum_capture_capped = True
        self._log_error(
            f"FAILURE_CAPTURE_CAPPED: failure-capture retention cap hit ({why}); "
            f"{len(self._checksum_failure_captures)} captures KEPT (the first, incl. the onset). "
            f"Further failures are still COUNTED but not fully captured — the failure ledger is "
            f"capped, NOT complete, and never silently truncated. Run NOT terminated by the cap."
        )

    def _enter_resync(self, reason: str) -> None:
        """
        Begin the no-emission window (FR-018a(d)).

        Discards the local book and requests a fresh snapshot. NO MarketState may
        be emitted until that snapshot is applied AND its checksum validates. An
        unverified book must not price anything (Principle V).

        WO-014c-2 §2: OPEN a CHECKSUM_RESYNC gap on the False->True transition only. A
        subsequent failure while already awaiting resync re-enters here but must NOT open a
        duplicate gap (the window is one continuous no-emission interval until a fresh
        snapshot validates). This is the cleanest open site in the codebase — an explicit flag.
        """
        newly_opening = not self._awaiting_resync
        self._awaiting_resync = True
        self._log_error(
            f"CHECKSUM_RESYNC: {reason}. Book discarded; "
            f"no MarketState until resync validates."
        )
        self._discard_book()
        self._request_snapshot()
        if newly_opening:
            import time
            self._open_gap(
                cause="CHECKSUM_RESYNC",
                reason_code="CHECKSUM_RESYNC",
                open_monotonic=time.monotonic(),
                detail=f"checksum resync: {reason}",
            )

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
            # WO-014c-2 §3: capture the failure ON EVERY OCCURRENCE (never positionally — that
            # is what lost WO-008b-B's three failures). The full forensic artifact is persisted
            # so a run's blessing can rule wire-anomaly vs residual parse/apply bug.
            self._capture_checksum_failure(quote_update, computed_checksum)
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
        # WO-014c-2 §2: retain the venue wall-clock of the last VALIDATED frame, for a gap
        # record's corroborating open_server_ts (the AUTHORITATIVE bound stays monotonic). The
        # v2 wire carries it as an ISO string; a parsed datetime is also accepted.
        _ts = quote_update.timestamp
        if isinstance(_ts, datetime):
            self._last_frame_server_ts = _ts.isoformat()
        elif isinstance(_ts, str) and _ts:
            self._last_frame_server_ts = _ts

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
            self._websocket = new_websocket  # WO-014c-1 §B.2: pong observer probes the LIVE socket
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
        # WO-014c-2 §2: the trip means the gap(s) open when the reconnect ran will NEVER close
        # (venue presumed gone). Mark them TERMINAL — preserving each trigger cause and its
        # true OPEN (when emission actually stopped), stamping the terminal breaker reason code
        # and the retry ladder as the forensic tail. close stays None (+inf => default-deny
        # from open onward). A terminal gap is COMPLETE (a known open-ended gap), not an
        # incomplete-ledger deficit. Defensive fallback: if somehow no gap was open, record one
        # terminal VENUE_DISCONNECT so the trip is never an unrecorded gap.
        if self._gap_ledger is not None:
            if not self._open_gaps:
                import time
                self._open_gap(
                    cause="VENUE_DISCONNECT",
                    reason_code="RECONNECT_CIRCUIT_BREAKER_TRIPPED",
                    open_monotonic=time.monotonic(),
                    detail=f"breaker trip (no open gap at trip): {reason}",
                )
            for record in self._open_gaps:
                record.terminal = True
                record.reason_code = "RECONNECT_CIRCUIT_BREAKER_TRIPPED"
                record.retry_ladder = list(ladder)
                # WO-014c-3 §0.1: TERMINAL flush — the trip is the event the ledger most needs
                # to survive; write it durably here, before the exception leaves this method.
                self._persist_gap_event(record, "terminal")
            self._gap_ledger.frames_captured = frames
            self._gap_ledger.evidentiary_bounds = self.capture_terminated["evidentiary_bounds"]
            self._persist_write({
                "event": "terminal_summary",
                "reason_code": "RECONNECT_CIRCUIT_BREAKER_TRIPPED",
                "trip_time": trip_time,
                "frames_captured": frames,
                "evidentiary_bounds": self._gap_ledger.evidentiary_bounds,
            })
            self._open_gaps = []
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
            # WO-023 §2 (D34-2): resolve the transport factory LATE — the injected _connect_fn if
            # one was given, else the module attribute `websockets.connect` (which an existing test
            # may have monkeypatched). Late resolution is what keeps module-level patching working
            # while the field still lets the gate name a default vs injected transport (see __init__).
            connect_fn = self._connect_fn or websockets.connect
            return await connect_fn(
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

    async def _observe_protocol_pong(self, record: "PongRecord") -> None:
        """
        WO-014c-1 §B.2 — PROTOCOL-level pong observer. Every interval it issues ws.ping(),
        which sends an RFC 6455 §5.5.2 control frame (the WebSocket-STANDARD ping — the layer
        whose timeout threw the 1011), NOT Kraken's application {"method":"ping"} of §1.2. The
        future ws.ping() returns resolves to the round-trip latency; per-ping RTT gives the
        DISTRIBUTION the branches need (not the `latency` scalar). Random payload (default)
        never collides with the library's own keepalive ping. Same time.monotonic() clock (§A.2).

        RULED COUNTER DISCIPLINE (carryover #1): a ping the task FAILED TO SEND (starved) is
        GAPPINESS (expected − sent); a ping SENT with no pong within the absent timeout is an
        ABSENT PONG — a SIGNAL (Branch 1/3), NEVER gappiness.

        ACTIVE-PROBE LIMIT (declared, not discovered):
          - MEASURED: whether Kraken answers OUR ping.
          - INFERRED: that Kraken answers THE LIBRARY'S keepalive ping — sound (identical RFC
            6455 control-frame type, identical peer handler) but an INFERENCE, so labelled.
          - CANNOT EXCLUDE: venue-side SELECTIVE behavior — Kraken deprioritizing keepalive-
            class traffic under load while answering active probes, or the reverse. Almost
            certainly negligible (same peer code path); stated as what it cannot exclude.
          - COMPENSATING ADVANTAGE: 1s cadence gives ~20x the library's 20s-keepalive samples,
            making pong latency a time series correlatable against message rate + lag.
          - PROBE LOAD: 1 ping/s against ~26 msg/s inbound is negligible; Kraken publishes no
            ping rate limit (documented silence) — noted so no one suspects the probe perturbed
            the measurement.
        """
        import asyncio
        import time

        interval = record.interval_s
        absent_timeout = record.absent_timeout_s
        record.started_monotonic = time.monotonic()
        inflight = []  # (sent_ts, pong_waiter) not yet resolved
        try:
            while True:
                await asyncio.sleep(interval)
                now = time.monotonic()
                # Resolve in-flight pings WITHOUT blocking the send cadence — this is why absent
                # pongs cannot shrink pings_sent (and so cannot be misread as gappiness): the send
                # loop stays paced at `interval` no matter how slow/absent the pongs are.
                still = []
                for sent_ts, waiter in inflight:
                    if waiter.done():
                        try:
                            record.pongs_received += 1
                            record.samples.append((sent_ts, waiter.result()))  # RTT in seconds
                        except Exception:
                            record.pongs_absent += 1
                            record.samples.append((sent_ts, None))
                    elif now - sent_ts >= absent_timeout:
                        record.pongs_absent += 1            # a SIGNAL (Branch 1/3), never gappiness
                        record.samples.append((sent_ts, None))
                        waiter.cancel()
                    else:
                        still.append((sent_ts, waiter))
                inflight = still
                # Send the next ping. Each iteration is one ATTEMPT; a ws.ping() that raises is
                # a MISSED SEND -> gappiness (attempted - sent). It is NOT an absent pong.
                record.pings_attempted += 1
                try:
                    pong_waiter = await self._websocket.ping()  # RFC 6455 §5.5.2 control frame, random payload
                except Exception:
                    continue
                record.pings_sent += 1
                inflight.append((time.monotonic(), pong_waiter))
        finally:
            record.ended_monotonic = time.monotonic()
            for _sent_ts, waiter in inflight:
                waiter.cancel()

    def _check_instruments_gappy(self, lag_record=None, pong_record=None) -> bool:
        """
        WO-014c-1 branch 5, RE-RULED WO-016 §B (D27). The LAG sampler is judged by a
        THREE-COMPONENT OR-GATE — each component owns one failure mode by construction, so the
        retired single missed_fraction gate (overhead-biased AND degradation-sensitive: the same
        property, D27) is replaced without losing sensitivity to any mode:
          (1) DISCRETE  — recorded missed-wakes (>=200ms) over > RECORDED_GAP_VOID_FRACTION,
          (2) SPIKY     — lag >100ms on > ELEVATED_LAG_VOID_FRACTION of samples,
          (3) UNIFORM   — mean-cycle drift above the FROZEN observed baseline (only slowdown fires;
                          the mode that escapes (1) and (2), e.g. a uniform 199ms cycle).
        Any component VOIDs the QUANTITATIVE discrimination; the gap timestamps stay REPORTED
        evidence (they NOMINATE starvation — only clean instruments CONVICT). The pong observer
        keeps its discrete missed-SENDS gate (ABSENT pongs are a signal, excluded by construction).
        Emits INSTRUMENTS_GAPPY naming the component. Returns True when any check trips.
        """
        gappy = False
        if lag_record is not None:
            rgf = lag_record.recorded_gap_fraction
            if rgf > self.RECORDED_GAP_VOID_FRACTION:
                self._log_error(
                    f"INSTRUMENTS_GAPPY: lag DISCRETE — recorded missed-wake fraction {rgf:.1%} > "
                    f"{self.RECORDED_GAP_VOID_FRACTION:.0%} ({len(lag_record.gaps)} gap(s) >=200ms); "
                    f"quantitative discrimination VOID. Gaps retained as reported evidence "
                    f"(may NOMINATE starvation; only clean instruments convict)."
                )
                gappy = True
            elf = lag_record.elevated_lag_fraction(self.ELEVATED_LAG_THRESHOLD_SECONDS)
            if elf > self.ELEVATED_LAG_VOID_FRACTION:
                self._log_error(
                    f"INSTRUMENTS_GAPPY: lag SPIKY — {elf:.1%} of samples elevated (>100ms lag) > "
                    f"{self.ELEVATED_LAG_VOID_FRACTION:.0%}; quantitative discrimination VOID."
                )
                gappy = True
            base = self._mean_cycle_baseline_s   # WO-016 §D28: host-scoped (runner-set) baseline
            drift = (lag_record.mean_cycle_s - base) / base if base > 0 else 0.0
            if drift > self.MEAN_CYCLE_DRIFT_VOID_FRACTION:
                self._log_error(
                    f"INSTRUMENTS_GAPPY: lag UNIFORM — mean cycle {lag_record.mean_cycle_s*1000:.1f}ms "
                    f"drifted {drift:+.0%} above the frozen {base*1000:.3f}ms baseline > "
                    f"{self.MEAN_CYCLE_DRIFT_VOID_FRACTION:.0%}; quantitative discrimination VOID."
                )
                gappy = True
        if (pong_record is not None
                and pong_record.missed_send_fraction > self.INSTRUMENTS_GAPPY_VOID_FRACTION):
            self._log_error(
                f"INSTRUMENTS_GAPPY: pong observer failed {pong_record.missed_sends} of "
                f"{pong_record.pings_attempted} attempted SENDS "
                f"({pong_record.missed_send_fraction:.0%} > {self.INSTRUMENTS_GAPPY_VOID_FRACTION:.0%}); "
                f"quantitative discrimination VOID. Absent pongs ({pong_record.pongs_absent}) are a "
                f"SIGNAL, not gappiness (Branch 1/3)."
            )
            gappy = True
        return gappy

    def _assert_clock_transport_gate(self, incoherent_clocks_allowed: str) -> None:
        """
        WO-023 §4 (RULINGS D34-2/D34-3) — the PRE-CONNECTION clock/transport gate.

        Inspects the THREE constructor-injected fields (_wall_clock, _monotonic_clock, _connect_fn)
        and refuses, BEFORE any connection, a clock injection that violates either assertion:

          (1) COUPLING — a fake clock is permitted ONLY where the transport is NOT the REAL one.
              The ruled invariant (D34, verbatim in the reason code's docstring) is "A REAL TRANSPORT
              WITH A FAKE CLOCK REFUSES" — REAL is an IDENTITY fact about the resolved callable, not
              the sentinel fact of whether _connect_fn was injected. So this test mirrors the
              clock-side identity tests: resolve the transport late (exactly as _connect does), then
              compare `resolved is _REAL_CONNECT` (the genuine callable captured at import). Keying on
              `_connect_fn is None` would let `connect_fn=websockets.connect` (non-default by config,
              REAL by identity) through — a fake clock on a real socket (WO-023 §2b correction).
              _REAL_CONNECT is captured at import, NOT read from the live module attribute, because a
              module-patching test replaces that attribute; comparing against the live attribute would
              read a patched fake as real and refuse 13 currently-green tests.

          (2) COHERENCE — injected clocks MUST be the coherent one-source pair, UNLESS the run
              declares the incoherence BY NAME via incoherent_clocks_allowed. The gate never INFERS
              the exception from the injection pattern (RULING D34-3: inference is vigilance; every
              incoherent run is greppable at its call site).

              COHERENCE-TOKEN DECLARATION (WO-023 §2b): coherence is PROVED by a shared
              `_coherence_token` attribute that the FakeClock harness stamps on BOTH its `wall` and
              `monotonic` readers (the token IS the one FakeClock instance — the single source). The
              gate reads the token; it does NOT infer coherence from the clocks' VALUES or behaviour.
              A clock pair without a shared token is NOT coherent regardless of how it behaves — two
              independently-constructed clocks that happen to agree numerically are still two sources.
              This is deliberate: proving one source is the only alternative to inferring it, and
              D34-3 refused inference. `_coherence_token` is a production-read attribute whose only
              producer is the test fixture; that is accepted and declared here, not incidental.

        Refuses with CLOCK_INJECTION_REFUSED, the payload naming WHICH assertion failed. Default
        clocks (no injection) return immediately — the path every real run and every non-suspend
        test takes.
        """
        import time

        wall_injected = self._wall_clock is not None
        mono_injected = self._monotonic_clock is not time.monotonic
        if not (wall_injected or mono_injected):
            return  # no injected clock — the default path (real runs + every non-suspend test)

        # (1) COUPLING — test the TRANSPORT BY IDENTITY (symmetric with the clock-side identity tests
        # above), NOT by injection status. Resolve late (unchanged from _connect), then compare
        # against the genuine callable captured at import. A REAL transport with a fake clock refuses.
        resolved = self._connect_fn or websockets.connect
        if resolved is _REAL_CONNECT:
            raise ValueError(
                "CLOCK_INJECTION_REFUSED: COUPLING — a fake clock is permitted ONLY where the "
                "transport is not the REAL one; a REAL transport with a fake clock refuses, "
                "pre-connection. Inject a non-real transport through connect_fn, or drop the clock."
            )

        # (2) COHERENCE — the injected clocks must be the one-source coherent pair (shared token),
        # unless the run declares the incoherence by name (never inferred — RULING D34-3).
        wall_token = getattr(self._wall_clock, "_coherence_token", None)
        mono_token = getattr(self._monotonic_clock, "_coherence_token", None)
        coherent = (wall_injected and mono_injected
                    and wall_token is not None and wall_token is mono_token)
        if not coherent and not incoherent_clocks_allowed:
            raise ValueError(
                "CLOCK_INJECTION_REFUSED: COHERENCE — injected clocks must be the coherent "
                "wall+monotonic pair from ONE source (D25: monotonic orders, wall locates). An "
                "incoherent pair is permitted ONLY when declared by name via "
                "incoherent_clocks_allowed=<reason>; the gate never infers it (RULING D34-3)."
            )

    async def get_live_market_data(self, duration_seconds: float,
                                   incoherent_clocks_allowed: str = "") -> AsyncIterator[MarketState]:
        """
        Stream MarketStates from the LIVE Kraken v2 public book channel.

        Transport only. Every frame goes to process_raw_frame() unmodified.

        Args:
            duration_seconds: hard bound on the capture window (an INTERVAL — measured on the
                monotonic deadline clock; D25).
            incoherent_clocks_allowed: WO-023 §4.3 (RULING D34-3) — an EXPLICIT, per-invocation
                declaration that this run injects an INCOHERENT wall/monotonic pair on purpose
                (the sole enumerated customer is the suspend detector, which tests wall-vs-monotonic
                divergence and so cannot use a coherent pair). The gate reads it BY NAME and never
                infers the exception from the injection pattern. Empty = coherence is enforced.

        Raises:
            ValueError: if called on a fixture-mode adapter (no silent switching); or
                CLOCK_INJECTION_REFUSED, pre-connection, if the injected clock/transport
                configuration fails the coupling or coherence assertion (WO-023 §4).
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

        # WO-014c-3 addendum C: REFUSE a live capture whose gap ledger would not be persisted,
        # unless the caller EXPLICITLY opts out. An unpersisted live ledger silently loses every
        # gap on a kill/trip — the vigilance-enforced guarantee the persistence fix closed, and
        # the last thing between a 60-minute run and a silently unrecorded ledger.
        if self._gap_persist_path is None and not self._persistence_optional:
            raise ValueError(
                "GAP_PERSIST_UNCONFIGURED: live capture started with gap-ledger persistence "
                "UNSET. Set _gap_persist_path to an append-only JSONL path, or (fixtures/tests "
                "only) set _persistence_optional=True to acknowledge running without a durable "
                "ledger. Refusing to run a silently-unpersisted live capture."
            )

        # WO-023 §2 (RULINGS D34-2/D34-3): the PRE-CONNECTION clock/transport gate. Same placement
        # discipline as GAP_PERSIST_UNCONFIGURED above — it refuses BEFORE any connection attempt,
        # so a fake clock can never drive a real socket even for one frame.
        self._assert_clock_transport_gate(incoherent_clocks_allowed)

        self._raw_received = 0
        self._market_states_emitted = 0
        self._start_time = time.time()
        self.captured_frames = []
        self.captured_raw_text = []
        # WO-014c-1 §B.1: the event-loop LAG sampler (PRIMARY starvation discriminator) runs
        # concurrently for this capture on the shared time.monotonic() clock (§A.2).
        self._lag_record = LagSampleRecord(interval_s=self.LAG_SAMPLE_INTERVAL_SECONDS)
        # WO-014c-1 §B.2: the protocol-level pong observer runs concurrently on the same clock.
        self._pong_record = PongRecord(
            interval_s=self._ping_sample_interval, absent_timeout_s=self._pong_absent_timeout,
        )
        # WO-014c-1 §B.3: per-second receive-to-process latency + message-rate completeness.
        self._throughput_record = ThroughputRecord(bucket_seconds=1.0)
        lag_task = None
        pong_task = None

        websocket = await self._connect()
        self._websocket = websocket   # kept current on reconnect so the pong observer probes it
        logger.info(
            "[kraken_v2_book] CONNECTED mode=%s venue=%s url=%s",
            self._mode, self.venue_name, self.WS_URL,
        )

        try:
            subscribe = self._build_subscribe_message()
            await websocket.send(json.dumps(subscribe))
            logger.info("[kraken_v2_book] subscribed: %s", json.dumps(subscribe))
            lag_task = asyncio.create_task(self._sample_event_loop_lag(self._lag_record))
            pong_task = asyncio.create_task(self._observe_protocol_pong(self._pong_record))

            # WO-023 §2 (RULING D34-1): a duration is an INTERVAL; D25 puts intervals on the
            # MONOTONIC clock. The deadline therefore runs on _monotonic_clock (default
            # time.monotonic), NOT on _wall_clock — which is the suspend detector's wall and can
            # jump (line 1136). This keeps the capture window immune to a wall-clock jump and makes
            # the deadline deterministically driveable through the injected clock.
            deadline = self._monotonic_clock() + duration_seconds
            # WO-014b-2 §1.1/§1.2 keepalive clocks (monotonic). last_frame is refreshed by
            # ANY received frame (book, heartbeat, or pong); last_ping paces the app ping.
            last_frame = time.monotonic()
            last_ping = time.monotonic()
            # WO-014c-2 §2: the ONCE-per-run (wall, monotonic) anchor for the gap ledger,
            # captured ATOMICALLY — two adjacent reads with NO await between them, so
            # cooperative scheduling cannot interleave and the wall<->monotonic skew is bounded
            # to sub-microsecond CPU time, not load (probe 2b). It is the ONLY wall clock in the
            # gap records; every monotonic bound is calendar-located via this pair.
            anchor_monotonic = time.monotonic()
            anchor_wall = datetime.now(UTC).isoformat()
            # WO-015 addendum A: the wall EPOCH paired atomically with the monotonic anchor, for
            # host-suspend detection (per-iteration wall-delta vs monotonic-delta divergence).
            _wall = self._wall_clock or time.time
            anchor_wall_epoch = _wall()
            susp_prev_wall = anchor_wall_epoch
            susp_prev_mono = anchor_monotonic
            self._gap_seq = 0
            self._open_gaps = []
            self._gap_ledger = GapLedger(
                run_wall_anchor=anchor_wall,
                run_monotonic_anchor=anchor_monotonic,
                run_start_monotonic=anchor_monotonic,
            )
            self._throughput_record.start_monotonic = anchor_monotonic
            # WO-014c-3 §0.2: reset failure-capture retention state per capture (count, kept
            # captures, byte total, and the cap-announced flag) so a reused adapter never carries
            # a prior run's cap or counts.
            self._checksum_failure_count = 0
            self._checksum_failure_captures = []
            self._checksum_failure_summaries = []
            self._checksum_capture_bytes = 0
            self._checksum_capture_capped = False
            # WO-014c-3 §0.1: open the append-only ledger file (if persistence is enabled) and
            # write the run anchor FIRST, so even a run that dies seconds in leaves the anchor +
            # any gaps on disk.
            self._open_gap_persistence()
            self._persist_write({
                "event": "run_start",
                "run_wall_anchor": anchor_wall,
                "run_monotonic_anchor": anchor_monotonic,
                "run_start_monotonic": anchor_monotonic,
                "venue": self.venue_name,
                "mode": self._mode,
            })
            while self._monotonic_clock() < deadline:   # WO-023 §2 (D34-1): deadline on monotonic
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

                # WO-015 addendum A: HOST-SUSPEND DETECTION. Compare this iteration's WALL delta
                # against its MONOTONIC delta. In normal operation both measure the same interval
                # (divergence ~0); a host suspend counts on one clock but not the other, so the
                # divergence jumps by ~the suspend duration in a single iteration. Beyond the
                # drift bound that is a suspend, not drift (WO-014c-3 §0.3). Record a HOST_SUSPEND
                # gap and report LOUDLY, but DO NOT terminate (diagnostic role — the corpus WO
                # makes it window-invalidating). Checked BEFORE heartbeat-absence so the suspend
                # is attributed to its own cause even though the link may also need a reconnect.
                _now_wall = _wall()
                _wall_delta = _now_wall - susp_prev_wall
                _mono_delta = mono - susp_prev_mono
                _divergence = abs(_wall_delta - _mono_delta)
                if _divergence > self._host_suspend_divergence:
                    self._log_error(
                        f"HOST_SUSPEND: wall/monotonic divergence {_divergence:.1f}s "
                        f"(wall +{_wall_delta:.1f}s vs monotonic +{_mono_delta:.1f}s in one "
                        f"iteration) exceeds the {self._host_suspend_divergence:.0f}s drift bound "
                        f"— a host suspend, not drift. This window is CONTAMINATED: a suspend is "
                        f"indistinguishable from catastrophic starvation. Recorded (diagnostic); "
                        f"the run continues."
                    )
                    _susp_gap = self._open_gap(
                        cause="HOST_SUSPEND",
                        reason_code="HOST_SUSPEND",
                        open_monotonic=susp_prev_mono,
                        detail=(
                            f"host suspend: divergence {_divergence:.1f}s "
                            f"(wall +{_wall_delta:.1f}s vs monotonic +{_mono_delta:.1f}s) "
                            f"> {self._host_suspend_divergence:.0f}s drift bound"
                        ),
                    )
                    # Diagnostic, not terminal: close it immediately at resume (the suspend
                    # window is [prev, now]); emission continues.
                    if _susp_gap is not None:
                        _susp_gap.close_monotonic = mono
                        _susp_gap.resumed = True
                        self._persist_gap_event(_susp_gap, "resolved")
                        if _susp_gap in self._open_gaps:
                            self._open_gaps.remove(_susp_gap)
                susp_prev_wall = _now_wall
                susp_prev_mono = mono

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
                    # WO-014c-2 §2: OPEN the keepalive gap at the LAST FRAME received (when
                    # emission actually stopped, not when the threshold tripped). The unified
                    # close hook closes it at the first post-reconnect validated emit — this
                    # is the close hook the absence path lacked (probe 2a).
                    self._open_gap(
                        cause="KEEPALIVE_RECONNECT",
                        reason_code="HEARTBEAT_ABSENCE",
                        open_monotonic=last_frame,
                        detail=f"heartbeat absence ({mono - last_frame:.1f}s without a frame)",
                    )
                    websocket = await self._perform_reconnect(
                        websocket,
                        reason=f"heartbeat absence ({mono - last_frame:.1f}s without a frame)",
                    )
                    self._attach_ladder_to_open_gaps()
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
                        # WO-014c-2 §2 (cause 4b): a dead socket detected on send is a venue
                        # disconnect. Open the gap at the last frame received; attach the
                        # reconnect ladder after recovery.
                        self._open_gap(
                            cause="VENUE_DISCONNECT",
                            reason_code="VENUE_CONNECTION_CLOSED",
                            open_monotonic=last_frame,
                            detail=f"application ping send failed ({exc})",
                        )
                        websocket = await self._perform_reconnect(
                            websocket, reason="application ping send failed",
                        )
                        self._attach_ladder_to_open_gaps()
                        last_frame = time.monotonic()
                        last_ping = time.monotonic()
                        continue
                    last_ping = time.monotonic()

                # WO-023 §2 (D34-1) — CODE-WINS FINDING (Checkpoint A): the §1 enumeration named
                # only two deadline lines (2388 set, 2434 guard), but `deadline` has a THIRD
                # consumer HERE. `deadline` is now a MONOTONIC value; subtracting wall-clock
                # time.time() mixed the two clocks (monotonic minus epoch = a huge negative
                # `remaining`) -> immediate break -> raw=0 frames. A deadline is coherent only when
                # every consumer reads the SAME clock, so this third site routes through
                # _monotonic_clock too — the forced completion of "the deadline is on monotonic".
                remaining = deadline - self._monotonic_clock()
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
                    # WO-014c-2 §2 (cause 4c): explicit venue close. Open the gap at the last
                    # frame received; attach the reconnect ladder after recovery.
                    self._open_gap(
                        cause="VENUE_DISCONNECT",
                        reason_code="VENUE_CONNECTION_CLOSED",
                        open_monotonic=last_frame,
                        detail=f"venue closed the connection unexpectedly ({exc})",
                    )
                    websocket = await self._perform_reconnect(
                        websocket, reason=f"venue closed the connection unexpectedly ({exc})",
                    )
                    self._attach_ladder_to_open_gaps()
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
                    # WO-008b-A3 §1.1 / WO-017 §1.1: PRESERVE the venue's transmitted
                    # digits AND retain the token text itself. parse_float/parse_int
                    # receive the RAW TEXT of each number and construct a WireDecimal,
                    # so Kraken's "0.00005100" stays "0.00005100" both as a value and on
                    # .wire. Plain json.loads would float it and Decimal(str(float)) would
                    # render "0.000051", dropping the trailing zeros the CRC32 digits
                    # require. We do NOT re-render into an assumed format (e.g. fixed 8dp):
                    # that would encode an uncited assumption about venue behaviour (rule
                    # 0.1e). The retained wire string is what the checksum consumes
                    # (WO-017 §1.3) — there is no rendering step left to be wrong.
                    raw_frame = json.loads(
                        message, parse_float=WireDecimal, parse_int=WireDecimal
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
                # WO-014c-1 §B.3: receive-to-process latency (last_frame = recv return) and the
                # per-second message count, on the shared monotonic clock.
                done_mono = time.monotonic()
                self._throughput_record.record(last_frame, done_mono)

                # WO-014c-2 §2: UNIFIED CLOSE HOOK. A validated MarketState means emission
                # resumed, which closes EVERY open gap at once (probe-1 collective close). This
                # single hook serves keepalive, checksum, and venue-disconnect gaps.
                if market_states:
                    self._close_open_gaps(done_mono)

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
                    # WO-014c-2 §2: the 5th-checksum-failure escalation opened a CHECKSUM_RESYNC
                    # gap in _enter_resync; attach this reconnect's ladder to it.
                    self._attach_ladder_to_open_gaps()
                else:
                    await self._maybe_resubscribe(websocket)

                # LAYER 4: yield boundary.
                for market_state in market_states:
                    self._market_states_emitted += 1
                    yield market_state

        finally:
            self._running = False
            # WO-014c-1 §B.1/§B.2: stop the instrument tasks, finalize their records, and report
            # gappiness (branch 5). Cancelling stamps ended_monotonic in each task's own finally.
            for _task in (lag_task, pong_task):
                if _task is not None:
                    _task.cancel()
                    try:
                        await _task
                    except asyncio.CancelledError:
                        pass
            self._throughput_record.end_monotonic = time.monotonic()
            self._check_instruments_gappy(self._lag_record, self._pong_record)
            # WO-014c-2 §2: finalize the gap ledger and report its own integrity. A gap that was
            # DETECTED (opened) but neither closed (emission never resumed) nor tripped the
            # breaker (terminal) is INCOMPLETE — the capture ended with it open. State it
            # loudly (GAP_LEDGER_INCOMPLETE), never drop it: a silently unrecorded/uncompleted
            # gap is the exact failure this WO exists to prevent. The records are retained.
            if self._gap_ledger is not None:
                self._gap_ledger.run_end_monotonic = time.monotonic()
                self._gap_ledger.frames_captured = len(self.captured_raw_text)
                incomplete = self._gap_ledger.incomplete
                if incomplete:
                    ids = ", ".join(
                        f"#{g.gap_id}({g.cause}, opened@{g.open_monotonic:.4f}mono)"
                        for g in incomplete
                    )
                    self._log_error(
                        f"GAP_LEDGER_INCOMPLETE: {len(incomplete)} of "
                        f"{self._gap_ledger.gaps_detected} recorded gap(s) opened but never "
                        f"closed or terminated — the capture ended with them open. Retained as "
                        f"open-ended (default-deny from open onward), NOT dropped: [{ids}]."
                    )
                # WO-014c-3 §0.1: FINALIZE flush (always runs unless SIGKILL) — the run summary,
                # then close the ledger file. Incremental writes already made the per-gap records
                # durable; this records the clean end and the integrity accounting.
                self._persist_write({
                    "event": "run_end",
                    "run_end_monotonic": self._gap_ledger.run_end_monotonic,
                    "frames_captured": self._gap_ledger.frames_captured,
                    "gaps_detected": self._gap_ledger.gaps_detected,
                    "incomplete": len(self._gap_ledger.incomplete),
                    "checksum_failures_total": self._checksum_failure_count,
                    "checksum_captures_kept": len(self._checksum_failure_captures),
                    "checksum_capture_capped": self._checksum_capture_capped,
                })
                self._close_gap_persistence()
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

    def get_gap_ledger(self) -> Optional["GapLedger"]:
        """WO-014c-2 §2: the data-gap ledger for the last live capture (None if no capture
        has run). The default-deny corpus reader (a later WO) consumes gaps + the run anchor
        + the completeness accounting from here; it is NOT built in this WO."""
        return self._gap_ledger

    def get_checksum_failure_captures(self) -> list:
        """WO-014c-2 §3: the full, redacted forensic artifacts KEPT this capture (the first N by
        count/bytes; empty if none). Captured on every occurrence until the §0.2 cap binds, never
        positionally sampled — the corpus-blessing gate that rules wire-anomaly vs parse/apply bug.
        Pair with get_checksum_failure_count(): captures may be capped, the count never is."""
        return list(self._checksum_failure_captures)

    def get_checksum_failure_count(self) -> int:
        """WO-014c-3 §0.2(b): the TOTAL number of checksum failures seen this capture — NEVER
        capped (the count is itself a finding). If it exceeds len(get_checksum_failure_captures())
        the capture cap bound and FAILURE_CAPTURE_CAPPED was announced."""
        return self._checksum_failure_count

    def get_checksum_failure_summaries(self) -> list:
        """WO-014c-3 addendum A: the one-line summaries (utc, expected/computed checksum, seq
        position) for failures BEYOND the capture cap — so a cluster's phases are visible even
        when full artifacts were capped. Empty until the cap binds."""
        return list(self._checksum_failure_summaries)

    async def _trigger_pause_for_test(self) -> None:
        """
        Trigger pause for testing purposes (T033).

        This method simulates book unavailability for testing pause behavior.
        """
        self.pause()
        # In production, this would be triggered by WebSocket disconnection


# --- WO-010 §5: self-registration ---------------------------------------
from trading.data.adapters.registry import register  # noqa: E402


@register("kraken_v2", live_capture=True)
def _build_kraken_v2(decision_logger=None, mode=KrakenV2BookAdapter.MODE_FIXTURE,
                     gap_persist_path=None) -> "KrakenV2BookAdapter":
    """Builder invoked by the registry when DATA_SOURCE=kraken_v2.

    WO-015: the registry is the SOLE adapter-resolution path (Principle IV/VII), so the LIVE
    adapter is built HERE (via the factory's create_live_capture_feed passing mode='live'),
    never by a caller importing this module. `gap_persist_path` configures the live gap ledger
    at construction so the live-capture runner need not touch adapter internals.
    """
    adapter = KrakenV2BookAdapter(mode=mode)
    if gap_persist_path is not None:
        adapter._gap_persist_path = str(gap_persist_path)
    return adapter
