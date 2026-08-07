# The line that says why it ended must never be the line that gets dropped

**Date:** 2026-08-07
**WO:** WO-045 §3
**Ruling:** D46
**Status:** RATIFIED

## The doctrine (verbatim)

> For unattended runs, any message that explains a TERMINATION logs at WARNING or above.
> **The line that says why it ended must never be the line that gets dropped.**

## What produced it

WO-044's corpus run `20260805220327` ran 12.9 hours and stopped — not at its 24-hour deadline, and
not on any error. It finalized cleanly: no exception, `crash_artifact: ""`, a full `MANIFEST.json`,
and a `run_end` ledger record with zero incomplete gaps.

The reason it stopped was logged. At `logger.info`. A detached corpus run captures WARNING and
above, so the single line explaining the termination existed in **no log anywhere**.

The cause was recovered by ELIMINATION: `get_live_market_data` has exactly three exits — the
deadline (not reached at 12.9 h of 24 h), an exception (none, per the empty crash artifact), and
`ConnectionClosedOK`. Only the third survives. Kraken had closed with a normal-closure code, and
WO-014b-2 §1.3(4c) ends the capture without reconnecting rather than hammering a venue that closed
on purpose.

That reasoning is sound and it is written down. It is also **inference**, and it should never have
been necessary. A capture that logs its own termination reason turns that inference into a fact you
read.

## Why the level is the whole point

An INFO-level explanation is not a quiet explanation — it is an ABSENT one, for exactly the runs
that need it most. The longer and more unattended a capture, the more aggressively its logs are
filtered, and the more likely nobody is watching when it ends. The message's importance and its
probability of being retained were inversely related. That is the defect.

## What the enumeration found (the larger instance)

§3.2 required enumerating *every* termination path rather than fixing the one that bit. That found
something worse than the reported defect:

| Path | Before | After |
|---|---|---|
| Deadline elapsed | **no log at all** | `CAPTURE_ENDED_DEADLINE` at WARNING |
| Clean venue close (1000/1001) | `logger.info` | `CAPTURE_ENDED_CLEAN_VENUE_CLOSE` at WARNING |
| Breaker STOP | `logger.error` | unchanged (already compliant) |
| `RECONNECT_FLAG_STRANDED` | raise only, no log | log at ERROR, then raise |
| Pre-connection guard refusals | raise before any capture starts | unchanged — a refusal to start is not a termination |

The **deadline** path is the ordinary planned end of every bounded capture. It ended corpus run
`20260806130401`. It logged nothing whatsoever — a strictly larger hole than the INFO line that
prompted the WO, and it would not have been found by fixing only what bit.

## How it is enforced

The reason is **centralised, not per-exit**. Each normal exit sets `termination_reason`; one
guaranteed WARNING is emitted after the loop. A future `break` that forgets to set it logs
`CAPTURE_ENDED_UNDECLARED` — loud by construction rather than silent by omission. Logging at each
break site would have left the next author free to add a silent exit.

The three causes are **declared reason codes**, not free text. This was forced by the
raised⇒declared guard, which correctly read code-shaped text in a log message as governed
vocabulary. The honest resolution was to govern it rather than reword it into invisibility: a
termination cause **is** an audit fact.

The two RAISING terminations log their reason at ERROR before propagating. A raise is not a
substitute for a log — the corpus runner CATCHES exceptions and writes the traceback to
`CRASH_TRACEBACK.txt`, so the log stream could otherwise carry no explanation at all.

## Scope

This is about the log LEVEL of termination explanations. It does not change any termination
BEHAVIOUR: the breaker still owns termination, a clean close still ends the capture without
reconnecting, and the deadline still bounds the run.

## Recorded against the corpus

`corpus_20260805`'s provenance records that run `20260805220327`'s termination cause is
**inference (cause-by-elimination)**, honestly labelled. The corpus is not re-derived and not
re-labelled; the fix makes the *next* such fact directly readable rather than reconstructed.
