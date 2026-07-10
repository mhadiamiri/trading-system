# Spec-Kit Sprint-1 Runbook — Ops & Tooling

> **Pointer:** See the **Strategy & Roadmap** chat for the spec-kit adoption decision and rationale. This runbook is the Ops-side execution of that decision: init spec-kit, ratify the constitution, run exactly one loop on the Sprint-1 walking skeleton, and judge on evidence.

Verified against **spec-kit v0.12.9** (released 2026-07-09) with the **Claude** integration, by running `specify init` in a sandbox. Notes below reflect that ground truth, which differs from the older docs in two ways worth knowing.

## Ground-truth notes (read once)

- **Skills, not slash-commands.** The Claude integration installs spec-kit as **agent skills** under `.claude/skills/speckit-*`. You invoke them as `/speckit-constitution`, `/speckit-specify`, `/speckit-plan`, `/speckit-clarify`, `/speckit-tasks`, `/speckit-analyze`, `/speckit-implement` — **hyphen**, not the `/speckit.dot` form in the older README (that's the Copilot/generic syntax).
- **No competing `CLAUDE.md` is generated.** In this version + integration, `specify init` creates **no** root `CLAUDE.md` and **no** `CLAUDE-template.md`. Durable law lives in `.specify/memory/constitution.md`; the workflow logic lives in the skills. (More under "The two-CLAUDE.md decision".)
- **What init scaffolds:** `.specify/{memory/constitution.md, templates/*, scripts/bash/*, workflows/*, integrations/*}` and `.claude/skills/speckit-*`. Architecture/tech decisions have a defined home in the **plan** template (Technical Context + Constitution Check gate + Project Structure), not in any CLAUDE.md.

## Step 1 — Install the CLI (on Hadi's machine)

Recommended (persistent, per the README), with Claude Code already installed so agent-tool checks pass:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v0.12.9
# (pip alternative:)
# pip install "git+https://github.com/github/spec-kit.git@v0.12.9"
specify --version
```

## Step 2 — Initialize the repo

```bash
specify init trading-system --integration claude
cd trading-system
```

(If the directory already exists / is non-empty, use `specify init . --force --integration claude`. On a machine *without* the Claude CLI, add `--ignore-agent-tools`.)

Confirm the skills are present:

```bash
ls .claude/skills          # expect speckit-constitution, -specify, -plan, -tasks, -analyze, -implement, ...
```

## Step 3 — Ratify the constitution

The attached, ratified `constitution.md` (v1.0.0) **is** the source of truth. Drop it into the memory slot, replacing the placeholder:

```bash
cp /path/to/constitution.md .specify/memory/constitution.md
```

Verified: it replaces the placeholder cleanly (0 template tokens remain). Optionally run `/speckit-constitution` afterward and ask it only to *validate formatting and confirm the version block* — do **not** let it rewrite the principles; they are already ratified in the Strategy & Roadmap chat.

## The two-CLAUDE.md decision (recorded)

**There is no second `CLAUDE.md` to reconcile.** The tension the roadmap chat anticipated — spec-kit generating and managing its own `CLAUDE.md` that competes with our hand-written one — does not occur in v0.12.9's Claude/skills integration: init produces none. So the decision is simply where the *leftover detail* from our draft `CLAUDE.md` goes, and the answer follows the roadmap principle exactly:

- **Durable law** (the nine principles, scope, governance) → `.specify/memory/constitution.md`. *(Done in Step 3. This supersedes the draft's §1.)*
- **Architecture, repo layout, tech stack, logging & order-ID conventions** → the Sprint-1 **`plan.md`** (and its `data-model.md` for record/entity shapes, `contracts/` for the `Strategy` and `ExchangeClient` interfaces). The plan template has explicit slots for exactly this (Technical Context, Project Structure, Constitution Check).
- **The Sprint-1 task list** → generated `tasks.md` (never hand-coded into a CLAUDE.md — that separation is the whole point of adopting spec-kit).

**We do not hand-write a bespoke root `CLAUDE.md`.** This is a reversible call: if a live Claude Code session later needs a standing orientation pointer, add a *minimal* one that only points to `.specify/memory/constitution.md` and the active `specs/NNN-*/` — no architecture, no conventions, no task lists (those would duplicate the plan and drift, which is the exact failure we're avoiding). The draft `CLAUDE.md` from the earlier Ops session is now **retired**; its content is fully rehomed above.

## Step 4 — Specify the walking skeleton (the *what/why*, no tech)

Run `/speckit-specify` with this prompt. It should generate `specs/001-walking-skeleton/spec.md`; check that output against the reference `spec.md` produced in this chat.

```
/speckit-specify Build the walking skeleton of a systematic crypto trading system: the simplest thing that runs end-to-end. The system connects to a single crypto pair's live testnet market data feed, and on each update a strategy component turns the current market state into a desired position. Every desired position passes through a deterministic risk check that can pass it, shrink it toward zero, or reject it, and emits a distinct reason code for what it did. Approved orders go to a simulated (paper) execution path — no real money — which records the simulated fill. Every decision, including "no signal", "clamped", and "rejected", is written to a log with a reason code; silent decisions are not allowed. Separately, the same strategy-to-risk-to-execution logic can be run over previously stored market data as a backtest that applies trading fees, the bid/ask spread, and a realistic slippage/fill model to every simulated trade, producing a profit-and-loss result net of costs and a list of trades. Forecasting accuracy, if reported, is kept separate from tradable profit. Success for this phase is that the whole loop runs end-to-end and reports honest, cost-inclusive results even if the strategy loses money. The strategy itself is deliberately trivial (react to a short-term price move or a volume spike); sophistication is out of scope. Out of scope: multiple pairs or exchanges, leverage, real-money trading, any AI in the decision path, and alternative data.
```

## Step 5 — Clarify (required gate)

The constitution makes `/speckit-clarify` a quality gate, not optional (a defect here can silently misplace a real order later). Run it and resolve every `NEEDS CLARIFICATION` before planning.

```
/speckit-clarify
```

## Step 6 — Plan (the *how* — this is where the ex-CLAUDE.md detail lands)

Run `/speckit-plan` with the technical prompt below. This produces `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`.

```
/speckit-plan Implement in Python 3.11+, one repo, one codebase. Storage is local: SQLite and/or Parquet, append-only for raw market events — no Kafka or Redis. Tests with pytest. The provisional venue is Bybit testnet, reached only through a strict ExchangeClient interface with all Bybit-specific code confined to one adapter module (src/trading/execution/adapters/bybit_testnet.py) so swapping to a Canada-legal venue (Kraken/Coinbase) later is a one-module change; no venue-specific types may leak above the adapter. Enforce the four-layer import boundaries in CI with import-linter, wired into the test command so the build fails if risk/ imports any ML/AI library, or if strategy/, risk/, data/, or backtest/ import execution adapters. Repo layout: src/trading/{data,strategy,risk,execution,backtest,logkit,loop}; config in config/config.yaml; secrets only in a gitignored .env with .env.example holding names not values; raw events in data/ and logs in logs/, both gitignored; tests in tests/ including test_risk.py and test_backtest_costs.py. A TRADING_ENV flag defaults to "testnet" and the execution client refuses to open a live connection without an explicit, deliberate override. Execution operational defaults: idempotent client order IDs, exponential backoff on HTTP 429, graceful degradation on venue outage; the kill switch blocks new orders while still permitting cancellation logic. The risk engine is pure and deterministic (no I/O, no clock reads inside logic, no randomness) and returns pass/clamp/veto where a clamp only reduces size toward zero. Every decision record includes at minimum: UTC timestamp, layer, event_type, reason_code, venue, symbol, side, size, intended vs executed price, fees, strategy_version, and feature_snapshot_hash; the ledger additionally captures CAD value for Canadian tax records. Reason codes are a controlled vocabulary in the shape LAYER_VERB_DETAIL (e.g. RISK_CLAMP_MAX_POSITION, RISK_VETO_KILL_SWITCH, EXEC_ORDER_SUBMITTED, STRAT_NO_SIGNAL). No secret ever appears in a log line or decision record.
```

Expected `contracts/`: the `Strategy` interface (`decide(market_state) -> DesiredPosition`) and the `ExchangeClient` interface. Expected `data-model.md`: `MarketState`, `DesiredPosition`, `ApprovedOrder`, `DecisionRecord`, `Trade/Fill`.

## Step 7 — Analyze (required gate)

```
/speckit-analyze
```

Treat any constitution-principle violation as **blocking**. Do not proceed to tasks/implement until analyze is clean.

## Step 8 — Tasks, then implement

```
/speckit-tasks
/speckit-implement
```

`/speckit-implement` executes local CLI (pytest, pip, etc.), so the machine needs the toolchain. Output of this phase is **running code**, not more docs — that is what keeps this from becoming a stall.

## Step 9 — Write the report

After the session, Claude Code writes `REPORT.md` in the format defined in this chat (`REPORT.template.md`). Hadi brings it back to the relevant chat.

---

## The one guardrail — time-box

Run **exactly one** full loop (specify → clarify → plan → analyze → tasks → implement) on this Sprint-1 skeleton, then judge on evidence:

- If the ceremony earns its keep on something this small → keep the full flow.
- If it's friction → **keep the constitution and the plan artifacts, drop the heavier commands**, and say so in the report.

Adopting spec-kit must not become the new stall — that is this project's documented failure mode. The exit condition is running code with honest, cost-inclusive numbers, not a fuller set of planning documents.

## Deferred, not forgotten

The "wire Claude to talk to Claude Code directly" (MCP/connectors) workflow belongs in this Ops chat too — but as its **own thread after the skeleton exists**, not now.

## Back to Hadi

Once init + the two-CLAUDE.md decision are confirmed here, bring the result to the Strategy & Roadmap chat for a sanity-check against the roadmap **before** Sprint-1 coding starts — same supervise-and-validate loop as the CLAUDE.md.
