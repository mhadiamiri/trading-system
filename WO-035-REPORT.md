# WO-035 — D42 amendments landed, then BATCH C CONVERTED (9 races)

**COMPLETE. No STOP.** Base HEAD `e3fa557`. **SHIP IMPACT: NO** — tests, evidence, docs, tools. Every
`src/` file byte-unchanged.

**Batch C is the last conversion batch. 24 of 27 clock-injectable races are now converted**; batch B's
remaining 3 (races 6, 15, 16) await the keepalive seam WO, which runs separately.

| § | Deliverable | Result |
|---|---|---|
| §1 | HEAD / suite / membership / **D42 artifact-currency check** | **PASS** — 222 both interpreters; the lag was present and is now landed |
| §2 | Three ratified amendments, own commit | **DONE — `daaf5f5`** |
| §3 | Batch C's 9 races converted | **DONE** — all `PROCEED_COHERENT`, zero assertions touched |
| §4 | Determinism (12 runs) + entry-35 control + ledger bite | **PASS / PASS / PASS** |

---

## §1 — HEAD, SUITE, MEMBERSHIP, ARTIFACT-CURRENCY (D42)

**Actual HEAD: `e3fa557`** (`WO-034 close`). The WO names base `e12d6d2`; `e3fa557` is its docs-close.

| Interpreter | Result |
|---|---|
| 3.14.6 | **222 passed**, 0 f/xf/xp |
| 3.11.15 | **222 passed**, 0 f/xf/xp |

`wo029_reverify_partition.py` → PASS, writes `.artifacts/`, `git status` clean after.

**The D42 standing check found the lag it was written for.** `batch_partition.md` read
`= **8 races**` for batch C — the amendment D40/D41 ratified had never reached the tree. Per §0.6 the
amendment was landed (§2) **before** §3 read it.

**Batch C's 9 members, by canonical node ID** (from `evidence/WO-034/audit_node_ids.md`, not prose):

| # | Node ID |
|---|---|
| 12 | `tests/integration/test_ledger_persistence.py::test_gap_ledger_persisted_readable_from_disk` |
| 35 | `tests/integration/test_ledger_persistence.py::test_incremental_persist_survives_unhandled_exception_mid_capture` |
| 14 | `tests/integration/test_host_suspend.py::test_no_host_suspend_under_normal_timing` |
| 22 | `tests/integration/test_protocol_ping.py::test_protocol_ping_params_set_deliberately` |
| 23 | `tests/integration/test_protocol_ping.py::test_protocol_level_close_recovers` |
| 24 | `tests/integration/test_throughput.py::test_receive_to_process_latency_recorded_through_production_path` |
| 25 | `tests/integration/test_reconnect_to_effect.py::test_five_real_failures_reconnect_and_emission_resumes` |
| 26 | `tests/integration/test_venue_close_path.py::test_venue_close_unexpected_reconnects_expected_shuts_down_cleanly` |
| 27 | `tests/integration/test_backoff_breaker.py::test_transient_reopen_failure_retries_under_backoff_then_emission_resumes` |

**Confirmed 9.** Four of these (24, 26, 27, 35) carried truncated prose identifiers — the reason
WO-034 stopped and the reason this WO addresses them by node ID.

---

## §2 — THE THREE AMENDMENTS, LANDED — commit **`daaf5f5`**

Committed separately from §3 so the landing is verifiable independent of the conversion (§2.4).

1. **`batch_partition.md`: batch C 8 → 9.** Entry 35 folded in with its BOUND → RACE
   reclassification noted (D40/D41). Clock-injectable 26 → **27**, bounds 7 → **6**.
2. **Race identifiers restated as pytest NODE IDs** from `audit_node_ids.md`. The prose
   `file:line` + name columns are **retained as superseded historical record, not deleted**, with all
   nine truncated identifiers marked in the table.
3. **`docs/decisions/2026-07-27-a-ruling-is-not-in-force-until-its-artifact-is-committed.md`** —
   carrying D42's standing step and the regeneration rule verbatim, with three specimens: WO-031's
   uncommitted D39 amendment, this file's own 8-vs-9 lag across two WOs, and WO-034's diff that
   measured a corrected restatement instead of the audit.

**A consequence handled rather than left broken:** restating the identifier column changed the table
shape `wo029_reverify_partition.py` parses, so it matched **zero rows and FAILED**. Its row regex now
reads the node-ID column (ignoring the historical one) and its expectations move to 31 rows /
clock-injectable 27. Re-run: **PASS 31/31, counts 27/3/1.** This is the direct consequence of an
instructed change, not scope creep — leaving the standing enumeration instrument broken would have
failed every future §1.

---

## §3 — BATCH C CONVERTED

Full per-race detail: **`evidence/WO-035/batch_c_conversion.md`**. Summary:

