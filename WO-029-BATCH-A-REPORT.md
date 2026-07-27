# WO-029 — PASS TWO, BATCH A: the first cluster of the 26 races converted to deterministic

**BASE / HEAD at start:** `d0450fa` on master — *not* the `9c084c3` the WO names. §1 confirmed the
actual HEAD and used it, as the WO directs. `d0450fa` is this same WO's own committed §2.0 + §2.0-bis
seam (the partition + the `AdvancingClock` harness build), which the prior session landed when its
context ran out; `9c084c3` is its parent. **The remainder — §2, §3, §4, §7 — is what this report covers.**

**SHIP IMPACT: NO.** Every production file byte-unchanged; §5 proves it with the five sha256s and an
empty `git diff -- src/`.

**RESULT: batch A converts WHOLE.** `test_live_capture.py` races 1, 2, 3, 4, 5 are all deterministic;
race 4 via the self-advancing fixture, race 5 through the runner→factory→builder seam. 218 unchanged.

---

## §0 RULES OF ENGAGEMENT — disposition

| Rule | Disposition |
|---|---|
| 0.1 No discretion; code wins → STOP and report | No STOP was reached. Two places where I formed a reading rather than following text literally are reported in full at §6 — neither was reconciled silently. |
| 0.2 No monkeypatching to make a guard pass; migrate transports in the same edit | Nothing monkeypatched. All five races were **already** transport-migrated (races 1–4 by WO-024 pass one, race 5 by WO-028 §5), so no transport migration rode along. The file's one remaining `patch("websockets.connect", …)` is in `test_live_capture_refuses_non_live_capable_data_source`, which is **not** one of the 30 audit races and injects no clock — untouched. |
| 0.3 Every guard/assertion touched gets a fail-then-pass bite proof | **No assertion was touched** — proved mechanically below. The two bite proofs this WO owes are §2.0-bis's (committed at `d0450fa`, re-verified here) and §4's (new). |
| 0.4 Preservation duals mandatory, local and direct | §2.0-bis's fixture proof carries its dual (fires / does-not-fire-prematurely). §4's proof carries its dual (pristine net quiet / mutated net bites). |
| 0.5 Report every attempt, including failures and retries | §9. |
| 0.6 Report `/context` at START and at the commit seam | **NOT DONE — and I could not do it.** `/context` is a user-side slash command; an agent turn cannot invoke it and I will not paste a number I did not read. Flagged as the one unmet acceptance item. |
| 0.7 BUILT-VS-OPERATED (D24) | All OPERATED rows verified as stated — table below. |

### §0.7 — the OPERATED rows, verified at this HEAD

| Thing | Verified how |
|---|---|
| WO-023 §1 audit (30 races, enumerated) | Re-derived: `tools/wo029_reverify_partition.py` → 30/30 identifiers land at their stated file:line. |
| Coherent FakeClock harness (shared token) | In `tests/fixtures/fake_ws_transport.py`; the gate reads the shared `_coherence_token` and every batch-A race records `PROCEED_COHERENT`. |
| `_wall_clock` / `_monotonic_clock` adapter seams | Both injected by all five conversions; the deadline demonstrably runs on the injected monotonic (§3 PART A). |
| `connect_fn` seam (runner/factory/builder) | Race 5 injects its transport through the runner; `connect_count == 1` and the factory-built adapter holds the injected callable (§3 PART B). |
| **Clock seam (runner/factory/builder) — race #5 injectable** | **CONFIRMED, and this was the row to check.** `LiveCaptureRunner(monotonic_clock=…, wall_clock=…)` → `create_live_capture_feed` → `_build_kraken_v2` → the adapter. §3 PART B shows the factory-built adapter holding *the very callables* handed to the runner. WO-030 achieved its purpose. |
| Gate ledger + marker exclusion + snapshot tool | §4 shows the ledger's session-end assertion still fires and names the nodeid; snapshot taken into `evidence/WO-029/`. |
| The 26-race A/B/C partition | Built by this WO's §2.0, committed at `d0450fa` (`evidence/WO-029/batch_partition.md`), re-verified here. |
| Self-advancing coherent clock fixture | Built by this WO's §2.0-bis, committed at `d0450fa`; bite proof re-run at this HEAD, still PASS. |

