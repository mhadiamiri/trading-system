# WO-056 — WIRE THE TRADE CHANNEL INTO THE CAPTURE PATH

**The reachability cell is filled.** `trading.data.trade_channel` is now reached from
**`tools/live_corpus_capture.py:895`**, and a witness that enters at that file — not at the
component — proves it against the bytes of the written corpus frames.

**NO SOCKET OPENED.** Fixtures only. **SHIP IMPACT: YES** (capture path, two channels).
Corpus v1 `e3ab1aec…` unchanged, 38/38 capture hashes verify.

> ## THE ASYMMETRY THAT IS THE FINDING
>
> Under the mutation that restores the WO-055 discard:
>
> | suite | entry point | result |
> |---|---|---|
> | **reachability witness** | `tools/live_corpus_capture.py` | **FAILS** |
> | `test_trade_channel.py` | `TradeMerger` / `parse_trade_message` | **all 22 STILL PASS** |
>
> 22 component tests, their own passing bite proof, and green CI on both legs in both orders were
> all structurally incapable of seeing that nothing called the component. The witness sees it.

---

## §1 STATE, AND THE TERM 2 MEASUREMENT

HEAD `e3f2625` (WO-055, no code changed, CI 31240124483, 509/2). `git diff -- src/` clean.
Baseline **509 passed, 2 skipped**. All gates green; corpus v1 `e3ab1aec…` and 38/38 verified.

*Attempt noted:* the baseline run again reported `508 passed, 1 failed` — the reason-code
vocabulary guard reads `src/` **at test time** and caught a new code mid-edit. 508 + 1 = 509
confirms the baseline; the guard passes 11/11 once both files landed. Sixth consecutive WO.

### Term 2 — informational, not a gate here (no socket opens)

| | WO-044 ref | WO-055 | **now (2026-08-08)** |
|---|---:|---:|---:|
| free memory | **12.33 GB** | 3.01 GB | **5.07 GB** |
| **swap in use** | **0** | 0.96 GB | **0.58 GB** |
| idle CPU | 1.0% | 1.64% | 2.78% |

**The verdict I would return if this were a gate: still 🔴 RED.** The operator has acted and it is
real progress — +2.06 GB free, swap down 40% — but **swap is still in use at idle**, so D46's first
link (memory pressure → swap → event-loop starvation → `HEARTBEAT_ABSENCE`) is still present rather
than implausible. **Falsifier:** ≥ ~12 GB free with swap at 0 would be GREEN.

---

## §2 THE FOUR CALL SITES — before

| § | Site | Before |
|---|---|---|
| 2.1 | `kraken_v2_book.py:2251` `_build_subscribe_message()` | `{"channel": "book", "depth":…, "snapshot": True}` — **book only** |
| 2.2 | `kraken_v2_book.py:1616` the parser | `if raw_frame.get("channel") != "book": return []` — **trade messages dropped on the floor** |
| 2.3 | `kraken_v2_book.py:2487` `_maybe_resubscribe()` / `:2582` reconnect | re-sent **book** unsubscribe+subscribe only |
| 2.4 | `live_corpus_capture.py:869` frame writer | seven fields — byte-identical in shape to `corpus_20260805` |

---

## §3 SUBSCRIBE / ACK — BOTH CHANNELS

**§3.1** `_send_subscriptions()` sends book + trade at connect; `_send_trade_subscription()` sends
the trade half alone. Two entry points, because the two paths need different halves — see §5.
`snapshot: false` on trade is WO-054's deliberate decision, pinned by a test.

**§3.2 — the ack, CITED not assumed.** Retrieved 2026-08-08 from
https://docs.kraken.com/api/docs/websocket-v2/trade:

```json
{"method": "subscribe",
 "result": {"channel": "trade", "snapshot": true, "symbol": "MATIC/USD"},
 "success": true, "time_in": "…", "time_out": "…"}
```

