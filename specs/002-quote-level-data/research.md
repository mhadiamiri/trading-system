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
  *(provenance: MEASURED locally on 2026-07-12, not a vendor claim — see progress.md
  session log. Retained as an observation, not a protocol assertion.)*
- ⚠ **UNVERIFIED VENUE CLAIM (flagged under rule 0.1e, 2026-07-19):** "v2 book channel
  provides hundreds to thousands of quote updates per minute". **No citation exists
  for this figure and no measurement backs it.** Kraken publishes no rate guarantee.
  This is precisely the question WO-008b was created to answer (acceptance threshold:
  sustained ≥60 MarketStates/min), and it remains OPEN. It must NOT be relied upon as
  established fact until a live capture measures it.
- v2 provides CRC32 checksum validation for book integrity (load-bearing for data
  honesty). *(cite: <https://docs.kraken.com/api/docs/websocket-v2/book/> — book
  messages carry a `checksum` field, "CRC32 checksum for the top 10 bids and asks".)*
- ~~v2 provides snapshot/incremental protocol with sequence numbers for gap detection~~
  **CORRECTED 2026-07-19 (WO-009b): THIS SENTENCE WAS FALSE.** The Kraken v2
  **public** book channel provides a snapshot/incremental protocol with a **CRC32
  checksum only — it transmits NO sequence numbers.** Sequence numbers exist in
  Kraken v2 only on private/execution channels.
  Source: <https://docs.kraken.com/api/docs/websocket-v2/book/> and
  <https://docs.kraken.com/api/docs/guides/spot-ws-book-v2/> — book messages carry
  `channel`, `type`, `symbol`, `bids`, `asks`, `checksum`, `timestamp`; there is no
  sequence, update-id, or ordering field.
  **ORIGIN NOTE — this line is the origin of the entire defect class.** An
  unverified factual claim about an external protocol, written here, propagated
  into FR-018a, `data-model.md`, `contracts/data-adapter.yml`, `tasks.md`, and the
  test fixtures — and from there into six work orders of "sequence-gap detection
  proven" claims that were attached to a protocol element that does not exist.
  Preserved by strike-through rather than deleted: the record of a false premise
  is itself evidence. See `docs/decisions/2026-07-19-research-claims-are-load-bearing.md`.

**Alternatives Considered**:
- **Stay on v1 trades feed**: Rejected — insufficient data density; violates Principle V (honest costs require observed spread)
- **Use third-party data provider**: Rejected — adds dependency; violates venue independence (Principle VII)
- **Full order book depth**: Rejected — out of scope for Sprint 2; top-of-book sufficient for cost model

**Evidence** *(citations added 2026-07-19 under rule 0.1e — the originals asserted that
documentation existed without ever pointing at it, which is how the false sequence-number
claim passed review)*:
- Kraken v2 API documentation: <https://docs.kraken.com/api/docs/websocket-v2/book/>
- Checksum algorithm (CRC32, top 10 levels per side, computed over the POST-update
  book): <https://docs.kraken.com/api/docs/guides/spot-ws-book-v2/>
- Snapshot/incremental protocol, message envelope and `qty: 0` deletion semantics:
  <https://docs.kraken.com/api/docs/websocket-v2/book/>
- Legal subscription depths (10/25/100/500/1000): same source

---

## Decision 2: Local Book Maintenance Strategy

**Decision**: Maintain local top-of-book state from v2 snapshot plus incremental updates, validated by CRC checksum.

**Rationale**:
- Top-of-book (best bid/ask) is sufficient for cost model — full depth not required
- Checksum validation on **every** update prevents silent book drift (Kraken permits
  periodic validation; permitted and honest are different standards — FR-018a(c))
- ~~Sequence-number tracking enables gap detection → resnapshot on gap~~
  **CORRECTED 2026-07-19 (WO-009b):** no sequence numbers exist on this channel.
  **Checksum divergence** is the sole detector — and it is the *broader* one: a
  sequence gap detects only a MISSING message, whereas a checksum mismatch detects
  ANY divergence, including misapplied updates and our own book-maintenance bugs.
- Checksum is defined over the **post-update** book, so validation must occur
  **after** applying each update (FR-018a(b))
- 5-consecutive-failure threshold tolerates transient glitches while catching real corruption
- No MarketState may be emitted from checksum failure until a fresh snapshot
  applies and validates (FR-018a(d))

**Alternatives Considered**:
- **Trust updates without checksum**: Rejected — violates Principle V (dishonest data = dishonest backtest)
- **Resync on every failure**: Rejected — too aggressive; transient glitches are common
- ~~**Continue on sequence gap**: Rejected — violates checksum discipline; corrupted state untrustworthy~~
  **SUPERSEDED 2026-07-19 (WO-009b):** reframed as **continue on checksum failure**,
  which is rejected for the same reason. The no-continue principle survives; only its
  trigger changes.

