# Implementation Plan: Walking Skeleton - Systematic Crypto Trading System

**Branch**: `001-walking-skeleton` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-walking-skeleton/spec.md`

## Summary

Build the walking skeleton of a systematic crypto trading system: the simplest end-to-end loop that connects to a single crypto pair's live testnet market data feed, evaluates a trivial strategy signal, passes decisions through deterministic risk checks, executes simulated trades, and logs every decision with reason codes. The system applies realistic trading costs (fees, spread, slippage) to every simulated trade and produces cost-inclusive P&L results. Technical approach: pure Python 3.11+ implementation on Windows with local SQLite/Parquet storage, four-layer architecture (data→strategy→risk→execution) with import-boundary enforcement, and Bybit testnet as provisional venue behind a strict adapter interface.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- `pytest` for testing
- `sqlite3` (stdlib) for structured data storage
- `pyarrow` for Parquet append-only raw market events
- `httpx` or `aiohttp` for HTTP client to testnet
- `pydantic` for data validation
- `pyyaml` for config loading
- `python-dotenv` for environment variable management
- `import-linter` for CI boundary enforcement

**Storage**:
- SQLite for positions, trades, decision logs (structured queryable data)
- Parquet files for raw market events (append-only, never mutated)
- Local filesystem only — no Kafka, Redis, or distributed storage

**Testing**: pytest with coverage

**Target Platform**: Windows 11

**Project Type**: CLI application / trading system backend

**Performance Goals**:
- Process 100+ consecutive market data updates without error
- Backtest 1000 historical data points in under 60 seconds
- Sub-second decision latency per market update

**Constraints**:
- Deterministic risk engine (no I/O, network, randomness, or clock reads in logic)
- Four-layer import boundaries enforced in CI (build fails on violation)
- Impossible to place real-money order by accident (TRADING_ENV defaults to testnet)
- No secrets in logs or git

**Scale/Scope**:
- Single crypto pair: BTC/USD
- Single venue: Bybit testnet (provisional)
- Single strategy: trivial momentum/volume signal
- Single process: local execution only
- Phase 1 scope: walking skeleton, not production system

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Truth Before Profit
✅ **SATISFIED**: Specification requires cost-inclusive P&L reporting (FR-018, FR-019, FR-021, FR-022). Backtest applies fees + spread + slippage to every trade (FR-017, FR-018, FR-019). Negative P&L is acceptable (SC-009).

### Principle II: Walking Skeleton Before Palace
✅ **SATISFIED**: Specification requires complete end-to-end loop (FR-026, SC-007). Single pair, single strategy, single venue. No sophistication beyond basic loop.

### Principle III: AI Proposes, Deterministic Code Disposes
✅ **SATISFIED**: Risk engine has no ML/AI dependencies (FR-025). AI is not in live decision path. Import boundary will enforce this mechanically.

### Principle IV: Layered Architecture, Enforced Boundaries
✅ **SATISFIED**: Four layers specified: data → strategy → risk → execution. Import-linter will enforce boundaries in CI. No cross-layer imports allowed.

### Principle V: No Backtest Without Costs
✅ **SATISFIED**: Backtest applies fees, spread, and slippage to every trade (FR-017, FR-018, FR-019). No cost-free code path exists.

### Principle VI: The Risk Engine Is Sovereign
✅ **SATISFIED**: Risk engine returns pass/clamp/veto (FR-004). Clamp only reduces toward zero (FR-004). Kill switch blocks new orders (FR-007, FR-008). Hard limits: max position (FR-006), max daily loss (FR-007).

### Principle VII: Venue Independence
✅ **SATISFIED**: Bybit testnet is provisional, accessed only through strict ExchangeClient interface. All venue-specific code confined to single adapter module. Swapping venue is one-module change.

### Principle VIII: Total Observability & Provenance
✅ **SATISFIED**: Every decision logged with reason code and context (FR-009, FR-010). Decision records include all required fields (FR-010). Raw data is append-only (FR-013). CAD tax fields captured (FR-015).

### Principle IX: Secrets and Safety Rails
✅ **SATISFIED**: Secrets only in gitignored .env (FR-014). No secrets in logs (FR-014). TRADING_ENV defaults to testnet. Execution client refuses live/mainnet without explicit override.

### Phase-1 Scope Constraints
✅ **SATISFIED**: One pair (BTC/USD), spot, one strategy, one venue (Bybit testnet), no leverage, no derivatives, no AI in decision path, no alternative data, no Kafka/Redis/microservices.

**CONSTITUTION CHECK RESULT**: ✅ **PASS** — All principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/001-walking-skeleton/
├── plan.md              # This file
├── research.md          # Technical research findings
├── data-model.md        # Core entities and relationships
├── quickstart.md        # Developer quickstart guide
├── contracts/           # Interface definitions
│   ├── strategy.py      # Strategy interface
│   ├── exchange_client.py  # ExchangeClient interface
│   └── risk_engine.py   # Risk engine interface
└── tasks.md             # Generated by /speckit-tasks
```

### Source Code (repository root)

