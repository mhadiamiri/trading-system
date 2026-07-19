# WORK ORDER — WO-008b-A2: Live WebSocket + First Mainnet Contact (2-Minute Smoke Test)

**Status:** ACTIVE. Released by project lead. **This is the first live mainnet connection in this project's history.**
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.
**Baseline:** `0893c1a` — 111 collected, 103 passed, 8 xfailed, 0 failed, 0 xpassed.
import-linter 6 kept / 0 broken. Contract count 6/6. ruff clean.

═══════════════════════════════════════════════════════════════
STANDING RULES — permanent
═══════════════════════════════════════════════════════════════
- **0.1** Unspecified → STOP and ask.
- **0.1a** Any public interface signature change, any `object.__setattr__`,
  `# type: ignore`, monkey-patching, or mechanism whose purpose is to bypass a
  declared constraint is a STOP-and-ask event.
- **0.1b** No enforcement-class test may be `xfail`/`skip`/conditionally excluded
  without escalation.
- **0.1c** No `Mock`, stub, fake, or test double in production code paths.
- **0.1d** An enforcement test whose trigger cannot occur is a false guarantee.
  A bite proof must interact with the LIVE mechanism — not a copy, not a stale
  object, not its own string literal.
- **0.1e** Research artifacts are load-bearing: protocol claims cite vendor docs.
- **0.2** Blockers escalate, never work around.
- **0.4** Never weaken a guard, invariant, assertion, or threshold.
- **0.5 SECRETS — HEIGHTENED.** Kraken's public WebSocket requires NO API key, NO
  secret, NO authentication. If ANY step appears to need a credential, STOP
  IMMEDIATELY — that signals something is deeply wrong. Never print `.env`, never
  echo environment wholesale, never log connection headers. A credential leak
  occurred once on this project during a venue run.
- **0.6a** Evidence is redirected output. Prose may ANNOTATE, never CONSTITUTE.
- **0.6b** Every bite proof includes the unedited summary line WITH DURATION.
- **0.6c** Preflight gate: `git status --porcelain` with each line classified;
  `git worktree list` showing ONLY main; package path inside repo; baseline
  stated against SHA; both preflight guards OK.
- **0.6d** Fabricated evidence invalidates the ENTIRE work order.
- **0.7** Bite proofs EXECUTED: PASS, ACTUAL FAIL with real assertion text, PASS
  after restore, empty `git diff`, durations pasted.
- **0.8** Do not tune to green.
- **0.9** "I could not complete X" is a successful outcome.
═══════════════════════════════════════════════════════════════

## PART ONE — CLOSURE ITEMS (no network yet)

### 1.1 Threshold bite proof — the project lead's closure condition
A1b established the history (answer (a)); the closure condition is a bite proof
that drives the counter to 5 through the **CURRENT** resync path and shows the
escalation fire. Four artifacts:
- Run → paste PASS with duration.
- Break the escalation (e.g. reinstate the counter wipe inside the discard, or
  disable the threshold check) → **PASTE THE ACTUAL FAILING OUTPUT** with real
  assertion text.
- Restore → PASS. Paste empty `git diff`.
Assert both directions: 5 failures → escalation fires; 4 → does not.
Evidence → `evidence/WO-008b-A2/threshold_bite_proof.txt`

### 1.2 Decision log — two entries (pre-ruled)
1. *"Fabrication path existed: `get_market_data` invented a 10-level ladder and
   self-computed its checksum so validation would pass. Reachable from the
   production factory one config value away. Proven unreachable in all evidence
   runs; removed. Third artifact after the sequence field and the tautological
   guard test that would have let the system LOOK alive while disconnected from
   reality."*
2. *"Ordering fix would have silently disabled the 5-failure threshold via
   `reset_for_resync` zeroing the counter inside the discard. Fix-induced
   regression caught before shipping — the rationale for converting
   order-dependence and interaction detection from observation to mechanism."*

