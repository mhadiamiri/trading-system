"""
WO-066 §3.1 — HYPERLIQUID public market-data adapter. CAPTURE ONLY.

CITED, NOT RECALLED (0.1e)
--------------------------
    https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket   retrieved 2026-08-11

    endpoint   : wss://api.hyperliquid.xyz/ws
    subscribe  : {"method":"subscribe","subscription":{"type":"l2Book","coin":"BTC"}}
                 {"method":"subscribe","subscription":{"type":"trades","coin":"BTC"}}
    l2Book msg : {"channel":"l2Book","data":{"coin","levels":[[{px,sz,n}],[{px,sz,n}]],"time"}}
    liveness   : {"method":"ping"} -> {"channel":"pong"}
    depth      : "5 levels if fast, 20 levels if slow"   <- WE SUBSCRIBE SLOW, for 20 (WO-066 §3.4)
    cadence    : "Snapshot feed, pushed on each block that is at least 0.5 since last push"

═══ THE ORDER PATH IS ABSENT BY CONSTRUCTION, NOT DISABLED ══════════════════════════════════════

This module contains **no order placement, cancellation, modification, signing, or account
method, and imports nothing capable of signing.** That is a property of what is *not written
here*, and `tests/test_hyperliquid_no_order_path.py` asserts it STRUCTURALLY — over this module's
symbols and imports — rather than behaviourally.

The distinction is the whole point: **a disabled order path can be re-enabled by a flag, an absent
one cannot.** Hyperliquid's own API exposes order actions through `{"method":"post"}` on the same
socket; that method name is deliberately never constructed anywhere in this file.

═══ FOUR GAP CAUSES, NOT FIVE — a per-venue declaration (ratified, WO-066) ══════════════════════

Kraken declares five. **`CHECKSUM_RESYNC` HAS NO REFERENT HERE**: Hyperliquid publishes no book
checksum, no sequence number, and no version — there is nothing to fail and nothing to resync
against. The standing form ratified with this WO is that **cause taxonomies are per-venue
declarations, and a cause with no referent on a venue is ABSENT there, never repurposed.**

Repurposing it would have been the worse option and it is worth naming: a `CHECKSUM_RESYNC` that
can never fire is a metric that cannot move, and this project has now recorded that defect shape
three times. The absence is documented here so a reader asking "where is the fifth?" finds the
reason rather than a silent omission.

**Consequently this adapter deliberately does NOT expose `get_checksum_failure_count()` or its
siblings.** `trading.loop.live_capture` used to call them unconditionally, which would have
reported **0** — a claim meaning "we checked and found none" — for a venue where nothing was
checked. **That call site now reads the declaration below** and reports **None with a reason**
instead: the WO-054 `count: 0` vs `count: null` distinction, applied to an integrity metric.
The declaration is `PUBLISHES_BOOK_CHECKSUM = False` + `CHECKSUM_ABSENT_REASON` on the adapter
class; it is DECLARED rather than inferred from a missing method, because a missing method is
also what a broken Kraken adapter looks like.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Optional

# ── Cited connection parameters ───────────────────────────────────────────────────────────────
WS_URL = "wss://api.hyperliquid.xyz/ws"
SPEC_URL = "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket"
SPEC_RETRIEVED_UTC = "2026-08-11"

SYMBOL = "BTC/USD"          # our canonical symbol
VENUE_COIN = "BTC"          # Hyperliquid's coin identifier for the BTC perpetual

# WO-066 §3.4 — THE EVIDENTIARY BOUND, declared where the subscription is made.
# "5 levels if fast, 20 levels if slow". We subscribe SLOW deliberately: 20 levels is the deeper
# of the two published settings, and WO-065 §3.3 declared a 10-level minimum (20 preferred) for
# slippage at $100. Depth beyond level 20 is UNOBSERVED BY CONSTRUCTION on this feed.
SUBSCRIBE_FAST = False
PUBLISHED_LEVELS = 20 if not SUBSCRIBE_FAST else 5

# §3.4 — THE TWO l2Book FEEDS, and what each one costs. Both MEASURED, 90 s per arm, l2Book-only
# so nothing in our loop paces the result:
#
#     FEED_SLOW  20 levels/side   0.200 msg/s   inter-frame p50 5.406 s
#     FEED_FAST   5 levels/side   1.867 msg/s   inter-frame p50 0.517 s
#
# The documented cadence — "pushed on each block that is at least 0.5 since last push" — describes
# the FAST feed. The slow feed's ~5.4 s appears in NO citation and is 10.4x the documented figure.
#
# The capture subscribes to BOTH (ratified WO-066 §3.4). Depth and freshness are different
# properties of the venue and neither substitutes for the other: the slow feed carries the 20-level
# evidentiary bound, and the fast feed is the only one against which tape-vs-book reconciliation
# means anything (33.3% of slow-feed frames cannot be reconciled at one tick, versus 2.5% of fast).
FEED_SLOW = "slow"
FEED_FAST = "fast"
FEED_LEVELS = {FEED_SLOW: 20, FEED_FAST: 5}

# ── The gap-cause taxonomy for THIS venue — four, and the fifth's absence is documented above ──
GAP_CAUSES = (
    "KEEPALIVE_RECONNECT",
    "BREAKER_RETRY_LADDER",
    "VENUE_DISCONNECT",
    "HOST_SUSPEND",
)
# CHECKSUM_RESYNC is deliberately NOT here. See the module docstring.
CAUSE_ABSENT_FROM_THIS_VENUE = {
    "CHECKSUM_RESYNC": (
        "Hyperliquid publishes no book checksum, sequence number or version, so there is no "
        "integrity failure to detect and nothing to resync against. Declared ABSENT rather than "
        "repurposed or left wired-and-always-zero (WO-066, ratified)."
    ),
}

HOST_SUSPEND_DIVERGENCE_SECONDS = 43.0   # host-level, venue-agnostic; matches the Kraken bound


class HyperliquidAdapterError(Exception):
    """Raised when the adapter is asked to record something it cannot honestly record."""


def build_book_subscribe(coin: str = VENUE_COIN, fast: bool = False) -> dict:
    """The cited l2Book subscribe frame. `fast` omitted => the SLOW (20-level) feed.

    MEASURED, because the citation only describes the depth half of the trade-off (WO-066 §3.4,
    90 s per arm, l2Book-only so nothing else paces the loop):

        slow (fast omitted)  20 levels/side   0.200 msg/s   inter-frame p50 **5.406 s**
        fast (fast=True)      5 levels/side   1.867 msg/s   inter-frame p50 **0.517 s**

    The documented cadence — "pushed on each block that is at least 0.5 since last push" — matches
    the FAST feed. **The slow feed's ~5.4 s appears in no citation**, and it is 10.4x the
    documented figure. Subscribing SLOW for the deeper evidentiary bound therefore costs an order
    of magnitude in book freshness, which is a fact about what any figure from this corpus means.
    """
    sub = {"type": "l2Book", "coin": coin}
    if fast:
        sub["fast"] = True
    return {"method": "subscribe", "subscription": sub}


def build_trades_subscribe(coin: str = VENUE_COIN) -> dict:
    """The cited trades subscribe frame."""
    return {"method": "subscribe", "subscription": {"type": "trades", "coin": coin}}


def build_ping() -> dict:
    """The cited liveness frame. Answered by {"channel":"pong"}."""
    return {"method": "ping"}


@dataclass(frozen=True)
class BookLevel:
    """One published level. Field names follow the venue's so the mapping is checkable."""

    px: Decimal
    sz: Decimal
    n: int