---

## §1 — HEAD AND THE STARTING SUITE

```
HEAD  d0450fa3ba6a59774901c102ff64980470c223d2   (working tree clean)
```

| Leg | Command | Result |
|---|---|---|
| 3.11 strict (`CPython 3.11.15`, uv venv) | `pytest tests/ -p no:randomly -rX` | **218 passed** in 244.99s, 0 f/xf/xp |
| 3.14 dev (`CPython 3.14.6`) | `pytest tests/ -p no:randomly -rX` | **218 passed** in 245.91s, 0 f/xf/xp |

218 as WO-030 left it. No edit was made before this confirmed.

---

## §2.0 — THE 26 RE-ENUMERATED AT THIS HEAD, AND THE PARTITION

The partition was derived one commit ago at base `9c084c3` and committed as
`evidence/WO-029/batch_partition.md`. D34-3's discipline — *an enumeration is only as good as its
identifiers*, the ruling that caught race #5 — forbids simply trusting it, so it was **re-derived**
rather than re-read: `tools/wo029_reverify_partition.py` parses the committed table and checks, for
each of the 30 races, that the named test really does begin at the stated `file:line`, reading the
lines from the **commit** rather than the working tree so a mid-conversion tree cannot flatter the
result. Evidence: `evidence/WO-029/partition_reverified_at_head.txt`.

```
identifiers verified at their stated line : 30/30
moved / missing                           : none
category counts   : {'CLOCK-INJECTABLE': 26, 'ALREADY-CONVERTED': 1, 'ASYNCIO-SLEEP': 3}  -> True
the 3 asyncio-sleep races, BY NAME        : True
race #5 is in the 26 (CLOCK-INJECTABLE)   : True
VERDICT: PASS
```

- **The injectable count is 26.** No STOP.
- The 3 excluded asyncio-sleep races are the named set (`…_records_rtt_distribution_via_protocol_ping`
  — the audit's truncation of race 28's name, flagged in the partition and carried here —
  `test_absent_pongs_are_a_signal_not_gappiness`, `test_starved_lag_sampler_self_reports_degradation`).
  The exclusion denominator did not change.
- **Race #5 is in the 26**, CLOCK-INJECTABLE via the runner seam. It is the **only** FACTORY-BUILT
  race; the other 25 are DIRECT. Confirmed against the table; no other race resolves through the factory.
- The full 30-row table with the construction-path column is the committed artifact
  `evidence/WO-029/batch_partition.md` (reproduced by the re-verification above row for row) — it is
  not re-pasted here, because two copies of an enumeration is exactly how the five prior wrong counts
  in this family travelled.

**The A/B/C partition (unchanged, and this WO touched only A):**

| Batch | Files | Races | Count |
|---|---|---|---|
| **A — this WO** | `test_live_capture.py` | 1, 2, 3, 4, 5 | **5** |
| B — named, not touched | `test_gap_recording.py`, `test_keepalive.py`, `test_failure_cap.py`, `test_failure_capture.py` | 6–11, 15–16, 17–19, 20–21 | 13 |
| C — named, not touched | `test_ledger_persistence.py`, `test_host_suspend.py`, `test_protocol_ping.py`, `test_throughput.py`, `test_reconnect_to_effect.py`, `test_venue_close_path.py`, `test_backoff_breaker.py` | 12, 14, 22–23, 24, 25, 26, 27 | 8 |

5 + 13 + 8 = **26**.

---

## §2.0-bis — THE SELF-ADVANCING COHERENT CLOCK FIXTURE

Built and bite-proved in this WO's prior session; `AdvancingClock` lives in the shared harness
`tests/fixtures/fake_ws_transport.py`, extending it beside `FakeClock` rather than as a new module.
It is the frozen harness made to move: one counter, the same D25 offsets (monotonic ORDERS from a
small boot-relative base, wall LOCATES from an epoch base), the same shared `_coherence_token` — so
it passes the gate's COHERENCE check exactly as the frozen pair does — with the counter advancing by
`delta` on every **monotonic** read, the deadline clock. Parameterized by `delta` alone, so a future
deadline race constructs one without bespoke code.

