# A number can be wrong in a way that survives being questioned for the wrong reason

**Date:** 2026-08-08
**WO:** WO-058 §2.1
**Ruling:** D58 ruling 1
**Status:** RATIFIED

## The doctrine

> **A number can be wrong in a way that survives being questioned for the wrong reason.**
>
> The derivation was audited — correctly found underived — and nobody asked whether it was the
> same quantity.

## The specimen: "12.33 GB free"

`12.33 GB` was carried through WO-054, WO-055 and WO-056 as the Term 2 reference for **free
memory**, taken from the WO-044 capture's preflight record.

It is not free memory. `LoadRecord.capture()` computed:

```python
memory_gb = psutil.virtual_memory().used / (1024 ** 3)
```

Host memory **USED**. Three reports compared today's *available* memory against the reference
capture's *used* memory — two different quantities, on opposite sides of the total.

Corrected on this host (total 15.715 GiB):

| | memory USED | ⇒ memory FREE |
|---|---:|---:|
| WO-044 capture (banked 12.9 h) | 12.334 GiB | **~3.381 GiB** |
| a later reading called RED | 11.141 GiB | 4.573 GiB |

**The capture that succeeded ran with LESS free memory than the readings later called RED.**

## The consequence, stated plainly

**An unreachable gate demanding ~3.6× more headroom than the reference capture itself ever had,
blocking a capture the host was always able to run.**

Three work orders reported Term 2 RED on that ground. WO-055 declined to open a socket partly
because of it. The grant went unspent.

## Why this one is different from `a025db1e…`

The digest was *uncheckable* — its scheme was gone, so nobody could evaluate it. This number was
fully checkable at every moment. It sat in a JSON file that anyone could open.

And it **was** questioned. WO-057 §2 was written precisely because the figure looked underived, and
that instinct was correct: it was underived. D57 re-specified the gate around a mechanism instead.
But the audit asked *"where does this threshold come from?"* — the right question about the
**derivation** — and never asked *"is this the quantity the name says it is?"*, the question about
the **identity**.

Questioning a number's provenance and questioning its identity are different acts. Passing the
first is not evidence of the second. A figure can survive a genuine audit because the audit was
aimed one layer away from the defect.

## The compounding shape

This is the third document-vs-reality naming defect in this project, and the name did the damage:
`memory_gb` states a unit and a subject but not the *quantity*. A reader supplies the missing word
from context, and "the memory figure in a preflight that gates on headroom" reads as free memory.

Renamed to `memory_used_gb` under D58 ruling 2, with the old key retained as a compatibility alias
so `corpus_20260805` stays readable.

## How to apply it

- When a figure is questioned and survives, **record which question it survived.** "Audited" is not
  a property; "audited for derivation" is.
- Before comparing two numbers, confirm they are **the same quantity**, not merely the same unit
  and shape. Two GB figures about memory can be opposites.
- A field name should state the **quantity**, not just the unit. `memory_gb` is a unit;
  `memory_used_gb` is a claim.
- A gate whose threshold no healthy host could satisfy is evidence about the threshold, not about
  the host. **When a mechanism-tied criterion is unreachable in practice, suspect the criterion.**

## Related

- [[2026-08-07-an-integrity-figure-is-computed-by-committed-code]] — `a025db1e…`, the uncheckable
  sibling
- [[2026-08-08-an-empty-result-from-a-query-that-cannot-fail]] — the same family at the
  observation level
