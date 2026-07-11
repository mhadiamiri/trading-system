# Implementation Tasks: Walking Skeleton - Systematic Crypto Trading System

**Feature**: 001-walking-skeleton
**Branch**: `001-walking-skeleton`
**Date**: 2026-07-11
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## Task Overview

This document defines the implementation tasks for the walking skeleton feature. Tasks are organized by phase and dependency order.

**Sequencing Constraints**:
- Guardrails (import-linter, .gitignore, .env.example) must be established before any code
- P1 (live end-to-end paper loop) must complete before P2 (backtest) begins
- Each user story must be independently testable

---

## Phase 0: Guardrails & Scaffolding

**Goal**: Establish project structure with constitutional guardrails before any code exists.

### Task 001: Initialize repository with guardrails [BLOCKING] [X]

**Description**: Create project structure, guardrails, and configuration files.

**File Changes**:
- Create `src/trading/` package structure (data, strategy, risk, execution, backtest, logkit, loop subdirectories)
- Create `config/` directory
- Create `tests/` directory structure
- Create `.importlinter.yaml` with four-layer boundary rules
- Create `pyproject.toml` with Python 3.11+ dependency
- Create `requirements.txt` with core dependencies (pytest, pyarrow, pydantic, httpx, python-dotenv, pyyaml)
- Create `requirements-dev.txt` with dev dependencies (pytest-cov, pytest-asyncio, import-linter, ruff, mypy)
- Create `.gitignore` with entries for `.env`, `data/`, `logs/`, `__pycache__/`, `.venv/`, `*.pyc`
- Create `.env.example` with variable names only (BYBIT_API_KEY=, BYBIT_API_SECRET=, TRADING_ENV=testnet)
- Create `pytest.ini` with test configuration
- Create `.github/workflows/ci.yml` with import-linter + pytest in test command

**Import-Linter Configuration** (`.importlinter.yaml`):
```yaml
unimported:
  - trading.risk
  - trading.strategy
  - trading.data

forbidden_modules:
  - torch
  - tensorflow
  - sklearn
  - transformers
importers:
  - trading.risk
action: error

contract_layers:
  - layer: trading.execution.adapters
    importers:
      - trading.strategy
      - trading.risk
      - trading.data
      - trading.backtest
    action: forbid
```

**Acceptance Criteria**:
- All directories created with `__init__.py` files
- Import-linter configuration enforces: risk layer cannot import ML/AI libraries
- Import-linter configuration enforces: execution adapters cannot be imported by strategy/risk/data/backtest
- `.gitignore` prevents commits of `.env`, `data/`, `logs/`
- `.env.example` contains no values, only variable names
- CI workflow runs `import-linter && pytest` (build fails on violation)

**Test**: Run `import-linter` from project root — should succeed with empty modules.

**Rationale**: Guardrails must fail the build from day one, while modules are still near-empty (Constitutional requirement IV: Layered Architecture, Enforced Boundaries).

---

## Phase 1: P1 - End-to-End Live Paper Trading

**Goal**: Build the walking skeleton — complete loop from market data to simulated execution to logged results.

**User Story**: A trader runs the system in live paper trading mode connected to a testnet market data feed. The system receives real-time market updates, evaluates a trivial strategy signal, passes decisions through risk checks, executes simulated trades, and logs every decision with reason codes.

**Independent Test**: Run the system in live paper trading mode for 5 minutes and observe: (1) market data being received, (2) every decision being logged with a reason code (including "no signal"), (3) simulated fills being recorded, and (4) a P&L report showing cost-inclusive results.

---

### Task 101: Implement data model entities [P1] [X]

**Description**: Create core data model entities as defined in `data-model.md`.

