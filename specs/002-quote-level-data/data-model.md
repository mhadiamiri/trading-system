# Data Model: Quote-Level Data + Observed-Spread Cost Model

**Feature**: 002-quote-level-data
**Date**: 2026-07-15

---

## Overview

This document defines the data entities for the Quote-Level Data feature. The core change is adding quote-centric fields to MarketState and introducing a local book state for the v2 adapter.

---

## Entity 1: LocalBookState (NEW)

**Module**: `src/trading/data/adapters/kraken_v2_book.py` (internal to adapter)

**Purpose**: Maintain synchronized top-of-book state from Kraken v2 exchange, validated by checksums.

### Fields

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `best_bid_price` | `Decimal` | Required, >0 | Best bid price from exchange |
| `best_bid_size` | `Decimal` | Required, >0 | Size at best bid |
| `best_ask_price` | `Decimal` | Required, >0 | Best ask price from exchange |
| `best_ask_size` | `Decimal` | Required, >0 | Size at best ask |
| ~~`last_sequence`~~ | ~~`int`~~ | ~~Required, >=0~~ | ~~Last sequence number received~~ **REMOVED 2026-07-19 (WO-009b): the Kraken v2 public book channel transmits no sequence number. See amended FR-018a(a).** |
| `last_checksum` | `str` | Required | Last checksum string from exchange |
| `consecutive_failures` | `int` | Required, >=0, <=5 | Count of consecutive checksum failures |
| `is_paused` | `bool` | Required | True when book channel unavailable (no MarketStates emitted) |

### State Transitions

```
INITIAL ──snapshot_received──> SYNCHRONIZED
SYNCHRONIZED ──incremental_update_valid──> SYNCHRONIZED
SYNCHRONIZED ──incremental_update_invalid_checksum──> SYNCHRONIZED (consecutive_failures++)
SYNCHRONIZED ──consecutive_failures==5──> RESYNC_REQUIRED
SYNCHRONIZED ──checksum_mismatch_on_applied_state──> RESYNC_REQUIRED
RESYNC_REQUIRED ──(NO MarketState emitted while in this state)──> RESYNC_REQUIRED
RESYNC_REQUIRED ──reconnect_snapshot──> SYNCHRONIZED
ANY ──book_channel_lost──> PAUSED
PAUSED ──book_channel_recovered──> SYNCHRONIZED
```

### Validation Rules

1. **Checksum validation**: On **every** incremental update, apply the update to the local book **first**, then compute CRC-32 over the **post-update** top-10-per-side ladder and compare to the exchange checksum. On mismatch, discard the **applied** state. (FR-018a(b),(c) — validating the pre-update book is a defect.)
2. ~~**Sequence gap detection**: If incoming sequence != last_sequence + 1, discard book and request fresh snapshot.~~ **REPLACED 2026-07-19 (WO-009b) by checksum-divergence recovery**: on checksum mismatch, discard the local book, request a fresh snapshot, and **emit NO MarketState until that snapshot is applied and its checksum validates** (FR-018a(d)). Checksum divergence is the broader detector — it catches misapplied updates and our own book-maintenance bugs, which a sequence counter cannot.
3. **Consecutive failure threshold**: After 5 consecutive checksum failures, reconnect and resync.
4. **Bid/Ask sanity**: Reject updates where bid >= ask (negative spread).

### Relationships

- **Consumes**: Kraken v2 WebSocket messages (snapshot + incremental)
- **Produces**: MarketState (via adapter interface)

---

## Entity 2: MarketState (MODIFIED)

**Module**: `src/trading/data/market_state.py`

**Purpose**: Quote-centric market data for strategy/risk/backtest consumption.

### Fields

