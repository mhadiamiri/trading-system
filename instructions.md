# WORK ORDER — WO-008a: Sprint 2 Phase 8, Integration & Loop Updates (FIXTURES ONLY)

**Status:** ACTIVE. Supersedes all previous instructions.
**Authority:** `.specify/memory/constitution.md` governs. If any instruction
conflicts with it, the constitution wins — STOP and escalate.
**Feature:** `specs/002-quote-level-data/` — Phases 1–7 (T001–T032) complete.
**Scope of THIS work order:** Phase 8 ONLY — tasks **T033–T036**
(integration & loop updates), wired and proven **on deterministic fixtures
and stored Parquet ONLY**.

## EXPLICITLY OUT OF SCOPE — DO NOT TOUCH

- **ANY LIVE NETWORK CONNECTION. THIS IS THE HARD LINE OF THIS WORK ORDER.**
  No Kraken WebSocket connection, no socket opened to any venue, not "just to
  check it connects," not for one second, not commented-out-and-run-once.
  The live run is WO-008b, a separately gated work order authorized by the
  project lead. If a task in T033–T036 appears to require a live connection
  to complete, that is a CORRECT finding — STOP, report it as BLOCKED with
  the task ID, and say what it needs. Reporting that blocker is a SUCCESS,
  not a failure. Working around it by opening a connection is a
  constitutional violation of this work order.
- Phase 9 (T037–T039) regression & validation — later WO, and gated behind
  a CI-green precondition.
- Phase 10 (T040–T041) docs & cleanup — later WO.
- CI / GitHub Actions debugging. CI is currently red (known, tracked
  separately). Do NOT attempt to fix it here. Do NOT modify
  `.github/workflows/`, `.gitignore`, `pytest.ini`, or `pyproject.toml`
  packaging config in this work order.
- `/speckit-implement` for the whole task list. T033–T036 only, then STOP.

## 0. RULES OF ENGAGEMENT

- **0.1 No discretion.** If unspecified, STOP and ask. No scope changes
  absorbed silently into code.
- **0.2 Blockers escalate, never work around.** Report which task, what
  blocks it, what you'd need. Reporting a blocker is a success.
- **0.3 Stay in scope.** T033–T036 only. No live run. No Phase 9–10 work.
- **0.4 Never weaken a guard or honesty property to simplify.** Any
  relaxation — of a guard, an invariant, a test's assertion, or a
  threshold — is a STOP-and-ask. This includes "temporarily."
- **0.5 Secrets:** never print/echo `.env` or any credential. Kraken public
  data requires NO API key. If any task appears to need a credential, STOP —
  that is a signal something is wrong.
- **0.6 Evidence, not assertion.** Paste command output and file content.
  "Verified" / "confirmed" / "works as expected" without pasted output is
  not evidence and will be rejected at review.
- **0.7 Negative proof is mandatory** where §2 states it: break it, run it,
  SHOW it fail, restore, SHOW it pass. Both directions pasted.
- **0.8 Do not tune to green.** A failing test is a BLOCKED report, not
  something to massage. Never adjust an assertion to match observed
  behavior — that inverts the purpose of the test.
- **0.9 Report per task ID:** DONE / BLOCKED / NOT DONE with evidence.

## 1. CONTEXT — WHY THIS WORK ORDER IS FIXTURES-ONLY

Phases 1–7 built and proved the pieces: the Kraken v2 L2 book adapter
(checksum reproducing Kraken's published 3310070434, sequence-gap detection,
5-failure recovery), quote processing, trades enrichment, the
observed-spread cost model with no synthetic fallback anywhere, and a
backtest that replays stored quotes and reconstructs spread from raw
bid/ask.

Phase 8 wires those pieces into the live trading loop. The project lead has
ruled that this integration is proven on fixtures FIRST, with a human gate,
and the actual mainnet contact happens separately in WO-008b. The reason is
specific and on the record: the one prior venue-contact run produced a
credential leak, a silently removed `TRADING_ENV=mainnet` guard, and a test
that asserted the wrong invariant. The review gate must be narrowest exactly
where we have already been burned. Bundling first-mainnet-contact into an
integration run widens that gate. Hence: your job is to make the loop
correct and provably safe while it is still impossible for it to touch a
venue.

## 2. THE NON-NEGOTIABLES THIS RUN MUST PROVE

### 2.1 The loop runs end-to-end on fixtures — Data → Strategy → Risk → Execution