**File Changes**:
- Create `src/trading/data/market_state.py` with `MarketState` dataclass (including `compute_snapshot_hash()` method)
- Create `src/trading/strategy/desired_position.py` with `DesiredPosition` dataclass (no confidence field, includes `feature_snapshot_hash`)
- Create `src/trading/execution/approved_order.py` with `ApprovedOrder` dataclass
- Create `src/trading/execution/fill.py` with `Fill` dataclass (all cost components: spread_cost, slippage_cost, fees, total_cost, cad_value)
- Create `src/trading/risk/position_state.py` with `PositionState` dataclass

**Acceptance Criteria**:
- All entities have frozen dataclasses with appropriate field types
- `MarketState.compute_snapshot_hash()` returns SHA256 hash
- `DesiredPosition` has no `confidence` field (Constitutional requirement III)
- `Fill` includes all cost components and `cad_value`

**Dependencies**: Task 001

---

### Task 102: Implement Strategy interface and trivial strategy [P1] [X]

**Description**: Create Strategy interface and implement trivial momentum/volume strategy.

**File Changes**:
- Create `src/trading/strategy/interface.py` with `Strategy` abstract base class (including `version` property and `decide()` method)
- Create `src/trading/strategy/trivial.py` with `TrivialMomentumStrategy` implementation
- Implement `decide()` method that returns `DesiredPosition` when price change > 1% or volume > 2x average, else None
- Include `feature_snapshot_hash` from `market_state.compute_snapshot_hash()`

**Acceptance Criteria**:
- `Strategy.version` property returns version string
- `decide()` returns `DesiredPosition` with `feature_snapshot_hash` populated
- Strategy is deterministic (same input → same output)
- No confidence field in `DesiredPosition`

**Dependencies**: Task 101

---

### Task 103: Implement RiskEngine interface and engine [P1] [X]

**Description**: Create RiskEngine interface and implement pure deterministic risk engine.

**File Changes**:
- Create `src/trading/risk/interface.py` with `RiskEngine` abstract base class
- Create `src/trading/risk/engine.py` with `DeterministicRiskEngine` implementation
- Implement `check()` method that returns (PASS/CLAMP/VETO, ApprovedOrder/None, reason_code)
- Implement `get_kill_switch_state()`, `set_kill_switch()` methods
- Implement `get_max_position_size()`, `get_max_daily_loss_pct()` methods
- Create `src/trading/risk/limits.py` with configurable limit values

**Acceptance Criteria**:
- `check()` is pure (no I/O, network, randomness, or clock reads in logic)
- CLAMP only reduces size toward zero, never flips side (Constitutional requirement VI)
- Returns `RiskDecision.PASS`, `CLAMP`, or `VETO` with reason codes
- Max position size enforced (configurable, default 1 BTC)
- Max daily loss enforced (configurable as % of equity, default 5%)
- Kill switch blocks new orders, permits cancellations

**Dependencies**: Task 101

---

### Task 104: Implement ExchangeClient interface and paper execution [P1] [X]

**Description**: Create ExchangeClient interface and implement simulated (paper) execution.

**File Changes**:
- Create `src/trading/execution/interface.py` with `ExchangeClient` abstract base class
- Create `src/trading/execution/paper.py` with `PaperExecutionClient` implementation
- Implement `place_order(order, kill_switch_engaged)` that raises `KillSwitchEngagedError` when engaged
- Implement `cancel_order(order_id, kill_switch_engaged)` that succeeds even when kill switch engaged
- Implement `get_market_data()` as placeholder (to be implemented in Task 106)
- Create `KillSwitchEngagedError` exception with `EXEC_BLOCKED_KILL_SWITCH` reason code

**Acceptance Criteria**:
- `place_order()` raises `KillSwitchEngagedError` when `kill_switch_engaged=True`
- `cancel_order()` succeeds regardless of kill switch state (Constitutional requirement VI)
- `Fill` includes all cost components (fees, spread, slippage, total_cost, cad_value)
- Fees default to 0.1% taker per side (configurable)
- No real-money orders (simulated only)

**Dependencies**: Task 101

---

### Task 105: Implement decision logging (logkit) [P1] [X]

**Description**: Create decision logging module that records every decision with reason codes.

