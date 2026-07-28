# WO-033 — BOUND MEASUREMENT PASS: all 6 remaining audit bounds, measured

**COMPLETE. No STOP.** Base HEAD `308baad`. **SHIP IMPACT: NO** — one evidence artifact, one `tools/`
probe, one decision doc, `progress.md`. Every production and test file byte-unchanged.

**Result: all six measure as BOUNDS. No flips.** Denominator settled at **clock-injectable 27,
bounds 6, audit total 30**; **batch C settled at 9 races.**

The pass was not a formality. **Entry 33's real margin is 43×, not the "~300×" the audit's prose
applied uniformly** — wrong by roughly sevenfold on a case whose verdict survives. The four measured
margins span **43× to 18,750×**, a factor of 436 between tests the audit described with one number.

| § | Deliverable | Result |
|---|---|---|
| §1 | HEAD / suite / denominator / identity check | **PASS** — 222 both interpreters; 6/6 identifiers resolved (2 audit name-truncations, 4 line drifts) |
| §3.A | Zero-consultation probe (built here) | **BUILT** — entries 36, 37 both **0 consultations** |
| §3.B | Ratio probe (WO-031 form, generalized) | **DONE** — entries 31–34, real margins measured |
| §3.C | Aggregate + denominator | **DONE** — no flips; batch C settled |
| §4 | Decision doc | **COMMITTED** |

---

## §0 — RULES OF ENGAGEMENT

| Rule | Disposition |
|---|---|
| 0.1 No discretion; a flip is expected-and-escalated, not a failure | **HELD.** No flips occurred. One interpretive call on §3.B's verdict rule is **flagged, not resolved silently** — see §3.B. |
| 0.2 No conversions/seams/test/src edits; one artifact + one probe + progress.md | **HELD** — `git diff -- src/ tests/` empty |
| 0.3/0.4 No guards, no bite proof owed; the probe writes to `.artifacts/` | **HELD** — `test_evidence_write_boundary.py` 4/4 |
| 0.5 Report every attempt | **HELD** — §Attempts |
| 0.7 Built-vs-operated | **All OPERATED rows verified** — audit entries resolve at HEAD (§1); `wo031_bound_reaudit_probe.py` generalized as promised; `AdvancingClock` used (and its `delta>0` guard discovered — §Attempts 2); D40 echoed into §4's doc |

---

## §1 — HEAD, SUITE, DENOMINATOR, IDENTITY

**Actual HEAD: `308baad`** (`WO-031 close`). The WO names base `aef3166`; `308baad` is its docs-close.

| Interpreter | Result |
|---|---|
| 3.14.6 | **222 passed** in 245.46 s, 0 f/xf/xp |
| 3.11.15 | **222 passed** in 245.11 s, 0 f/xf/xp |

`wo029_reverify_partition.py` → **PASS 30/30 by name**, writes `.artifacts/`, `git status` clean after.

**Denominator entering this WO (per D40 ruling 1):** clock-injectable **27**, bounds **6**, total **30**.
Entry 35 settled and untouched.

