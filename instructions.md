# WO-032 — UNBLOCK BATCH B: fix the reverify instrument, commit the D39 amendments, write the docs.

BASE: HEAD `3410435` on master (WO-029 batch-A docs-close). 218 both interpreters, CI green both legs
(run 30279805350). Working tree clean.

WHY THIS WO EXISTS: WO-031 correctly STOPPED at §2 — the D39 amendment to `batch_partition.md` and
the D39 decision docs were ratified in the decision record (`d39`) but NEVER COMMITTED to the tree.
Claude Code operates on the tree, not the decision record; an uncommitted ruling is an unverified
OPERATED row (D24). WO-031 also surfaced a live regression (Finding 4) of the WO-026 evidence-write
defect. This WO repairs the instrument, commits the amendments, writes the docs — then WO-031
re-runs clean.

SCOPE: §1 instrument fix; §2 partition amendment; §3 decision docs; §4 the evidence-write guard
generalization. Commit green, STOP. Converts NO race, threads NO seam.
SHIP IMPACT: **NO** — a `tools/` instrument, evidence markdown, decision docs, and a test-time guard.
Every `src/` production file byte-unchanged; §5 proves it with the five sha256s.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report.
0.2 No `src/` production logic changes. `tools/`, `evidence/`, `docs/`, `conftest.py`/test-fixtures
    only.
0.3 Every guard built gets a fail-then-pass bite proof: four artifacts, sha256 exact-restore.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | `wo029_reverify_partition.py` (line-keyed verdict, evidence-writing) | **OPERATED — DEFECTIVE** | WO-029; Findings 3+4 |
    | WO-026 evidence-write doctrine + `_assert_ledger_dir_outside_evidence` | **OPERATED — TOO NARROW** | `conftest.py:100-112`, guards only the gate-ledger path |
    | `batch_partition.md` (unamended) | **OPERATED — MISSING THE D39 AMENDMENT** | `d0450fa`; the strike never landed |
    | D39 path-preservation + residual-reads-method rulings | **OPERATED — UNCOMMITTED AS DOCS** | Exist in `d39`; no `docs/decisions/` entry |
    | Generalized evidence-write guard reaching `tools/` | **THIS WO IS THE BUILDER** | Does not exist — §4 |

---

## §1 FIX THE REVERIFY INSTRUMENT (Finding 3) — key the verdict on NAME, not LINE

`tools/wo029_reverify_partition.py` fails 25/30 not because any race moved wrongly but because its
verdict requires every race at its ORIGINAL line, and each conversion moves its own file's races. All
30 resolve BY NAME; that is the correct identity (the ratified entry: *position beats name* was for
finding a race, but a partition that must survive conversions keys on the stable identifier, which
here is the test name — line numbers are invalidated by the conversions themselves).

1.1 Change the verdict condition: PASS when all 30 races RESOLVE BY NAME to a real test, 30 distinct,
    categories `{CLOCK-INJECTABLE:26, ASYNCIO-SLEEP:3, ALREADY-CONVERTED:1}`, the 3 asyncio races
    present by name, race #5 in the 26. Line numbers become INFORMATIONAL (report current line, do
    not gate on it). A race whose NAME no longer resolves is still a hard FAIL — that is a real
    partition break.
1.2 Fix the hardcoded trailing sentence (`:95-96`) that prints "the partition stands…converts WHOLE"
    regardless of verdict. The trailing line must reflect the actual verdict — on FAIL it must not
    reassure. (Instrument-competence family.)
1.3 **Bite proof** (§0.3, four artifacts, sha256 exact-restore): mutate the partition table's copy to
    RENAME one race to a non-existent test → the tool FAILS naming that race (a real break is still
    caught). Preservation dual: the pristine table with post-conversion moved lines → PASSES on name
    resolution (the false FAIL is gone). Restore; sha256 == pristine.

---

## §2 COMMIT THE D39 PARTITION AMENDMENT (the missing OPERATED artifact)

Edit `evidence/WO-029/batch_partition.md`:
- **Strike** the batch-A entry's "at construction, terminate via scripted clean-close" — replace with
  the record of what WO-029 actually did: all five converted on their own termination branch
  (deadline via `AdvancingClock`), asserted.
- **Add to the B and C plan entries** the ratified requirement: *a conversion must keep the race on
  its own production termination branch (deadline / venue-close / failure-cap / breaker), and the
  branch exercised before and after is part of acceptance — asserted, not assumed.* No scripted
  clean-close substitution.
- Annotate (do not silently rewrite): a dated note that this amendment implements D39 item 1,
  ratified after `d0450fa`, committed here in WO-032.

This is the artifact WO-031 §2 STOPPED for. After this commit, WO-031's precondition is satisfiable.

