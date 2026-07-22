"""WO-016 §2 — permanent regression: the 200 captured checksum failures must all VALIDATE.

Ground-truth fixture (accretion doctrine): tests/fixtures/kraken_v2_checksum_captures_wo016.json
holds the 200 full checksum-failure captures from the WO-008b-B-RERUN live capture. Each replays
its recorded top-10 ladder through the PRODUCTION checksum path (KrakenV2BookAdapter.apply_snapshot
-> _current_ladder_strings -> compute_checksum, rule 0.1h — no reimplementation) and MUST reproduce
Kraken's `expected_checksum`. "The defect class is closed" means the captured failures all validate,
not that new runs happen to stay clean.

The defect: `str(Decimal)` rendered small quantities in scientific notation ('1.0E-7'), so the
checksum's remove-'.'-lstrip-zeros rule produced '10E-7' not '10'. WO-017 closed it STRUCTURALLY:
`_current_ladder_strings` now consumes the venue's retained WIRE STRING (`.wire`), with no rendering
step at all. This fixture WITNESSES small-quantity rendering and repeated-price application (its
stated evidentiary bounds).

COVERAGE BOUNDARY (WO-017 follow-up A): this fixture is a REGRESSION GUARD ON THE CHECKSUM MATH;
it does NOT witness the production wire-retention path, because its artifacts contain no wire text
to retain (the wire text was discarded at capture time). The wire path is certified ELSEWHERE, by
tests/integration/test_wire_string_retention.py bite proofs (a) and (c), against real frames
including the scientific-notation case. Fixture-coverage doctrine: a fixture is sovereign for what
it CONTAINS and cannot certify a path its data does not reach. See _meta.evidentiary_bounds.

FIXTURE RECONSTRUCTION SUBTLETY (WO-017 §2): the capture predates wire retention and stores each
local_book level as `str(Decimal)` — e.g. qty '1.0E-7' (SCIENTIFIC), NOT the transmitted text
'0.00000010'. Seeding WireDecimal('1.0E-7') would set .wire='1.0E-7' -> the OLD FAILING value. So
the replay RECONSTRUCTS the wire form the parse would have retained: `format(Decimal(x), 'f')` is
the fixed-point rendering WO-016 proved reproduces Kraken's transmitted string 200/200 for exactly
this set. The book is seeded with WireDecimal(that string); production then consumes .wire with no
render. The reconstruction lives in the TEST harness (rebuilding recorded evidence); production
retains .wire at parse and never renders.
"""
import json
import os
from decimal import Decimal

import pytest

from trading.data.adapters.kraken_v2_book import (
    KrakenV2BookAdapter,
    LocalBookData,
    WireDecimal,
)

_FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures",
                        "kraken_v2_checksum_captures_wo016.json")


def _load():
    with open(_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def _wire(levels):
    """Reconstruct the transmitted wire string (WO-017 §2): fixed-point rendering of the
    captured Decimal, carried on a WireDecimal exactly as the live parse would have retained it."""
    return [
        (WireDecimal(format(Decimal(p), "f")), WireDecimal(format(Decimal(q), "f")))
        for p, q in levels
    ]


def _production_checksum(cap):
    """Drive the PRODUCTION apply + wire-string + checksum path over a capture's recorded ladder."""
    book = LocalBookData()
    book.apply_snapshot(bid_levels=_wire(cap["local_book_bids"]),
                        ask_levels=_wire(cap["local_book_asks"]),
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
    # WO-017 follow-up A: the evidentiary bounds state what this fixture DOES and does NOT certify.
    eb = data["_meta"]["evidentiary_bounds"]
    assert "CHECKSUM MATH" in eb["certifies"]
    assert "WIRE RETENTION" in eb["does_not_witness"]
    assert "test_wire_string_retention.py" in eb["does_not_witness"]  # where the wire path IS certified


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
