# Feature Specification: Quote-Level Data + Observed-Spread Cost Model

**Feature Branch**: `002-quote-level-data`

**Created**: 2026-07-15

**Status**: Draft

**Input**: Change the system's market data from a trades feed to quote-level data so the cost model uses real observed spread instead of an assumption. Subscribe to Kraken's book channel (top-of-book: best bid/ask price and size) as the primary data source, keep trades as a secondary enrichment stream (volume, last price), and migrate the data adapter to Kraken WebSocket v2 as part of this change. MarketState becomes quote-centric: timestamp, best bid/ask price and size, derived mid-price and spread, plus rolling trade stats over a window. The backtest cost model must compute spread cost from the actual observed bid/ask spread, not a constant assumption. The v2 book channel's checksum/snapshot protocol must be validated on every update so the local book cannot silently drift out of sync. Out of scope: any change to the strategy's logic or interface — the strategy still takes a MarketState and returns a desired position.

---

## Clarifications

### Session 2026-07-15

- **Q: Checksum failure threshold → A: 5 consecutive failures trigger reconnection/resync.** Transient glitches are tolerated; genuine book corruption is caught after 5 consecutive checksum validation failures.

- **Q: Abnormal spread handling (zero, negative, or >5% of price) → A: REJECT the trade (log + skip).** A negative or impossible spread means the book data is wrong. Principle V forbids fabricating a cost to trade through a data fault. Using "maximum observed spread from history" manufactures a plausible number to keep trading on bad data — that is the exact dishonest-backtest failure this sprint exists to eliminate. When the true cost is unknown, the system does not trade. A skipped trade is free; a trade priced on corrupt data is not.

- **Q: Rolling trade window default → A: 100 trades AND 60 seconds (whichever comes first), configurable.** Hybrid approach self-limits in both active and dead markets while maintaining recency.

- **Q: Sequence gap detection → A: ~~Track sequence numbers; on a gap, discard the local book and request a fresh snapshot.~~** ***SUPERSEDED 2026-07-19 (WO-009).*** This answer assumed a sequence number that the Kraken v2 **public** book channel does not transmit. The clarification is preserved rather than deleted because the record of a false premise is itself evidence. The surviving and correct half of the intent — *discard the local book and re-snapshot rather than trusting patched-over state, with no continue-on-failure path* — is retained in amended **FR-018a**, triggered by **checksum mismatch** instead of by a sequence gap. See Amendment History.

- **Q: Book unavailable, trades still connected → A: PAUSE (emit no MarketStates) until the book recovers.** MarketState is now quote-centric and the cost model requires observed spread. Producing a MarketState with null/stale bid/ask would either break the cost model or silently resurrect an assumed-spread fallback — the precise lie this sprint exists to remove. No honest book means no honest decision, so the system emits nothing, logs the degradation with a reason code, and resumes on recovery.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-Time Quote Processing (Priority: P1)

As a trading system operator, I need the system to consume Kraken's book channel (best bid/ask) as the primary heartbeat so that strategy decisions are based on current market quotes rather than delayed trade prints.

**Why this priority**: The current trades-only feed delivers ~14 events/min, which is too sparse for meaningful strategy signals. Quote-level data provides dense, continuous updates (hundreds to thousands per minute), enabling the strategy to see real market conditions.

**Independent Test**: Can be fully tested by connecting to Kraken's public book feed and verifying that quote updates are received, parsed, and emitted as MarketState objects with bid/ask fields populated.

**Acceptance Scenarios**:

1. **Given** the system is connected to Kraken's book channel, **When** a top-of-book update is received, **Then** a MarketState is emitted with populated best_bid, best_ask, best_bid_size, and best_ask_size fields
2. **Given** the book channel is subscribed, **When** the checksum validation passes, **Then** the local book state is updated and emitted
3. **Given** the book channel emits a snapshot message, **When** the snapshot is processed, **Then** the local book is synchronized with the exchange state

---

### User Story 2 - Observed Spread Cost Model (Priority: P1)

As a backtest analyst, I need the cost model to use the actual observed bid/ask spread from the market data rather than a constant assumption so that backtest results reflect real trading costs.

**Why this priority**: This is the constitutional payoff of the entire change. Principle V (No Backtest Without Costs) requires honest cost modeling. The current assumed spread violates this principle. Real observed spread must be used.

**Independent Test**: Can be fully tested by running a backtest on captured quote data and verifying that spread costs vary according to actual bid/ask spreads in the data, not a fixed percentage.

**Acceptance Scenarios**:

