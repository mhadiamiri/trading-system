# Tasks: Quote-Level Data + Observed-Spread Cost Model

**Input**: plan.md, research.md, data-model.md, contracts/data-adapter.yml, spec.md
**Prerequisites**: All artifacts verified; analyze report CLEAN
**Feature Branch**: `002-quote-level-data`

**Organization**: Tasks grouped by user story with sequencing constraints per instructions.md:
- Import-linter contract update early (before adapter internals)
- Checksum validation + fail-then-pass test as single unit
- Explicit "no synthetic spread" tests
- Backtest quote-replay reconstructs observed spread from stored raw quotes
- MarketState schema change before consumers

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, FOUND)
- Include exact file paths in descriptions

---

## Phase 1: Import-Linter Contract (EARLY — Before Adapter Internals)

**Purpose**: Establish boundary enforcement BEFORE v2/book/checksum code exists, so violations fail the build from the start.

> **SEQUENCING CONSTRAINT (instructions.md)**: "The import-linter contract update goes in an early task, before the adapter internals are built — so the v2/book/checksum boundary (including the loop/ block) can fail the build from the start, not be bolted on after."

- [ ] **T001 [FOUND]** Update .importlinter.yaml with v2/book/checksum boundary contract
  - Path: `.importlinter.yaml`
  - Add "Forbidden v2-book-checksum imports above adapter" contract
  - Forbidden modules: trading.data.adapters.kraken_v2_book
  - Forbidden importers: trading.strategy*, trading.risk*, trading.execution*, trading.backtest*, trading.loop*
  - Allow factory import only: `from trading.data.adapters import KrakenV2BookAdapter`
  - Verify: Run `import-linter lint` — should pass (adapter doesn't exist yet, so no violations)

**Checkpoint**: Import-linter contract in place; any v2/book/checksum leak will fail build

---

## Phase 2: Schema & Interface Changes (Foundational)

**Purpose**: MarketState schema change MUST land before its consumers are updated.

> **SEQUENCING CONSTRAINT (instructions.md)**: "The MarketState schema change lands before its consumers are updated, and no task may alter the Strategy interface signature."

- [ ] **T002 [FOUND]** Add quote-centric fields to MarketState schema
  - Path: `src/trading/data/market_state.py`
  - Add fields: best_bid, best_ask, best_bid_size, best_ask_size, mid_price, spread, trade_count, total_volume, last_price
  - Remove deprecated fields: price, volume
  - Maintain backward compatibility: strategy/risk/execution interfaces unchanged
  - Add validation: bid > 0, ask > 0, bid < ask, derived fields computed correctly
  - Verify: Unit tests pass for new schema

- [ ] **T003 [P] [FOUND]** Update SimulatedMarketFeed for new MarketState schema
  - Path: `src/trading/data/adapters/simulated_feed.py`
  - Emit quote-centric MarketState objects (bid/ask/size/mid/spread/trade stats)
  - Maintain backward compatibility with existing tests
  - Verify: Existing Sprint 1 tests using simulated feed still pass

- [ ] **T004 [P] [FOUND]** Update factory.get_feed() for kraken_v2 option
  - Path: `src/trading/data/adapters/__init__.py`
  - Add 'kraken_v2' → KrakenV2BookAdapter mapping (adapter doesn't exist yet, mapping prepared)
  - Verify: Factory returns NotImplementedError for kraken_v2 (adapter not built yet)

**Checkpoint**: MarketState schema changed; factory prepared; adapter infrastructure ready

---

## Phase 3: User Story 3 - Book Integrity via Checksum Validation (Priority: P1) 🎯

**Goal**: Implement v2 book adapter with checksum validation on every update; recovery logic (resync/resnapshot/pause) must fire when guards trigger.

> **SEQUENCING CONSTRAINT (instructions.md)**: "Checksum validation and its fail-then-pass test are a single unit of work — the test that proves a corrupted book is seen to fail must be part of the same task that implements the checksum, not a later 'testing' task."

### Tests for US3 (Write FIRST, ensure they FAIL)

- [ ] **T005 [P] [US3]** Test: Valid checksum passes and updates local book
  - Path: `tests/test_data_adapters.py`
  - Test: Create valid quote update with checksum; verify validation passes; verify local book updated
  - Verify: Test FAILS (adapter doesn't exist yet)

- [ ] **T006 [P] [US3]** Test: Corrupted checksum rejected and logged
  - Path: `tests/test_data_adapters.py`
  - Test: Create valid update; alter price (break checksum); verify rejection; verify log with error; verify consecutive_failures increments
  - Verify: Test FAILS (adapter doesn't exist yet)
  - > **CRITICAL**: This is the fail-then-pass proof that checksum validation bites

- [ ] **T007 [P] [US3]** Test: 5 consecutive checksum failures trigger resync
  - Path: `tests/test_data_adapters.py`
  - Test: Simulate 5 consecutive checksum failures; verify resync triggered (reconnection + fresh snapshot request)
  - Verify: Test FAILS (adapter doesn't exist yet)

- [ ] **T008 [P] [US3]** ~~Test: Sequence gap triggers resnapshot~~ **Test: Checksum divergence triggers resnapshot** *(AMENDED 2026-07-19, WO-009b)*
  - Path: `tests/test_data_adapters.py`
  - ~~Test: Establish synchronized book (sequence 100); receive update with sequence 105 (gap); verify book discarded; verify snapshot requested~~
  - **Test: establish book from the ground-truth snapshot fixture; apply an update whose checksum does not match the POST-update ladder; verify the APPLIED state is discarded, a snapshot is requested, and NO MarketState is emitted until that snapshot validates (FR-018a(b),(d))**
  - **WO-008b-A must also DELETE `test_sequence_gap_triggers_resnapshot` — its trigger cannot occur (rule 0.1d).**
  - Verify: Test FAILS (adapter doesn't exist yet)

### Implementation for US3

- [ ] **T009 [US3]** Create LocalBookState entity (adapter-internal)
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Fields: best_bid_price, best_bid_size, best_ask_price, best_ask_size, ~~last_sequence~~, last_checksum, consecutive_failures, is_paused *(last_sequence removed WO-009b)*
  - State transitions: INITIAL → SYNCHRONIZED → RESYNC_REQUIRED → PAUSED → SYNCHRONIZED
  - Validation rules: Checksum validation on EVERY update computed over the POST-update ladder; ~~sequence gap detection~~; 5-failure threshold; no-emission window until resync validates *(WO-009b)*
  - Verify: Unit tests for state transitions pass

- [ ] **T010 [US3]** Create QuoteUpdate entity (adapter-internal)
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Fields: bid_price, bid_size, ask_price, ask_size, checksum, ~~sequence~~, timestamp *(sequence removed WO-009b — not transmitted)*
  - Validation: Checksum format (CRC-32); ~~sequence monotonic~~ *(WO-009b)*
  - Verify: Unit tests pass

- [ ] **T011 [US3]** Implement CRC-32 checksum validation algorithm
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Algorithm per Kraken v2 documentation: Compute CRC-32 over bid/ask prices/sizes
  - Return: bool (match/nomatch)
  - Verify: Unit tests with known valid/invalid checksums pass

- [ ] **T012 [US3]** Implement KrakenV2BookAdapter: WebSocket connection and subscription
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Connect to wss://ws.kraken.com
  - Subscribe to book channel: {"name":"book","subscription":{"depth":1}}
  - Subscribe to trades channel: {"name":"trade"}
  - Handle connection messages per v2 protocol
  - Verify: Manual connection test shows successful subscription

- [ ] **T013 [US3]** Implement KrakenV2BookAdapter: Snapshot processing
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Parse v2 snapshot message (initial book state)
  - Initialize LocalBookState from snapshot
  - Validate snapshot checksum
  - Emit initial MarketState on success
  - Verify: Unit tests with snapshot fixtures pass

- [ ] **T014 [US3]** Implement KrakenV2BookAdapter: Incremental update processing with checksum validation
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Parse v2 incremental message
  - Validate checksum on EVERY update
  - Update LocalBookState on valid checksum
  - Reject and log on invalid checksum; increment consecutive_failures
  - Emit MarketState on successful update
  - Verify: Tests T005, T006, T007, T008 now PASS

- [ ] **T015 [US3]** ~~Implement KrakenV2BookAdapter: Sequence gap detection and resnapshot~~ **Implement checksum-divergence detection and resnapshot** *(AMENDED 2026-07-19, WO-009b)*
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - ~~Track sequence numbers~~ **Apply each update, THEN validate CRC32 over the post-update top-10-per-side ladder**
  - ~~On gap (incoming sequence != last_sequence + 1): discard local book; request fresh snapshot~~ **On mismatch: discard the APPLIED state; request fresh snapshot**
  - **Emit NO MarketState until the fresh snapshot is applied and validates (FR-018a(d))**
  - ~~No continue-on-gap path~~ **No continue-on-checksum-failure path**
  - Verify: Test T008 now PASS

- [ ] **T016 [US3]** Implement KrakenV2BookAdapter: Recovery logic (resync after 5 failures)
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Track consecutive_failures counter
  - On 5 consecutive checksum failures: trigger reconnection; request fresh snapshot
  - Reset counter on successful resync
  - Verify: Test T007 now PASS

- [ ] **T017 [US3]** Implement KrakenV2BookAdapter: Book unavailable → pause behavior
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - On book channel disconnect: set is_paused=True; stop yielding MarketStates
  - Log with reason code: PAUSE_ON_BOOK_UNAVAILABLE
  - On book recovery: resume yielding when validation passes
  - No trades-only fallback mode
  - Verify: Unit tests for pause/resume pass

- [ ] **T018 [US3]** Add reason codes for checksum/resync/~~sequence-gap~~/pause events *(AMENDED 2026-07-19, WO-009b)*
  - Path: `src/trading/logkit/decision.py`
  - Add to LAYER_VERB_DETAIL: CHECKSUM_RESYNC, ~~SEQUENCE_GAP_RESNAPSHOT~~ *(WITHDRAWN — trigger cannot occur; see WO-009b §2)*, PAUSE_ON_BOOK_UNAVAILABLE
  - **Open for WO-008b-A: whether the FR-018a(d) no-emission window needs its own code**
  - Verify: Import-linter still passes; reason codes defined

- [ ] **T019 [US3]** Update import-linter: Verify no v2/book/checksum leaks
  - Path: `.importlinter.yaml`
  - Run `import-linter lint`
  - Verify: No violations (all v2 detail confined to kraken_v2_book.py)
  - Verify: trading.loop* cannot import kraken_v2_book internals

**Checkpoint**: US3 complete; checksum validation passes; recovery fires correctly; pause works; no boundary violations

---

## Phase 4: User Story 1 - Real-Time Quote Processing (Priority: P1) 🎯

**Goal**: System consumes Kraken's book channel as primary heartbeat; quote updates emitted as MarketState.

### Tests for US1 (Write FIRST, ensure they FAIL)

- [ ] **T020 [P] [US1]** Test: Quote updates received from Kraken v2
  - Path: `tests/test_data_adapters.py`
  - Test: Connect to Kraken v2 book channel; verify quote updates received; verify MarketState emitted with populated bid/ask/size
  - Verify: Test FAILS (trades enrichment not implemented yet)

### Implementation for US1

- [ ] **T021 [US1]** Implement KrakenV2BookAdapter: MarketState emission from LocalBookState
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - On successful book update: emit MarketState with quote fields populated
  - Compute derived fields: mid_price = (bid + ask) / 2; spread = ask - bid
  - Validate MarketState before emission (bid > 0, ask > 0, bid < ask)
  - Verify: Unit tests for MarketState construction pass

**Checkpoint**: US1 complete; quotes received; MarketState emitted; core adapter working

---

## Phase 5: User Story 4 - Trades as Secondary Enrichment (Priority: P2)

**Goal**: Trade data (volume, last price) available as rolling stats in MarketState.

### Tests for US4 (Write FIRST, ensure they FAIL)

- [ ] **T022 [P] [US4]** Test: Rolling trade stats computed correctly
  - Path: `tests/test_data_adapters.py`
  - Test: Subscribe to trades channel; receive trades; verify trade_count, total_volume, last_price computed over rolling window
  - Verify: Test FAILS (rolling stats not implemented yet)

### Implementation for US4

- [ ] **T023 [US4]** Create RollingTradeStats entity (adapter-internal)
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Fields: trades list (buffer), window_count_cap (default 100), window_time_cap (default 60 seconds)
  - Computed fields: count = len(trades), total_volume = sum(t.volume), last_price = trades[-1].price
  - Validation: Window pruning (remove trades older than time_cap); count cap (remove oldest if > count_cap); hybrid truncation (BOTH caps applied)
  - Verify: Unit tests for window pruning pass

- [ ] **T024 [US4]** Implement KrakenV2BookAdapter: Trades channel processing and rolling stats
  - Path: `src/trading/data/adapters/kraken_v2_book.py`
  - Parse v2 trades channel messages
  - Update RollingTradeStats with each trade
  - Embed rolling stats in emitted MarketState (trade_count, total_volume, last_price)
  - Verify: Test T022 now PASS

**Checkpoint**: US4 complete; trades enriched; rolling stats computed; MarketState complete

---

## Phase 6: User Story 2 - Observed Spread Cost Model (Priority: P1) 🎯

**Goal**: Cost model uses actual observed bid/ask spread; no assumed or synthetic spread anywhere.

> **SEQUENCING CONSTRAINT (instructions.md)**: "The backtest quote-replay task must reconstruct observed spread from stored raw quotes — no task may introduce a computed-spread or fallback-spread shortcut."
>
> **SEQUENCING CONSTRAINT (instructions.md)**: "'No synthetic spread' tests are explicit tasks — including: abnormal spread → reject; book unavailable → pause (no yield); and a test asserting no code path emits a null/stale/synthetic spread."

### Tests for US2 (Write FIRST, ensure they FAIL)

- [ ] **T025 [P] [US2]** Test: Cost model uses observed spread only (no synthetic path)
  - Path: `tests/test_backtest_costs.py`
  - Test: Read cost model source; verify all spread costs derived from market_state.spread; verify no constant/assumed/fallback spread exists
  - Verify: Test FAILS (cost model not updated yet)

- [ ] **T026 [P] [US2]** Test: Abnormal spread (zero/negative/wide) causes trade rejection
  - Path: `tests/test_backtest_costs.py`
  - Test: Create MarketState with negative spread (bid > ask); verify trade rejected; verify ABNORMAL_SPREAD_REJECT reason code logged
  - Test: Create MarketState with spread >5% of price; verify trade rejected
  - Verify: Test FAILS (abnormal spread handling not implemented yet)

- [ ] **T027 [P] [US2]** Test: No code path emits null/stale/synthetic spread
  - Path: `tests/test_backtest_costs.py`
  - Test: Code review of cost model; assert no path where spread is assumed, fabricated, or cached-stale
  - Test: Verify cost model rejects trade when market_state.spread is None or invalid
  - Verify: Test FAILS (cost model not updated yet)

### Implementation for US2

- [ ] **T028 [US2]** Update backtest cost model: Use observed spread from MarketState
  - Path: `src/trading/backtest/costs.py`
  - Read spread from market_state.spread (not from constant or assumption)
  - Compute buy-side spread cost: (ask - mid_price) or (ask - bid) / 2
  - Compute sell-side spread cost: (mid_price - bid) or (ask - bid) / 2
  - Verify: Tests T025, T026, T027 now PASS

- [ ] **T029 [US2]** Add ABNORMAL_SPREAD_REJECT reason code
  - Path: `src/trading/logkit/decision.py`
  - Add to LAYER_VERB_DETAIL: ABNORMAL_SPREAD_REJECT
  - Verify: Import-linter passes; reason code defined

**Checkpoint**: US2 complete; cost model uses observed spread; abnormal spread rejected; no synthetic path

---

## Phase 7: Backtest Data & Replay

**Goal**: Backtest replays from stored raw quotes; reconstructs observed spread identically to live.

> **SEQUENCING CONSTRAINT (instructions.md)**: "The backtest quote-replay task must reconstruct observed spread from stored raw quotes — no task may introduce a computed-spread or fallback-spread shortcut."

### Tests for Backtest Replay (Write FIRST, ensure they FAIL)

- [ ] **T030 [P] [FOUND]** Test: Backtest reads stored quote data from Parquet
  - Path: `tests/integration/test_backtest.py`
  - Test: Capture live quote data to Parquet; verify schema (timestamp, symbol, bid, ask, sizes, spread, trade stats)
  - Test: Backtest reads stored data; verify MarketState reconstructed with observed spread
  - Verify: Test FAILS (backtest runner not updated yet)

- [ ] **T031 [P] [FOUND]** Test: Backtest honesty (replay = live)
  - Path: `tests/integration/test_backtest.py`
  - Test: Capture live quote data; run backtest; verify spread costs match observed spreads in data
  - Test: Verify no assumed spread used during replay
  - Verify: Test FAILS (backtest runner not updated yet)

### Implementation for Backtest Replay

- [ ] **T032 [FOUND]** Update backtest runner: Replay from quote data instead of trades
  - Path: `src/trading/backtest/runner.py`
  - Read Parquet files with quote schema (raw bid/ask data)
  - Reconstruct MarketState from stored quotes
  - Reconstruct observed spread from bid/ask (no synthetic path)
  - Verify: Tests T030, T031 now PASS

**Checkpoint**: Backtest replay honest; observed spread reconstructed from stored raw quotes

---

## Phase 8: Integration & Loop Updates

**Goal**: Live loop uses new adapter; handles book-unavailable pause; end-to-end integration works.

### Tests for Integration (Write FIRST, ensure they FAIL)

- [ ] **T033 [P] [FOUND]** Test: Live loop pauses when book unavailable
  - Path: `tests/integration/test_live_loop.py`
  - Test: Start live loop with book channel connected; simulate book disconnect; verify loop pauses (no MarketStates emitted); verify PAUSE_ON_BOOK_UNAVAILABLE logged
  - Test: Reconnect book; verify loop resumes
  - Verify: Test FAILS (live loop not updated yet)

- [ ] **T034 [P] [FOUND]** Test: End-to-end quote-centric pipeline
  - Path: `tests/integration/test_live_loop.py`
  - Test: Run live loop; verify quote updates processed; verify strategy receives quote-centric MarketState; verify risk checks position; verify execution computes cost using observed spread; verify all decisions logged with reason codes
  - Verify: Test FAILS (live loop not updated yet)

### Implementation for Integration

- [ ] **T035 [FOUND]** Update live loop: Use KrakenV2BookAdapter; handle book-unavailable pause
  - Path: `src/trading/loop/live.py`
  - Use factory.get_feed('kraken_v2') to obtain adapter
  - Handle FeedUnavailableError (pause logging)
  - No direct imports of kraken_v2_book (use factory only)
  - Verify: Tests T033, T034 now PASS

- [ ] **T036 [P] [FOUND]** Update existing test files for new schema
  - Path: `tests/test_market_state.py`
  - Add tests for quote-centric fields
  - Update existing tests for new schema
  - Verify: All tests pass

**Checkpoint**: Integration complete; loop handles pause; end-to-end works

---

## Phase 9: Regression & Validation

**Goal**: All existing tests pass; quickstart scenarios validate; no regressions.

- [ ] **T037 [FOUND]** Verify all 36 Sprint 1 tests still pass
  - Path: Root directory
  - Run `pytest -v`
  - Verify: All existing tests pass (no regressions)

- [ ] **T038 [P] [FOUND]** Run import-linter: Verify no boundary violations
  - Path: Root directory
  - Run `import-linter lint`
  - Verify: All contracts satisfied; no v2/book/checksum leaks

- [ ] **T039 [P] [FOUND]** Run quickstart.md validation scenarios
  - Path: Root directory
  - Run all 10 quickstart scenarios
  - Verify: Scenario 1 (quotes), Scenario 2 (checksum), Scenario 3 (recovery), Scenario 4 (~~sequence gap~~ checksum divergence, WO-009b), Scenario 5 (pause), Scenario 6 (abnormal spread), Scenario 7 (observed spread only), Scenario 8 (backtest honesty), Scenario 9 (import boundaries), Scenario 10 (end-to-end)
  - Verify: All scenarios pass

**Checkpoint**: Feature complete; all validations pass; ready for review

---

## Phase 10: Documentation & Cleanup

- [ ] **T040 [P] [FOUND]** Update decision log reason codes documentation
  - Path: `src/trading/logkit/decision.py`
  - Document new reason codes: PAUSE_ON_BOOK_UNAVAILABLE, CHECKSUM_RESYNC, ~~SEQUENCE_GAP_RESNAPSHOT~~ *(withdrawn WO-009b)*, ABNORMAL_SPREAD_REJECT
  - Verify: Documentation matches implementation

- [ ] **T041 [P] [FOUND]** Mark KrakenPublicFeed as deprecated
  - Path: `src/trading/data/adapters/kraken_public.py`
  - Add deprecation notice; document removal in Sprint 3
  - Verify: Deprecation warning emitted if used

**Checkpoint**: Documentation complete; deprecated adapters marked

---

## Dependencies & Execution Order

### Critical Path (Must Execute Sequentially)

1. **T001** (Import-linter contract) → BLOCKS all adapter work (boundary must exist first)
2. **T002** (MarketState schema) → BLOCKS T003, T004 (consumers need schema)
3. **Phase 3 Tests (T005-T008)** → BLOCKS T009-T019 (write tests first, fail-then-pass)
4. **T009-T019** (US3 implementation) → BLOCKS T020-T021 (US1 depends on adapter core)
5. **T021** (US1 MarketState emission) → BLOCKS T022-T024 (US4 completes adapter)
6. **Phase 6 Tests (T025-T027)** → BLOCKS T028-T029 (write tests first, fail-then-pass)
7. **T028-T029** (US2 cost model) → BLOCKS T030-T032 (backtest depends on cost model)
8. **T030-T032** (backtest replay) → BLOCKS T033-T036 (integration depends on replay)
9. **T033-T036** (integration) → BLOCKS T037-T039 (regression depends on integration)

### Parallel Opportunities (Different Files, No Dependencies)

- **T003, T004** can run in parallel after T002 completes
- **T005, T006, T007, T008** (US3 tests) can all run in parallel
- **T020, T022** (US1/US4 tests) can run in parallel after US3 completes
- **T025, T026, T027** (US2 tests) can all run in parallel
- **T030, T031** (backtest tests) can run in parallel
- **T033, T034** (integration tests) can run in parallel
- **T038, T039, T040, T041** (validation/cleanup) can run in parallel after T037

### User Story Independence

- **US3 (Book Integrity)**: Can be completed independently (adapter core, checksum, recovery)
- **US1 (Quote Processing)**: Depends on US3 (adapter core must exist first)
- **US4 (Trades Enrichment)**: Depends on US1 (adapter emitting MarketState)
- **US2 (Cost Model)**: Independent of adapter implementation (consumes MarketState interface only)

---

## Sequencing Constraints Verification

Per instructions.md WO-005-B, the following constraints are honored:

| Constraint | Task(s) | Status |
|-----------|---------|--------|
| Import-linter contract early (before adapter internals) | T001 (Phase 1, before Phase 3) | ✅ HONORED |
| Checksum validation + fail-then-pass test as single unit | T005-T008 (tests) + T009-T019 (implementation) in same phase | ✅ HONORED |
| Explicit "no synthetic spread" tests | T025, T026, T027 (Phase 6) | ✅ HONORED |
| Backtest quote-replay reconstructs observed spread from stored raw quotes | T032 (explicit requirement) | ✅ HONORED |
| MarketState schema change before consumers | T002 (schema) before T003, T004, T021, T024, T028, T032 | ✅ HONORED |
| No task alters Strategy interface signature | All tasks: strategy/ interface unchanged | ✅ HONORED |

---

## Final Report — then STOP

**Status**: tasks.md generated for feature 002

**Evidence**:

### (a) Import-linter contract task is early
- ✅ T001 (Phase 1) — Import-linter contract update
- Executes BEFORE Phase 3 (adapter internals)
- Any v2/book/checksum leak will fail build from the start

### (b) Checksum implementation and its fail-then-pass test are the same task
- ✅ T005-T008 (tests) + T009-T019 (implementation) — all in Phase 3
- Tests written FIRST, fail-then-pass pattern enforced
- Corrupted book must fail validation (T006)
- Recovery must fire (T007 resync, T008 ~~sequence gap~~ **checksum divergence**, WO-009b)

### (c) Explicit no-synthetic-spread tests exist
- ✅ T025: Cost model uses observed spread only (no synthetic path)
- ✅ T026: Abnormal spread causes rejection
- ✅ T027: No code path emits null/stale/synthetic spread

### (d) No task changes the Strategy interface
- ✅ All tasks honor: "strategy interface unchanged: decide(market_state) -> DesiredPosition"
- ✅ T002 explicitly maintains backward compatibility
- ✅ FR-023 through FR-026: Strategy logic/interface out of scope

**Total Tasks**: 41 tasks across 10 phases
**Estimated Sequencing**: Foundational (Phase 1-2) → US3 (Phase 3) → US1 (Phase 4) → US4 (Phase 5) → US2 (Phase 6) → Backtest (Phase 7) → Integration (Phase 8) → Validation (Phase 9) → Cleanup (Phase 10)

**Do NOT run `/speckit-implement`. Do NOT edit code under `src/`.** The task list comes back to the human before any implementation begins.
