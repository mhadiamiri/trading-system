# Trading System - Walking Skeleton

**Feature**: 001-walking-skeleton
**Status**: Complete
**Date**: 2026-07-11

A systematic crypto trading system walking skeleton - the simplest thing that runs end-to-end.

## Overview

This is the walking skeleton of a systematic crypto trading system. It demonstrates the complete data-flow loop from market data ingestion through strategy decisions, risk checks, simulated execution, and cost-inclusive P&L reporting.

**Key Principles**:
- **Truth Before Profit**: All costs are explicitly listed and reported
- **Walking Skeleton Before Palace**: End-to-end loop before sophistication
- **AI Proposes, Deterministic Code Disposes**: Risk engine is pure, rule-based, no ML/AI

## Constitutional Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Truth Before Profit | ✅ PASS | Cost-inclusive P&L reporting, negative P&L acceptable |
| II. Walking Skeleton Before Palace | ✅ PASS | End-to-end loop completes successfully |
| III. AI Proposes, Deterministic Code Disposes | ✅ PASS | Risk layer has no ML/AI imports |
| IV. Layered Architecture, Enforced Boundaries | ✅ PASS | Import-linter enforces boundaries |
| V. No Backtest Without Costs | ✅ PASS | All trades include fees, spread, slippage |
| VI. Risk Engine Is Sovereign | ✅ PASS | Clamp only reduces toward zero, kill switch works |
| VII. Venue Independence | ✅ PASS | No venue-specific types leak above adapters |
| VIII. Total Observability & Provenance | ✅ PASS | Every decision logged with reason code |
| IX. Secrets and Safety Rails | ✅ PASS | .env gitignored, no secrets in logs |

## Quick Start

### Prerequisites

- Python 3.11 or higher
- pip or uv

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd trading-system

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Configuration

```bash
# Copy example environment file
copy .env.example .env

# Edit .env and add your testnet API keys (optional - system works with simulated feed)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/trading --cov-report=html

# Run import-linter
import-linter lint
```

### Running the System

**Live Paper Trading (Simulated Feed)**:
```bash
python -m trading.loop.live
```

**Backtest**:
```bash
python -m trading.backtest.runner
```

## Architecture

### Components

- **Data Layer**: Market state, desired position, fixtures, simulated feed
- **Strategy Layer**: Trivial momentum strategy
- **Risk Layer**: Deterministic risk engine with position limits, daily loss limits, kill switch
- **Execution Layer**: Paper (simulated) execution client
- **Backtest Layer**: Backtest runner with cost model
- **Logkit**: Decision logging with reason codes

### Import Boundaries

The import-linter enforces:
1. **Forbidden ML in Risk Layer**: Risk cannot import torch, tensorflow, sklearn, transformers
2. **Forbidden Execution Adapters Imports**: Strategy, risk, data, backtest cannot import execution.adapters

## Test Results

```
================ 35 passed, 707 warnings in 232.54s =================

Test breakdown:
- Risk engine tests: 10 passed
- Import boundary tests: 5 passed
- Live loop integration tests: 5 passed
- Backtest integration tests: 6 passed
- Cost model tests: 9 passed

Import-linter: 2 kept, 0 broken
```

## Constitutional Requirements Verification

### SC-001: System processes 100 consecutive market data updates
✅ PASS - Live loop integration test verifies 100 updates processed

### SC-002: Every decision has a reason code
✅ PASS - All decisions logged with reason_code field

### SC-003: Backtest completes in under 60 seconds
✅ PASS - 1000 data points complete in under 60 seconds

### SC-004: P&L report explicitly lists all cost components
✅ PASS - Fees, spread, slippage listed separately

### SC-005: Determinism verified
✅ PASS - Same input produces identical output

### SC-006: Risk engine has no ML/AI imports
✅ PASS - Import-linter enforces this

### SC-007: End-to-end loop completes successfully
✅ PASS - Integration test verifies complete loop

### SC-008: Manual calculation matches within 0.01%
✅ PASS - Cost verification tests confirm accuracy

### SC-009: Negative P&L is acceptable
✅ PASS - System accepts losing strategies

### SC-010: Clamp test uses small enough limit
✅ PASS - Test uses 0.5 BTC limit, clamp fires correctly

## Safety Rails

- ⚠️ **NEVER** commit real API keys to git
- ⚠️ **NEVER** run with `TRADING_ENV=mainnet` in development
- ⚠️ **ALWAYS** test on testnet before any real-money consideration
- ⚠️ **VERIFY** import boundaries pass before committing

## Project Structure

```
trading-system/
├── src/trading/
│   ├── data/           # Market data and fixtures
│   ├── strategy/       # Trading strategies
│   ├── risk/           # Risk engine and limits
│   ├── execution/      # Paper execution and interfaces
│   ├── backtest/       # Backtest runner and cost model
│   ├── logkit/         # Decision logging
│   └── loop/           # Live trading loop orchestrator
├── tests/
│   ├── integration/    # Integration tests
│   ├── test_risk.py
│   ├── test_backtest_costs.py
│   └── test_boundaries.py
├── specs/              # Feature specifications
├── config/             # Configuration files
├── logs/               # Decision logs (gitignored)
└── .env                # Environment variables (gitignored)
```

## Next Steps

After completing the walking skeleton:
1. Review the constitution for governing principles
2. Review `specs/001-walking-skeleton/` for full specification
3. Run `/speckit-tasks` to generate actionable task list
4. Run `/speckit-implement` to execute the tasks

## License

[Your License Here]
