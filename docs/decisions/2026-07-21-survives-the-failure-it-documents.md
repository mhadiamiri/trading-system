# A component that activates during failure must survive the failure it documents

**Date:** 2026-07-21
**Context:** WO-014c-3 review (project-lead ruling, addendum B).
**Status:** Ruled — now a STANDING §0 review question.

## The named review question

> **Any component whose purpose ACTIVATES DURING FAILURE must be audited for whether it
> SURVIVES the failure it documents.** The reconnect path, the gap ledger, the failure
> capture, the forensic tail.

Three instances found so far, each the same shape one altitude apart:

1. **`_reconnect()` was a no-op (`pass`)** — so the five-failure recovery never ran. The
   mechanism that was supposed to act on failure did nothing when failure came
   (WO-014b-1; `docs/decisions/2026-07-20-reconnect-never-worked-in-production.md`).
2. **The gap ledger evaporated on the terminal event it existed to record** — it was
   in-memory only, so a breaker trip or a process kill lost exactly the gap the ledger
   was built to document (WO-014c-3 §0.1). Fixed with incremental, fsync-at-open,
   append-only persistence: the record is durable the instant the gap opens, before any
   clean shutdown.
3. **The failure capture would drown the run in the failures it was documenting** — an
   unbounded capture under a pathological failure cluster fills the disk and ends the run
   it was meant to observe (WO-014c-3 §0.2). Fixed with a first-N cap that counts every
   failure and announces `FAILURE_CAPTURE_CAPPED`, never a silent truncation and never a
   second termination judgment (the breaker owns termination).

## Why it is standing

This sits alongside the preservation-dual question already in the §0 vocabulary —
"*what must still work when this guard fires?*"
(`docs/decisions/2026-07-19-guard-surfaces-and-denominators.md`). The dual is about the
REST of the system surviving a guard; this question is about the GUARD ITSELF surviving
the very event it exists for. A durability or recovery feature that is present but does not
survive its own triggering condition is a false guarantee — the failure mode is invisible
until the failure it was built for actually happens, which is the worst possible moment to
discover it.

**Apply at §0 review:** for every component whose reason to exist is a failure (reconnect,
persistence, forensic tail, capture, watchdog), ask explicitly: *when that failure occurs,
is this component still there to record/act — or does the failure take it down first?*
