"""
Replay of LIVE-CAPTURED Kraken v2 frames against Kraken's own checksums
(WO-008b-A2 §4.4).

This is the first independent verification of the INCREMENTAL checksum path that
has ever existed in this project. Kraken documents a checksum for the snapshot
case only; every incremental fixture before this one was self-generated and could
not detect a shared misunderstanding.

The frames in `tests/fixtures/kraken_v2_captured_frames.py` were captured from
the live public feed on 2026-07-19 and carry Kraken's own checksum values.

NO NETWORK — these are static captured dicts.
"""

from decimal import Decimal

import pytest

from tests.fixtures.kraken_v2_captured_frames import (
    CAPTURED_SNAPSHOT,
    CAPTURED_UPDATES,
    DEPTH,
    SYMBOL,
)
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter


def _render(level):
    """
    Render a level the way Kraken's checksum requires: fixed-point, 8dp qty.

    Kraken sends price/qty as JSON NUMBERS, so json.loads floats them before any
    project code runs. `Decimal(str(5.1e-05))` yields "0.000051", dropping the
    trailing zeros the checksum digits require. Kraken's own rendering is
    "0.00005100". See the module docstring of the fixture.
    """
    return (f'{level["price"]:.1f}', f'{level["qty"]:.8f}')


def _sorted_book(levels, reverse):
    return sorted([_render(l) for l in levels], key=lambda x: Decimal(x[0]), reverse=reverse)[:DEPTH]


def _apply(levels, book, reverse):
    for level in levels:
        price, qty = _render(level)
        book = [x for x in book if x[0] != price]
        if Decimal(qty) != 0:
            book.append((price, qty))
    book.sort(key=lambda x: Decimal(x[0]), reverse=reverse)
    return book[:DEPTH]


class TestCapturedGroundTruth:
    """Kraken's real checksums, reproduced by our algorithm."""

    def test_captured_snapshot_matches_krakens_checksum(self):
        """The live snapshot validates against the value Kraken sent with it."""
        element = CAPTURED_SNAPSHOT["data"][0]
        bids = _sorted_book(element["bids"], reverse=True)
        asks = _sorted_book(element["asks"], reverse=False)

        assert element["symbol"] == SYMBOL
        assert len(bids) == DEPTH and len(asks) == DEPTH
        assert KrakenV2BookAdapter.compute_checksum(bids, asks) == element["checksum"]

    def test_every_captured_update_validates_post_update(self):
        """
        THE PROOF THIS CAPTURE EXISTS FOR.

        Replaying real incremental updates, the checksum matches when computed
        over the POST-update book — for every single frame. This is FR-018a(b)
        confirmed against the venue rather than against our own assumption.
        """
        element = CAPTURED_SNAPSHOT["data"][0]
        bids = _sorted_book(element["bids"], reverse=True)
        asks = _sorted_book(element["asks"], reverse=False)

        checked = 0
        for frame in CAPTURED_UPDATES:
            data = frame["data"][0]
            bids = _apply(data.get("bids", []), bids, reverse=True)
            asks = _apply(data.get("asks", []), asks, reverse=False)

            assert KrakenV2BookAdapter.compute_checksum(bids, asks) == data["checksum"], (
                f"post-update checksum mismatch on captured frame {checked}"
            )
            checked += 1

        assert checked == len(CAPTURED_UPDATES)
        assert checked > 0

    def test_pre_update_ordering_does_not_match(self):
        """
        The negative control — without it the test above proves nothing.

        If the pre-update ladder also matched, the replay could not distinguish
        the two orderings and would certify nothing.
        """
        element = CAPTURED_SNAPSHOT["data"][0]
        bids = _sorted_book(element["bids"], reverse=True)
        asks = _sorted_book(element["asks"], reverse=False)

        pre_update_matches = 0
        for frame in CAPTURED_UPDATES:
            data = frame["data"][0]
            if KrakenV2BookAdapter.compute_checksum(bids, asks) == data["checksum"]:
                pre_update_matches += 1
            bids = _apply(data.get("bids", []), bids, reverse=True)
            asks = _apply(data.get("asks", []), asks, reverse=False)

        assert pre_update_matches == 0, (
            f"{pre_update_matches} frames matched the PRE-update ladder; the "
            f"replay cannot distinguish orderings and proves nothing"
        )

    def test_qty_zero_deletion_appears_in_real_traffic(self):
        """`qty: 0` deletions are real, not a fixture invention."""
        deletions = sum(
            1
            for frame in CAPTURED_UPDATES
            for side in ("bids", "asks")
            for level in frame["data"][0].get(side, [])
            if Decimal(f'{level["qty"]:.8f}') == 0
        )
        assert deletions > 0, "no qty:0 deletion in the captured window"
