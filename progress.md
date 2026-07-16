# Trading System - Project Progress

**Last Updated**: 2026-07-15 (Session 3)
**Current Phase**: Sprint 2 Planning Complete ✅ | Quote-Level Data + Observed Spread Cost Model
**Status**: Task List Ready for Implementation
**Remote**: https://github.com/mhadiamiri/trading-system (Private)

---

## Executive Summary

A systematic crypto trading system built on constitutional principles. The project has completed Sprint 1 (Walking Skeleton) and successfully executed a venue swap from Bybit testnet to Kraken mainnet public feed. All safety guards have been verified with fail-then-pass proofs. **Sprint 2 planning (WO-004, WO-005) is now complete** with all artifacts generated, analyzed, and task list ready. Ready to proceed to implementation phase.

### Key Achievements
- ✅ Walking skeleton complete (36/36 tests passing)
- ✅ Venue swap executed (Bybit → Kraken)
- ✅ DATA_SOURCE/TRADING_ENV decoupled
- ✅ Import-linter enforcing boundaries (3 contracts with loop/ added)
- ✅ All four constitutional guards verified with fail-then-pass proofs
- ✅ WO-002-C and WO-002-D completed
- ✅ Code pushed to private GitHub repository
- ✅ WO-003: Sprint 2 spec complete with all clarifications resolved
- ✅ **WO-004: Implementation plan generated (plan.md, research.md, data-model.md, contracts/, quickstart.md)**
- ✅ **WO-005-A: Cross-artifact consistency analyze — CLEAN**
- ✅ **WO-005-B: Task list generated (41 tasks across 10 phases)**

---

## Project Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Trading System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐                        │
│  │  Data Layer  │─────>│   Strategy   │                        │
│  │              │      │              │                        │
│  │ • MarketState│      │ • Decide()   │                        │
│  │ • Feed       │      │ • Version    │                        │
│  │ • Adapters   │      │              │                        │
│  │  - Kraken    │      │              │                        │
│  │  - Simulated │      │              │                        │
│  └──────────────┘      └──────┬───────┘                        │
│                                 │                                │
│                                 v                                │
│                        ┌──────────────┐                        │
│                        │  Risk Layer  │                        │
│                        │              │                        │
│                        │ • Check()    │                        │
│                        │ • Limits     │                        │
│                        │ • Kill Switch│                        │
│                        └──────┬───────┘                        │
│                               │                                 │
│                               v                                 │
│                      ┌──────────────┐                        │
│                      │  Execution   │                        │
│                      │              │                        │
│                      │ • Paper      │                        │
│                      │ • Costs      │                        │
│                      │ • Fill       │                        │
│                      └──────┬───────┘                        │
│                             │                                 │
│                             v                                 │
│                      ┌──────────────┐                        │
│                      │   Logkit     │                        │
│                      │              │                        │
│                      │ • Log Every  │                        │
│                      │   Decision   │                        │
│                      │ • Reason Code│                        │
│                      └──────────────┘                        │
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐                        │
│  │  Backtest   │      │   Live Loop  │                        │
│  │              │      │              │                        │
│  │ • Runner     │      │• Orchestrator│                       │
│  │ • Cost Model │      │• End-to-End │                        │
│  └──────────────┘      └──────────────┘                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

**Language**: Python 3.13+ (3.14.6 in development)
**Package Manager**: pip with pyproject.toml
**Testing Framework**: pytest (with asyncio, coverage plugins)
**Linting/Quality**: import-linter for boundary enforcement, ruff for linting
**Data Persistence**: Parquet files (via pandas/pyarrow)
**Configuration**: python-dotenv for .env management
**Async Runtime**: asyncio
**WebSocket**: websockets library for market data feeds
**Version Control**: Git (hosted on private GitHub repository)

---

## Development Tools & Workflow

### Speckit System

This project uses the **Speckit** spec-driven development workflow — a systematic approach to building software through explicit specifications and task lists.

#### How Speckit Works

Speckit implements a full-cycle development workflow:

1. **Constitution** (`.specify/memory/constitution.md`) — Governing principles that all work must comply with
2. **Specify** (`/speckit-specify`) — Create specifications with requirements, constraints, and acceptance criteria
3. **Clarify** (`/speckit-clarify`) — Resolve ambiguities and underspecified elements
4. **Plan** (`/speckit-plan`) — Design implementation strategy considering architectural trade-offs
5. **Tasks** (`/speckit-tasks`) — Break down into concrete, actionable tasks with dependencies
6. **Implement** (`/speckit-implement`) — Execute the plan while respecting boundaries
7. **Analyze** (`/speckit-analyze`) — Review implementation for compliance and quality