Drive the integrated loop from a deterministic fixture/replay source and show
a complete pass through all four layers: MarketState produced from quote
data → strategy emits DesiredPosition → risk clamps/approves → paper
execution records the result with full costs (fee + observed spread +
slippage). Paste the run output showing at least one full cycle, including
the cost breakdown.

### 2.2 No order-capable path is reachable in paper mode — PROVEN, NOT ASSERTED

With `TRADING_ENV=paper`, the process must refuse to construct any
order-capable client. Prove it with a **negative test that attempts the
construction and asserts the failure**. Paste the test and its passing
output. Then prove the test bites: temporarily weaken the guard so
construction succeeds → run the test → **SHOW IT FAIL** → restore →
**SHOW IT PASS**. Paste both directions.

This is the direct mitigation for a known prior failure. Do not skip it, and
do not substitute a manual inspection for the negative test.

### 2.3 The mainnet guard in `Settings.validate()` is INTACT

Show the current source of the `TRADING_ENV` mainnet block in
`Settings.validate()`. Confirm it is present and unmodified. Then show
`git diff` for `settings.py` across this work order — if it is non-empty,
justify every line. **If you find the guard is already missing or weakened
from prior work, STOP and report it immediately as a finding.** Do not
silently restore it and do not silently proceed.

### 2.4 The instrumentation for WO-008b's threshold exists and is correct

WO-008b must measure throughput against a ruled threshold of **sustained
≥60 MarketStates/min**, and the project lead requires two counters recorded
**separately**:
  - **raw book updates RECEIVED** from the feed
  - **MarketStates EMITTED** by the pipeline

The reason they must be separate is diagnostic: if raw is high but emitted is
low, the constraint is our own pipeline (coalescing/throttling), not the
venue — and those two have opposite remedies. Conflating them is what made
the Bybit diagnosis slow.

In THIS work order, build and prove that instrumentation on fixtures:
  - Both counters exist, are incremented at the correct points, and are
    reported as rates per minute alongside absolute counts.
  - Prove correctness with a fixture of KNOWN size: feed N known raw updates,
    show received == N, and show emitted matches the pipeline's expected
    output count. Paste input count and reported output.
  - The counters must be reportable at the end of a run without requiring a
    live connection.

Do NOT hardcode, assume, or simulate a throughput number anywhere. The
threshold is evaluated in WO-008b against real measured data.

## 3. CONSUMERS & BOUNDARY

- **xfail cleanup.** Any consumer updated in this phase must have its
  `xfail` marker REMOVED and the test PASS for real — not deleted, not left
  xfail'd. Report which xfails now pass and which remain, with the phase
  that will clear each.
- **Boundary intact.** After all changes, run import-linter. Confirm all 4
  contracts still active and green, and paste the output. The deep order
  book must not leak above the adapter.
- **Strategy interface unchanged** — `decide(market_state) -> DesiredPosition`.
  No strategy-logic changes in this work order.
- **Risk layer contains no AI/ML** — unchanged and verified by the existing
  contract.

## 4. TASKS

Execute **T033–T036** in the order given in
`specs/002-quote-level-data/tasks.md`. Honor §2 and §3 throughout. Commit at
sensible points with clear messages. No live connection. Do not proceed
past T036.

## 5. FINAL REPORT — then STOP

Report per task (T033–T036): DONE / BLOCKED / NOT DONE with evidence. Then
answer these directly:

1. **§2.1** — Paste a full Data→Strategy→Risk→Execution cycle on fixtures,
   with the cost breakdown (fee + observed spread + slippage).
2. **§2.2** — Paste the negative test for order-capable construction under
   `TRADING_ENV=paper`, and BOTH directions of the bite proof (weakened →
   FAIL, restored → PASS).
3. **§2.3** — Paste the current `Settings.validate()` mainnet guard source
   and the `git diff` for `settings.py`. Is the guard intact?
4. **§2.4** — Paste proof that raw-received and emitted counters are separate
   and correct against a known-size fixture. Show the per-minute rate
   reporting format WO-008b will use.
5. **§3** — Which xfails now pass for real, which remain? Paste import-linter
   output — is it 4/4 green?
6. **Did you open ANY network connection to any venue during this work
   order?** Answer yes or no explicitly.
7. **What, if anything, did you have to decide that wasn't specified?**
   List it and ask.
8. **What did you change that you were not asked to change?** List every
   file touched outside the scope of T033–T036, with justification, or
   state "none."

