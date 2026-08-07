# An integrity figure is computed by committed code

**Date:** 2026-08-07
**WO:** WO-052 §2
**Ruling:** D51 ruling 2
**Status:** RATIFIED

## The doctrine

> **An integrity-certifying figure must be computed by code committed in the tree it certifies — a
> digest whose scheme lives outside the tree certifies nothing.**
>
> Specimen: `a025db1e…`, certified in five reports (WO-045→WO-050) as proof the ratified corpus was
> untouched, computed by throwaway scripts that were never committed. Twenty candidate schemes failed
> to reproduce it. **It was never a claim about the corpus — only about a script that no longer
> exists.** Fourth member of the repetition family: a number that traveled through five documents on
> the strength of being repeated.
>
> Note the shape: this is the same defect as an uncited fee, ONE LEVEL UP — a figure everyone repeats
> and nobody can check. It was found by the WO that existed to fix the fee version of it.

## What produced it

WO-051 §1 asked for the corpus to be snapshotted at digest `a025db1e…`, the value carried forward
through WO-045, WO-046, WO-047, WO-048, WO-049 and WO-050. It could not be reproduced. Twenty
candidate schemes were tried against the real 88 files — content-only, path-plus-digest under POSIX
and Windows separators, four different path roots, absolute paths, several text-manifest forms,
sorted-hash forms, raw-byte concatenations. None matched.

The scheme had lived in ad-hoc scripts in a scratch directory. Those scripts are gone. With them
went the only definition of what `a025db1e…` meant.

The number was never checkable. Every report that cited it was repeating a predecessor, and the
chain terminated not in a verification but in a deleted file.

## The immediate corollary, discovered by WO-052

WO-052 §1 tried to close the gap with a different witness: git object identity for the corpus paths
across the WO-045→WO-051 interval. **That witness does not exist either.**

`/captures/` is gitignored by deliberate policy (WO-042 §2.3 — capture data must not enter history
it could never be removed from, given a 90-day retention minimum). **Zero corpus files are tracked,
in any commit, in all of history.** There are no blobs and no trees to compare. Confirmed four ways:
`git ls-files` returns nothing; `git log --all -- captures/` returns nothing; `captures/` is absent
from `HEAD^{tree}`; no deletion commit exists, so it was never tracked and later removed.

This produced a second specimen of the same family, and one that had already been published:

> **An empty result from a query that cannot fail is not evidence.**

WO-051's own report cited `git status --porcelain captures/... → empty` as corroboration that the
corpus was untouched. An ignored path *always* reports clean. That line proved nothing, and it was
written by the WO whose entire purpose was to stop uncheckable figures from propagating.

## What actually witnesses the corpus

The capture wrote its own witness and it satisfies this doctrine exactly. `CORPUS_MANIFEST.json`
records, for each of the 38 segments, a `sha256` with `hashed_at_capture: true`, computed by
`trading.data.corpus.sha256_file` — **committed code, in `src/`, in the tree it certifies** — at the
moment each segment was closed.

Verified by `tools/corpus_verify.py` (WO-052): **38/38 segments match, 0 mismatched, 0 missing.**

That is a stronger witness than the git log the ruling asked for:

- it is **per-segment**, so a failure names the corrupted file rather than reporting a
  directory-wide mismatch;
- it dates from **capture**, not from whenever someone first thought to hash the tree, so it covers
  each byte from the moment it was written — an interval no later-computed digest can reach back to.

Its honest limit: it does not prove the manifest itself is unaltered. An actor who rewrote a segment
*and* its manifest entry would pass. Any self-describing artifact has this property; it is recorded
rather than papered over.

## How to apply it

- A digest, checksum, or count offered as proof of integrity **ships with the code that computes
  it**, in the same tree, or it is not evidence.
- Prefer a figure written **by the process that created the data** over one computed later by an
  auditor.
- Before citing a command's empty output as proof, establish that the command **could have produced
  non-empty output**. `git status` on an ignored path, a grep over a directory that does not exist,
  and a test suite that collects zero tests all "pass" identically.
- A figure repeated across reports is not corroborated by the repetition. Re-derive it, or cite the
  committed code that derives it.

## Related

- [[2026-08-07-cite-the-fee]] — the same defect one level down: an uncited constant that traveled
  on the strength of being declared.
- WO-042 §2.3 — why `/captures/` is ignored. The policy is correct and is **not** changed by this
  ruling; the corpus is witnessed by its manifest, not by git.