Bite proof re-run at this HEAD (four artifacts, sha256 exact-restore, both directions):
`evidence/WO-029/advancing_clock_bite_proof.txt`, `tools/advancing_clock_bite_proof.py`.

- **FIRES** — an advance that reaches the deadline ends the run via the deadline path
  (`connect_count=1`, no reconnect, `capture_terminated None`), **after** the snapshot was processed.
- **DOES NOT FIRE PREMATURELY** (the preservation dual, local and direct) — an advance too small to
  reach the threshold lets the run continue and end by clean close instead.
- **NECESSITY** — mutate the advance to `*1_000_000` and the deadline fires *before* the snapshot
  (`emitted=0`): race 4 would then pass for the wrong reason. This is the half that matters, and it
  is why race 4 could not simply be handed the frozen `FakeClock`.
- `sha256` of the harness AFTER == BEFORE (`7b17732c…`), VERDICT PASS.

---

## §2 — BATCH A CONVERTED

All five races were already transport-injected, so each conversion is purely the addition of a
**coherent clock pair from one source**: `monotonic_clock=clock.monotonic` at construction (or
through the runner for race 5) plus `_wall_clock = clock.wall`, both carrying the same
`_coherence_token`. `CLOCK_DELTA = 0.01` is shared by the file.

**What now drives time, in one sentence:** the adapter's deadline is
`_monotonic_clock() + duration_seconds` and every one of its three consumers reads that same seam, so
the capture ends after `ceil(duration/delta)` clock **reads** — a fixed count, identical every run and
every order — instead of after a real interval measured against a loaded host.

**Termination is still the deadline.** That is deliberate and is the main judgement call in this
batch; see §6.

| # | Path | Before — what drove time | After — what drives it | Transport migration rode along? | Gate ledger |
|---|---|---|---|---|---|
| 1 `…_drives_instrumented_transport_end_to_end` | DIRECT | Real 0.25 s wall window. Whether **both** book frames were consumed before the deadline was a scheduler-load gamble, and `emitted_per_minute` — the assertion — was the thing at risk. The runner's per-minute bucketing read `time.time` besides. | `AdvancingClock(0.01)` drives the adapter's monotonic deadline **and** the runner's bucketing wall (`clock=clock.wall`), one source. Deadline fires ~12 iterations in; the two frames land in iterations 1–2. | No — WO-024 pass one | `PROCEED_COHERENT` |
| 2 `…_persistence_is_not_optional_on_the_adapter` | DIRECT | Real 0.15 s wall window; the run had to survive a real interval before the configuration assertions could be read. | Same pair; deadline after a fixed read count (~7 iterations). | No — WO-024 pass one | `PROCEED_COHERENT` |
| 3 `…_short_bounded_run_completes_with_readable_artifacts` | DIRECT | Real 0.2 s wall window — "bounded" meant a real interval, so the artifacts read back from disk were whatever that interval happened to capture. | Same pair; the bound is the **same deadline**, reached on the injected seam (~10 iterations). Still deadline-terminated: `terminated is None`. | No — WO-024 pass one | `PROCEED_COHERENT` |
| 4 `…_clean_deadline_close_does_not_reconnect_dual` | DIRECT (deadline-assertion) | Both halves raced a real window; half (a)'s subject **is** the deadline, so a frozen clock cannot convert it and rescripting it as a clean close would change what the test observes (a §2 STOP). | `AdvancingClock` on **both** halves (a: 0.15 s → ~7 iterations, ~6 heartbeats served before the deadline ends it; b: 0.25 s → ~12 iterations, the reconnect completing with ~10 to spare). | No — WO-024 pass one | `PROCEED_COHERENT` ×2 (one per half) |
| 5 `…_resolves_live_adapter_from_data_source_via_factory` | **FACTORY-BUILT** | Real 0.15 s wall window. Could not be converted at construction — this test builds no adapter (`adapter=None`); it needed WO-030 to thread the clock seams through runner → `create_live_capture_feed` → `_build_kraken_v2`. | The coherent pair goes in at the **runner** boundary (`monotonic_clock=`, `wall_clock=`) and comes out held by the adapter the **factory** built — identity-proved at the far end (§3 PART B). | No — WO-028 §5 | `PROCEED_COHERENT` |