Do NOT run Phase 9–10. Do NOT open a live connection. Do NOT touch CI
config. STOP for human review before WO-008b.
------------------------------------------------------------

fixes:

# WORK ORDER — WO-008a-R3: Complete Phase 8 Integration + Commit/Push Everything

**Status:** ACTIVE. Blocks WO-008b until closed.
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.

## WHY THIS EXISTS

WO-008a-R2 was an honest report and closed BLOCKER 1, BLOCKER 3, and ITEM 4.2.
Its Item 4.1 finding revealed something larger:

- WO-008a reported "§2.1 PROVEN — Complete Data → Strategy → Risk → Execution
  cycle on fixtures" and marked T033–T036 DONE. Item 4.1 shows the Strategy and
  RISK steps were NEVER OBSERVED, and end-to-end tests are XFAILED with
  "Consumer update scheduled T036" — i.e. T036 is not actually complete.
- Phase 8 IS the integration phase. Its integration is undemonstrated.
- All WO-008a / R / R2 work is UNCOMMITTED. `git log -15` shows WO-007 as latest.

This WO does two things: (1) actually complete and demonstrate Phase 8
integration on fixtures, (2) get everything committed and pushed.

**Reporting a task incomplete is a SUCCESS. Reporting it DONE when its tests are
xfailed pending that same task is the failure mode we are eliminating.**

## OUT OF SCOPE
- **ANY LIVE NETWORK CONNECTION.** Unchanged hard line. That is WO-008b. If an
  item appears to require it, STOP and report BLOCKED — that is a success.
- Phase 9 (T037–T039), Phase 10 (T040–T041).
- New features beyond completing T033–T036 as specified in tasks.md.
- Do not modify `.github/workflows/`, `pytest.ini`, or `pyproject.toml`.
  (`.gitignore` may be inspected but not changed without reporting first.)

## 0. RULES OF ENGAGEMENT
- **0.1** Unspecified → STOP and ask.
- **0.2** Blockers escalate, never work around.
- **0.4** Never weaken a guard, invariant, assertion, or threshold.
- **0.5** Never print `.env` or any credential.
- **0.6** EVIDENCE = redirected output committed under `evidence/WO-008a-R3/`,
  then `cat` and pasted. No prose standing in for output.
- **0.8** DO NOT TUNE TO GREEN. Specifically: do NOT clear an xfail by deleting
  the test, by weakening its assertions, or by marking it skip. An xfail is
  cleared ONLY by making the real behavior work.
- **0.9** "I could not complete X" is a successful outcome. A false DONE is not.

## 1. STEP ONE — COMMIT AND PUSH EVERYTHING (do this FIRST)

All prior work is uncommitted. Do this before any new code so the baseline is
recoverable and CI can be evaluated against reality.

    mkdir -p evidence/WO-008a-R3
    git status --short              > evidence/WO-008a-R3/pre_commit_status.txt 2>&1
    git log --oneline -15           > evidence/WO-008a-R3/pre_commit_log.txt 2>&1
    cat evidence/WO-008a-R3/pre_commit_status.txt
    cat evidence/WO-008a-R3/pre_commit_log.txt

Then, BEFORE committing, verify no secrets are staged:
    git add -A
    git diff --cached --name-only > evidence/WO-008a-R3/staged_files.txt 2>&1
    git diff --cached --name-only | grep -Ei '\.env|secret|credential|\.key|\.pem|apikey|api_key' \
        > evidence/WO-008a-R3/secret_scan.txt 2>&1 || echo "clean — no secrets staged" \
        > evidence/WO-008a-R3/secret_scan.txt
    cat evidence/WO-008a-R3/staged_files.txt
    cat evidence/WO-008a-R3/secret_scan.txt

If ANY secret-looking file is staged, STOP and report immediately. Do not commit.

Then commit and push:
    git commit -m "WO-008a/R/R2: Phase 8 integration work, proof remediation, evidence artifacts"
    git push
    git log --oneline -5            > evidence/WO-008a-R3/post_push_log.txt 2>&1
    git status -sb                  > evidence/WO-008a-R3/post_push_status.txt 2>&1
    echo "local  HEAD: $(git rev-parse HEAD)"   >> evidence/WO-008a-R3/post_push_status.txt
    echo "remote HEAD: $(git ls-remote origin -h refs/heads/$(git branch --show-current) | awk '{print $1}')" \
        >> evidence/WO-008a-R3/post_push_status.txt
    cat evidence/WO-008a-R3/post_push_status.txt

