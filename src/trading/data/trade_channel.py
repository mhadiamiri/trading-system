"""
WO-054 §2 — THE KRAKEN v2 TRADE CHANNEL: subscribe, parse, merge, and record availability.

The declarative contract this implements is `evidence/WO-054/trade_merge_schema.md`, committed as a
schema so that this module and any future reader are both built to satisfy it, rather than the
reader inheriting whatever the capture happened to write (the WO-014c-2 precedent).

CITED, NOT RECALLED (§2.1 / rule 0.1e)
--------------------------------------
    https://docs.kraken.com/api/docs/websocket-v2/trade   — retrieved 2026-08-08

    subscribe : {"method":"subscribe",
                 "params":{"channel":"trade","symbol":["BTC/USD"],"snapshot":false}}
    payload   : symbol, side, qty, price, ord_type, trade_id, timestamp   (type: snapshot|update)

`snapshot: false` is deliberate. The snapshot delivers "the most recent 50 trades" — activity from
BEFORE capture began. Merging those into the first frame would attribute pre-capture trades to a
capture-window interval, fabricating the opening frame's `count` and `volume`. Declining it costs
nothing, because we want only what happens inside the window.

THE ONE PROPERTY THIS MODULE EXISTS TO GUARANTEE
------------------------------------------------
**A number is written only when it is a claim we can make.**

    count: 0     means "we were listening, and nothing traded"   — a positive claim
    count: null  means "we could not see"                        — the absence of one

A corpus that wrote `0` during a trade-channel outage would say *no trades occurred* when it meant
*the trade channel dropped*: the misattribution family (host problem reported as venue problem) one
channel over. And `last_price` is never fabricated from mid or carried silently into an interval
that had no trade — that is the D48 substitution moved to capture time, where it is HARDER to catch
because the reader has no way to tell an invented price from an observed one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

# ── Cited subscription parameters ─────────────────────────────────────────────────────────────
TRADE_CHANNEL = "trade"
TRADE_SPEC_URL = "https://docs.kraken.com/api/docs/websocket-v2/trade"
TRADE_SPEC_RETRIEVED_UTC = "2026-08-08"

# How long we wait for the venue to acknowledge our subscribe before declaring it failed.
# DERIVATION: the book channel's own subscribe is answered within one round trip; 10 s is ~2 orders
# of magnitude above a normal RTT to Kraken and well below the 60 s gap-acknowledgment bound the
# backtest already declares, so a failed trade subscribe is recorded long before it could be
# confused with a book-level discontinuity.
SUBSCRIBE_ACK_TIMEOUT_SECONDS = 10.0

# ── The declared outage causes (§2.4) ─────────────────────────────────────────────────────────
#
# NOT added to kraken_v2_book.GAP_CAUSES. That set is RULED AND EXHAUSTIVE
# (evidence/WO-014c-2/gap_schema.txt §1.1) and its fifth member was added by an explicit LEAD
# ruling, not by an executor. Extending it here would also be semantically WRONG: that schema
# defines a gap as an interval during which NO validated MarketState is emitted, and during a
# trade-channel outage the book keeps flowing and states keep being emitted. There is no gap.
# Recording one would subtract book coverage that was never lost.
#
# ⚠ SILENCE IS NOT A CAUSE, DELIBERATELY. A subscribed channel that simply stops producing is
# INDISTINGUISHABLE from a market in which nothing traded — both look identical on the wire.
# Inventing an outage on a silence timeout would fabricate outages on every quiet night, which is
# the same misattribution running in the opposite direction. See the schema for the stated limit.
TRADE_OUTAGE_CAUSES = (
    "TRADE_CHANNEL_SUBSCRIBE_FAILED",
    "TRADE_CHANNEL_DROPPED",
)


class TradeChannelError(Exception):
    """Raised when the trade channel is asked to record something it cannot honestly record."""


def build_subscribe_message(symbol: str) -> dict:
    """The cited subscribe frame. `snapshot: false` — see the module docstring."""
    return {
        "method": "subscribe",
        "params": {"channel": TRADE_CHANNEL, "symbol": [symbol], "snapshot": False},
    }


def build_unsubscribe_message(symbol: str) -> dict:
    """The cited unsubscribe frame."""
    return {
        "method": "unsubscribe",
        "params": {"channel": TRADE_CHANNEL, "symbol": [symbol]},
    }


@dataclass(frozen=True)
class TradeEvent:
    """One published trade. Field names follow the venue's, so the mapping is checkable."""

    symbol: str
    side: str
    qty: Decimal
    price: Decimal
    ord_type: str
    trade_id: int
    timestamp: str


def parse_trade_message(raw: dict) -> list:
    """Extract `TradeEvent`s from one `channel: "trade"` message.

    Returns [] for anything that is not a trade payload — the caller feeds it every socket message
    and must not have to pre-filter. A malformed entry is SKIPPED, never guessed: the same
    treatment a torn JSONL line gets everywhere else in this codebase.
    """
    if raw.get("channel") != TRADE_CHANNEL:
        return []
    events = []
    for item in raw.get("data") or []:
        try:
            events.append(TradeEvent(
                symbol=item["symbol"],
                side=item["side"],
                qty=Decimal(str(item["qty"])),
                price=Decimal(str(item["price"])),
                ord_type=item.get("ord_type", ""),
                trade_id=int(item["trade_id"]),
                timestamp=item["timestamp"],
            ))
        except (KeyError, ValueError, ArithmeticError, TypeError):
            continue
    return events