- **All nine are DIRECT** construction (race 5, the only FACTORY-BUILT race, is batch A's).
- **No transport migration rode along with any conversion** — all nine were already on `connect_fn`
  from WO-024 pass one, so §0.2 had nothing to do.
- **Time driver, before → after (all nine):** real `time.monotonic()` deadline → injected **coherent
  `AdvancingClock` pair** (`monotonic_clock=clk.monotonic` + `_wall_clock = clk.wall`, shared
  `_coherence_token`), delta = `duration / 50`, so the deadline fires after a determinate ~50
  monotonic reads with wide margin over the ≤9 recvs any script needs.
- **Gate ledger: all nine `PROCEED_COHERENT`.**

**Termination branches, kept and asserted:**

| Branch | Races |
|---|---|
| DEADLINE | 12, 14, 22, 23, 24, 25, 27, and **26 half 1** |
| **CRASH** | **35** — the injected `RuntimeError` propagates out; not the deadline, not a scripted close |
| **VENUE-CLOSE** | **26 half 2** — the clean 1000 close ends the run |

Race 26 is the one race with **two** branches, and the dual's entire content is that the two closes
take *different* paths — so the conversion had to keep half 2 off the deadline. The wide margin puts
the clean close at recv #2 of ~50 available reads.

### Apparatus-honesty (D41), per race

Each race's statement is in the evidence artifact. The two worth surfacing here:

- **Race 24 (throughput)** is the sharpest case. The throughput record's stamps stay on the **real**
  `time.monotonic()`; the injected clock drives only the deadline. So `lat_n >= 1` / `lat_max >= 0.0`
  still measure real receive-to-process latency through the production path — **the fake clock bounds
  the RUN, it does not manufacture the LATENCIES asserted on.** Were it otherwise, that assertion
  would be a decoupling artifact.
- **Race 14 (no host suspend)** is doubly apt: "normal timing" *is* wall and monotonic tracking each
  other, and `AdvancingClock` drives both from one counter with fixed D25 offsets, so the divergence
  the detector looks for is zero **by construction** — exactly the real-clock condition asserted.

### No assertion weakened — proved

Assert counts identical across all seven files (15/11/7/8/7/8/18 before and after), and
**`git diff -- tests/` contains zero lines beginning `+assert` or `-assert`**. 125 insertions /
18 deletions; every deletion is a constructor line re-emitted with clock arguments.

### A deliberate non-conversion, recorded in the file

`test_backoff_breaker.py` also holds **entry 31**, a **measured bound at 199×** (WO-033 §3.B). It is
not in batch C and was not converted — its breaker trips on the non-injectable real-clock streak, and
WO-033 measured that margin rather than assuming it. The file now holds one converted race beside one
deliberately real-clock bound; that is stated in the file so a later reader does not "finish the job".

---

## §4 — DETERMINISM + LEDGER BITE

### 12 runs, all green

| Interpreter | `-p no:randomly` | 20260901 | 20260902 | 20260903 | 20260904 | 20260905 |
|---|---|---|---|---|---|---|
| 3.14.6 | 222 | 222 | 222 | 222 | 222 | 222 |
| 3.11.15 | 222 | 222 | 222 | 222 | 222 | 222 |

0 f/xf/xp throughout. Seeds: **20260901, 20260902, 20260903, 20260904, 20260905**.

### The injected clock CONTROLS entry 35's outcome — `tools/wo035_entry35_clock_control.py`

Not "it still passes" — the clock **decides which branch wins**, and each setting reproduces exactly:

| delta | run 1 | run 2 | identical | gap | csum |
|---|---|---|---|---|---|
| 0.2 | DEADLINE | DEADLINE | yes | 0 | 0 |
| 0.125 | DEADLINE | DEADLINE | yes | 0 | 0 |
| 0.05 | DEADLINE | DEADLINE | yes | 1 | 1 |
| **0.005 ← converted** | **CRASH** | **CRASH** | **yes** | 1 | 1 |
| 0.0005 | CRASH | CRASH | yes | 1 | 1 |

Slow the clock and the crash wins; speed it up and the deadline wins. The converted delta sits at ~50
reads of margin over the ~3 recvs the crash needs. **Apparatus honesty:** CRASH is the branch every
green real-clock run produced, and the one WO-033 §3-bis's real-clock row measured — the conversion
removes the possibility of the *other* branch, it does not manufacture an unreachable state.

### Ledger still bites — `tools/wo035_ledger_still_bites.py`, four artifacts, sha256 exact-restore

`41562333…` before and after, **IDENTICAL**. Repointing `_live_adapter`'s wall reader at a second
`AdvancingClock` (mismatched token) makes the gate refuse and the session-end assertion fail, naming
**both** batch-C nodeids:

```
E   AssertionError: GATE LEDGER VIOLATION.
(1) refusals from UNMARKERED tests (a real gate firing):
    [('tests/integration/test_ledger_persistence.py::test_gap_ledger_persisted_readable_from_disk', 'REFUSED_COHERENCE'),
     ('tests/integration/test_ledger_persistence.py::test_incremental_persist_survives_unhandled_exception_mid_capture', 'REFUSED_COHERENCE')]
```

Artifact 1 pristine → quiet; artifact 2 mutated → bites; artifact 3 restored → quiet; artifact 4
sha256 identical.

---

## §5 — SCOPE FENCE: HELD

| Fence | Held? |
|---|---|
| Batch C's 9 only; no batch A/B race re-touched | **HELD** |
| No keepalive-blocked race (B's 6/15/16) touched | **HELD** |
| The 3 asyncio.sleep races untouched | **HELD** |
| No production logic change; no new reason codes; no gate docstring note | **HELD** |
| No assertion weakened | **HELD** — proved above |

**Five `src/` sha256, unchanged:** `kraken_v2_book.py` `b06c347e` · `factory.py` `103a8ba7` ·
`registry.py` `5bf833c7` · `live_capture.py` `dab18f67` · `logkit/decision.py` `3d153a11`.
`git diff -- src/` **empty**.

---

## §6 — ACCEPTANCE

| Gate | Result |
|---|---|
| `pytest tests/ -p no:randomly -rX` → 222 both interpreters | **PASS.** Arithmetic: **222 + 0 = 222** — batch C converts; it adds, removes, splits and merges nothing. |
| `pytest --randomly-seed=<5 seeds>` all green both interpreters | **PASS** — 10 seeded runs, table above |
| `batch_partition.md` reads batch C = 9 with node-ID identifiers; §2 its own commit | **PASS** — commit `daaf5f5` |
| Gate ledger: 0 unmarkered refusals, 0 stale markers; batch-C dispositions | **PASS** — 43 invocations; `[]` and `[]`; all nine batch-C races `PROCEED_COHERENT` (race 26 twice, once per half). The sole `PROCEED_DECLARED` remains the foundation suspend test. |
| Ledger-still-bites: four artifacts, sha256 exact-restore | **PASS** |
| Five `src/` sha256 IDENTICAL; `git diff -- src/` empty | **PASS** |
| lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass | **PASS** |
| `evidence/WO-035/` + gate ledger snapshot committed | **PASS** |
| progress.md WO-035 block | **PASS** |
| Commit (separate from §2), push, local == remote, CI green both legs | **see §CI** |

---

## §Attempts — every one, including the failures

1. **Re-read `instructions.md` from disk** (sha256 `12F1FACD…`, 8782 bytes) before acting.
2. **Ran §1's D42 currency check as a real check, not a formality** — and it fired: `batch_partition.md`
   still read 8. Landing it first (§2) is the whole point of the standing step.
3. **The §2.2 identifier restatement broke `wo029_reverify_partition.py`** — its row regex expected
   `| n | file.py:line | name | …` and matched **zero** rows against the new node-ID column, so it
   FAILED with "the table has 0 rows". Fixed by re-keying the regex on the node ID and moving the
   expectations to 31 rows / 27 clock-injectable. Recorded because the failure mode is the good one:
   a tolerant parser would have reported zero mismatches and looked like a pass.
4. **Chose `delta = duration / 50` rather than a single global constant.** Batch A used a fixed
   `CLOCK_DELTA = 0.01`, which is fine for a 0.25 s window but leaves only ~5 reads for race 22's
   0.05 s window — too tight for a script needing several recvs. Scaling to the duration gives every
   race the same ~50-read margin regardless of its window. WO-029 §9 measured its firing point rather
   than deriving it; scaling is how that lesson generalises.
5. **Checked entry 35's converted delta against WO-033's measured boundary** rather than picking one
   and hoping: WO-033 §3-bis measured crash-wins at δ ≤ 0.01 and deadline-wins at δ = 0.05. The
   converted δ = 0.005 sits inside the measured crash-wins region, and §4's sweep re-confirms it at
   this HEAD.
6. **Verified "no assertion weakened" mechanically**, not by inspection: assert counts per file before
   vs after, plus a diff scan for any line starting `+assert`/`-assert`. Both clean. Counting is what
   makes it a claim rather than an impression.
7. **Ran the bite proof and the control demo before the acceptance matrix**, since both mutate or
   drive tracked files, and the matrix must not share the tree with them.
8. **Left entry 31 unconverted deliberately** and said so in the file it shares with race 27. It is a
   measured bound (199×), not an oversight, and an undocumented real-clock test sitting beside a
   converted one is exactly the shape a later reader "fixes".
9. **`PYTHONUTF8=1` on every invocation** — without it `contract_count_check.py` aborts the session at
   `pytest_sessionstart`. Environmental; CI is Linux/UTF-8.

---

## §CI

- **§2 commit:** `daaf5f5` (the amendment landing, verifiable on its own) · **§3/§4 commit:** `86f0a96`
- **Local == remote:** `86f0a9621e8921ee656dd35f6db4edf22fdc0929` == `origin/master`
- **CI run `30363939767`** — **`test (3.11)` success · `test (3.14)` success**, green both legs on the first attempt, both orders.

**THEN STOP.** 24 of 27 clock-injectable races converted. Next: the keepalive seam WO closes batch B's
remaining 3 (`last_frame` + `last_ping`, sized by WO-031 §4) → all 27 done → taxonomy migration →
capture-loop baseline → corpus preconditions.
