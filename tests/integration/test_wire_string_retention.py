"""WO-017 §1.6 — wire-string retention: three permanent regression guards.

FR-018a(f) is satisfied LITERALLY: the checksum consumes the venue's TRANSMITTED
representation (WireDecimal.wire), never a re-render. These three tests are the standing
guards for that invariant and are the targets of the §1.6 bite proofs
(tools/wire_string_bite_proof.py weakens each guard, shows the test FAILS, restores).

  (a) checksum input equals the transmitted text, not a re-render that happens to match;
  (b) a level missing its wire string RAISES the declared code (the no-fallback guard);
  (c) a frame whose text and canonical rendering DIFFER (scientific-notation qty) still
      validates end-to-end through the production parse+apply+checksum path.
"""
from decimal import Decimal

import pytest

from trading.data.adapters.kraken_v2_book import (
    KrakenV2BookAdapter,
    LocalBookData,
    WireDecimal,
)


def _adapter_with_book(book):
    adapter = KrakenV2BookAdapter()   # fixture mode; opens NO socket
    adapter._local_book = book
    return adapter


# ── (a) checksum input == transmitted text, NOT a re-render ──────────────────────────
def test_checksum_input_is_transmitted_text_not_a_rerender():
    """The wire token '0.00000010' and its canonical str() render '1.0E-7' DIFFER. The
    checksum must consume the transmitted token, so _current_ladder_strings returns
    '0.00000010' — proving retention, not a re-render that coincidentally matches."""
    tiny = WireDecimal("0.00000010")
    assert str(tiny) != tiny.wire, "precondition: canonical render must differ from wire text"
    assert str(tiny) == "1.0E-7" and tiny.wire == "0.00000010"

    book = LocalBookData()
    book.apply_snapshot(
        bid_levels=[(WireDecimal("66452.7"), tiny)],
        ask_levels=[(WireDecimal("66452.8"), WireDecimal("0.00000020"))],
        sequence=0, checksum=0,
    )
    bids, asks = _adapter_with_book(book)._current_ladder_strings()

    assert bids[0][1] == "0.00000010", "checksum input must be the TRANSMITTED text"
    assert bids[0][1] != str(tiny), "must NOT be str()'s scientific re-render"


# ── (b) missing wire string RAISES the declared code (no fallback) ───────────────────
def test_missing_wire_string_raises_declared_code():
    """A ladder level carrying a plain Decimal (no retained wire string) cannot be
    checksummed over the venue's representation. The load-bearing guard REFUSES with
    CHECKSUM_WIRE_STRING_MISSING — it does not silently fall back to a render."""
    book = LocalBookData()
    book.apply_snapshot(
        bid_levels=[(Decimal("66452.7"), Decimal("1.0E-7"))],
        ask_levels=[(Decimal("66452.8"), Decimal("2.0E-7"))],
        sequence=0, checksum=0,
    )
    adapter = _adapter_with_book(book)
    with pytest.raises(ValueError, match="CHECKSUM_WIRE_STRING_MISSING"):
        adapter._current_ladder_strings()


# ── (c) scientific-notation frame round-trips and validates end-to-end ───────────────
def _ten(prefix, tiny_qty_at):
    """Ten (price, qty) STRING levels (wire form); one qty is a small value whose canonical
    render differs from its transmitted text."""
    levels = []
    for i in range(10):
        price = f"{prefix + i}.5"
        qty = "0.00000010" if i == tiny_qty_at else f"{(i + 1)}.54000000"
        levels.append((price, qty))
    return levels


@pytest.mark.asyncio
async def test_scientific_notation_frame_round_trips_and_validates():
    """A snapshot frame carrying qty '0.00000010' (whose str() render '1.0E-7' DIFFERS)
    validates through the full production path: parse retains the wire token, the checksum
    consumes it, and the declared checksum (computed over the transmitted text) matches."""
    bids = _ten(66000, tiny_qty_at=3)
    asks = _ten(66100, tiny_qty_at=7)

    # precondition: the small qty's canonical render differs from its wire text
    assert str(Decimal("0.00000010")) == "1.0E-7"

    # declared checksum is computed over the TRANSMITTED strings in the SORTED top-10 order
    # production uses (bids desc, asks asc) — drive the production path to obtain it.
    _seed = LocalBookData()
    _seed.apply_snapshot(
        bid_levels=[(WireDecimal(p), WireDecimal(q)) for p, q in bids],
        ask_levels=[(WireDecimal(p), WireDecimal(q)) for p, q in asks],
        sequence=0, checksum=0,
    )
    _bstr, _astr = _adapter_with_book(_seed)._current_ladder_strings()
    declared = KrakenV2BookAdapter.compute_checksum(_bstr, _astr)

    frame = {
        "channel": "book",
        "type": "snapshot",
        "data": [{
            "symbol": "BTC/USD",
            "bids": [{"price": p, "qty": q} for p, q in bids],
            "asks": [{"price": p, "qty": q} for p, q in asks],
            "checksum": declared,
            "timestamp": "2026-07-21T00:00:00.000000Z",
        }],
    }

    adapter = KrakenV2BookAdapter()
    states = await adapter.process_raw_frame(frame)

    assert len(states) == 1, "the scientific-notation frame must validate and emit"
    assert adapter._local_book.consecutive_failures == 0