#### Speckit Skills Available

| Skill | Purpose |
|-------|---------|
| `/speckit-constitution` | View constitutional principles |
| `/speckit-specify` | Create new specifications |
| `/speckit-clarify` | Resolve specification ambiguities |
| `/speckit-plan` | Design implementation strategy |
| `/speckit-tasks` | Generate task lists |
| `/speckit-implement` | Execute implementation |
| `/speckit-analyze` | Analyze implementation for compliance |
| `/speckit-checklist` | Review specification completeness |
| `/speckit-converge` | Resolve conflicts across specifications |

#### Speckit Artifacts Location

```
.specify/
├── memory/
│   └── constitution.md          # Constitutional principles
├── workflows/
│   └── speckit/workflow.yml     # Speckit workflow configuration
└── templates/                   # Spec, plan, and task templates
```

### Other Development Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| **pytest** | Test runner | `pytest` or `python -m pytest` |
| **pytest-asyncio** | Async test support | Required for async tests |
| **pytest-cov** | Coverage reporting | `pytest --cov=src/trading` |
| **import-linter** | Boundary enforcement | `import-linter lint` |
| **ruff** | Fast Python linter | `ruff check` |
| **mypy** | Static type checking | `mypy src/` |
| **websockets** | WebSocket client | For market data feeds |
| **pandas/pyarrow** | Data handling | Parquet read/write |
| **python-dotenv** | Environment config | Load .env files |

### CI/CD

- GitHub Actions workflow configured (`.github/workflows/ci.yml`)
- Runs tests and lint checks on push
- Currently configured but depends on repository settings

### Local Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest                          # All tests
pytest tests/test_risk.py      # Specific file
pytest -v                      # Verbose output
pytest --cov=src/trading      # With coverage

# Run import-linter
import-linter lint

# Run live loop (simulated feed)
python -m trading.loop.live

# Run live loop (Kraken public feed)
DATA_SOURCE=kraken_public python -m trading.loop.live

