# WO-029 (refreshed) — PASS TWO, BATCH A. Clock injection into the first cluster of the 26 races.

BASE: current HEAD on master (the WO-030 docs-close, `9c084c3`, on top of clock-seam `dd9def5`) —
**confirm actual HEAD in §1 and use it.** 218 both orders both interpreters, CI green both legs
(WO-030 code `dd9def5` run 30183494157).

SCOPE: **BATCH A ONLY.** Batches B and C are separate WOs that re-read this WO's committed partition.
Commit green, STOP. Do not convert a race outside batch A even if it looks trivial.
SHIP IMPACT: **NO** — tests, conftest, evidence. Every production file byte-unchanged; §7 proves it.

WHAT CHANGED SINCE THIS WO WAS FIRST DRAFTED: WO-030 threaded the clock seam through
runner→factory→builder, so **race #5 is now clock-injectable** and the pass-two denominator is a
genuine **26** (D38 named it). `test_live_capture.py` (races 1–5) now converts WHOLE — no file split.

WHAT PASS TWO DOES: converts wall-clock-dependent races to deterministic by injecting a COHERENT
clock pair (shared `_coherence_token`) through the WO-023/028/030 seams. The gate permits a coherent
pair; an incoherent one refuses. The gate ledger is the live safety net — a wrong injection trips a
refusal and cannot pass silently.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report. Do not reconcile silently.
0.2 No monkeypatching to make a guard pass. Where a race still monkeypatches the transport, migrate
    it to `connect_fn` (direct construction) or the runner clock/transport seams (factory-built) in
    the same edit — a clock injection with a module-patched transport trips COUPLING, so the two go
    together for any race not already transport-migrated.
0.3 Every guard/assertion touched gets a fail-then-pass bite proof: four artifacts, sha256
    exact-restore.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt, including failures and retries.
0.6 Report `/context` at START and at the commit seam.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | WO-023 §1 audit (the 30 races, enumerated) | **OPERATED** | Committed `86e2a33` |
    | Coherent FakeClock harness (shared token) | **OPERATED** | WO-023 §3 |
    | `_wall_clock`/`_monotonic_clock` adapter seams | **OPERATED** | WO-023 foundation |
    | `connect_fn` seam (runner/factory/builder) | **OPERATED** | WO-028 `c50b70e` |
    | Clock seam (runner/factory/builder) — makes race #5 injectable | **OPERATED** | WO-030 `dd9def5` |
    | Gate ledger + marker exclusion + snapshot tool | **OPERATED** | WO-024/025/026; first-run WO-027 |
    | The 26-race partition into batches A/B/C | **THIS WO IS THE BUILDER** | Does not exist — §2.0 |
    | Self-advancing coherent clock fixture (deadline-firing) | **THIS WO IS THE BUILDER** | Does not exist — §2.0-bis |

    Any OPERATED row not verified as stated → **STOP and report.** In particular: confirm race #5
    (`…_resolves_live_adapter_from_data_source_via_factory`) can now inject a clock through the
    runner seam (WO-030). If it cannot, STOP — WO-030 did not achieve its purpose.

---

## §1 CONFIRM HEAD AND THE STARTING SUITE
State actual HEAD. Run `pytest tests/ -p no:randomly -rX` on both interpreters; confirm the starting
count (**218**, per WO-030) before any edit. If it is not 218, STOP.

---

## §2.0 RE-ENUMERATE ALL 26 AT HEAD, DECLARE THE PARTITION (before any edit)

