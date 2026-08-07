# A discrimination set holds only single-purpose tests

**Date:** 2026-08-07
**WO:** WO-050 §5.2 (recording WO-049's finding)
**Status:** RATIFIED

## The doctrine

> A test that exercises **both halves** of a property fails under **either** mutation, and therefore
> attributes nothing.
>
> Broad and contract tests prove the CONTRACT. Only **single-purpose** tests can ATTRIBUTE a
> failure. A discrimination set holds only the latter — and the exclusion of the former is recorded
> **in the proof itself**, not in someone's memory.

## The specimen: WO-049's first run

WO-049 built the aggregate position cap and proved it with two mutations, each meant to break a
different half:

- **Mutation A** — revert to the per-order clamp (the accumulation defect). The **refusal** half
  should fail; the **preservation** half should survive.
- **Mutation B** — refuse all orders at the cap, including reducing ones (over-blocking). The
  **preservation** half should fail; the **refusal** half should survive.

The result:

```
MUTATION A discriminates (refusal fails, preservation holds) : False
MUTATION B discriminates (preservation fails, refusal holds) : False
VERDICT: FAIL
```

**Neither mutation discriminated.** Both halves failed under both mutations, and the proof could not
say which mechanism was doing the work.

The code was correct. The **classification** was wrong. Two tests sat in the discriminating sets
that had no business there:

1. **The S13 contract test** — which asserts refusal *and* preservation in one test, deliberately,
   because §4.1/§4.2 require both halves stated together. By construction it fails under either
   mutation.
2. **A 70-case parametrised invariant sweep** — spanning 7 positions × 2 sides × 5 sizes, so it
   covers increasing and reducing, at, below and beyond the cap. Also fails under either mutation.

Both are good tests. Neither can attribute a failure, because a test that always fails tells you
only that *something* broke.

## Why this is not obvious

The instinct is that a **broader** test is a **stronger** discriminator — more coverage, more
chances to catch the mutation. The opposite is true for attribution. Coverage and attribution pull
in opposite directions:

| | proves the contract | attributes a failure |
|---|---|---|
| broad / S13 / parametrised sweep | ✅ strong | ❌ none |
| narrow / single-purpose | ⚠ partial | ✅ exact |

A suite needs both. A **discrimination set** needs only the second kind.

## What the rule requires

1. Each half of a property gets at least one **single-purpose** test that exercises *only* that half
   — e.g. `test_pure_refusal_zero_headroom_vetoes` and
   `test_pure_preservation_small_reduction_at_the_cap`.
2. The discrimination sets in the bite proof contain **only** those.
3. Broad and contract tests are **explicitly excluded and reported** — WO-049's proof emits them as
   `both_halves_failed`, so their failure under both mutations is visible as expected behaviour
   rather than mistaken for evidence, and a later reader can see the exclusion was deliberate.

## Relation to S13

This does not weaken S13 (refusal and preservation in one test). S13 exists so the two halves cannot
drift apart in different files with different fixtures, and it remains mandatory. The point is that
an S13 test is a **contract statement**, not a **discriminator** — a WO needs both, and must not
mistake one for the other.

## The general form

**A test's value in a suite and its value in a discrimination set are different properties.** The
first asks "does this catch a regression?". The second asks "if this fails, do I know *which*
mechanism broke?". Broad tests answer the first well and the second not at all.