1. **Given** a MarketState with bid/ask prices, **When** a buy order is simulated, **Then** the spread cost is computed as (ask - mid_price) or (ask - bid) / 2
2. **Given** a MarketState with bid/ask prices, **When** a sell order is simulated, **Then** the spread cost is computed as (mid_price - bid) or (ask - bid) / 2
3. **Given** historical quote data with varying spreads, **When** backtested, **Then** the cost model reports different spread costs per trade matching the observed spreads
4. **Given** the cost model, **When** no assumed-spread path exists, **Then** all spread costs are derived from actual bid/ask data

---

### User Story 3 - Book Integrity via Checksum Validation (Priority: P1)

As a system operator, I need the local book state to be validated on every update via Kraken v2's checksum protocol so that the book cannot silently drift out of sync with the exchange.

**Why this priority**: A drifted book means dishonest spread data, which corrupts both strategy signals and cost modeling. The v2 book channel provides CRC checksums for integrity validation. This guard is load-bearing for data honesty.

**Independent Test**: Can be fully tested by manually corrupting a book update (e.g., altering a price) and verifying that the checksum validation fails and the update is rejected.

**Acceptance Scenarios**:

1. **Given** a book update with a valid checksum, **When** the checksum is validated, **Then** the local book state is updated
2. **Given** a book update with an invalid checksum, **When** the checksum validation fails, **Then** the update is rejected and logged with an error
3. **Given** the local book has diverged from exchange state, **When** checksum validation fails consistently, **Then** the system initiates reconnection and resynchronization

---

### User Story 4 - Trades as Secondary Enrichment (Priority: P2)

As a strategy designer, I need trade data (volume, last price) to be available as enrichment fields in MarketState so that volume-based and price-based indicators can still be computed.

**Why this priority**: While quotes are the primary heartbeat, trade data provides valuable enrichment (volume spikes, last traded price) that some strategies may use. This is secondary because quotes alone satisfy the core requirement.

**Independent Test**: Can be fully tested by subscribing to both book and trades channels and verifying that MarketState objects include rolling trade statistics (count, volume, last price) alongside quote data.

**Acceptance Scenarios**:

1. **Given** both book and trades channels are subscribed, **When** a trade is received, **Then** rolling trade stats (count, total volume, last price) are updated in MarketState
2. **Given** quote updates are arriving rapidly, **When** trades are interleaved, **Then** trade stats reflect the rolling window, not the last trade alone
3. **Given** only quotes are received (no trades in window), **When** MarketState is emitted, **Then** trade stats show zero or stale data appropriately

---

### Edge Cases

- What happens when the book channel is temporarily unavailable or disconnected?
- How does the system handle a checksum validation failure (reject update vs. resync)?
- What happens when the spread is abnormally wide (e.g., during volatility)?
- How does the system handle quote updates that arrive out of order?
- What happens when the trades channel is available but book is not (fallback behavior)?
- How does rolling window initialization work on startup (cold start)?

---

## Requirements *(mandatory)*

### Functional Requirements

**Data Source & Channel Subscription**

- **FR-001**: System MUST subscribe to Kraken WebSocket v2 book channel (top-of-book: best bid/ask price and size) as the primary data source
- **FR-002**: System MUST maintain a local book state synchronized with Kraken's exchange state via v2's snapshot/increment protocol
- **FR-003**: System MUST subscribe to Kraken v2 trades channel as a secondary enrichment stream (volume, last price)
- **FR-004**: System MUST validate v2 book channel checksums on every update and reject updates with invalid checksums
- **FR-005**: System MUST use quote updates (book channel) as the primary heartbeat, not trades

**MarketState Schema**

- **FR-006**: MarketState MUST include timestamp, best_bid, best_ask, best_bid_size, best_ask_size fields
- **FR-007**: MarketState MUST include derived mid_price (average of bid and ask)
- **FR-008**: MarketState MUST include derived spread (ask - bid)
- **FR-009**: MarketState MUST include rolling trade statistics: trade_count, total_volume, last_price over a window with default of 100 trades AND 60 seconds (whichever comes first), configurable. Rationale: Hybrid approach self-limits in both active markets (100-trade cap) and dead markets (60-second cap) while maintaining recency.
- **FR-010**: MarketState schema MUST be backward-compatible with strategy interface (strategy still takes MarketState and returns desired position)

**Cost Model**

