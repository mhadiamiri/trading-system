# WO-067 — DISPOSITION OF TWO ORPHAN RUNS IN `phaseb_20260809`

**Ruled by the operator, 2026-08-23. DISCARD.** Applying WO-044 §2's standing standard: *without
capture-time hashes a run cannot be verified, and an unverifiable run does not enter a corpus whose
value is that every segment is provable.* Same ruling WO-066 applied to its own killed leg.

Both runs were created by **this agent's failed attempts to launch the WO-067 counterpart leg**.
Neither was an operator launch, and neither is a venue or capture defect.

---

## THE TWO RUNS

### `20260822152837` — preflight only, died before the socket

| | |
|---|---|
| contents | `PREFLIGHT.json` only |
| frames | **none** |
| cause of death | launched with `nohup … &`; the process ended when the harness shell tore down |
| seam | none opened |

All twelve conditions were GREEN when it died. It never reached the socket.

### `20260822153020` — 26.7 minutes of real frames, unverifiable

| | |
|---|---|
| contents | `PREFLIGHT.json`, `gap_ledger.json`, `corpus_HADI_20260822T15Z.jsonl` |
| frames | **54,351** (17,437,638 bytes) |
| span | 2026-08-22T15:31:27.666006Z → 2026-08-22T15:58:08.939928Z |
| `run_end` | **NOT WRITTEN** |
| segment hash | **NONE** — the segment never closed, so no at-capture digest exists |
| manifest entry | none |
| cause of death | harness terminated the background task mid-capture |

**Why it is unverifiable, precisely.** The frames are almost certainly fine. That is not the test.
The segment never closed, so no digest was ever computed *by the capturing process against the
bytes as written*. A hash computed now would attest only what the file contains NOW — it cannot
witness the interval between capture and hashing. WO-066 drew exactly this line when it marked its
reconciled legs `hashed_at_capture: false` and refused to conflate them with witnessed ones. Here
there is not even a post-hoc reconciliation to mark: there is no attestation at all.

**It also lands on the open coverage-query defect.** A run killed before `run_end` contributes ZERO
covered hours and is reported as `incomplete_runs: []`. These 54,351 frames were on disk and
invisible to the accounting — the second measured instance of that defect, after the 2.780-hour
ghost recorded in `progress.md`.

---

## WHAT WAS DONE

1. **Backed up in full** to the session scratchpad, `wo067-discarded-runs/`, and every file hashed
   BEFORE removal so the discard is provable rather than merely asserted:

```
770ef81acb03eb57660087c05ab3b7170a760f375284da39328f3bf0cdeb2c4f   4578  20260822152837/PREFLIGHT.json
9f366c7cedbb7b3ea55ad9d961b9cd3d28c4fac93f77c89ee3e34e12704ee882   4664  20260822153020/PREFLIGHT.json
e2cc39d6a6f36a2ab3c65e0a7357a970bbe4524bebe68980ba3139cedbe31e70    201  20260822153020/gap_ledger.json
72b4cc801e41854da3282c39ad03810ed6f611d9aa01ccc7edef319b1b6f82d9  17437638  20260822153020/corpus_HADI_20260822T15Z.jsonl
```

Each backup file was verified byte-identical against its source before anything was removed
(4/4 MATCH).

2. **Removed both directories** from the corpus tree.

3. **Removed seam 4 and its two ledger events.** Not requested explicitly, done under WO-066's
   ruling that *"the discarded run and its seam records were removed"*, and reported here because
   it is a deliberate edit to the corpus's own ledger.

   **Why leaving it would have been worse than removing it.** Seam 4 was `resolved=True` naming
   `resumed_run_id=20260822153020`, a run that no longer exists. `open_seam`'s readoption matches
   only UNRESOLVED seams with the same measured left bound, so a resolved seam over that gap can
   never be adopted — and the next resume after `20260814025055` would have appended a SECOND seam
   for the identical gap. Two seams for one gap is precisely the duplicate the WO-066 readoption
   fix exists to prevent, arriving by a different route. Manifest and seam ledger were backed up
   (`CORPUS_MANIFEST.json.before`, `seam_ledger.jsonl.before`) before the edit.

4. **`--progress` was NOT run**, per instruction. It reconciles from disk and writes; running it
   would have re-derived state we are choosing rather than observing, and would have folded the
   discarded run into the accounting as `hashed_at_capture: false` — the opposite of the ruling.

---

## CORPUS STATE, BEFORE AND AFTER

| | before the failed launches | after disposition |
|---|---|---|
| runs | 5 | **5** |
| seams | 4 | **4** |
| cumulative covered hours | 63.7509 | **63.7509** |
| unfinalized runs | `['20260812022908']` | `['20260812022908']` |
| dangling seam references | 0 | **0** |

**The corpus is byte-for-byte back to its pre-launch state.** `20260812022908` remains the one
unfinalized run — that is the Windows-Update-killed leg from WO-066, untouched by this and still
carrying `hashed_at_capture: false` on all seven of its segments.

---

## THE FINDING THAT CAUSED BOTH

**A long-running capture cannot be hosted by the agent's session.** Two launches, two deaths, one
cause — the harness owned the parent process:

| attempt | mechanism | died | how far it got |
|---|---|---|---|
| 1 | `nohup … &` | shell teardown | preflight GREEN, pre-socket |
| 2 | harness background task | task terminated | 26.7 min of capture |

Neither death came from the capture code, the venue, or any guard. Both are properties of where the
process was parented. **The counterpart leg must be launched from a process the harness does not
own** — the operator's own terminal — and that is how the next attempt will be run.

Recorded rather than retried: a third attempt by the same mechanism would have failed the same way,
and the standing instruction is to report a disruption rather than improvise around it.
