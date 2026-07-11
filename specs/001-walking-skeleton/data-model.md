# Data Model: Walking Skeleton

**Feature**: 001-walking-skeleton
**Date**: 2026-07-11
**Phase**: 1 (Design)

## Core Entities

### 1. MarketState

Represents a single aggregated view of market data at a point in time.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime (UTC)` | Event timestamp from exchange |
| `symbol` | `str` | Trading pair (e.g., "BTC/USD") |
| `bid_price` | `Decimal` | Current best bid price |
| `ask_price` | `Decimal` | Current best ask price |
| `last_price` | `Decimal` | Last traded price |
| `volume_24h` | `Decimal` | 24-hour trading volume |

**Invariants**:
- `ask_price >= bid_price` (spread is non-negative)
- `timestamp` is monotonically increasing per feed

**Source**: Market data feed adapter

---

### 2. DesiredPosition

Represents the strategy's desired position output.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime (UTC)` | When the decision was made |
| `symbol` | `str` | Trading pair |
| `side` | `Side` | `Side.BUY` (long), `Side.SELL` (short), or `Side.HOLD` (flat) |
| `quantity` | `Decimal` | Position size in base currency (positive for long, negative for short) |
| `confidence` | `float` | Strategy confidence score (0.0 to 1.0) |

**Invariants**:
- `quantity > 0` if `side == Side.BUY`
- `quantity < 0` if `side == Side.SELL`
- `quantity == 0` if `side == Side.HOLD`

**Source**: Strategy.decide()

---

### 3. ApprovedOrder

Represents a risk-approved order ready for execution.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime (UTC)` | When approved by risk engine |
| `symbol` | `str` | Trading pair |
| `side` | `Side` | `Side.BUY` or `Side.SELL` |
| `size` | `Decimal` | Order size (always positive, clamped by risk) |
| `price` | `Decimal` | Limit price (or market price approximation) |
| `reason_code` | `str` | Risk decision reason (e.g., "RISK_PASS", "RISK_CLAMP_MAX_POSITION") |
| `original_size` | `Decimal` | Original requested size before clamping (for audit trail) |

**Invariants**:
- `size > 0` (risk engine ensures non-zero)
- `size <= original_size` (clamp only reduces)
- `side` does not flip from original DesiredPosition (clamp only reduces size)

**Source**: RiskEngine.check()

---

### 4. DecisionRecord

Represents an auditable decision at any layer (strategy, risk, execution).

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime (UTC)` | Decision timestamp |
| `layer` | `Layer` | `Layer.STRATEGY`, `Layer.RISK`, `Layer.EXECUTION`, or `Layer.BACKTEST` |
| `event_type` | `str` | Event type (e.g., "NO_SIGNAL", "PASS", "CLAMP", "VETO", "ORDER_SUBMITTED", "FILLED") |
| `reason_code` | `str` | Controlled vocabulary code (LAYER_VERB_DETAIL format) |
| `venue` | `str` | Venue identifier (e.g., "bybit_testnet") |
| `symbol` | `str` | Trading pair |
| `side` | `Side | None` | Order side (None for no-signal decisions) |
| `size` | `Decimal | None` | Order size (None for no-signal decisions) |
| `intended_price` | `Decimal | None` | Intended price (None for rejections) |
| `executed_price` | `Decimal | None` | Actual executed price (None if not executed) |
| `fees` | `Decimal | None` | Fees paid (None if not executed) |
| `strategy_version` | `str` | Strategy version identifier |
| `feature_snapshot_hash` | `str` | Hash of feature/market snapshot the decision acted on |

**Invariants**:
- No secret or credential appears in any field
- `reason_code` follows controlled vocabulary (see below)
- `timestamp` is UTC timezone-aware

**Source**: All layers (via logkit)

---

### 5. Fill (Trade)