No race legitimately injects no clock, so there is no `EARLY_RETURN` among the five. (The file's
`test_breaker_trip_terminates_run_with_forensic_tail` still records `EARLY_RETURN` — it is one of the
audit's 7 legitimate BOUNDS, not one of the 30 races, and was not touched.)

### No assertion was weakened — proved, not asserted

The §2 failure mode is a "converted" test that is really a loosened one. Mechanically:

```
$ git diff -U0 -- tests/integration/test_live_capture.py | grep '^[-+]' | grep 'assert'
    (four hits, all prose inside docstrings; zero assert STATEMENTS)
$ git show HEAD:tests/integration/test_live_capture.py | grep -c 'assert '   -> 29
$ grep -c 'assert ' tests/integration/test_live_capture.py                   -> 29
```

Not one `assert` statement was added, removed, reordered, or edited. The diff is 92 insertions /
15 deletions, and every deletion is a constructor line replaced by the same constructor line plus a
clock argument. This is also why §0.3 owes no per-race bite proof: no guard or assertion was touched.

### Residual real-time reads, named

§2 says a conversion leaving any real-time dependency is incomplete. Read literally that is
unsatisfiable — `get_live_market_data` also reads the **real** `time.monotonic` for keepalive
pacing, the ping interval, the ledger anchor, `last_frame`, and the throughput/lag/pong instruments,
and none of those is an injectable seam (WO-030 threaded the deadline and suspend seams only). So I
name them rather than claim they are gone, and state what makes them harmless here: they are all
**interval** reads against thresholds of 5 s and 10 s, while the whole converted run now completes in
milliseconds of real time, and none of them feeds any assertion in these five races. The quantity each
race's assertions depend on — the capture window — is on the injected seam and is measured under
control in §3. I flag this as a reading of §2 rather than a silent judgement; see §6.

---

## §3 — THE FLAKE IS GONE: MEASURED, NOT ASSERTED

### 5 seeds + deterministic, both interpreters

Seeds: **20260802, 20260803, 20260804, 20260805, 20260806**.

Twelve full-suite runs, **218 passed every time, 0 f/xf/xp every time**:

| Ordering | 3.11 strict (`CPython 3.11.15`) | 3.14 dev (`CPython 3.14.6`) |
|---|---|---|
| `-p no:randomly` (deterministic) | **218** — 244.86 s | **218** — 245.40 s |
| `--randomly-seed=20260802` | **218** — 244.43 s | **218** — 245.25 s |
| `--randomly-seed=20260803` | **218** — 245.46 s | **218** — 246.01 s |
| `--randomly-seed=20260804` | **218** — 244.88 s | **218** — 245.72 s |
| `--randomly-seed=20260805` | **218** — 244.74 s | **218** — 245.48 s |
| `--randomly-seed=20260806` | **218** — 244.38 s | **218** — 245.19 s |

Batch A's own file was additionally run under all five seeds on its own before the matrix was
launched (10 passed each), so a per-seed failure would have surfaced in seconds rather than 40
minutes in.



### The injected clock CONTROLS the timing — `evidence/WO-029/clock_control_proof.txt`

"Still passes" is not "is now deterministic" (the WO-008b throughput VOID is the precedent). So the
representative race — race 1 — was measured, not re-run: hold **everything** fixed except the injected
clock's advance-per-read and watch the **observed capture window**, i.e. how many raw frames the
capture actually consumed before the deadline ended it.

```
   delta |                  run 1 |                  run 2 | identical?
---------+------------------------+------------------------+-----------
    0.05 |     window=2 emitted=2 |     window=2 emitted=2 | YES
    0.01 |    window=11 emitted=2 |    window=11 emitted=2 | YES
   0.002 |    window=58 emitted=2 |    window=58 emitted=2 | YES

CONTROL      : observed window is strictly monotonic in 1/delta  -> True [2, 11, 58]
DETERMINISM  : each delta reproduces its run EXACTLY on repeat   -> True
ASSERTION    : emissions pinned at the 2 scripted book frames    -> True [2]
```

Shrinking `delta` by 5× lengthens the observed window ~5×, and each setting reproduces its window
**exactly** on repeat. If the host's clock were still in charge, `delta` would not move the window and
repeats would scatter. Meanwhile the emitted deliverable stays pinned at 2 across a 29× spread of
window lengths — which is precisely the property the old test lacked: emissions no longer race the
deadline.

### Race #5's injection reaches the adapter THROUGH the runner seam

Race 5 constructs no adapter, so the proof has to be identity at the far end. The adapter below was
recovered from `factory.get_active_feed()` — i.e. it is the one the **factory** built, not one the
proof constructed:

```
built_by                     KrakenV2BookAdapter
monotonic_is_injected        True      # adapter._monotonic_clock IS clk.monotonic
wall_is_injected             True      # adapter._wall_clock      IS clk.wall
transport_is_injected        True      # WO-028's connect_fn, same path
shared_coherence_token       True      # both seams carry the ONE AdvancingClock instance
venue_name                   kraken_mainnet
connect_count                1
THROUGH-THE-SEAM: True
```

Corroborated independently by the gate ledger: race 5's nodeid records `PROCEED_COHERENT`, which can
only happen if the gate — running inside the **factory-built** adapter — saw a coherent injected pair.
Two different instruments, same conclusion. WO-030's seam carries the clock.

---

## §4 — THE LEDGER STILL BITES AFTER THE BATCH — verbatim

Batch A took five tests from "injects no clock" to "injects a coherent pair". That is exactly the
change that could turn the net into scenery, so the existing net was re-run against the new
population. Not a new guard. `evidence/WO-029/ledger_still_bites_bite_proof.txt`,
`tools/wo029_ledger_still_bites.py`. Mutation: race 1's wall taken from a **second** `AdvancingClock`
— both clocks injected, tokens mismatched; the precise failure a careless conversion produces, since
both clocks look fake and plausible and only the shared token distinguishes one source from two.

```
sha256 BEFORE: 843f5c5866804cd322cf1395ba14652279fd4f9cb4c3d660c46ffd44a53deb5c

-- ARTIFACT 1 — PRISTINE (the net is quiet because the batch is correct) --
  returncode                 0
  summary                    ============================= 10 passed in 1.25s ==============================
  gate_refused_coherence     False
  ledger_assertion_fired     False
  ledger_names_the_nodeid    False

  sha256 WHILE MUTATED: 7d5af1094192e80fa84a5f6ac5ccd9f7dd12a68e31d289fab233ac3d03afafc4

-- ARTIFACT 2 — MUTATED (the bite: an incoherent pair must NOT pass silently) --
  returncode                 1
  summary                    ==================== 1 failed, 9 passed, 1 error in 0.79s =====================
  gate_refused_coherence     True
  ledger_assertion_fired     True
  ledger_names_the_nodeid    True

  VERBATIM — the ledger's session-end assertion:
    E   AssertionError: GATE LEDGER VIOLATION.
            (1) refusals from UNMARKERED tests (a real gate firing): [('tests/integration/test_live_capture.py::test_runner_drives_instrumented_transport_end_to_end', 'REFUSED_COHERENCE')]
            (2) STALE markers (markered tests that never refused): []
            markered set: []. See C:\Projects\bot\trading-system\.artifacts\gate_ledger\20260727T145220Z-d0450fa.txt.

-- ARTIFACT 3 — RESTORED --
  returncode                 0
  summary                    ============================= 10 passed in 1.15s ==============================
  gate_refused_coherence     False
  ledger_assertion_fired     False

-- ARTIFACT 4 — sha256 EXACT-RESTORE --
sha256 AFTER:  843f5c5866804cd322cf1395ba14652279fd4f9cb4c3d660c46ffd44a53deb5c
IDENTICAL: YES

VERDICT: PASS
```

Both halves of the net fired: the **gate** refused pre-connection with `COHERENCE` (so the test
failed) **and** the **ledger's** session-end assertion named the exact nodeid — so a refusal survives
even if a test-level failure were swallowed. The net did not go slack.

---

## §5 — SCOPE FENCE

| Fence | Held? |
|---|---|
| BATCH A ONLY; B and C named, not touched | Yes — the only test file modified is `tests/integration/test_live_capture.py`. |
| The 3 asyncio.sleep races not touched | Yes — `test_pong_observer.py`, `test_lag_sampler.py` unmodified. |
| **NO production logic changes** | Yes — `git diff -- src/` is **empty**. Five hashes below, all identical to WO-030's. |
| NO new reason codes | Yes — `logkit/decision.py` byte-unchanged. |
| NO gate docstring precision note (D37) | Yes — `kraken_v2_book.py` byte-unchanged. |
| NO weakening of any assertion | Yes — 29 assert statements before and after, none in the diff. |

```
b06c347e66ded3a739505c7f6598a6de3eb40f38b2019ac2cca3a1c4c3889615  src/trading/data/adapters/kraken_v2_book.py
103a8ba793c6c1d2bff6012095e9616a9e7ab5d92f428eadd7f2b194a041834c  src/trading/data/adapters/factory.py
5bf833c78fd3b91e055e91c08026da2439801cf124c485928ecf8f492ba38a68  src/trading/data/adapters/registry.py
dab18f67a7f334d746a72d3a34944e7212961fac1685ae09d6973213ef58d0ff  src/trading/loop/live_capture.py
3d153a110248ec5395d9b74be7631009a53eae966659f7852985e73dcefee337  src/trading/logkit/decision.py
```

All five match the WO-030 report's stated prefixes (`b06c347e…`, `103a8ba7…`, `5bf833c7…`,
`dab18f67…`, `3d153a11…`) exactly. **Also unchanged:** `conftest.py` (the ledger instrument needed no
edit to guard the larger population) and `tests/fixtures/fake_ws_transport.py` (the fixture was built
at `d0450fa` and is used as-is — extended, not rebuilt).