**The local and remote HEAD hashes MUST match.** If they differ, the push did
not land — paste the full push output and STOP. This is likely the root cause of
the persistent CI failure, so this evidence matters.

Report the CI run result triggered by this push. Do NOT attempt to fix CI in
this work order — just report what it now says.

## 2. STEP TWO — COMPLETE T036 FOR REAL

Per `specs/002-quote-level-data/tasks.md`, T036 updates consumers for the new
quote-centric MarketState schema. Tests are currently xfailed with
"Consumer update scheduled T036."

Required:
- Update every consumer that the xfail markers point at so it works against the
  new schema (the noted case is strategy using `volume_24h`; find and handle ALL
  of them).
- Remove those xfail markers and make the tests PASS for real. Not deleted, not
  skipped, not weakened.
- The strategy interface stays `decide(market_state) -> DesiredPosition`.
- The risk layer contains no ML — unchanged.

Evidence:
    pytest tests/ -v -rxX > evidence/WO-008a-R3/t036_tests.txt 2>&1
    cat evidence/WO-008a-R3/t036_tests.txt

Report: which xfails were cleared (by name), which remain, and for each
remaining one the specific task/phase that will clear it. If a marker cannot be
cleared, say so and explain why — do not remove it to make the count look good.

## 3. STEP THREE — DEMONSTRATE THE FULL LOOP (this is the deliverable)

Produce an observable, end-to-end run on fixtures showing ALL FOUR layers acting
on the same tick. This is what WO-008a claimed and never delivered.

Run with `-v -s` so program output is captured:
    pytest tests/integration/test_live_loop.py -v -s \
        > evidence/WO-008a-R3/end_to_end_full_cycle.txt 2>&1
    cat evidence/WO-008a-R3/end_to_end_full_cycle.txt

The output must show, AS THE PROGRAM PRINTED IT, for at least one complete cycle:
1. **DATA** — MarketState with best_bid, best_ask, spread, mid_price (real values,
   no corrupted characters).
2. **STRATEGY** — the DesiredPosition emitted, with its side and size.
3. **RISK** — the risk decision ACTUALLY INVOKED: input size, output size, and
   whether it clamped, approved, or vetoed, with the reason. This is the step
   that has never been observed. "Through existing integration" is not evidence.
4. **EXECUTION** — the paper fill with the full cost breakdown: fee, observed
   spread cost, slippage, total.

If the loop needs print/logging to make this observable, add it to the TEST or
use existing structured logging — do NOT add debug prints to production code
paths. State exactly what you added.

**Also prove the clamp-only-shrinks invariant holds in this cycle** (Principle
VII): the risk layer's output size must be between zero and the requested size,
same sign, never flipped. Show the numbers.

If the full cycle STILL cannot be demonstrated after completing T036, STOP and
report precisely which layer cannot be exercised and why. That is a legitimate
outcome and goes to the project lead — it means Phase 8 has an unmet dependency.

## 4. STEP FOUR — RE-VERIFY AND COMMIT

    import-linter lint    > evidence/WO-008a-R3/import_linter.txt 2>&1
    pytest tests/ -rX     > evidence/WO-008a-R3/final_tests.txt 2>&1
    cat evidence/WO-008a-R3/import_linter.txt
    cat evidence/WO-008a-R3/final_tests.txt

Requirements: 4/4 contracts kept, 0 xpassed, no test weakened to achieve it.

Then commit and push all of Step 2–4, and again show matching local/remote HEAD.

## 5. FINAL REPORT — then STOP

For each item: DONE / BLOCKED / NOT DONE, with evidence filename and pasted
contents.

1. **Commit/push:** paste pre-status, post-push log, and the local vs remote HEAD
   hashes. Do they match? What does CI now report?
2. **T036:** which xfails cleared by name, which remain and why. Paste test output.
3. **Full loop:** paste the four-layer cycle output. Was the RISK layer actually
   invoked — YES or NO? Paste the clamp-only-shrinks numbers.
4. **Was WO-008a's original claim that T036 was DONE accurate?** Answer plainly.
   This is not a trap — an accurate "no, it was reported complete prematurely" is
   the correct answer and closes the loop honestly.
5. Paste import-linter (4/4?) and final pytest summary (0 xpassed?).
6. **Did you open ANY network connection to any venue?** YES/NO explicitly.
7. **What did you change that you were not asked to change?** Every file, with
   justification, or "none."
8. **What could not be proven or completed, and why?** Be specific.

Do NOT proceed to WO-008b. STOP for human review.