```text
src/
└── trading/
    ├── __init__.py
    ├── data/
    │   ├── __init__.py
    │   ├── market_state.py      # MarketState entity
    │   ├── feed.py              # Market data feed interface
    │   ├── storage.py           # SQLite/Parquet storage layer
    │   └── adapters/
    │       └── bybit_testnet.py  # Bybit testnet adapter (isolated)
    ├── strategy/
    │   ├── __init__.py
    │   ├── interface.py         # Strategy interface (decide())
    │   └── trivial.py           # Trivial momentum/volume strategy
    ├── risk/
    │   ├── __init__.py
    │   ├── interface.py         # Risk engine interface (check())
    │   ├── engine.py            # Pure deterministic risk engine
    │   └── limits.py            # Configurable hard limits
    ├── execution/
    │   ├── __init__.py
    │   ├── interface.py         # ExchangeClient interface
    │   ├── paper.py             # Simulated execution (paper trading)
    │   └── adapters/
    │       └── bybit_testnet.py  # Bybit testnet adapter (isolated)
    ├── backtest/
    │   ├── __init__.py
    │   ├── runner.py            # Backtest runner
    │   └── costs.py             # Cost model (fees, spread, slippage)
    ├── logkit/
    │   ├── __init__.py
    │   ├── decision.py          # Decision record logging
    │   └── provenance.py        # Strategy version, snapshot hash
    └── loop/
        ├── __init__.py
        └── live.py              # Live trading loop orchestrator

config/
├── __init__.py
├── config.yaml                 # Configuration (NOT secrets)
└── defaults.yaml               # Default values

tests/
├── __init__.py
├── conftest.py                 # pytest fixtures
├── test_risk.py                # Risk engine tests (incl. clamp test)
├── test_backtest_costs.py      # Cost model verification
├── test_boundaries.py          # Import boundary tests
├── integration/
│   ├── test_live_loop.py       # End-to-end live loop test
│   └── test_backtest.py        # End-to-end backtest test
└── unit/
    ├── test_strategy.py
    ├── test_feed.py
    └── test_storage.py

data/                           # Gitignored: raw market events (Parquet)
logs/                           # Gitignored: decision logs
.env                            # Gitignored: secrets
.env.example                    # Git tracked: variable names only
.pytest.ini                      # pytest configuration
.importlinter.yaml              # Import boundary rules
pyproject.toml                   # Python project config
requirements.txt                 # Dependencies
requirements-dev.txt             # Development dependencies
```

**Structure Decision**: Single-project Python layout with `src/trading/` as the root package. The four-layer architecture (data→strategy→risk→execution) maps directly to subdirectories. Venue-specific code is isolated in `adapters/` subdirectories. All configuration in `config/`. Tests mirror the source structure under `tests/`. Data and logs directories are gitignored and created at runtime.

## Complexity Tracking

> No constitutional violations requiring justification.

---

## Phase 0: Research

**OUTPUT**: `research.md`

Research topics to resolve:
1. Bybit testnet API authentication and WebSocket market data endpoints
2. Bybit testnet order placement and cancellation APIs (for interface definition)
3. Parquet append-only write patterns with pyarrow
4. SQLite schema design for decision logs and trade records
5. Import-linter configuration for four-layer boundaries

## Phase 1: Design

**OUTPUTS**: `data-model.md`, `contracts/`, `quickstart.md`

### Data Model Entities

**Core Entities** (to be defined in `data-model.md`):
1. **MarketState** — Aggregated market data view (timestamp, symbol, bid, ask, last_price, volume)
2. **DesiredPosition** — Strategy output (timestamp, symbol, side, quantity, confidence)
3. **ApprovedOrder** — Risk-approved order (timestamp, symbol, side, size, price)
4. **DecisionRecord** — Auditable decision (timestamp, layer, event_type, reason_code, venue, symbol, side, size, intended_price, executed_price, fees, strategy_version, feature_snapshot_hash)
5. **Trade/Fill** — Executed trade (timestamp, symbol, side, size, fill_price, fees, spread_cost, slippage_cost, cad_value)

### Interfaces

**Strategy Interface** (`contracts/strategy.py`):
```python
class Strategy(Protocol):
    def decide(self, market_state: MarketState) -> Optional[DesiredPosition]:
        """Return desired position or None for 'no signal'."""
```

**ExchangeClient Interface** (`contracts/exchange_client.py`):
```python
class ExchangeClient(Protocol):
    async def place_order(self, order: ApprovedOrder) -> Fill:
        """Place order and return fill (simulated or real)."""

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order. Returns True if cancelled."""

    async def get_market_data(self) -> AsyncIterator[MarketState]:
        """Stream market data updates."""
```

**Risk Engine Interface** (`contracts/risk_engine.py`):
```python
class RiskEngine(Protocol):
    def check(self, desired: DesiredPosition, current_state: PositionState, utc_now: datetime) -> RiskDecision:
        """Return PASS, CLAMP, or VETO with reason code."""
```

### Import Boundaries

**Rules** (`.importlinter.yaml`):
- `src/trading/risk/` MUST NOT import any ML/AI libraries (torch, tensorflow, sklearn, etc.)
- `src/trading/strategy/` MUST NOT import from `execution/adapters/`
- `src/trading/data/` MUST NOT import from `execution/adapters/`
- `src/trading/backtest/` MUST NOT import from `execution/adapters/`
- `src/trading/execution/adapters/` MUST NOT import from strategy, risk, data, or backtest
- Violations cause CI build to FAIL

### Quickstart Guide

**Contents** (`quickstart.md`):
1. Prerequisites (Python 3.11+, pip/uv)
2. Clone and setup (`python -m venv .venv`, pip install -r requirements.txt)
3. Configure (copy `.env.example` to `.env`, fill in testnet API keys)
4. Run tests (`pytest`)
5. Run live loop (`python -m trading.loop.live --env=testnet`)
6. Run backtest (`python -m trading.backtest.runner --data=data/btcusd.parquet`)

---

## Next Steps

After this plan is reviewed and approved:
1. Run `/speckit-tasks` to generate actionable task list (`tasks.md`)
2. Run `/speckit-implement` to execute the tasks
