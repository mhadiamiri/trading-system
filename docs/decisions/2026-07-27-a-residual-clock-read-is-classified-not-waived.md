# Decision Log: a residual clock read is classified, not waived (WO-029 §6 item 2 / D39)

**Date:** 2026-07-27
**WO:** WO-029 batch A raised it; ratified as **D39** (the operative METHOD); committed as a doc by
WO-032 §3.2
**Authority:** D39 (this ruling); D35 (the asyncio-sleep exclusion); D37/D38 (the ruled-asymmetry
distinction)
**Related:** [[a-conversion-preserves-the-path-not-just-the-assertions]],
[[incidental-coverage-is-not-coverage]], [[the-exception-must-be-requested-by-name]],
[[a-transport-seam-is-not-a-clock-seam]]

---

## The problem this rules on

Pass two's conversion order said: *"a conversion leaving any real-time dependency is incomplete — name
it and STOP rather than half-converting."*

Read literally, **no race in the population can satisfy that.** `get_live_market_data` holds several
non-injectable real-clock reads on every path — keepalive pacing, application-ping interval, the
ledger anchor, `last_frame`, and the throughput/lag/pong instruments. WO-030 threaded only the
deadline and suspend seams. Taken literally, pass two STOPs on race 1 and never proceeds, which
contradicts the premise that 26 races are convertible.

Read loosely — "residuals are fine if the test still passes" — it becomes a waiver, and a waiver is
how a conversion that is really a *loosening* gets through.

Neither reading is acceptable. The ruling replaces the yes/no with a **classification**.

---

## The entry (ratified verbatim)

> A residual real-clock read is **classified, not waived**. For each race, enumerate every real-clock
> read on its code path and classify each one:
>
> * **OUTCOME-BEARING** — an assertion in that race depends on the value or timing of the read.
> * **INCIDENTAL** — an interval read against a fixed threshold, feeding no assertion, harmless in a
>   run compressed to milliseconds.
>
> **Convert only if all reads are incidental.** Any outcome-bearing read on a non-injectable seam is
> a **pre-committed STOP** and an escalation — it needs a production seam before that race can be
> converted, and the classification is what sizes that seam.

The classification is **shown, not asserted**: name the assertion for each outcome-bearing read, and
state explicitly that no assertion references the read for each incidental one. This is the per-read
evidence that makes it a method rather than a waiver.

---

## Seam-sized-to-measurement

When the classification convicts a read, the seam WO threads **the convicted reads and nothing more.**
Incidental residuals stay **unthreaded BY DESIGN** and are recorded as such.

This asymmetry is deliberate and must be written down where a later reader will meet it, because an
undocumented gap in a seam reads as a place work stopped. It is not: it is a ruled boundary, the same
distinction D37/D38 drew. A seam that grows to cover every read "for consistency" is unbounded work
justified by symmetry rather than by measurement.

---

## The expected collision, named in advance

`test_keepalive`'s races (15, 16) have **keepalive pacing as their subject.** "Feeds no assertion"
cannot hold for them by construction. The method names this before the batch opens rather than
discovering it mid-conversion — which is the whole value of classifying first: the STOP arrives as a
scheduled finding with a measurement attached, not as a surprise halfway through an edit.

---

## Standing consequence

1. A conversion WO enumerates real-clock reads **per race** and publishes the classification.
2. An outcome-bearing read on a non-injectable seam is a STOP — **an expected outcome, not a
   failure.** It produces the measurement that sizes the seam WO.
3. Incidental residuals are **named in the report**. Unnamed residuals are indistinguishable from
   unexamined ones, and [[the-exception-must-be-requested-by-name]] applies: the allowance is only as
   good as its naming.
4. The three `asyncio.sleep` races remain excluded under D35; this ruling does not reopen them.
