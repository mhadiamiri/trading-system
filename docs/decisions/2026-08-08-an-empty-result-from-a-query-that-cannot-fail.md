# An empty result from a query that cannot fail is not evidence

**Date:** 2026-08-08
**WO:** WO-053 §1.3
**Ruling:** D52
**Status:** RATIFIED

## The doctrine

> **An empty result from a query that cannot fail is not evidence.**
>
> Before citing a command's silence as proof, establish that the command **could have spoken**. A
> query structurally incapable of returning a finding returns nothing whether or not there is
> something to find, and the two cases are indistinguishable in the output.

## The specimen

WO-051's report offered, as corroboration that the ratified corpus was untouched:

```
git status --porcelain captures/corpus_24h/corpus_20260805/   →   empty at open and close
```

`/captures/` is gitignored. **`git status` on an ignored path always returns empty** — before the
work, after the work, and after deliberately corrupting every file in it. The observation had no
falsifier. It was reported in a table of checks, next to real ones, and read as though it had
passed a test.

WO-052 discovered this while executing the *next* ruling, which asked git to witness the same
corpus across an interval — and found git had never tracked it at all.

## Why this family is harder to catch

This is the guard-that-cannot-bite defect, which the project already knows well: WO-048's force-flat
proof asserted a label and missed a missing trade (D49); WO-050's R4 guard covered one of two fee
sites and reported the same green as a guard covering both (D51 ruling 4a).

But those were **tests**, and tests get bite proofs. This one arrived as an **observation** in a
report. Observations are not mutated, not run under a discrimination set, not asked to fail on
purpose. A number in a table looks like evidence by being formatted like evidence.

That is the gap 0.12 closes.

## The recursion, recorded

The defect was:

- **committed** by WO-051 — the work order whose entire purpose was to stop uncheckable figures from
  propagating, in the same report that correctly identified `a025db1e…` as uncheckable;
- **accepted** by the reviewer, who read the table and did not ask what a non-empty result would
  have looked like;
- **struck** by the executor of WO-052, while carrying out a ruling premised on the same false
  assumption about where the corpus lives.

Every node in the loop failed at some point in the chain, and the error was still caught. **The
loop's integrity lives in no single node.** That is the argument for keeping the ratchet — WO,
execution, report, ruling — rather than trusting any one participant's care, including in the
specific case where the participant is being unusually careful.

It is also the second lead-premise failure in three work orders (a remembered vendor fee in WO-051,
a gitignore in WO-052), which is what extended 0.1e to *cite, do not assume — including about our
own tree*.

## The standing consequence (rule 0.12)

> **Any observation offered as corroboration must state what result would have falsified it.**

The observation-level analog of a bite proof. In practice:

- `git status` / `git log` on a path — first establish the path is **tracked**;
- a grep returning nothing — establish the pattern matches something, somewhere, or the directory
  exists;
- a test suite reporting no failures — establish it **collected** the tests (a suite that collects
  zero passes perfectly);
- a log with no errors — establish the code path ran at all.

If the falsifier cannot be stated, the observation is not evidence and must not be tabled as one.

## Related

- [[2026-08-07-an-integrity-figure-is-computed-by-committed-code]] — the parent ruling
- [[2026-08-08-corpus-20260805-provenance]] — the record this defect corrupted
- [[2026-08-07-a-bite-proof-asserts-the-economic-effect]] — same family, test-level
- [[2026-08-07-a-discrimination-set-holds-only-single-purpose-tests]] — same family, proof-level