# Run backtest
python -m trading.backtest.runner
```

---

## Constitutional Principles

| # | Principle | Status | Description |
|---|-----------|--------|-------------|
| I | Truth Before Profit | ✅ PASS | All costs explicitly listed. Negative P&L acceptable. |
| II | Walking Skeleton Before Palace | ✅ PASS | End-to-end loop before sophistication. |
| III | AI Proposes, Deterministic Code Disposes | ✅ PASS | Risk layer has no ML/AI. Pure rule-based. |
| IV | Layered Architecture, Enforced Boundaries | ✅ PASS | Import-linter enforces boundaries. |
| V | No Backtest Without Costs | ✅ PASS | All trades include fees, spread, slippage. |
| VI | Risk Engine Is Sovereign | ✅ PASS | Clamp only reduces toward zero. Kill switch works. |
| VII | Venue Independence | ✅ PASS | No venue-specific types leak above adapters. |
| VIII | Total Observability & Provenance | ✅ PASS | Every decision logged with reason code. |
| IX | Secrets and Safety Rails | ✅ PASS | .env gitignored. No secrets in logs. |

---

## Current Status (2026-07-15)

### ✅ Recent Updates - Sprint 2 Spec Complete (WO-003)

**Major Work Completed (Session 2):**

1. **Sprint 2 Specification Created** ✅
   - Spec file: `specs/002-quote-level-data/spec.md`
   - Feature: Quote-Level Data + Observed-Spread Cost Model
   - Focus: Migrate from trades feed to quote-level data (Kraken v2 book channel)
   - Core requirement: Cost model uses real observed spread, not assumptions

2. **Five Clarifications Resolved** ✅
   - Q1: Checksum failure threshold → 5 consecutive failures trigger reconnection/resync
   - Q2: Abnormal spread handling → REJECT trade (overrides tool recommendation — no fallback)
   - Q3: Rolling trade window → 100 trades AND 60 seconds (whichever first), configurable
   - Q4: Sequence gap detection → Track sequence; on gap, discard book + resnapshot (no continue-on-gap)
   - Q5: Book unavailable, trades still connected → PAUSE, emit no MarketStates (overrides tool recommendation — no trades-only mode)

3. **Spec Updated with Clarifications** ✅
   - All five answers integrated into functional requirements
   - New FRs added: FR-015a (no synthetic spread), FR-018a (sequence gap detection), FR-019a (pause on no book)
   - Updated FRs: FR-009 (rolling window), FR-015 (abnormal spread), FR-018 (checksum threshold)
   - No [NEEDS CLARIFICATION] markers remain
   - All clarifications documented with rationale in spec

4. **Three Load-Bearing Items Verified** ✅
   - ✅ Cost model uses observed spread (FR-011, FR-012, FR-015a, SC-002, SC-005)
   - ✅ v2 book checksum validation on every update (FR-004, FR-016 through FR-019, SC-003, QG-003)
   - ✅ Strategy logic/interface is out of scope (FR-023 through FR-026, SC-006, QG-002)

5. **Committed and Pushed** ✅
   - Commit: `6e1c79a` - "spec(002): resolve clarifications — reject-on-anomaly, pause-on-no-book, observed-spread-only"
   - Pushed to private GitHub repository
   - Spec ready for planning phase

---

## Current Status (Session 3 - 2026-07-15)

### ✅ Recent Updates - Sprint 2 Planning Complete (WO-004, WO-005)

**Major Work Completed (Session 3):**

#### WO-004: Implementation Plan Generated ✅

**Artifacts Created:**
1. **plan.md** — Implementation plan with:
   - Technical context (Python 3.11+, dependencies, storage)
   - Constraints (no synthetic spread, v2/book detail confined to adapter)
   - Constitution Check (pre-design and post-design evaluations)
   - Project structure (all files that need changes)
   - Load-bearing items verified

2. **research.md** — 10 technical decisions:
   - Decision 1: Kraken v2 vs v1 (migrate to v2 book channel)
   - Decision 2: Local book maintenance strategy (checksum + sequence tracking)
   - Decision 3: Abnormal spread handling (REJECT trade, no fallback)
   - Decision 4: Rolling trade window (100 trades AND 60 seconds, hybrid)
   - Decision 5: Book unavailable behavior (PAUSE, no trades-only mode)
   - Decision 6: Adapter placement & boundary (all v2 detail in kraken_v2_book.py)
   - Decision 7: MarketState schema changes (quote-centric fields)
   - Decision 8: Backtest data storage (Parquet append-only, raw quotes)
   - Decision 9: Checksum/recovery testing strategy (fail-then-pass proofs)
   - Decision 10: Reason code vocabulary additions

3. **data-model.md** — 4 entities defined:
   - LocalBookState (adapter-internal)
   - MarketState (modified — quote-centric)
   - RollingTradeStats (adapter-internal)
   - QuoteUpdate (adapter-internal)

4. **contracts/data-adapter.yml** — Interface contracts:
   - MarketFeed interface (abstract base)
   - MarketState contract (validation rules, pause contract)
   - Import-linter contracts (v2/book/checksum boundary, loop isolation)
   - Factory contract
   - Testing contracts
   - Reason codes

5. **quickstart.md** — 10 validation scenarios:
   - Scenario 1: Quote processing (happy path)
   - Scenario 2: Checksum validation bites
   - Scenario 3: Recovery fires (5 failures → resync)
   - Scenario 4: Sequence gap → resnapshot
   - Scenario 5: Book unavailable → pause
   - Scenario 6: Abnormal spread → reject trade
   - Scenario 7: Observed spread only (no synthetic path)
   - Scenario 8: Backtest honesty (replay = live)
   - Scenario 9: Import boundaries enforced
   - Scenario 10: End-to-end integration

**Constitution Check:**
- Pre-design evaluation: All 9 principles PASS
- Post-design evaluation: Principles IV and VII re-verified PASS
- Adapter boundary confirmed: `src/trading/data/adapters/kraken_v2_book.py`
- Import-linter contract specified: blocks v2/book/checksum leaks above adapter

**Two Non-Negotiables Verified:**
1. ✅ No synthetic spread anywhere (Principle V)
   - FR-011 through FR-015a mandate observed-spread-only
   - Pause contract: Forbidden patterns block synthetic spread
   - Research Decision 3: REJECT trade, no fallback
   - No alternative accepted (all rejected)

2. ✅ v2/book detail confined to adapter (Principle VII)
   - All v2/book/checksum/sequence/resync detail in kraken_v2_book.py
   - Import-linter contract blocks leaks (strategy, risk, execution, backtest, loop)
   - Factory pattern preserved

---

#### WO-005-A: Cross-Artifact Consistency Analyze ✅

**Analyze Result: CLEAN**

**Traceability Matrix:**
- Spec → Research: 5 clarifications → 10 decisions (100% matched)
- Spec → Plan: All FRs → constraints enforced (100% covered)
- Spec → Data Model: All entities defined (100% complete)
- Spec → Contracts: All enforcement points specified (100% enforced)
- Quickstart → Spec: 10 scenarios → all requirements covered (100% covered)

**Constitution Alignment:**
- Principle I (Truth Before Profit): ✅ PASS — Multiple enforcement points
- Principle II (Walking Skeleton): ✅ PASS — Enhancement to existing loop
- Principle III (AI Proposes): ✅ PASS — No risk layer changes
- Principle IV (Layered Architecture): ✅ PASS — Import-linter contract specified
- Principle V (No Backtest Without Costs): ✅ PASS — Core requirement enforced
- Principle VI (Risk Sovereign): ✅ PASS — No changes to risk layer
- Principle VII (Venue Independence): ✅ PASS — Adapter module specified
- Principle VIII (Total Observability): ✅ PASS — Reason codes specified
- Principle IX (Secrets and Safety Rails): ✅ PASS — Public feed, no credentials

**Findings:**
- FINDING-001: Info — plan.md references Bybit in constitution but this sprint uses Kraken (expected, Principle VII permits single-module swap)
- FINDING-002: Info — "FR has no corresponding task" expected (tasks.md doesn't exist yet, resolves at WO-005-B)

**Load-Bearing Items Verification:**
1. ✅ Cost model uses observed spread only (multiple enforcement points)
2. ✅ v2 book checksum validation on every update (tests specified)
3. ✅ Strategy logic/interface unchanged (no changes)

**Gate Status**: ✅ CLEAN — Ready for tasks generation

---

#### WO-005-B: Task List Generated ✅

**Tasks Generated:** 41 tasks across 10 phases

**Sequencing Constraints (per instructions.md):**
| Constraint | Tasks | Status |
|-----------|-------|--------|
| Import-linter contract early (before adapter internals) | T001 (Phase 1) | ✅ HONORED |
| Checksum + fail-then-pass test same unit | T005-T008 (tests) + T009-T019 (implementation) in Phase 3 | ✅ HONORED |
| Explicit no-synthetic-spread tests | T025, T026, T027 (Phase 6) | ✅ HONORED |
| Backtest reconstructs observed spread from stored raw quotes | T032 (explicit requirement) | ✅ HONORED |
| MarketState schema change before consumers | T002 (Phase 2) before all consuming tasks | ✅ HONORED |
| No task changes Strategy interface signature | All tasks honor interface unchanged | ✅ HONORED |

**Task Breakdown by Phase:**
- Phase 1: Import-Linter Contract (T001) — Establish boundary enforcement first
- Phase 2: Schema & Interface Changes (T002-T004) — MarketState schema, factory prepared
- Phase 3: US3 Book Integrity (T005-T019) — Checksum validation + fail-then-pass tests
- Phase 4: US1 Quote Processing (T020-T021) — Quotes received, MarketState emitted
- Phase 5: US4 Trades Enrichment (T022-T024) — Rolling stats computed
- Phase 6: US2 Cost Model (T025-T029) — Observed spread only, abnormal spread reject
- Phase 7: Backtest Replay (T030-T032) — Replay from stored raw quotes
- Phase 8: Integration (T033-T036) — Loop handles pause, end-to-end works
- Phase 9: Regression (T037-T039) — All Sprint 1 tests pass, validation scenarios pass
- Phase 10: Documentation (T040-T041) — Reason codes documented, deprecated adapters marked

**Parallel Opportunities Identified:**
- T003, T004 (after T002)
- T005, T006, T007, T008 (US3 tests)
- T020, T022 (US1/US4 tests after US3)
- T025, T026, T027 (US2 tests)
- T030, T031 (backtest tests)
- T033, T034 (integration tests)
- T038, T039, T040, T041 (validation/cleanup)

**Status**: Task list complete; ready for human review before implementation

---

### Previous Status (Session 2 - WO-003 Complete)

**Major Work Completed (Session 1):**

1. **WO-002-C: Suspenders Guard Testability** ✅
   - Added `TRADING_ENV=test` as valid value (behaves exactly like paper for execution)
   - Belt guard verified unchanged (lines 78-86 still block mainnet)
   - Suspenders guard FAIL-THEN-PASS proven live
   - Test-mode-as-bypass assertion PASSES

2. **WO-002-D: Venue Leak Closure** ✅
   - Added `venue_name` property to `KrakenPublicFeed` and `SimulatedMarketFeed`
   - Added `get_venue_name()` function to factory.py
   - `loop/live.py` now uses `get_venue_name()` (no hardcoded strings)
   - Import-linter FAIL-THEN-PASS proven for loop/ contract

3. **Four Fail-Then-Pass Proven** ✅
   - Suspenders guard FAIL→PASS
   - Belt guard verified untouched
   - Loop/ import-linter FAIL→PASS
   - Test-mode-as-bypass PASSES

4. **GitHub Remote Setup** ✅
   - Repository pushed to private GitHub: https://github.com/mhadiamiri/trading-system
   - Security verification: No secrets in git history
   - Branch `master` tracking `origin/master`

---

### Implementation Status

**Phase 0: Guardrails & Scaffolding** ✅ COMPLETE
- Repository structure, import-linter, CI workflow

**Phase 1: P1 - End-to-End Live Paper Trading** ✅ COMPLETE
- Data models, strategy, risk, execution, logging
- Kraken public feed adapter
- Live loop orchestrator
- Risk engine tests (10 tests)
- Integration tests (5 tests)
- Import boundary tests (6 tests)

**Phase 2: P2 - Historical Backtest** ✅ COMPLETE
- Backtest runner with cost model
- Cost verification tests (9 tests)
- Backtest integration tests (6 tests)

**Phase 3: Polish & Documentation** ✅ COMPLETE
- README.md, REPORT.md, progress.md
- Decision records in docs/decisions/

**Sprint 2: Quote-Level Data + Observed Spread** 🔄 READY FOR IMPLEMENTATION
- ✅ Specification complete (WO-003)
- ✅ All clarifications resolved
- ✅ Implementation plan generated (WO-004)
- ✅ Cross-artifact analyze — CLEAN (WO-005-A)
- ✅ Task list generated (WO-005-B)
- ⏳ Implementation pending (41 tasks across 10 phases)
- ⏳ Testing pending

---

### Test Coverage

| Category | Tests | Status | File |
|----------|-------|--------|------|
| Risk Engine | 10 | ✅ PASS | `tests/test_risk.py` |
| Import Boundaries | 6 | ✅ PASS | `tests/test_boundaries.py` |
| Live Loop Integration | 5 | ✅ PASS | `tests/integration/test_live_loop.py` |
| Cost Model | 9 | ✅ PASS | `tests/test_backtest_costs.py` |
| Backtest Integration | 6 | ✅ PASS | `tests/integration/test_backtest.py` |
| **TOTAL (Sprint 1)** | **36** | ✅ **PASS** | |
| **Sprint 2 Tests** | **0** | ⏳ **PENDING** | |

**Success Criteria**: All 10 success criteria met (SC-001 through SC-010) for Sprint 1

---

### Import-Linter Status

```
Contracts: 3 kept, 0 broken

