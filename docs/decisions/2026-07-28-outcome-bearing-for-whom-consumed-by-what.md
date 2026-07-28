# Decision Log: outcome-bearing for whom, consumed by what — the two questions any seam must answer

**Date:** 2026-07-28
**WO:** raised by WO-036's §1 red-line precheck; landed by WO-037 §2.2
**Authority:** the call-graph doctrine, final form; the red lines (d); D39; D42
**Related:** [[races-6-15-16-not-clock-convertible]],
[[a-residual-clock-read-is-classified-not-waived]],
[[a-doctrine-needs-a-guard-that-reaches-every-producer]],
[[a-ruling-is-not-in-force-until-its-artifact-is-committed]],
[[incidental-coverage-is-not-coverage]]

---

## The entry (ratified verbatim)

> A variable can be **outcome-bearing for a TEST** and simultaneously carry unrelated **PRODUCTION
> consumers**. The classification that convicts a read for a test says **nothing** about what
> threading it does to the corpus.
>
> Both questions are standing form for any seam threading:
> **(1) outcome-bearing for whom?** — which assertions depend on this read.
> **(2) consumed by what?** — what else, in production, does this value flow into.

---

## Why this needed writing down

D39 gave pass two its classification method: for each race, enumerate every real-clock read on its
path and classify each **outcome-bearing** (an assertion depends on it) or **incidental**. That method
is correct and it worked — WO-031 §4 applied it to batch B and produced exactly the measurement the
seam WO was sized to: two reads, `last_frame` and `last_ping`, convicting races 6, 15, 16.

The method answers question (1). It was never asked question (2), and nothing in it prompts the asker
to notice that (2) exists.

## Specimen

`last_frame` is **outcome-bearing for races 6, 15 and 16** — their assertions rest on heartbeat-absence
detection, which is `mono - last_frame >= self._heartbeat_absence_timeout`. WO-031 §4 said so, and was
right.

`last_frame` is **also**:

- the `open_monotonic` opening bound of the **KEEPALIVE_RECONNECT** gap (`kraken_v2_book.py:2674`),
- the same bound for **VENUE_DISCONNECT 4b** (`:2708`) and **4c** (`:2765`),
- the recv-return timestamp of the receive-to-process **latency instrument** (`:2817`).

Threading it to make three tests deterministic would have put injected time into the opening bound of
three of the five ruled gap causes — the corpus's own record of which time ranges are missing data.

**Two true statements about one variable, and only the second one is a red line.**

## WO-031 §4 made no error

This must be recorded plainly, because the shape of the finding invites the wrong conclusion. WO-031
was asked "outcome-bearing for whom," it answered that question correctly and completely, and its
measurement remains the correct sizing for the seam. The precheck asked "consumed by what" — a
question WO-031 was neither asked nor equipped to answer, since a test-side classification looks at
assertions, not at the production call graph downstream of the read.

An audit is bounded by the question it was given. Blaming the earlier answer for not containing the
later question is the same error as trusting a prose figure because it was stated confidently.

## Standing consequence

1. **Any seam threading answers both questions before any edit.** (1) sizes the seam; (2) decides
   whether it may be threaded at all, and by whose authority.
2. **Question (2) is answered from the code, per read, at the call sites** — not inherited from the
   classification that produced (1), and not from a grep. WO-036 opened each site: it was the comments
   at `:2667`, `:2702`, `:2760` and `:2814` that made the finding conclusive rather than suggestive.
3. **The two answers are recorded separately.** A read that is clean on (2) can be threaded at Ops
   authority; a read that is not escalates regardless of how strongly (1) convicts it.

## The meta-point: D42's mode validated on its first firing

D42 established standing Ops authority bounded by declared red lines, with a mandatory precheck at the
boundary. WO-036 was its first real test, and the mode behaved exactly as designed:

- the WO proceeded on standing authority, without waiting for per-item approval;
- the precheck ran **before any threading**, as a gate rather than a risk assessment;
- it fired precisely at the (d) boundary — corpus integrity — and not before;
- **nothing was threaded**, no production file was touched, and the escalation reached the lead with a
  complete call-site enumeration attached.

The value of the mode is that it moves fast where it is safe and stops hard where it is not, and the
first time the stopping mattered, it stopped.
