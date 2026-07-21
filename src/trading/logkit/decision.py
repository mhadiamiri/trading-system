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
        "CHECKSUM_RESYNC",  # T018: Reconnecting after 5 consecutive checksum failures
        # WO-016 §A (D27): REGRESSION SENTINEL (rule 0.1d — its trigger CANNOT occur while the
        # fixed-point render holds; legitimate, but labelled, not dressed as a data-path guard).
        # Raised by compute_checksum when the ASSEMBLED checksum input contains scientific
        # notation ('E'/'e'). The interim render fix guards one site; this guards the INVARIANT
        # at all of them — "checksum input contains no synthesized notation" — converting any
        # future formatting regression from a silent CRC mismatch into a LOUD NAMED failure. It
        # outlives the wire-string WO because it guards the invariant, not the implementation.
        "CHECKSUM_INPUT_SYNTHESIZED_NOTATION",
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
    ],
    "STRATEGY": [
        "NO_SIGNAL",  # No trading signal
        "LONG_SIGNAL",  # Long position signal
        "SHORT_SIGNAL",  # Short position signal
    ],
    "EXECUTION": [
        "ORDER_FILLED",  # Order successfully filled
        "ORDER_REJECTED",  # Order rejected by exchange
        # Paper-venue staleness guards (WO-008a-R6). Declared in WO-011 §5: they
        # were raised in production (paper.py) but never declared — the exact
        # raised-but-undeclared gap the vocabulary-completeness check now closes.
        "EXEC_NO_MARKET_STATE",  # place_order before set_market_state
        "EXEC_MARKET_STATE_TIMESTAMP_MISSING",  # staleness-guard invariant violation
        "EXEC_STALE_MARKET_STATE",  # MarketState older than the staleness threshold
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
