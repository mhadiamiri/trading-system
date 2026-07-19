# Quickstart Validation Guide: Quote-Level Data + Observed-Spread Cost Model

**Feature**: 002-quote-level-data
**Date**: 2026-07-15

---

## Overview

This guide provides runnable validation scenarios to prove the feature works end-to-end. Use these scenarios to verify:

1. Quote processing from Kraken v2 book channel
2. Observed spread cost model (no synthetic spread)
3. Checksum validation and recovery
4. Pause behavior on book unavailability
5. Backtest replay with observed spread

---

## Prerequisites

### Environment Setup

```bash
# Navigate to project root
cd C:\Projects\bot\trading-system

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify environment
python --version  # Python 3.11+
pytest --version
import-linter --version
```

### Configuration

Create or verify `.env`:
```bash
# Data source (for live testing)
DATA_SOURCE=kraken_v2

# Trading environment
TRADING_ENV=paper
```

---

## Validation Scenarios

### Scenario 1: Quote Processing (Happy Path)

**Objective**: Verify Kraken v2 book adapter receives and processes quote updates.

**Steps**:

```bash
# Run quote processor test
pytest tests/test_data_adapters.py -v -k "test_quotes_received"
```

**Expected Outcome**:
- Test passes
- Quote updates are received from Kraken v2
- MarketState objects emitted with populated `best_bid`, `best_ask`, `best_bid_size`, `best_ask_size`
- `mid_price` and `spread` derived correctly

**Manual Verification** (optional):

```bash
# Run live loop for 1 minute
timeout 60 python -m trading.loop.live
```

**Expected Output**:
- Quote updates logged (hundreds to thousands per minute)
- No "checksum failure" errors under normal conditions *(CORRECTED 2026-07-19, WO-009b: no sequence numbers on the v2 public book channel; checksum divergence is the detector.)*
- MarketStates emitted with all quote fields populated

---

### Scenario 2: Checksum Validation Bites

**Objective**: Prove checksum validation rejects corrupted updates.

**Steps**:

```bash
# Run checksum failure test
pytest tests/test_data_adapters.py -v -k "test_checksum_rejection"
```

**Expected Outcome**:
- Test passes
- Corrupted update (manually altered price) fails checksum validation
- Update is rejected and logged with error
- `consecutive_failures` counter increments

**What the test does**:
1. Creates a valid quote update with checksum
2. Alters a price (breaking checksum)
3. Calls validation
4. Verifies rejection

---

### Scenario 3: Recovery Fires (5 Failures → Resync)

**Objective**: Verify resync triggers after 5 consecutive checksum failures.

**Steps**:

```bash
# Run resync test
pytest tests/test_data_adapters.py -v -k "test_resync_after_failures"
```

**Expected Outcome**:
- Test passes
- After 5 consecutive failures, adapter triggers reconnection
- Fresh snapshot requested
- Book state synchronized with exchange

**What the test does**:
1. Simulates 5 consecutive checksum failures
2. Verifies resync triggered
3. Simulates successful snapshot
4. Verifies book state recovered

---

### Scenario 4: ~~Sequence Gap → Resnapshot~~ Checksum Divergence → Resnapshot

**REPLACED 2026-07-19 (WO-009b).** The original scenario validated a mechanism that
cannot occur: the Kraken v2 public book channel transmits no sequence numbers. Under
rule 0.1d a scenario whose trigger cannot occur in production is a false guarantee.
Original text preserved by strike-through below; history is annotated, not laundered.

~~**Objective**: Verify sequence gap detection triggers resnapshot.~~
~~pytest tests/test_data_adapters.py -v -k "test_sequence_gap_resnapshot"~~
~~1. Establishes synchronized book (sequence 100); 2. Receives update with sequence 105 (gap); 3. Verifies book discarded and snapshot requested~~

**Objective**: Verify checksum divergence triggers resnapshot, with no MarketState
emitted until the fresh snapshot validates.

**Steps**:

```bash
# Run checksum divergence test (to be written in WO-008b-A)
pytest tests/test_data_adapters.py -v -k "checksum_divergence"
```

**Expected Outcome**:
- Update applied to the local book, then CRC32 computed over the POST-update
  top-10-per-side ladder (FR-018a(b))
- Mismatch detected; the APPLIED state discarded (not merely the message)
- Fresh snapshot requested
- **NO MarketState emitted from the moment of failure until the fresh snapshot is
  applied and its checksum validates** (FR-018a(d))

**What the test must do**:
1. Establish a synchronized book from the ground-truth snapshot fixture
2. Apply an update whose checksum does not match the resulting book
3. Verify the applied state is discarded, a snapshot is requested, and nothing is
   emitted until that snapshot validates

**Status**: this test does not exist yet. Owned by WO-008b-A, which must also delete
`test_sequence_gap_triggers_resnapshot`. Fixtures are ready in
`tests/fixtures/kraken_v2_raw_frames.py`.

---

### Scenario 5: Book Unavailable → Pause

**Objective**: Verify system pauses when book channel unavailable (no fallback to trades-only).

**Steps**:

```bash
# Run pause test
pytest tests/test_data_adapters.py -v -k "test_pause_on_book_unavailable"
```

**Expected Outcome**:
- Test passes
- When book channel lost, adapter stops yielding MarketStates
- Reason code `PAUSE_ON_BOOK_UNAVAILABLE` logged
- When book recovers, yielding resumes
- No synthetic/assumed spread ever emitted

**What the test does**:
1. Starts with book channel connected
2. Simulates book channel disconnect
3. Verifies no MarketStates yielded during disconnect
4. Reconnects book
5. Verifies yielding resumes

---

### Scenario 6: Abnormal Spread → Reject Trade