`_handle_subscription_response()` reads exactly that shape. `_check_trade_ack_deadline()` runs **on
the frame path** — so it is evaluated by the real loop, not by a timer nobody drives.

### §3.3 — what happens when the subscribe never acks (the decision, declared)

**Chosen: start with `observable: false` recorded from the first frame** — Ops's expectation, and I
agree. The alternative (refuse to start) throws away a good book capture over a second channel, and
worse, it makes the corpus *silent* about the question. This way the corpus **says "we could not
see"**: `count: null`, not `0`. A `0` would assert that nothing traded.

One rule covers three cases: **the merger starts unobservable and becomes observable only on the
ack.** That is simultaneously §3.3 (never acks), §5.1 (reconnect — the new socket's subscription is
unacked, so the interval is recorded unseen) and §6.2 (seam — a fresh process cannot fabricate a
delta across it). Proved by `test_without_an_ack_the_corpus_says_it_could_not_see`.

---

## §4 THE DEMUX, AND THE BOOK PATH'S DUAL

**Placed in `process_raw_frame`, deliberately** — the one point every raw frame passes through on
**both** the live and fixture paths ("LAYER 3: the SHARED entry point"). Anywhere else would be a
live-only branch, and a live-only branch is unreachable from a fixture — the exact defect class
this WO exists to close.

### §4.1 What else Kraken sends on this socket — enumerated, not assumed (0.11)

| Kind | Handling |
|---|---|
| `channel: "book"` | falls through untouched to `_parse_book_frame` |
| `channel: "trade"` | → `TradeMerger` (**the wire D55 says was missing**) |
| `channel: "heartbeat"` | ignored — liveness already refreshed `last_frame` upstream |
| `channel: "status"` | ignored — carries no market data |
| `method: subscribe/unsubscribe` | **the ack path** — the one kind of chatter that must NOT be dropped |
| **anything else** | **counted** in `get_unrecognised_channels()` — a future WO inherits a number, not a silence |

### §4.2 The preservation dual — proven

`test_dual_a_book_only_stream_still_writes_the_seven_original_fields` asserts the written frame's
key set is **exactly** the seven original fields plus `trades`. Nothing renamed, nothing dropped —
byte-shape compatible with `corpus_20260805`. **This dual also holds under the §8 mutation**, which
is what makes the witness's failure attributable to lost reachability rather than a broken capture.

---

## §5 RECONNECT / RESUBSCRIBE — the silent-death case

**§5.1** On reconnect the merger is marked `TRADE_CHANNEL_DROPPED`, then the **trade** subscribe is
re-sent on the fresh socket — the book half is already re-sent by `_maybe_resubscribe`, the
committed resync producer, immediately above. Without the trade half the channel dies at the first
reconnect and the corpus keeps writing `observable: true` frames with no trades — a lie of exactly
the WO-055 §3.5 shape, and one that would read as a quiet market.

**A duplicate I introduced and an existing test caught.** My first draft sent the full pair here,
which put **two book subscriptions** on the reopened socket. `test_reconnect_to_effect` failed and
named it; the send path was split so the reconnect adds only the half that is actually missing. The
fresh socket now carries exactly `unsubscribe(book), subscribe(book), subscribe(trade)`.

**§5.2** A venue `unsubscribe` naming the trade channel, on a live socket, records
`TRADE_CHANNEL_DROPPED` and flips `observable: false`. Never a `GapRecord`: there is no no-emission
window, so recording a gap would subtract book coverage that was never lost.

**The resync path deliberately does NOT re-send trade** — a checksum resync unsubscribes and
resubscribes the *book* on the *same* live socket, where the trade subscription was never touched;
re-sending would be a spurious duplicate. Both behaviours are pinned by tests, and the "does not"
test asserts on **calls with comments stripped** — matching the explanatory comment would have made
it pass for the wrong reason.

---

## §6 THE MERGER LIFECYCLE