@dataclass
class TradeChannelOutage:
    """One recorded interval during which the trade channel was NOT observable.

    Deliberately NOT a `GapRecord` — see TRADE_OUTAGE_CAUSES.
    """

    cause: str
    opened_utc: str
    closed_utc: Optional[str] = None
    detail: str = ""

    def __post_init__(self):
        if self.cause not in TRADE_OUTAGE_CAUSES:
            raise TradeChannelError(
                f"TRADE_CHANNEL_CAUSE_UNDECLARED: {self.cause!r} is not one of "
                f"{TRADE_OUTAGE_CAUSES}. An outage recorded under an undeclared cause is an "
                f"unattributable hole in the availability ledger."
            )

    def to_dict(self) -> dict:
        return {"cause": self.cause, "opened_utc": self.opened_utc,
                "closed_utc": self.closed_utc, "resolved": self.closed_utc is not None,
                "detail": self.detail}


@dataclass
class TradeMerger:
    """Accumulates trades between book frames and emits the frame's `trades` sub-object.

    Usage is a stream, mirroring the capture loop: `observe()` for each trade message, then
    `snapshot_for_frame()` once per book frame written. The accumulator RESETS on each snapshot,
    because the fields are per-interval deltas.
    """

    observable: bool = True
    _count: int = 0
    _volume: Decimal = field(default_factory=lambda: Decimal("0"))
    _last_price: Optional[Decimal] = None            # this interval only
    _running_last_price: Optional[Decimal] = None    # carried forward
    _running_last_price_utc: Optional[str] = None
    outages: list = field(default_factory=list)

    # ── availability ──────────────────────────────────────────────────────────────────────────
    def mark_unobservable(self, cause: str, utc: str, detail: str = "") -> TradeChannelOutage:
        """The channel is down. Opens an outage record and stops all counting."""
        outage = TradeChannelOutage(cause=cause, opened_utc=utc, detail=detail)
        self.outages.append(outage)
        self.observable = False
        # Discard the partial interval: it covers a stretch we only partly saw, and reporting it
        # as a complete interval's delta would understate activity by an unknown amount.
        self._count = 0
        self._volume = Decimal("0")
        self._last_price = None
        return outage

    def mark_observable(self, utc: str) -> None:
        """The channel is back. Closes the open outage and resumes counting."""
        for outage in reversed(self.outages):
            if outage.closed_utc is None:
                outage.closed_utc = utc
                break
        self.observable = True
        self._count = 0
        self._volume = Decimal("0")
        self._last_price = None

    # ── accumulation ──────────────────────────────────────────────────────────────────────────
    def observe(self, event: TradeEvent) -> None:
        """Record one trade into the current interval.

        A trade arriving while the channel is marked unobservable is a CONTRADICTION — we are
        receiving from a channel we recorded as down. Refuse rather than silently pick one of the
        two stories, since either choice would make the ledger disagree with the frames.
        """
        if not self.observable:
            raise TradeChannelError(
                "TRADE_CHANNEL_CAUSE_UNDECLARED: a trade arrived while the channel was recorded "
                "as unobservable. The availability ledger and the frames now disagree; refusing "
                "rather than choosing which one to believe. Call mark_observable() first."
            )
        self._count += 1
        self._volume += event.qty
        self._last_price = event.price
        self._running_last_price = event.price
        self._running_last_price_utc = event.timestamp

    # ── emission ──────────────────────────────────────────────────────────────────────────────
    def snapshot_for_frame(self, frame_utc: str) -> dict:
        """The `trades` sub-object for one book frame, then RESET the interval.

        `frame_utc` is the book frame's own timestamp — the right edge of the interval — used only
        to age `running_last_price`.
        """
        age_ms = _age_ms(self._running_last_price_utc, frame_utc)
        if self.observable:
            out = {
                "observable": True,
                "count": self._count,
                "volume": str(self._volume),
                # null, NEVER fabricated, when this interval held no trade.
                "last_price": str(self._last_price) if self._last_price is not None else None,
                "running_last_price": (str(self._running_last_price)
                                       if self._running_last_price is not None else None),
                "running_last_price_age_ms": age_ms,
            }
        else:
            # NO CLAIM. Nulls, not zeros — see the module docstring. `running_last_price` IS
            # retained with its age: the last price we saw genuinely is the last price we saw, and
            # the age states exactly how stale it is. `observable: False` is what stops a reader
            # treating it as current; nulling it would discard true information.
            out = {
                "observable": False,
                "count": None,
                "volume": None,
                "last_price": None,
                "running_last_price": (str(self._running_last_price)
                                       if self._running_last_price is not None else None),
                "running_last_price_age_ms": age_ms,
            }
        self._count = 0
        self._volume = Decimal("0")
        self._last_price = None
        return out

    def ledger(self) -> list:
        return [o.to_dict() for o in self.outages]


def _age_ms(then_utc: Optional[str], now_utc: str) -> Optional[int]:
    """Milliseconds between two ISO timestamps, or None if unknown. Never negative."""
    if not then_utc:
        return None
    from datetime import datetime
    try:
        a = datetime.fromisoformat(then_utc.replace("Z", "+00:00"))
        b = datetime.fromisoformat(now_utc.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return max(0, int((b - a).total_seconds() * 1000))
