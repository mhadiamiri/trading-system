# Decision Log: The F811 Rule Earned Its Place Within One Work Order

**Date**: 2026-07-19
**Status**: RECORDED — build-enforced-over-vigilance, demonstrated at small scale
**Related WO**: WO-008b-A1b (logging a WO-008b-A1 event)

## What happened

While rewiring the adapter in WO-008b-A1, a patch script located its edit region by
anchoring on a string:

```python
end = s.index("    def pause(self) -> None:")
```

`def pause` matches **`LocalBookData.pause` at line 239** — a different class, hundreds of
lines *before* the intended target at line 957. The resulting slice
`s[:start] + NEW + s[end:]` re-included everything from line 239 onward and **duplicated
the entire `KrakenV2BookAdapter` class**. The file went from 937 to 1852 lines with two
complete copies of every method.

Python accepts this silently. The later definition wins; the earlier one becomes dead
code. Exactly the defect shape that produced the original `venue_name` /
`get_diagnostic_counters` duplication — where the surviving definition returned a constant
`"kraken_v2"` and made a live run indistinguishable from a fixture replay.

The syntax check passed. The file imported. Only the mismatched behaviour of the *second*
copy surfaced anything, and it surfaced as a confusing `AttributeError` about a `dict`,
several layers away from the cause.

**`ruff check --select F811` named it immediately:**

```
F811 Redefinition of unused `KrakenV2BookAdapter`
help: Remove definition: `KrakenV2BookAdapter`
Found 2 errors.
```

Restored from git, re-applied every patch with anchors scoped after the start index, and
verified F811 clean after each one.

## Why this belongs in the record

The rule was added in **WO-009 §4** for a defect that had **already been reverted away**.
At the time it looked close to ceremonial: the duplicates it was written to catch no
longer existed, so it could only ever fire on a *future* mistake. WO-009's report said as
much — that its value would come "when the risk actually returns during the WO-008b-A
rewrite."

The risk returned in the very next work order, from a direction nobody predicted: not a
careless copy-paste of a method, but a scripted edit with a bad anchor duplicating an
entire class.

This is **the build-enforced-over-vigilance argument paying off at the smallest possible
scale.** No amount of care would reliably catch a 900-line duplication in a file being
edited by script — the diff is enormous, the syntax is valid, and the symptom appears
somewhere else entirely. A static check that knows what "defined twice" means catches it
in 0.3 seconds, every time, without being clever.

## The general form

Three guards now exist that share one property: they answer a question a careful human
cannot reliably answer by looking.

| guard | question | added |
|---|---|---|
| `tools/preflight_path_check.py` | is the instrument pointed at the right tree? | WO-010 §2 |
| `tools/contract_count_check.py` | did the instrument actually run? | WO-010b |
| `ruff F811` | is anything defined twice, with the second silently winning? | WO-009 §4 |

Each was written after a defect of its class had already caused damage. Each is cheap.
Each has now fired on something its author did not anticipate — F811 within one work order
of being added, and the contract-count check on its own first invalid config.

**The lesson is not "add more rules."** It is that a rule which encodes a *class* of defect
keeps working after the specific instance that motivated it is gone — and that the moment
a rule looks redundant because its original target was fixed is precisely the moment it is
cheapest to keep.

## Evidence

- `evidence/WO-008b-A1/raw_frame_rewire.txt`
- WO-008b-A1 final report, closing note
