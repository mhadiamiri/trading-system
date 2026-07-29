# WO-040 FIXTURE INVESTIGATION — Can the real loop be measured on real checksums?

**Date:** 2026-07-28
**WO:** WO-039 CLOSEOUT + WO-040 FIXTURE INVESTIGATION
**Base:** HEAD `89a2842` (WO-039 flag + bite proof, pushed)
**CI:** GREEN both legs run `30399653951` (verified §1)

---

## §1 FINDING: raw_frames Path Completeness

**Question:** Does WO-039's bite proof (median 0.078 ms/frame on `raw_frames`) measure the FULL processing path or a TRUNCATED one?

**Answer:** FULL PATH. `raw_frames` executes parse → CRC32 → book update → MarketState construction.

**Evidence:**

### 1.1 Processing Path Traced

When a `raw_frames` frame is processed through `get_live_market_data`:

1. **JSON Parse** (`kraken_v2_book.py:2927-2929`):
   ```python
   raw_frame = json.loads(message, parse_float=WireDecimal, parse_int=WireDecimal)
   ```
   - Creates `WireDecimal` instances with `.wire` attribute set to the transmitted string

2. **Process** (`kraken_v2_book.py:2945`):
   ```python
   market_states = await self.process_raw_frame(raw_frame)
   ```

3. **Parse Book Frame** → **Apply Update** (`kraken_v2_book.py:1882-1981`):
   ```python
   async def _process_quote_update(self, quote_update: QuoteUpdate) -> Optional:
       # Apply snapshot or incremental update to local book
       if quote_update.is_snapshot:
           self._local_book.apply_snapshot(...)
       else:
           self._local_book.apply_incremental_update(...)
   ```

4. **Checksum Validation** (`kraken_v2_book.py:1920-1938`):
   ```python
   # FR-018a(b),(c): checksum over the POST-update ladder, on EVERY update
   bid_levels, ask_levels = self._current_ladder_strings()
   computed_checksum = self.compute_checksum(bid_levels, ask_levels)

   if computed_checksum != quote_update.checksum:
       self._local_book.record_failure()
       self._log_error(...)
       self._capture_checksum_failure(...)
       if self._local_book.consecutive_failures >= self.CHECKSUM_FAILURE_THRESHOLD:
           self._reconnect()
       self._enter_resync("post-update checksum mismatch")
       return None  # <-- EARLY RETURN if checksum fails
   ```

5. **MarketState Construction** (`kraken_v2_book.py:1967-1981`):
   ```python
   return MarketState(
       timestamp=...,
       symbol=...,
       best_bid=self._local_book.best_bid_price,
       best_ask=self._local_book.best_ask_price,
       ...
   )
   ```

### 1.2 Does raw_frames Short-Circuit?

**NO.** The checksum validation GATES the MarketState return (line 1938). If checksum fails, `None` is returned and no MarketState is yielded.

