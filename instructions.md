# WORK ORDER — WO-008b-A1: Local Defect Remediation + Raw-Frame Rewire (NO NETWORK)

**Status:** ACTIVE once WO-009b clears review. Precedes WO-008b-A2 (WebSocket + smoke test).
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.
**Baseline:** state it from WO-009b's closing commit.

═══════════════════════════════════════════════════════════════
STANDING RULES — permanent
═══════════════════════════════════════════════════════════════
- **0.1** Unspecified → STOP and ask.
- **0.1a** Any change to a public interface signature, any use of
  `object.__setattr__`, `# type: ignore`, monkey-patching, or any mechanism whose
  purpose is to bypass a declared constraint is a STOP-and-ask event.
- **0.1b** No test in a constitutional enforcement class may be marked `xfail`,
  `skip`, or conditionally excluded without escalation.
- **0.1c** No `Mock`, stub, fake, or test double in production code paths.
- **0.1d** An enforcement test whose trigger condition cannot occur in production
  is a false guarantee. A bite proof must INTERACT with the mechanism it certifies.
- **0.1e** Research artifacts are load-bearing: any claim about an external
  protocol, API, or venue behavior must cite vendor documentation at the point of
  claim. Uncited protocol claims may not flow into requirements.
- **0.2** Blockers escalate, never work around.
- **0.4** Never weaken a guard, invariant, assertion, or threshold.
- **0.5** Never print `.env` or any credential.
- **0.6a** Evidence is redirected output, never typed or reconstructed. Prose may
  ANNOTATE evidence, never CONSTITUTE it.
- **0.6b** Every bite proof includes the unedited summary line WITH DURATION.
- **0.6c** Preflight gate: `git status --porcelain` with every line classified
  exempt-(a) work-order file / exempt-(b) current evidence dir / UNEXPECTED;
  `git worktree list` showing ONLY the main tree; package path proven inside repo;
  baseline stated against its SHA; both preflight guards reporting OK.
- **0.6d** Any evidence later found fabricated invalidates the ENTIRE work order.
- **0.7** Bite proofs EXECUTED: PASS, ACTUAL FAIL with real assertion text, PASS
  after restore, empty `git diff`, durations pasted.
- **0.8** Do not tune to green.
- **0.9** "I could not complete X" is a successful outcome.
═══════════════════════════════════════════════════════════════

## SCOPE NOTE
The project lead released WO-008b-A as one unit. Ops has split it: A1 is all
local work with NO network; A2 is the WebSocket and first mainnet contact. This
follows the standing principle from the original 008a/008b split — first live
venue contact gets its own gate, not a bundle. Same total scope, one extra gate.

## OUT OF SCOPE — A2, not here
- **ANY NETWORK CONNECTION.** No WebSocket implementation, no socket to any
  venue, not "just to check." If something appears to require it, STOP and report
  BLOCKED — that is a success.