---

## §6 — DECISION LOG: ONE CANDIDATE PROPOSED, ONE READING FLAGGED

No entry was written. Both items below are reported for a ruling, per §0.1 and §6.

### Candidate entry — *a conversion must preserve the path, not merely the assertions*

**What happened.** The committed partition (`batch_partition.md`, written by this WO's earlier
session) planned races 1–3 as "inject `FakeClock` at construction, terminate via scripted
clean-close". I did not do that. All five races use the **self-advancing** clock and still terminate
at the **deadline**.

**Why.** The frozen-clock plan works — every assertion in races 1–3 passes under it, because none of
them asserts *how* the run ended. But it would have quietly moved three tests off the deadline branch
of `get_live_market_data` and onto the `ConnectionClosedOK` branch. Races 1–3 are the end-to-end
wiring proofs for a capture that, in production, ends at minute 60 by deadline; converting them to
exercise the venue-close path instead would leave the deadline branch's end-to-end coverage resting on
race 4 alone — while every gate stayed green and no assertion ever complained. Race 3 is named
`test_short_bounded_run_completes_…`; the bound is its subject.

**The general shape.** *A test's assertions do not fully specify which production path it covers. A
conversion that keeps every assertion passing while changing the path the test takes is a coverage
loss that no assertion can report.* This is the same family as D24 (built-vs-operated) and the
"incidental coverage is not coverage" entry, one level out: **incidental path coverage is still
coverage, and silently trading it away is the cheap conversion's failure mode.** Cost of avoiding it
was near zero here, because §2.0-bis had already built the fixture that makes a deadline fire.