**Evidence** *(citations added 2026-07-19 under rule 0.1e)*:
- Checksum algorithm and post-update ordering:
  <https://docs.kraken.com/api/docs/guides/spot-ws-book-v2/>
- Ground truth available: Kraken publishes a worked 10-level snapshot with checksum
  3310070434, reproduced in `tests/fixtures/kraken_v2_raw_frames.py`. **No incremental
  checksum example is published**, so the incremental path has no documented ground
  truth — verification deferred to first live contact (WO-008b-A).
- 5-failure threshold: NOT a vendor specification. Project judgement, chosen to
  balance noise vs. signal. *(flagged under 0.1e: previously stated as "established
  practice in similar systems" with no source. It is our own call, and is now labelled
  as such rather than borrowing unearned authority.)*

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
- ⚠ **UNCITED MARKET CLAIM (flagged under rule 0.1e, 2026-07-19):** "typical spreads on
  BTC/USD are <0.1%". No source and no measurement backs this. It is plausible and is
  not load-bearing for correctness — the 5% threshold only has to be far above normal —
  but it is stated as fact without provenance. Flagged rather than corrected: the
  observed-spread capture in WO-008b will supply a real measured distribution, at which
  point this line should be replaced with our own data.
- 5% threshold is a project judgement, not a vendor specification.
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

**Decision**: Add reason codes to LAYER_VERB_DETAIL for: abnormal-spread reject, pause-on-book-unavailable, checksum-resync, ~~sequence-gap resnapshot~~.

**CORRECTED 2026-07-19 (WO-009b):** `SEQUENCE_GAP_RESNAPSHOT` is **withdrawn** — it
named an event that cannot occur on this channel (rule 0.1d: a reason code that can
never legitimately fire is a false guarantee). `CHECKSUM_RESYNC` already covers the
real detector and is retained. Whether a distinct code is needed for the
FR-018a(d) **no-emission window** (book unverified, awaiting fresh snapshot) is
**not decided here** — that is WO-008b-A's call, made against a working
implementation. See WO-009b §2.

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
| ~~Sequence gap detection~~ **Checksum divergence detection** *(CORRECTED 2026-07-19, WO-009b)* | ~~Track sequence; on gap, discard book + resnapshot~~ **Validate CRC32 on every update against the post-update book; on mismatch discard book + resnapshot, emitting no MarketState until the fresh snapshot validates** | Q4 (superseded) → amended FR-018a |
| Book unavailable behavior | PAUSE, emit no MarketStates | Q5 in spec clarifications |

**No NEEDS CLARIFICATION items remain** — all resolved in spec.

---

## Dependencies & Best Practices

### Kraken WebSocket v2 API

**Documentation**: ~~https://docs.kraken.com/websockets/~~
**CORRECTED 2026-07-19 (WO-009b):** that URL is the **v1** documentation. Correct v2
references: <https://docs.kraken.com/api/docs/websocket-v2/book/> and
<https://docs.kraken.com/api/docs/guides/spot-ws-book-v2/>

**Key Points** *(every line below was wrong; ALL CORRECTED 2026-07-19, WO-009b)*:
- Connection endpoint: ~~`wss://ws.kraken.com`~~ → **`wss://ws.kraken.com/v2`**
  The struck value is the **v1** endpoint. This line is the origin of
  `WS_URL = "wss://ws.kraken.com"` in `kraken_v2_book.py`.
- Book channel subscription: ~~`{"name":"book","subscription":{"depth":1}}`~~ →
  **`{"method":"subscribe","params":{"channel":"book","symbol":["BTC/USD"],"depth":10}}`**
  The struck form is **v1 framing** *and* carries an **illegal depth**. Kraken
  accepts depth ∈ {10, 25, 100, 500, 1000} only. This line is the origin of
  `BOOK_DEPTH = 1` in `kraken_v2_book.py`, an unsubscribable value.
- Checksum algorithm: CRC-32 over the **top 10 levels per side of the POST-update
  book**, regardless of subscribed depth. (Retained and made precise: the original
  line was correct but underspecified, and the missing "post-update" is a live
  defect — the implementation validates the pre-update book.)
- ~~Sequence numbers in message headers~~ → **NO sequence numbers are transmitted
  on the public book channel.** Messages carry `channel`, `type`, `symbol`, `bids`,
  `asks`, `checksum`, `timestamp`.
- Message envelope: a **dict** `{"channel":"book","type":"snapshot"|"update","data":[…]}`
  with levels as `{"price": …, "qty": …}` objects — **not** positional arrays.
- `qty: 0` **removes** a price level; it does not set its size to zero.
- After applying an update the book must be **truncated to the subscribed depth**;
  Kraken does not send `qty: 0` for levels falling out of scope.

**ORIGIN NOTE:** three of the five defects blocking the WO-008b-A rewrite
(v1 endpoint, `depth: 1`, sequence field) trace directly to this block. The
implementation faithfully built what this research artifact specified. See
`evidence/WO-009b/blocking_defects.txt`.

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
