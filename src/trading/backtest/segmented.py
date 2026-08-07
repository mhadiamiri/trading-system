"""
WO-048 §4 — THE SEGMENTED BACKTEST RUNNER: the six rulings, in one place.

`BacktestRunner.run()` is the OPERATED continuous path and is deliberately left untouched (§0.7).
This is the corpus path, and it exists because a corpus is not a stream: `corpus_20260805` is 20
discontinuous stretches separated by 19 gaps and a 2.1-hour seam, and feeding them to a loop that
assumes adjacency-in-list means adjacency-in-time produces a beautiful number that is fiction.

THE SIX RULINGS AS BUILT (D48):

  U1 (§4.1) — `BookImbalanceStrategy` is what runs. The corpus is top-of-book; substituting a
      trade channel would redefine what was measured. `TrivialMomentumStrategy`'s evaluation is
      DEFERRED, blocked on a trade-channel re-capture — recorded, not dropped.

  U2 (§4.2) — FORCE-FLAT AT EVERY BOUNDARY, with NO duration threshold. Any threshold is a knob
      that quietly moves the P&L. DECLARED COST: a 1.7-second reconnect flattens a position where
      a real trader would not have — this makes the result CONSERVATIVE in a way that is stated
      rather than hidden. Each flattening is a LABELLED EVENT in the output.

  U3 (§4.3) — FULL STATE RESET per segment via a FRESH STRATEGY INSTANCE. Stronger than a
      `reset()` someone must remember to call correctly: a new object cannot carry stale state
      because there is no state to carry. Plus a DECLARED minimum eligible segment length; shorter
      segments are EXCLUDED and the exclusion is reported.

  U4 (§4.4) — THE FIRST TICK OF EVERY SEGMENT IS OBSERVATION-ONLY, never fillable. One tick. No
      parameter. The first frame after a hole may be far from the last one seen, and nobody could
      have traded on a price they could not see coming.

  U5 (§4.5) — PER-SEGMENT RESULTS PLUS A DECLARED AGGREGATE. **The sum is meaningful ONLY BECAUSE
      U2 makes every segment start and end flat.** Without force-flat, cross-boundary position
      carry would make the total depend on boundary handling, and summing would be arithmetic
      dressed as a measurement.

  U6 (§4.6) — ACKNOWLEDGMENTS are built here and handed to the reader. Structural note worth
      keeping in view: **acknowledgment governs READING; force-flat governs TRADING.** Acknowledging
      more classes never buys a more continuous backtest — only permission to read more segments.
      That is what removes the incentive to acknowledge everything to make the run work.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Callable, Dict, List, Optional

from trading.backtest.position_pnl import PositionLedger
from trading.data.corpus_frames import count_window_frames, iter_segment_frames
from trading.data.corpus_reader import Acknowledge, CorpusWindow
from trading.execution.interface import ExchangeClient
from trading.execution.paper import PaperExecutionClient
from trading.risk.engine import DeterministicRiskEngine
from trading.risk.interface import RiskEngine
from trading.risk.position_state import PositionState
from trading.strategy.book_imbalance import BookImbalanceStrategy


# ── U6 (§4.6): the declared acknowledgment set ────────────────────────────────────────────────
# DECLARED ENGINEERING JUDGEMENT, with the observed maxima and the re-declaration trigger stated.
#
#   KEEPALIVE_RECONNECT  observed max 16.863 s   -> 60 s bound is ~3.6x headroom
#   VENUE_DISCONNECT     observed max  3.287 s   -> 60 s bound is ~18x headroom
#
# RE-DECLARATION TRIGGER: if any future corpus shows a gap of either class exceeding ~30 s (half the
# bound), this 60 s figure must be re-derived rather than silently relied on. A bound that a corpus
# is quietly approaching has stopped being a bound and become a coincidence.
#
# PROCESS_RESTART is acknowledged with NO duration bound, and that is not a loosening: under U2 the
# runner force-flats at every boundary, so acknowledging the 2.1-hour seam buys permission to READ
# both sides as separate segments and nothing else. It never permits trading across it.
#
# accept_open_ended is deliberately NOT set anywhere here. `corpus_20260805` has no open-ended
# discontinuity; a future corpus ending in a breaker trip must acknowledge that truncation as its
# own deliberate act, not inherit it from this list.
GAP_ACKNOWLEDGMENT_BOUND_SECONDS = 60.0

BACKTEST_ACKNOWLEDGMENTS = (
    Acknowledge(
        "KEEPALIVE_RECONNECT", max_duration_seconds=GAP_ACKNOWLEDGMENT_BOUND_SECONDS,
        reason="sub-minute keepalive reconnect; segment boundary, never traded across (U2)",
    ),
    Acknowledge(
        "VENUE_DISCONNECT", max_duration_seconds=GAP_ACKNOWLEDGMENT_BOUND_SECONDS,
        reason="sub-minute venue disconnect; segment boundary, never traded across (U2)",
    ),
    Acknowledge(
        "PROCESS_RESTART",
        reason="declared inter-run seam; acknowledged to SEGMENT at it, never to trade across it",
    ),
)

# ── U3 (§4.3): the declared minimum eligible segment length ───────────────────────────────────
# DERIVATION: the strategy's warm-up window (BookImbalanceStrategy.WINDOW_TICKS = 100) x a safety
# factor of 10 = 1,000 frames. The factor is round and deliberately generous: a segment that is
# merely long enough to warm up would spend its entire life in warm-up and contribute a signal
# computed over the minimum possible history.
#
# NOT BINDING ON THIS CORPUS — measured: the shortest continuous stretch is 201.0 s, which at the
# observed ~24-32 frames/s holds ~4,823-6,431 frames, i.e. ~5-6x this bound. It is declared ANYWAY
# so that a future reconnect-burst corpus is refused by a STATED BOUND rather than saved by accident.
# A rule that only works because the data happened to be generous is not a rule.
MIN_ELIGIBLE_SEGMENT_FRAMES = BookImbalanceStrategy.WINDOW_TICKS * 10


class SegmentedBacktestRunner:
    """Runs a strategy over a reader-approved, explicitly segmented corpus window."""

    def __init__(
        self,
        corpus_dir,
        strategy_factory: Callable = BookImbalanceStrategy,
        risk_engine: RiskEngine = None,
        execution_client: ExchangeClient = None,
        min_segment_frames: int = MIN_ELIGIBLE_SEGMENT_FRAMES,
    ) -> None:
        """
        Args:
            corpus_dir: the corpus directory (read-only).
            strategy_factory: a CALLABLE returning a NEW strategy — U3's fresh instance per segment.
                A factory rather than an instance, so the runner cannot be handed one object and
                accidentally reuse it across segments.
            min_segment_frames: U3's declared eligibility bound.
        """
        self._corpus_dir = corpus_dir
        self._strategy_factory = strategy_factory
        self._risk_engine = risk_engine or DeterministicRiskEngine()
        self._execution_client = execution_client or PaperExecutionClient()
        self._min_segment_frames = min_segment_frames

    async def run(self, window: CorpusWindow, max_events: Optional[int] = None) -> Dict:
        """Run the strategy over every ELIGIBLE segment of `window`.

        `max_events` is per §5.3: None = ALL. Truncation is explicit and reported.
        """
        frame_counts = count_window_frames(self._corpus_dir, window)

        segments: List[Dict] = []
        excluded: List[Dict] = []
        boundary_events: List[Dict] = []
        processed_total = 0
        available_total = sum(frame_counts.values())

        for index, segment in enumerate(window.segments):
            n_frames = frame_counts.get(index, 0)

            # U3: eligibility, by the DECLARED bound.
            if n_frames < self._min_segment_frames:
                excluded.append({
                    "segment_index": index,
                    "run_id": segment.run_id,
                    "start_utc": segment.start_utc.isoformat(),
                    "end_utc": segment.end_utc.isoformat(),
                    "frames": n_frames,
                    "reason": (
                        f"SEGMENT_BELOW_MIN_FRAMES: {n_frames} < {self._min_segment_frames} "
                        f"(warm-up {self._strategy_factory().WINDOW_TICKS} x safety factor 10)"
                    ),
                })
                continue

            remaining = None if max_events is None else max(0, max_events - processed_total)
            if remaining == 0:
                break

            result = await self._run_segment(index, segment, remaining, window)
            segments.append(result)
            boundary_events.extend(result.pop("_boundary_events"))
            processed_total += result["frames_processed"]

        return self._aggregate(
            window, segments, excluded, boundary_events,
            processed_total, available_total, max_events,
        )

    async def _run_segment(self, index: int, segment, max_frames: Optional[int],
                           window: CorpusWindow) -> Dict:
        """One segment: fresh strategy, flat start, observation-only first tick, flat end.

        `window` is threaded through explicitly so the loader's containment check receives the
        REAL issuing window — the segment can only be read as a member of the window the reader
        approved.
        """
        # U3: a FRESH INSTANCE. Not reset() — a new object, so stale state is unrepresentable.
        strategy = self._strategy_factory()

        position = PositionState(
            symbol="BTC/USD", current_quantity=Decimal("0"), average_entry_price=Decimal("0"),
            unrealized_pnl=Decimal("0"), realized_pnl=Decimal("0"), daily_pnl=Decimal("0"),
        )

        # WO-050 §3 (R3): position-aware AVERAGE-COST accounting replaces the unmatched cash-flow
        # figure. `ledger` is the economic truth; `position` below is kept only as the risk engine's
        # input, and the two are reconciled at the boundary.
        ledger = PositionLedger()

        trades: List[Dict] = []
        boundary_events: List[Dict] = []
        frames_processed = 0
        first_tick_skipped = False
        first_frame_utc = last_frame_utc = None
        last_state = None                    # the boundary frame: R1 closes at ITS market
        # WO-048 §6.1: WHEN the segment first traded, and how many frames in. This is the
        # OBSERVABLE that distinguishes a cold segment from one carrying leaked state: a genuinely
        # fresh strategy cannot trade until it has warmed on THIS segment's own data, so an early
        # first trade is the signature of state crossing a hole. Without it the anti-splice test
        # asserts only that trades happened somewhere, which a leaking runner satisfies too.
        first_trade_utc = None
        first_trade_frame_index = None

        for state in iter_segment_frames(self._corpus_dir, segment, _approved=window):
            if max_frames is not None and frames_processed >= max_frames:
                break
            if first_frame_utc is None:
                first_frame_utc = state.timestamp
            last_frame_utc = state.timestamp
            last_state = state
            frames_processed += 1

            # U4: the FIRST tick of every segment is OBSERVATION-ONLY. The strategy still SEES it
            # (it feeds the rolling window), but no order may result from it. The first frame after
            # a hole may be far from the last one seen, and nobody could have traded on a price they
            # could not see coming.
            desired = strategy.decide(state)
            if not first_tick_skipped:
                first_tick_skipped = True
                boundary_events.append({
                    "event": "SEGMENT_OPEN_OBSERVATION_ONLY",
                    "segment_index": index,
                    "utc": state.timestamp.isoformat(),
                    "detail": "first tick of the segment: observed, never fillable (U4)",
                })
                continue

            if desired is None:
                continue

            decision, approved_order, _ = self._risk_engine.check(
                desired, position, state.timestamp)
            if decision.value == "VETO":
                continue

            self._execution_client.set_market_state(state)
            fill = await self._execution_client.place_order(
                symbol=approved_order.symbol, side=approved_order.side,
                size=float(approved_order.size), price=float(approved_order.price),
                kill_switch_engaged=False,
            )
            trades.append(fill)
            ledger.apply_fill(fill)
            if first_trade_utc is None:
                first_trade_utc = state.timestamp
                first_trade_frame_index = frames_processed
            position = self._apply_fill(position, fill)

        # ── U2 + WO-050 §2 (R1): FORCE-FLAT EXECUTES A REAL ECONOMIC CLOSE ────────────────────
        #
        # THE DEFECT THIS CLOSES. This previously did `dataclasses.replace(position,
        # current_quantity=0)` — it zeroed the variable and executed NO TRADE. U2 was labelled but
        # never economically executed, so the P&L omitted the cost and proceeds of closing all 21
        # segments of WO-048's run. The bite proof asserted the EVENT and missed the missing trade,
        # which is the specimen behind D49 ("a log line is a claim; the ledger is the effect").
        #
        # The flatten is now a REAL FILL: priced by `compute_execution_costs` at the BOUNDARY
        # FRAME's own bid/ask/spread, stamped in MARKET time (D-a), on the side that reduces the
        # position to zero. It enters the trade ledger like any other trade, LABELLED so it is
        # attributable — but never excluded, because excluding it would be the same omission in a
        # different disguise.
        flatten = None
        if position.current_quantity != 0 and last_state is not None:
            qty = abs(position.current_quantity)
            close_side = "SELL" if position.current_quantity > 0 else "BUY"

            self._execution_client.set_market_state(last_state)
            close_fill = await self._execution_client.place_order(
                symbol="BTC/USD", side=close_side, size=float(qty), price=0.0,
                kill_switch_engaged=False,
            )
            close_fill["boundary_close"] = True        # attributable, not excluded
            trades.append(close_fill)
            ledger.apply_fill(close_fill, is_boundary_close=True)
            position = self._apply_fill(position, close_fill)

            flatten = {
                "event": "SEGMENT_CLOSE_FORCE_FLAT",
                "segment_index": index,
                "utc": last_frame_utc.isoformat() if last_frame_utc else None,
                "quantity_flattened": str(qty),
                "close_side": close_side,
                # THE LEDGER CONSEQUENCE, recorded alongside the label so the two cannot drift:
                "close_fill_price": str(close_fill["fill_price"]),
                "close_fill_timestamp": close_fill["timestamp"],
                "close_cost": str(close_fill["total_cost"]),
                "detail": (
                    "position force-flattened at segment end (U2, no duration threshold) via a "
                    "REAL costed fill at the boundary frame's market. DECLARED COST: a short "
                    "reconnect flattens where a real trader would not — the result is conservative "
                    "in a stated direction."
                ),
            }
            boundary_events.append(flatten)

        return {
            "segment_index": index,
            "run_id": segment.run_id,
            "start_utc": segment.start_utc.isoformat(),
            "end_utc": segment.end_utc.isoformat(),
            "first_frame_utc": first_frame_utc.isoformat() if first_frame_utc else None,
            "last_frame_utc": last_frame_utc.isoformat() if last_frame_utc else None,
            "frames_processed": frames_processed,
            "trades": len(trades),
            # WO-050 §3.2 (R3): with R1's real close, the segment MUST end flat and its unrealised
            # P&L MUST be exactly zero. A non-zero residual means the close did not execute — this
            # is R1's independent check, computed from the position rather than from the event.
            "realised_pnl": str(ledger.realised_pnl),
            "unrealised_pnl_at_close": str(
                ledger.position.unrealised_pnl(last_state.mid_price) if last_state else Decimal("0")),
            "final_quantity": str(ledger.position.quantity),
            "boundary_closes": ledger.boundary_closes,
            "first_trade_utc": first_trade_utc.isoformat() if first_trade_utc else None,
            # 1-based index of the frame on which this segment first traded. Under U3+U4 it can
            # never be less than WINDOW_TICKS + 1: the strategy must warm on this segment's own
            # data, and the first frame is observation-only.
            "first_trade_frame_index": first_trade_frame_index,
            "force_flattened": flatten is not None,
            # WO-050 §3.4: the OLD unmatched-cash-flow figure is KEPT under an unambiguous name for
            # the before/after attribution (§7.3), never as "gross_pnl". The old key is REMOVED, so
            # a stale reader gets a loud KeyError rather than a wrong number (the WO-045 precedent).
            "unmatched_cashflow_legacy": str(self._gross_pnl(trades)),
            "fees": str(ledger.fees),
            "slippage_cost": str(ledger.slippage),
            "spread_cost_attribution": str(ledger.spread_attribution),
            "_trades": trades,
            "_boundary_events": boundary_events,
        }

    def _apply_fill(self, position: PositionState, fill: dict) -> PositionState:
        size = Decimal(str(fill["size"]))
        qty = position.current_quantity + (size if fill["side"] == "BUY" else -size)
        realized = position.realized_pnl - Decimal(str(fill["total_cost"]))
        return dataclasses.replace(
            position, current_quantity=qty, realized_pnl=realized)

    @staticmethod
    def _gross_pnl(trades: List[Dict]) -> Decimal:
        gross = Decimal("0")
        for t in trades:
            notional = Decimal(str(t["size"])) * Decimal(str(t["fill_price"]))
            gross += notional if t["side"] == "SELL" else -notional
        return gross

    def _aggregate(self, window, segments, excluded, boundary_events,
                   processed_total, available_total, max_events) -> Dict:
        """U5: per-segment results PLUS a declared aggregate, with the dependency stated."""
        def _sum(key):
            return sum(Decimal(s[key]) for s in segments) if segments else Decimal("0")

        realised = _sum("realised_pnl")
        fees = _sum("fees")
        slippage = _sum("slippage_cost")
        spread_attr = _sum("spread_cost_attribution")
        total_costs = fees + slippage           # spread is attribution, never additive (WO-008a-R6)
        legacy = _sum("unmatched_cashflow_legacy")
        residual = _sum("unrealised_pnl_at_close")

        return {
            "aggregate": {
                # THE DEPENDENCY, stated where the number is read, not only in the report:
                "sum_validity": (
                    "The per-segment sum is meaningful ONLY BECAUSE U2 force-flattens at every "
                    "boundary, so every segment starts and ends flat. Without that, the total "
                    "would depend on boundary handling and summing would be arithmetic dressed as "
                    "a measurement."
                ),
                "pnl_method": "average_cost",     # §3.1 — declared, never ambiguous
                "segments_run": len(segments),
                "segments_excluded": len(excluded),
                "trades": sum(s["trades"] for s in segments),
                "boundary_closes": sum(s["boundary_closes"] for s in segments),
                # §3.3: net = REALISED − total costs, with the channels attributed separately.
                "realised_pnl": str(realised),
                "total_fees": str(fees),
                "total_slippage_cost": str(slippage),
                "total_spread_cost_attribution": str(spread_attr),
                "total_costs": str(total_costs),
                "net_pnl": str(realised - total_costs),
                # §3.2: every segment ends flat, so this MUST be exactly zero. A non-zero value
                # means a close did not execute — R1's independent check, at the aggregate.
                "unrealised_residual": str(residual),
                "force_flattenings": sum(1 for s in segments if s["force_flattened"]),
                # §3.4 / §7.3: the OLD figure, kept under an unambiguous name for the before/after
                # attribution. It is NOT the reported P&L and is never called gross_pnl.
                "unmatched_cashflow_legacy": str(legacy),
            },
            "segments": [{k: v for k, v in s.items() if not k.startswith("_")} for s in segments],
            "excluded_segments": excluded,
            "boundary_events": boundary_events,
            "coverage": {
                "available_frames": available_total,
                "processed_frames": processed_total,
                "coverage_fraction": (processed_total / available_total) if available_total else 1.0,
                "max_events": max_events,
                "truncated": max_events is not None and processed_total < available_total,
            },
            "acknowledgments": [
                {"cause": a.cause, "max_duration_seconds": a.max_duration_seconds,
                 "accept_open_ended": a.accept_open_ended, "reason": a.reason}
                for a in BACKTEST_ACKNOWLEDGMENTS
            ],
        }
