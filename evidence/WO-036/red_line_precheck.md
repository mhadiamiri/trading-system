# WO-036 §1 — RED-LINE PRECHECK: every consumer of `last_frame` and `last_ping` in `src/`

Derived at HEAD `dd5a6f9`. **Classify/verify only — nothing threaded, nothing converted.**

§1 requires: *"enumerate every consumer of `last_frame` and `last_ping` in `src/`. For each read site,
state what it feeds. If EITHER read reaches the gap-ledger, gap-detection timing, the checksum path,
or any corpus-integrity machinery, STOP and escalate — threading a corpus-integrity clock is red line
(d) and is NOT Ops-authority. WO-031 §4 classified both as keepalive/ping PACING reads feeding pacing
assertions; **confirm that from the code, do not inherit it.**"*

**RESULT: NOT CLEAN. `last_frame` reaches the gap ledger at three sites and the throughput instrument
at one. The precheck's STOP condition is met.**

All sites are in `src/trading/data/adapters/kraken_v2_book.py`; no other production module references
either name. (`_last_frame_server_ts` at `:1112/:1117/:1512/:1834/:1836` is a *different* field — the
venue's wall-clock string off the wire, not a monotonic read — and is out of scope.)

---

## `last_ping` — **CLEAN.** Pure pacing.

| Site | Code | What it feeds |
|---|---|---|
| `:2552` | `last_ping = time.monotonic()` | initialise |
| `:2683` | `last_ping = time.monotonic()` | reset after an absence reconnect |
| `:2691` | `if mono - last_ping >= self._app_ping_interval:` | **PACING** — the app-ping interval gate |
| `:2716` | `last_ping = time.monotonic()` | reset after a ping-send-failure reconnect |
| `:2718` | `last_ping = time.monotonic()` | reset after a successful ping send |
| `:2736` | `self._app_ping_interval - (mono - last_ping)` | **PACING** — remaining time until the next ping, feeding the recv timeout |
| `:2773` | `last_ping = time.monotonic()` | reset after a venue-close reconnect |

**Two reads, both pacing. No gap-ledger consumer, no checksum consumer, no instrument consumer.**
WO-031 §4's classification holds for `last_ping`.

---

## `last_frame` — **NOT CLEAN.** Pacing *plus* four non-pacing consumers.

| Site | Code | What it feeds |
|---|---|---|
| `:2551` | `last_frame = time.monotonic()` | initialise |
| `:2661` | `if mono - last_frame >= self._heartbeat_absence_timeout:` | **PACING** — heartbeat-absence detection |
| `:2663` | `f"HEARTBEAT_ABSENCE: no frame for {mono - last_frame:.2f}s …"` | log text |
| **`:2674`** | **`open_monotonic=last_frame`** in `self._open_gap(cause="KEEPALIVE_RECONNECT", …)` | ⚠ **GAP LEDGER — the gap's OPEN BOUND** |
| `:2675`, `:2679` | detail / reason strings | log + gap `detail` text |
| **`:2708`** | **`open_monotonic=last_frame`** in `self._open_gap(cause="VENUE_DISCONNECT", …)` (cause 4b, ping-send failure) | ⚠ **GAP LEDGER — the gap's OPEN BOUND** |
| `:2735` | `self._heartbeat_absence_timeout - (mono - last_frame)` | **PACING** — recv-timeout computation |
| **`:2765`** | **`open_monotonic=last_frame`** in `self._open_gap(cause="VENUE_DISCONNECT", …)` (cause 4c, venue close) | ⚠ **GAP LEDGER — the gap's OPEN BOUND** |
| `:2682`, `:2715`, `:2772`, `:2777` | `last_frame = time.monotonic()` | resets / refresh on any received frame |
| **`:2817`** | **`self._throughput_record.record(last_frame, done_mono)`** | ⚠ **THROUGHPUT INSTRUMENT — the recv-return timestamp of the receive-to-process latency sample** |

### The gap-ledger consumers, verbatim

The code is explicit that this is deliberate, load-bearing gap semantics — not incidental reuse:

```python
# :2667-2676  WO-014c-2 §2: OPEN the keepalive gap at the LAST FRAME received (when
#             emission actually stopped, not when the threshold tripped). The unified
#             close hook closes it at the first post-reconnect validated emit — this
#             is the close hook the absence path lacked (probe 2a).
self._open_gap(
    cause="KEEPALIVE_RECONNECT",
    reason_code="HEARTBEAT_ABSENCE",
    open_monotonic=last_frame,
    ...
```

```python
# :2702-2708  WO-014c-2 §2 (cause 4b): a dead socket detected on send is a venue
#             disconnect. Open the gap at the last frame received; …
    open_monotonic=last_frame,
```

```python
# :2760-2765  WO-014c-2 §2 (cause 4c): explicit venue close. Open the gap at the last
#             frame received; …
    open_monotonic=last_frame,
```

`open_monotonic` is a gap record's **opening time bound** — three of the five ruled gap causes take it
from `last_frame`. Gap windows are precisely how the corpus knows which time ranges are missing data,
so this is corpus-integrity machinery by any reading. Threading `last_frame` through an injected clock
would put fake time into `open_monotonic`, and therefore into `duration_s` and every gap-window
computation derived from it.

### The instrument consumer, verbatim

```python
# :2814-2817  WO-014c-1 §B.3: receive-to-process latency (last_frame = recv return) and the
#             per-second message count, on the shared monotonic clock.
done_mono = time.monotonic()
self._throughput_record.record(last_frame, done_mono)
```

`last_frame` is the **recv-return timestamp** of the receive-to-process latency sample. §6 of this WO
explicitly fences the throughput/lag/pong instrument clocks off as unconvicted — but `last_frame` *is*
one of the two inputs to the throughput latency measurement. Threading it would inject fake time into
an instrument the measurement did not convict, which §6 forbids and D39 calls speculative surface.

---

## Why this is not a contradiction of WO-031 §4

WO-031 §4 was asked which **non-injectable reads are outcome-bearing for a batch-B race**, and it
answered that correctly: races 6, 15 and 16 assert on absence detection and ping pacing, so
`last_frame` and `last_ping` are outcome-bearing *for those assertions*.

This precheck asks a **different question**: what does the read feed **in production**? A variable can
be outcome-bearing for a test's assertion *and* carry a second, unrelated production consumer. That is
exactly the case here, and it is exactly why §1 says *"confirm that from the code, do not inherit it."*
The instruction anticipated this and the check found it.

---

## Disposition

| Read | Verdict | Threadable at Ops authority? |
|---|---|---|
| `last_ping` | **CLEAN** — pacing only | Yes |
| `last_frame` | **RED LINE (d)** — gap-ledger open bound ×3 + throughput instrument ×1 | **No — escalate** |

**STOPPED before any threading.** Races 6, 15 and 16 are not converted; no `src/` file is touched.

### Why a partial thread is not an obvious way out

Threading only `last_frame`'s pacing comparisons (`:2661`, `:2735`) while leaving `:2674/:2708/:2765`
and `:2817` on the real clock would require **splitting one variable into two** — a fake-clock
"pacing last_frame" and a real-clock "gap/instrument last_frame". That changes what a gap's
`open_monotonic` *means* relative to the absence decision that opened it: today they are by
construction the **same instant**, and the comments at `:2667` make that identity deliberate ("when
emission actually stopped, not when the threshold tripped"). Decoupling them is a production semantic
change to gap-window accounting, which is further into red line (d), not a way around it.

That is a design question for the lead, not a call this WO can make.
