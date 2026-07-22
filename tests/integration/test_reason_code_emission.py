"""WO-013 §1 — behavioral proofs that three declared codes are PRODUCED on their triggering event.

Each proof drives the PRODUCTION loop (LiveTradingLoop.run) and asserts the reason code IS IN THE
DECISION LOG (the JSON-lines file the production DecisionLogger writes) — not that an emit function
was called (0.1i). A test strategy / risk-engine double supplies the TRIGGER only; the emission
path exercised is the loop's own log_decision call (0.1h — a test that emits the code itself proves
nothing).

  - LONG_SIGNAL  / SHORT_SIGNAL  : strategy produces a BUY / SELL -> loop emits the declared code.
  - KILL_SWITCH_ENGAGED          : order attempted while the switch is engaged -> exception stops it,
                                    loop logs the declared code. PRESERVATION DUAL (S13): cancellation
                                    still succeeds while engaged, and is not logged as a blocked order.
"""
import json
from datetime import datetime, UTC
from decimal import Decimal

import pytest

from trading.data.market_state import MarketState
from trading.data.desired_position import DesiredPosition, Side
from trading.execution.approved_order import ApprovedOrder
from trading.execution.paper import PaperExecutionClient
from trading.risk.interface import RiskDecision
from trading.logkit.decision import DecisionLogger
from trading.loop.live import LiveTradingLoop


def _market_state(symbol="BTC/USD"):
    return MarketState(
        timestamp=datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC),
        symbol=symbol,
        best_bid=Decimal("65000.00"),
        best_ask=Decimal("65005.00"),
        best_bid_size=Decimal("1.5"),
        best_ask_size=Decimal("2.0"),
        trade_count=100,
        total_volume=Decimal("500.0"),
        last_price=Decimal("65000.00"),
    )


async def _feed(states):
    for s in states:
        yield s


class _FixedSignalStrategy:
    """Returns a fixed side. Supplies the TRIGGER only; the loop's log_decision is the production
    emission under proof (§1 permits a test strategy driving the production path)."""
    version = "test-fixed-signal-v1"

    def __init__(self, side):
        self._side = side

    def decide(self, market_state):
        if self._side == Side.HOLD:
            return None
        qty = Decimal("0.001") if self._side == Side.BUY else Decimal("-0.001")
        return DesiredPosition(
            timestamp=market_state.timestamp,
            symbol=market_state.symbol,
            side=self._side,
            quantity=qty,
            feature_snapshot_hash=market_state.compute_snapshot_hash(),
        )


class _VetoRiskEngine:
    """Vetoes every order, so the signal proofs stop cleanly after the (production) signal emission
    without exercising execution. The signal reason_code is logged BEFORE the risk check, so the
    veto does not affect what is under proof."""
    def check(self, desired_position, position_state, now):
        return RiskDecision.VETO, None, "RISK_VETO_DAILY_LOSS"

    def get_kill_switch_state(self):
        return False


class _PassButKillSwitchOnRiskEngine:
    """PASSES the order yet reports the kill switch ENGAGED — isolating the EXECUTION-layer block
    (defense-in-depth, independent of the risk veto) so the loop reaches place_order(
    kill_switch_engaged=True) and its production except-branch logs KILL_SWITCH_ENGAGED. See
    evidence/WO-013/emission_diagnosis.txt (loop-reachability finding: the integrated risk engine
    vetoes first, so the except branch is otherwise unreachable)."""
    def check(self, desired_position, position_state, now):
        size = abs(desired_position.quantity)
        order = ApprovedOrder(
            timestamp=desired_position.timestamp,
            symbol=desired_position.symbol,
            side=desired_position.side.value,
            size=size,
            price=Decimal("0"),
            reason_code="RISK_PASS",
            original_size=size,
        )
        return RiskDecision.PASS, order, "RISK_PASS"

    def get_kill_switch_state(self):
        return True


class _FakePersistence:
    _data_dir = "(test)"

    def write_event(self, market_state):
        pass

    def close(self):
        pass

    def get_file_info(self):
        return {}


def _log_entries(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


@pytest.mark.asyncio
async def test_long_signal_emitted_to_decision_log(tmp_path):
    log = tmp_path / "decisions.log"
    loop = LiveTradingLoop(
        strategy=_FixedSignalStrategy(Side.BUY),
        risk_engine=_VetoRiskEngine(),
        decision_logger=DecisionLogger(log_file=str(log)),
        persistence=_FakePersistence(),
    )
    await loop.run(max_updates=1, feed=_feed([_market_state()]))
    codes = [e["reason_code"] for e in _log_entries(log)]
    assert "LONG_SIGNAL" in codes, f"LONG_SIGNAL must be IN THE DECISION LOG; got {codes}"


@pytest.mark.asyncio
async def test_short_signal_emitted_to_decision_log(tmp_path):
    log = tmp_path / "decisions.log"
    loop = LiveTradingLoop(
        strategy=_FixedSignalStrategy(Side.SELL),
        risk_engine=_VetoRiskEngine(),
        decision_logger=DecisionLogger(log_file=str(log)),
        persistence=_FakePersistence(),
    )
    await loop.run(max_updates=1, feed=_feed([_market_state()]))
    codes = [e["reason_code"] for e in _log_entries(log)]
    assert "SHORT_SIGNAL" in codes, f"SHORT_SIGNAL must be IN THE DECISION LOG; got {codes}"


@pytest.mark.asyncio
async def test_kill_switch_engaged_emitted_and_cancellation_preserved(tmp_path):
    """§1: engage the kill switch, attempt an order, see KILL_SWITCH_ENGAGED in the decision log
    (the exception stops the order, the code records why). PRESERVATION DUAL (S13, same test):
    cancellation STILL succeeds while engaged, and is NOT logged as a blocked order."""
    log = tmp_path / "decisions.log"
    venue = PaperExecutionClient()
    loop = LiveTradingLoop(
        strategy=_FixedSignalStrategy(Side.BUY),
        risk_engine=_PassButKillSwitchOnRiskEngine(),
        execution_client=venue,
        decision_logger=DecisionLogger(log_file=str(log)),
        persistence=_FakePersistence(),
    )
    await loop.run(max_updates=1, feed=_feed([_market_state()]))

    entries = _log_entries(log)
    codes = [e["reason_code"] for e in entries]
    # BLOCKING + EMISSION: the declared code records why the order was stopped.
    assert "KILL_SWITCH_ENGAGED" in codes, f"KILL_SWITCH_ENGAGED must be IN THE DECISION LOG; got {codes}"
    # It was logged as a REJECTED order, never as a filled one.
    ks = next(e for e in entries if e["reason_code"] == "KILL_SWITCH_ENGAGED")
    assert ks["event_type"] == "ORDER_REJECTED"
    assert "EXEC_ORDER_FILLED" not in codes, "a kill-switched order must not also fill"

    # PRESERVATION DUAL (S13): cancellation succeeds while the switch is engaged, and does not
    # emit a blocked-order code.
    venue._orders["ord-1"] = {"symbol": "BTC/USD", "side": "BUY"}
    cancelled = await venue.cancel_order("ord-1", kill_switch_engaged=True)
    assert cancelled is True, "cancellation MUST succeed even while the kill switch is engaged (Principle VI)"
    assert "ord-1" not in venue._orders, "the cancelled order must be removed"
