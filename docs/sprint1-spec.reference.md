# Feature Specification: Walking Skeleton — End-to-End Paper Loop + Cost-Inclusive Backtest

**Feature Branch**: `001-walking-skeleton`

**Created**: 2026-07-10

**Status**: Draft (review reference — the canonical spec is what `/speckit-specify` generates; use this to sanity-check that output)

**Input**: Sprint 1 of the master brief — data ingester, one trivial strategy, backtester with costs, paper loop end-to-end, everything logged.

---

> **Note on this file.** In spec-kit you generate `spec.md` by running `/speckit-specify "<description>"`, not by hand. This document is a *reference* of what a good generated spec should contain, so the generated one can be checked against it. The `/speckit-specify` prompt that should produce it lives in the runbook. Keep this behavioral — the *what* and *why*, never the tech stack (that belongs in `plan.md`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The end-to-end paper loop runs (Priority: P1)

As the operator, I can point the system at one crypto pair's live (testnet) market data and watch it turn each market update into a decision, pass that decision through a deterministic risk check, place a *simulated* order, and log every step — however trivial each part is.

**Why this priority**: This is the walking skeleton. Per the constitution (Walking Skeleton Before Palace), no part may be deepened until this complete loop runs. It is the MVP: data in → decision → risk → simulated order → logged result.

**Independent Test**: Start the loop against the testnet feed for a fixed window; confirm the log contains, for every market update, a strategy decision (including "no signal"), a risk outcome with a reason code, and — when an order is approved — a simulated fill. No real order is ever placed.

**Acceptance Scenarios**:

1. **Given** a live testnet feed for one pair, **When** the strategy emits a desired position within limits, **Then** the risk engine returns *pass*, a simulated order is recorded, and the fill is logged with a reason code.
2. **Given** the strategy emits a desired position that exceeds the max position limit, **When** it reaches the risk engine, **Then** the order is *clamped* toward zero (never enlarged, never flipped) and the clamp is logged with a distinct reason code.
3. **Given** the kill switch is engaged, **When** any new desired position arrives, **Then** no new order is placed, the block is logged with a reason code, and cancellation logic is still permitted to run.
4. **Given** a market update that produces no signal, **When** the strategy runs, **Then** a "no signal" decision is still logged (silent decisions are not allowed).

---

### User Story 2 — An honest, cost-inclusive backtest (Priority: P2)

As the researcher, I can replay previously stored market data through the *same* strategy → risk → execution logic offline, with trading fees, the bid/ask spread, and a realistic slippage/fill model applied to every simulated trade, and get a profit-and-loss result plus a trade list I can trust.

**Why this priority**: Separable from the live loop (runs offline over stored data) and directly serves the system's first purpose — telling the truth about whether a strategy makes money after costs. Per the constitution (No Backtest Without Costs), a cost-free path must not exist.

**Independent Test**: Run the backtest over a stored data slice; verify every trade in the output carries fees, spread, and slippage, and that the reported P&L reflects them. Attempting to run a backtest with costs disabled must fail rather than silently produce a cost-free result.

**Acceptance Scenarios**:

1. **Given** a stored slice of market data, **When** the backtest runs, **Then** every simulated trade shows a non-zero fee, a spread cost, and a slippage adjustment, and the P&L is net of all three.
2. **Given** the same stored slice and strategy, **When** the backtest is re-run, **Then** it produces identical results (deterministic).
3. **Given** forecast quality is reported, **When** results are presented, **Then** forecasting accuracy is reported separately from tradable P&L (they are not conflated).

---

### Edge Cases

- The market feed disconnects mid-session → the loop reconnects (with backoff) and continues without losing the append-only record's integrity.
- A market update arrives while the kill switch is engaged → logged as blocked, no order.
- The stored data slice has a gap → the backtest handles it explicitly rather than silently interpolating profit.
- The strategy requests a side/size the account cannot support → risk clamps to a feasible size or vetoes, with a reason code.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST ingest live market data for exactly one configured pair and store raw events append-only.
- **FR-002**: On each relevant market update, the strategy MUST produce a desired position (which MAY be "flat"/"no signal"), through a stable interface that does not change when the strategy's internals change.
- **FR-003**: Every desired position MUST pass through the deterministic risk engine before any (simulated) order is placed. No path may bypass it.
- **FR-004**: The risk engine MUST return one of *pass*, *clamp*, or *veto*, where a clamp only reduces size toward zero and never increases size or flips direction, and MUST emit a distinct reason code for clamp and veto.
- **FR-005**: The risk engine MUST enforce max position size, max daily loss, and a kill switch; when the kill switch is engaged it MUST block new orders while still permitting cancellation logic.
- **FR-006**: All order placement in this phase MUST be simulated (paper); the system MUST NOT place real-money orders and MUST default to a non-real-money mode.
- **FR-007**: The system MUST log every order AND every non-order decision (including "no signal", clamp, and veto) with a reason code and enough context to reconstruct why it happened.
- **FR-008**: Each decision record MUST include at least: UTC timestamp, venue, symbol, side, size, intended vs. executed price, fees, `strategy_version`, and `feature_snapshot_hash`; the ledger MUST also capture the fields needed for Canadian tax records.
- **FR-009**: The backtester MUST apply fees, spread crossing, and a realistic slippage/fill model to every simulated trade; a cost-free backtest path MUST NOT exist.
- **FR-010**: The backtester MUST report P&L net of costs and a trade list, and MUST report forecasting accuracy (if any) separately from tradable profit.
- **FR-011**: No credential or secret MUST appear in any log line or decision record, nor be committed to version control.

### Key Entities

- **MarketState**: the current view of the market handed to the strategy (e.g. latest prices/among stored context) — no venue-specific detail.
- **DesiredPosition**: what the strategy proposes (side, target size) — a proposal, not an order.
- **ApprovedOrder**: the risk engine's output after pass/clamp/veto, carrying its reason code.
- **DecisionRecord**: the logged record of any decision (order or non-order), with provenance fields.
- **Trade / Fill**: a (simulated) execution with its costs attached.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The paper loop runs end-to-end against the testnet feed for a continuous window (target: ≥ 30 minutes) without crashing, surviving at least one feed reconnect.
- **SC-002**: 100% of decisions in that window — including "no signal", clamp, and veto — have a corresponding log record with a reason code.
- **SC-003**: 0 orders reach the (simulated) execution path without a recorded risk outcome.
- **SC-004**: 100% of simulated trades in a backtest run carry non-zero fee, spread, and slippage components, and P&L is net of them.
- **SC-005**: A deliberately oversized desired position is demonstrably clamped (never enlarged/flipped), evidenced by its reason code.
- **SC-006**: It is acceptable — and expected — that the strategy's P&L is negative. Honest, cost-inclusive measurement is the pass condition, not profitability.

## Assumptions

- One pair (BTC/USD or ETH/USD), spot, seconds-to-minutes horizon; the strategy is deliberately trivial (short-term move or volume spike).
- The development venue is a testnet/paper environment; real-money trading is out of scope for this phase.
- Multiple pairs/exchanges, leverage, arbitrage, any AI in the live decision path, and alternative data are explicitly out of scope (constitutional Phase-1 scope constraints).
- A stored data slice is available (or captured by the ingester) for the backtest to replay.