✅ Forbidden ML in Risk Layer
   - Risk cannot import: torch, tensorflow, sklearn, transformers

✅ Forbidden Execution Adapters Imports
   - Strategy, risk, data, backtest, loop cannot import trading.execution.adapters
```

---

### Git History

```
6e1c79a spec(002): resolve clarifications — reject-on-anomaly, pause-on-no-book, observed-spread-only
295e0a1 docs: Update instructions.md with post-completion security guidance
a427003 docs: Update REPORT.md and record Kraken data channel open question
efb5935 WO-002-C/D: Suspenders guard testability + venue leak closure
```

---

## File Structure

### Source Files
```
src/trading/
├── data/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── kraken_public.py         # Kraken mainnet public feed
│   │   └── simulated_feed.py        # Simulated market data
│   ├── fixtures.py                  # Test data
│   ├── market_state.py
│   ├── desired_position.py
│   └── persistence.py
├── strategy/
│   ├── interface.py
│   └── trivial.py                   # Trivial momentum strategy
├── risk/
│   ├── interface.py
│   ├── engine.py                    # Deterministic risk engine
│   ├── limits.py
│   └── position_state.py
├── execution/
│   ├── interface.py
│   ├── paper.py                     # Paper execution only
│   ├── approved_order.py
│   ├── fill.py
│   └── adapters/
│       └── __init__.py              # No execution adapters (paper only)
├── backtest/
│   ├── runner.py                    # Backtest orchestrator
│   ├── costs.py                     # Cost model (fees, spread, slippage)
│   └── report.py                    # P&L report generation
├── logkit/
│   ├── decision.py
│   └── provenance.py
└── loop/
    └── live.py                      # Live trading loop
