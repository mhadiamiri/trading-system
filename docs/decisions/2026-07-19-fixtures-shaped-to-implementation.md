# Decision Log: Fixtures Were Shaped to the Implementation, Not the Protocol

**Date**: 2026-07-19
**Status**: REMEDIATED (raw-frame fixtures added in WO-009 §2; rewire owned by WO-008b-A)
**Related WO**: WO-009 §3 entry 2

## Statement

The Phase 1-3 fixtures supplied **pre-parsed `QuoteUpdate` objects rather than raw wire
frames**. This is the **generator of the defect class**, not one of its products. The
remedy is raw frames, so the parse path is under test.

## Why this is the generator, not a symptom

With fixtures handing `QuoteUpdate` objects straight to `_process_quote_update`:

- `_parse_book_message` was **never called by any test**. Confirmed: zero test call sites.
- Nothing anchored the fixtures to Kraken's actual message schema. They were free to drift
  toward whatever the implementation happened to accept.
- A fictional field (`sequence`) could therefore be invented, populated by fixtures, and
  reported as "sequence-gap detection proven" — with every test passing.

Every downstream defect follows from this one property:

| defect | how the fixture shape enabled it |
|---|---|
| `sequence` field that Kraken never sends | fixtures supplied it, so nothing contradicted it |
| parser expecting a list envelope `[seq, bids, asks, checksum]` | parser untested; real v2 is a dict |
| levels as positional pairs, not `{price, qty}` | never compared against a real frame |
| `BOOK_DEPTH = 1`, illegal at the venue | fixtures were 1-level, so 1-level looked fine |
| checksum validated pre-update instead of post-update | self-generated checksums agreed with our own error |
| `qty: 0` deletion never exercised | fixtures never contained a deletion |

A test suite built this way cannot fail for the right reason. It certifies the
implementation against a mirror of itself.

## Remedy

`tests/fixtures/kraken_v2_raw_frames.py` — raw v2 dict envelopes matching Kraken's
documented schema: `channel`, `type` (`snapshot`|`update`), `symbol`, `bids`/`asks` as
`{price, qty}` arrays at depth 10, server-sent `timestamp`, `checksum`. Coverage now
includes snapshot-vs-update distinction, `qty: 0` deletion, and truncation to subscribed
depth.

**Provenance is labelled per fixture**, which the old fixtures never did:

- `# GROUND TRUTH: Kraken docs <url>` — Kraken's published value, independent of our code
- `# SELF-GENERATED — not independent verification` — computed by our own
  `compute_checksum()`; proves internal consistency only

The old incremental fixture asserted `388076886`, which is exactly what our
`compute_checksum()` returns for that input — the fixture asserted our own output. That
circularity is now impossible to reproduce unlabelled.

## Honest limit of the remedy

Kraken publishes a checksum for the **snapshot only**. No documented incremental example
exists, so **independent verification of the incremental path is not achievable from
documentation**. Three update fixtures are labelled SELF-GENERATED for that reason.
Incremental verification becomes the job of **first live contact in WO-008b-A**.

This matters because the known pre-update/post-update checksum defect is precisely the
class a self-generated fixture cannot catch: our code would make the same mistake on both
sides of the comparison.

## Transition discipline

Old fixtures were **retained**, not deleted — removing them would drop coverage before the
raw-frame consumer exists. All 13 construction sites carry an in-line deprecation marker
naming **WO-008b-A** as removal owner. No test was rewired, xfailed, skipped, or weakened.

Adding the fixtures broke nothing: `81 collected, 73 passed, 8 xfailed in 237.50s` —
identical to the `9a7c438` baseline.

## Evidence

- `evidence/WO-009/ground_truth_sources.txt`
- `evidence/WO-009/tests_requiring_rewire.txt`
- `evidence/WO-008b-DIAG/fixture_fidelity_audit.txt`