| Field | Type | Validation | Description | Change |
|-------|------|------------|-------------|--------|
| `timestamp` | `datetime` | Required, UTC | Event timestamp | No change |
| `best_bid` | `Decimal` | Required, >0 | Best bid price | **NEW** |
| `best_ask` | `Decimal` | Required, >0 | Best ask price | **NEW** |
| `best_bid_size` | `Decimal` | Required, >=0 | Size at best bid | **NEW** |
| `best_ask_size` | `Decimal` | Required, >=0 | Size at best ask | **NEW** |
| `mid_price` | `Decimal` | Required, >0 | Derived: (bid + ask) / 2 | **NEW** |
| `spread` | `Decimal` | Required, >=0 | Derived: ask - bid | **NEW** |
| `trade_count` | `int` | Required, >=0 | Trades in rolling window | **NEW** |
| `total_volume` | `Decimal` | Required, >=0 | Total volume in rolling window | **NEW** |
| `last_price` | `Decimal` | Optional | Last trade price in window | **NEW** |

### Removed Fields (Sprint 1)

| Field | Reason |
|-------|--------|
| `price` | Replaced by bid/ask/mid |
| `volume` | Replaced by rolling total_volume |

### Validation Rules

1. **Bid/Ask sanity**: bid > 0, ask > 0, bid < ask (positive spread)
2. **Derived fields**: mid_price = (bid + ask) / 2; spread = ask - bid
3. **Rolling window**: trade_count and total_volume reflect configured window (default: 100 trades AND 60 seconds, whichever first)

### Relationships

- **Produced by**: `KrakenV2BookAdapter`, `SimulatedMarketFeed` (updated), `KrakenPublicFeed` (deprecated)
- **Consumed by**: Strategy (`decide(market_state)`), Risk (`check(desired_position, market_state)`), Backtest (replay), Execution (cost model)

---

## Entity 3: RollingTradeStats (NEW)

**Module**: `src/trading/data/adapters/kraken_v2_book.py` (internal to adapter)

**Purpose**: Aggregate trade data over a rolling window for enrichment.

### Fields

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `trades` | `list[Trade]` | Max len = window_size | Rolling buffer of trades |
| `window_count_cap` | `int` | Required, >0 | Max trades in window (default: 100) |
| `window_time_cap` | `int` | Required, >0 | Max seconds in window (default: 60) |

### Nested Entity: Trade

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `price` | `Decimal` | Required, >0 | Trade price |
| `volume` | `Decimal` | Required, >0 | Trade volume |
| `timestamp` | `datetime` | Required, UTC | Trade timestamp |

### Computed Fields

| Field | Computation | Description |
|-------|-------------|-------------|
| `count` | `len(trades)` | Number of trades in window |
| `total_volume` | `sum(t.volume for t in trades)` | Total volume in window |
| `last_price` | `trades[-1].price if trades else None` | Last trade price |

### Validation Rules

1. **Window pruning**: Remove trades older than `window_time_cap` seconds
2. **Count cap**: If `len(trades) > window_count_cap`, remove oldest
3. **Hybrid truncation**: Apply BOTH time and count caps (whichever hits first)

### Relationships

- **Consumes**: Kraken v2 trades channel messages
- **Produced by**: `KrakenV2BookAdapter`
- **Embedded in**: MarketState (as `trade_count`, `total_volume`, `last_price`)

---

## Entity 4: QuoteUpdate (NEW)

**Module**: `src/trading/data/adapters/kraken_v2_book.py` (internal to adapter)

**Purpose**: Represents a top-of-book update from Kraken v2 WebSocket.

### Fields

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `bid_price` | `Decimal` | Required, >0 | Best bid price |
| `bid_size` | `Decimal` | Required, >=0 | Size at best bid |
| `ask_price` | `Decimal` | Required, >0 | Best ask price |
| `ask_size` | `Decimal` | Required, >=0 | Size at best ask |
| `checksum` | `str` | Required | CRC checksum from exchange |
| ~~`sequence`~~ | ~~`int`~~ | ~~Required, >=0~~ | ~~Sequence number~~ **REMOVED 2026-07-19 (WO-009b): not transmitted by the venue.** |
| `timestamp` | `datetime` | Required, UTC | Update timestamp |

### Validation Rules

1. **Checksum format**: Must be valid CRC-32 per Kraken docs, computed over the post-update top-10-per-side ladder
2. ~~**Sequence monotonic**: sequence should increase (gap = resync)~~ **REMOVED 2026-07-19 (WO-009b): no sequence field exists.**

