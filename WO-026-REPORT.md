# WO-026 — EVIDENCE INTEGRITY — REPORT

**Base:** `94bbf0f` (worked from `147b010`, the WO-025 docs-close — identical code).
**Ship impact: NO** — conftest, evidence layout, tooling, docs. `kraken_v2_book.py` byte-unchanged:
sha256 `a9388694f0af3d46e596c5aeae50596a9d7ad02da6cc3dd69b3c8da8ea03379b` **before AND after**.

**`/context` (0.7):** measured **68%** at WO-026 start (user ran `/context`) — at the ~70% §0.7 STOP
threshold. The user directed resuming in this session; recorded as an explicit choice.

**§0.8 built-vs-operated:** the gate-ledger session hook exists (WO-024 §3 / WO-025 §3, `94bbf0f`);
the ledger's git history exists (b8f18b3 / 959e832 / 94bbf0f). The run-scoped path + snapshot
discipline is the row THIS WO built.

---

## §1 — THE DAMAGE (established before any edit)

**sha256 pair:**
- authentic pass-one blob `git show b8f18b3:…/gate_ledger.txt` → `9f54efa536e58ee0287153d4c123c6d175bab84672e7238a59cb81e36c14f1a6`
- regenerated at `94bbf0f` → `51732bcd119643a3b319ff1fda422f087af41e71409c3446bf27636c85efba42`

**diff (b8f18b3 vs 94bbf0f): they DIFFER** — header `WO-024 →  WO-024/WO-025`; the "EXCLUDING the
guard's own test" (by-name) section became the "MARKER-BASED TOLERANCE" section; per-invocation ORDER
differs (randomized seed); guard-test lines gained `[markered]`. The **arithmetic is identical** in
both (total 41; guard test = 6 invocations; the sixth `EARLY_RETURN`).

**Does WO-025 §1's answer hold against the TRUE blob? — YES.** Re-verified against
`/tmp/ledger_passone_true.txt` (the b8f18b3 blob): Total 41; EARLY_RETURN 35 / PROCEED_DECLARED 2 /
PROCEED_COHERENT 1 / REFUSED_COUPLING 2 / REFUSED_COHERENCE 1; `test_clock_injection_gate` appears SIX
times, the sixth `EARLY_RETURN`. WO-025 §1's answer was CORRECT — but it was read off the CLOBBERED
`94bbf0f` file, not the authentic blob. It held only because the instrument is reproducible.

