# Decision: Retire Bybit Testnet, Adopt Kraken Mainnet Public Feed

**Date:** 2026-07-14
**Status:** Active
**Context:** WO-002 Venue Swap

---

## Problem Statement

Bybit testnet was chosen as the provisional development venue per Principle VII. However, testing revealed a fundamental issue: Bybit testnet delivers only ~12 trade events/minute, which is too thin for the strategy→risk→execution chain to fire meaningfully. Additionally, Bybit is not legally usable for real-money trading from Canada.

## Decision

**Retire Bybit testnet entirely. Adopt Kraken mainnet public WebSocket feed.**

### What Changed

1. **Data Source:** `DATA_SOURCE` environment variable selects market data feed
   - Options: `simulated`, `kraken_public`
   - Bybit testnet removed entirely

2. **Execution Environment:** `TRADING_ENV` gates execution only (independent of data source)
   - Options: `paper`, `mainnet`
   - Defaults to `paper` for safety
   - Real-money execution requires explicit, deliberate override

3. **No API Keys Required:** Public feeds require zero credentials
   - Removed `BYBIT_API_KEY` and `BYBIT_API_SECRET` from configuration
   - Kraken public feed is unauthenticated, read-only

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layer                      │
├─────────────────────────────────────────────────────────────┤
│  DATA_SOURCE = "kraken_public"  │  TRADING_ENV = "paper"    │
│  (Market data feed)              │  (Execution gating)       │
└────────────┬────────────────────┴──────────┬────────────────┘
             │                               │
             v                               v
┌─────────────────────┐         ┌─────────────────────────┐
│  Kraken Public WS   │         │   Paper Execution       │
│  (read-only, no     │         │   (simulated fills)      │
│   credentials)      │         │                         │
└─────────────────────┘         └─────────────────────────┘
```

## Rationale

### Why Drop Bybit?

1. **Insufficient Event Rate:** ~12 events/min on testnet vs. 1,000–10,000 on mainnet
2. **Legal Constraints:** Bybit cannot be used for real-money trading from Canada
3. **Dishonest Backtesting:** Any backtest on testnet data is fictional evidence (wrong spread/depth/volume)

### Why Kraken?

1. **Likely Real-Money Venue:** Kraken is Canada-legal for real-money trading (Phase 3 consideration)
2. **Honest Substrate:** Kraken mainnet order flow provides real microstructure for calibration
3. **Public Feed Available:** No API keys required for public market data (Principle IX compliance)

### Why Decouple DATA_SOURCE from TRADING_ENV?

**The Invariant:**
> No code path that can place, amend, or cancel a real order is reachable while `TRADING_ENV=paper` — **regardless of what `DATA_SOURCE` is set to.**

This separation enables:
- Testing against live market data (`DATA_SOURCE=kraken_public`) while safely executing in paper mode (`TRADING_ENV=paper`)
- Production deployment with paper-trading monitoring before going live
- Clear separation between data access and execution risk

### Constitutional Compliance

| Principle | Status |
|-----------|--------|
| VII. Venue Independence | ✅ Venue swap was single-module change (adapter layer only) |
| IX. Secrets and Safety Rails | ✅ Zero credentials required for public feed |
| VI. Risk Engine Is Sovereign | ✅ Execution gated by `TRADING_ENV=paper` |

## Implementation

### Files Modified
- Created: `src/trading/data/adapters/kraken_public.py` (new adapter)
- Modified: `src/trading/data/adapters/factory.py` (switched from Bybit to Kraken)
- Modified: `config/settings.py` (changed `FEED_TYPE` to `DATA_SOURCE`, removed Bybit credentials)
- Modified: `.env.example` (removed Bybit credentials, added `DATA_SOURCE`/`TRADING_ENV`)
- Deleted: `src/trading/data/adapters/bybit_testnet.py` (retired)

### Guardrails
1. **Settings.validate()** blocks `TRADING_ENV=mainnet` at module import time
2. **PaperExecutionClient** double-checks `is_paper_trading()` in `__init__`
3. **No real-money execution adapters** exist in Phase 1 scope

## Trade-offs

### Gained
- Real market data for testing (vs. insufficient testnet data)
- No credential management required
- Honest substrate for strategy calibration
- Clear separation of data access and execution risk

### Accepted
- Venue detail leakage detected in `src/trading/loop/live.py` line 142 (`venue = "kraken_mainnet"`)
- One-module claim did NOT hold (WO-002-D finding)
- Import-linter did not catch leakage (proposal: add `loop/` to contract)

## Future Considerations

### Sprint 3 (Real-Money Execution)
When real-money execution adapters are added:
- Adapters will require `TRADING_ENV=mainnet` (inverse of paper check)
- This will create true belt+suspenders for both environments
- `KrakenMainnetExecutionClient` will implement `ExchangeClient` interface

### Additional Venues
Architecture supports adding more public feeds:
- Coinbase public WebSocket
- Binance public WebSocket
- All follow same adapter pattern behind factory

## References

- Work Order WO-002: Complete the Kraken Venue Swap
- Constitution: `.specify/memory/constitution.md`
- Progress: `progress.md`
- Instructions: `instructions.md`

---

**Decision Record ID:** DR-2026-07-14-001
**Ratified:** 2026-07-14
**Amendment History:** None