### Relationships

- **Produced by**: Parsing Kraken v2 WebSocket messages
- **Consumed by**: `LocalBookState` (for validation and state update)

---

## Data Flow

```
Kraken v2 WebSocket
    │
    ├─> Snapshot Message ──> QuoteUpdate ──> LocalBookState (initial)
    │
    └─> Incremental Message ──> QuoteUpdate ──> LocalBookState (update)
                                               │
                                               ├─> Apply update to local book
                                               ├─> Checksum Validation (post-update)
                                               └─> MarketState (on success)
                                                      │
                                                      └─> Strategy.decide()
                                                              │
                                                              └─> Risk.check()
                                                                      │
                                                                      └─> Execution (cost model uses spread)
```

---

## Schema Changes

### MarketState Migration

**Before (Sprint 1)**:
```python
@dataclass
class MarketState:
    timestamp: datetime
    symbol: str
    price: Decimal
    volume: Decimal
```

**After (Sprint 2)**:
```python
@dataclass
class MarketState:
    timestamp: datetime
    symbol: str
    best_bid: Decimal
    best_ask: Decimal
    best_bid_size: Decimal
    best_ask_size: Decimal
    mid_price: Decimal  # derived
    spread: Decimal     # derived
    trade_count: int
    total_volume: Decimal
    last_price: Optional[Decimal]
```

### Backward Compatibility

**Strategy Interface**: Unchanged — `decide(market_state) -> DesiredPosition`
- Strategies may read new fields but must not require interface changes
- Existing strategies (e.g., `TrivialMomentumStrategy`) work without modification

**Risk Interface**: Unchanged — `check(desired_position, market_state) -> CheckedPosition`
- Risk layer may read new fields but interface unchanged

**Execution Interface**: Unchanged — cost model reads spread from MarketState

---

## Storage Model

### Live Data

- **In-memory**: `LocalBookState` (adapter internal)
- **In-memory**: `RollingTradeStats` (adapter internal)
- **Emitted**: `MarketState` (passed to strategy/risk/execution)

### Backtest Data

**Format**: Parquet files (append-only)

**Schema**:
```python
{
    "timestamp": "datetime64[ns]",
    "symbol": "string",
    "best_bid": "decimal",
    "best_ask": "decimal",
    "best_bid_size": "decimal",
    "best_ask_size": "decimal",
    "mid_price": "decimal",
    "spread": "decimal",
    "trade_count": "int64",
    "total_volume": "decimal",
    "last_price": "decimal"
}
```

**Replay Behavior**:
- Backtest reads stored quotes
- Reconstructs MarketState identically to live
- Cost model computes spread from observed bid/ask (no synthetic path)

---

## Validation Summary

| Entity | Key Validations |
|--------|----------------|
| LocalBookState | Post-update checksum match, bid/ask sanity (~~sequence continuity~~ removed WO-009b) |
| MarketState | bid > 0, ask > 0, bid < ask, derived fields computed correctly |
| RollingTradeStats | Window pruning, count/time caps applied |
| QuoteUpdate | Checksum format (~~sequence monotonic~~ removed WO-009b) |

---

## Testing Requirements

Per spec (SC-003, QG-003), tests must prove:

1. **Checksum validation bites**: Corrupted update fails validation
2. **Recovery fires**: Resync on 5 failures, resnapshot on gap, pause on book lost
3. **No synthetic spread**: Cost model rejects on null/abnormal spread
4. **Backtest honesty**: Replay from stored quotes produces identical spread costs

---

## Summary

**New Entities**: `LocalBookState`, `RollingTradeStats`, `QuoteUpdate` (all adapter-internal)
**Modified Entities**: `MarketState` (quote-centric fields)
**Unchanged Entities**: All strategy/risk/execution interfaces

**Key Point**: All v2/book-specific detail is internal to the adapter. Above the adapter (`data/` consumers), only the standard `MarketState` interface is visible.
