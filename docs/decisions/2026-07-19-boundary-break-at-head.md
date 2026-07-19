# Decision Log: Boundary Break at HEAD (Principles IV & VII violated in the shipped tree)

**Date**: 2026-07-19
**Status**: RESOLVED (fix landed in WO-010 §5)
**Related WO**: WO-010 §8 entry 1

## What happened

`src/trading/data/adapters/factory.py:15` carried a module-level import:

```python
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
```

Committed in **`af27491`**. This created the import chain:

```
trading.loop.live -> trading.data.adapters.factory -> trading.data.adapters.kraken_v2_book
```

That chain violates the contract *"Forbidden v2-book-checksum imports above adapter"*,
and with it **Constitution Principle IV** (Layered Architecture, Enforced Boundaries)
and **Principle VII** (Venue Independence). Venue-specific v2/book/checksum detail was
reachable from the loop layer in the shipped tree.

## Duration

Present continuously from `af27491` (2026-07-18) through `43ca600`. Verified per-commit
in WO-010 §6 against the real tree using the contract set as it existed at `43ca600`:

| commit | kept | broken | deps |
|---|---|---|---|
| 400a28b (control) | 4 | 0 | 171 |
| af27491 | 3 | 1 | 174 |
| 90882d0 | 3 | 1 | 175 |
| 8e8a891 | 3 | 1 | 176 |
| 43ca600 | 3 | 1 | 176 |

## Why it was not detected

It was detected only **after** the environment was corrected. Until then import-linter
was analysing a stale tree. See `2026-07-19-instrument-pointed-at-wrong-tree.md`.

## Resolution

WO-010 §5: adapter registry (`registry.py`). `factory.py` no longer imports any concrete
adapter module; it resolves by name. Contracts now **5 kept, 1 broken**, the single break
being the intentional new *"No test doubles in production code"* rule, which is expected
RED until WO-008b-A removes the committed `Mock`.

The `ignore_imports` exemption for `trading.loop.live -> trading.data.adapters.factory`
was also **removed**, since the registry makes it unnecessary. Keeping it would have
preserved a mask.

## Evidence

- `evidence/WO-008b-DIAG/import_linter_contract_broken.txt` (discovery)
- `evidence/WO-010/retroactive_audit.txt` (per-commit audit)
- `evidence/WO-010/registry_bite_proof.txt` (fail-then-pass)