**Proposed title:** *a conversion preserves the path, not just the assertions.* Not written — awaiting
a ruling. If ratified it should also amend `batch_partition.md`'s parenthetical plan for batches B and
C, whose races will face the same choice.

### Flagged reading — §2's "any real-time dependency"

§2 says "a conversion leaving any real-time dependency is incomplete — name it and STOP rather than
half-converting." Read literally this cannot be satisfied by any of the 26: `get_live_market_data`
holds several **non-injectable** real-clock reads (keepalive pacing, app-ping interval, ledger anchor,
`last_frame`, the throughput/lag/pong instruments), and WO-030 threaded only the deadline and suspend
seams. Taken literally, pass two would STOP on race 1 and never proceed — which contradicts the WO's
own premise that 26 races are convertible.

**My reading, applied:** the clause targets a real-time dependency the test's **outcome** rests on. I
named the residuals (§2, "Residual real-time reads") and showed they are interval reads against 5 s
and 10 s thresholds in a run that now finishes in milliseconds, feeding no assertion in these five
races. **I did not STOP.** If the lead intends the literal reading, batch A is a STOP and so is every
remaining batch, and the correct next step is a production WO to thread the remaining clock reads —
so this needs a ruling before batch B, not after.

---

## §7 — ACCEPTANCE

