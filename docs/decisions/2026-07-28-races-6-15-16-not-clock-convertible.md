# Decision Log: races 6, 15 and 16 are not clock-convertible — pass two is closed (Option 4)

**Date:** 2026-07-28
**WO:** raised by WO-036's §1 red-line precheck; ruled Option 4; landed by WO-037 §2.1
**Authority:** the red lines (d — corpus integrity); D39 (seam-sized-to-measurement); D35 (the
asyncio-sleep exclusion precedent)
**Related:** [[outcome-bearing-for-whom-consumed-by-what]],
[[a-residual-clock-read-is-classified-not-waived]],
[[bound-versus-race-is-a-measurement-not-a-margin]],
[[a-conversion-preserves-the-path-not-just-the-assertions]]

---

## The entry (ratified verbatim)

> **Making three test conversions deterministic is not worth any change to how the corpus records gap
> windows; options that inject fake time into `open_monotonic` are not a cost-benefit calculation but
> the red line doing what red lines do.**

---

## What was found

WO-031 §4 measured pass two's outcome-bearing non-injectable set and found exactly two reads —
`last_frame` (the heartbeat-absence clock) and `last_ping` (the app-ping interval) — convicting
batch B's races 6, 15 and 16. WO-036 was authorized to thread them at Ops authority, in the WO-030
shape, sized to that measurement and nothing more.

Its §1 precheck required enumerating every `src/` consumer of both reads and stopping if either
touched corpus-integrity machinery. `last_ping` was clean. **`last_frame` was not:**

| Site | Consumer |
|---|---|
| `kraken_v2_book.py:2674` | `open_monotonic=last_frame` — the **KEEPALIVE_RECONNECT** gap's open bound |
| `:2708` | `open_monotonic=last_frame` — the **VENUE_DISCONNECT (4b)** gap's open bound |
| `:2765` | `open_monotonic=last_frame` — the **VENUE_DISCONNECT (4c)** gap's open bound |
| `:2817` | `_throughput_record.record(last_frame, done_mono)` — the recv-return timestamp of the receive-to-process **latency instrument** |

`last_frame` **is the opening time bound of three of the five ruled gap causes.** Gap windows are how
the corpus knows which time ranges are missing data. Threading it would put injected time into
`open_monotonic`, and thence into `duration_s` and every gap-window computation the archive carries.

That is red line (d), and it is not Ops authority. WO-036 stopped with nothing threaded.

## Why the alternatives were refused

**Thread `last_frame` anyway (option 2).** This is what the entry above refuses. It would make the
corpus's gap bounds injectable so that three tests could stop being timing-sensitive. The trade is not
close enough to weigh — and weighing it at all is the error the red line exists to prevent.

**Split `last_frame` in production (option 3)** — a fake-clock pacing stamp and a real-clock
gap/instrument stamp. Beyond being the largest change on the table, it has a defect of its own: it
would **decouple what `:2667` deliberately made identical.** The code reads:

> *"OPEN the keepalive gap at the LAST FRAME received (when emission actually stopped, not when the
> threshold tripped)."*

The gap's open bound and the absence decision are the **same instant on purpose**. Splitting the
variable makes them two instants that merely happen to be close, and quietly changes what a gap window
means. A change that alters the semantics of the thing being archived, in order to make tests
deterministic, is worse than the problem.

**Thread only `last_ping` (option 1).** Clean, and permitted — but it convicts only part of race 16
(`assert len(pings) >= 3`) and leaves races 6 and 15 untouched, both of which rest on `last_frame`'s
absence detection. Partial progress at the cost of a split WO; not taken.

## The disposition

**Races 6, 15 and 16 are DECLARED NOT-CLOCK-CONVERTIBLE** — the same standing the three
`asyncio.sleep` races have carried since D35. Declared, not deferred: there is no pending work item
here, and a later WO should not "finish" it.

**Pass two is CLOSED, denominator 30:**

| Disposition | Count |
|---|---|
| CONVERTED | **24** |
| NOT-CLOCK-CONVERTIBLE — keepalive-blocked (6, 15, 16) | **3** |
| NOT-CLOCK-CONVERTIBLE — asyncio.sleep (28, 29, 30) | **3** |

## Standing consequence

1. **Races 6, 15 and 16 stay on the flake-doctrine `diagnose-before-rerun` discipline.** They are the
   residue a structural fix should not chase: timing-sensitive by construction, because what makes
   them sensitive is load-bearing production semantics. A failure in one is **investigated**, never
   re-run away. That discipline is now their permanent mitigation, not an interim one.
2. **A declared non-conversion is a result, not a gap.** Pass two set out to make 27 races
   deterministic and made 24, because the remaining 3 turned out to be asking for something the red
   line forbids. Recording that as *closed* rather than *incomplete* is the honest accounting — the
   alternative invites a future WO to reopen it without the context.
3. **The precheck that produced this is now standing form** — see
   [[outcome-bearing-for-whom-consumed-by-what]].
