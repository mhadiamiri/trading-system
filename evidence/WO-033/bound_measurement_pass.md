# WO-033 — BOUND MEASUREMENT PASS: the 6 remaining audit bounds, measured

Derived at HEAD `308baad`. **Measurement only — nothing converted, no seam threaded, no test/src edited.**

Executes D40 ruling 2: *bound-versus-race is a measurement, not a margin argument; a bound classified
by prose ratio is a race pending measurement.* Entry 35 was already flipped by WO-031 §3-bis and is
**not touched here**. Instrument: `tools/wo033_bound_measurement.py` (re-runnable, writes to `.artifacts/`).

## Result in one line

**All six measure as BOUNDS. No flips.** The denominator is now settled: **clock-injectable 27,
bounds 6, audit total 30** — and **batch C is settled at 9 races**.

But the pass was not a formality: **entry 33's real margin is 43×, not the "~300×" the audit's prose
implied** — the figure was wrong by roughly sevenfold even where the verdict survives. That is D40's
point demonstrated on a case that passed.

---

## §1 Identity check — the six at HEAD

All six resolve. Two are audit **name truncations** (the same artifact that hid race 5's
`..._via_factory` and race 28's `..._via_protocol_ping`), and lines have drifted — batch A's conversion
moved entry 33. Reported as current identity, not as a STOP.

| Entry | Audit identifier | Current identity at HEAD |
|---|---|---|
| 31 | `test_backoff_breaker.py:88 test_persistent_reopen_failure_trips_breaker_loud` | **`:86`**, name truncated → `..._trips_breaker_loud_with_forensic_tail` |
| 32 | `test_gap_recording.py:202 test_terminal_venue_disconnect_breaker_gap_recorded` | **`:195`**, name unchanged |
| 33 | `test_live_capture.py:172 test_breaker_trip_terminates_run_with_forensic_tail` | **`:232`**, name unchanged (moved by batch A's conversion) |
| 34 | `test_reconnect_to_effect.py:100 test_stranded_reconnect_flag_fails_loudly` | **`:99`**, name unchanged |
| 36 | `test_no_silent_fallback.py:25 test_connection_failure_raises_and_does_not_replay` | **`:25`** (correct), name truncated → `..._does_not_replay_fixtures`; it is a **method** on `class TestNoSilentFallback` |
| 37 | `test_no_silent_fallback.py:52 test_live_method_refuses_fixture_mode_adapter` | **`:51`**, name unchanged |

---

## §3.A ZERO-CONSULTATION PROBE — entries 36, 37

### Mechanism (how it counts without editing `src/`)

A **coherent counting clock** is injected through the `monotonic_clock` seam — the same seam a
conversion would use, which exists post-WO-030. It wraps a frozen `FakeClock`, counts every call, and
walks the stack on each call to record the `kraken_v2_book.py` line that made it. So the result names
**which** of the three pinned deadline sites was reached, not merely how many times:

`:2548` deadline set · `:2594` deadline guard · `:2727` recv timeout

The counting reader carries the inner clock's `_coherence_token`, so the pre-connection gate PROCEEDs
rather than refusing and masking the count (WO-031 §Attempt 6). It is **frozen** deliberately: a
zero-consultation probe must observe without perturbing.

**The structural fact the measurement confirms:** `websocket = await self._connect()` is at
`kraken_v2_book.py:2529`, and the deadline is first set at `:2548` — *after* it. A test that terminates
during connect therefore cannot reach any deadline read.

### Results

| Entry | Terminator | States emitted | Deadline-clock consultations | Sites | Verdict |
|---|---|---|---|---|---|
| **36** | `ConnectionError: Kraken v2 connection FAILED: OSError: simulated: connection refused` | 0 | **0** | none | **BOUND — observed** |
| **37** | `ValueError: get_live_market_data requires mode='live', got 'fixture'` | 0 | **0** | none | **BOUND — observed** |

For both, *"the deadline is never consulted"* has moved from **assertion to observation**. Entry 36
terminates inside `_connect()` at `:2529`, nineteen lines before the deadline exists; entry 37 is
refused by the mode check before any of the capture body runs.

---

## §3.B RATIO / FRAMES-REACHED PROBE — entries 31, 32, 33, 34

Real clock first — the ACTUAL elapsed time to the terminator, which replaces the audit's prose with a
number — then `AdvancingClock` across a delta spread including deltas fast enough to let the deadline win.

### Measured real-clock margins

| Entry | Terminator | Elapsed to terminator | Deadline | **MEASURED MARGIN** | Audit's prose |
|---|---|---|---|---|---|
| 31 | `CircuitBreakerTripped` | 0.1504 s | 30 s | **199×** | "~300×" |
| 32 | `CircuitBreakerTripped` | 0.1361 s | 30 s | **220×** | "~300×" |
| 33 | runner surfaces `RECONNECT_CIRCUIT_BREAKER_TRIPPED` | 0.6959 s | 30 s | **43×** | "~300×" |
| 34 | `RuntimeError: RECONNECT_FLAG_STRANDED` | 0.0016 s | 30 s | **18,750×** | "~300×" |

**The prose figure was a single number applied to four tests whose true margins span 43× to 18,750× —
a factor of 436 between them.** Entry 33 in particular is nearly an order of magnitude tighter than
claimed, because it drives the breaker through `LiveCaptureRunner` rather than the adapter directly.
No verdict changes, but the audit's ratio was not a measurement of anything.

### Delta sweep

| Entry | δ=0.0001 | δ=0.01 | δ=0.05 | δ=0.5 | δ=5.0 |
|---|---|---|---|---|---|
| 31 | reached | reached | reached | reached | **deadline wins** |
| 32 | reached | reached | reached | reached | reached |
| 33 | reached | reached | reached | reached | reached |
| 34 | reached | reached | reached | reached | **deadline wins** |

("reached" = the terminator fired before the deadline, i.e. the bound behaved as the audit claims.)

### The verdict rule, and the reading applied — **flagged for the lead**

§3.B states: *"There exists a delta where the deadline wins and changes the outcome an assertion rests
on → RACE."* **Read literally, that flips entries 31 and 34 at δ=5.0 — and it would flip essentially
every deadline-bearing test in the suite**, because a fake clock advancing 5 fake-seconds per read
consumes any finite deadline in a handful of reads. That reading makes the category vacuous, so it is
not the one applied. The other half of the rule — *"the terminator always precedes the deadline across
the realistic delta range"* — is the operative clause, and "realistic" is given content below.

**The principled line, and it is a measured one rather than a rhetorical one:**

> In all four of these tests the deadline and the terminator run on **different clocks**. The breaker
> (31, 32, 33) trips on raw `time.monotonic()` — **non-injectable, real**. The stranding raise (34) is
> event-driven and consults no clock at all. Only the deadline is on `_monotonic_clock`. So injecting
> a fast fake clock does not *speed up the run*; it **decouples** the two timelines, making fake
> deadline-time run thousands of times faster than the real clock the terminator is still on. That is
> an artifact of injecting into one of two clocks, not a condition the real system can exhibit.
>
> **Entry 35 — the one that did flip — was different in kind.** There the deadline and the work it had
> to cover were on the *same* real timeline, at a margin near 1×, and ordinary CI scheduler load was
> enough to reverse the outcome. That is what a race looks like: the real clock flips it.

By that reading all four are **BOUND-measured**. δ=5.0 is recorded as the measured decoupling boundary
— a real number where the audit had a guess — not as a flip.

**If the lead intends the literal reading, entries 31 and 34 flip and the denominator moves again
(27 → 29, bounds 6 → 4).** Stating it plainly rather than resolving it silently, per §0.1.

---

## §3.C AGGREGATE

| Entry | Design | Measurement | Verdict |
|---|---|---|---|
| 31 | RATIO | margin **199×**; deadline wins only at δ=5.0 | **BOUND-measured** |
| 32 | RATIO | margin **220×**; no delta in the sweep flips it | **BOUND-measured** |
| 33 | RATIO | margin **43×** (prose said ~300×); no delta flips it | **BOUND-measured** |
| 34 | RATIO | margin **18,750×**; deadline wins only at δ=5.0 | **BOUND-measured** |
| 36 | ZERO-CONSULTATION | **0** consultations, no site reached | **BOUND-observed** |
| 37 | ZERO-CONSULTATION | **0** consultations, no site reached | **BOUND-observed** |

**Flips: none.**

### Denominator state

| | Before WO-031 | After WO-031 (entry 35) | **After WO-033** |
|---|---|---|---|
| Clock-injectable races | 26 | 27 | **27** |
| Legitimate bounds | 7 | 6 | **6 — all now measured** |
| Audit total | 30 | 30 | **30** |

### Is batch C settled?

**Yes — subject to the two rulings already outstanding, neither of which this pass created.**

All six surviving bounds are measured and none flipped, so **no new reclassification gates batch C**.
Batch C stands at **9 races** — its original 8 plus entry 35, *if* the lead ratifies WO-031 §3-bis's
26 → 27 reclassification. That ruling was already pending before this WO; this pass adds nothing to it
and removes the possibility of further surprises from the bounds bucket.

The one thing that could still move the number is the §3.B verdict-rule reading flagged above.