### 1.3 Declare pytest-randomly properly
It was installed as a dev tool only, not declared. A2's preflight requires
randomized ordering, so declare it as a dev dependency. Do NOT add to `addopts` —
default and CI behavior stay deterministic; randomization is invoked explicitly.

## PART TWO — IMPLEMENT THE LIVE CONNECTION

### 2.1 THE GOVERNING CONSTRAINT
**The WebSocket layer's ONLY job is transport.** Receive frame → hand the raw
message to the SAME entry point the raw-frame fixtures feed. Every proof built in
WO-009 and A1 — parse path, checksum ordering, `qty: 0` deletion, depth
truncation, counters — attaches to that code. A live-only parsing branch detaches
all of them.

**If you find you need ANY live-only parsing branch, that is a STOP-and-ask.**

Paste the call path showing live frames entering the shared entry point, AND log
it at runtime so the smoke output demonstrates live messages arriving through it.

### 2.2 Connection
- Kraken **public** WebSocket **v2** (the `WS_URL` constant corrected in A1).
  Unauthenticated. Paste the URL from source.
- Channel **book**, symbol **BTC/USD**, depth **10** (the pinned legal value).
- Handle snapshot and update messages per the v2 dict envelope.
- Adapter self-registers via the registry from WO-010. Confirm the loop never
  imports the adapter directly — import-linter must stay 6/6.

### 2.3 Counters at the proven positions
`raw_messages_received` at the parse boundary before any filtering/validation;
`market_states_emitted` at the yield. Same semantic positions proven in R2.

### 2.4 No silent fixture fallback
A failed connection RAISES. It must NEVER quietly replay fixtures. Mode is
explicit and logged at startup, and `venue_name` reports `kraken_mainnet` for
live (the A1 observability work must hold under real conditions).
**Bite proof, four artifacts:** force a connection failure, show the run fails
loudly rather than falling back.
Evidence → `evidence/WO-008b-A2/no_silent_fallback.txt`

### 2.5 Credential scan
    grep -rniE "api_key|apikey|secret|token|auth" src/trading/data/adapters/kraken_v2_book.py
Report and justify every hit, or confirm none. Confirm the connection sends no
authentication of any kind.

## PART THREE — PREFLIGHT GATE (before any socket opens)

Complete and paste ALL of this first. This is the full instrument check.