**Objective**: Verify cost model rejects trades on zero/negative/wide spread.

**Steps**:

```bash
# Run abnormal spread test
pytest tests/test_backtest_costs.py -v -k "test_abnormal_spread_reject"
```

**Expected Outcome**:
- Test passes
- MarketState with zero/negative spread causes trade rejection
- MarketState with spread >5% of price causes trade rejection
- Rejection logged with `ABNORMAL_SPREAD_REJECT` reason code
- No cost fabricated for rejected trades

**What the test does**:
1. Creates MarketState with negative spread (bid > ask)
2. Calls cost model
3. Verifies rejection

---

### Scenario 7: Observed Spread Only (No Synthetic Path)

**Objective**: Prove cost model uses observed spread only; no synthetic/assumed/fallback path exists.

**Steps**:

```bash
# Run observed spread test
pytest tests/test_backtest_costs.py -v -k "test_observed_spread_only"
```

**Expected Outcome**:
- Test passes
- All spread costs computed from bid/ask in MarketState
- No hardcoded or assumed spread values used
- Code review confirms no fallback path

**What the test does**:
1. Reads cost model source
2. Verifies all spread costs derived from `market_state.spread`
3. Verifies no constant/assumed/fallback spread exists

---

### Scenario 8: Backtest Honesty (Replay = Live)

**Objective**: Verify backtest replay produces identical spread costs to live behavior.

**Steps**:

```bash
# Run backtest honesty test
pytest tests/integration/test_backtest.py -v -k "test_backtest_honesty"
```

**Expected Outcome**:
- Test passes
- Backtest reads stored quote data from Parquet
- Reconstructs MarketState with observed spread
- Cost model computes spread cost from reconstructed spread
- No synthetic spread introduced during replay

**What the test does**:
1. Captures live quote data to Parquet
2. Runs backtest on captured data
3. Verifies spread costs match observed spreads
4. Verifies no assumed spread used

---

### Scenario 9: Import Boundaries Enforced

**Objective**: Verify import-linter blocks v2/book/checksum leaks above adapter.

**Steps**:

```bash
# Run import-linter
import-linter lint
```

**Expected Outcome**:
- Linter passes
- Contract forbids v2/book/checksum imports above adapter
- Strategy, risk, execution, backtest, loop cannot import `kraken_v2_book` internals
- Only `from trading.data.adapters import KrakenV2BookAdapter` allowed

---

### Scenario 10: End-to-End Integration

**Objective**: Verify full pipeline works: adapter → strategy → risk → execution (with observed spread costs).

**Steps**:

```bash
# Run integration test
pytest tests/integration/test_live_loop.py -v -k "test_quote_centric_pipeline"
```

**Expected Outcome**:
- Test passes
- Quote updates processed end-to-end
- Strategy receives quote-centric MarketState
- Risk checks position (strategy logic unchanged)
- Execution computes cost using observed spread
- All decisions logged with reason codes

---

## Regression Tests

### Verify Existing Tests Pass

**Objective**: Ensure no regressions from Sprint 1.

**Steps**:

```bash
# Run all tests
pytest -v
```

**Expected Outcome**:
- All 36 Sprint 1 tests pass
- New tests for Sprint 2 pass
- No existing functionality broken

---

## Troubleshooting

### Checksum Failures in Live Run

**Symptom**: Many checksum failures in logs

**Diagnosis**:
1. Check network connectivity to Kraken
2. Verify checksum algorithm implementation matches Kraken docs
3. Check for checksum failures (may indicate message loss, misapplied updates, or a book-maintenance bug) *(CORRECTED 2026-07-19, WO-009b: no sequence numbers on the v2 public book channel; checksum divergence is the detector.)*

**Resolution**:
- If transient: 5-failure threshold tolerates glitches
- If persistent: Check implementation bug or network issues

### No Quote Updates Received

**Symptom**: Zero quote updates in logs

**Diagnosis**:
1. Check WebSocket connection to Kraken
2. Verify subscription message format
3. Check Kraken API status

**Resolution**:
- Verify `wss://ws.kraken.com` endpoint
- Check subscription payload matches v2 docs
- Ensure no firewall blocking WebSocket

### Import-Linter Failures

**Symptom**: Import-linter reports violations

**Diagnosis**:
1. Check which module is importing v2 internals
2. Verify import-linter contract configuration

**Resolution**:
- Refactor to use only `MarketFeed` interface above adapter
- Move v2-specific code into adapter module

---

## Validation Checklist

Before declaring feature complete, verify:

- [ ] Scenario 1: Quote processing happy path passes
- [ ] Scenario 2: Checksum validation bites
- [ ] Scenario 3: Recovery fires (5 failures → resync)
- [ ] Scenario 4: ~~Sequence gap~~ **Checksum divergence** → resnapshot *(WO-009b)*
- [ ] Scenario 5: Book unavailable → pause (no fallback)
- [ ] Scenario 6: Abnormal spread → reject trade
- [ ] Scenario 7: Observed spread only (no synthetic path)
- [ ] Scenario 8: Backtest honesty (replay = live)
- [ ] Scenario 9: Import boundaries enforced
- [ ] Scenario 10: End-to-end integration passes
- [ ] Regression tests: All 36 Sprint 1 tests pass
- [ ] Constitution Check: Principles V and VII verified
- [ ] Import-linter: All contracts satisfied

---

## Next Steps

After validation passes:

1. **Run `/speckit-tasks`** to generate actionable task list
2. **Run `/speckit-implement`** to execute implementation
3. **Run `/speckit-analyze`** to verify compliance
4. **Manual review**: Verify two non-negotiables held:
   - No synthetic spread anywhere
   - Adapter boundary (v2 detail confined)
