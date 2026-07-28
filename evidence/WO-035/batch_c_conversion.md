# WO-035 §3 — BATCH C converted: 9 races, by node ID

Derived at HEAD `daaf5f5` (the §2 amendment commit). **No `src/` file touched.**

Every race was already transport-migrated to `connect_fn` (WO-024 pass one), so **no transport
monkeypatch migration rode along with any conversion** — §0.2 had nothing to do here. All nine are
**DIRECT** construction (none is factory-built; race 5, the only FACTORY-BUILT race, is in batch A).

**Time driver, before → after, for all nine:** the real `time.monotonic()` deadline → an injected
**coherent `AdvancingClock` pair** (`monotonic_clock=clk.monotonic` + `_wall_clock = clk.wall`,
shared `_coherence_token`). Delta is `duration / 50` throughout, so the deadline fires after a
**determinate ~50 monotonic reads** — the same construction gives the same firing point on every run
and in every order, with wide margin over the ≤9 recvs any of these scripts needs.

Gate ledger disposition for all nine: **`PROCEED_COHERENT`**.

---

## Per-race table

| # | Node ID | Path | Termination branch (KEPT, asserted before + after) | Apparatus-honesty (D41) |
|---|---|---|---|---|
| **12** | `test_ledger_persistence.py::test_gap_ledger_persisted_readable_from_disk` | DIRECT | **DEADLINE** — socket 2 heartbeats keep the link up; asserted by `"run_end" in events` and the resolved record, which exist only because the run reached its clean finalize after the reconnect | The end state is a clean deadline-finalize after a venue-close reconnect — the ordinary real-clock outcome of this script. The clock bounds the run; the ledger records asserted on are written by production code from real stamps. |
| **35** | `test_ledger_persistence.py::test_incremental_persist_survives_unhandled_exception_mid_capture` | DIRECT | **CRASH** — the injected `RuntimeError` propagates out; asserted by `pytest.raises(RuntimeError, match=…)`. **Not** the deadline, and not a scripted close | The CRASH branch is what every green real-clock run produced, and what WO-033 §3-bis's real-clock row measured. The conversion removes the possibility of the *other* branch; it does not manufacture an unreachable state. §4's sweep proves the clock decides which branch wins. |
| **14** | `test_host_suspend.py::test_no_host_suspend_under_normal_timing` | DIRECT | **DEADLINE** — heartbeats keep the link up | Doubly apt: "normal timing" *is* wall and monotonic tracking each other, and `AdvancingClock` drives both from one counter with fixed D25 offsets, so the divergence the detector looks for is zero **by construction** — exactly the real-clock condition the test asserts. This is the coherent half of the dual whose incoherent half is the foundation suspend test. |
| **22** | `test_protocol_ping.py::test_protocol_ping_params_set_deliberately` | DIRECT | **DEADLINE** — heartbeats keep the link up | The assertions are on `connect_kwargs` captured at connection time — configuration, not timing. Real-clock reachable trivially; the clock only bounds the run. |
| **23** | `test_protocol_ping.py::test_protocol_level_close_recovers` | DIRECT | **DEADLINE** — socket 2 heartbeats after recovery; asserted by `len(emitted) == 2`, so the post-recovery emission must land inside the window | Recovery-then-emission inside a bounded window is the ordinary real-clock outcome; the deadline is the same production deadline, fired deterministically rather than raced. |
| **24** | `test_throughput.py::test_receive_to_process_latency_recorded_through_production_path` | DIRECT | **DEADLINE** — heartbeats keep the link up | **The sharpest case.** The throughput record's own stamps stay on the REAL `time.monotonic()` — the injected clock drives only the deadline. So `lat_n >= 1` and `lat_max >= 0.0` still measure real receive-to-process latency through the production path. The fake clock bounds the RUN; it does not manufacture the LATENCIES asserted on. Were it otherwise this would be a decoupling artifact. |
| **25** | `test_reconnect_to_effect.py::test_five_real_failures_reconnect_and_emission_resumes` | DIRECT | **DEADLINE** — asserted by `connect_count == 2` + emission resumed | Six frames, a checksum-triggered reconnect and a fresh snapshot inside the window is the real-clock outcome; only the gamble on scheduler load is removed. |
| **26** | `test_venue_close_path.py::test_venue_close_unexpected_reconnects_expected_shuts_down_cleanly` | DIRECT ×2 | **TWO branches, both kept.** Half 1 = **DEADLINE** (socket 2 heartbeats after the 1011 reconnect; asserted by `connect_count == 2` + `len(emitted_a) == 2`). Half 2 = **VENUE-CLOSE** (the clean 1000 close ends the run; asserted by `connect_count == 1` + `len(emitted_b) == 1`) | The dual's whole content is that the two closes take *different* branches, so the conversion must not let the deadline pre-empt half 2's clean close. The ~50-read margin puts the close at recv #2, far inside the window. Both branches are ones the real clock reaches routinely. |
| **27** | `test_backoff_breaker.py::test_transient_reopen_failure_retries_under_backoff_then_emission_resumes` | DIRECT | **DEADLINE** — asserted by `len(emitted) == 2`, `capture_terminated is None` (the breaker must NOT trip) | Six frames + two refused reopens + one successful reopen inside the window is the real-clock outcome. The breaker's own streak stays on the non-injectable real `time.monotonic()` against a 600 s threshold, so "breaker did not trip" is a real-clock property, not a decoupling artifact. |

