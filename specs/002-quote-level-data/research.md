# Research: Quote-Level Data + Observed-Spread Cost Model

**Feature**: 002-quote-level-data
**Date**: 2026-07-15
**Status**: Complete — All clarifications resolved in spec

---

## Overview

This document consolidates research findings for the Quote-Level Data feature. All technical decisions are grounded in the Sprint 2 spec (`spec.md`) and the constitutional requirements.

---

## Decision 1: Kraken WebSocket v2 vs v1

**Decision**: Migrate to Kraken WebSocket v2 book channel as primary data source.

**Rationale**:
- v1 trades-only feed provides ~14 events/min, too sparse for meaningful signals
- v2 book channel provides hundreds to thousands of quote updates per minute
- v2 provides CRC checksum validation for book integrity (load-bearing for data honesty)
- v2 provides snapshot/incremental protocol with sequence numbers for gap detection

**Alternatives Considered**:
- **Stay on v1 trades feed**: Rejected — insufficient data density; violates Principle V (honest costs require observed spread)
- **Use third-party data provider**: Rejected — adds dependency; violates venue independence (Principle VII)
- **Full order book depth**: Rejected — out of scope for Sprint 2; top-of-book sufficient for cost model

**Evidence**:
- Kraken v2 API documentation publicly available
- v2 book channel checksum algorithm documented (CRC-32)
- Snapshot/incremental protocol specified in v2 docs

---

## Decision 2: Local Book Maintenance Strategy

**Decision**: Maintain local top-of-book state from v2 snapshot plus incremental updates, validated by CRC checksum.

**Rationale**:
- Top-of-book (best bid/ask) is sufficient for cost model — full depth not required
- Checksum validation on every update prevents silent book drift
- Sequence-number tracking enables gap detection → resnapshot on gap
- 5-consecutive-failure threshold tolerates transient glitches while catching real corruption

**Alternatives Considered**:
- **Trust updates without checksum**: Rejected — violates Principle V (dishonest data = dishonest backtest)
- **Resync on every failure**: Rejected — too aggressive; transient glitches are common
- **Continue on sequence gap**: Rejected — violates checksum discipline; corrupted state untrustworthy

**Evidence**:
- Kraken v2 docs specify checksum algorithm
- 5-failure threshold balances noise vs. signal (established practice in similar systems)

---

## Decision 3: Abnormal Spread Handling

**Decision**: REJECT trade when spread is zero, negative, or abnormally wide (>5% of price). Log + skip; do not fabricate cost.

**Rationale**:
- Zero/negative spread indicates corrupted book data
- Abnormally wide spread (>5%) indicates illiquidity or data fault
- Principle V forbids trading on fabricated costs
- A skipped trade is free; a trade priced on corrupt data is not

**Alternatives Considered**:
- **Use maximum observed spread from history**: Rejected — manufactures plausible number; exact failure mode this sprint exists to eliminate
- **Use fixed percentage spread**: Rejected — violates observed-spread-only requirement; dishonest backtest
- **Trade through with warning**: Rejected — risks real losses on corrupt data

**Evidence**:
- 5% threshold is conservative (typical spreads on BTC/USD are <0.1%)
- Principle V explicitly forbids assumed/fallback spreads (FR-015a)

---

## Decision 4: Rolling Trade Window Design

**Decision**: Hybrid window of 100 trades AND 60 seconds (whichever comes first), configurable.

**Rationale**:
- Trade-count cap self-limits in active markets (prevents stale data in high-volume periods)
- Time-cap self-limits in dead markets (prevents stale data in low-volume periods)
- Hybrid approach maintains recency across both regimes
- Configurable allows future tuning without code changes

**Alternatives Considered**:
- **Trade-count only**: Rejected — goes stale in dead markets
- **Time-window only**: Rejected — goes stale in active markets (too many trades)
- **No rolling stats**: Rejected — trades channel provides valuable enrichment (volume spikes, last price)

**Evidence**:
- 100 trades is reasonable for BTC/USD typical volume
- 60 seconds is standard window for short-term trading signals
- Hybrid pattern common in similar systems

---

## Decision 5: Book Unavailable Behavior

**Decision**: PAUSE — emit no MarketStates — until book channel recovers. Trades-only mode not permitted.

**Rationale**:
- MarketState is now quote-centric; cost model requires observed spread
- Emitting MarketState with null/stale bid/ask would break cost model or resurrect assumed-spread fallback
- No honest book means no honest decision
- Pause is observable; silent fallback is not

**Alternatives Considered**:
- **Fall back to trades-only mode**: Rejected — would require assumed spread; violates Principle V
- **Emit MarketState with null bid/ask**: Rejected — breaks cost model; misleading
- **Use stale last-known bid/ask**: Rejected — violates observed-spread-only requirement

**Evidence**:
- Principle V requires honest costs; no spread = no trade
- Spec explicitly rejects trades-only fallback (FR-019a)

---

## Decision 6: Adapter Placement & Boundary

**Decision**: All Kraken-v2-specific and order-book-specific detail confined to `src/trading/data/adapters/kraken_v2_book.py`. Import-linter contract updated to prevent leaks above adapter.

**Rationale**:
- Principle VII requires venue detail confinement
- Prior leak (venue detail in loop/) violated this; this is the clean re-test
- Single-module swap enables future venue changes
- Import-linter enforces boundary mechanically, not by convention