1. Clean tree, worktree list showing only main, package path inside repo.
2. **Full suite with RANDOMIZED ORDERING ACTIVE** (project lead's requirement).
   Today's evidence showed bite proofs can pass in isolation and fail in suite —
   the guards must be proven under the conditions that exposed that, not the ones
   that flattered it. Paste the seed and summary line with duration.
3. `import-linter` 6 kept / 0 broken; contract count 6/6; ruff clean.
4. Both preflight guards reporting OK.
5. **Bite proofs, four artifacts each:**
   - order-capable path unreachable under `TRADING_ENV=paper`
   - `Settings.validate()` mainnet guard (the real one from A1, not the
     tautological predecessor) + empty `git diff config/settings.py`
   - staleness guard: `EXEC_NO_MARKET_STATE` and `EXEC_STALE_MARKET_STATE`
6. Confirm `TRADING_ENV=paper` and no credentials present.

**GATE:** state *"PREFLIGHT COMPLETE — proceeding to live connection."* If any
item failed, STOP and report. Do not connect on a partial preflight.
Evidence → `evidence/WO-008b-A2/preflight.txt`

## PART FOUR — THE SMOKE TEST (2 MINUTES ONLY)

Symbol BTC/USD, depth 10, `TRADING_ENV=paper`, duration **2 minutes. Not 60.**

### 4.1 PASS CRITERIA — numbers pasted, not summarized
1. **Connection established** to the public v2 endpoint.
2. **Snapshot received and applied**, its checksum validated against Kraken's
   value.
3. **N incremental updates applied with EVERY checksum validated.** Report N,
   checksums attempted, passed, failed. Continuous validation is the point — a
   spot-check is not sufficient. **This is the only verification of the
   post-update ordering fix that exists anywhere**, since no fixture can prove it.
4. **At least one MarketState emitted end-to-end** through the shared pipeline.
5. **Clean disconnect.**

### 4.2 Also capture
Raw received, MarketStates emitted, sequence-free integrity events, reconnects,
staleness-guard firings, `venue_name` as recorded, and sample MarketStates with
real bid/ask.

**Do NOT report the 2-minute rate as a throughput result.** The <60s rate refusal
exists for this. Label any rate a smoke observation, not the 008b-B measurement.

### 4.3 PRE-RULED FAILURE INTERPRETATION — read before running
If checksums fail repeatedly: **assume the ordering defect first, not venue
instability.** Do NOT retry, do NOT tune, do NOT adjust the validation. STOP,
capture the raw frames, and diagnose against them offline. A feed that
"mostly works" after adjustment is exactly how a wrong ordering assumption
survives contact. Report the failure — a smoke test that fails and is diagnosed
honestly is a successful work order.

### 4.4 RETAIN THE RAW FRAMES — this is a durable deliverable
Capture the smoke window's raw frames **verbatim**, with Kraken's own checksums,
and retain them as a permanent fixture. This is the only route to genuine
ground truth for INCREMENTAL updates — Kraken documents a checksum for the
snapshot case only, so these captured frames permanently close the verification
gap that no constructed fixture can.
- Store under the fixtures directory, clearly labeled
  `# GROUND TRUTH: captured live from Kraken v2, <UTC timestamp>, run <id>`.
- Add at least one test replaying them through the parse path and validating
  Kraken's checksums.
- Redact nothing except anything credential-shaped (there should be none).
Evidence → `evidence/WO-008b-A2/captured_frames_fixture.txt`

## PART FIVE — VERIFY, COMMIT, PUSH
    pytest tests/ -rX
    import-linter lint
    python tools/contract_count_check.py
    ruff check .
Explain every test-count delta against `0893c1a`. Secret scan — and confirm no
captured frame, log, or evidence file contains a credential, token, or session
identifier. Push, paste local vs remote HEAD.

## PART SIX — FINAL REPORT — then STOP

1. **Threshold bite proof** — four artifacts with durations, both directions.
2. **Path identity** — paste the call path and the runtime log showing live
   frames entering the shared entry point. **Does ANY live-only parsing branch
   exist? YES/NO.**
3. Endpoint URL, channel, symbol, depth from source. Registry registration
   confirmed; import-linter still 6/6.
4. **No-silent-fallback bite proof** — four artifacts.
5. **Credential scan** — any authentication in the connection path? YES/NO.
6. **Preflight** — paste all of it, including the randomized-order suite run with
   its seed, and all four bite proofs. Confirm the gate statement preceded the
   connection.
7. **SMOKE RESULTS against all five §4.1 criteria** — each PASS/FAIL with numbers.
   Checksums attempted / passed / failed — state them explicitly.
8. **Did the post-update ordering fix hold against real Kraken data?** This is the
   question A1 could not answer and the reason this run exists. Answer it directly.
9. Staleness-guard firings, reconnects, `venue_name` as recorded.
10. **Captured frames retained?** Paste the fixture header and the replay test.
11. **Did any credential, token, or session ID appear in ANY output, log, evidence
    file, or captured frame?** YES/NO explicitly.
12. **Was any order placed at any venue?** YES/NO explicitly.
13. Paste Part Five verification with the test-count delta explained.
14. **Is any file in `evidence/WO-008b-A2/` prose standing in for output?** YES/NO.
15. **What did you change that you were not asked to change?** Every file, or "none."
16. **What could not be completed, and why?**

Do NOT run the 60-minute capture — that is WO-008b-B. STOP for human review.
The project lead reviews this report regardless of outcome.