**Commit history of the path** (`git log --oneline -- evidence/WO-024-PASS1/gate_ledger.txt`):
`b8f18b3` (pass-one batch 1 — the authentic first capture), `959e832` (pass-one batch 2 — an
INCIDENTAL clobber: a pass-one acceptance run's output swept into the docs commit), `94bbf0f` (WO-025 —
an INCIDENTAL clobber: a WO-025 acceptance run's marker-form output). **Evidence lost:** none
irrecoverably — the instrument is a reproducible deterministic output (only per-invocation ORDER varies
by seed), and the authentic pass-one blob survives at `b8f18b3`. Dozens of intermediate runs overwrote
the working file, but no run held a UNIQUE state; the defect is the automatic-overwrite mechanism, not
a specific lost measurement.

---

## §2 — THE FIX (instrument streams; evidence is snapshotted)

- **`conftest.py`:** the ledger output directory is now `_LEDGER_OUTPUT_DIR = REPO_ROOT/.artifacts/gate_ledger`
  (git-ignored, run-scoped `<utc>-<sha>.txt` + `latest.txt`, NEVER committed). The mechanical guard
  `_assert_ledger_dir_outside_evidence` runs at session end BEFORE any write and RAISES
  `GATE_LEDGER_PATH_IN_EVIDENCE` (naming the path) if the configured dir resolves inside `evidence/`.
- **`.gitignore`:** `.artifacts/` added.
- **`tools/snapshot_gate_ledger.py`:** the DELIBERATE snapshot — copies a run-scoped ledger into
  `evidence/<WO>/` with a provenance header (commit sha, UTC timestamp, interpreter, seed/ordering, the
  WO). No test session imports or runs it.
- **`evidence/WO-024-PASS1/gate_ledger.txt`:** ANNOTATED with a header (incidentally regenerated at
  `94bbf0f`; authentic blob at `b8f18b3`; the §1 sha256 pair + diff result) — **NOT content-restored**
  (that would be a third rewrite; §6).

---

## §3 — BITE PROOF (`evidence/WO-026/evidence_guard_bite_proof.txt`)
Four artifacts, sha256 exact-restore of `conftest.py` (pristine sha256 pasted in the artifact file):
- **Artifact 1** — pristine PASS; `git status --porcelain evidence/` unchanged during the run.
- **Mutation A (refusal half)** — point `_LEDGER_OUTPUT_DIR` inside `evidence/WO-024-PASS1` → the
  session-end guard RAISES `GATE_LEDGER_PATH_IN_EVIDENCE: … resolves inside …/evidence …` at teardown.
  Restore sha256 == pristine.
- **Mutation B (preservation half, local & direct)** — a DIFFERENT legit `.artifacts/gate_ledger_biteB`
  path → guard PASSES, ledger writes there (`ls` shown), `evidence/` untouched during the run. Restore
  sha256 == pristine.
- **Artifact 4** — post-restore PASS; final sha256 == pristine (IDENTICAL: YES).

---

## §4 — TWO CLOSEOUT ITEMS

**4.1 — pass-one report annotated.** `WO-024-PASS1-REPORT.md` gained a dated correction block (original
text preserved): the guard test contributes **6** outcomes and **41** total, not 5/40 — the missing one
is the guard test's assertion-5 `EARLY_RETURN`.

**4.2 — by-name inventory, grep patterns stated, and THE COUNT EXCEEDS ONE (the finding).** WO-025 §3
reported exactly ONE by-name identifier without stating its search. Re-run with explicit patterns —
  P1 hardcoded nodeids: `tests/[^ ]*::` , `::test_[A-Za-z0-9_]+` , `[A-Za-z0-9_]+\.py::`
  P2 deselect/ignore/skip/filters: `deselect|collect_ignore|--ignore|norecursedirs| -k |addopts|filterwarnings|skip.*test_`
  P3 by-name refs in tooling/CI: `test_[a-z_]+` inside quoted strings
— over `tools/ conftest.py pytest.ini pyproject.toml setup.cfg .importlinter .github/workflows/ Makefile`
(setup.cfg / .importlinter / Makefile absent). **Result: ~12 hardcoded test nodeids across FIVE tooling
bite-proof scripts** — `tools/emission_bite_proof.py` (3), `tools/instrument_mismatch_bite_proof.py` (1),
`tools/vocabulary_enforcement_bite_proof.py` (1 — the one WO-025 found), `tools/vocabulary_scan_bite_proof.py`
(4), `tools/wire_string_bite_proof.py` (3). WO-025's "exactly one" was a search-too-narrow miss (it
didn't match the `f"{T}::test_…"` and multi-line `NODE` forms). No deselect/ignore/skip by-name lists
exist (`pytest.ini` addopts is `-v --strict-markers --tb=short`; pyproject has no collection filters).
**Enumerated, NOT converted** — a later identifier-hardening WO can be written against this real list.

---

## §5 — DECISION LOG
`docs/decisions/2026-07-24-an-instrument-must-not-write-into-the-evidence-record.md` — ratified verbatim,
recording the ground-truth-fixture-accretion family and that this hazard was worse (automatic, not
authored).

---

## §6 — SCOPE FENCE (honored)
No `connect_fn` threading, no clock injection, no transport migration, no touching sites 29/30, **no
gate docstring precision note** (r20 ruling 2 still unruled — not added), no production logic, no
deleting or content-restoring any committed evidence (the pass-one ledger was annotated, not restored).

---

## §7 — ACCEPTANCE

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest -p no:randomly -rX` | __311_DET__ | __314_DET__ |
| `pytest --randomly-seed=20260729 -rX` | __311_RAND__ | __314_RAND__ |

- **`git status --porcelain evidence/` EMPTY after a full suite run on each leg** → __EVIDENCE_CLEAN__
- Marker mechanism still asserting both directions; markered set unchanged (1: `test_clock_injection_gate`).
- Bite proof: mutations A + B, four artifacts, sha256 exact-restore (above).
- `kraken_v2_book.py` sha256 `a9388694…` BEFORE == AFTER.
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 ·
  `preflight_path_check.py` pass.
- **Test-count arithmetic:** WO-026 adds/removes no test (conftest path change + a tooling script + docs).
  **Total stays 216.**
- **Commit / push / CI:** __COMMIT_CI__

---

## STOPPED / attempts / changed-but-not-asked
- **STOPPED at:** nothing in WO-026 (§1 verified WO-025 §1 holds → no STOP; §2–§5 completed).
- **0.5 attempts:** the bite proof ran once per direction; no failed/retried edits.
- **Changed but not asked?** Only: `conftest.py` (path + guard), `.gitignore` (.artifacts/),
  `tools/snapshot_gate_ledger.py` (new), `evidence/WO-024-PASS1/gate_ledger.txt` (annotation),
  `WO-024-PASS1-REPORT.md` (dated correction), the new decision log, this report, `progress.md`, and
  `evidence/WO-026/`. `instructions.md` carries the WO text. **No production logic.**