**File Changes**:
- Create `src/trading/logkit/decision.py` with `DecisionLogger` class
- Create `src/trading/logkit/provenance.py` with `strategy_version` and `feature_snapshot_hash` helpers
- Implement logging to both console and file (`logs/decisions.log`)
- Ensure no secrets or credentials appear in logs (Constitutional requirement IX)

**Acceptance Criteria**:
- Every decision ("no signal", "clamped", "rejected", "executed") is logged with reason code
- Zero silent decisions (Constitutional requirement VIII)
- Log includes: timestamp, layer, event_type, reason_code, venue, symbol, side, size, prices, fees
- No secrets or credentials in any log line

**Dependencies**: Task 101

---

### Task 106: Implement Bybit testnet market data feed adapter [P1] [X]

**Description**: Create Bybit testnet adapter for market data WebSocket feed.

**File Changes**:
- Create `src/trading/data/adapters/bybit_testnet.py` with `BybitTestnetFeed` class
- Implement WebSocket connection to `wss://stream-testnet.bybit.com/v5/public/linear`
- Subscribe to BTC/USD ticker updates
- Parse messages into `MarketState` objects
- Handle disconnections gracefully (log, pause, resume on reconnect)

**Acceptance Criteria**:
- Connects to Bybit testnet WebSocket
- Parses market data into `MarketState` objects
- Handles disconnections with graceful degradation
- No venue-specific types leak above adapter (Constitutional requirement VII)

**Dependencies**: Task 101

---

### Task 107: Implement live trading loop orchestrator [P1] [X]

**Description**: Create live trading loop that orchestrates all components end-to-end.

**File Changes**:
- Create `src/trading/loop/live.py` with `LiveTradingLoop` class
- Implement main loop: market data → strategy → risk → execution → logging
- Wire together: BybitTestnetFeed → TrivialMomentumStrategy → DeterministicRiskEngine → PaperExecutionClient → DecisionLogger
- Handle graceful shutdown on keyboard interrupt

**Acceptance Criteria**:
- End-to-end loop completes: data in → strategy → risk → execution → logged result → report
- 100 consecutive market data updates processed without error
- Every decision produces a log entry with reason code
- Simulated fills recorded with all cost components

**Dependencies**: Tasks 102, 103, 104, 105, 106

---

### Task 108: Implement P&L report generation [P1] [X]

**Description**: Create P&L report that shows cost-inclusive results.

**File Changes**:
- Create `src/trading/backtest/report.py` with `PnLReport` class
- Implement report generation with: total trades, gross P&L, cost breakdown (fees, spread, slippage), net P&L
- Ensure all costs listed as separate line items (no hidden costs)

**Acceptance Criteria**:
- P&L report shows net profit/loss after all costs
- Cost breakdown explicitly lists: fees, spread, slippage (Constitutional requirement I)
- Trade-by-trade list included
- Negative P&L is acceptable outcome (Constitutional requirement I)

**Dependencies**: Task 104

---

### Task 109: Implement risk engine tests [P1] [CRITICAL] [X]

**Description**: Create comprehensive risk engine tests including clamp and kill switch scenarios.

**File Changes**:
- Create `tests/test_risk.py` with risk engine test suite
- Test: Clamp fires when position limit exceeded (SC-010)
- Test: Veto fires when daily loss exceeded
- Test: Kill switch engaged → place_order refused AND cancel_order still succeeds
- Test: No ML/AI imports in risk layer (Constitutional requirement III)
- Test: Clamp only reduces size, never flips side (Constitutional requirement VI)

**Acceptance Criteria**:
- Clamp test uses small enough limit that clamp actually fires (SC-010)
- Kill switch test verifies: `place_order()` raises `KillSwitchEngagedError`, `cancel_order()` succeeds
- Import test verifies no `torch`, `tensorflow`, `sklearn` imports in risk layer
- All tests pass

**Dependencies**: Tasks 103, 104

**Parallel**: [P] with Tasks 110-111

---

### Task 110: Implement live loop integration test [P1]

