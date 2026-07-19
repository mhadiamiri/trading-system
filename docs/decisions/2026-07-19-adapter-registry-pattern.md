# Decision: Adopt Registry Pattern for Adapter Resolution

**Date**: 2026-07-19
**Status**: ADOPTED (implemented in WO-010 §5)
**Related WO**: WO-010 §8 entry 3

## Decision

Adapters **self-register** under a config name; the factory resolves by name from
`DATA_SOURCE`. Implemented as a name→builder dict plus a registration decorator in
`src/trading/data/adapters/registry.py` (**18 executable lines**).

## Why — and what was rejected

The boundary break (see `2026-07-19-boundary-break-at-head.md`) came from `factory.py`
importing concrete adapter modules at module level.

**A lazy / function-local import was explicitly REJECTED.** It would have removed the
violation from static analysis while leaving the dependency real — hiding the edge from
the linter is the exact defect shape this episode is about. We do not fix a masked
violation with a sanctioned mask.

**Scope discipline was ruled in advance:** dict + decorator only. No plugin framework,
no entry-points machinery, no dynamic discovery, no auto-scanning. Over-engineering the
factory is a known failure mode of this project's history. Delivered within that bound:
18 lines, no abstraction beyond a dict and a decorator.

## Shape

```
trading.data.adapters.__init__   -> imports each adapter module (registration trigger)
adapter module                   -> @register("<name>") on a builder function
trading.data.adapters.factory    -> registry.create(DATA_SOURCE)
```

The adapter imports live **inside** `trading.data.adapters` — the one package permitted
to know concrete adapter modules. Nothing outside it imports an adapter module.

## Contract encoding (§5.2)

Added: *"Registry is the sole adapter resolution path"* — no module in `strategy`,
`risk`, `execution`, `backtest`, or `loop` may import a concrete adapter module.

Removed: the `ignore_imports` exemption for
`trading.loop.live -> trading.data.adapters.factory`. It existed only because factory
imported adapters directly; the registry makes it unnecessary, and retaining it would
preserve a mask.

Result: **5 kept, 1 broken** — the single break being the intentional
*"No test doubles in production code"* rule (expected RED until WO-008b-A).

## This is also Sprint 3's venue-swap mechanism

Built early by necessity, but it is the mechanism Principle VII has always required:
add one adapter module, it registers itself, config names it, nothing else moves. A
venue swap becomes a single-module change, as the constitution demands.

## Verification

- Fail-then-pass bite proof: `evidence/WO-010/registry_bite_proof.txt`
  (before: 3 kept / 2 broken → after: 5 kept / 1 broken)
- Full suite unchanged: `73 passed, 8 xfailed in 237.37s`, 81 collected
