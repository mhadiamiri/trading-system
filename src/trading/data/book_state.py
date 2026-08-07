"""
WO-048 §3 (D48) — `BookState`: the top-of-book state a BOOK corpus can honestly produce.

WHY A SEPARATE TYPE AND NOT AN OPTIONAL-FIELD `MarketState`.

`corpus_20260805` is a top-of-book capture. Its frames carry exactly:

    timestamp, symbol, bid, ask, bid_qty, ask_qty, spread

`MarketState` additionally REQUIRES `trade_count`, `total_volume` and `last_price` — as required
positional arguments, so constructing one from a corpus frame is a hard failure (WO-047 FINDING A):

    TypeError: MarketState.__init__() missing 3 required positional arguments:
               'trade_count', 'total_volume', and 'last_price'

§3 offers two honest shapes and forbids a third. The forbidden one is substitution — filling those
fields with a mid price, a zero, or a running proxy — because that produces a number by redefining
what was measured (D48, U1).

Of the two honest shapes, an OPTIONAL-FIELD variant was REJECTED and a BOOK-ONLY TYPE chosen:

  - With `Optional` fields defaulting to None, a strategy CAN still write `market_state.last_price`
    and receive None. The next author who wants the code to run writes `or Decimal(0)` or
    `or self._mid`, and the fabrication is back — in a single line, in a strategy file, far from
    this decision. The type would permit exactly what §3 says must be impossible.
  - With a book-only type, `state.last_price` raises `AttributeError`. The attribute does not
    exist, so there is nothing to default, coalesce or quietly fill. **A strategy cannot read a
    fabricated `last_price` because there is no `last_price` to read.**

`MarketState` IS DELIBERATELY UNTOUCHED by this WO. Adding optional fields to it would weaken the
guarantee for every existing consumer to serve one new one, and §3 warns that a `MarketState` change
which "looks like a substitution in disguise" is a STOP. This type adds a narrower vocabulary
alongside the existing one rather than widening it.

WHAT IT IS COMPATIBLE WITH, AND WHY THAT IS SAFE. `compute_execution_costs` (the ONE ruled cost
model) reads only `best_bid`, `best_ask`, `spread` and `mid_price` — all of which a book corpus
genuinely observed. It annotates its parameter as `MarketState` under `TYPE_CHECKING` only, so the
binding is structural, not nominal: a `BookState` priced by that model is priced from REAL observed
quotes, with nothing synthesised. That is the whole point — the cost model transfers unchanged
because it never needed the trade channel.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class BookState:
    """Top-of-book market state: ONLY fields a book corpus actually observed.

    Deliberately NOT a subclass of `MarketState` — inheriting it would inherit the three required
    trade-channel fields and reintroduce the very problem this type exists to avoid.

    Validation mirrors `MarketState.__post_init__` for the fields they share, so a corpus frame that
    would have been rejected as a `MarketState` (crossed book, negative size) is rejected here too.
    A loader must not become a way to admit data the stricter type would have refused.
    """

    timestamp: datetime
    symbol: str

    best_bid: Decimal
    best_ask: Decimal
    best_bid_size: Decimal
    best_ask_size: Decimal

    # Derived from the observed quotes — never assumed.
    mid_price: Decimal = field(init=False)
    spread: Decimal = field(init=False)

    # NOTE (load-bearing): there is deliberately NO trade_count, total_volume or last_price here.
    # Their ABSENCE is the guarantee. Do not add them "for compatibility" — the moment they exist,
    # something will fill them.

    def __post_init__(self) -> None:
        if self.best_bid <= 0:
            raise ValueError(f"best_bid must be > 0, got {self.best_bid}")
        if self.best_ask <= 0:
            raise ValueError(f"best_ask must be > 0, got {self.best_ask}")
        if self.best_bid >= self.best_ask:
            raise ValueError(
                f"best_bid ({self.best_bid}) must be < best_ask ({self.best_ask})"
            )
        if self.best_bid_size < 0:
            raise ValueError(f"best_bid_size must be >= 0, got {self.best_bid_size}")
        if self.best_ask_size < 0:
            raise ValueError(f"best_ask_size must be >= 0, got {self.best_ask_size}")

        object.__setattr__(self, "mid_price", (self.best_bid + self.best_ask) / 2)
        object.__setattr__(self, "spread", self.best_ask - self.best_bid)

    def compute_snapshot_hash(self) -> str:
        """Provenance hash over exactly the observed fields (Principle VIII).

        Deliberately does NOT include placeholder keys for the absent trade-channel fields: a hash
        that hashed `"last_price": None` would imply the field was considered and found empty,
        rather than never having existed in this data at all.
        """
        state_dict = {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "best_bid": str(self.best_bid),
            "best_ask": str(self.best_ask),
            "best_bid_size": str(self.best_bid_size),
            "best_ask_size": str(self.best_ask_size),
            "mid_price": str(self.mid_price),
            "spread": str(self.spread),
            "channel": "book_only",     # states WHAT this snapshot is, so it cannot be misread
        }
        return hashlib.sha256(json.dumps(state_dict, sort_keys=True).encode()).hexdigest()