`raw_frames` uses SELF-GENERATED checksums (computed by the project's own `compute_checksum()`), but they ARE validated:
- `SNAPSHOT_FRAME`: Ground-truth from Kraken docs (checksum `3310070434`)
- `UPDATE_*_LEVEL`: Self-generated but match because computed identically

When WO-039's bite proof collected 4 timings with flag ON:
- All 4 frames passed checksum validation
- All 4 reached MarketState construction
- The 0.078 ms median measures: JSON parse → WireDecimal → book update → CRC32 computation → MarketState construction

**VERDICT:** `raw_frames` drives the FULL path. WO-039's 0.078 ms/frame is a valid measurement of the real processing loop.

---

## §2 FINDING: captured_frames Scientific Notation Root Cause

**Question:** Why do `captured_frames` (41 frames with real Kraken checksums) FAIL validation?

**Answer:** The A2 fixture stores POST-PARSE Python dicts where `json.dumps` rendered floats in scientific notation (`5.1e-05` instead of `0.00005100`), losing the trailing zeros the checksum depends on.

### 2.1 The Fixture Generation Path

From `kraken_v2_captured_frames.py` lines 24-30:
```
⚠ NOTE ON NUMBER RENDERING — the defect this capture exposed
------------------------------------------------------------
Kraken sends price and qty as JSON NUMBERS, not strings, so `json.loads`
floats them before any project code runs. `Decimal(str(5.1e-05))` renders
"0.000051", dropping trailing zeros the checksum digits require; Kraken's
own rendering is fixed-point 8dp, "0.00005100".
```

The capture process:
1. Live WebSocket receives JSON: `{"price": 0.00005100, ...}` (Kraken wire format)
2. `json.loads` (default) parses to Python `float`: `5.1e-05`
3. Python dict stored to file
4. When fixture is loaded, `Decimal(str(5.1e-05))` = `Decimal("0.000051")`
5. Checksum computed over `"0.000051"` ≠ checksum computed over `"0.00005100"`

### 2.2 Why A2 Cannot Validate

The WO-008b-B guard (`kraken_v2_book.py:1381-1386`):
```python
# data-path guard. It stays load-bearing after the wire-string WO: it then
# guards the invariant ("no synthesized notation reaches the CRC"), not the implementation.
if 'e' in checksum_input or 'E' in checksum_input:
    raise ValueError(
        "CHECKSUM_INPUT_SYNTHESIZED_NOTATION: assembled checksum input contains "
        "scientific notation; a formatting regression re-entered the render path."
    )
```

When A2 fixture values are converted to checksum input strings:
- `5.1e-05` → `"5.1e-05"` (contains 'e')
- Guard raises `CHECKSUM_INPUT_SYNTHESIZED_NOTATION`
- Validation fails

**ROOT CAUSE:** A2 fixture is LOSSY vs the wire. The checksums are real (from Kraken), but the stored values lost trailing zeros during serialization.

---

## §3 FINDING: A Validating Full-Path Fixture EXISTS

**Question:** Does a replayable, real-checksum-validating, full-path-driving fixture exist?

**Answer:** YES. The A3 fixture (`tests/fixtures/kraken_v2_captured_frames_a3.py`) — 41 frames, real Kraken checksums, validates correctly.

### 3.1 The A3 Fixture

From `kraken_v2_captured_frames_a3.py`:
```python
"""
GROUND TRUTH: captured live from Kraken v2, 2026-07-19T17:54:37.034140+00:00
Window: 1 snapshot + 1253 book updates over ~122s (1376 raw frames).
Retained: snapshot + first 40 updates, as RAW WIRE TEXT.

Validated under the ruled fix (json.loads parse_float=Decimal, parse_int=Decimal):
snapshot checksum reproduced, and 1253 of 1253 incremental checksums reproduced.
"""
```

### 3.2 Why A3 Validates

The A3 fixture stores RAW WIRE TEXT as JSON strings:
```python
CAPTURED_SNAPSHOT_TEXT = '{"channel":"book",...,"bids":[{"price":64525.0,"qty":0.53807066},...],"asks":[{"price":64522.9,"qty":0.00005100},...],"checksum":2175437505,...}'
```

When parsed with `json.loads(parse_float=Decimal, parse_int=Decimal)`:
- Numbers create `Decimal` instances (not `float`)
- `Decimal("0.00005100")` preserves trailing zeros
- `.wire` attribute receives the original text representation
- Checksum input is `"00005100"` (no 'e')
- Guard passes
- Real Kraken checksum validates

### 3.3 Validation Proof

From `tests/test_captured_frames_a3_raw_text.py`:
```python
def test_snapshot_checksum_reproduces_from_raw_text(self):
    element = _parse(CAPTURED_SNAPSHOT_TEXT)["data"][0]
    bids = _levels(element["bids"], reverse=True)
    asks = _levels(element["asks"], reverse=False)

    assert KrakenV2BookAdapter.compute_checksum(bids, asks) == element["checksum"]

def test_every_captured_update_reproduces_from_raw_text(self):
    """N of N — the denominator travels with the claim."""
    validated = 0
    for text in CAPTURED_UPDATE_TEXTS:
        data = _parse(text)["data"][0]
        # ... apply updates ...
        assert KrakenV2BookAdapter.compute_checksum(bids, asks) == data["checksum"]
        validated += 1

    assert validated == len(CAPTURED_UPDATE_TEXTS)  # 40 frames
```

**VERDICT:** A3 fixture is a replayable, real-checksum-validating, full-path-driving fixture. 41 frames (1 snapshot + 40 updates), all real Kraken checksums validate.

---

## §4 OUTCOME: Option A — Validating Fixture Exists

**Outcome:** **(A)** A validating full-path fixture EXISTS.

**Fixture:** `tests/fixtures/kraken_v2_captured_frames_a3.py`
- **Frame count:** 41 (1 snapshot + 40 updates)
- **Checksums:** Real Kraken checksums (ground truth from live capture)
- **Validation:** 100% — 1253/1253 updates validated in original capture, 40/40 in regression test
- **Path:** FULL — parse (WireDecimal with .wire) → CRC32 → book update → MarketState
- **Provenance:** Live capture `2026-07-19T17:54:37.034140+00:00`, raw wire text preserved

**WO-040 Use:** WO-040 can use the A3 fixture to produce the real baseline. The fixture:
1. Drives the full `get_live_market_data` path with `enable_instrument=True`
2. Executes real parse+CRC32+book-update on every frame
3. Validates checksums (real Kraken values, not self-generated)
4. Collects per-frame timings through the production instrument
5. Produces a valid capture-loop baseline (7 dimensions, host-suspend verified)

**NO BLOCKER.** No new capture, no production/guard change, no escalation. The A3 fixture was built specifically for this purpose and validates correctly.

---

## §5 ADDITIONAL FINDING: Two Fixture Distinctions

| Fixture | Frames | Checksums | Format | Validates? |
|---------|--------|-----------|--------|-------------|
| **A2** `kraken_v2_captured_frames.py` | 41 (1+40) | Real Kraken | POST-PARSE dicts (Python floats) | NO — `5.1e-05` → CHECKSUM_INPUT_SYNTHESIZED_NOTATION |
| **A3** `kraken_v2_captured_frames_a3.py` | 41 (1+40) | Real Kraken | RAW WIRE TEXT (JSON strings) | YES — `"0.00005100"` → validates |

**Key distinction:** A2 stores what happened AFTER `json.loads` converted everything to Python types. A3 stores the bytes AS RECEIVED, so the parsing layer itself is under test.

---

## §6 ATTEMPTS

1. **§1 CI verification** — SUCCESS
   - Run `30399653951` verified: both 3.11 and 3.14 legs GREEN
   - Local == remote reconfirmed at `89a2842`

2. **§2.1 raw_frames path tracing** — SUCCESS
   - Full processing path traced from `get_live_market_data` through `process_raw_frame` → `_process_quote_update`
   - Checksum validation gate confirmed (line 1938 early return on mismatch)
   - WO-039's 0.078 ms confirmed as FULL path measurement

3. **§2.2 captured_frames root cause** — SUCCESS
   - Scientific notation (`5.1e-05`) traced to fixture generation (POST-PARSE storage)
   - A2 is LOSSY vs wire, checksums validate against original wire format only
   - A3 preserves raw wire text, validates correctly

4. **§2.3 outcome classification** — SUCCESS
   - Outcome A confirmed: A3 fixture exists and validates
   - 41 frames, real Kraken checksums, full-path driving
   - No blocker for WO-040

5. **No STOPs** — Investigation proceeded straight through without stopping

---

## §7 ACCEPTANCE

- ✓ WO-039 CI verified GREEN both legs (run `30399653951`)
- ✓ raw_frames path traced: FULL path (parse → CRC32 → book update → MarketState)
- ✓ captured_frames root-caused: A2 fixture LOSSY (scientific notation), A3 fixture preserves raw wire
- ✓ Validating fixture EXISTS: A3 (`kraken_v2_captured_frames_a3.py`), 41 frames, 100% validation
- ✓ Outcome A: WO-040 can use A3 for real baseline, no blocker
- ✓ `git diff -- src/` empty vs `89a2842` (investigation only, no code change)
- ✓ No test count change (237 both interpreters)

---

## NEXT STEP

**WO-040** can now proceed to produce the real capture-loop baseline using the A3 fixture (`tests/fixtures/kraken_v2_captured_frames_a3.py`):

1. Drive frames through `get_live_market_data(enable_instrument=True)`
2. Collect per-frame timings through production instrument
3. Measure seven dimensions with host-suspend verification
4. Produce anti-VOID measurement (full path, real checksums)

The fixture investigation is COMPLETE. Outcome A — a validating full-path fixture EXISTS and is ready for WO-040.
