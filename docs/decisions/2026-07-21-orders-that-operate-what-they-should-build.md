# Orders written to OPERATE a thing the order was implicitly supposed to BUILD

**Date:** 2026-07-21
**Context:** WO-015 (project-lead ruling, addendum B), after WO-008b-B-RERUN halted at preflight.
**Status:** Ruled — now a checklist item for every future work order.

## The named Ops failure mode

An order specifies HOW TO OPERATE something that does not exist yet — the order was, implicitly,
supposed to BUILD it. The operating instructions are detailed and correct; the thing they operate
was never poured. Three instances, spanning the project:

1. **WO-008b** specified how to operate a WebSocket transport that **WO-008b was meant to build** —
   the connection logic was a placeholder.
2. **WO-014 §1** scoped an amendment to `settings.py` while the change it described actually
   **spanned three files** — the footprint was larger than the order assumed.
3. **WO-008b-B-RERUN §2** assumed a **live-capture runner that had never existed**:
   `get_live_market_data` had only ever been driven by tests with a patched transport. Nothing in
   the codebase opened a real socket and drove the Data→Strategy→Risk→Execution loop for an hour.
   The re-run halted at its own preflight when the runner was found missing (WO-015 builds it).

Three coincidences become a pattern once named. The pattern is the **authoring layer** (Ops
writing the order), not the code.

## The checklist item

> **EVERY FUTURE WORK ORDER THAT OPERATES ANYTHING STATES WHERE THE OPERATED THING WAS BUILT AND
> VERIFIED, OR DECLARES ITSELF THE BUILDER.**

If an order says "run X / capture with Y / drive Z," it must cite the commit/WO where X, Y, Z were
built and bite-proved — or say explicitly "this order builds it." No order operates an unbuilt
thing by assumption.

## Why it belongs with the §0 carry-over questions

This is the §0 review question — "does this survive what it documents?"
(`docs/decisions/2026-07-21-survives-the-failure-it-documents.md`) — turned on the reviewer itself:
the review loop now audits the ORDER, not just the code the order produces. The same discipline
(state the precondition, verify it exists, don't assume it) applied one level up, at the layer that
writes the preconditions.