**§6.1 Rotation — the declared rule.** *The pending delta attaches to the frame it is written with,
and that call closes and resets the interval.* Rotation happens **between** frames, so a trade
arriving between the last frame of segment N and the first of N+1 lands in exactly **one** delta —
the first frame of N+1. Nothing is double-counted and nothing is dropped, because there is exactly
one snapshot call per written frame and only that call advances the interval. Proved by
`test_rotation_one_snapshot_call_per_written_frame_is_the_whole_rule`.

**§6.2 Seam — the declared rule.** A fresh process builds a fresh adapter whose merger starts
**unobservable**. The first interval of a resumed run reports `count: null` — *we could not see* —
rather than a `0` claiming nothing traded across the seam, and `running_last_price` is `null`
because **no price carries across a process restart**. No delta is ever fabricated over an interval
that spans the seam.

---

## §7 THE FRAME WRITER

```python
frame["trades"] = adapter.trade_snapshot_for_frame(frame["timestamp"])
```

`live_corpus_capture.py:895`. Emits the WO-054 schema's three states: `count: 0` a positive claim,
`count: null` the absence of one, `last_price` never fabricated, `running_last_price` separately
named with its age.

---

## §8 THE REACHABILITY WITNESS — `tools/wo056_reachability_bite_proof.py`, **VERDICT: PASS**

| Artifact | Result |
|---|---|
| 1 — PRISTINE | witness 16 passed; component 22 passed |
| 2 — **MUTATION** (the WO-055 discard restored) | **witness 6 failed / 10 passed** · **component 22 PASSED** · **book dual held** |
| 3 — RESTORED | witness 16 passed; component 22 passed |
| 4 — **THE REACHABILITY CELL** | `live_corpus_capture.py:895` named |

```
kraken_v2_book.py sha256 BEFORE/AFTER : 1ea4c221792a8811788ce51f1ea7df74a782bee8fc10ee5ad2f914ed42add81d
IDENTICAL                              : True
WITNESS bites under the mutation                  : True
COMPONENT TESTS STAY GREEN under the same mutation: True
BOOK-PATH DUAL holds under the mutation           : True
```

**Why the asymmetry is the point.** If both suites failed, the mutation would be "a broken build"
and would prove nothing about *where* the blindness lived. If both passed, the witness would be
decoration. Only the asymmetry shows that entering at the component is structurally blind to
non-reachability — and that entering at the production runner is not.

---

## THE BUILT-VS-OPERATED TABLE, REACHABILITY COLUMN FILLED (0.14)

| Thing | Status | Verified where | **Reached from (production call site)** |
|---|---|---|---|
| `trade_channel.py` (merger, ledger, schema) | **BUILT + REACHED** (not yet operated) | WO-054 22 tests; WO-056 witness | **`live_corpus_capture.py:895` — `frame["trades"] = adapter.trade_snapshot_for_frame(...)`** |
| `kraken_v2_book.py` book path | **OPERATED** | four captures | `live_corpus_capture.py` read loop |
| Segment rotation + manifest | **OPERATED** | WO-044 | `live_corpus_capture.py` |
| Trade subscribe/ack | **BUILT** | §3, witness | `kraken_v2_book._send_subscriptions` ← connect + `_perform_reconnect` |
| Channel demux | **BUILT** | §4, witness | `kraken_v2_book.process_raw_frame` ← the live read loop |
| Reconnect resubscribe (both) | **BUILT** | §5, witness | `kraken_v2_book._perform_reconnect` |
| Frame writer (`trades`) | **BUILT** | §7, witness | `live_corpus_capture.py:895` |
| Merger lifecycle (rotation, seam) | **BUILT** | §6, witness | `live_corpus_capture.py:895` + fresh adapter per run |

**No empty cells.** Everything built here is still **BUILT, not OPERATED** — nothing has met Kraken.
That is WO-055's job, re-issued.

---

## EVERY ATTEMPT

