"""WO-016 §2 — permanent regression: the 200 captured checksum failures must all VALIDATE.

Ground-truth fixture (accretion doctrine): tests/fixtures/kraken_v2_checksum_captures_wo016.json
holds the 200 full checksum-failure captures from the WO-008b-B-RERUN live capture. Each replays
its recorded top-10 ladder through the PRODUCTION checksum path (KrakenV2BookAdapter.apply_snapshot
-> _current_ladder_strings -> compute_checksum, rule 0.1h — no reimplementation) and MUST reproduce
Kraken's `expected_checksum`. "The defect class is closed" means the captured failures all validate,
not that new runs happen to stay clean.

The defect: `str(Decimal)` rendered small quantities in scientific notation ('1.0E-7'), so the
checksum's remove-'.'-lstrip-zeros rule produced '10E-7' not '10'. The INTERIM fix renders
fixed-point (`format(x, 'f')`) at _current_ladder_strings. This fixture WITNESSES small-quantity
rendering and repeated-price application (its stated evidentiary bounds).
"""
import json
import os
from decimal import Decimal

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, LocalBookData

_FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures",
                        "kraken_v2_checksum_captures_wo016.json")


def _load():
    with open(_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def _dec(levels):
    return [(Decimal(p), Decimal(q)) for p, q in levels]


def _production_checksum(cap):
    """Drive the PRODUCTION apply + format + checksum path over a capture's recorded ladder."""
    book = LocalBookData()
    book.apply_snapshot(bid_levels=_dec(cap["local_book_bids"]),
                        ask_levels=_dec(cap["local_book_asks"]),
                        sequence=0, checksum=0)
    adapter = KrakenV2BookAdapter()          # fixture mode; opens NO socket
    adapter._local_book = book
    bid_strs, ask_strs = adapter._current_ladder_strings()
    return adapter.compute_checksum(bid_strs, ask_strs)


def test_fixture_present_and_labelled():
    data = _load()
    assert data["_meta"]["label"] == \
        "witnesses SMALL-QUANTITY RENDERING and REPEATED-PRICE APPLICATION"
    assert data["_meta"]["evidentiary_bounds"]["n_captures"] == 200
    assert len(data["captures"]) == 200


def test_all_200_captures_validate_through_production_checksum():
    """THE ACCEPTANCE CONDITION (WO-016 §2): 200/200 captured failures validate.

    Before the WO-016 fix this asserted 0/200 (every recorded ladder mis-rendered a small
    quantity into scientific notation). It is the standing guard on the render edge.
    """
    caps = _load()["captures"]
    assert len(caps) == 200
    mismatches = []
    for c in caps:
        got = _production_checksum(c)
        if got != c["expected_checksum"]:
            mismatches.append((c["seq"], got, c["expected_checksum"]))
    passed = len(caps) - len(mismatches)
    assert not mismatches, (
        f"{passed}/200 validated; {len(mismatches)} still mismatch Kraken's expected "
        f"checksum (first 5: {mismatches[:5]}). The captured-failure defect class is NOT closed."
    )
