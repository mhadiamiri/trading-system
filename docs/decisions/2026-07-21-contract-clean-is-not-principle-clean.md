# Contract-clean is not principle-clean

**Date:** 2026-07-21
**Context:** WO-015 review (project-lead ruling). The first live-capture runner resolved the
adapter with a hardcoded `registry.create("kraken_v2", …)` to satisfy the loop→adapter import
boundary. Import-linter stayed 6/6 green — and Principle VII was violated anyway.

## The line for the record

> **A mechanical boundary guard constrains the SHAPE of a dependency, not its CONTENT.** An
> import contract cannot see a hardcoded venue name. Contract-clean is not principle-clean, and
> Principle VII's single-module-swap property has to be checked by reading, not only by linting.

## What happened

The runner may not import a concrete adapter (import-linter contracts "Forbid loop from importing
adapters directly" / "Registry is the sole adapter resolution path"). Resolving through the
factory satisfied that — no concrete adapter imported, contracts 6/6. But the resolved venue was
frozen in a **string literal** (`"kraken_v2"`), which no import contract can see. The effect:
`DATA_SOURCE=kraken_fixture` would still connect to Kraken **mainnet** — configuration saying one
thing, the system doing another, on the single code path that holds a real venue socket, undoing
WO-008b-A1's deliberate fixture-vs-mainnet distinction at the resolution layer.

Fixed by resolving from `DATA_SOURCE` and refusing a non-live-capable adapter loudly
(`LIVE_CAPTURE_UNSUPPORTED`) before any connection.

## Why it generalizes

An import-linter contract checks the *shape* of the dependency graph — which module imports which.
It is blind to *content*: a venue name in a string, a URL, a config key, a magic constant. So a
mechanical guard can be fully green while the principle it stands in for is soft. Principle VII
(single-module venue swap) is a property of what the code *does*, not only of what it *imports* —
and properties like that are verified by reading, by a swap dry-run, or by a test that changes the
config and asserts the behavior follows. Green linters are necessary, not sufficient; the review
must still read for the content the linter cannot.