```

### Specs (Speckit)
```
specs/
├── 001-walking-skeleton/           # Sprint 1 spec (complete)
│   ├── spec.md
│   ├── plan.md
│   ├── tasks.md
│   └── checklists/
│       └── requirements.md
└── 002-quote-level-data/           # Sprint 2 spec (planning complete)
    ├── spec.md                      # ✅ Complete with clarifications
    ├── plan.md                      # ✅ Implementation plan (WO-004)
    ├── research.md                  # ✅ 10 technical decisions
    ├── data-model.md                 # ✅ 4 entities defined
    ├── quickstart.md                # ✅ 10 validation scenarios
    ├── contracts/                   # ✅ Interface contracts
    │   └── data-adapter.yml         # MarketFeed, MarketState, import-linter
    ├── analyze-report.md            # ✅ Cross-artifact consistency (WO-005-A)
    ├── tasks.md                     # ✅ 41 tasks across 10 phases (WO-005-B)
    └── checklists/
        └── requirements.md
```

### Configuration Files
```
.importlinter.yaml                   # Import boundary contracts
.env                                 # Local environment (gitignored)
.env.example                        # Environment template
pyproject.toml                       # Project configuration
pytest.ini                           # Test configuration
```

### Documentation Files
```
README.md                            # Quickstart guide
REPORT.md                            # Session report with decisions
progress.md                          # This file
instructions.md                      # Session-specific instructions
docs/decisions/                      # Decision records
```

---

## Configuration Guide

### Environment Variables

| Variable | Options | Default | Purpose |
|----------|---------|---------|---------|
| `DATA_SOURCE` | `simulated`, `kraken_public` | `simulated` | Market data feed selection |
| `TRADING_ENV` | `paper`, `mainnet`, `test` | `paper` | Execution environment gating |

### Example .env File
```bash
# Data Source Configuration
DATA_SOURCE=simulated