- **FR-011**: Backtest cost model MUST compute spread cost from actual observed bid/ask spread in MarketState
- **FR-012**: Cost model MUST NOT use assumed or constant spread values — all spread costs derived from real bid/ask data
- **FR-013**: Cost model MUST compute buy-side spread cost as (ask - mid_price) or (ask - bid) / 2
- **FR-014**: Cost model MUST compute sell-side spread cost as (mid_price - bid) or (ask - bid) / 2
- **FR-015**: When spread is zero, negative, or >5% of price (data anomaly), system MUST REJECT the trade (log + skip). Rationale: A negative or impossible spread means book data is wrong. Principle V forbids fabricating a cost to trade through a data fault. Using "maximum observed spread from history" manufactures a plausible number to keep trading on bad data — that is the exact dishonest-backtest failure this sprint exists to eliminate. When the true cost is unknown, the system does not trade. A skipped trade is free; a trade priced on corrupt data is not.
- **FR-015a**: NO assumed or synthetic spread may ever substitute for real observed spread, anywhere in the system. This requirement applies to all code paths — no fallback to assumed spread is permitted when book data is unavailable or anomalous.

**Book Integrity & Validation**

- **FR-016**: System MUST validate CRC checksums on every v2 book update per Kraken's documentation
- **FR-017**: System MUST reject updates with invalid checksums and log the rejection
- **FR-018**: System MUST initiate reconnection and resynchronization after 5 consecutive checksum validation failures. Rationale: Transient glitches are tolerated (1-4 failures); genuine book corruption is caught after 5 consecutive failures, which is a real "the book is corrupt" signal.
- **FR-018a** *(AMENDED 2026-07-19, WO-009 — supersedes the sequence-number mandate; see Amendment History)*: The CRC32 checksum is the **sole** integrity mechanism for the book channel. The system MUST NOT depend on sequence numbers, which the Kraken v2 **public** book channel does not provide. Specifically:
  - **(a) Integrity mechanism.** Book integrity MUST be established by CRC32 checksum validation. No sequence-number tracking, gap detection, or ordering field may be relied upon for the public book channel, because none is transmitted.
  - **(b) Ordering — this is the guarantee, not an implementation detail.** Kraken's CRC32 is defined over the **post-update book state**. Validation MUST therefore occur **after** applying each update to the local book, never before. A mismatch invalidates the **applied** state, and the applied state MUST be discarded — not merely the incoming message. Validating a pre-update book against a post-update checksum is a defect, not an optimization.
  - **(c) Validation frequency: EVERY update.** The system MUST validate the checksum on every single book update. Kraken permits periodic or sampled validation; **permitted and honest are different standards**. This project validates every update. This mandate is stated in the requirement text precisely so it cannot later drift to "periodic" as a throughput optimization.
  - **(d) Recovery semantics, including the no-emission window.** On checksum failure the system MUST: (1) discard the local book; (2) resubscribe / request a fresh snapshot; and (3) **emit NO MarketState from the moment of failure until a fresh snapshot has been applied AND its checksum validates.** A book in an unverified state MUST NOT price anything. Emitting a quote from an unverified book would put an unverifiable spread into the cost model, which is the exact class of lie Principle V forbids. No continue-on-failure path may exist.
  - **(e) Subscription depth is pinned.** Kraken accepts depth values of **10, 25, 100, 500, or 1000** only. This project subscribes at **depth 10**. Rationale: the CRC32 is computed over the top 10 levels per side regardless of subscribed depth, so depth 10 is the smallest legal value that supplies exactly the ladder the checksum requires — no wasted bandwidth, no under-supply. Depth MUST NOT be set to any value outside the legal set. Recorded explicitly because `BOOK_DEPTH = 1` — an illegal value that Kraken rejects and that can never satisfy a 10-level checksum — was only possible while no spec text made depth explicit.
  - **(f) Checksum input MUST derive from the venue's transmitted representation** *(AMENDED 2026-07-19, WO-008b-A3)*. Re-rendering a parsed numeric value into an assumed format is **prohibited** as checksum input. Rationale: re-rendering (e.g. fixed 8-decimal-place formatting) is an **uncited assumption about venue behaviour** — rule 0.1e applied to number formatting rather than to protocol fields. It holds for BTC/USD today and breaks silently on the first symbol or price magnitude Kraken renders differently. "Breaks silently" here is not hypothetical: every checksum mismatches and the book never validates, and we know exactly what that looks like because we watched it for two minutes during the WO-008b-A2 smoke test. Concretely: `json.loads` floats Kraken's numbers before any project code runs, so `Decimal(str(5.1e-05))` yields `"0.000051"` where Kraken transmitted `"0.00005100"` — and the trailing zeros are checksum-bearing digits. The ruled implementation is `json.loads(..., parse_float=Decimal, parse_int=Decimal)`, which preserves the transmitted digits exactly; any concrete reason it cannot work is a STOP-and-ask, not a licence to fall back to a heuristic.