The "26" is now D38-ratified, but the FILE+LINE identity of each race must be re-derived at THIS HEAD
— WO-030 moved lines in `kraken_v2_book.py`/`factory.py`/`live_capture.py`, and *an enumeration is
only as good as its identifiers* (the ratified entry that caught race #5). Do not trust prior line
numbers.

Produce the full table of all 30 audit races at THIS HEAD:
- file+line (current), test name (current — flag any rename), audit race #,
- category: **CLOCK-INJECTABLE** (must total **26**, now including race #5) /
  **ASYNCIO-SLEEP** (3, excluded, D35) / **ALREADY-CONVERTED** (1, the suspend test, foundation).
- Confirm the 3 asyncio.sleep races by name: `test_pong_observer_records_rtt_distribution`,
  `test_absent_pongs_are_a_signal_not_gappiness`, `test_starved_lag_sampler_self_reports_degradation`.
  If the set differs, STOP — the exclusion denominator changed.
- Confirm race #5 is in the 26 (CLOCK-INJECTABLE via the runner seam). If not, STOP.
- For each of the 26, note its construction path: **DIRECT** (test builds
  `KrakenV2BookAdapter(...)` — injects FakeClock directly) or **FACTORY-BUILT** (via the runner —
  injects through the runner clock/transport seams). Race #5 is the only known FACTORY-BUILT; confirm
  no others are.

**If the injectable count is not 26, STOP and report the real number with the delta.** Five prior
counts in this family traveled as prose and were wrong; this one is derived at HEAD or not trusted.

**Then declare the A/B/C partition** as a committed artifact (`evidence/WO-029/batch_partition.md`):
each of the 26 assigned to exactly one batch, **partitioned BY TEST FILE** (a file's races convert
together — no file split across batches). State batch A's members explicitly with their construction
path. B and C named, not touched. The partition is evidence; later batches re-read it and
re-enumerate against it rather than re-deciding.

Batch A sizing guidance (not a hard rule): aim for a cluster whose conversion + determinism proof
fits comfortably in one session with margin, biasing toward whole test files. If one file's race
count alone is large, batch A may be that single file. State your sizing rationale.

---

## §2.0-bis THE SELF-ADVANCING COHERENT CLOCK FIXTURE — THIS WO IS THE BUILDER

The §2.0 enumeration surfaced a harness gap: race 4
(`test_clean_deadline_close_does_not_reconnect_dual`, `test_live_capture.py`) asserts DEADLINE-CLOSE
semantics — reaching the deadline ENDS the run. Every existing FakeClock is FROZEN: it injects a
coherent pair but cannot FIRE a deadline (that needs the clock to advance past the threshold on its
own). Reframing "deadline close" as a scripted clean-close is a §2 STOP (changes what the test
observes). So race 4 needs a NEW self-advancing coherent clock fixture — and because §2.0 forbids
splitting a file, race 4 gates the whole of `test_live_capture.py`.

**This fixture is a HARNESS BUILD, not a test edit.** It is subject to §0.3 (bite proof) and §0.4
(preservation dual), because every future deadline-assertion race will depend on it. Build it BEFORE
converting any race in the file.

Requirements:
- A coherent clock source (shared `_coherence_token`, same as the frozen harness — it must pass the
  gate's COHERENCE check exactly as the frozen pair does) whose wall and monotonic ADVANCE together
  by a fixed delta per read (or per an explicit `advance()`), so a deadline computed on the
  monotonic seam is REACHED after a determinate number of reads. Deterministic: same construction →
  same firing point, every run, every order.
- The advance must preserve D25's discipline INSIDE the fixture (monotonic orders, wall locates,
  fixed offset between them) — it is the frozen harness made to move, not a new incoherent thing.
- It must be reusable: parameterized by the advance delta and/or the target firing iteration, so any
  future deadline race constructs it without bespoke code.

### Bite proof — four artifacts, sha256 exact-restore, BOTH directions (§0.3, §0.4)
- **FIRES (refusal-analog / the positive assertion):** construct with an advance that REACHES the
  deadline → the run terminates via the deadline path (not via reconnect, not via a scripted close).
  Prove the termination is the DEADLINE firing, by the same signal race 4 checks.
- **DOES NOT FIRE PREMATURELY (preservation dual, local and direct):** construct with an advance
  that approaches but does NOT pass the threshold → the run CONTINUES (no premature deadline). This
  is the half that matters: a clock that fires too eagerly makes race 4 pass for the wrong reason.
- Restore; sha256 == pristine; final artifact PASS.

State the fixture's name and location, and confirm it lands in the shared harness
(`tests/fixtures/…`), extending it, not rebuilt.

---

## §2 CONVERT BATCH A

For each race in batch A:
- Inject a COHERENT clock pair (shared `_coherence_token`) via the FakeClock harness, replacing the
  wall-clock dependency that makes the test flaky. DIRECT races inject at construction; FACTORY-BUILT
  races (race #5, if in batch A) inject through the runner's clock+transport seams.
- If the race still monkeypatches the transport, migrate it in the same edit (0.2).
- The test must become DETERMINISTIC: state, per race, what wall-clock dependency was removed and
  what now drives time. A conversion leaving any real-time dependency is incomplete — name it and
  STOP rather than half-converting.
- **Do NOT weaken an assertion to make a test pass under the fake clock.** If the fake clock changes
  what the test observes, that is a finding about the test's original correctness — STOP and report;
  do not adjust the assertion to fit. (This is the pass-two failure mode: a "converted" test that is
  really a loosened one.)

Per-race in the report: race #, construction path, before (what drove time), after (what drives it),
whether a transport migration rode along, and the gate ledger disposition (`PROCEED_COHERENT` for an
injected coherent pair; `EARLY_RETURN` only if the race legitimately injects no clock — state which
and why).

---

## §3 THE FLAKE MUST ACTUALLY BE GONE — PROVE IT, DON'T ASSERT IT

- Run batch A's tests under **randomized ordering with 5 distinct seeds** AND `-p no:randomly`, both
  interpreters. All green, all runs. Paste the seeds.
- For at least ONE representative converted race, demonstrate the injected clock now CONTROLS the
  timing the test depends on — e.g. advancing the fake clock is what advances the test's observed
  time — not merely that the test still passes. "Still passes" ≠ "is now deterministic" (the WO-008b
  throughput VOID is the precedent for measuring the real thing).
- If race #5 is in batch A: additionally show its clock injection reaches the adapter THROUGH the
  runner→factory→builder path (the WO-030 seam actually carrying the fake clock to the adapter),
  not a directly-constructed shortcut.

If any converted race remains order- or timing-sensitive, it is NOT converted. STOP and report.

---

## §4 THE LEDGER STILL BITES AFTER THE BATCH (safety-net integrity)

Prove the net still catches a wrong injection AFTER batch A's changes (four artifacts, sha256
exact-restore):
- Take one batch-A converted race, corrupt its injection to an INCOHERENT pair (mismatched token)
  → the gate refuses, the ledger's session-end assertion FAILS naming the nodeid. Restore; sha256
  == pristine; passes.
This is not a new guard — it is proof the existing net did not go slack as the population it guards
grew. Report it verbatim.

---

## §5 SCOPE FENCE
- BATCH A ONLY. Batches B and C named in the partition, not touched.
- The 3 asyncio.sleep races NOT touched (out of pass two, D35).
- NO production logic changes. NO new reason codes (the vocabulary split is a later WO).
- NO gate docstring precision note (r20 ruling 2 folds into the vocabulary-audit WO, D37).
- NO weakening of any assertion to fit the fake clock.

---

## §6 DECISION LOG
No new entry required unless the enumeration or a conversion surfaces one. If §2.0's count differs
from 26, or a conversion reveals a test that was passing for the wrong reason, THAT is a candidate —
report it and propose the entry; do not write it without flagging.

---

## §7 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → count = 218 (batch A converts, does not add/remove) unless a
  conversion legitimately splits/merges a test — if the count changes, state the arithmetic and why.
  0 f/xf/xp.
- `pytest tests/ --randomly-seed=<5 seeds>` → all green, both interpreters (§3).
- Gate ledger: 0 unmarkered refusals, 0 stale markers; batch-A dispositions as stated in §2.
- Self-advancing clock fixture (§2.0-bis): bite proof BOTH directions (fires / does-not-fire-early),
  four artifacts, sha256 exact-restore. Fixture lands in the shared harness, coherent-token-passing.
- Ledger-still-bites bite proof (§4): four artifacts, sha256 exact-restore.
- If batch A = `test_live_capture.py`, all five of its races (1,2,3,4,5) convert together; race 4 via
  the self-advancing fixture, race 5 through the runner seam. State that the file converts WHOLE.
- Every production file sha256 IDENTICAL before/after — paste the five hashes from the WO-030 report
  (`kraken_v2_book.py` `b06c347e…`, `factory.py` `103a8ba7…`, `registry.py` `5bf833c7…`,
  `live_capture.py` `dab18f67…`, `logkit/decision.py` `3d153a11…`).
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 ·
  `preflight_path_check.py` pass.
- Commit, push, local == remote, CI green BOTH legs via `gh run view` (paste the run number — real,
  not a placeholder).
- Snapshot the gate ledger into `evidence/WO-029/` via `tools/snapshot_gate_ledger.py`.
- `evidence/WO-029/batch_partition.md` committed.
- Append a WO-029 (pass two batch A) block to `progress.md`.

## §8 REPORT — `WO-029-BATCH-A-REPORT.md`
The §2.0 full 26-enumeration at HEAD with construction-path column and the A/B/C partition; per-race
conversion table; the §3 determinism proof (5 seeds + the representative real-control demonstration,
+ race #5's through-the-runner proof if applicable); the §4 ledger-bite proof verbatim; the five
unchanged production sha256s; `/context` at start and seam; the §7 gate output; the CI run number;
every attempt; any STOP.

**THEN STOP.** Batch B re-reads the committed partition.