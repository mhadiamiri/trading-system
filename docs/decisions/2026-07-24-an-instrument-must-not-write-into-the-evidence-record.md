# Decision Log: an instrument must not write into the evidence record (WO-026)

**Date:** 2026-07-24
**WO:** WO-026 — evidence integrity (the ledger was overwriting committed evidence)
**Authority:** D24 (built-vs-operated); Principle VIII (observability / an honest record); the
ground-truth-fixture accretion family
**Related:** [[an-enumeration-is-only-as-good-as-its-identifiers]],
[[incidental-coverage-is-not-coverage]], [[a-guard-can-audit-the-object-model]]

---

## The entry (ratified verbatim)

> An instrument that streams its output into a committed evidence path rewrites history on every
> run, silently and with no one deciding to. The gate ledger — built to be pass two's safety net —
> overwrote WO-024 pass one's own committed evidence during WO-025, and the overwrite was
> discovered in a changed-files list, not by any guard.
>
> Standing consequence: **an instrument streams to an ignored run-scoped path; evidence is a
> deliberate snapshot taken at close, with provenance in its header.** No test session may write
> under `evidence/`, and that is enforced mechanically rather than by convention.

---

## The family it joins

This is the same family as **ground-truth fixtures accreting and never being replaced** — a record
that grows or mutates without anyone authoring the change. The hazard here was **worse**, because the
replacement was **automatic** rather than authored: a fixture at least changes only when someone edits
it; the gate ledger's committed blob was overwritten by the mere act of running the suite, so the
authentic pass-one evidence at `b8f18b3` was silently succeeded by two regenerated blobs (`959e832`,
`94bbf0f`) that no one decided to commit as evidence — they rode in on unrelated commits' changed-files
lists. The arithmetic finding of WO-025 §1 was then read off a clobbered file (it happened to hold
because the instrument is reproducible; that it held was luck, not design).

---

## What was built (WO-026)

The instrument now streams to `.artifacts/gate_ledger/<utc>-<sha>.txt` (+ `latest.txt`),
git-ignored, never committed. Evidence is authored by `tools/snapshot_gate_ledger.py`, which stamps a
provenance header (commit, UTC, interpreter, seed/ordering, the WO). A **mechanical guard** in
`conftest.py` (`_assert_ledger_dir_outside_evidence`) fails loudly if the configured output directory
resolves inside `evidence/` — enforced, not conventional, and bite-proved both directions. The
clobbered `evidence/WO-024-PASS1/gate_ledger.txt` was **annotated, not restored** (restoring by
overwrite would be a third rewrite of the same artifact); the authentic blob remains at `b8f18b3`.
