# Kraken Data Channel Question - Open

**Date**: 2026-07-14
**Status**: OPEN (Deferred to Sprint 2 / Strategy & Roadmap)
**Related WO**: WO-002

## Question

Should the trading system consume Kraken's trade channel (~14 events/min) or switch to ticker/book channel (~1,000-10,000 events/min)?

## Context

- Current implementation: KrakenPublicFeed subscribes to trade channel only
- Observed rate: ~14 trade events/minute on BTC/USD
- Trade channel contains only executed trades (no order book depth, no bid/ask ticks)
- Ticker/book channels would provide significantly more events but different data shape

## Current Assessment

**For walking-skeleton phase (~14 events/min is acceptable)**:
- Trivial momentum strategy producing zero signals on sparse, flat data is **expected and correct**, not a defect
- The end-to-end loop (data → strategy → risk → execution → log) functions correctly
- All constitutional guards verified (belt + suspenders)
- Venue independence verified (single-module change works)

**For production strategy (Sprint 2+ consideration)**:
- Higher event rates may improve signal quality for momentum strategies
- Book data enables bid/ask spread modeling (already simulated in costs)
- Different API versions may offer better normalization

## Constraints

- **DO NOT change subscription, channel, or API version** until Sprint 2 strategy decision
- Walking skeleton phase is about proving the loop works, not signal quality
- Venue swap (Bybit → Kraken) already completed successfully

## Decision Required (Sprint 2)

Strategy & Roadmap work order should evaluate:
1. Whether momentum/volume strategies benefit from higher tick rates
2. Whether book/top-of-book data improves entry/exit timing
3. API version stability and normalization requirements
4. Cost impact of more frequent signals (fees, slippage)

## Reference

- Instruction: "do not act on it now. It is deferred to a Strategy & Roadmap decision for Sprint 2."
- Venue swap WO-002: Completed successfully, all tests passing
- Principle II (Walking Skeleton Before Palace): Infrastructure validated before optimization
