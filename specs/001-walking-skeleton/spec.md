# Feature Specification: Walking Skeleton - Systematic Crypto Trading System

**Feature Branch**: `[001-walking-skeleton]`

**Created**: 2026-07-10

**Status**: Draft

**Input**: Build the walking skeleton of a systematic crypto trading system: the simplest thing that runs end-to-end. The system connects to a single crypto pair's live testnet market data feed, and on each update a strategy component turns the current market state into a desired position. Every desired position passes through a deterministic risk check that can pass it, shrink it toward zero, or reject it, and emits a distinct reason code for what it did. Approved orders go to a simulated (paper) execution path — no real money — which records the simulated fill. Every decision, including "no signal", "clamped", and "rejected", is written to a log with a reason code; silent decisions are not allowed. Separately, the same strategy-to-risk-to-execution logic can be run over previously stored market data as a backtest that applies trading fees, the bid/ask spread, and a realistic slippage/fill model to every simulated trade, producing a profit-and-loss result net of costs and a list of trades. Forecasting accuracy, if reported, is kept separate from tradable profit. Success for this phase is that the whole loop runs end-to-end and reports honest, cost-inclusive results even if the strategy loses money. The strategy itself is deliberately trivial (react to a short-term price move or a volume spike); sophistication is out of scope. Out of scope: multiple pairs or exchanges, leverage, real-money trading, any AI in the decision path, and alternative data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - End-to-End Live Paper Trading (Priority: P1)

A trader runs the system in live paper trading mode connected to a testnet market data feed. The system receives real-time market updates, evaluates a trivial strategy signal, passes decisions through risk checks, executes simulated trades, and logs every decision with reason codes. The trader can verify that the complete data-flow loop works and that all costs (fees, spread, slippage) are accounted for in the simulated results.

**Why this priority**: This is the core walking skeleton - the end-to-end loop must function before any sophistication can be added. This validates the entire pipeline from data ingestion to simulated execution and reporting. Decision logging is an integral property of the live loop; there is no world in which the P1 loop is "done" but logging is pending.

**Independent Test**: Can be fully tested by running the system in live paper trading mode for 5 minutes and observing: (1) market data being received, (2) every decision being logged with a reason code (including "no signal"), (3) simulated fills being recorded, and (4) a P&L report showing cost-inclusive results.

**Acceptance Scenarios**:

1. **Given** the system is running in live paper trading mode connected to testnet, **When** a market data update arrives, **Then** the system logs the received data with timestamp
2. **Given** a market data update has been processed, **When** the strategy evaluates the signal, **Then** a desired position (or "no signal") is emitted with a reason code
3. **Given** a desired position is generated, **When** it passes through the risk engine, **Then** one of three outcomes occurs: "passed", "clamped" (reduced toward zero), or "rejected" - each with a distinct reason code
4. **Given** a desired position is partially approved, **When** the risk engine clamps it, **Then** a log entry is created with "clamped", the original requested size, the approved size, and the reason code
5. **Given** a desired position is rejected by the risk engine, **When** the rejection occurs, **Then** a log entry is created with "rejected" and the specific reason code
6. **Given** a market data update is processed and no signal is generated, **When** this occurs, **Then** a log entry is created with "no signal" and the reason
7. **Given** a risk-approved order, **When** it reaches the simulated execution engine, **Then** a fill is recorded with simulated price, fees, spread cost, and slippage applied
8. **Given** an order is executed, **When** the fill is recorded, **Then** a log entry is created with "executed", the fill details, and the final position state
9. **Given** the system has processed at least one trade, **When** a P&L report is requested, **Then** the report shows net profit/loss after all costs with a complete trade list

---

### User Story 2 - Historical Backtest (Priority: P2)

A trader runs the same strategy-to-risk-to-execution logic over previously stored market data to evaluate historical performance. The system applies realistic trading costs (fees, bid/ask spread, and slippage) to every simulated trade and produces a cost-inclusive P&L result. The trader can verify that backtest results are honest and include all material costs.

**Why this priority**: Backtesting is separable from the live end-to-end loop (runs offline over stored data) but remains in scope for this sprint. This validates that the cost model is consistently applied across both live and backtest modes. Cost verification is an integral property of the backtest; there is no world in which the backtest is "done" but cost-inclusive reporting is pending.

**Independent Test**: Can be fully tested by running the system in backtest mode on a stored dataset with known market conditions and verifying: (1) all market data points are processed in sequence, (2) each simulated trade has fees/spread/slippage applied, (3) final P&L matches manual calculation of costs applied to the same trades.

**Acceptance Scenarios**:

