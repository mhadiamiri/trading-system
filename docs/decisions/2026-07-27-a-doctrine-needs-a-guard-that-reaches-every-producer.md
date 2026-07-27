# Decision Log: a doctrine needs a guard that reaches every producer (WO-032 §4.4 / D40)

**Date:** 2026-07-27
**WO:** WO-032 §4 — generalizing the evidence-write prohibition
**Authority:** **D40** (this ruling; next free D-number — D39 is taken by the pass-two classification
method, and no `src/` string cites D40). Builds on WO-026 §2's doctrine.
**Related:** [[an-instrument-must-not-write-into-the-evidence-record]],
[[incidental-coverage-is-not-coverage]], [[instrument-competence]],
[[a-check-is-bounded-by-the-form-it-matches]]

---

## The entry (ratified verbatim)

> A doctrine enforced by a guard scoped to ONE producer is enforced nowhere the guard cannot reach.
> The banned pattern re-enters through a producer the guard cannot see, and it re-enters *silently* —
> because a green suite is indistinguishable from an enforced rule.

---

## Specimen

WO-026 §2 ruled the doctrine after finding that the gate-ledger hook wrote directly to a **committed**
evidence path, so every pytest run silently overwrote committed evidence:

> *An instrument streams to an ignored run-scoped path; evidence is a DELIBERATE snapshot.*

The fix was real and it worked — for the gate ledger. Its mechanical guard,
`conftest.py::_assert_ledger_dir_outside_evidence`, validates one hardcoded `_LEDGER_OUTPUT_DIR`
inside `conftest.py`. It **structurally cannot see a `tools/` script.**

Three work orders later, WO-029 authored `tools/wo029_reverify_partition.py` with

```python
OUT = os.path.join(REPO, "evidence", "WO-029", "partition_reverified_at_head.txt")
```

and wrote to it unconditionally. WO-031 §1 then *instructed* re-running that tool — and doing so
silently overwrote WO-029's committed `VERDICT: PASS` record into a `FAIL` record. **No guard fired.**
It was caught by a human reading a changed-files list: the same detection mode, and the same defect,
that WO-026 existed to eliminate.

The inventory was also far larger than one script. A repo-wide scan found **eleven** tracked `tools/`
scripts writing under `evidence/` — every bite-proof instrument in the tree. The one script anybody
had thought about was the one that had just been caught.

---

## Why the guard did not reach

The WO-026 guard was written against the **instance** (this path, in this file) rather than the
**class** (any producer, any path resolving into `evidence/`). That is not an oversight of care; it is
the natural shape of a fix written at the moment a specific defect is found. The generalization step
is the one that gets skipped, because at the moment of the fix the instance *is* the whole known
population.

This is [[a-check-is-bounded-by-the-form-it-matches]] applied to producers instead of forms.

---

## Standing consequence

1. When a doctrine bans a pattern, **enumerate the producers that can emit it** and build enforcement
   that reaches all of them — not only the one that triggered the ruling.
2. An enforcement scoped to a single call site must **say so in its own text**, so a later reader
   does not mistake local enforcement for the doctrine being enforced.
3. Both halves stay: the WO-032 static scan cannot evaluate a runtime-computed output directory, and
   the WO-026 runtime check cannot see `tools/`. They are belt and suspenders on one doctrine, and
   `test_the_gate_ledger_conftest_guard_still_exists` pins the pairing so removing either is loud.

**What was built under this ruling** (WO-032 §4):
`tests/test_evidence_write_boundary.py` — an AST scan over every **tracked** `tools/*.py` that fails on
any write whose target resolves inside `evidence/`, naming the script *and* the resolved path. It is
write-directed: reading committed evidence stays legal (the reverify tool legitimately reads the
partition table; `replay_checksum_capture.py` legitimately reads a capture dump), because the doctrine
bans *authoring* evidence as a side effect, not reading it. One examined exemption —
`snapshot_gate_ledger.py`, the deliberate snapshot tool — with an honesty test forbidding a stale
entry. Bite-proved both directions: a throwaway `tools/` script pointed into `evidence/` fails the
guard by name and path; the same script pointed at `.artifacts/` passes.
