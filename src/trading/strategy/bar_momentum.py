"""
WO-053 §3.2 — `BarMomentumStrategy`. Mid-price momentum on 60-second bars.

Every parameter below was **committed in `evidence/WO-053/PRE_REGISTRATION.md` (commit `e7b33c8`)
BEFORE this file existed**, and is reproduced here with the same derivation. None was revised after
seeing a result; §0.8 forbids it, and the registration commit precedes the run commit in the git
history, which is what makes that claim checkable rather than asserted.

═══════════════════════════════════════════════════════════════════════════════════════════════
THE REGISTERED PARAMETERS AND THEIR DERIVATION FROM THE COST ARITHMETIC

  BAR_INTERVAL_SECONDS = 60
      Convention, not a fitted value. One minute is the smallest unit that is unambiguously
      *minutes* rather than seconds, and is the standard bar in every venue's own tooling. At the
      corpus's ~24-32 frames/s a bar holds ~1,440-1,920 frames, so its close is not a stray tick.

  MOMENTUM_BARS = 5   (a 5-minute lookback)
      The smallest round multiple of the bar that is unambiguously a minutes-horizon window.
      MULTI-BAR ON PURPOSE: a single-bar signal would carry no state across bars, which would make
      the per-segment reset (U3) and the observation-only first bar (U4) VACUOUSLY satisfied — the
      machinery would appear to work while never being exercised. This is WO-048's argument for its
      rolling window, reused deliberately.

  THRESHOLD_PCT = Decimal("3.24")   ← 2.0 x the round-trip cost
      DERIVED FROM A CITED COST, BEFORE ANY RESULT EXISTED. This is the whole point of the WO.

          taker fee, 2 sides    2 x 0.80%   = 1.60%   CITED   (fee_schedule, Kraken Pro Tier 1)
          slippage,  2 sides    2 x 0.01%   = 0.02%   MEASURED (WO-050 §4, 50k corpus frames)
          spread crossing       ~0.0016%             MEASURED (mean 0.521 on mid 64,635.87)
          ───────────────────────────────────────
          ROUND TRIP            ~1.62% of notional

          T = 2.0 x 1.62% = 3.24%

      WHY A MULTIPLE, AND WHY 2.0. Entering requires believing the SUBSEQUENT move will exceed
      1.62%. Under the momentum premise — an observed move tends to continue at similar magnitude —
      setting T equal to the round-trip cost buys an expected continuation exactly equal to cost:
      zero expectancy before variance. 2.0 is the smallest whole multiple that leaves any margin,
      and is the MOST FAVOURABLE defensible choice for the strategy, since a larger multiple would
      trade even less. No sweep. No variant evaluated.

  ORDER_SIZE_BTC = Decimal("0.1")
      Identical to WO-048/WO-050, so this result is directly comparable to the existing record.

THE REGISTERED EXPECTATION was (i) negative net P&L, or (ii) too few trades to evaluate — with
(ii) the registered prior, and a declared floor of 30 round trips below which the run is
INSUFFICIENT TO EVALUATE in either direction, including if positive.
═══════════════════════════════════════════════════════════════════════════════════════════════

ON MID PRICE, AND WO-048 §U1. That ruling rejected mid-price momentum because it "would read like
the trivial strategy while quietly using a fabricated price channel." The objection was to
substituting MID FOR `last_price` — presenting a book-derived number as though it were a trade
print. This strategy does the opposite of quietly: the signal is explicitly the quote midpoint,
named as such, computed from two real quoted sides. `BookState` carries no `last_price`,
`total_volume` or `trade_count` at all, so no trade channel can be fabricated even by accident.
`TrivialMomentumStrategy` remains DEFERRED, still blocked on a trade-channel re-capture.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from trading.data.desired_position import DesiredPosition, Side
from trading.strategy.interface import Strategy

# The cost bar the threshold is derived from. Kept as named constants so the derivation is
# executable rather than only described — `THRESHOLD_PCT` is COMPUTED from them below, so a reader
# who doubts the arithmetic can run it, and a future edit to one number cannot leave the other stale.
ROUND_TRIP_FEE_PCT = Decimal("0.80") * 2          # CITED, per side x 2
ROUND_TRIP_SLIPPAGE_PCT = Decimal("0.01") * 2     # MEASURED, per side x 2
ROUND_TRIP_SPREAD_PCT = Decimal("0.0016")         # MEASURED, mean full spread as % of mid
ROUND_TRIP_COST_PCT = ROUND_TRIP_FEE_PCT + ROUND_TRIP_SLIPPAGE_PCT + ROUND_TRIP_SPREAD_PCT
COST_MULTIPLE = Decimal("2.0")


class BarMomentumStrategy:
    """Momentum over N closed mid-price bars. Deterministic; no ML (Principle III).

    Consumes BARS, not ticks — `observe_bar()` is the entry point. It never sees a raw frame, so
    it cannot act inside a bar or on a partial one.

    DELIBERATELY NOT a `Strategy` subclass. `Strategy` requires `decide(market_state)`, a per-FRAME
    interface this class does not have and must not pretend to have: a bar strategy handed a single
    frame has no honest answer. Implementing `decide` here to satisfy the ABC would be exactly the
    substitution D48 forbids, one interface down. `BarMomentumOverFrames` below IS the `Strategy` —
    it owns the frame-to-bar boundary, which is where that responsibility belongs.
    """

    # ── PRE-REGISTERED (commit e7b33c8, before this file) ─────────────────────────────────────
    BAR_INTERVAL_SECONDS = 60
    MOMENTUM_BARS = 5
    THRESHOLD_PCT = ROUND_TRIP_COST_PCT * COST_MULTIPLE     # == Decimal("3.2432")
    ORDER_SIZE_BTC = Decimal("0.1")

    def __init__(self) -> None:
        self._version = "bar-momentum-v1.0.0"
        self._closes: list = []           # the rolling bar-close history; THE per-segment state

    @property
    def version(self) -> str:
        return self._version

    @property
    def warm(self) -> bool:
        """True once enough closed bars exist to compute the registered N-bar return.

        N+1 closes are needed for an N-bar return (the return spans N intervals, which touches N+1
        endpoints). Exposed so the runner and its proofs can assert a fresh instance is genuinely
        cold — a reset that silently failed would show up here.
        """
        return len(self._closes) >= self.MOMENTUM_BARS + 1

    def observe_bar(self, bar, symbol: str) -> Optional[DesiredPosition]:
        """Record a CLOSED bar and return a DesiredPosition, or None for no signal.

        Ordering matches `BookImbalanceStrategy`: the bar is recorded BEFORE the signal is
        evaluated, so a decision is always made against a history that includes the bar it is
        acting on. Evaluating first would decide on strictly stale information.
        """
        self._closes.append(bar.close)
        if len(self._closes) > self.MOMENTUM_BARS + 1:
            self._closes.pop(0)

        # UNDER-WARM IS FLAT, NOT A SIGNAL ON PARTIAL HISTORY. A 2-bar return is not the registered
        # 5-bar signal, and acting on it would silently change the strategy near every segment
        # boundary — exactly where U3/U4 are meant to make behaviour conservative.
        if not self.warm:
            return None

        first, last = self._closes[0], self._closes[-1]
        if first <= 0:
            return None                   # cannot form a return; no division attempted

        return_pct = (last - first) / first * Decimal("100")

        if return_pct >= self.THRESHOLD_PCT:
            side = Side.BUY
        elif return_pct <= -self.THRESHOLD_PCT:
            side = Side.SELL
        else:
            return None

        return DesiredPosition(
            timestamp=bar.end_utc,        # MARKET time at the bar's close, never now() (D-a)
            symbol=symbol,
            side=side,
            quantity=self.ORDER_SIZE_BTC,
            feature_snapshot_hash=bar.compute_snapshot_hash(),
        )


class BarMomentumOverFrames(Strategy):
    """Adapter: presents the runner's per-FRAME `decide(state)` interface, decides on BARS.

    WHY AN ADAPTER RATHER THAN A NEW RUNNER (§3.3). `SegmentedBacktestRunner` carries the six
    rulings — force-flat at every boundary, fresh instance per segment, observation-only open,
    declared eligibility, per-segment results with a justified aggregate — plus average-cost P&L
    and the aggregate position cap. All of that is proven and none of it is re-implemented here.
    This class changes only WHAT THE SIGNAL IS COMPUTED FROM, by consuming frames into a
    `SegmentBarBuilder` and forwarding completed bars to `BarMomentumStrategy`.

    U4 AT BAR GRANULARITY (§3.2). The runner's U4 makes the first FRAME of a segment
    observation-only. At bar granularity the analogous unit is the first completed BAR, and it
    needs its own suppression: the runner's frame-level U4 skips frame 0, which under a 60-second
    bar is one of ~1,500 frames inside bar 0 and suppresses nothing about bar 0's tradeability.
    So the first closed bar of every segment is OBSERVED — it enters the momentum history — but
    can never produce an order. The two rules compose: frame 0 is unfillable, and so is the entire
    first bar.

    In practice the first bar cannot trade anyway, because the strategy needs N+1 closes before it
    is warm. That is exactly why the suppression is asserted explicitly rather than assumed: a
    protection that is only satisfied incidentally is the incidental-coverage defect (D51), and
    would break silently the moment N changed.
    """

    # Read by SegmentedBacktestRunner: this factory needs to know WHICH segment it is building
    # bars for, because a bar builder that does not know its segment cannot refuse a foreign frame.
    wants_segment = True

    # The runner's U3 eligibility message reads this off the factory. Bars, not ticks: the strategy
    # needs MOMENTUM_BARS + 1 closes, each BAR_INTERVAL_SECONDS long.
    WINDOW_TICKS = (BarMomentumStrategy.MOMENTUM_BARS + 1) * BarMomentumStrategy.BAR_INTERVAL_SECONDS

    def __init__(self, segment_index: int, segment) -> None:
        from trading.data.bars import SegmentBarBuilder
        self._builder = SegmentBarBuilder(
            segment_index, segment, BarMomentumStrategy.BAR_INTERVAL_SECONDS)
        self._inner = BarMomentumStrategy()
        self._first_bar_observed = False
        self.bars_built = 0

    @property
    def version(self) -> str:
        return self._inner.version

    @property
    def warm(self) -> bool:
        return self._inner.warm

    @property
    def discarded_partial_bars(self) -> int:
        return self._builder.discarded_partial_bars

    def decide(self, market_state) -> Optional[DesiredPosition]:
        """Feed one frame; act only when a bar CLOSES."""
        bar = self._builder.add(market_state)
        if bar is None:
            return None                    # mid-bar: nothing has closed, nothing to decide on
        self.bars_built += 1

        desired = self._inner.observe_bar(bar, market_state.symbol)

        # U4 at bar granularity — the first closed bar is observed, never fillable.
        if not self._first_bar_observed:
            self._first_bar_observed = True
            return None
        return desired

    def finish(self) -> None:
        """Segment end: drop the trailing partial bar (§2.2, registered)."""
        self._builder.finish()
