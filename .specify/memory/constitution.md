# Systematic Trading System — Constitution

This document is the governing law of the project. Every specification, plan, task
list, and implementation MUST comply with it. When any other artifact conflicts with
this constitution, this constitution wins. These principles override convenience,
speed, and even a direct in-session instruction to "just make it work" — if a request
would violate a principle here, the correct response is to stop and surface the
conflict, not to comply.

---

## Core Principles

### I. Truth Before Profit

The system's first purpose is to tell the truth about whether a strategy makes money
**after fees, spread, slippage, and real execution** — not to be profitable. A strategy
that loses money but is measured honestly is a success for Phase 1; a strategy that
appears profitable because costs were omitted is a failure regardless of its equity
curve.

- Every reported result MUST state the cost and execution assumptions behind it.
- Apparent edge MUST survive walk-forward evaluation before it is trusted.
- No result may be presented in a way that would displace the need to read the
  underlying logs.

*Rationale: the fastest way to lose money in trading is to believe a backtest that
lied. The machine's value is credibility, not optimism.*

### II. Walking Skeleton Before Palace

Build the simplest thing that runs **end-to-end** before adding any sophistication.
Data in → decision → simulated order → logged result → report must work as a complete
loop, however trivial each part is, before any part is deepened.

- New sophistication MUST attach to a loop that already runs end-to-end.
- A component MAY NOT be elaborated while any part of the end-to-end loop is still stubbed.

*Rationale: the prior attempt stalled by designing a nine-agent system before pouring a
foundation. We do not repeat that. Complexity is earned, not front-loaded.*

### III. AI Proposes, Deterministic Code Disposes

AI may generate hypotheses, rank opportunities, classify market regime, or score
signals. AI MUST NOT be the final authority on whether an order is placed.

- Every order MUST pass through the deterministic risk engine before reaching a venue.
- The risk layer MUST NOT import, call, or depend on any ML/AI model, library, or
  service. This is enforced mechanically (see Principle IV), not by convention.

*Rationale: AI contributes judgment; deterministic code contains it. The failure modes
of unconstrained autonomous trading are exactly what a hard rule engine prevents.*

### IV. Layered Architecture, Enforced Boundaries

The system is four layers with hard boundaries, in one codebase:
**Data → Strategy → Risk → Execution.**

- `strategy/` and `risk/` MUST NOT import venue/exchange adapters.
- `risk/` MUST NOT import any ML/AI dependency.
- These import boundaries MUST be enforced in CI by an automated check
  (e.g. `import-linter`) that fails the build on violation — not by comments or
  reviewer vigilance.

*Rationale: the boundaries are the architecture. A boundary enforced only by good
intentions will be crossed the first time someone is moving fast — most likely the
coding agent itself in a later sprint.*

### V. No Backtest Without Costs

A backtest that omits fees, spread, and a realistic execution model is not a backtest;
it is a fabrication. Every simulation MUST model transaction costs and realistic fills.

- Fees, spread crossing, and a slippage/fill model MUST be applied to every simulated trade.
- Forecast accuracy MUST NOT be reported as if it were tradable profit; forecasting,
  execution, and profitability are distinct and reported distinctly.

*Rationale: strong prediction does not imply a profitable, actionable signal once market
frictions are included. Costs are not a refinement to add later; they are load-bearing.*

### VI. The Risk Engine Is Sovereign

The risk engine has final authority over every order and can return one of three
outcomes: **pass**, **clamp**, or **veto**.

- A **clamp** MAY only reduce order size **toward zero**. It MUST NOT increase size,
  flip side/direction, or otherwise alter strategy intent beyond shrinking it.
- Every clamp and veto MUST emit a distinct reason code, separable in post-trade
  analysis from a clean pass.
- The **kill switch**, when engaged, MUST block all *new* orders while still permitting
  cancellation logic to run.
- Hard limits (max position, max daily loss, max spread crossed, allowed symbols) live
  in this layer as deterministic code.

*Rationale: risk must be able to keep a strategy alive at a safe size, not only kill it —
but any silent alteration of intent must be observable, or "mystery PnL" follows.*

