# REPORT.md — Session Write-Back Format

> Claude Code writes a file named `REPORT.md` in the repo root after **every** work session, in the shape below. Hadi brings it to the relevant component chat (Ops / Data / Strategy & Research / Risk & Execution / Strategy & Roadmap) for review and redirection. Overwrite `REPORT.md` each session; prior reports live in git history.
>
> Three rules for writing it: (1) be concrete and skimmable — this is read, not admired; (2) never paste a secret, key, or raw credential, even redacted; (3) if progress would have required violating the constitution, it did **not** happen — record it under *Blocked / flagged* instead.

---

## Session

- **Date (UTC)**:
- **Feature / spec**: `specs/NNN-<slug>/` — branch `NNN-<slug>`
- **Spec-kit phase reached**: specify · clarify · plan · analyze · tasks · implement *(circle/keep the furthest reached)*
- **One-line status**: *(e.g. "Paper loop P1 running end-to-end on testnet; backtest costs stubbed, not yet real.")*

## 1. Summary

*2–4 sentences: what moved this session, in plain language.*

## 2. Tasks

Reference task IDs from `specs/NNN-<slug>/tasks.md`.

- **Completed**: T0xx — … ; T0xx — …
- **In progress**: T0xx — … *(what's left on it)*
- **Not started / blocked**: T0xx — … *(why)*

## 3. Constitution & gate status

Explicit PASS / FAIL / N/A per checkable invariant. A FAIL on any of these is a blocking finding, not a footnote.

| Check | Status | Note |
|---|---|---|
| `import-linter` green (risk/ has no ML import; strategy/risk/data/backtest don't import adapters) | | |
| Risk-layer unit tests pass (max position, max daily loss, kill switch, clamp-only-shrinks) | | |
| Every simulated trade includes fee + spread + slippage (no cost-free path) | | |
| Every order **and** non-order decision has a reason code | | |
| Provenance fields present (ts, venue, symbol, side, size, intended/exec price, fees, `strategy_version`, `feature_snapshot_hash`) | | |
| `TRADING_ENV` defaults to testnet; live connection refused without explicit override | | |
| No secret in git or in any log/decision record | | |
| Raw data path is append-only | | |
| `/speckit-analyze` run and clean (or: findings listed below) | | |

*Any FAIL above → describe it in §5.*

## 4. Decisions & rationale

- **Decision**: … — **why**: …
- **Deviation from plan/spec** (if any): … — **why it was necessary**: … *(deviations from the constitution are not listed here because they are not permitted — see §5)*

## 5. Blocked / flagged

- **Blocker / conflict**: … — **which chat should resolve it**: Data / Strategy & Research / Risk & Execution / Ops / Roadmap
- **Would-have-required-breaking-the-constitution**: *(what was asked, which principle it hit, what I did instead — i.e. stopped)*

## 6. Evidence & how to verify

- **Tests**: *(command + one-line result, e.g. `pytest -q` → 24 passed; `lint-imports` → clean)*
- **Run it**: *(exact commands to reproduce the loop / backtest)*
- **Artifacts**: *(paths only — e.g. `logs/2026-07-11.jsonl`, `data/btcusd/…parquet`, backtest P&L file). Never inline secrets or full log dumps.*

## 7. Open questions for Hadi

*Crisp and decision-oriented — each should be answerable with a choice.*

1. …
2. …

## 8. Proposed next session

- …