| Gate | Result |
|---|---|
| `pytest tests/ -p no:randomly -rX` = **218**, 0 f/xf/xp | **PASS**, both interpreters. **Test-count arithmetic: 218 + 0 = 218.** Batch A converts; it adds, removes, splits and merges nothing. The two new instruments are standalone `tools/` scripts, not suite tests. |
| `pytest tests/ --randomly-seed=<5 seeds>` all green, both interpreters | **PASS** — 10 runs, table above |
| Gate ledger: 0 unmarkered refusals, 0 stale markers; batch-A dispositions as stated | **PASS** — 43 invocations (unchanged from WO-030): 29 `EARLY_RETURN`, 8 `PROCEED_COHERENT` (6 of them batch A's — race 4 records twice, once per half), 2 `PROCEED_DECLARED` (the suspend test — still the sole unmarkered declared-incoherent customer — plus one inside the gate's own test), 3 `REFUSED_COUPLING` + 1 `REFUSED_COHERENCE` **all four from the two markered gate tests**. Unmarkered refusals `[]`, stale markers `[]`. Snapshot: `evidence/WO-029/gate_ledger.txt`. |
| §2.0-bis fixture: bite proof BOTH directions, 4 artifacts, sha256 exact-restore, in the shared harness, coherent-token-passing | **PASS** — re-run at this HEAD, `sha256` after == before (`7b17732c…`), VERDICT PASS. `AdvancingClock` lives beside `FakeClock` in `tests/fixtures/fake_ws_transport.py`, stamping the same `_coherence_token` on both readers. |
| §4 ledger-still-bites: 4 artifacts, sha256 exact-restore | **PASS** — `843f5c58…` after == before, VERDICT PASS |
| Batch A = `test_live_capture.py` → all five races (1,2,3,4,5) convert together; race 4 via the self-advancing fixture, race 5 through the runner seam | **PASS — the file converts WHOLE.** No file is split across batches. |
| Every production file sha256 IDENTICAL before/after | **PASS** — five hashes at §5, all matching WO-030's; `git diff -- src/` empty |
| `lint-imports` 6/6 | **PASS** — 6 kept, 0 broken |
| `contract_count_check.py` 6/6 | **PASS** — "import-linter evaluated 6 contracts (expected 6)" |
| `ruff` clean | **PASS** — "All checks passed!" |
| `annotation_name_scan.py` 0 | **PASS** — 0 names |
| `preflight_path_check.py` | **PASS** — `trading` resolves inside the repo tree |
| `evidence/WO-029/batch_partition.md` committed | **PASS** — committed at `d0450fa`; re-verified here |
| Snapshot the gate ledger into `evidence/WO-029/` via `tools/snapshot_gate_ledger.py` | **PASS** |
| Append a WO-029 (pass two batch A) block to `progress.md` | **PASS** |
| Commit, push, local == remote, CI green BOTH legs | <!--CI--> |
| `/context` at START and at the commit seam (§0.6) | **NOT DONE** — see §0. An agent turn cannot invoke a user-side slash command; no number was fabricated. |


