# Developer Quickstart: Walking Skeleton

**Feature**: 001-walking-skeleton
**Date**: 2026-07-11
**Phase**: 1 (Design)

## Prerequisites

- **Python**: 3.11 or higher
- **Git**: For cloning the repository
- **uv** (recommended) or **pip**: For package management
- **Windows 11**: Target development platform

## 1. Clone and Setup

```powershell
# Clone the repository
git clone <repository-url>
cd trading-system

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 2. Configure

```powershell
# Copy example environment file
copy .env.example .env

# Edit .env and add your testnet API keys
# Bybit testnet: https://testnet.bybit.com/
# Get API keys from: https://testnet.bybit.com/app/apikey
```

**`.env` file contents**:
```env
# Bybit Testnet API Keys (get from https://testnet.bybit.com/app/apikey)
BYBIT_API_KEY=your_testnet_api_key_here
BYBIT_API_SECRET=your_testnet_api_secret_here

# Trading Environment (DO NOT change to mainnet without explicit override)
TRADING_ENV=testnet

# Optional: Override default configuration values
# RISK_MAX_POSITION_BTC=1.0
# RISK_MAX_DAILY_LOSS_PCT=0.05
# EXECUTION_FEE_RATE_PCT=0.1
```

**⚠️ WARNING**: Never commit real API keys to git. The `.env` file is gitignored.

## 3. Verify Installation

```powershell
# Run pytest to verify all tests pass
pytest

# Run with coverage report
pytest --cov=src/trading --cov-report=html
```

Expected output:
```
tests/test_risk.py PASSED
tests/test_backtest_costs.py PASSED
tests/test_boundaries.py PASSED
tests/integration/test_live_loop.py PASSED
tests/integration/test_backtest.py PASSED
```

## 4. Run Tests

```powershell
# Run all tests
pytest

# Run specific test file
pytest tests/test_risk.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_risk.py::test_clamp_fires_when_limit_exceeded
```

## 5. Run Live Loop (Testnet)

```powershell
# Run live paper trading loop on testnet
python -m trading.loop.live --env=testnet

# Expected output:
# Connecting to Bybit testnet...
# Subscribed to BTC/USD market data...
# [2024-07-11 12:00:00] No signal (insufficient price movement)
# [2024-07-11 12:00:05] Buy signal detected (price change > 1%)
# [2024-07-11 12:00:05] Risk check: RISK_PASS
# [2024-07-11 12:00:06] Order submitted: BTC/USD BUY 0.1
# [2024-07-11 12:00:07] Order filled: 0.1 BTC @ 65000.00
# [2024-07-11 12:00:07] Fees: $6.50 | Spread: $32.50 | Slippage: $1.30
```

**Safety rails**:
- System defaults to `testnet` (simulated execution only)
- Real-money orders require explicit `--allow-mainnet` flag
- Kill switch can be engaged via Ctrl+C or API call

## 6. Run Backtest

```powershell
# Run backtest on stored market data
python -m trading.backtest.runner --data=data/btcusd.parquet

# Expected output:
# Loading 1000 market data points...
# Backtest window: 2024-07-10 00:00:00 to 2024-07-10 23:59:59
# Processing market data...
# Total trades: 5
# Gross P&L: $150.00
# Fees: -$7.50
# Spread cost: -$25.00
# Slippage cost: -$5.00
# Net P&L: $112.50
# Win rate: 60%
# Max drawdown: -$50.00
```

## 7. Import Boundary Verification

```powershell
# Run import-linter to verify boundary violations fail CI
import-linter

# Expected: PASS (no violations)

# To test violation detection, temporarily add a forbidden import:
# In src/trading/risk/engine.py, add: import torch
# Then run: import-linter
# Expected: FAIL (error on ML/AI import in risk layer)
```

## 8. View Decision Logs

```powershell
# Decision logs are written to logs/ directory
# View in real-time:
Get-Content logs\decisions.log -Wait

# View backtest results:
cat logs\backtest_results.json
```

**Decision log format**:
```json
{
  "timestamp": "2024-07-11T12:00:05Z",
  "layer": "RISK",
  "event_type": "PASS",
  "reason_code": "RISK_PASS",
  "venue": "bybit_testnet",
  "symbol": "BTC/USD",
  "side": "BUY",
  "size": 0.1,
  "intended_price": 65000.00,
  "executed_price": 65000.00,
  "fees": 6.50,
  "strategy_version": "v1.0.0",
  "feature_snapshot_hash": "abc123"
}
```

## 9. Kill Switch Test

```powershell
# Engage kill switch (via API or environment variable)
$env:RISK_KILL_SWITCH="true"

# Run live loop - should block all new orders
python -m trading.loop.live --env=testnet

# Expected: All orders rejected with RISK_VETO_KILL_SWITCH
```

## 10. Common Issues

**Issue**: `ImportError: No module named 'trading'`
**Solution**: Make sure virtual environment is activated (`.venv\Scripts\activate.ps1`)

**Issue**: `ConnectionError: Failed to connect to testnet`
**Solution**: Check API keys in `.env` file, verify network connectivity

**Issue**: `PermissionError: Refusing to connect to mainnet`
**Solution**: Don't set `TRADING_ENV=mainnet`. Use `testnet` for development.

**Issue**: Import linter fails
**Solution**: Fix boundary violations. Risk layer cannot import ML/AI libraries.

## 11. Development Workflow

1. Make changes to source code in `src/trading/`
2. Run tests: `pytest`
3. Verify import boundaries: `import-linter`
4. Run type checking: `mypy src/trading/`
5. Commit changes

**Pre-commit hooks** (recommended):
```bash
# Install pre-commit
pip install pre-commit

# Run hooks
pre-commit run --all-files
```

## 12. Next Steps

After completing the walking skeleton:
1. Review `plan.md` for full implementation plan
2. Review `data-model.md` for entity definitions
3. Review `contracts/` for interface specifications
4. Run `/speckit-tasks` to generate actionable task list
5. Run `/speckit-implement` to execute the tasks

## 13. Configuration Reference

**config/config.yaml**:
```yaml
trading:
  env: testnet
  pair: BTC/USD

strategy:
  name: trivial_momentum
  params:
    price_change_pct: 0.01
    volume_multiple: 2.0

risk:
  max_position_btc: 1.0
  max_daily_loss_pct: 0.05
  kill_switch: false

execution:
  venue: bybit_testnet
  fee_rate_pct: 0.1

backtest:
  input_data: data/btcusd.parquet
  output_dir: logs/backtest
```

## 14. Safety Reminders

⚠️ **NEVER** commit real API keys to git
⚠️ **NEVER** run with `TRADING_ENV=mainnet` in development
⚠️ **ALWAYS** test on testnet before any real-money consideration
⚠️ **VERIFY** import boundaries pass before committing

---

**Need help?** Review the constitution at `.specify/memory/constitution.md` for governing principles.
