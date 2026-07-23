"""
Decision Logging Module

Records every decision with reason codes for audit trail.

Constitutional Principles:
- VIII. Total Observability & Provenance: Every decision logged
- IX. Secrets and Safety Rails: No secrets in logs

Valid Reason Codes (LAYER_VERB_DETAIL vocabulary):
- Data layer: CHECKSUM_RESYNC, PAUSE_ON_BOOK_UNAVAILABLE, RECONNECT_FLAG_STRANDED,
  RECONNECT_CIRCUIT_BREAKER_TRIPPED, HEARTBEAT_ABSENCE, VENUE_CONNECTION_CLOSED,
  INSTRUMENTS_GAPPY
  (SEQUENCE_GAP_RESNAPSHOT withdrawn 2026-07-19, WO-009b — see below)
- Cost model: ABNORMAL_SPREAD_REJECT
- Risk layer: PASS, CLAMP, VETO, KILL_SWITCH_ENGAGED
- Strategy layer: NO_SIGNAL, LONG_SIGNAL, SHORT_SIGNAL
- Execution layer: ORDER_FILLED, ORDER_REJECTED,
  EXEC_NO_MARKET_STATE, EXEC_MARKET_STATE_TIMESTAMP_MISSING, EXEC_STALE_MARKET_STATE
  (paper-venue staleness guards; declared WO-011 §5)
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional
from enum import Enum
import json


class Layer(Enum):
    """Decision layer identifiers."""
    STRATEGY = "STRATEGY"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    BACKTEST = "BACKTEST"


# Valid reason codes per layer (documented for reference)
VALID_REASON_CODES = {
    "DATA": [
        # WO-018 §2: feed-lifecycle + per-frame reason codes the loop/feed emit as reason_code=
        # keyword literals — invisible to the colon-form scan (the escape hatch). DECLARED (real
        # emitted audit vocabulary, Principle VIII). DATA_RECEIVED is emitted per MarketState with
        # event_type="MARKET_DATA_RECEIVED" (the same-fact overlap is a §6 finding, not a retire).
        "DATA_RECEIVED",  # a market-data frame was received and processed (live.py)
        "FEED_CONNECTED",  # feed transport connected (kraken_public)
        "FEED_MALFORMED_PAYLOAD",  # a received payload failed to parse
        "FEED_UNEXPECTED_PAYLOAD",  # a received payload was well-formed but unexpected
        "FEED_CONNECTION_CLOSED",  # feed transport closed
        "FEED_CONNECTION_ERROR",  # feed transport errored
        "CHECKSUM_RESYNC",  # T018: Reconnecting after 5 consecutive checksum failures
        # WO-016 §A (D27): REGRESSION SENTINEL (rule 0.1d — its trigger CANNOT occur while the
        # fixed-point render holds; legitimate, but labelled, not dressed as a data-path guard).
        # Raised by compute_checksum when the ASSEMBLED checksum input contains scientific
        # notation ('E'/'e'). The interim render fix guards one site; this guards the INVARIANT
        # at all of them — "checksum input contains no synthesized notation" — converting any
        # future formatting regression from a silent CRC mismatch into a LOUD NAMED failure. It
        # outlives the wire-string WO because it guards the invariant, not the implementation.
        "CHECKSUM_INPUT_SYNTHESIZED_NOTATION",
        # WO-017 §1.4 (load-bearing NO-FALLBACK guard): raised when a ladder level reaches the
        # checksum path without a retained wire string — either at the parse origin
        # (_retain_wire) or at the consumption point (_current_ladder_strings/_wire_pair). The
        # checksum consumes the venue's TRANSMITTED token EXCLUSIVELY (FR-018a(f), satisfied
        # literally); a level with no such token cannot be checksummed correctly, so the code
        # REFUSES rather than synthesize one by re-rendering. A silent fallback would reintroduce
        # the exact scientific-notation defect class this WO closes structurally and would be
        # undetectable until some future edge (0.1g: an unimplementable path fails loudly, never
        # quietly succeeds). Prefix-free against CHECKSUM_INPUT_SYNTHESIZED_NOTATION and
        # CHECKSUM_RESYNC (CHECKSUM_WIRE_ is a unique stem).
        "CHECKSUM_WIRE_STRING_MISSING",
        # WO-014b-1: raised by get_live_market_data when a reconnect was requested
        # (_reconnect() set _pending_reconnect at 5 consecutive checksum failures) but
        # the transport failed to effect it before the next loop boundary. Silent
        # non-action recovery is the WO-008b-B defect class; this code makes the
        # watchdog's loud failure part of the audit vocabulary (Principle VIII).
        "RECONNECT_FLAG_STRANDED",
        # WO-014b-2 §2: raised when reconnect reopen attempts exceed the circuit-breaker
        # threshold within its rolling window — the venue is presumed gone and the live
        # capture STOPS LOUDLY (Ruling B) rather than retrying into an undisclosed
        # multi-hour hole. Carries a forensic tail (Principle VIII).
        "RECONNECT_CIRCUIT_BREAKER_TRIPPED",
        # WO-014b-2 §1.3: logged when the venue closes the connection UNEXPECTEDLY (abnormal
        # WS close code, e.g. 1011 protocol keepalive-ping timeout) — routed into reconnect
        # rather than ending the capture. A clean/normal close is an expected shutdown and is
        # NOT logged with this code (it does not reconnect).
        "VENUE_CONNECTION_CLOSED",
        # WO-014c-1 §B.1 / branch 5: logged when the event-loop lag sampler missed more than
        # the VOID fraction of its expected samples — the instrument starved itself, so the
        # QUANTITATIVE discrimination is VOID (the gap timestamps remain reported evidence that
        # may NOMINATE the starvation hypothesis; only clean instruments CONVICT). Declared now
        # (approved Q4) so the completeness guard stays green and the re-run is never blocked
        # by a missing code at the moment it needs to report one.
        "INSTRUMENTS_GAPPY",
        # WO-014b-2 §1.1: logged by the transport when no frame of any kind (heartbeat,
        # data, or pong) has arrived within the heartbeat-absence threshold — the
        # connection is presumed dead and a reconnect is triggered (Kraken's own
        # liveness signal, applied at the application layer).
        "HEARTBEAT_ABSENCE",
        # WO-014c-2 §2: logged at capture end when the gap ledger holds a gap that was
        # DETECTED (opened) but neither closed (emission never resumed) nor terminal (breaker
        # trip) — the capture ended with it open. The record is RETAINED as open-ended
        # (default-deny from open onward), never dropped: a silently uncompleted gap is the
        # exact failure gap recording exists to prevent. The ledger reports its own integrity
        # (Principle VIII). Prefix-free against the vocabulary (GAP_ is a unique stem).
        "GAP_LEDGER_INCOMPLETE",
        # WO-014c-3 §0.2: logged ONCE when failure-targeted checksum capture reaches its
        # retention cap (first-N by count OR total bytes, whichever binds first). Further
        # failures are still COUNTED (the count is itself a finding) but not fully captured.
        # Announces the truncation rather than silently dropping — a silently-truncated failure
        # ledger is the same defect class as the positional sampling §3 exists to kill. The cap
        # prevents DISK EXHAUSTION from ending a run; it does NOT terminate the run (the breaker
        # owns termination). Prefix-free (FAILURE_ stem is unique in the vocabulary).
        "FAILURE_CAPTURE_CAPPED",
        # WO-014c-3 addendum C: raised when a LIVE capture is started with gap-ledger
        # persistence UNCONFIGURED and not explicitly opted out. An opt-in durability feature
        # that silently no-ops when unset is a vigilance-enforced guarantee — the exact class
        # the persistence fix closed. The live path REFUSES to run a silently-unpersisted
        # ledger; fixture/test paths opt out explicitly. Prefix-free (GAP_PERSIST_ vs
        # GAP_LEDGER_ — neither prefixes the other).
        "GAP_PERSIST_UNCONFIGURED",
        # WO-016 §D28: raised by the live-capture runner's preflight when this HOST has no frozen
        # mean-cycle baseline (kraken_v2_book.MEAN_CYCLE_BASELINE_SECONDS is host-scoped — scheduler,
        # Python build, load). Without a matching baseline the UNIFORM drift component would convict
        # against a reference from another machine, so the run REFUSES to start (before any
        # connection) rather than limp or guess. New host => run tools/establish_mean_cycle_baseline.py.
        "MEAN_CYCLE_BASELINE_HOST_MISMATCH",
        # WO-013 follow-up item 1: raised when a mean-cycle measurement is differenced against a
        # STORED baseline whose INSTRUMENT differs (full-loop vs adapter-only). Instrument identity is
        # the SIXTH scope dimension (host / load / source / duration / resolution / INSTRUMENT); a
        # cross-instrument delta is UNINTERPRETABLE BY CONSTRUCTION (two boundaries), not merely noisy.
        # Same treatment as the host mismatch: a REFUSAL (not a warning — a warning is vigilance). The
        # loop-boundary ledger opens at entry zero and is never inherited via a cross-instrument delta.
        # Prefix-free vs MEAN_CYCLE_BASELINE_HOST_MISMATCH (…_INSTRUMENT_… vs …_HOST_… — neither prefixes).
        "MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH",
        # WO-015: raised by the live-capture runner's preflight when TRADING_ENV is not 'paper'
        # — a live capture must never run where the order-capable path could be reachable. The
        # refusal lives IN the runner (checklist-enforced rules are 0-for-N), before any component
        # is built. Prefix-free (LIVE_CAPTURE_ is a unique stem).
        "LIVE_CAPTURE_ENV_REFUSED",
        # WO-015 review: raised when a live capture is requested for a DATA_SOURCE adapter that
        # did NOT declare live capability (registry.is_live_capable). Refuses specifically and
        # BEFORE any connection, rather than connecting to the wrong venue (a hardcoded resolver
        # would have connected to mainnet regardless of DATA_SOURCE) or crashing on a rejected
        # live-only kwarg. Prefix-free (LIVE_CAPTURE_ENV_ vs LIVE_CAPTURE_UNSUPPORTED — neither
        # prefixes the other).
        "LIVE_CAPTURE_UNSUPPORTED",
        # WO-015 addendum A: the RULED FIFTH gap-ledger cause (a lead ruling, not an invented
        # fifth — so it does NOT trigger WO-014c-2's "STOP if a path fits none of the four").
        # Emitted when wall-vs-monotonic divergence exceeds the declared drift bound (WO-014c-3
        # §0.3: ~5s typical, <=43s worst case) — divergence beyond that is a host SUSPEND, not
        # drift. Without it, a mid-capture suspend MASQUERADES as catastrophic starvation and
        # sends the discrimination chasing pipeline architecture that isn't the problem. Role in
        # WO-015/re-run is DIAGNOSTIC (record + report loudly, do not terminate); the corpus WO
        # makes it load-bearing (invalidate the affected window). Prefix-free (HOST_ is unique).
        "HOST_SUSPEND",
        # WO-023 §2 (RULINGS D34-2/D34-3): raised PRE-CONNECTION by the clock/transport gate when
        # a clock is injected in a configuration the gate refuses. The ruled invariant, VERBATIM:
        #
        #     A NON-DEFAULT CLOCK IS PERMITTED ONLY WHERE THE TRANSPORT IS ALSO NON-DEFAULT.
        #     A REAL TRANSPORT WITH A FAKE CLOCK REFUSES, PRE-CONNECTION, WITH THE DECLARED CODE.
        #
        # A fake clock against the real websockets transport would drive a LIVE socket off a
        # SIMULATED clock — the deterministic-driving seam turned into a live-run hazard. The gate
        # also refuses an INCOHERENT clock pair (wall and monotonic not from one source) unless the
        # run declares the exception BY NAME, so D25 (monotonic orders, wall locates) holds for
        # every injected pair. The refusal payload names WHICH assertion failed (COUPLING vs
        # COHERENCE) — one code, diagnosable. Prefix-free (CLOCK_ is a unique stem).
        "CLOCK_INJECTION_REFUSED",
        # WITHDRAWN 2026-07-19 (WO-009b, ratified by project lead):
        #   "SEQUENCE_GAP_RESNAPSHOT"  # T018: Sequence gap detected, requesting fresh snapshot
        # The Kraken v2 PUBLIC book channel transmits no sequence number, so this
        # code's trigger CANNOT OCCUR. A reason code that can never legitimately
        # fire is a false guarantee (rule 0.1d). Superseded by CHECKSUM_RESYNC,
        # which covers the real detector and is strictly broader — checksum
        # divergence catches missed messages, misapplied updates, and our own
        # book-maintenance bugs, none of which a sequence counter can see.
        # Verified before removal: never emitted anywhere, no test referenced it.
        "PAUSE_ON_BOOK_UNAVAILABLE",  # T017: Book channel disconnected, paused
    ],
    "COST_MODEL": [
        "ABNORMAL_SPREAD_REJECT",  # T029: Spread >5% of price, trade rejected
    ],
    "RISK": [
        "PASS",  # Risk check passed
        "CLAMP",  # Position size reduced toward zero
        "VETO",  # Trade rejected by risk limits
        "KILL_SWITCH_ENGAGED",  # Kill switch activated
        # WO-018 §2: the DISTINCT reason codes the risk engine actually EMITS (engine.py REASON_*,
        # returned by check() and logged via reason_code=). They were emitted via VARIABLE
        # indirection (reason_code=<var>) and so lived outside the colon-form scan (the reason_code=
        # escape hatch). DECLARED, not retired: these ARE the canonical risk reason codes in use, and
        # Principle VI requires each clamp/veto to emit a DISTINCT code separable from a clean pass —
        # RISK_VETO_KILL_SWITCH vs RISK_VETO_DAILY_LOSS are different causes. (The bare PASS/CLAMP/VETO
        # above are emitted as EVENT_TYPES via RiskDecision.value; that overlap is a reported taxonomy
        # finding, WO-018 §6 — NOT license to retire these emitted reason codes here.)
        "RISK_PASS",  # clean pass (engine REASON_PASS)
        "RISK_CLAMP_MAX_POSITION",  # size clamped by the max-position limit
        "RISK_VETO_KILL_SWITCH",  # vetoed: kill switch engaged
        "RISK_VETO_DAILY_LOSS",  # vetoed: daily-loss limit
        "RISK_VETO_INVALID_INPUT",  # vetoed: invalid desired-position input
    ],
    "STRATEGY": [
        "NO_SIGNAL",  # No trading signal
        "LONG_SIGNAL",  # Long position signal
        "SHORT_SIGNAL",  # Short position signal
    ],
    "EXECUTION": [
        "ORDER_FILLED",  # Order successfully filled
        "ORDER_REJECTED",  # Order rejected by exchange
        # WO-018 §2: THE FILL EVENT the loop actually emits (live.py reason_code="EXEC_ORDER_FILLED",
        # event_type="ORDER_FILLED"). It was a reason_code= keyword literal invisible to the colon-form
        # scan — the decisive weight of this WO (the atom of every post-trade audit, Principle VIII).
        # DECLARED, not retired: EXEC_ is the execution-namespace convention (EXEC_NO_MARKET_STATE etc.).
        # Whether the emitted EXEC_ORDER_FILLED and the declared-but-event_type-only ORDER_FILLED should
        # be one code is a TAXONOMY finding for a ruling (WO-018 §6), not a rename to make in-WO.
        "EXEC_ORDER_FILLED",
        # Paper-venue staleness guards (WO-008a-R6). Declared in WO-011 §5: they
        # were raised in production (paper.py) but never declared — the exact
        # raised-but-undeclared gap the vocabulary-completeness check now closes.
        "EXEC_NO_MARKET_STATE",  # place_order before set_market_state
        "EXEC_MARKET_STATE_TIMESTAMP_MISSING",  # staleness-guard invariant violation
        "EXEC_STALE_MARKET_STATE",  # MarketState older than the staleness threshold
    ],
}


# WO-018 §3: the event_type namespace, now GOVERNED. Previously entirely ungoverned — no declared
# vocabulary, no scan — which is precisely what masked WO-013's §0 defect (canonical codes read
# "producible" via their event_type literals while the emitted reason_code said something else). An
# ungoverned namespace adjacent to a governed one lets canonical-looking literals borrow the governed
# namespace's credibility. Structured exactly as VALID_REASON_CODES; the completeness scan reads it
# for the same four properties (raised=>declared, declared=>producible, prefix-freedom across the
# UNION with reason codes, scan reads EMITTED strings).
VALID_EVENT_TYPES = {
    # kraken_public feed events (log_feed_event) — emitted LOWERCASE. FINDING (§6): the feed layer
    # uses lowercase event_types while the loop layer uses UPPERCASE. Declared AS EMITTED (governance,
    # not a rename); normalising the casing is a taxonomy question for a ruling, not this WO.
    "FEED": [
        "feed_connected",
        "feed_disconnected",
        "feed_error",
        "payload_error",
    ],
    # live.py loop events (log_decision) — emitted UPPERCASE.
    "LOOP": [
        "FEED_PAUSED",           # feed paused on book unavailability
        "MARKET_DATA_RECEIVED",  # a market-data frame reached the loop
        "NO_SIGNAL",             # strategy produced no signal (also a reason_code — §6 overlap)
        "SIGNAL_GENERATED",      # strategy produced a long/short signal
        "ORDER_FILLED",          # an order filled (also a declared reason_code — §6 overlap)
        "ORDER_REJECTED",        # an order was rejected/blocked (also a declared reason_code — §6 overlap)
    ],
    # Risk-decision event_types are emitted as RiskDecision.value (live.py event_type=decision.value).
    # These MUST equal the RiskDecision enum values; a hand-restated enum is a second source of truth
    # waiting to diverge (§3). decision.py (logkit) must not import trading.risk (layering / cycle), so
    # the sync is enforced MECHANICALLY by test_event_type_risk_values_match_enum in the vocabulary
    # tests (which may import both) — drift fails there, not silently.
    "RISK": [
        "PASS",
        "CLAMP",
        "VETO",
    ],
}


class DecisionLogger:
    """
    Decision logger that records every decision with reason codes.

    Constitutional requirements:
    - Every decision logged with reason code (Principle VIII)
    - No secrets or credentials in any log line (Principle IX)
    - Zero silent decisions (Principle VIII)
    """

    def __init__(self, log_file: str = "logs/decisions.log") -> None:
        """
        Initialize decision logger.

        Args:
            log_file: Path to log file (creates logs/ directory if needed)
        """
        self._log_file = log_file
        self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        """Ensure log directory exists."""
        import os
        log_dir = os.path.dirname(self._log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    def log_decision(
        self,
        layer: Layer,
        event_type: str,
        reason_code: str,
        venue: str,
        symbol: str,
        side: Optional[str] = None,
        size: Optional[Decimal] = None,
        intended_price: Optional[Decimal] = None,
        executed_price: Optional[Decimal] = None,
        fees: Optional[Decimal] = None,
        spread_cost: Optional[Decimal] = None,
        slippage_cost: Optional[Decimal] = None,
        total_cost: Optional[Decimal] = None,
        strategy_version: Optional[str] = None,
        feature_snapshot_hash: Optional[str] = None,
    ) -> None:
        """
        Log a decision with reason code.

        Args:
            layer: Decision layer (STRATEGY, RISK, EXECUTION, BACKTEST)
            event_type: Event type (e.g., "NO_SIGNAL", "PASS", "CLAMP", "VETO")
            reason_code: Controlled vocabulary reason code
            venue: Venue identifier (e.g., "kraken_public", "simulated")
            symbol: Trading pair
            side: Order side (None for no-signal decisions)
            size: Order size (None for no-signal decisions)
            intended_price: Intended price (None if not executed)
            executed_price: Actual executed price (None if not executed)
            fees: Trading fees paid (None if not executed)
            spread_cost: Observed spread cost from bid/ask (None if not executed)
            slippage_cost: Assumed slippage cost 0.1% (None if not executed)
            total_cost: Total cost including all components (None if not executed)
            strategy_version: Strategy version identifier
            feature_snapshot_hash: Hash of feature snapshot

        Constitutional requirements:
            - Every decision logged with reason code (Principle VIII)
            - No secrets or credentials in any field (Principle IX)
        """
        decision_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "layer": layer.value,
            "event_type": event_type,
            "reason_code": reason_code,
            "venue": venue,
            "symbol": symbol,
            "side": side.value if side and hasattr(side, 'value') else side,
            "size": str(size) if size is not None else None,
            "intended_price": str(intended_price) if intended_price is not None else None,
            "executed_price": str(executed_price) if executed_price is not None else None,
            "fees": str(fees) if fees is not None else None,
            "spread_cost": str(spread_cost) if spread_cost is not None else None,
            "slippage_cost": str(slippage_cost) if slippage_cost is not None else None,
            "total_cost": str(total_cost) if total_cost is not None else None,
            "strategy_version": strategy_version,
            "feature_snapshot_hash": feature_snapshot_hash,
        }

        # Sanitize: ensure no secrets in the record
        self._sanitize(decision_record)

        # Write to log file
        self._write_log(decision_record)

        # Also print to console
        self._print_log(decision_record)

    def log_feed_event(
        self,
        layer: str,
        event_type: str,
        reason_code: str,
        venue: str = "unknown",
        symbol: str = "unknown",
        details: str = "",
    ) -> None:
        """
        Log a feed event with reason code.

        Args:
            layer: Layer identifier (e.g., "data", "feed")
            event_type: Event type (e.g., "feed_connected", "feed_disconnected")
            reason_code: Controlled vocabulary reason code
            venue: Venue identifier
            symbol: Trading pair
            details: Additional details about the event
        """
        feed_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "layer": layer,
            "event_type": event_type,
            "reason_code": reason_code,
            "venue": venue,
            "symbol": symbol,
            "details": details,
        }

        # Sanitize: ensure no secrets in the record
        self._sanitize(feed_record)

        # Write to log file
        self._write_log(feed_record)

        # Also print to console
        print(f"[{layer}] {event_type}: {reason_code}")
        if details:
            print(f"  Details: {details}")

    def _sanitize(self, record: dict) -> None:
        """
        Sanitize record to ensure no secrets are logged.

        Args:
            record: Decision record to sanitize

        Constitutional requirements:
            - No secrets or credentials in any log line (Principle IX)
        """
        # Check for common secret patterns
        secret_keywords = ["api_key", "api_secret", "password", "token", "secret"]
        record_str = json.dumps(record, default=str).lower()

        for keyword in secret_keywords:
            if keyword in record_str:
                raise ValueError(f"Secret detected in log record: {keyword}")

    def _write_log(self, record: dict) -> None:
        """Write decision record to log file."""
        with open(self._log_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    def _print_log(self, record: dict) -> None:
        """Print decision record to console."""
        print(f"[{record['layer']}] {record['event_type']}: {record['reason_code']}")
        if record['size']:
            print(f"  Size: {record['size']}, Side: {record['side']}, Symbol: {record['symbol']}")
        if record['executed_price']:
            print(f"  Executed Price: {record['executed_price']}, Fees: {record['fees']}, "
                  f"Spread (observed, included in executed price): {record.get('spread_cost', 'N/A')}, "
                  f"Slippage (assumed 0.1%): {record.get('slippage_cost', 'N/A')}, "
                  f"Total (fees + slippage): {record.get('total_cost', 'N/A')}")


# Singleton logger instance
_logger: Optional[DecisionLogger] = None


def get_logger(log_file: str = "logs/decisions.log") -> DecisionLogger:
    """Get or create the singleton decision logger."""
    global _logger
    if _logger is None:
        _logger = DecisionLogger(log_file)
    return _logger