@dataclass
class BookSnapshot:
    """A parsed l2Book message. A SNAPSHOT — there are no deltas on this feed.

    `levels_published` is carried on every snapshot rather than assumed, because it is this
    corpus's evidentiary bound (§3.4) and a feed that silently returned 5 where 20 was requested
    would otherwise be indistinguishable from one that returned 20.

    `feed` says WHICH l2Book subscription produced it. Both feeds arrive on the same channel with
    the same shape, so without this a dual-feed capture would silently interleave a 5-level 0.52 s
    stream and a 20-level 5.4 s stream into one undifferentiated corpus — two different
    observations of the venue wearing one label. **The discriminator is the venue's own `fast`
    field**, verified present on 5-level messages and absent on 20-level ones (WO-066 §3.4), not
    inferred from the level count, which would be circular.
    """

    coin: str
    bids: list
    asks: list
    venue_time_ms: int
    levels_published: int
    feed: str = FEED_SLOW


def parse_l2_book(raw: dict) -> Optional[BookSnapshot]:
    """Extract a BookSnapshot from one `channel: "l2Book"` message, or None for anything else.

    Returns None rather than raising for non-book frames: the caller feeds it every socket
    message and must not have to pre-filter. A MALFORMED book frame is also None — never guessed,
    the same treatment a torn JSONL line gets everywhere else in this codebase.
    """
    if raw.get("channel") != "l2Book":
        return None
    data = raw.get("data") or {}
    levels = data.get("levels")
    if not isinstance(levels, list) or len(levels) != 2:
        return None
    try:
        bids = [BookLevel(Decimal(str(x["px"])), Decimal(str(x["sz"])), int(x["n"]))
                for x in levels[0]]
        asks = [BookLevel(Decimal(str(x["px"])), Decimal(str(x["sz"])), int(x["n"]))
                for x in levels[1]]
        return BookSnapshot(coin=data["coin"], bids=bids, asks=asks,
                            venue_time_ms=int(data["time"]),
                            levels_published=max(len(bids), len(asks)),
                            # THE VENUE'S OWN DISCRIMINATOR, not our inference. Deriving the feed
                            # from the level count would be circular: the level count is exactly
                            # the thing §4.4 exists to detect a lie about.
                            feed=FEED_FAST if "fast" in data else FEED_SLOW)
    except (KeyError, ValueError, TypeError, ArithmeticError):
        return None


