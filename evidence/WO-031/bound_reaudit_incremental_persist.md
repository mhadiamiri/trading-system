# WO-031 §3-bis — RE-AUDIT of one audit BOUND, by the D39 method

**Subject:** `test_incremental_persist_survives_unhandled_exception_mid_capture`
(`tests/integration/test_ledger_persistence.py:82`)

**Audit's filing:** one of the **7 legitimate BOUNDS** (`evidence/WO-023/wall_clock_race_audit.txt`,
section *DETERMINISTIC OPERATION WITH A BOUND (LEGITIMATE, stay)*), justified as:

> `test_ledger_persistence.py:82 test_incremental_persist_survives_unhandled_exception dur=0.25, injected crash ends it`

with the section's shared rationale: *"In each the deadline is a BACKSTOP against a hang; the passing
path terminates via the script, not the clock."*

**Verdict: (a) — a RACE the audit misfiled as a BOUND. The read is INJECTABLE, so it is
CLOCK-INJECTABLE / CONVERTIBLE. Denominator 26 → 27. ESCALATED, not folded into a batch.**

Classification performed by the D39 method (enumerate reads → name the assertion), **not** from the
differential symptom. Instrument: `tools/wo031_bound_reaudit_probe.py` (re-runnable, writes to
`.artifacts/`).

---

## 3.1 Termination branch

Script: `[SNAPSHOT_FRAME, corrupted_update, RuntimeError("injected unhandled crash mid-capture")]`,
`on_drain="block"`, `duration_seconds=0.25`.

The audit assumes the branch is **crash-propagation** (frame 3 raises out of the capture). The code
admits a second exit for the same script: the **deadline** guard at `kraken_v2_book.py:2594`
(`while self._monotonic_clock() < deadline`), which ends the capture cleanly if it is reached before
frame 3 is drained. Which branch the test takes is decided at run time by a race between the two.

## 3.2 Real-clock reads on this race's path

Identical inventory to batch B (this is the same `get_live_market_data` loop). Overrides in this test:
`_heartbeat_absence_timeout = 100.0`, `_app_ping_interval = 100.0`, `_reconnect_sleep` collapsed.

**INJECTABLE:** deadline set `:2548`, deadline guard `:2594`, recv-timeout `remaining` `:2727`
(all `_monotonic_clock`); suspend wall `:2562` (`_wall_clock`).

**NON-INJECTABLE:** `last_frame` (100 s here), `last_ping` (100 s here), `_start_time` `:2514`,
`anchor_monotonic` `:2558`, gap open stamp `:1757`, instrument stamps `:2611/:2732/:2816/:2861/:2869`,
breaker streak `:2077/:2085` (600 s).

## 3.3 Classification, with the naming evidence

### The divergence flows from the DEADLINE read — pinned, not inferred

`AdvancingClock` advances its counter on every **monotonic** read, and `_monotonic_clock` is routed to
exactly three sites (`:2548`, `:2594`, `:2727`) — all the deadline seam. Every other read on the path
is raw `time.monotonic()` / `time.time()`, which the fixture **does not touch at all**. A behaviour
change under this fixture therefore *cannot* originate in a non-injectable read.

The probe turns that argument into a measurement by reporting how far into the script the run got:

| Clock | emitted | frame 2 reached (checksum failure) | gap opened | frame 3 reached (crash) |
|---|---|---|---|---|
| real clock (what CI runs) | 1 | True | 1 | **True** |
| `AdvancingClock(delta=0.2)` | 0 | False | 0 | **False** |
| `AdvancingClock(delta=0.05)` | 1 | **True** | 1 | **False** |
| `AdvancingClock(delta=0.01)` | 1 | True | 1 | **True** |
| `AdvancingClock(delta=0.0001)` | 1 | True | 1 | **True** |

A monotone gradient: as the deadline clock advances faster, the run ends **earlier in the script**.
`delta=0.05` is the decisive row — frame 2 drains and opens the gap, then the deadline arrives and
frame 3 never does. The cut lands *between* frames purely as a function of the deadline read's rate.

### OUTCOME-BEARING · the deadline read (INJECTABLE)

**The assertion that observes it** is the test's central one:

```python
with pytest.raises(RuntimeError, match="injected unhandled crash"):
    async for _ in adapter.get_live_market_data(duration_seconds=0.25):
        pass
```

`pytest.raises` fails with `Failed: DID NOT RAISE RuntimeError` exactly when the deadline wins — which
is the CI failure observed on run `30304749145` (3.14 leg, `--randomly-seed=2050525690`).

The downstream assertions inherit the same dependence, since they describe state that only exists once
frame 2 has been processed and the run has ended:
`assert len(opens) == 1` · `assert opens[0]["cause"] == "CHECKSUM_RESYNC"` ·
`assert opens[0]["gap_id"] == 0` · `assert not [r for r in records if r["event"] == "resolved"]`.

