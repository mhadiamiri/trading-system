"""
Decision Logging Module

Records every decision with reason codes for audit trail.

Constitutional Principles:
- VIII. Total Observability & Provenance: Every decision logged
- IX. Secrets and Safety Rails: No secrets in logs

Valid Reason Codes (LAYER_VERB_DETAIL vocabulary):
- Data layer: CHECKSUM_RESYNC, PAUSE_ON_BOOK_UNAVAILABLE, RECONNECT_FLAG_STRANDED,
  RECONNECT_CIRCUIT_BREAKER_TRIPPED, HEARTBEAT_ABSENCE, VENUE_CONNECTION_CLOSED
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
        # WO-014b-2 §1.1: logged by the transport when no frame of any kind (heartbeat,
        # data, or pong) has arrived within the heartbeat-absence threshold — the
        # connection is presumed dead and a reconnect is triggered (Kraken's own
        # liveness signal, applied at the application layer).
        "HEARTBEAT_ABSENCE",
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