1. **Cited the ack shape** rather than assuming it (0.1e) — a second fetch specifically for the
   subscription response, since the merge's ack handling depends on `result.channel`.
2. **`_wall` was a *local* inside the transport loop**, returning an epoch float, not a module
   helper returning a datetime. My first draft called `_wall().isoformat()` from three methods and
   `NameError`d six existing tests. Fixed by adding `_utc_now_iso()` that goes **through the
   injected wall clock** — a hardcoded `datetime.now()` there would have been a clock-control hole
   in a record the reader trusts.
3. **The witness hung for >5 minutes on the first attempt.** Two causes, both mine: `on_drain="raise"`
   is not a valid option and silently fell through to `"block"` (wait forever); and injecting a
   `FakeClock` as `monotonic_clock` meant the capture's deadline (`monotonic() + duration`) was
   never reached because nothing advanced the fake. Fixed with `on_drain="timeout"` and real clocks
   plus a sub-second duration. **An option name that is silently ignored is its own small lesson.**
4. **Frames must be dicts, not JSON strings.** The fake socket `json.dumps()` whatever it is handed,
   so my JSON-string frames were double-encoded and every consumer saw a `str`. This is why the
   first passing-preflight run reported *"frames received 2, states emitted 0"* — the book snapshot
   was never a dict. Found by comparing against how `test_gap_recording.py` scripts `SNAPSHOT_FRAME`.
5. **The preflight runs in `__init__`**, not in `run()` — deliberately, "BEFORE any connection" — so
   the scoped grant environment had to wrap construction too.
6. **The preflight refused three times, correctly**, before I satisfied it: auto-mode, shutdown
   policy, grant expiry; then `LIVE_CAPTURE_UNSUPPORTED` because `DATA_SOURCE` defaulted to
   `simulated`. Every refusal was the guard working. All are scoped with `patch.dict` so they cannot
   leak into another test, and the socket is still the scripted fake.
7. **One test initially passed for the wrong reason** — asserting `_send_subscriptions` was absent
   from `_maybe_resubscribe` matched the *comment* explaining why it is absent. Rewritten to assert
   on calls with comment lines stripped.
8. **A placeholder `assert True`** in the unrecognised-channel test was replaced with two real
   assertions (the frame is uncorrupted; the counter counts).
9. **A DUPLICATE BOOK SUBSCRIPTION, caught by an existing test.** My first draft called
   `_send_subscriptions` (book **and** trade) on the reconnect path — but `_maybe_resubscribe`
   already re-sends book there, so every reconnect would have put **two book subscriptions** on one
   socket. `test_reconnect_to_effect` failed and named it. Split into `_send_trade_subscription`
   so the reconnect path adds only the half that is actually missing.
10. **A CLOCK-READ SIDE EFFECT, and a real clock-mixing bug.** The ack deadline was first set from
   `self._monotonic_clock()` (the injected clock) while the loop's liveness bounds run on
   `time.monotonic()` — mixing two clocks in one bound, the exact defect this file already carries
   a warning about. Worse, `_check_trade_ack_deadline()` read the clock **again per frame**, and
   the harness's `AdvancingClock` advances on *every read*: the extra tick tripped a spurious
   reconnect and broke `test_termination_log_level` and `test_reconnect_to_effect`. Fixed by
   putting the ack deadline on the loop's own clock and **passing the value the loop already
   read**, so the check costs no clock read at all.
11. **⚠ FINDING — TWO DISTINCT `Settings` CLASS OBJECTS EXIST UNDER THE FULL SUITE.**
   `config.settings.Settings is trading.data.adapters.factory.Settings` evaluates to **False**
   when the whole suite runs, because the package is reachable by more than one `sys.path` route.
   `Settings.DATA_SOURCE` is also bound from `os.getenv` **at import time**, so neither an env var
   nor a patch on the locally-imported class reaches the copy the factory reads. This is why the
   witness passed alone and failed in the full suite. Worked around by patching the object the
   production code actually holds (`adapter_factory.Settings`), with the reasoning recorded at the
   site. **Not fixed here — it is a repo-wide import-hygiene defect outside this WO's scope, and
   it silently defeats configuration patching in any test that tries it. Recommend a follow-up.**