**Description**: Create end-to-end integration test for live paper trading loop.

**File Changes**:
- Create `tests/integration/test_live_loop.py` with integration test
- Test: 100 consecutive market data updates without error
- Test: Every decision produces a log entry with reason code (SC-002)
- Test: Simulated fills recorded with all cost components
- Test: P&L report generated with cost breakdown

**Acceptance Criteria**:
- Integration test runs live loop for 5 minutes (or simulated equivalent)
- Verifies: market data received, decisions logged, fills recorded, P&L report generated
- All SC-001 through SC-008 criteria verified

**Dependencies**: Tasks 102, 103, 104, 105, 106, 107, 108

**Parallel**: [P] with Task 109

---

### Task 111: Implement import boundary tests [P1]

**Description**: Create tests that verify import boundary rules are enforced.

**File Changes**:
- Create `tests/test_boundaries.py` with boundary test suite
- Test: Risk layer cannot import ML/AI libraries
- Test: Strategy cannot import execution adapters
- Test: Data cannot import execution adapters
- Test: Backtest cannot import execution adapters

**Acceptance Criteria**:
- All boundary violations detected
- Tests can be run with `pytest`
- CI configuration runs these tests

**Dependencies**: Task 001

**Parallel**: [P] with Task 109

---

## Phase 2: P2 - Historical Backtest

**Goal**: Build backtest capability that runs the same logic over stored data with cost-inclusive reporting.

**User Story**: A trader runs the same strategy-to-risk-to-execution logic over previously stored market data to evaluate historical performance. The system applies realistic trading costs to every simulated trade and produces a cost-inclusive P&L result.

**Independent Test**: Run backtest on stored dataset and verify: (1) all data points processed in sequence, (2) each simulated trade has fees/spread/slippage applied, (3) final P&L matches manual calculation.

**Dependencies**: Phase 1 (P1) must complete first.

---

### Task 201: Implement backtest runner [P2]

**Description**: Create backtest runner that processes stored market data.

**File Changes**:
- Create `src/trading/backtest/runner.py` with `BacktestRunner` class
- Implement: Load Parquet file with market data, process chronologically, apply strategy/risk/execution logic
- Report: Data window (start/end timestamps, number of events), cost breakdown, P&L (FR-022)

**Acceptance Criteria**:
- Loads and processes market data from Parquet file
- No minimum data requirement (runs on whatever exists)
- Reports data window: start timestamp, end timestamp, number of events/trades
- Completes in under 60 seconds for 1000 data points (SC-003)

**Dependencies**: Tasks 102, 103, 104, 108

---

### Task 202: Implement cost model (fees, spread, slippage) [P2]

**Description**: Create cost model that applies fees, spread, and slippage to every trade.

**File Changes**:
- Create `src/trading/backtest/costs.py` with `CostModel` class
- Implement: Fee calculation (0.1% taker per side, configurable)
- Implement: Spread cost calculation (buy at ask, sell at bid)
- Implement: Slippage model (linear function of order size vs liquidity)

**Acceptance Criteria**:
- Fees applied to every simulated trade (Constitutional requirement V)
- Spread applied on both entry and exit
- Slippage reduces fill prices
- No cost-free code path exists
- Taker fees (not maker) for momentum strategy crossing spread

**Dependencies**: Task 104

---

### Task 203: Implement backtest cost verification tests [P2] [CRITICAL]

**Description**: Create tests that verify backtest cost model is honest and complete.

**File Changes**:
- Create `tests/test_backtest_costs.py` with cost verification test suite
- Test: Fees applied to every trade (SC-008: manual calculation matches within 0.01%)
- Test: Spread applied on entry and exit
- Test: Slippage reduces fill prices
- Test: P&L report shows cost breakdown (SC-004)

**Acceptance Criteria**:
- Manual calculation of 5 sample trades matches system's reported costs within 0.01%
- All cost components verified in tests
- P&L report explicitly lists all costs

**Dependencies**: Tasks 108, 201, 202

