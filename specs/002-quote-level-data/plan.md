# Implementation Plan: Quote-Level Data + Observed-Spread Cost Model

**Branch**: `002-quote-level-data` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-quote-level-data/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Replace the trades feed with quote-level (order book) data from Kraken WebSocket v2 so the cost model uses **REAL observed spread** instead of an assumption. The data adapter migrates to Kraken v2 book channel (top-of-book: best bid/ask) as primary, with trades channel as secondary enrichment for rolling statistics. All v2-specific detail (protocol, checksum algorithm, sequence tracking, resync logic) is confined to a single adapter module. MarketState becomes quote-centric, and the backtest cost model computes spread cost from actual observed bid/ask only — no synthetic or fallback spreads anywhere.

## Technical Context

**Language/Version**: Python 3.11+ (3.13+ in development; 3.14.6 tested)

**Primary Dependencies**:
- `websockets` — WebSocket client for market data feeds
- `pandas`/`pyarrow` — Parquet append-only storage
- `pytest` + `pytest-asyncio` — Test framework with async support
- `import-linter` — Boundary enforcement (CI gate)

**Storage**:
- Live: In-memory local book state (top-of-book only)
- Backtest: Parquet files (append-only) storing raw quote/book data

**Testing**: pytest with asyncio plugin; import-linter for boundary enforcement

**Target Platform**: Windows 11 (development), Linux (production/CI)

**Project Type**: Single-repo trading system with layered architecture: Data → Strategy → Risk → Execution

**Performance Goals**:
- Process quote updates at real-time rate (hundreds to thousands per minute)
- Checksum validation on every update (<1ms per update)
- Book resync within 30 seconds of disconnection

**Constraints**:
- **No synthetic spread anywhere** — Principle V non-negotiable
- **v2/book detail confined to adapter** — Principle VII non-negotiable
- Strategy interface unchanged: `decide(market_state) -> DesiredPosition`
- All book validations logged with reason codes

**Scale/Scope**:
- One trading pair (BTC/USD or ETH/USD)
- Top-of-book only (best bid/ask) — full depth out of scope
- Single venue (Kraken) — single-module swap for other venues later

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Evaluation

| Principle | Requirement | Evaluation | Status |
|-----------|------------|------------|--------|
| **I. Truth Before Profit** | Cost model uses real observed spread, not assumptions | FR-011 through FR-015a mandate observed-spread-only; FR-015a explicitly forbids synthetic/assumed/fallback spreads anywhere | ✅ PASS |
| **II. Walking Skeleton Before Palace** | Change attaches to already-working end-to-end loop | Sprint 1 complete (36 tests passing); this change enhances data layer only | ✅ PASS |
| **III. AI Proposes, Deterministic Code Disposes** | Risk layer has no ML/AI | No risk layer changes; risk/ stays deterministic | ✅ PASS |
| **IV. Layered Architecture, Enforced Boundaries** | v2/book detail confined to adapter; no leaks upward | FR-020 through FR-022 + import-linter contract updates | ✅ PASS (pending contract design) |
| **V. No Backtest Without Costs** | Real observed spread in backtest cost model | FR-011, FR-012, FR-015a, SC-002, SC-005, QG-001 — core requirement | ✅ PASS |
| **VI. Risk Engine Is Sovereign** | Risk layer unchanged; still final authority | No risk layer changes; interface unchanged | ✅ PASS |
| **VII. Venue Independence** | Venue-specific detail confined to adapter module | This is the **clean re-test** after prior leak; import-linter will enforce | ✅ PASS (pending contract design) |
| **VIII. Total Observability & Provenance** | All book validations logged with reason codes | FR-004, FR-017, FR-018, FR-018a, FR-019a mandate reason codes | ✅ PASS |
| **IX. Secrets and Safety Rails** | No credentials needed for public Kraken v2 feed | Public WebSocket; no API keys required | ✅ PASS |

### Pre-Design Gates

**GATE STATUS**: ✅ **PASS** — All principles satisfied pending contract design for IV and VII.

**REQUIRED POST-DESIGN RE-EVALUATION**: Principles IV and VII must be re-checked after Phase 1 design to confirm:
1. Adapter module path is explicitly specified
2. Import-linter contracts are updated to block v2/book/checksum leaks above adapter
3. No v2 detail appears in data/, strategy/, risk/, backtest/, or loop/

### Load-Bearing Items from Spec

Three load-bearing items verified intact in spec and must remain intact in design:

1. **Cost model uses observed spread only** (FR-011, FR-012, FR-015a, SC-002, SC-005, QG-001)
   - No assumed, fixed, cached-stale, or "maximum-observed-from-history" spread
   - On anomaly (zero, negative, >5% of price): REJECT trade (log + skip)

2. **v2 book checksum validation on every update** (FR-004, FR-016 through FR-019, SC-003, QG-003)
   - CRC checksum validated on every update
   - 5 consecutive failures → reconnect and resync
   - Sequence gap → discard book + resnapshot

3. **Strategy logic/interface unchanged** (FR-023 through FR-026, SC-006, QG-002)
   - `decide(market_state) -> DesiredPosition` signature unchanged
   - No strategy logic changes in this feature

## Project Structure

### Documentation (this feature)