# Trading Environment Configuration
TRADING_ENV=paper
```

### Running on Kraken Public Feed
```bash
# Option 1: Set in .env
DATA_SOURCE=kraken_public

# Option 2: Override via command line
DATA_SOURCE=kraken_public python -m trading.loop.live

# Option 3: Set environment variable
export DATA_SOURCE=kraken_public
python -m trading.loop.live
```

---

## Known Gaps & Future Work

### Open Questions (Deferred to Sprint 2)

**Kraken Data Channel Question** — `docs/decisions/2026-07-14-kraken-data-channel-question.md`
- Current: Trade channel (~14 events/min)
- Status: ✅ **RESOLVED in Sprint 2 spec** — migrating to book channel as primary source
- Sprint 2 addresses: Quote-level data with book channel as primary, trades as secondary enrichment

### Sprint 2 Scope (Ready for Planning)

**Feature**: Quote-Level Data + Observed-Spread Cost Model
- Migrate to Kraken WebSocket v2 book channel (top-of-book: best bid/ask)
- Implement checksum validation on every update
- Cost model uses actual observed spread (no assumptions)
- MarketState becomes quote-centric
- Trades channel as secondary enrichment only
- Out of scope: Strategy logic changes

**Key Requirements**:
- FR-001 through FR-026 defined in `specs/002-quote-level-data/spec.md`
- All clarifications resolved with behavioral requirements
- Three load-bearing items verified intact
- Ready for `/speckit-plan` phase

### Technical Debt
- Deprecated `datetime.utcnow()` warnings (707 total) - migrate to `datetime.now(datetime.UTC)`
- No file persistence for decision logs (currently stdout only)
- No rate limiting stress testing (need longer live runs)

### Future Enhancements
- Additional data sources (Coinbase, other mainnet feeds)
- Real-money execution adapters (for Sprint 3)
- More sophisticated strategies
- Portfolio management features
- Advanced backtest analytics

---

## Session History

### 2026-07-15 (Session 3): Sprint 2 Planning Complete
- **WO-004**: Implementation plan generated for Sprint 2
- Generated plan.md with technical context and constraints
- Generated research.md with 10 technical decisions
- Generated data-model.md with 4 entities defined
- Generated contracts/data-adapter.yml with interface contracts
- Generated quickstart.md with 10 validation scenarios
- Constitution check: All 9 principles PASS
- Two non-negotiables verified (no synthetic spread, adapter boundary)
- Pre-approval verification: 3 checks completed
- **WO-005-A**: Cross-artifact consistency analyze — CLEAN
  - Traceability matrix: 100% coverage across all artifacts
  - Constitution alignment: All 9 principles PASS
  - 2 informational findings (non-blocking)
  - Load-bearing items: All 3 verified
- **WO-005-B**: Task list generated — 41 tasks across 10 phases
  - Sequencing constraints: All 6 honored
  - Import-linter contract task is early (T001)
  - Checksum + fail-then-pass test same unit (Phase 3)
  - Explicit no-synthetic-spread tests (Phase 6)
  - Backtest replay reconstructs observed spread from stored raw quotes
  - MarketState schema change before consumers
  - No task changes Strategy interface signature
- Status: Task list ready for human review before implementation

### 2026-07-15 (Session 2): Sprint 2 Spec Complete
- **WO-003**: Sprint 2 specification created for quote-level data
- Generated spec with all required sections
- Created five clarification questions
- All clarifications resolved with behavioral requirements
- Two answers (Q2, Q5) override tool recommendations — no "keep trading through bad data" escape hatches
- Spec updated with new functional requirements (FR-015a, FR-018a, FR-019a)
- Three load-bearing items verified intact
- Committed and pushed to GitHub: `6e1c79a`
- Ready for `/speckit-plan` phase

### 2026-07-15 (Session 1): Walking Skeleton Complete
- Implemented all Phase 1-3 tasks
- 35 tests passing
- Import-linter configured and verified
- Live loop tested on simulated feed

### 2026-07-12: Initial Venue Swap
- Decision: Retire Bybit, adopt Kraken mainnet public feed
- Created: KrakenPublicFeed adapter
- Deleted: Bybit testnet adapter and credentials
- Updated: Configuration split (DATA_SOURCE/TRADING_ENV)
- Tested: 10-minute live loop on Kraken (102 events)
- Verified: All 36 tests pass, import-linter green

### 2026-07-14: WO-002 Completion
- **WO-002-C**: Suspenders guard testability (TRADING_ENV=test added, fail-then-pass proven)
- **WO-002-D**: Venue leak closure (get_venue_name from factory, loop/ import-linter contract)
- All four guards verified with fail-then-pass proofs
- Kraken data channel question recorded in docs/decisions/

### 2026-07-15: GitHub Remote Setup
- Security verification: No secrets in git history
- Remote added: https://github.com/mhadiamiri/trading-system (Private)
- Code pushed to GitHub
- Branch master tracking origin/master

---

## Commands Reference

### Development Workflow
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest                          # Quick run
pytest -v                      # Verbose
pytest --cov=src/trading      # With coverage
pytest tests/test_risk.py     # Specific test file

# Run import-linter
import-linter lint

# Speckit workflow
/speckit-constitution         # View principles
/speckit-specify             # Create specification
/speckit-clarify             # Resolve ambiguities
/speckit-plan                # Design implementation
/speckit-tasks               # Generate tasks
/speckit-implement           # Execute implementation
/speckit-analyze             # Analyze compliance
```