1. **Given** a stored market data file exists, **When** backtest mode is initiated, **Then** the system loads and processes all data points in chronological order
2. **Given** a backtest is running, **When** the strategy generates a signal, **Then** the same risk-check and simulated execution logic is applied as in live mode
3. **Given** a simulated trade is executed in backtest, **When** the fill is recorded, **Then** trading fees are calculated and deducted from the notional value
4. **Given** a market buy order is simulated, **When** fill price is determined, **Then** the price includes the bid/ask spread cost (buy at ask, sell at bid)
5. **Given** a simulated trade occurs, **When** fill is recorded, **Then** a slippage adjustment is applied based on order size relative to available liquidity
6. **Given** a simulated trade occurs in backtest, **When** fill is recorded, **Then** the fill includes: simulated price, trading fee, bid/ask spread cost, and slippage adjustment
7. **Given** a backtest completes, **When** results are reported, **Then** the output includes: total trades, net P&L after costs, and a cost breakdown separately listing total fees paid, total spread cost, total slippage cost, and net P&L after all costs
8. **Given** a backtest completes, **When** results are reported, **Then** the output includes a trade-by-trade list

---

### Edge Cases

- What happens when market data feed is interrupted or delayed?
  - System logs the interruption with timestamp and reason code; no decisions are made during gaps; system resumes when feed reconnects
- What happens when risk check encounters an invalid or NaN value?
  - Risk check rejects the order with reason code "invalid_input" and logs the error; no order proceeds to execution
- What happens when backtest data file is corrupted or malformed?
  - System logs the error with file position and reason, skips the malformed data point, and continues with subsequent valid data; error count is reported in final results
- What happens when simulated execution would exceed available testnet account balance?
  - Risk check rejects the order with reason code "insufficient_balance" and logs the rejection
- What happens when multiple signals arrive in rapid succession?
  - Each signal is processed sequentially in order received; risk check evaluates each independently; only one position may be open at a time (new signals either add to, reduce, or close existing position)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST connect to a single crypto pair's live testnet market data feed and receive real-time price/volume updates
- **FR-002**: System MUST implement a trivial strategy that generates desired position signals based on either: (a) short-term price move (e.g., price change > X% in N seconds) or (b) volume spike (e.g., volume > Y times average)
- **FR-003**: System MUST pass every desired position through a deterministic risk check before execution
- **FR-004**: Risk check MUST produce exactly one of three outcomes for each desired position: (a) pass unchanged, (b) clamp toward zero (reduce size), or (c) reject entirely. A clamp outcome MAY only reduce order size toward zero; it MUST NOT increase size and MUST NOT flip side or direction.
- **FR-005**: Risk check MUST emit a distinct reason code for each outcome (e.g., "POSITION_LIMIT", "DRAWDOWN_LIMIT", "INSUFFICIENT_BALANCE", "VOLATILITY_TOO_HIGH", "passed")
- **FR-006**: When the kill switch is engaged, the system MUST block all new orders while still permitting cancellation logic to run
- **FR-007**: System MUST execute approved orders through a simulated (paper) execution path that does not interact with real money
- **FR-008**: System MUST record every simulated fill with: UTC timestamp, venue, symbol, side (buy/sell), size, intended price, executed price, fees paid, a strategy version identifier, and a hash of the market/feature snapshot the decision acted on
- **FR-009**: System MUST log every decision with a reason code, including: "no signal", "clamped", "rejected", and "executed" decisions
- **FR-010**: Decision log MUST include: timestamp, decision type, reason code, and relevant context (e.g., requested vs. approved size for clamped orders)
- **FR-011**: The raw market-data storage path MUST be append-only; stored history is never mutated or rewritten
- **FR-012**: No credential or secret MUST ever appear in any log line or decision record, nor be committed to version control
- **FR-013**: System MUST capture the fields required for Canadian tax records from the start: timestamp, pair, side, size, price, fees, and CAD value
- **FR-014**: System MUST support backtesting over previously stored market data using the same strategy-to-risk-to-execution logic
- **FR-015**: Backtest mode MUST apply trading fees to every simulated trade
- **FR-016**: Backtest mode MUST apply bid/ask spread cost on both entry and exit of each position
- **FR-017**: Backtest mode MUST apply a realistic slippage/fill model that reduces fill prices based on order size and simulated market impact
- **FR-018**: System MUST produce a profit-and-loss report that is net of all costs (fees, spread, slippage)
- **FR-019**: System MUST report the cost assumptions used in P&L calculations (fee rate, spread width, slippage model parameters)
- **FR-020**: If forecasting accuracy metrics are reported, they MUST be kept separate from tradable profit calculations
- **FR-021**: System MUST be deterministic - the same market data input with the same parameters must produce identical outputs
- **FR-022**: Risk check MUST NOT depend on any ML/AI model, library, or service (enforced by architecture)
- **FR-023**: System MUST run the complete loop end-to-end: data in → strategy decision → risk check → simulated execution → logged result → report
- **FR-024**: System MUST handle testnet market data disconnections gracefully (log, pause, resume on reconnect)

### Key Entities