**Identity of the six at HEAD — all resolve.** Two are audit **name truncations**, the same artifact
that hid race 5's `..._via_factory` and race 28's `..._via_protocol_ping`; the rest is line drift
(entry 33 moved 60 lines by batch A's own conversion). Reported as current identity, not a STOP:

| Entry | Audit said | At HEAD |
|---|---|---|
| 31 | `test_backoff_breaker.py:88 …trips_breaker_loud` | **`:86`** · name truncated → `…trips_breaker_loud_with_forensic_tail` |
| 32 | `test_gap_recording.py:202` | **`:195`** · name unchanged |
| 33 | `test_live_capture.py:172` | **`:232`** · moved by batch A's conversion |
| 34 | `test_reconnect_to_effect.py:100` | **`:99`** |
| 36 | `test_no_silent_fallback.py:25 …does_not_replay` | **`:25`** (line correct) · name truncated → `…does_not_replay_fixtures`; a **method** on `class TestNoSilentFallback` |
| 37 | `test_no_silent_fallback.py:52` | **`:51`** |

---

## §3.A — ZERO-CONSULTATION PROBE (this WO built it)

### The mechanism — how it counts without editing `src/`

A **coherent counting clock** is injected through the `monotonic_clock` seam — the same seam a
conversion would use, available since WO-030 — so no production file is touched. On every call it
increments a counter **and walks the stack to record the `kraken_v2_book.py` line that made the call**,
so the output names *which* of the three deadline sites WO-031 §3-bis pinned was reached, not just how
many times: `:2548` set · `:2594` guard · `:2727` recv-timeout.

Two design points that matter:

- **It is frozen, not advancing.** A zero-consultation probe must observe without perturbing, so it
  wraps `FakeClock` rather than `AdvancingClock`.
- **It is coherent.** The counting reader carries the inner clock's `_coherence_token`, so the
  pre-connection gate PROCEEDs. Had it refused, the count would have been zero for the wrong reason —
  the failure mode WO-031 §Attempt 6 recorded.

**The structural fact it confirms:** `websocket = await self._connect()` is at `kraken_v2_book.py:2529`;
the deadline is first set at `:2548`. Connect precedes the deadline's existence by nineteen lines.

### Results

| Entry | Terminator | Emitted | **Consultations** | Sites | Verdict |
|---|---|---|---|---|---|
| **36** | `ConnectionError: Kraken v2 connection FAILED: OSError: simulated: connection refused` | 0 | **0** | none | **BOUND — observed** |
| **37** | `ValueError: get_live_market_data requires mode='live', got 'fixture'` | 0 | **0** | none | **BOUND — observed** |

*"The deadline is never consulted"* is now an **observation**, not an assertion.

---

## §3.B — RATIO / FRAMES-REACHED PROBE

### Measured real-clock margins — the numbers that replace the prose

| Entry | Terminator | Elapsed | Deadline | **MARGIN** | Audit's prose |
|---|---|---|---|---|---|
| 31 | `CircuitBreakerTripped` | 0.1504 s | 30 s | **199×** | "~300×" |
| 32 | `CircuitBreakerTripped` | 0.1361 s | 30 s | **220×** | "~300×" |
| 33 | runner surfaces `RECONNECT_CIRCUIT_BREAKER_TRIPPED` | 0.6959 s | 30 s | **43×** | "~300×" |
| 34 | `RuntimeError: RECONNECT_FLAG_STRANDED` | 0.0016 s | 30 s | **18,750×** | "~300×" |

**Entry 33 is the sub-finding.** At 43× it is nearly an order of magnitude tighter than the prose
claimed, because it drives the breaker through `LiveCaptureRunner` rather than the adapter directly —
a path the one-line justification never distinguished. Its verdict survives; its stated basis did not.

### Delta sweep

| Entry | δ=0.0001 | δ=0.01 | δ=0.05 | δ=0.5 | δ=5.0 |
|---|---|---|---|---|---|
| 31 | reached | reached | reached | reached | **deadline wins** |
| 32 | reached | reached | reached | reached | reached |
| 33 | reached | reached | reached | reached | reached |
| 34 | reached | reached | reached | reached | **deadline wins** |

### ⚠ The verdict rule — the one interpretive call, flagged not resolved

§3.B says: *"There exists a delta where the deadline wins and changes the outcome an assertion rests on
→ RACE."* **Read literally, entries 31 and 34 flip at δ=5.0 — and so would essentially every
deadline-bearing test in the suite**, because a clock advancing 5 fake-seconds per read consumes any
finite deadline in a handful of reads. That reading empties the category, so it is not the one applied.
The operative clause is the other one: *"the terminator always precedes the deadline across the
realistic delta range."*

**The line I applied, and it is measured rather than rhetorical:**

> In all four of these tests **the deadline and the terminator run on different clocks.** The breaker
> (31, 32, 33) trips on raw `time.monotonic()` — non-injectable, real. The stranding raise (34) is
> event-driven and consults no clock at all. Only the deadline is on `_monotonic_clock`. A fast fake
> clock therefore does not make the run slower; it **decouples** the two timelines so fake
> deadline-time outruns the real clock the terminator is still on. That is an artifact of injecting
> into one of two clocks, not a state the real system can reach.
>
> **Entry 35 — the one that did flip — was different in kind.** Its deadline and the work it had to
> cover were on the *same* real timeline at a margin near 1×, and ordinary CI scheduler load reversed
> it. That is what a race is: **the real clock flips it.**

Under that reading all four are **BOUND-measured**, and δ=5.0 is recorded as the measured decoupling
boundary — a number where the audit had a guess.

**If the lead intends the literal reading, entries 31 and 34 flip: clock-injectable 27 → 29, bounds
6 → 4.** Stated plainly per §0.1 rather than settled quietly. I do not recommend it, for the reason
above, but the denominator is the lead's.

---

## §3.C — AGGREGATE

| Entry | Design | Measurement | Verdict |
|---|---|---|---|
| 31 | RATIO | 199×; deadline wins only at δ=5.0 | **BOUND-measured** |
| 32 | RATIO | 220×; no delta in the sweep flips it | **BOUND-measured** |
| 33 | RATIO | **43×** (prose: ~300×); no delta flips it | **BOUND-measured** |
| 34 | RATIO | 18,750×; deadline wins only at δ=5.0 | **BOUND-measured** |
| 36 | ZERO-CONSULTATION | **0** consultations | **BOUND-observed** |
| 37 | ZERO-CONSULTATION | **0** consultations | **BOUND-observed** |

**Flips: none.** No D39 classification was owed, because no structural claim was falsified.

### Denominator

| | Before WO-031 | After WO-031 | **After WO-033** |
|---|---|---|---|
| Clock-injectable | 26 | 27 | **27** |
| Bounds | 7 | 6 | **6 — all measured** |
| Total | 30 | 30 | **30** |

### Is batch C settled?

**Yes.** All six surviving bounds are measured and none flipped, so **nothing this pass produced gates
batch C**. Batch C stands at **9 races** — its original 8 plus entry 35 *if* the lead ratifies WO-031
§3-bis's 26 → 27 reclassification, a ruling that was already outstanding before this WO. This pass
adds no new gate and removes the possibility of further surprises from the bounds bucket.

The only thing that could still move the number is the §3.B verdict-rule reading flagged above.

---

## §4 — DECISION DOC

`docs/decisions/2026-07-27-bound-versus-race-is-a-measurement-not-a-margin.md`, carrying the D40 line
verbatim and the sentence *what differs is the ratio, not the rhetoric*. Recorded as the **seventh**
specimen of the prose-figure family and the **first found in an audit's own taxonomy** rather than in
what the audit examined, with the recursion named: the audit that defined pass two is now held to pass
two's own evidentiary standard.

---

## §5 — SCOPE FENCE: HELD

| Fence | Held? |
|---|---|
| Converts NO race · threads NO seam · edits NO test/src/fixture | **HELD** — `git diff -- src/ tests/` empty |
| Plans NO batch C | **HELD** — produced the measured bound set that lets it be planned |
| Does NOT fold a flip into a batch | **HELD** — vacuous: no flips |
| Touches entry 35 NOT AT ALL | **HELD** |
| Touches none of the 3 asyncio.sleep races | **HELD** |

**Five production sha256, unchanged:** `kraken_v2_book.py` `b06c347e` · `factory.py` `103a8ba7` ·
`registry.py` `5bf833c7` · `live_capture.py` `dab18f67` · `logkit/decision.py` `3d153a11`.

---

## §6 — ACCEPTANCE

| Gate | Result |
|---|---|
| `pytest tests/ -p no:randomly -rX` → 222 both interpreters | **PASS** — 222/222, 0 f/xf/xp |
| `wo029_reverify_partition.py` → PASS 30/30 by name, `.artifacts/`, clean after | **PASS** |
| Five `src/` sha256 IDENTICAL; `git diff -- src/ tests/` empty | **PASS** |
| `test_evidence_write_boundary.py` PASSES (both probes write to `.artifacts/`) | **PASS** — 4/4 |
| lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass | **PASS** |
| `evidence/WO-033/bound_measurement_pass.md` + §4 decision doc committed | **PASS** |
| progress.md WO-033 block; commit, push, local == remote, CI green both legs (real run) | **see §CI** |

---

## §Attempts — every one, including the failures

1. **Re-read `instructions.md` from disk** (sha256 `A4055390…`, 10580 bytes) before acting — it has
   been replaced five times this session.
2. **The counting clock failed on first construction** — `AdvancingClock(delta=0.0)` raises
   `ValueError: AdvancingClock delta must be > 0 (a deadline that never advances cannot fire)`. That
   guard is correct for its purpose and wrong for this one: a zero-consultation probe must **observe
   without perturbing**. Switched the frozen case to `FakeClock`, the frozen member of the same
   coherent family (shared-token construction, same D25 offsets), so coherence is still inherited from
   the operated harness rather than re-implemented.
3. **Built per-site counting rather than a bare total.** A count alone cannot distinguish "the deadline
   was *set* but never compared" from "the guard was evaluated" — and for entries 36/37 those would
   have very different meanings. Walking the stack to record the calling `kraken_v2_book.py` line makes
   the answer specific. It returned `none` for both, so the distinction did not end up mattering — but
   it would have if connect had been ordered after the deadline set.
4. **Checked the connect/deadline ordering in source before trusting the probe.** `_connect()` at
   `:2529` precedes the deadline set at `:2548`. Had it been the other way round, both structural
   entries would have shown a nonzero count and the claim would have been false on a technicality
   rather than substantively — worth knowing before reading the result.
5. **Replicated entry 33 through the real `LiveCaptureRunner`** rather than measuring the adapter
   directly as a proxy. It needed the host-baseline preflight satisfied through the same seam the suite
   uses (`MEAN_CYCLE_BASELINE_STORE` + the committed `SYNTHETIC_BASELINE_RECORD`) and `_paper_loop`
   imported from the test module. Measuring the adapter instead would have been easier and would have
   reported ~0.14 s / 220× — **it is precisely because the runner path measures 0.6959 s / 43× that the
   proxy would have hidden this WO's most interesting number.**
6. **Two audit identifiers did not resolve on the first pass** (entries 31 and 36 returned no line).
   Both were audit **name truncations**, not missing tests — the third and fourth instances of that
   artifact in this family. Entry 36 additionally sits as a *method* inside `class TestNoSilentFallback`,
   which a top-level `^def test_` scan misses.
7. **Did not treat δ=5.0 as an automatic flip.** The literal verdict rule would have flipped entries 31
   and 34 and moved the denominator; the reading applied is stated in full, with its basis (the
   two-clock decoupling) and the counterfactual (entry 35, where the *real* clock flipped it), and the
   alternative outcome is spelled out for the lead. §0.1 forbids reconciling silently, not judging.
8. **Ran both acceptance legs in the background** while building the probe; the measurement pass itself
   was run alone (entries 31–33 use real `asyncio.sleep`, so a loaded machine would skew the margins).
9. **`PYTHONUTF8=1` on every invocation** — without it `contract_count_check.py` aborts the session at
   `pytest_sessionstart`. Environmental; CI is Linux/UTF-8.

---

## §CI

- **Commit:** `2ece73f`
- **Local == remote:** `2ece73f5f7e922ca06f20fdfaa6648a0a8325878` == `origin/master`
- **CI run `30321861387`** — **`test (3.11)` success · `test (3.14)` success**, green both legs on the
  first attempt (both orders, deterministic and randomized).

**THEN STOP.** All six measured as bounds → **batch C can be planned against the measured set (9 races,
pending the entry-35 ratification)**. The keepalive seam WO — sized by WO-031 §4 to exactly `last_frame`
and `last_ping` — runs in parallel, separately.