- **FR-019** *(AMENDED 2026-07-19, WO-009)*: System MUST detect book drift (e.g., checksum divergence, stale data) and recover without silent corruption. Note that checksum validation is **broader** than the sequence-gap mechanism originally specified: a sequence gap detects only a *missing* message, whereas a checksum mismatch detects *any* divergence — missed messages, misapplied updates, and the system's own book-maintenance bugs.
- **FR-019a**: When book channel is unavailable but trades channel remains connected, system MUST PAUSE (emit no MarketStates) until the book recovers. Rationale: MarketState is now quote-centric and the cost model requires observed spread. Producing a MarketState with null/stale bid/ask would either break the cost model or silently resurrect an assumed-spread fallback — the precise lie this sprint exists to remove. No honest book means no honest decision, so the system emits nothing, logs the degradation with a reason code, and resumes on recovery.

**API Migration**

- **FR-020**: Data adapter MUST migrate from Kraken WebSocket v1 to v2 as part of this change
- **FR-021**: System MUST handle v2's connection message format, subscription format, and message schema
- **FR-022**: System MUST maintain backward compatibility with existing strategy/risk/execution interfaces (no changes to strategy logic)

**Out of Scope**

- **FR-023**: Strategy logic and interface MUST remain unchanged — strategy still takes MarketState and returns DesiredPosition
- **FR-024**: Risk engine logic and interface MUST remain unchanged
- **FR-025**: Execution layer interfaces MUST remain unchanged
- **FR-026**: Adding new strategy sophistication or indicators is out of scope for this change

### Key Entities

- **QuoteUpdate** *(AMENDED 2026-07-19, WO-009)*: Represents a book update parsed from a raw Kraken v2 book frame, containing the bid/ask ladder (`{price, qty}` levels), the server-sent timestamp, the symbol, the message type (`snapshot` | `update`), and the CRC32 checksum. **No `sequence` field**: the Kraken v2 public book channel transmits no sequence number, and a vestigial field modeling a nonexistent protocol element is what allowed "sequence-gap detection proven" to be asserted against a fiction.
- **LocalBookState**: Maintains the synchronized best bid/ask from the exchange, validated by checksums
- **RollingTradeStats**: Aggregates trade data over a configurable window (count, volume, last price, VWAP if needed)
- **MarketState**: Quote-centric data structure containing timestamp, bid/ask fields, derived mid-price/spread, and rolling trade stats

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Quote updates are received and processed at a rate consistent with Kraken's public book channel (hundreds to thousands per minute, not ~14/min as with trades)
- **SC-002**: Cost model uses 100% observed spread data — zero trades are executed with assumed spread values
- **SC-003**: Checksum validation passes on >99.9% of updates (failure rate <0.1% for healthy feed)
- **SC-004**: Book resynchronization completes within 30 seconds of disconnection
- **SC-005**: Backtest results show spread cost variability matching actual observed spreads in the data
- **SC-006**: All 36 existing tests continue to pass after the migration (no regressions in strategy/risk/execution behavior)
- **SC-007**: Import-linter contracts remain satisfied (no layer boundary violations)

### Quality Gates

- **QG-001**: No assumed-spread code path remains in cost model — verified by code review and tests
- **QG-002**: Strategy interface is unchanged — strategy still accepts MarketState and returns DesiredPosition
- **QG-003**: v2 book channel checksum validation is exercised in tests with both valid and invalid checksums
- **QG-004**: Constitution principles are satisfied, especially Principle V (No Backtest Without Costs) and Principle VII (Venue Independence)

---

## Assumptions

- Kraken v2 WebSocket API is stable and publicly documented for the book channel
- The rolling window for trade statistics is configurable with a reasonable default (e.g., 100 trades or 60 seconds)
- Checksum validation logic is specified in Kraken's v2 API documentation
- The existing strategy (TrivialMomentumStrategy) will continue to work with quote-centric MarketState without modification
- Book depth is top-of-book only (best bid/ask) — full order book depth is out of scope
- Network connectivity to Kraken's WebSocket servers is reliable enough for production use
- The spread in quote data is normally positive (ask > bid) — zero/negative spreads are treated as data anomalies

### Dependencies