### Running the System
```bash
# Live loop (simulated feed)
python -m trading.loop.live

# Live loop (Kraken public feed)
DATA_SOURCE=kraken_public python -m trading.loop.live

# Backtest on captured data
python -m trading.backtest.runner
```

### Verification Commands
```bash
# Verify tests pass
pytest

# Verify import boundaries
import-linter lint

# Verify no ML in risk layer
pytest tests/test_risk.py -k "import"

# Verify cost model
pytest tests/test_backtest_costs.py

# Verify end-to-end loop
pytest tests/integration/test_live_loop.py
```

### Git Workflow
```bash
# Check status
git status

# Pull latest changes
git pull origin master

# Push changes
git push origin master

# View commit history
git log --oneline -10
```

---

## Safety Reminders

### Critical Safety Rules
- ⚠️ **NEVER** commit real API keys to git
- ⚠️ **NEVER** run with `TRADING_ENV=mainnet` in development
- ⚠️ **ALWAYS** verify import-linter passes before committing
- ⚠️ **VERIFY** tests pass before committing
- ⚠️ **ENSURE** `DATA_SOURCE` and `TRADING_ENV` are set appropriately

### Invariant to Maintain
**No code path that can place a real order is reachable while `TRADING_ENV=paper`, regardless of `DATA_SOURCE` setting.**

