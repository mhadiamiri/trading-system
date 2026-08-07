"""
WO-048 §2 (D48) — `BookImbalanceStrategy`.

WHY THIS STRATEGY. It consumes `bid_qty` / `ask_qty` — data only a BOOK corpus carries — so it is
the natural consumer of `corpus_20260805` and cannot be mistaken for `TrivialMomentumStrategy`
wearing a different name. Mid-price momentum was rejected as structurally the substitution D48
forbids: it would read like the trivial strategy while quietly using a fabricated price channel.

    imbalance = (bid_qty − ask_qty) / (bid_qty + ask_qty)     ∈ [−1, +1]

Positive means more size resting on the bid than the ask. The signal is the ROLLING MEAN of that
ratio over N ticks: BUY when the smoothed value ≥ +T, SELL when ≤ −T, HOLD otherwise.

THE ROLLING WINDOW IS DELIBERATE (§2.1). A single-tick signal would carry no state across ticks,
which would make the segmented runner's per-segment reset (U3) and observation-only first tick (U4)
VACUOUSLY satisfied — the machinery would appear to work while never being exercised. Carrying N
ticks of history means a reset that failed to happen would be VISIBLE in the signal.

═══════════════════════════════════════════════════════════════════════════════════════════════
PRE-REGISTERED PARAMETERS (WO-048 §0.8 — THE HARD RULE)

These values were FIXED AND COMMITTED BEFORE the run and were NOT revised after seeing any P&L.
They were not swept, not optimised, and not chosen because a variant looked better. There is no
variant: each was picked once, from the reasoning below, and left alone.

  WINDOW_TICKS = 100
      Derivation: matches the ESTABLISHED 100-sample convention already in this codebase —
      `TrivialMomentumStrategy._update_average_volume` keeps its rolling volume history at exactly
      100 samples (`trivial.py:85-86`). Reusing the house number rather than inventing one means the
      window was not selected for this data. It is also comfortably inside the corpus's shortest
      continuous stretch (~4,823–6,431 frames measured, WO-047 §2.2), so warm-up is not binding.

  THRESHOLD = Decimal("0.20")
      Derivation: a ROUND, UNTUNED starting value on a scale whose bounds are known a priori. The
      imbalance ratio lives in [−1, +1] by construction, so 0.20 means "the smoothed top-of-book is
      at least 20% more size on one side than the other". One-fifth of the available range is an
      obvious first choice on a bounded scale; it was not derived from this corpus and no other
      value was evaluated against it.

  ORDER_SIZE_BTC = Decimal("0.1")
      Derivation: identical to `TrivialMomentumStrategy`'s fixed size (`trivial.py:70`). §2.3
      requires a fixed size — position sizing is a separate question and would introduce another
      free parameter into a run whose purpose is to test the APPARATUS, not to find an edge.

If any of these turns out to be a poor choice, §0.8 is explicit: REPORT IT, do not fix it and
re-run. A second run with changed parameters is a new WO, with this run's number still on record.
═══════════════════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from trading.data.desired_position import DesiredPosition, Side
from trading.strategy.interface import Strategy


class BookImbalanceStrategy(Strategy):
    """Top-of-book imbalance, smoothed over a rolling window. Deterministic; no ML (Principle III).

    Consumes a `BookState` (or anything exposing `best_bid_size` / `best_ask_size` / `symbol` /
    `timestamp`). It NEVER reads `last_price`, `total_volume` or `trade_count` — on a `BookState`
    those attributes do not exist, so the strategy could not fabricate them even by mistake.
    """

    # ── PRE-REGISTERED (see module docstring; fixed before the run, unrevised after) ──────────
    WINDOW_TICKS = 100
    THRESHOLD = Decimal("0.20")
    ORDER_SIZE_BTC = Decimal("0.1")

    def __init__(self) -> None:
        self._version = "book-imbalance-v1.0.0"
        self._samples: list = []          # the rolling imbalance history; THE per-segment state

    @property
    def version(self) -> str:
        return self._version

    @property
    def warm(self) -> bool:
        """True once the rolling window is full.

        Exposed so the segmented runner and its proofs can assert that a fresh instance at a segment
        boundary is genuinely cold — a reset that silently failed would show up here.
        """
        return len(self._samples) >= self.WINDOW_TICKS

    def decide(self, market_state) -> Optional[DesiredPosition]:
        """Return a DesiredPosition, or None for no signal.

        NOTE on ordering: the tick is recorded into the window BEFORE the signal is evaluated, so a
        decision is always made against a window that includes the tick it is acting on. The
        alternative (evaluate, then record) would decide on strictly stale information.
        """
        imbalance = self._imbalance(market_state)
        if imbalance is None:
            return None                   # degenerate tick (§2.4) — no division, no signal

        self._samples.append(imbalance)
        if len(self._samples) > self.WINDOW_TICKS:
            self._samples.pop(0)

        # UNDER-WARM IS HOLD, NOT A SIGNAL ON PARTIAL DATA. A mean over 3 of 100 intended samples is
        # not the declared signal; acting on it would silently change the strategy near every
        # segment boundary — exactly where U3/U4 are meant to make behaviour conservative.
        if not self.warm:
            return None

        smoothed = sum(self._samples) / Decimal(len(self._samples))

        if smoothed >= self.THRESHOLD:
            side = Side.BUY
        elif smoothed <= -self.THRESHOLD:
            side = Side.SELL
        else:
            return None

        return DesiredPosition(
            timestamp=market_state.timestamp,     # WO-048 §5.1 (D-a): MARKET time, never now()
            symbol=market_state.symbol,
            side=side,
            quantity=self.ORDER_SIZE_BTC,
            feature_snapshot_hash=market_state.compute_snapshot_hash(),
        )

    def _imbalance(self, market_state) -> Optional[Decimal]:
        """(bid_qty − ask_qty) / (bid_qty + ask_qty), or None on a degenerate tick.

        §2.4: `bid_qty + ask_qty == 0` yields None — HOLD, with no division attempted. A real
        top-of-book can legitimately show zero resting size on both sides for an instant; that is an
        ABSENCE of information, not a balanced book, and must not be read as imbalance 0.0.
        """
        bid = market_state.best_bid_size
        ask = market_state.best_ask_size
        total = bid + ask
        if total == 0:
            return None
        return (bid - ask) / total