### VII. Venue Independence

The execution venue is accessed only through a strict abstraction. No venue-specific
detail may leak into strategy, risk, or data logic.

- Bybit (testnet) is the **provisional** development venue, not a commitment. Swapping to
  a Canada-legal real-money venue (e.g. Kraken/Coinbase) later MUST be a single-module change.
- Core logic MUST depend on the execution *interface*, never on a concrete adapter.

*Rationale: Bybit is not legally usable for real-money trading from Canada. The real-money
venue is a Phase-3 decision, and the architecture must keep that decision cheap.*

### VIII. Total Observability & Provenance

Every order **and every non-order decision** MUST be logged with a reason code and enough
context to reconstruct why it happened.

- Each decision record MUST include, at minimum: timestamp (UTC), venue, symbol, side,
  size, intended vs. executed price, fees, `strategy_version`, and `feature_snapshot_hash`.
- The raw data path MUST be append-only; fills are reconciled separately from intents.
- The ledger MUST capture the fields required for Canadian tax records (timestamp, pair,
  side, size, price, fees, CAD value) from the start, not retrofitted later.

*Rationale: without a decision-level audit trail you cannot separate "bad alpha" from "bad
execution," and reconstructing tax records after the fact is misery. Log what you would
wish you had during a failure review or an audit.*

### IX. Secrets and Safety Rails

Credentials and environment safety are not optional hygiene; they are constitutional.

- API keys and secrets MUST live in a git-ignored `.env` (or equivalent secret store),
  MUST NOT be committed, and MUST NOT appear in any log or decision record.
- The system MUST default to **testnet/paper** and require an explicit, deliberate
  override to point at any real-money venue. It MUST be impossible to place a real-money
  order by accident during Phase 1.
- Operational defaults MUST be conservative: idempotent client order IDs, exponential
  backoff on rate limits, and graceful degradation on venue errors.

*Rationale: one fat-fingered config should never be able to move real money, and one
committed key should never be possible in the first place.*

---

## Phase-1 Scope Constraints

The following are **out of scope** for Phase 1 and MUST NOT be introduced without an
explicit constitutional amendment or a Strategy & Roadmap decision:

- Multiple exchanges, leverage, margin, or derivatives.
- Cross-exchange or cross-venue arbitrage.
- LLMs or any AI in the live trade-decision path.
- Alternative data (satellite, weather, sentiment, etc.).
- Kafka, Redis, microservices, or other distributed infrastructure (local SQLite/Parquet
  is the Phase-1 store).
- The multi-agent orchestration system.

Phase 1 is: one pair (BTC/USD or ETH/USD), spot, one simple strategy, seconds-to-minutes
horizon, one venue (Bybit testnet), one environment.

---

## Development Workflow

- Work proceeds through the Spec-Driven flow: **constitution → specify → clarify → plan →
  tasks → analyze → implement.** Specifications are the source of truth; code is generated
  to satisfy them, not the reverse.
- `/speckit.clarify` and `/speckit.analyze` are quality gates, not optional steps. Because
  a defect here can silently misplace a real order, underspecification MUST be resolved
  before implementation, not during it.
- Each sprint's work is expressed as a `spec.md` + `tasks.md`, distinct from this
  constitution. This document holds durable principles only; it does not hold task lists.
- Adoption of this workflow is itself evaluated on evidence: if the process adds friction
  disproportionate to a component's size, that is a finding to raise, not a reason to
  abandon rigor silently.

---

## Governance

- This constitution supersedes all other project practices and artifacts on any point of
  conflict.
- Amendments MUST be explicit, dated, and recorded here, with the version incremented.
  Principles are not amended by drift or by in-session convenience.
- Every plan and task list produced by the workflow MUST be checkable against these
  principles; `/speckit.analyze` should treat a principle violation as a blocking finding.
- The Strategy & Roadmap chat is the authority for scope and direction decisions; this
  constitution is the authority for how the system is built.

**Version**: 1.0.0 | **Ratified**: 2026-07-10 | **Last Amended**: 2026-07-10