```text
specs/002-quote-level-data/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── data-adapter.yml  # Adapter interface contract
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

**Structure Decision**: Single-project (Python trading system) with layered architecture.

```text
src/trading/
├── data/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── kraken_public.py         # EXISTING: v1 trades feed (to be deprecated)
│   │   ├── kraken_v2_book.py        # NEW: v2 book adapter (checksum, sequence, resync)
│   │   └── simulated_feed.py        # EXISTING: Simulated feed (no changes)
│   ├── fixtures.py                  # EXISTING: Test data
│   ├── market_state.py             # MODIFY: Add quote-centric fields (bid/ask/size)
│   ├── desired_position.py         # EXISTING: No changes
│   └── persistence.py               # EXISTING: Parquet append-only (no changes)
├── strategy/
│   ├── interface.py                 # EXISTING: No signature changes
│   └── trivial.py                   # EXISTING: No logic changes (may read new fields)
├── risk/
│   ├── interface.py                 # EXISTING: No changes
│   ├── engine.py                    # EXISTING: No changes
│   ├── limits.py                     # EXISTING: No changes
│   └── position_state.py            # EXISTING: No changes
├── execution/
│   ├── interface.py                 # EXISTING: No changes
│   ├── paper.py                     # EXISTING: No changes
│   ├── approved_order.py           # EXISTING: No changes
│   ├── fill.py                      # EXISTING: No changes
│   └── adapters/
│       └── __init__.py              # EXISTING: No execution adapters (paper only)
├── backtest/
│   ├── runner.py                    # MODIFY: Replay from quote data instead of trades
│   ├── costs.py                     # MODIFY: Use observed spread from MarketState
│   └── report.py                    # EXISTING: No changes
├── logkit/
│   ├── decision.py                  # MODIFY: Add new reason codes
│   └── provenance.py               # EXISTING: No changes
└── loop/
    └── live.py                      # MODIFY: Use new adapter; handle book-unavailable pause

tests/
├── test_data_adapters.py            # NEW: Adapter tests (checksum, sequence, resync)
├── test_market_state.py             # MODIFY: Add quote-centric field tests
├── test_backtest_costs.py           # MODIFY: Add observed-spread cost tests
├── test_boundaries.py               # MODIFY: Verify adapter boundary contracts
├── integration/
│   ├── test_live_loop.py            # MODIFY: Test book-unavailable pause
│   └── test_backtest.py             # MODIFY: Test backtest over quote data
└── (existing test files unchanged)

.importlinter.yaml                   # MODIFY: Add adapter boundary contract
```

**Key Structure Points**:

1. **NEW adapter module**: `src/trading/data/adapters/kraken_v2_book.py` — ALL v2/book/checksum/sequence/resync detail lives here
2. **MODIFIED files**: MarketState schema, backtest runner, costs, decision log, live loop
3. **NO changes to**: Strategy, risk, execution interfaces or logic (except reading new MarketState fields)
4. **Import-linter contract update**: New contract preventing v2/book/checksum imports above `data/adapters/`

## Post-Design Constitution Re-Evaluation

*GATE: Re-check after Phase 1 design to confirm Principles IV and VII are satisfied.*

### Design Evidence for IV and VII

**Principle IV (Layered Architecture) & Principle VII (Venue Independence)**:

1. **Adapter module path explicitly specified**:
   - `src/trading/data/adapters/kraken_v2_book.py` — ALL v2/book/checksum/sequence/resync detail lives here
   - Documented in [Project Structure](#project-structure) and [data-model.md](./data-model.md)

2. **Import-linter contract specified**:
   - See [contracts/data-adapter.yml](./contracts/data-adapter.yml)
   - Contract forbids v2/book/checksum imports above adapter:
     - `trading.strategy*` cannot import `kraken_v2_book` internals
     - `trading.risk*` cannot import `kraken_v2_book` internals
     - `trading.execution*` cannot import `kraken_v2_book` internals
     - `trading.backtest*` cannot import `kraken_v2_book` internals
     - `trading.loop*` cannot import `kraken_v2_book` internals
   - Only allowed: `from trading.data.adapters import KrakenV2BookAdapter` (factory import)

3. **No v2 detail appears above adapter**:
   - Data consumers (`strategy/`, `risk/`, `execution/`, `backtest/`, `loop/`) see only `MarketFeed` interface and `MarketState` objects
   - v2 protocol, checksum algorithm, sequence numbers, resync logic are adapter-internal
   - Documented in [data-model.md](./data-model.md): "All v2/book-specific detail is internal to the adapter. Above the adapter (`data/` consumers), only the standard `MarketState` interface is visible."

### Post-Design Evaluation

| Principle | Pre-Design Status | Post-Design Evidence | Final Status |
|-----------|-------------------|---------------------|--------------|
| **IV. Layered Architecture** | ✅ PASS (pending contract) | Contract specified in `contracts/data-adapter.yml`; v2 detail confined to `kraken_v2_book.py` | ✅ PASS |
| **VII. Venue Independence** | ✅ PASS (pending contract) | Adapter module path specified; import-linter contract blocks leaks above adapter; factory pattern preserved | ✅ PASS |

### Post-Design Gate Status

**GATE STATUS**: ✅ **PASS** — Principles IV and VII satisfied.

**Adapter Boundary Confirmed**:
- Module: `src/trading/data/adapters/kraken_v2_book.py`
- Contract: `contracts/data-adapter.yml`
- Enforcement: Import-linter blocks v2/book/checksum imports above adapter

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | No violations | All principles satisfied; design is simpler than prior version (fewer layers, clearer boundaries) |
