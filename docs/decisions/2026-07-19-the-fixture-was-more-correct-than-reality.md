# Decision Log: "The fixture was more correct than reality."

**Date**: 2026-07-19 · **Related WO**: WO-008b-A3 addendum D, entry 2

`tests/fixtures/kraken_v2_raw_frames.py`, written in WO-009, stored prices and quantities
as **strings** and warned in its own docstring:

> "Parsed from STRING form to preserve exact decimal precision: the checksum is computed
> over the digits as sent, so a float round-trip would corrupt it."

The production parse path was committing exactly that round trip. Kraken transmits price
and qty as JSON **numbers**, so `json.loads` floated them before any project code ran, and
`Decimal(str(5.1e-05))` rendered `"0.000051"` where the venue sent `"0.00005100"`. The
trailing zeros are checksum-bearing digits.

**The fixture-fidelity work from WO-009 was paying before the socket opened.** WO-009 was
motivated by a different defect — fixtures shaped to the implementation rather than the
protocol, which had let a fictional `sequence` field be "proven". In fixing that, it
recorded a precise, correct statement about how the checksum consumes digits. That
statement then described a live defect nobody had looked for yet, in code the fixture did
not touch.

Two things worth keeping from this:

1. **Writing down *why* a fixture is shaped a certain way is itself a durable artifact.**
   The warning was more valuable than the fixture. Had the comment been omitted as
   obvious, the diagnosis would have started from nothing.
2. **The corruption happened upstream of the code being careful.** `_parse_levels` used
   `Decimal(str(...))` precisely to be careful about precision — but `json.loads` had
   already destroyed the information one layer earlier. Care applied at the wrong layer
   looks identical to care applied at the right one, right up until a venue disagrees.

Now encoded as **FR-018a(f)**: checksum input must derive from the venue's transmitted
representation; re-rendering a parsed numeric value into an assumed format is prohibited.

**Evidence**: `evidence/WO-008b-A3/rendering_and_ground_truth.txt`