---

## §8 — ARTIFACTS

| Path | What |
|---|---|
| `evidence/WO-029/batch_partition.md` | The 30-race table + A/B/C partition (committed `d0450fa`) |
| `evidence/WO-029/partition_reverified_at_head.txt` | 30/30 identifiers re-derived at this HEAD |
| `evidence/WO-029/advancing_clock_bite_proof.txt` | §2.0-bis fixture, 4 artifacts, both directions |
| `evidence/WO-029/clock_control_proof.txt` | §3 real control + race #5 through the runner seam |
| `evidence/WO-029/ledger_still_bites_bite_proof.txt` | §4, 4 artifacts, sha256 exact-restore |
| `evidence/WO-029/gate_ledger.txt` | §7 gate-ledger snapshot (provenance-stamped) |
| `tools/wo029_reverify_partition.py` | Re-derivation instrument — **batches B and C should re-run this** |
| `tools/wo029_clock_control_proof.py` | §3 instrument |
| `tools/wo029_ledger_still_bites.py` | §4 instrument |

---

## §9 — EVERY ATTEMPT, AND EVERY STOP

**STOPs: none.** No code-wins contradiction was reached. The two judgement calls are reported at §6
rather than resolved silently.

**Attempts, including the failures:**

1. **The first baseline run crashed before collection** — `TypeError: unsupported operand type(s) for
   +: 'NoneType' and 'str'` inside `tools/contract_count_check.py`, from `pytest_sessionstart`. Root
   cause is environmental, not a defect: `subprocess.run(text=True)` decodes the import-linter child's
   output with the parent's locale encoding, this shell's is cp1252, and import-linter emits a byte
   (`0x90`) that cp1252 cannot decode, so the reader thread dies and `proc.stdout` is `None`. Fixed by
   running every command in this session with `PYTHONUTF8=1`. **No repo file was changed for it** —
   CI runs on Linux/UTF-8 and is unaffected. Worth recording because the guard's failure mode is a
   session-abort with a message that points at arithmetic rather than at encoding.
2. **§3 PART B first reported `transport_is_injected: False`, VERDICT FAIL.** My check compared
   `adapter._connect_fn is conn.connect` — but `conn.connect` is a **bound method**, and every
   attribute access mints a fresh object, so `is` against it is False no matter what was threaded. A
   bug in the instrument, not a finding about the seam. Fixed to compare the two stable parts
   (`__func__` and `__self__`); the clock seams need no such care because `clk.monotonic`/`clk.wall`
   are instance attributes holding one closure object each. Recorded because it is a plausible way to
   manufacture a false through-the-seam failure — or, with the comparison the other way round, a false
   success.
3. **`AdvancingClock`'s firing point was measured before it was relied on**, not derived on paper. A
   throwaway probe swept `(delta, duration, script)` across all five races' shapes; the read-count
   arithmetic I had worked out by hand was off by one on race 1 (predicted 12 recvs, actual 11), which
   is exactly why `CLOCK_DELTA = 0.01` was chosen to leave the frames a wide margin rather than to sit
   at the boundary. The margin is now permanently measurable via `tools/wo029_clock_control_proof.py`.
4. **Batch A was run under all 5 seeds on its own file before the full matrix was launched**, to avoid
   discovering a per-seed failure ~40 minutes into a 12-run matrix. All 5 green.
5. **The §2.0-bis and §4 bite proofs mutate tracked files**, so both were run to completion — including
   their sha256 exact-restore — with no suite running concurrently. The restore was verified against
   `git status` before the acceptance matrix started.
6. **No production edit was attempted**, so the auto-mode classifier was never engaged.

**THEN STOP.** Batch B re-reads the committed partition, re-runs
`tools/wo029_reverify_partition.py` against it, and converts `test_gap_recording.py`,
`test_keepalive.py`, `test_failure_cap.py`, `test_failure_capture.py` (13 races) — after a ruling on
the two §6 items, since both change how those conversions should be done.