- Kraken WebSocket v2 API documentation and public endpoint availability
- Existing test suite (36 tests) provides regression coverage for strategy/risk/execution behavior
- Constitution (`.specify/memory/constitution.md`) governs all decisions
- Spec template (`.specify/templates/spec-template.md`) defines required sections

### Scope Boundaries

**IN SCOPE:**
- Data layer changes (adapter migration to v2, book channel subscription)
- MarketState schema changes (adding bid/ask fields)
- Cost model changes (observed spread vs assumed)
- Book integrity (checksum validation)
- Tests for new functionality (quote processing, checksum validation, observed spread costs)

**OUT OF SCOPE:**
- Strategy logic changes (strategy interface unchanged)
- Risk engine changes
- Execution layer changes
- New strategies or indicators
- Full order book depth (top-of-book only)
- Order book management beyond best bid/ask
- Changes to other venues (Kraken-only change)
- GUI or visualization changes
- Performance optimizations beyond correctness

---

## Constitutional Compliance

This specification complies with the following constitutional principles:

- **Principle I (Truth Before Profit)**: FR-011 through FR-015 ensure cost model uses real observed spread, not assumptions
- **Principle II (Walking Skeleton Before Palace)**: This change attaches to an already-working end-to-end loop
- **Principle IV (Layered Architecture)**: FR-023 through FR-025 maintain layer boundaries; changes are data-layer only
- **Principle V (No Backtest Without Costs)**: FR-011 and FR-012 are the core requirement — observed spread only
- **Principle VII (Venue Independence)**: This is a Kraken-specific change but maintains the abstraction; swapping venues later remains a single-module change
- **Principle VIII (Total Observability)**: All book validations and checksum failures are logged with reason codes
- **Principle IX (Secrets and Safety Rails)**: No credentials are required for public Kraken v2 WebSocket

---

## Notes

This specification was generated as part of WO-003 (Sprint 2 Spec Kickoff). The three load-bearing items verified:
1. ✅ Cost model uses observed spread (FR-011, FR-012, SC-002, SC-005, QG-001)
2. ✅ v2 book checksum validation on every update (FR-004, FR-016 through FR-019, SC-003, QG-003)
3. ✅ Strategy logic/interface is out of scope (FR-023 through FR-026, SC-006, QG-002)

---

## Amendment History

### 2026-07-19 — WO-009: FR-018a sequence-number mandate replaced by CRC32 checksum semantics

**What was wrong.** FR-018a mandated tracking sequence numbers for book updates and
detecting gaps. **The Kraken v2 public book channel transmits no sequence number.**
CRC32 checksum is the sole integrity mechanism it provides. Sequence numbers exist on
Kraken v2 only for private/execution channels.

**How it survived review.** The Phase 1-3 fixtures carried a synthetic `sequence` field,
so "sequence-gap detection proven" was a guarantee attached to a fictional protocol. The
fixtures supplied pre-parsed `QuoteUpdate` objects rather than raw frames, so the parse
path was never under test and the fixtures drifted toward whatever the implementation
expected — rather than toward what the venue actually sends.

**Sections amended:**

| Section | Change |
|---|---|
| Clarifications (sequence-gap Q/A) | Struck through and marked SUPERSEDED; original text preserved |
| FR-018a | Replaced with CRC32 semantics: mechanism, post-update ordering, every-update validation, recovery incl. no-emission window, pinned depth |
| FR-019 | "sequence gaps" → "checksum divergence"; notes checksum is the broader detector |
| Key Entities → QuoteUpdate | `sequence` removed; raw-frame field set specified |

**What is materially stronger, not merely different.** Checksum validation is *broader*
than the mechanism it replaces. A sequence gap detects only a **missing message**. A
checksum mismatch detects **any divergence** — missed messages, misapplied updates, and
the system's own book-maintenance bugs. The amendment closes a fiction and widens real
coverage at the same time.

**What is now pinned that was previously unstated.** Subscription depth. Kraken accepts
only 10/25/100/500/1000; this project uses **10**. `BOOK_DEPTH = 1` — illegal at the
venue, and incapable of ever satisfying a 10-level checksum — was possible only because
no spec text made depth explicit.

**Not in scope of this amendment.** No implementation was changed. Wiring live frames
through the parse path is WO-008b-A.

**Evidence:** `evidence/WO-009/`, and the diagnosis in `evidence/WO-008b-DIAG/`
(`sequence_usage.txt`, `fixture_fidelity_audit.txt`, `checksum_pre_vs_post_update.txt`).