- Cost-unification (`backtest/costs.py`), Phase 9, Phase 10.
- CI config. (The CI error capture is Hadi's browser action, ruled for this week.)

## 1. FIX THE CHECKSUM ORDERING DEFECT

The implementation validates the checksum BEFORE applying the update (lines
~874-881); the update is applied at ~901. Per amended FR-018a, Kraken defines the
CRC32 over the **post-update book state**.

- Move validation to AFTER the update is applied.
- On mismatch, the **applied state is invalidated** — not merely the message.
- Implement the full ruled recovery: discard local book → resubscribe / request
  fresh snapshot → **emit NO MarketState from the moment of failure until a fresh
  snapshot is applied and its checksum validates.**
- Validate on **EVERY update**, never periodically.
- Set `BOOK_DEPTH` to the pinned value from the amended spec (10). `BOOK_DEPTH = 1`
  is not a legal Kraken depth and cannot hold the 10 levels the checksum requires.

**HONEST LIMIT — state this plainly in your report:** the snapshot checksum has
genuine Kraken ground truth (3310070434), but no fixture can verify the
INCREMENTAL post-update ordering, because a self-generated fixture encodes our
own ordering assumption on both sides of the comparison. This fix is verifiable
only at first live contact in A2. Do NOT manufacture a fixture that appears to
verify it.

Evidence → `evidence/WO-008b-A1/checksum_ordering.txt`

## 2. REMOVE THE Mock() — with retroactive re-certification

`kraken_v2_book.py:22` (`from unittest.mock import Mock`) and `:458`
(`self._log_error = Mock()`), committed `71eb901`, shipped through `43ca600`.
Every checksum-failure log has gone into a Mock and been discarded since — in
FIXTURE mode as well as live. FR-017 is unfulfilled in the shipped system.

- Remove the Mock; wire `_log_error` to the real logger at `:983`.
- **FR-017 bite proof (four artifacts):** force a checksum failure, show the log
  record is actually WRITTEN. Break the logging, show the test FAIL with real
  assertion text, restore, PASS, empty diff.
- **RETROACTIVE RE-CERTIFICATION (ruled):** re-run the FULL checksum-failure test
  class and show the log records now exist. This is the moment the Phases 1–3
  "proven to bite" claims get re-certified against a working alarm rather than a
  silenced one. Report whether any previously-passing test now behaves
  differently — if detection behavior was fine and only the evidence trail was
  dark, say so; if anything changed, that is a finding.
- The `no-test-doubles` import-linter contract should now go GREEN. Confirm
  6 kept / 0 broken and that `EXPECTED_CONTRACT_COUNT` remains 6.

Evidence → `evidence/WO-008b-A1/mock_removal_fr017.txt`

## 3. REPLACE THE TAUTOLOGICAL MAINNET-GUARD TEST

`test_settings_validate_blocks_mainnet` asserts substrings of its own local string
literal — it would pass against an empty repository, and it was the bite proof for
the single most safety-critical invariant in the codebase. Nothing has ever tested
that guard.

- Replace with a real bite proof: set `TRADING_ENV=paper`, attempt to construct an
  order-capable path, show it FAILS. Then set the mainnet condition and show
  `Settings.validate()` raises.
- Prove it bites: deliberately disable the guard → **PASTE THE ACTUAL FAILING
  OUTPUT** with real assertion text → restore → PASS → empty diff.
- The quarantined `test_order_guard_bite_proof.py` was identified as the better
  salvage candidate — use or adapt it if it helps; state what you reused.

Evidence → `evidence/WO-008b-A1/mainnet_guard_real_bite_proof.txt`

## 4. VENUE-MODE OBSERVABILITY

`venue_name` returns `"kraken_v2"` for `live_mode=True` and `False` alike, so a
LIVE RUN AND A FIXTURE REPLAY ARE INDISTINGUISHABLE IN THE DECISION LOG. That is a
Principle VIII defect: captured data whose provenance cannot be established is not
honest evidence.

- `venue_name` (or an accompanying provenance field) must distinguish live from
  fixture unambiguously — e.g. `kraken_mainnet` vs `kraken_fixture`.
- Mode must be logged at startup and carried into the decision log for every
  MarketState and every fill.
- **Bite proof (four artifacts):** a test asserting a fixture-mode run can never
  be recorded as live. Break it, show FAIL, restore, PASS, empty diff.

Evidence → `evidence/WO-008b-A1/venue_mode_observability.txt`

## 5. REWIRE FIXTURES TO RAW FRAMES

Per WO-009's rewire list: 13 `QuoteUpdate` construction sites (5 + 8), 5+
parse-path tests to add, 1 test to delete.

- Rewire all 13 sites to the raw v2 dict envelopes built in WO-009.
- **DELETE `test_sequence_gap_triggers_resnapshot`** — its trigger cannot occur
  (rule 0.1d: a false guarantee, not merely obsolete). Record the deletion in the
  report; do not xfail it.
- Add the parse-path tests: raw frame → parse → book application → MarketState.
  This is the code path that has never been under test.
- Remove the deprecated `QuoteUpdate` fixtures once nothing references them.
- **Exercise `qty: 0` deletion and depth truncation through the real parse path.**
- **DO NOT** xfail, skip, or weaken any test to accommodate the rewire. If a test
  breaks and the cause isn't an obvious wiring change, STOP AND REPORT — it may
  mean the test only ever passed because fixtures were shaped to it.

Evidence → `evidence/WO-008b-A1/raw_frame_rewire.txt`

## 6. RESOLVE THE FIVE BLOCKING IMPLEMENTATION DEFECTS

WO-009 identified five implementation defects blocking the rewire. Enumerate each
(file, line, what it is), then fix or report BLOCKED with reasoning. If any turns
out to require network work, that belongs to A2 — say so rather than reaching for it.

Evidence → `evidence/WO-008b-A1/blocking_defects_resolved.txt`

## 7. VERIFY, COMMIT, PUSH
    pytest tests/ -rX
    import-linter lint
    python tools/contract_count_check.py
    ruff check .
Expected: 6 kept / 0 broken (mock rule now green); contract count 6/6; F811 clean;
0 failed; 0 xpassed. Test count WILL change (deletion + new parse-path tests) —
state the new count, explain every delta against the prior baseline SHA, and
confirm no test was weakened to reach it. Secret scan, push, local vs remote HEAD.

## 8. FINAL REPORT — then STOP
1. **Checksum ordering** — paste before/after. Confirm post-update validation,
   every-update, and the no-emission window. State the honest limit: incremental
   ordering is unverifiable until A2's live contact.
2. **Mock removal** — paste the FR-017 bite proof (four artifacts) and the
   retroactive re-certification. Did any previously-passing test behave
   differently once the alarm worked? Confirm import-linter 6 kept / 0 broken.
3. **Mainnet guard** — paste the real bite proof, four artifacts. What did you
   reuse from the quarantined test?
4. **Venue mode** — paste the bite proof. Can a fixture run ever be recorded as
   live? Show the decision-log entry for each mode.
5. **Rewire** — all 13 sites converted? Paste the deleted test's removal. List the
   new parse-path tests. Did anything break unexpectedly?
6. **Five blocking defects** — enumerate each with disposition.
7. Paste §7 verification, all four commands, with the test-count delta explained.
8. **Did you open ANY network connection to any venue?** YES/NO explicitly.
9. **Is any file in `evidence/WO-008b-A1/` prose standing in for output?** YES/NO.
10. **What did you change that you were not asked to change?** Every file, or "none."
11. **What could not be completed, and why?**

Do NOT implement the WebSocket. Do NOT connect to anything. STOP for human review.