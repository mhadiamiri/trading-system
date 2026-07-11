# Technical Research: Walking Skeleton

**Feature**: 001-walking-skeleton
**Date**: 2026-07-11
**Phase**: 0 (Research)

## Bybit Testnet API

### Authentication
- Bybit uses API key + secret for HMAC SHA256 signature
- Testnet URL: `https://api-testnet.bybit.com`
- Testnet WebSocket: `wss://stream-testnet.bybit.com/v5/public/linear`

### Market Data (WebSocket)
- Endpoint: `/v5/public/linear` for BTCUSDT perpetual futures
- Subscription: `{"topic":"tickers","symbol":"BTCUSDT"}`
- Response fields: `bid1Price`, `ask1Price`, `lastPrice`, `volume24h`
- Update frequency: real-time push

### Order Management (REST)
- Place order: `POST /v5/order/create`
- Cancel order: `POST /v5/order/cancel`
- Query order: `GET /v5/order/realtime`
- Required params: `symbol`, `side` (Buy/Sell), `orderType` (Market/Limit), `qty`
- Response: `orderId`, `orderStatus`, `executedQty`, `avgPrice`

## Storage Strategy

### SQLite (Structured Data)
**Schema Design**:
- `decision_logs` table: timestamp, layer, event_type, reason_code, venue, symbol, side, size, intended_price, executed_price, fees, strategy_version, snapshot_hash
- `trades` table: timestamp, symbol, side, size, fill_price, fees, spread_cost, slippage_cost, cad_value
- Indexes on timestamp, symbol for query performance

**Connection Pattern**:
```python
import sqlite3
conn = sqlite3.connect('logs/trading.db')
conn.execute("PRAGMA journal_mode=WAL")  # Concurrent access
```

### Parquet (Raw Market Events)
**Write Pattern** (append-only):
```python
import pyarrow as pa
import pyarrow.parquet as pq

schema = pa.schema([
    ('timestamp', pa.timestamp('ns')),
    ('symbol', pa.string()),
    ('bid_price', pa.float64()),
    ('ask_price', pa.float64()),
    ('last_price', pa.float64()),
    ('volume', pa.float64()),
])

# Append to existing file or create new
writer = pq.ParquetWriter('data/market_events.parquet', schema)
writer.write_table(table)
writer.close()
```

## Import Boundary Configuration

### .importlinter.yaml Structure
```yaml
unimported:
  - trading.risk  # Risk layer must be pure
  - trading.strategy  # Strategy layer must be independent
  - trading.data  # Data layer must be independent
  - trading.backtest  # Backtest must be independent

contract_layers:
  - layer: trading.execution.adapters
    importers:
      - trading.strategy
      - trading.risk
      - trading.data
      - trading.backtest
    action: forbid

forbidden_modules:
  - torch
  - tensorflow
  - sklearn
  - transformers
importers:
  - trading.risk
action: error
```

### CI Integration
```bash
# In pytest command or GitHub Actions
import-linter && pytest
```

## Configuration Strategy

### config.yaml Structure
```yaml
trading:
  env: testnet  # default, requires explicit override for mainnet
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

### .env Structure (secrets only)
```
BYBIT_API_KEY=
BYBIT_API_SECRET=
TRADING_ENV=testnet  # redundant with config.yaml but provides override point
```

## Python Dependencies

### Core (requirements.txt)
```
pyarrow>=14.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
httpx>=0.25.0
```

### Development (requirements-dev.txt)
```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
import-linter>=2.0.0
ruff>=0.1.0
mypy>=1.6.0
```

## Testing Strategy

### test_risk.py (Required)
- Test clamp fires when position limit exceeded
- Test veto fires when daily loss exceeded
- Test kill switch blocks new orders
- Test no ML/AI imports in risk layer

### test_backtest_costs.py (Required)
- Test fees applied to every trade
- Test spread applied on entry and exit
- Test slippage reduces fill prices
- Test P&L report shows cost breakdown

### test_boundaries.py (Required)
- Test import boundary violations fail CI
- Test venue adapter isolation

## Open Questions Resolved

1. **How to handle WebSocket reconnection?**
   - Exponential backoff on disconnect, log gap, resume on reconnect (edge case already in spec)

2. **How to generate client order IDs?**
   - Idempotent UUID-based IDs with timestamp prefix

3. **How to handle partial fills?**
   - Out of scope for walking skeleton (assumed full fills)

4. **How to model spread crossing?**
   - Buy at ask, sell at bid (taker behavior matches strategy type)

5. **How to validate TRADING_ENV before execution?**
   - ExchangeClient.__post_init__ raises if TRADING_ENV=mainnet without explicit override flag