This invariant is enforced through:
1. Configuration validation in `settings.py` (belt guard)
2. Paper-only execution in `execution/paper.py` (suspenders guard)
3. Import-linter blocking execution adapters
4. Test coverage verifying the invariant

---

## Next Steps

### Immediate Actions (Next Session)

1. **Review Sprint 2 task list** (`specs/002-quote-level-data/tasks.md`)
   - 41 tasks across 10 phases
   - Sequencing constraints honored
   - Ready for implementation after approval

2. **Review Sprint 2 artifacts** (if needed)
   - `specs/002-quote-level-data/spec.md` — Requirements (WO-003 complete)
   - `specs/002-quote-level-data/plan.md` — Implementation plan (WO-004 complete)
   - `specs/002-quote-level-data/research.md` — 10 technical decisions
   - `specs/002-quote-level-data/data-model.md` — 4 entities defined
   - `specs/002-quote-level-data/contracts/data-adapter.yml` — Interface contracts
   - `specs/002-quote-level-data/quickstart.md` — 10 validation scenarios
   - `specs/002-quote-level-data/analyze-report.md` — Cross-artifact consistency (WO-005-A CLEAN)
   - `specs/002-quote-level-data/tasks.md` — Task list (WO-005-B complete)

3. **Implementation Phase** (after task list approval)
   - Begin with T001: Update .importlinter.yaml with v2/book/checksum boundary contract
   - Follow task sequencing: Phase 1 → Phase 2 → Phase 3 → ... → Phase 10
   - Write tests first (fail-then-pass pattern)
   - Verify each task completes before proceeding
   - Run pytest after each phase
   - Run import-linter lint after boundary changes

### For Next Session
1. Review this document for current status
2. Read `specs/002-quote-level-data/tasks.md` for task breakdown
3. Run `pytest` to verify Sprint 1 tests still pass
4. Check `.env` configuration matches intended use
5. Pull latest from GitHub: `git pull origin master`
6. Begin implementation with T001 when ready

---

**Project Status**: 🟢 **SPRINT 2 PLANNING COMPLETE** - Task list ready for implementation. All artifacts generated, cross-artifact consistency verified CLEAN, 41 tasks across 10 phases with sequencing constraints honored.

**Last Session Outcome**:
- WO-004: Implementation plan generated (plan.md, research.md, data-model.md, contracts/, quickstart.md)
- WO-005-A: Cross-artifact consistency analyze — CLEAN (all 9 constitutional principles PASS)
- WO-005-B: Task list generated (41 tasks across 10 phases, 6 sequencing constraints honored)

**Next Phase**: Begin implementation with T001 (import-linter contract update) after human review of task list.

---

## Artifacts Summary (Session 3)

### WO-004: Implementation Plan Generated
| Artifact | Purpose | Status |
|----------|---------|--------|
| `plan.md` | Technical context, constraints, constitution check, project structure | ✅ COMPLETE |
| `research.md` | 10 technical decisions with rationale and alternatives | ✅ COMPLETE |
| `data-model.md` | 4 entities defined (LocalBookState, MarketState, RollingTradeStats, QuoteUpdate) | ✅ COMPLETE |
| `contracts/data-adapter.yml` | Interface contracts, import-linter rules, testing contracts | ✅ COMPLETE |
| `quickstart.md` | 10 validation scenarios with expected outcomes | ✅ COMPLETE |

### WO-005-A: Cross-Artifact Consistency Analyze
| Check | Result | Details |
|-------|--------|---------|
| Spec → Research traceability | ✅ 100% | 5 clarifications → 10 decisions |
| Spec → Plan traceability | ✅ 100% | All FRs → constraints enforced |
| Spec → Data Model traceability | ✅ 100% | All entities defined |
| Spec → Contracts traceability | ✅ 100% | All enforcement points specified |
| Quickstart → Spec traceability | ✅ 100% | 10 scenarios → all requirements |
| Constitution alignment | ✅ 100% | All 9 principles PASS |
| Load-bearing items | ✅ 3/3 | All verified |

### WO-005-B: Task List Generated
| Metric | Value |
|-------|-------|
| Total tasks | 41 |
| Phases | 10 |
| Sequencing constraints | 6 honored |
| Parallel opportunities | Multiple identified |
| Critical path phases | Phase 1 → Phase 2 → Phase 3 → Phase 6 → Phase 7 → Phase 8 → Phase 9 |