### A deliberate non-conversion, recorded

`test_backoff_breaker.py` also contains **entry 31**
(`::test_persistent_reopen_failure_trips_breaker_loud_with_forensic_tail`), a **MEASURED bound** at
199× (WO-033 §3.B). It is **not** in batch C and was **not** converted — its breaker trips on the
non-injectable real-clock streak, and WO-033 measured that margin rather than assuming it. The file
therefore now holds one converted race and one deliberately real-clock bound, which is correct and is
stated in the file so a later reader does not "finish the job".

---

## No assertion weakened — proved, not asserted

| File | asserts before | asserts after |
|---|---|---|
| `test_ledger_persistence.py` | 15 | 15 |
| `test_host_suspend.py` | 11 | 11 |
| `test_protocol_ping.py` | 7 | 7 |
| `test_throughput.py` | 8 | 8 |
| `test_reconnect_to_effect.py` | 7 | 7 |
| `test_venue_close_path.py` | 8 | 8 |
| `test_backoff_breaker.py` | 18 | 18 |

**`git diff -- tests/` contains ZERO lines beginning `+assert` or `-assert`.** The diff is
125 insertions / 18 deletions, and every deletion is a constructor line re-emitted with clock
arguments attached. No assertion was added, removed, loosened or re-expressed.

---

## Determinism, measured (§4)

`tools/wo035_entry35_clock_control.py` — **the injected clock CONTROLS entry 35's outcome**, it does
not merely permit a pass:

| delta | run 1 | run 2 | identical | gap opened | checksum failures |
|---|---|---|---|---|---|
| 0.2 | DEADLINE | DEADLINE | yes | 0 | 0 |
| 0.125 | DEADLINE | DEADLINE | yes | 0 | 0 |
| 0.05 | DEADLINE | DEADLINE | yes | 1 | 1 |
| **0.005 ← the converted test** | **CRASH** | **CRASH** | **yes** | 1 | 1 |
| 0.0005 | CRASH | CRASH | yes | 1 | 1 |

Slow the clock and the crash wins; speed it up and the deadline wins; every setting reproduces
exactly. The converted delta sits at ~50 reads of margin over the ~3 recvs the crash needs, so the
branch the test asserts is **pinned by construction rather than by winning a real-time race**.

`tools/wo035_ledger_still_bites.py` — **the net still bites after batch C**, four artifacts, sha256
exact-restore (`41562333…` before and after, IDENTICAL). Repointing `_live_adapter`'s wall reader at a
second `AdvancingClock` (mismatched token) makes the gate refuse on COHERENCE and the session-end
ledger assertion fail **naming both batch-C nodeids**:

```
E   AssertionError: GATE LEDGER VIOLATION.
(1) refusals from UNMARKERED tests (a real gate firing):
    [('tests/integration/test_ledger_persistence.py::test_gap_ledger_persisted_readable_from_disk', 'REFUSED_COHERENCE'),
     ('tests/integration/test_ledger_persistence.py::test_incremental_persist_survives_unhandled_exception_mid_capture', 'REFUSED_COHERENCE')]
```
