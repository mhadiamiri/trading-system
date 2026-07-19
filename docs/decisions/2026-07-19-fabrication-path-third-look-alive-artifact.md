# Decision Log: The Fabrication Path — Third "Looks Alive While Disconnected" Artifact

**Date**: 2026-07-19
**Status**: REMOVED (WO-008b-A1) · reachability analysed (WO-008b-A1b)
**Related WO**: WO-008b-A2 §1.2 entry 1

## Statement (project lead, pre-ruled)

> Fabrication path existed: `get_market_data` invented a 10-level ladder and
> self-computed its checksum so validation would pass. Reachable from the production
> factory one config value away. Proven unreachable in all evidence runs; removed. Third
> artifact after the sequence field and the tautological guard test that would have let the
> system LOOK alive while disconnected from reality.

## The mechanism

Called without `fixture_data`, `get_market_data()` invented a book:

- bids `65000.0 … 64991.0`, asks `65005.0 … 65014.0` — ten levels of nothing
- **computed its own checksum over the invented ladder**, so validation passed
- emitted ten MarketStates from it

The self-computed checksum is what makes this the third of its kind rather than merely a
bad stub. Integrity validation *ran and passed*. A system consuming this would see a
checksummed, validated, structurally perfect feed carrying data that no venue ever sent.

## Reachability

Reachable from the production factory (`af27491`):

```python
elif data_source == "kraken_v2":
    feed = KrakenV2BookAdapter()
    return feed.get_market_data()      # no fixture_data → fabricating branch
```

`DATA_SOURCE=kraken_v2` was the only thing standing between the system and invented market
data, for nine commits.

**Never executed.** Four checks in WO-008b-A1b: no factory banner in any evidence output,
the distinctive prices appear only inside captured `git diff` text, no test calls
`create_feed()`, `.env` untracked and set to `simulated`. **Latent hazard, not a
contamination event — nothing quarantined.**

## The family

| # | artifact | how it faked aliveness |
|---|---|---|
| 1 | synthetic `sequence` field | modelled a protocol element Kraken never sends; "gap detection proven" against a fiction |
| 2 | tautological mainnet-guard test | asserted substrings of its own string literal; would pass against an empty repository |
| 3 | **fabrication path** | invented market data and self-validated it |

Each let the system **look alive while disconnected from reality**, and each passed review
because the thing checking it shared the same false premise. That is the family
resemblance, and it is why they belong in one record rather than three.

## Why it is worth naming as a class

A crashing stub is harmless — it announces itself. These three are dangerous precisely
because they *succeed*: green tests, valid checksums, passing guards. The failure mode of
this project has never been code that breaks. It is code that produces confident,
well-formed, self-consistent output about something that did not happen.

Every guard added since exists to answer one question the system could not previously
answer about itself: **is this measurement touching reality?** — the preflight path
assertion (right tree?), the contract-count check (did it run?), F811 (defined twice?),
and now first live contact (does the ordering assumption survive a real venue?).

## Current state

`get_market_data()` raises without `fixture_data`. It will not fabricate under any input.

## Evidence

- `evidence/WO-008b-A1b/fabricated_data_reachability.txt`
- `docs/decisions/2026-07-19-fr018a-sequence-versus-reality.md`
- `docs/decisions/2026-07-19-fixtures-shaped-to-implementation.md`