Represents an executed trade (simulated or real).

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime (UTC)` | Fill timestamp |
| `symbol` | `str` | Trading pair |
| `side` | `Side` | `Side.BUY` or `Side.SELL` |
| `size` | `Decimal` | Filled quantity |
| `fill_price` | `Decimal` | Price before spread adjustment |
| `spread_cost` | `Decimal` | Bid/ask spread cost paid |
| `slippage_cost` | `Decimal` | Slippage adjustment |
| `fees` | `Decimal` | Trading fees paid |
| `total_cost` | `Decimal` | `spread_cost + slippage_cost + fees` |
| `cad_value` | `Decimal` | CAD value for Canadian tax records |

**Invariants**:
- `total_cost = spread_cost + slippage_cost + fees`
- All cost components are non-negative
- `cad_value` is calculated from `size * fill_price` converted to CAD

**Source**: Execution layer (simulated or real)

---

### 6. PositionState

Represents the current portfolio state.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `symbol` | `str` | Trading pair |
| `current_quantity` | `Decimal` | Current position (positive=long, negative=short, zero=flat) |
| `average_entry_price` | `Decimal` | Average entry price for current position |
| `unrealized_pnl` | `Decimal` | Unrealized profit/loss |
| `realized_pnl` | `Decimal` | Realized profit/loss (closed trades) |
| `daily_pnl` | `Decimal` | P&L for current trading day |

**Invariants**:
- `current_quantity` can be negative (short selling allowed in paper trading)
- `unrealized_pnl` is calculated from current market prices
- `realized_pnl` accumulates from closed trades

**Source**: Execution layer (maintained state)

---

## Enums and Controlled Vocabularies

### Side Enum
```python
class Side(Enum):
    BUY = "BUY"      # Long position
    SELL = "SELL"    # Short position
    HOLD = "HOLD"    # No position / flat
```

### Layer Enum
```python
class Layer(Enum):
    STRATEGY = "STRATEGY"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    BACKTEST = "BACKTEST"
```

### Reason Code Vocabulary (LAYER_VERB_DETAIL format)

**Strategy Layer**:
- `STRAT_NO_SIGNAL` — No trading signal generated
- `STRAT_SIGNAL_BUY` — Buy signal generated
- `STRAT_SIGNAL_SELL` — Sell signal generated

**Risk Layer**:
- `RISK_PASS` — Order passed unchanged
- `RISK_CLAMP_MAX_POSITION` — Clamped due to position limit
- `RISK_VETO_DAILY_LOSS` — Rejected due to daily loss limit
- `RISK_VETO_KILL_SWITCH` — Rejected due to kill switch engaged
- `RISK_VETO_INVALID_INPUT` — Rejected due to invalid input
- `RISK_VETO_INSUFFICIENT_BALANCE` — Rejected due to insufficient balance

**Execution Layer**:
- `EXEC_ORDER_SUBMITTED` — Order submitted to venue
- `EXEC_ORDER_FILLED` — Order filled completely
- `EXEC_ORDER_PARTIAL_FILLED` — Order partially filled (not expected in walking skeleton)
- `EXEC_ORDER_CANCELLED` — Order cancelled
- `EXEC_BACKOFF_RATE_LIMIT` — Backing off due to rate limit

**Backtest Layer**:
- `BACKTEST_START` — Backtest started
- `BACKTEST_COMPLETE` — Backtest completed
- `BACKTEST_DATA_ERROR` — Data error encountered

---

## Data Flow

```
MarketState → Strategy.decide() → DesiredPosition
                                   ↓
RiskEngine.check() → ApprovedOrder (PASS/CLAMP/VETO)
                          ↓
Execution.place_order() → Fill
                          ↓
DecisionRecord (logged at every stage)
```

---

## Storage Mapping

| Entity | Storage | Table/File |
|--------|---------|------------|
| MarketState (raw) | Parquet | `data/market_events.parquet` (append-only) |
| DecisionRecord | SQLite | `decision_logs` table |
| Fill | SQLite | `trades` table |
| PositionState | SQLite | `positions` table (in-memory for live) |

---

## Relationships

```
MarketState (feed)
    ↓
DesiredPosition (strategy output)
    ↓
ApprovedOrder (risk-approved)
    ↓
Fill (executed) → DecisionRecord (audit trail)
    ↓
PositionState (updated)
```

**Key Relationships**:
- One `MarketState` → Zero or One `DesiredPosition` (strategy may not emit signal)
- One `DesiredPosition` → One `ApprovedOrder` or DecisionRecord (VETO)
- One `ApprovedOrder` → One `Fill`
- Every decision → One `DecisionRecord`