12. **My own diagnostics hid the cause.** `_run_capture` swallowed the exception from `cap.run()`,
   so a `LIVE_CAPTURE_UNSUPPORTED` refusal presented as "no frames written". Now surfaced under
   `WITNESS_DEBUG=1` — a swallowed exception is its own small version of a query that cannot fail.
13. **Two harness details cost real time, both mine:** `on_drain="raise"` is not a valid option and
   silently fell through to `"block"` (wait forever); and the fake socket `json.dumps()` whatever
   it is handed, so scripted frames must be **dicts** — JSON strings get double-encoded and every
   consumer sees a `str`. Both are recorded in the test file so the next person does not repeat them.
14. **No socket opened.**

---

## §9 ACCEPTANCE

- [x] Both channels subscribed, per-channel ack tracking, single send path
- [x] Demux with the non-book/non-trade set **enumerated** (six kinds) and unknowns counted
- [x] **Book-path preservation dual proven** — and it holds under the mutation
- [x] Reconnect resubscribes both; the trade-only failure is recorded as `TRADE_CHANNEL_DROPPED`
- [x] Merger lifecycle declared and proven across **rotation** and **seam**
- [x] Writer emits the schema's three states
- [x] **Reachability witness passing, with its discard-mutation asymmetry**
- [x] `corpus_20260805` untouched — v1 `e3ab1aec…`, 38/38 capture hashes
- [x] Every BUILT row's reachability cell filled — **no empty cells**
- [x] Gates: lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

### Test count arithmetic

```
  509  baseline at HEAD e3f2625 (WO-055 close, CI 31240124483)
+  16  tests/test_trade_capture_wiring.py (new — the reachability witness)
─────
  525  expected  (+ 2 skipped)
```

| Leg | Order A | Order B (seed 56056) |
|---|---|---|
| Python 3.14.6 | **525 passed, 2 skipped** (314.97s) | **525 passed, 2 skipped** (314.72s) |
| Python 3.11.15 | **525 passed, 2 skipped** (312.87s) | **525 passed, 2 skipped** (313.38s) |

Two existing tests were updated, not silently: `test_reconnect_to_effect` (expectation widened to
both channels, book half unweakened and now checked *by channel*) and its neighbours listed under
EVERY ATTEMPT. Net count is +16, all new.

### CI — **run `31264684723`, GREEN both legs** (commit `907e917`)

| Job | Deterministic | Randomised |
|---|---|---|
| `test (3.11)` — 93120813923, 10m46s | **525 passed, 2 skipped** (312.85s) | **525 passed, 2 skipped** (307.67s) |
| `test (3.14)` — 93120813966, 10m49s | **525 passed, 2 skipped** (312.06s) | **525 passed, 2 skipped** (309.68s) |

Eight independent runs (four local, four CI) all report 525/2. Note what CI *cannot* tell you on
its own, and why this WO exists: a green suite is exactly what a well-tested but unreachable
component produces. The witness is what closes that gap.

---

## FILES

| File | Disposition |
|---|---|
| `src/trading/data/adapters/kraken_v2_book.py` | **CHANGED** — trade subscribe, demux, ack handling, reconnect, `_utc_now_iso` |
| `src/trading/logkit/decision.py` | unchanged this WO (codes declared in WO-054) |
| `tools/live_corpus_capture.py` | **CHANGED** — one line: the production call site |
| `tests/test_trade_capture_wiring.py` | **NEW** — 16 tests, the reachability witness |
| `tools/wo056_reachability_bite_proof.py` | **NEW** — PASS, with the asymmetry |
| `captures/corpus_24h/corpus_20260805/` | **READ-ONLY — untouched**, verified twice |
