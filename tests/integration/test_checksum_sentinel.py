"""WO-016 §A (D27) — 'E'-rejecting checksum sentinel — REGRESSION SENTINEL (rule 0.1d).

`compute_checksum` must REFUSE an assembled checksum input containing scientific notation
('E'/'e') with the declared reason code CHECKSUM_INPUT_SYNTHESIZED_NOTATION.

LABELLED per rule 0.1d: this is a REGRESSION SENTINEL, not a data-path guard. Its trigger
CANNOT occur while the fixed-point render (_current_ladder_strings) holds — that is exactly
why it is legitimate and why it is labelled rather than dressed up as a live guard. It converts
a future render regression (str(Decimal) re-entering the path) from a SILENT CRC mismatch into a
LOUD NAMED failure at the boundary where representation matters, and it stays load-bearing after
the wire-string WO closes FR-018a(f) (it then guards the invariant, not the implementation).
"""
import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter


def test_checksum_rejects_scientific_notation_with_reason_code():
    """THE SENTINEL. A size rendered in scientific notation (the WO-008b-B-RERUN defect shape)
    must be refused with the declared reason code — not silently CRC'd into a mismatch."""
    with pytest.raises(ValueError, match="CHECKSUM_INPUT_SYNTHESIZED_NOTATION"):
        KrakenV2BookAdapter.compute_checksum([("66452.7", "1.0E-7")], [])


def test_checksum_rejects_uppercase_and_lowercase_e():
    for sci in ("1.0E-7", "1.0e-7", "5E-8"):
        with pytest.raises(ValueError, match="CHECKSUM_INPUT_SYNTHESIZED_NOTATION"):
            KrakenV2BookAdapter.compute_checksum([], [("66452.8", sci)])


def test_checksum_accepts_plain_fixed_point_input():
    """Guard on the guard: plain fixed-point input (what the fix produces) must NOT trip it."""
    v = KrakenV2BookAdapter.compute_checksum(
        [("66452.7", "0.00000010")], [("66452.8", "1.88014504")]
    )
    assert isinstance(v, int)