---

### Task 204: Implement backtest integration test [P2]

**Description**: Create end-to-end integration test for backtest.

**File Changes**:
- Create `tests/integration/test_backtest.py` with backtest integration test
- Test: 1000 data points complete in under 60 seconds
- Test: Determinism verified (same input → bit-for-bit identical output)
- Test: Data window reported in results

**Acceptance Criteria**:
- Backtest runs on stored data and produces cost-inclusive P&L
- Determinism verified (SC-005)
- Data window included in report (FR-022)

**Dependencies**: Tasks 201, 202

---

## Phase 3: Polish & Documentation

**Goal**: Final polish, documentation, and verification.

---

### Task 301: Create quickstart documentation [P3]

**Description**: Create developer quickstart guide as defined in `quickstart.md`.

**File Changes**:
- Create `README.md` with project overview
- Document setup steps (clone, venv, install)
- Document configuration (.env setup)
- Document test execution
- Document live loop execution
- Document backtest execution

**Acceptance Criteria**:
- Quickstart guide matches `quickstart.md` structure
- All steps verified to work
- Safety warnings included (TRADING_ENV defaults to testnet)

**Dependencies**: All Phase 1 and Phase 2 tasks

---

### Task 302: Verify constitutional compliance [P3]

**Description**: Final verification that all constitutional principles are satisfied.

**File Changes**:
- Review all code against constitution
- Verify no ML/AI in risk layer (Principle III)
- Verify import boundaries enforced (Principle IV)
- Verify cost-inclusive reporting (Principle I)
- Verify kill switch semantics (Principle VI)
- Verify no secrets in logs (Principle IX)

**Acceptance Criteria**:
- All 9 constitutional principles verified
- No violations found
- Document verification results

**Dependencies**: All Phase 1 and Phase 2 tasks

---

## Dependencies Summary

**Phase Sequencing**:
- Phase 0 (Guardrails) must complete first
- Phase 1 (P1) must complete before Phase 2 (P2) begins
- Phase 3 (Polish) depends on Phase 1 and Phase 2

**Task Dependencies**:
- Task 001 → All tasks (scaffolding)
- Task 101 → Tasks 102, 103, 104, 105, 106 (data model)
- Tasks 102, 103, 104, 105 → Task 107 (wiring)
- Task 103, 104 → Task 109 (risk tests)
- Task 108 → Task 110 (P&L report needed for integration test)
- Phase 1 complete → Phase 2 (P1 before P2)

**Parallel Execution Opportunities**:
- Tasks 109, 110, 111 can run in parallel [P] once dependencies are met
- Tasks 201, 202 can run in parallel once Phase 1 completes

---

## Implementation Strategy

**MVP First Approach**:
1. Establish guardrails (Task 001)
2. Build data model (Task 101)
3. Build P1 walking skeleton end-to-end (Tasks 102-108)
4. Verify P1 with tests (Tasks 109-111)
5. Build P2 backtest (Tasks 201-202)
6. Verify P2 with tests (Tasks 203-204)
7. Polish and verify (Tasks 301-302)

**Incremental Delivery**:
- After Phase 1: Functional live paper trading loop
- After Phase 2: Functional backtest with cost-inclusive reporting
- After Phase 3: Production-ready walking skeleton

---

## Total Tasks

**Phase 0**: 1 task (guardrails)
**Phase 1**: 11 tasks (P1 live loop)
**Phase 2**: 4 tasks (P2 backtest)
**Phase 3**: 2 tasks (polish)

**Total**: 18 tasks

---

## Critical Success Factors

1. **Guardrails First** (Task 001): Import-linter must fail build from day one
2. **P1 Before P2**: Walking skeleton must work before backtest is built
3. **Clamp Test** (Task 109): Must actually fire clamp to verify behavior
4. **Kill Switch Test** (Task 109): Must verify place_order refused, cancel_order succeeds
5. **Cost Verification** (Task 203): Manual calculation must match within 0.01%
