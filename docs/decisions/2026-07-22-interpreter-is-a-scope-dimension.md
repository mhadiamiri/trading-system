# Decision Log: the development host's interpreter is a scope dimension of every local green (WO-021)

**Date:** 2026-07-22
**WO:** WO-021 — Annotation-Name Sweep → Targeted Fix → Version Matrix
**Authority:** Principle VIII (observability); Principle IV/VII (the live-path module involved)
**Related:** [[instrument-competence]], the WO-019/WO-020 CI diagnosis, standing rules 0.1j / 0.1k,
host-scoped baselines (WO-016 D28/D29), instrument identity (WO-013 follow-up)

---

## 5.1 — the interpreter as scope dimension

> "THE DEVELOPMENT HOST'S INTERPRETER IS A SCOPE DIMENSION OF EVERY LOCAL GREEN. `AsyncIterator` was
> used in a live-path annotation and never imported; Python 3.14's PEP 649 deferred evaluation meant
> the name was never looked up, so 215 tests in both orders, import-linter, and ruff were all
> structurally incapable of seeing it. Python 3.11's eager evaluation found it at collection.
> Seventh scope dimension, same family as host-scoped baselines and instrument identity. The
> correction that stings: we assumed CI was a SECOND OPINION when its actual value was COVERAGE OF A
> BLIND SPOT LOCAL STRUCTURALLY CANNOT COVER. Redundancy tolerates a broken leg; complementary
> coverage does not — which is why the no-op import-linter step was worse than it looked, and why the
> matrix keeps both interpreters permanently rather than choosing one."

## 5.2 — symptom suppression at file scope

> "`from __future__ import annotations` would have made CI green by making every annotation lazy on
> every interpreter — fixing nothing and hiding the next instance everywhere. FILE-SCOPE SYMPTOM
> SUPPRESSION IS REFUSED ON THE SAME GROUNDS AS TEST-SCOPE SYMPTOM SUPPRESSION: it is the
> Mock-in-production move performed on the interpreter, silencing the reporter instead of fixing the
> report. Also recorded: the failure shape was WRONG for ten work orders — we hunted
> `ModuleNotFoundError` and it was `NameError` throughout, a hunt inherited from a report never
> re-derived from captured logs until WO-020 made the logs observable."

---

**What was done (WO-021).** Sweep first (`evidence/WO-021/annotation_sweep.txt`), committed standalone
before the fix: the 3.11 collection instrument reported the defect but MASKED its second instance
(a class body aborts at its first bad annotation), so a complementary static scan
(`tools/annotation_name_scan.py`) established the complete denominator — **2** instances, both
`AsyncIterator`, both in `kraken_v2_book.py` (lines 2300, 2718). Fixed with one targeted
`from collections.abc import AsyncIterator` (the canonical home since 3.9); **no `from __future__ import
annotations` was added anywhere**. `ci.yml` now runs a **3.11 (strict/detector) + 3.14 (development)**
matrix, `fail-fast: false`, both legs the full gate, with the intent commented so a future reader cannot
"simplify" the detector away. The strict leg is bite-proved a DETECTOR not a duplicate
(`evidence/WO-021/strict_leg_detector_bite_proof.txt`): an injected unimported annotation name makes
**3.11 collection fail with the real NameError while 3.14 passes (masked)** — the 3.14-passes half being
the artifact that shows why the matrix exists.

**Report-only finding.** `src/trading/data/adapters/registry.py` already carries
`from __future__ import annotations` (pre-existing); left untouched, none added.
