# WO-026 — EVIDENCE INTEGRITY: THE LEDGER IS OVERWRITING COMMITTED EVIDENCE



BASE: HEAD `94bbf0f` on master (local == remote). 216 both orders both interpreters,
CI green both legs (run 30069882143).

SCOPE: §1–§5. Small WO. Commit green, STOP.
SHIP IMPACT: **NO** — conftest, evidence layout, docs. `kraken_v2_book.py` byte-unchanged;
report sha256 before and after (expected `a9388694f0af3d46e596c5aeae50596a9d7ad02da6cc3dd69b3c8da8ea03379b`).

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report.
0.2 No monkeypatching to make a guard pass.
0.3 Fail-then-pass bite proof: four artifacts, `sha256` exact-restore.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 AUTO MODE OFF for any production file.
0.7 Report your `/context` reading; ask the user for it rather than estimating.
0.8 **BUILT-VS-OPERATED DECLARATION (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | Gate ledger session hook (`conftest.py`) | **OPERATED** | Built WO-024 §3; marker mechanism WO-025 §3, committed `94bbf0f` |
    | `git` history of `evidence/WO-024-PASS1/gate_ledger.txt` | **OPERATED** | Committed `b8f18b3` (pass one), re-committed `94bbf0f` (regenerated — the defect) |
    | Run-scoped ledger output path + snapshot discipline | **THIS WO IS THE BUILDER** | Does not exist — §2 |

---

## §1 ESTABLISH THE DAMAGE BEFORE CHANGING ANYTHING

The WO-025 report lists, under changed files, *"the regenerated
`evidence/WO-024-PASS1/gate_ledger.txt`."* The ledger is an autouse session hook writing directly
to a committed evidence path, so every pytest run overwrites pass one's evidence automatically.

Do this first, edit nothing:

1. `git show b8f18b3:evidence/WO-024-PASS1/gate_ledger.txt > /tmp/ledger_passone_true.txt`
   `git show 94bbf0f:evidence/WO-024-PASS1/gate_ledger.txt > /tmp/ledger_regenerated.txt`
   `sha256sum` both. `diff` them. **Paste the sha256 pair and the full diff (or "identical").**

2. Against `/tmp/ledger_passone_true.txt` — the TRUE pass-one blob — re-verify WO-025 §1's
   answer: total invocations, the per-outcome breakdown, and that
   `test_clock_injection_gate` appears SIX times with the sixth being `EARLY_RETURN`.
   **State whether WO-025 §1's answer holds against the true blob or was read off a clobbered
   file.** If it does not hold, STOP and report — the arithmetic finding would be void.

3. Enumerate **every commit** in which `evidence/WO-024-PASS1/gate_ledger.txt` changed
   (`git log --oneline -- <path>`), and for each, whether the change was a deliberate evidence
   update or an incidental clobber by a test run. **State how many runs' evidence has been lost**
   — i.e. whether any ledger state existed that is now recoverable from no commit.

---

## §2 THE FIX — AN INSTRUMENT STREAMS; EVIDENCE IS SNAPSHOTTED (this WO is the builder)

The design error is that the hook's output path IS a committed evidence path. Separate them:

- **Instrument output** → a run-scoped, git-ignored working path (e.g.
  `.artifacts/gate_ledger/<utc-timestamp>-<short-sha>.txt`, plus a `latest.txt` symlink or copy
  for convenience). Written on every run. Never committed. Add the directory to `.gitignore`.
- **Evidence** → a deliberate COPY taken at WO close, into `evidence/<WO>/`, by an explicit
  command a human or a WO runs — never by the test session.

Requirements:
- The session hook MUST NOT write anywhere under `evidence/`. Enforce this **mechanically**, not
  by convention: a check that fails if the ledger's configured output path resolves inside
  `evidence/`. This is the guard for §3.
- Existing committed ledger evidence is **not deleted and not rewritten.** Per standing form,
  annotate. `evidence/WO-024-PASS1/gate_ledger.txt` gets a header comment recording that it was
  incidentally regenerated at `94bbf0f`, that the authentic pass-one blob is at `b8f18b3`, and
  the §1 diff result. Do NOT restore the file contents by overwriting — that would be a third
  rewrite of the same artifact.
- The snapshot step must record provenance in the copied file's header: commit sha, UTC
  timestamp, interpreter, seed/ordering, and the WO that took it.

---

## §3 BITE PROOF — FOUR ARTIFACTS, sha256 EXACT-RESTORE, BOTH DIRECTIONS

- **Mutation A (refusal half):** point the ledger's output path back inside `evidence/` → the
  mechanical check FAILS with a message naming the offending path. Restore; sha256 == pristine.
- **Mutation B (preservation half, local and direct):** a legitimate path under `.artifacts/`
  → the check PASSES and the ledger writes there. Prove the file appears at the run-scoped path
  and that nothing under `evidence/` was modified during the run (`git status --porcelain
  evidence/` empty after a full suite run — paste it).

Artifact 1 pristine PASS, artifact 4 post-restore PASS, sha256 identical.

---

## §4 TWO CLOSEOUT ITEMS FROM WO-025

4.1 **Annotate the pass-one report's incorrect accounting.** `WO-024-PASS1-REPORT.md` states the
    guard test contributes 5 outcomes and totals 40 against a recorded 41. The correct figure is
    6 and 41. Per standing form, ANNOTATE the committed report with a dated correction block —
    do not edit the original text. WO-025 applied this form to the closeout instruction but not
    to this.

4.2 **Report the by-name inventory's GREP PATTERNS.** WO-025 §3 found exactly one other by-name
    test identifier (`tools/vocabulary_enforcement_bite_proof.py:18`) but did not state how it
    searched. Given the 13-vs-38 history, an inventory is only as good as its search. Paste the
    patterns used and re-run over: `tools/`, `conftest.py`, `pytest.ini`, `.github/workflows/`,
    `setup.cfg`/`pyproject.toml`, `.importlinter`, and any Makefile or shell scripts. Include
    deselect/ignore/skip lists and CI job filters, not just nodeid strings. **Enumerate, do not
    convert.** If the count exceeds one, that is the finding.

---

## §5 DECISION LOG — ONE ENTRY

`docs/decisions/2026-07-24-an-instrument-must-not-write-into-the-evidence-record.md`:

> An instrument that streams its output into a committed evidence path rewrites history on every
> run, silently and with no one deciding to. The gate ledger — built to be pass two's safety net —
> overwrote WO-024 pass one's own committed evidence during WO-025, and the overwrite was
> discovered in a changed-files list, not by any guard.
>
> Standing consequence: **an instrument streams to an ignored run-scoped path; evidence is a
> deliberate snapshot taken at close, with provenance in its header.** No test session may write
> under `evidence/`, and that is enforced mechanically rather than by convention.

Record that this is the same family as ground-truth fixtures accreting and never being replaced —
and that the hazard here was worse, because the replacement was automatic rather than authored.

---

## §6 SCOPE FENCE
- NO `connect_fn` threading. NO clock injection. NO transport migration. NO touching sites 29/30.
- NO gate docstring precision note (r20 ruling 2 still UNRULED — STOP and cite if you disagree).
- NO production logic changes.
- NO deleting or content-restoring any committed evidence file.

---

## §7 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → **216**, 0 f/xf/xp · `--randomly-seed=20260729` → same
- BOTH interpreters (3.11 strict, 3.14 dev)
- `git status --porcelain evidence/` **EMPTY** after a full suite run on each leg — paste it
- Marker mechanism still asserting both directions; markered set unchanged (1 test)
- Bite proof: mutations A + B, four artifacts, sha256 exact-restore
- `kraken_v2_book.py` sha256 identical before/after — paste both
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0
  · `preflight_path_check.py` pass
- Test count arithmetic stated explicitly
- Commit, push, local == remote, CI green BOTH legs via `gh run view`
- Append a WO-026 block to `progress.md`

## §8 REPORT — `WO-026-REPORT.md`
The §1 sha256 pair and diff; whether WO-025 §1's answer holds against the true blob; the
per-commit history of the ledger path and how much evidence was lost; the new path layout and the
mechanical check; both bite-proof mutations with sha256 lines; the `git status --porcelain
evidence/` output; the annotation added to the pass-one report; the grep patterns and the full
re-run inventory; the decision log entry; every attempt; any STOP.

**THEN STOP.** The `connect_fn` threading WO is next, in another fresh session.