**Alternatives Considered**:
- **Spread v2 detail across data/**: Rejected — violates Principle VII; enables leaks
- **Put book logic in backtest/**: Rejected — wrong layer; backtest consumes MarketState, not raw book
- **No import-linter enforcement**: Rejected — boundary-by-intention fails; prior leak proves this

**Evidence**:
- Prior leak occurred despite good intentions
- Import-linter successfully enforced other boundaries (ML in risk, execution adapters)
- Spec requires import-linter contract updates (FR-020 through FR-022)

---

## Decision 7: MarketState Schema Changes

**Decision**: MarketState becomes quote-centric: timestamp, best_bid, best_ask, best_bid_size, best_ask_size, derived mid_price and spread, plus rolling trade statistics (trade_count, total_volume, last_price).

**Rationale**:
- Quotes are primary heartbeat; trades are secondary enrichment
- Derived fields (mid, spread) computed once in adapter, consumed by downstream
- Rolling stats enable volume-based and price-based indicators
- Strategy interface unchanged (still takes MarketState)

**Alternatives Considered**:
- **Keep existing MarketState**: Rejected — insufficient for observed-spread cost model
- **Separate QuoteMarketState and TradeMarketState**: Rejected — unnecessary complexity; unified is clearer
- **Put derived fields in strategy**: Rejected — computation belongs in adapter, not consumer

**Evidence**:
- FR-006 through FR-009 specify quote-centric fields
- Strategy interface unchanged (FR-023 through FR-026)

---

## Decision 8: Backtest Data Storage

**Decision**: Store raw quote/book data append-only in Parquet format. Backtest replays from stored quotes to reconstruct observed spread identically to live.

**Rationale**:
- Parquet provides efficient columnar storage for time-series data
- Append-only ensures immutability (audit trail)
- Raw quotes enable replay with identical observed spread (no synthetic path)
- Pandas/pyarrow already in stack

**Alternatives Considered**:
- **SQLite**: Rejected — less efficient for time-series; Parquet better for analytics
- **CSV**: Rejected — slower; no schema; larger files
- **Store computed spread instead of quotes**: Rejected — violates observed-spread-only; can't reconstruct live behavior

**Evidence**:
- Existing stack uses Parquet (persistence.py)
- Principle V requires honest replay; raw quotes required

---

## Decision 9: Checksum/Recovery Testing Strategy

**Decision**: Tests must PROVE checksum validation bites: corrupted/drifted book must fail validation, and recovery (resync/resnapshot/pause) must fire.

**Rationale**:
- Checksum is a safety property (drifted book = dishonest spread)
- Negative testing required (prove guard fires on bad data)
- Same discipline used for risk guards (fail-then-pass proofs)

**Alternatives Considered**:
- **Test only happy path**: Rejected — doesn't prove guard works
- **Mock checksum validation**: Rejected — doesn't prove real checksum algorithm
- **Skip recovery testing**: Rejected — recovery is critical; must verify it fires

**Evidence**:
- Risk guard testing uses fail-then-pass pattern
- Spec requires checksum testing (SC-003, QG-003)

---

## Decision 10: Reason Code Vocabulary Additions

**Decision**: Add reason codes to LAYER_VERB_DETAIL for: abnormal-spread reject, pause-on-book-unavailable, checksum-resync, sequence-gap resnapshot.

**Rationale**:
- Principle VIII requires total observability
- Every non-order decision must be logged with reason code
- Machine-readable codes enable post-trade analysis

**Alternatives Considered**:
- **Free-text log messages only**: Rejected — not machine-readable; hard to analyze
- **Reuse existing codes**: Rejected — insufficient granularity; new failures need distinct codes
- **Skip logging for transient failures**: Rejected — violates Principle VIII

**Evidence**:
- Existing reason codes in logkit/decision.py
- Principle VIII requires reason codes (FR-004, FR-017, FR-018, FR-018a, FR-019a)

---

## Technical Unknowns Resolved

All technical unknowns were resolved during spec clarification (WO-003):

| Unknown | Resolution | Spec Reference |
|---------|------------|----------------|
| Checksum failure threshold | 5 consecutive failures trigger reconnection/resync | Q1 in spec clarifications |
| Abnormal spread handling | REJECT trade (log + skip); no fallback | Q2 in spec clarifications |
| Rolling trade window default | 100 trades AND 60 seconds (whichever first), configurable | Q3 in spec clarifications |
| Sequence gap detection | Track sequence; on gap, discard book + resnapshot | Q4 in spec clarifications |
| Book unavailable behavior | PAUSE, emit no MarketStates | Q5 in spec clarifications |

**No NEEDS CLARIFICATION items remain** — all resolved in spec.

---

## Dependencies & Best Practices

### Kraken WebSocket v2 API

**Documentation**: https://docs.kraken.com/websockets/

**Key Points**:
- Connection endpoint: `wss://ws.kraken.com`
- Book channel subscription: `{"name":"book","subscription":{"depth":1}}`
- Checksum algorithm: CRC-32 over bid/ask prices/sizes
- Sequence numbers in message headers

### Checksum Validation Best Practice

**Pattern**: Validate on every update; reject on failure; resync after threshold

**Rationale**:
- Catches corrupted updates immediately
- Threshold prevents resync loops on transient glitches
- Proven pattern in similar trading systems

### Rolling Window Best Practice

**Pattern**: Hybrid (count + time) with configurable caps

**Rationale**:
- Self-limits in both active and dead markets
- Maintains recency across volume regimes
- Tunable per symbol/horizon

### Import-Linter Enforcement

**Pattern**: Contract forbidding specific imports across boundary

**Rationale**:
- Mechanical enforcement, not convention
- CI gate fails build on violation
- Proved effective for other boundaries (ML in risk, execution adapters)

---

## Summary

All technical decisions grounded in:
1. Sprint 2 spec clarifications (WO-003)
2. Constitutional requirements (especially V and VII)
3. Established best practices for similar systems
4. Proven patterns from Sprint 1 (import-linter, fail-then-pass testing)

**No NEEDS CLARIFICATION items remain** — research complete.
