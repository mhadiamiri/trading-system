# Decision Log: scope intentions do not survive a shared implementation (WO-028)

**Date:** 2026-07-24
**WO:** WO-028 — connect_fn threading (production), D36
**Authority:** D36 (1b scope / 2b registration contract / 3 full discipline); Principle VII (venue
independence); the call-graph doctrine
**Related:** [[an-instrument-must-not-write-into-the-evidence-record]],
[[a-ruling-about-a-seam-must-be-written-against-its-consumers]],
[[the-exception-must-be-requested-by-name]]

---

## The entry (ratified verbatim)

> A shared builder makes "the live path" and "the production path" the same edit — scope intentions
> do not survive a shared implementation. Ruling D36-1 existed only because one builder
> (`_build_kraken_v2`) serves both `create_live_capture_feed` and `create_feed`; a change scoped to
> "live" could not be confined to live without splitting the builder. General consequence: **scope
> claims are checked against the implementation's sharing topology, not the caller's intent** — the
> call-graph doctrine arriving at scoping decisions.

---

## What the topology forced (WO-028)

The declared default `connect_fn=_REAL_CONNECT` was placed on `_build_kraken_v2` — the single builder
both factory functions route through. Because it is shared, the non-live production path (`create_feed`
→ `registry.create("kraken_v2")` → `_build_kraken_v2`) inherits the declared default automatically,
with **no edit to `create_feed` at all**: a builder-constructed adapter holds `_connect_fn is
_REAL_CONNECT` whether it was reached through the live or the non-live path. The intent "thread the
live path" could not be honoured without also, by construction, threading the non-live path — exactly
because the builder is shared. `create_feed` could not even *forward* the seam if asked to: it is
polymorphic over `DATA_SOURCE`, and the `simulated`/`kraken_public` builders reject `connect_fn`. So
the seam lives where the sharing is (the builder), and the scope of the change is the scope of the
call-graph node it touches — not the caller's stated intent.