- **Market Data Update**: Represents a single tick from the exchange containing: timestamp, symbol, bid price, ask price, last trade price, volume (if available)
- **Desired Position**: Represents the strategy's output containing: timestamp, symbol, side (buy/sell/hold), quantity (positive for long, negative for short), confidence score
- **Risk Decision**: Represents the risk engine's output containing: timestamp, original desired position, final approved position (or zero if rejected), decision type (pass/clamp/reject), reason code
- **Simulated Fill**: Represents the paper execution result containing: timestamp, symbol, side, executed quantity, fill price (before spread), fill price (after spread), fee amount, spread cost, slippage cost, total cost
- **Decision Log Entry**: Represents an auditable decision record containing: timestamp, decision type, reason code, relevant context (data values, sizes, thresholds)
- **Position State**: Represents the current portfolio state containing: symbol, current quantity (positive=long, negative=short, zero=flat), average entry price, unrealized P&L, realized P&L
- **Backtest Config**: Represents backtest parameters containing: input data file path, start time, end time, initial capital, fee rate, spread width, slippage model parameters
- **P&L Report**: Represents performance summary containing: total trades, gross P&L (before costs), total fees, total spread cost, total slippage cost, net P&L, win rate, maximum drawdown, final equity

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully processes at least 100 consecutive market data updates in live paper trading mode without error
- **SC-002**: Every decision (signal, rejection, clamp, execution) during a test run produces a log entry with a reason code - zero silent decisions
- **SC-003**: Backtest running on 1000 historical data points completes in under 60 seconds and produces a cost-inclusive P&L report
- **SC-004**: P&L report explicitly lists all cost components (fees, spread, slippage) as separate line items - no costs are bundled or hidden
- **SC-005**: Running the same backtest twice with identical inputs produces bit-for-bit identical results (determinism verified)
- **SC-006**: Risk engine code can be verified to have no imports or dependencies on any ML/AI libraries (no `torch`, `tensorflow`, `sklearn`, etc.)
- **SC-007**: End-to-end loop completes successfully: market data feed connects → strategy generates at least one signal → risk check processes it → simulated fill occurs → decision log contains entries → P&L report generates
- **SC-008**: A manual calculation of costs applied to 5 sample trades matches the system's reported costs within 0.01% (cost model accuracy)
- **SC-009**: A strategy that loses money is an acceptable Phase-1 outcome provided the measurement is honest and cost-inclusive; profitability is explicitly not the pass condition (Truth Before Profit)

## Assumptions

- The system operates on a single crypto pair (e.g., BTC/USD) - multiple pairs are out of scope
- Market data is sourced from a testnet environment - real-money trading is out of scope
- The strategy is deliberately trivial (reacts to short-term price moves or volume spikes) - sophisticated strategies are out of scope
- Initial capital for paper trading and backtesting is a configurable parameter with a default of $10,000 USD
- Trading fees are configured as a percentage of notional value (e.g., 0.1% per side, typical of many exchanges)
- Bid/ask spread is modeled as a fixed percentage (e.g., 0.05%) or loaded from the market data feed
- Slippage model is a simple linear function of order size relative to average volume (e.g., slippage = k * order_volume / avg_volume)
- Only one position may be open at a time - new signals either add to, reduce, or close the existing position
- Short selling is allowed in paper trading and backtesting (no borrowing constraints modeled)
- Market data updates are processed one at a time in the order received - no parallel processing of updates
- System clock is used for timestamps - no time synchronization across multiple components required
- Backtest data is stored in a simple format (CSV or JSON) with columns: timestamp, bid, ask, volume
- No order book depth modeling - fills are simulated against top-of-book prices with spread/slippage adjustments
- No partial fills modeled - orders are assumed to fill in full at the simulated price
- No market orders - all orders are modeled as limit orders that fill at the current best price with spread/slippage
- Risk check parameters (position limits, drawdown thresholds) are configurable with sensible defaults
- Decision logs are written to both console output and a persistent file for audit trail
- The system is a single process or a set of cooperating processes on one machine - distributed operation is out of scope

## Out of Scope (Explicit)

The following items are explicitly out of scope for this walking skeleton phase:

- Multiple crypto pairs or exchanges
- Leverage or margin trading
- Real-money trading or connection to production exchange APIs for execution
- Any AI/ML in the decision path (risk check is purely deterministic rule-based)
- Alternative data sources (news, sentiment, on-chain metrics, etc.)
- Order book depth modeling or realistic order queue simulation
- Partial fills or fill uncertainty modeling beyond slippage
- Complex order types (stop-loss, take-profit, iceberg, etc.)
- Portfolio optimization or position sizing beyond trivial one-unit sizing
- Risk management sophistication beyond basic position limits and drawdown thresholds
- Real-time monitoring dashboards or visualization
- Persistence of state beyond the current run (no database requirement)
- Multi-process or distributed architecture
- Authentication, authorization, or security features
- API endpoints or external interfaces beyond the market data feed