---

## §3 WRITE THE TWO D39 DECISION DOCS (ratified in `d39`, never committed)

3.1 `docs/decisions/2026-07-27-a-conversion-preserves-the-path-not-just-the-assertions.md` — WO-029
    §6 item 1, ratified. Use the report's proposed text. The tightened acceptance criterion D39
    added, verbatim: *a conversion's acceptance includes which production branches the test exercises
    before and after, asserted not assumed.* Record it as the conversions-layer arrival of the
    incidental-coverage family (r19).
3.2 `docs/decisions/2026-07-27-a-residual-clock-read-is-classified-not-waived.md` — the ratified
    METHOD (D39): enumerate every real-clock read on a race's path; classify outcome-bearing vs
    incidental; convert only if all incidental; any outcome-bearing read on a non-injectable seam is
    a pre-committed STOP and escalation. Record the seam-sized-to-measurement constraint: convicted
    reads get threaded, incidental residuals stay unthreaded BY DESIGN and recorded — a ruled
    asymmetry, not a place work stopped (the D37/D38 distinction).

(D-numbering: `d39` is the decision record entry; these docs implement it. If the project's doc
convention wants a D-number in the filename or header, use the next free one and state it — do NOT
reuse a number cited in any `src/` string. `git grep` to confirm free.)

---

## §4 GENERALIZE THE EVIDENCE-WRITE PROHIBITION (Finding 4) — this WO is the builder

WO-026 established: *an instrument streams to an ignored run-scoped path; evidence is a deliberate
snapshot.* Its guard watches ONE path inside `conftest.py` and cannot see a `tools/` script — so
`wo029_reverify_partition.py` reintroduced the banned pattern and no guard fired, caught only in a
changed-files list. Three WOs after the doctrine, same defect, same detection mode.

4.1 Fix the instrument: `wo029_reverify_partition.py` must write its output to a git-ignored
    run-scoped path under `.artifacts/` (matching the WO-026 pattern), NOT into `evidence/`. Evidence
    is a deliberate snapshot step, not an instrument side effect. Apply the same fix to ANY other
    `tools/` script that writes under `evidence/` — grep for it and report the full list (there may be
    more than one; WO-025's inventory-was-too-narrow lesson applies).
4.2 Build the generalized guard: a test (or a preflight check runnable in CI) that FAILS if ANY
    tracked `tools/` script contains a write path resolving inside `evidence/`. This is the guard
    that would have caught Finding 4 at authoring time. It must reach `tools/`, which the
    `conftest.py` guard structurally cannot.
4.3 **Bite proof** (§0.3, four artifacts, sha256 exact-restore): point a throwaway `tools/` script's
    output inside `evidence/` → the guard FAILS naming the script and path. Preservation dual: the
    same script writing under `.artifacts/` → PASSES. Restore; sha256 == pristine.
4.4 Decision doc `docs/decisions/2026-07-27-a-doctrine-needs-a-guard-that-reaches-every-producer.md`:
    WO-026's fix guarded the gate ledger's path but not the CLASS; the banned pattern re-entered
    through a producer the guard could not see. A doctrine enforced by a guard scoped to one producer
    is enforced nowhere the guard cannot reach. Same family as *incidental coverage is not coverage*.

---

## §5 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → 218 (+ any tests §4.2's guard adds — state arithmetic),
  both interpreters, 0 f/xf/xp
- `wo029_reverify_partition.py` → **PASS on name resolution** (30/30 by name), writing to `.artifacts/`
- §1 bite proof (name-key), §4 bite proof (evidence-write guard): four artifacts each, sha256 restore
- `git grep` for other `tools/` scripts writing under `evidence/` — full list, all fixed
- The five `src/` production sha256 IDENTICAL (`b06c347e…`, `103a8ba7…`, `5bf833c7…`, `dab18f67…`,
  `3d153a11…`); `git diff -- src/` empty
- `batch_partition.md` amendment committed; the two §3 docs + the §4.4 doc committed
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 ·
  `preflight_path_check.py` pass
- Commit, push, local == remote, CI green both legs (real run number)
- Append a WO-032 block to `progress.md`

## §6 REPORT — `WO-032-REPORT.md`
The reverify verdict change and its bite proof; the partition amendment diff; the three decision docs
as committed; the full list of `tools/` scripts that wrote under `evidence/` and their fixes; the
generalized guard and its bite proof; the five unchanged `src/` hashes; the §5 gate output; the CI
run number; every attempt; any STOP.

**THEN STOP.** WO-031 (batch B classification) re-runs from §1 against the now-committed amended
partition and the fixed, name-keyed, `.artifacts/`-writing reverify tool.