"""
A3 captured RAW WIRE TEXT — verifies the parse layer itself (WO-008b-A3).

A2's fixture stored the post-parse structure, so it could verify the checksum
ALGORITHM but not the PARSE LAYER — the trailing zeros were already gone by the
time they were saved. These frames are the bytes as received, so they can prove
that `json.loads(..., parse_float=Decimal, parse_int=Decimal)` preserves the
venue's transmitted digits and that the resulting checksums reproduce.

NO NETWORK — static captured text.
"""

import json
from decimal import Decimal

from tests.fixtures.kraken_v2_captured_frames_a3 import (
    CAPTURED_SNAPSHOT_TEXT,
    CAPTURED_UPDATE_TEXTS,
    DEPTH,
)
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter


def _parse(text):
    """Parse exactly as the transport does — preserving transmitted digits."""
    return json.loads(text, parse_float=Decimal, parse_int=Decimal)


def _levels(raw, reverse):
    return sorted(
        [(str(l["price"]), str(l["qty"])) for l in raw],
        key=lambda x: Decimal(x[0]),
        reverse=reverse,
    )[:DEPTH]


def _apply(raw, book, reverse):
    for level in raw:
        price, qty = str(level["price"]), str(level["qty"])
        book = [x for x in book if x[0] != price]
        if Decimal(qty) != 0:
            book.append((price, qty))
    book.sort(key=lambda x: Decimal(x[0]), reverse=reverse)
    return book[:DEPTH]


class TestRawTextPreservesVenueRendering:
    """FR-018a(f): checksum input derives from the transmitted representation."""

    def test_parse_float_decimal_preserves_trailing_zeros(self):
        """
        THE DEFECT THIS FIXTURE EXISTS TO CATCH.

        Plain `json.loads` floats the number and `Decimal(str(...))` drops
        checksum-bearing trailing zeros. `parse_float=Decimal` keeps them.
        """
        sample = '{"qty":0.00005100}'

        preserved = json.loads(sample, parse_float=Decimal)["qty"]
        round_tripped = Decimal(str(json.loads(sample)["qty"]))

        assert str(preserved) == "0.00005100"
        assert str(round_tripped) == "0.000051"
        assert str(preserved) != str(round_tripped), (
            "if these agreed, the fixture could not detect the rendering defect"
        )

    def test_snapshot_checksum_reproduces_from_raw_text(self):
        element = _parse(CAPTURED_SNAPSHOT_TEXT)["data"][0]
        bids = _levels(element["bids"], reverse=True)
        asks = _levels(element["asks"], reverse=False)

        assert KrakenV2BookAdapter.compute_checksum(bids, asks) == element["checksum"]

    def test_every_captured_update_reproduces_from_raw_text(self):
        """N of N — the denominator travels with the claim (addendum C)."""
        element = _parse(CAPTURED_SNAPSHOT_TEXT)["data"][0]
        bids = _levels(element["bids"], reverse=True)
        asks = _levels(element["asks"], reverse=False)

        validated = 0
        for text in CAPTURED_UPDATE_TEXTS:
            data = _parse(text)["data"][0]
            bids = _apply(data.get("bids", []), bids, reverse=True)
            asks = _apply(data.get("asks", []), asks, reverse=False)
            assert KrakenV2BookAdapter.compute_checksum(bids, asks) == data["checksum"], (
                f"checksum mismatch at captured update {validated}"
            )
            validated += 1

        assert validated == len(CAPTURED_UPDATE_TEXTS)
        assert validated > 0

    def test_float_round_trip_would_break_these_checksums(self):
        """
        Negative control.

        If the corrupted rendering also validated, this fixture would prove
        nothing about the parse layer.
        """
        element = json.loads(CAPTURED_SNAPSHOT_TEXT)["data"][0]  # plain: floats
        bids = sorted(
            [(str(Decimal(str(l["price"]))), str(Decimal(str(l["qty"])))) for l in element["bids"]],
            key=lambda x: Decimal(x[0]), reverse=True)[:DEPTH]
        asks = sorted(
            [(str(Decimal(str(l["price"]))), str(Decimal(str(l["qty"])))) for l in element["asks"]],
            key=lambda x: Decimal(x[0]))[:DEPTH]

        assert KrakenV2BookAdapter.compute_checksum(bids, asks) != element["checksum"], (
            "the float round-trip reproduced the checksum — this capture cannot "
            "distinguish correct rendering from corrupted rendering"
        )