### INCIDENTAL · everything else

`last_frame` and `last_ping` are pinned at 100 s against a 0.25 s window and no assertion references
either. The breaker streak (600 s) is unreachable. `_start_time`, the ledger anchor, the gap open
stamp and the instrument stamps feed no assertion in this test — the persisted record is asserted on
`event`, `cause` and `gap_id`, never on a timestamp value.

## 3.4 Verdict

**RACE — not a bound.** An OUTCOME-BEARING clock read that the test's central assertion rests on. The
read is the **deadline**, which is **INJECTABLE** post-WO-023/WO-030, so under D39 this is
**CLOCK-INJECTABLE / CONVERTIBLE**, *not* NOT-YET-CONVERTIBLE. It needs no production seam.

It converts on the **DEADLINE branch** — but with the opposite polarity from batch A's race 4: race 4
needs the deadline to FIRE, this one needs it **not** to fire until the script has finished. The
`AdvancingClock` delta must be slow enough to leave all three frames a margin (`delta ≤ 0.01` in the
table above; batch A's `CLOCK_DELTA = 0.01` is the same choice for the same reason). No new fixture.

## The category consequence — a DENOMINATOR CHANGE, escalated

- Clock-injectable races: **26 → 27**.
- Legitimate bounds: **7 → 6**.
- The 30-race audit total is unchanged; a test moves buckets, and the *bounds* bucket loses one.

Per §3-bis this **escalates to the lead**. This WO does **not** reclassify unilaterally, does not
amend `batch_partition.md`, and does not assign the test to a batch. It is a `test_ledger_persistence.py`
member, the same file as batch C's race 12 — so if ratified, the natural home is batch C, which would
become 9 races.

---

## The other 6 bounds — enumerated, and scoped (not probed)

Per §3-bis: enumerate by name, state from the audit's own text whether any shares this one's shape,
and flag rather than probe-everything.

| # | Bound | Audit's stated justification | Deadline | Work before the scripted terminator | Shares the shape? |
|---|---|---|---|---|---|
| 31 | `test_backoff_breaker.py:88 test_persistent_reopen_failure_trips_breaker_loud` | `dur=30, breaker trips ~0.1s` | 30 s | breaker trip, backoff collapsed | **No** — ~300× margin |
| 32 | `test_gap_recording.py:202 test_terminal_venue_disconnect_breaker_gap_recorded` | `dur=30, breaker trip ends it` | 30 s | breaker trip | **No** — ~300× margin |
| 33 | `test_live_capture.py:172 test_breaker_trip_terminates_run_with_forensic_tail` | `dur=30, breaker trip ends it` | 30 s | breaker trip | **No** — ~300× margin |
| 34 | `test_reconnect_to_effect.py:100 test_stranded_reconnect_flag_fails_loudly` | `dur=30, RECONNECT_FLAG_STRANDED raises` | 30 s | flag raises | **No** — ~300× margin |
| 35 | **`test_ledger_persistence.py:82` (this re-audit)** | `dur=0.25, injected crash ends it` | **0.25 s** | **3 frames must drain** | **YES — reclassified** |
| 36 | `test_no_silent_fallback.py:25 test_connection_failure_raises_and_does_not_replay` | `dur=5, connection raises at once` | 5 s | raises during connect | **No** — raises before the loop is entered |
| 37 | `test_no_silent_fallback.py:52 test_live_method_refuses_fixture_mode_adapter` | `dur=1, refuses before any loop` | 1 s | refuses pre-loop | **No** — the deadline is never consulted |

**The shape, stated precisely:** a bound is safe when the deadline is large *relative to the work the
script must complete before its terminator fires*. Entry 35 is the sole outlier — the only bound whose
deadline (0.25 s) is the **same order of magnitude** as the work it must cover (draining three frames
through the full checksum/gap path). Entries 31–34 carry a ~300× margin; 36 and 37 terminate before or
during connect, so the deadline guard is never reached.

**Honesty about this reasoning.** The margin argument above is the *same form* of reasoning the audit
used and that this re-audit falsified — prose about which event "ends it". What distinguishes the two
cases is the ratio, not the rhetoric. Entries 31–34 and 36–37 are therefore recorded as
**not-obviously-shaped-like-35**, not as *proved safe*.

**Recommendation (enumerate-then-scope, as §3-bis directs):** do not probe them here. The probe is
cheap and now exists — `tools/wo031_bound_reaudit_probe.py` generalises to any bound by swapping the
script and duration. A single follow-on pass over entries 31–34, 36–37 would convert "not obviously
shaped like it" into a measurement, and would close the bounds bucket the way the 30 races are being
closed. That is a one-session job and is worth doing **before batch C is planned**, because entry 35
already lives in a batch-C file.