@dataclass(frozen=True)
class TradePrint:
    """One published trade from the `trades` channel."""

    coin: str
    side: str
    px: Decimal
    sz: Decimal
    time_ms: int


def parse_trades(raw: dict) -> list:
    """Extract TradePrints from one `channel: "trades"` message. [] for anything else."""
    if raw.get("channel") != "trades":
        return []
    out = []
    for item in raw.get("data") or []:
        try:
            out.append(TradePrint(coin=item["coin"], side=item.get("side", ""),
                                  px=Decimal(str(item["px"])), sz=Decimal(str(item["sz"])),
                                  time_ms=int(item["time"])))
        except (KeyError, ValueError, TypeError, ArithmeticError):
            continue
    return out


def is_pong(raw: dict) -> bool:
    """The cited liveness response."""
    return raw.get("channel") == "pong"


@dataclass
class HyperliquidBookAdapter:
    """Read-only Hyperliquid market-data adapter.

    **No order path exists on this class.** See the module docstring; the property is asserted
    structurally by `tests/test_hyperliquid_no_order_path.py`.
    """

    MODE_FIXTURE = "fixture"
    MODE_LIVE = "live"
    VENUE_LIVE = "hyperliquid_mainnet"
    VENUE_FIXTURE = "hyperliquid_fixture"

    HOST_SUSPEND_DIVERGENCE_SECONDS = HOST_SUSPEND_DIVERGENCE_SECONDS
    GAP_CAUSES = GAP_CAUSES
    WS_URL = WS_URL
    PUBLISHED_LEVELS = PUBLISHED_LEVELS

    # WO-066 §3.3 — the DECLARATION `trading.loop.live_capture` reads instead of inferring.
    # False means "this venue publishes nothing to check", which makes the runner report the
    # checksum figures as None rather than 0. The reason travels with the declaration because a
    # null with no reason is indistinguishable from a bug.
    PUBLISHES_BOOK_CHECKSUM = False
    CHECKSUM_ABSENT_REASON = CAUSE_ABSENT_FROM_THIS_VENUE["CHECKSUM_RESYNC"]

    mode: str = MODE_FIXTURE
    # §3.4 — which l2Book feeds this adapter subscribes to. BOTH is the ratified setting: depth and
    # freshness are different properties and neither substitutes for the other. See FEED_LEVELS.
    feeds: tuple = (FEED_SLOW, FEED_FAST)
    connect_fn: Optional[Callable] = None
    monotonic_clock: Callable = time.monotonic
    _wall_clock: Optional[Callable] = None
    _last_book: Optional[BookSnapshot] = field(default=None, repr=False)
    _frames_seen: int = 0
    _books_parsed: int = 0
    _trades_parsed: int = 0
    _unparsed: int = 0

    @property
    def venue_name(self) -> str:
        """LIVE and FIXTURE are distinguishable — captured data whose provenance cannot be
        established is not honest evidence (Principle VIII)."""
        return self.VENUE_LIVE if self.mode == self.MODE_LIVE else self.VENUE_FIXTURE

    @property
    def published_levels(self) -> int:
        """The DEEPEST book this adapter's subscriptions can deliver — the evidentiary bound.

        An instance property rather than the module constant, because the bound is a property of
        the subscriptions that were actually made, not of the module that could make either.
        """
        return max(FEED_LEVELS[f] for f in self.feeds)

    def subscriptions(self) -> list:
        """Every frame this adapter will send. ENUMERATED, so a reader can see the whole
        outbound surface in one place — WO-056 found six message kinds on Kraken where two
        were assumed, and the fix is to make the set inspectable rather than implied."""
        return ([build_book_subscribe(fast=(f == FEED_FAST)) for f in self.feeds]
                + [build_trades_subscribe()])

    def process_raw_frame(self, raw: dict) -> dict:
        """The SHARED entry point every inbound frame passes through.

        Returns a small record describing what the frame was, so the caller never has to
        re-dispatch on the venue's own field names.
        """
        self._frames_seen += 1
        book = parse_l2_book(raw)
        if book is not None:
            self._last_book = book
            self._books_parsed += 1
            return {"kind": "book", "book": book}
        trades = parse_trades(raw)
        if trades:
            self._trades_parsed += len(trades)
            return {"kind": "trades", "trades": trades}
        if is_pong(raw):
            return {"kind": "pong"}
        self._unparsed += 1
        return {"kind": "other"}

    def get_diagnostic_counters(self) -> dict:
        """Counters that CAN move on this venue.

        `checksum_failures_total` is deliberately absent: there is no checksum to fail, and a
        counter that cannot move is not a metric (WO-063/064). `levels_published_last` is carried
        because it is the corpus's evidentiary bound (§3.4) and must be observable, not assumed.
        """
        return {
            "frames_seen": self._frames_seen,
            "books_parsed": self._books_parsed,
            "trades_parsed": self._trades_parsed,
            "unparsed_frames": self._unparsed,
            "levels_published_last": (self._last_book.levels_published
                                      if self._last_book else None),
            "checksum_failures_total": None,   # NOT 0 — see the module docstring
            "checksum_absent_reason": CAUSE_ABSENT_FROM_THIS_VENUE["CHECKSUM_RESYNC"],
        }


# --- self-registration (WO-010 §5: the registry is the SOLE adapter-resolution path) ----------
from trading.data.adapters.registry import register  # noqa: E402


@register("hyperliquid_v1")
def _build_hyperliquid_v1(mode: str = HyperliquidBookAdapter.MODE_FIXTURE,
                          connect_fn=None,
                          monotonic_clock=time.monotonic,
                          wall_clock=None) -> "HyperliquidBookAdapter":
    """Builder invoked by the registry when DATA_SOURCE=hyperliquid_v1.

    Registered WITHOUT `live_capture=True` deliberately. That flag is a declaration that the
    adapter supports a live capture through `create_live_capture_feed` — which requires
    `get_live_market_data`, a gap ledger, and the checksum surface `trading.loop.live_capture`
    calls unconditionally. **None of that is wired yet** (WO-066 §3.3), and declaring a capability
    the adapter does not have is the WO-055 defect this WO's 0.14 warns about. The flag goes on
    when the capture path is genuinely reachable, not before.
    """
    adapter = HyperliquidBookAdapter(mode=mode, connect_fn=connect_fn,
                                     monotonic_clock=monotonic_clock)
    if wall_clock is not None:
        adapter._wall_clock = wall_clock
    return adapter
