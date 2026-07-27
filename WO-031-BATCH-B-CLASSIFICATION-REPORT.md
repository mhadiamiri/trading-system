# WO-031 — PASS TWO, BATCH B CLASSIFICATION: **STOPPED AT §2. NO COMMIT.**

**Outcome: the pre-committed STOP of §2 fired.** The D39 amendment to `batch_partition.md`'s B/C plan
is **not present in the committed file** — it exists only inside `instructions.md`. Per §2 ("If it is
NOT (e.g. the amendment was described but not committed), STOP and report — batch B cannot be planned
against an unamended partition") and §0.7 ("Any OPERATED row not verified as stated → STOP and
report"), the classification of §3/§4 was **not produced**.

Per §0.1 this is an **expected outcome, not a failure**. Nothing was converted, no seam was threaded,
no test or src file was edited. Following the precedent of WO-029's own §2.0 STOP (`progress.md`:
"STOPPED at §2.0, no commit"), **nothing is committed** and no `progress.md` block is appended —
both await the lead's disposition.

**Two further findings surfaced, one of them a live defect in an instrument this WO was instructed to
run.** They are at §Finding-3 and §Finding-4 and matter independently of the STOP.

---

## §0 RULES OF ENGAGEMENT — disposition

| Rule | Disposition |
|---|---|
| 0.1 No discretion; code wins; STOP is an expected outcome | **HELD.** The §2 condition was met and the WO stopped there. §3/§4 were not attempted under an assumed amendment. |
| 0.2 No edits beyond one evidence artifact + a progress.md block | **HELD — with one incident, repaired.** The §1-mandated tool overwrote a committed evidence file as a side effect of being run (see Finding 4). Restored via `git checkout`; tree verified clean. No test or src file touched. |
| 0.3/0.4 No guards built; no bite proof owed | **N/A** — no guard built. No classification instrument was written (the classification was not reached). |
| 0.5 Report every attempt | **HELD** — §Attempts. |
| 0.7 BUILT-VS-OPERATED (D24) | **ONE ROW FAILS** — table below. |

### §0.7 — the OPERATED rows, verified at this HEAD

| Thing | Claimed | Verified? | Evidence |
|---|---|---|---|
| WO-029 batch A partition (`batch_partition.md`) | OPERATED — committed `d0450fa`, **amended B/C plan per D39** | **NO — the amendment is absent** | `git log -- evidence/WO-029/batch_partition.md` → **exactly one commit, `d0450fa`**. Committed text still contains the phrase the amendment was to strike. See §2. |
| The 26-race enumeration + `wo029_reverify_partition.py` | OPERATED — WO-029 §2.0, `f0660e3` | **YES, with a caveat** | Tool exists and runs; all 30 names resolve; categories 26/3/1 correct. But it now exits 1 / VERDICT FAIL — see Finding 3. |
| `AdvancingClock` self-advancing fixture | OPERATED — shared harness | **YES** | `tests/fixtures/fake_ws_transport.py:248` `class AdvancingClock`, sharing `_coherence_token` (`:287`, `:295`) beside `FakeClock` (`:46`). |
| Clock seam through runner/factory/builder | OPERATED — WO-030 | **YES** | `live_capture.py:58-59,85-86,135-136`; `factory.py:68-69,112-113`; `registry.py:34` `_LIVE_FORWARDED_PARAMS = ("connect_fn", "monotonic_clock", "wall_clock")`. |
| The batch-B clock-read classification | THIS WO IS THE BUILDER | **NOT BUILT** | Blocked by the §2 STOP. |

---

## §1 — HEAD, SUITE, AND BATCH-B MEMBERSHIP (completed before the STOP)

**Actual HEAD: `3410435`** — `WO-029 batch A close: CI GREEN both legs (run 30279805350) + fill run id
in report/progress`.

The WO names base `f0660e3`; `3410435` is the docs-only close sitting on top of it. Verified
docs-only: `git diff --stat f0660e3 3410435` → `WO-029-BATCH-A-REPORT.md | 2 +-`,
`progress.md | 5 +++--` — **2 files, 4 insertions, 3 deletions, no code**. Working tree clean at start
(`git status --porcelain` → only the lead's own `instructions.md` edit).

**Suite — 218 on both interpreters, deterministic order:**

| Interpreter | Command | Result |
|---|---|---|
| 3.14.6 (ambient) | `pytest tests/ -p no:randomly -rX` | **218 passed** in 245.82 s, 0 f/xf/xp |
| 3.11.15 (strict, throwaway uv venv) | `pytest tests/ -p no:randomly -rX` | **218 passed** in 245.03 s, 0 f/xf/xp |

`PYTHONUTF8=1` was set on every invocation (without it `contract_count_check.py` aborts the session at
`pytest_sessionstart` with a `TypeError` that is really a cp1252 decode failure — environmental, not a
repo defect; CI is Linux/UTF-8 and never sees it).

**Batch B membership — confirmed against the committed file, matches the WO exactly:**

| File | Races | Count |
|---|---|---|
| `test_gap_recording.py` | 6, 7, 8, 9, 10, 11 | 6 |
| `test_keepalive.py` | 15, 16 | 2 |
| `test_failure_cap.py` | 17, 18, 19 | 3 |
| `test_failure_capture.py` | 20, 21 | 2 |
| | | **13** |

This is byte-for-byte what `batch_partition.md` states. **No discrepancy — no STOP on this criterion.**

**`tools/wo029_reverify_partition.py` — did NOT return 30/30. It returned 25/30 and exited 1.** This
is Finding 3; it is not a partition defect and it does not move any batch-B race.

---

## §2 — THE STOP: THE AMENDED B/C PLAN DID NOT LAND

§2 requires confirming that WO-029's ratification amended `batch_partition.md`'s B/C plan to **strike
"scripted clean-close"** and **require conversion on the race's own termination branch, asserted not
assumed**. It did not.

**Evidence, four independent checks:**

**(a) The file has exactly one commit — the pre-ratification one.**
```
$ git log --oneline -- evidence/WO-029/batch_partition.md
d0450fa WO-029 §2.0 + §2.0-bis: partition + the AdvancingClock deadline fixture (harness build)
```
`d0450fa` predates both the batch-A conversion (`f0660e3`) and any ratification of WO-029's §6.
No later commit touches the file.

**(b) The working tree is identical to HEAD for that file** — so this is not an uncommitted local
amendment: `git diff --exit-code HEAD -- evidence/WO-029/batch_partition.md` → clean.

**(c) The phrase the amendment was supposed to STRIKE is still present**, at line 54 of the committed
file:
> `at construction, terminate via scripted clean-close); **4** DIRECT deadline-assertion (uses the new`

**(d) The committed B/C plan carries no termination-branch requirement at all** — it names files and
race counts only:
> - **BATCH B (named, not touched):** `test_gap_recording.py` (6: races 6–11), `test_keepalive.py`
>   (2: 15–16), `test_failure_cap.py` (3: 17–19), `test_failure_capture.py` (2: 20–21) = **13 races**.
> - **BATCH C (named, not touched):** `test_ledger_persistence.py` (1: 12), `test_host_suspend.py`
>   (1: race 14 — the non-foundation one), `test_protocol_ping.py` (2: 22–23), `test_throughput.py`
>   (1: 24), `test_reconnect_to_effect.py` (1: 25), `test_venue_close_path.py` (1: 26),
>   `test_backoff_breaker.py` (1: 27) = **8 races**.

**(e) Repo-wide, the amendment language exists only in `instructions.md`.** Searching every tracked
file for `own termination branch`, `asserted not assumed`, `strike…clean-close`, `amended partition`:

```
instructions.md:52  ## §1 CONFIRM HEAD, SUITE, AND THE AMENDED PARTITION
instructions.md:54  ...(the amended partition
instructions.md:62  WO-029's ratification amended `batch_partition.md`'s B/C plan to strike "scripted clean-close" and
instructions.md:63  require conversion on the race's own termination branch, asserted not assumed. Confirm that
instructions.md:65  committed), STOP and report — batch B cannot be planned against an unamended partition.
instructions.md:149 batches B/C convert under the amended partition.
```

Zero hits in `evidence/`, `docs/`, `progress.md`, or any report. Untracked files: none
(`git status --porcelain -uall` → only ` M instructions.md`).

**This is exactly the failure mode §2 names in its own parenthetical — "the amendment was described
but not committed."**

### Related: no D39 decision-log entry exists either

The WO refers to D39 as a ratified ruling. There is **no committed decision document for it**.
`docs/decisions/` holds 15+ dated entries, the most recent being `2026-07-25-a-transport-seam-is-not-a-clock-seam.md`.
No entry corresponds to WO-029 §6's proposed title *"a conversion preserves the path, not just the
assertions."* WO-029's own report states, at §6: *"No entry was written. Both items below are reported
for a ruling."* That remains the committed state of the repo.

**The D-number itself is free — this is NOT a collision.** D39 was used by WO-028 as an explicitly
flagged placeholder ("leave the D-number as D39 for the lead to confirm"), and WO-030 §3 then
**superseded it**: the production message was generalized to `LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM`
citing **D38**. Verified: `git grep "D39" -- src/` returns **nothing** — no production file cites D39.
Residual D39 mentions are confined to `WO-028-REPORT.md`, `evidence/WO-028/`, and `progress.md`, all
historical. So reusing D39 for the classification ruling is clean; it simply has not been written down.

---

## §3 / §4 — NOT PRODUCED

The per-race clock-read classification (§3) and the outcome-bearing aggregate that would size the
keepalive seam WO (§4) were **not produced**, because §2 stopped the WO before them.

This was a deliberate reading, not an omission of convenience. §3.1 requires naming each race's
termination branch under "the *criterion D39 tightened onto acceptance*", and §4's whole purpose is to
size a downstream WO against a ruling. Producing that measurement against a ruling that exists in no
committed artifact would be building on an unverified OPERATED row — the precise failure D24
(built-vs-operated) exists to prevent, and the reason §0.7 makes an unverified row a STOP.

**Consequently `evidence/WO-031/batch_b_clock_read_classification.md` was not written**, and §4's
conditional fork (expected keepalive/ping-shaped set → proceed; surprising or instrument-touching set →
return to the lead) **cannot be stated**. Neither branch obtains; the measurement does not exist.

---

## Finding 3 — `wo029_reverify_partition.py` is stale-by-construction after every batch

§1 asks for 30/30. The tool returned **25/30 and exit code 1, VERDICT FAIL**. The five that did not
verify are **batch A's own races 1–5**, all in `test_live_capture.py`:

```
 1  MOVED->82   test_live_capture.py:59  -> test_runner_drives_instrumented_transport_end_to_end
 2  MOVED->128  test_live_capture.py:96  -> test_runner_persistence_is_not_optional_on_the_adapter
 3  MOVED->151  test_live_capture.py:111 -> test_short_bounded_run_completes_with_readable_artifacts
 4  MOVED->185  test_live_capture.py:136 -> test_clean_deadline_close_does_not_reconnect_dual
 5  MOVED->256  test_live_capture.py:190 -> test_runner_resolves_live_adapter_from_data_source_via_factory
```

**This is not a partition defect and not a moved race in any meaningful sense.** The partition table
stores line numbers derived at base `9c084c3`. Batch A's conversion (`f0660e3`, +92/−15 lines in that
file) pushed its own five races down. Every one was **found by name**; all 30 names resolve, 30
distinct, categories `{CLOCK-INJECTABLE: 26, ASYNCIO-SLEEP: 3, ALREADY-CONVERTED: 1}` correct, the
3 asyncio-sleep races confirmed by name, race #5 confirmed in the 26.

**Critically for this WO: all 13 batch-B identifiers land exactly at their stated lines (`OK`), as do
all of batch C and the excluded three.**

Two structural consequences the lead should note:

1. **The tool's PASS condition is unreachable from here on.** Its verdict requires
   `verified == len(rows) == 30` (`tools/wo029_reverify_partition.py:93-94`) — every race at its
   *original* line. Each batch that converts moves its own file's races, so **batch B will see 5 more
   MOVED, batch C 18 more.** The WO instructs batches to re-run this tool; it will fail for all of
   them. Either the table's line numbers must be refreshed at each close, or the verdict must key on
   name-resolution (which already works perfectly) rather than line identity.
2. **A FAIL run emits a self-contradictory line.** The trailing sentence is hardcoded regardless of
   verdict (`:95-96`), so the tool printed:
   `VERDICT: FAIL — the partition stands at this HEAD; batch A = test_live_capture.py races 1-5, and it converts WHOLE.`
   A reader skimming for the verdict gets "FAIL"; a reader reading the sentence gets reassurance. This
   is the `instrument-competence` decision-doc family.

**Corroboration that WO-029's "30/30" was never re-measured after its own conversion:** the committed
`evidence/WO-029/partition_reverified_at_head.txt` header reads **`RE-VERIFIED at HEAD (d0450fa)`** —
the §2.0-bis seam, *before* the batch-A conversion. The WO-029 batch-A report cites "30/30 identifiers
land at their stated file:line" for a HEAD at which that had ceased to be true. The claim was correct
when measured and was carried forward across a commit that invalidated it.

---

## Finding 4 — **DEFECT: the §1-mandated instrument writes into committed evidence** (WO-026 regression)

`tools/wo029_reverify_partition.py` line 32:

```python
OUT = os.path.join(REPO, "evidence", "WO-029", "partition_reverified_at_head.txt")
```

It `os.makedirs` + writes there unconditionally. **WO-031 §1 instructs re-running this tool.** Doing
so, as instructed, silently overwrote a **committed** evidence file:

```
$ git status --porcelain
 M evidence/WO-029/partition_reverified_at_head.txt
```

The overwrite rewrote WO-029's PASS record into a FAIL record (9 insertions / 9 deletions: the header
sha `d0450fa`→`3410435`, five `OK`→`MOVED`, `30/30`→`25/30`, `VERDICT: PASS`→`FAIL`).

**This is the exact defect class WO-026 §2 was created to eliminate** — quoting `conftest.py:89-95`:

> *"AN INSTRUMENT STREAMS TO AN IGNORED RUN-SCOPED PATH; EVIDENCE IS A DELIBERATE SNAPSHOT. The
> WO-024/025 defect: this hook wrote directly to a COMMITTED evidence path, so every pytest run
> silently overwrote committed evidence — found in a changed-files list, not by any guard."*

WO-026's fix was **scoped to the gate ledger only**. Its mechanical guard,
`_assert_ledger_dir_outside_evidence` (`conftest.py:100-112`), validates one hardcoded
`_LEDGER_OUTPUT_DIR` inside `conftest.py`. It does not — and structurally cannot — see a `tools/`
script. So WO-029, three WOs later, reintroduced the banned pattern in a new instrument, and no guard
fired. Same detection mode as the original: *found in a changed-files list.*

**Repair performed:** `git checkout -- evidence/WO-029/partition_reverified_at_head.txt`. Verified
restored — `git status --porcelain` now shows only ` M instructions.md` (the lead's own edit). The
committed evidence record is intact; nothing was committed.

**Note the scope trap.** WO-031 §0.2 says "No edits at all beyond the one committed evidence artifact
and a progress.md block," and §6 requires `git status --porcelain` to be clean. Obeying §1 literally
*violates* §0.2 and §6 — the WO cannot be executed as written without either dirtying committed
evidence or reverting afterwards. **Batches B and C hit this the moment they run §1.** The instrument
should write to `.artifacts/` with a deliberate snapshot step, matching the WO-026 pattern; and the
`evidence/`-write prohibition should be enforced somewhere `tools/` scripts are subject to it, not only
inside `conftest.py`.

---

## §5 — SCOPE FENCE: HELD

| Fence | Held? |
|---|---|
| Converts NO race | **HELD** — zero conversions |
| Threads NO seam | **HELD** |
| Edits NO test, NO src file | **HELD** — `git diff` over `src/` and `tests/` empty |
| Builds NO new fixture | **HELD** |
| Does NOT scope the keepalive seam WO | **HELD** — and could not; §4 not reached |
| Touches NONE of batch C, none of the 3 asyncio.sleep races | **HELD** |

**Five production sha256, unchanged and matching WO-029/WO-030 exactly:**

| File | sha256 (first 8) |
|---|---|
| `kraken_v2_book.py` | `b06c347e` |
| `factory.py` | `103a8ba7` |
| `registry.py` | `5bf833c7` |
| `live_capture.py` | `dab18f67` |
| `logkit/decision.py` | `3d153a11` |

---

## §6 — ACCEPTANCE (what a STOP can and cannot satisfy)

| Gate | Result |
|---|---|
| `pytest tests/ -p no:randomly -rX` → 218 both interpreters | **PASS** — 218/218 on 3.14.6 and 3.11.15, 0 f/xf/xp |
| `wo029_reverify_partition.py` → 30/30 | **FAIL — 25/30**, all 5 accounted for and none in batch B (Finding 3) |
| Every production AND test file sha256 unchanged; `git status --porcelain` pasted | **PASS after repair** — ` M instructions.md` only (the lead's own edit). One transient evidence overwrite caused by running §1's tool, reverted — Finding 4. |
| `lint-imports` 6/6 | **PASS** — 6 kept, 0 broken (63 files, 211 dependencies) |
| `contract_count_check.py` 6/6 | **PASS** — "import-linter evaluated 6 contracts (expected 6)" |
| `ruff` clean | **PASS** — "All checks passed!" |
| `annotation_name_scan.py` 0 | **PASS** — 0 names |
| `preflight_path_check.py` | **PASS** — `trading` resolves inside the repo tree |
| Classification committed as `evidence/WO-031/batch_b_clock_read_classification.md` | **NOT DONE** — §2 STOP; the classification does not exist |
| Append a WO-031 block to `progress.md` | **NOT DONE** — no commit on a STOP (WO-029 §2.0 precedent) |
| Commit, push, local == remote, CI green both legs | **NOT DONE** — nothing to commit |

---

## §Attempts — every one, including the failures

1. **Read `instructions.md` at the start of the session and found WO-029 batch A**, already complete
   and CI-green. Reported rather than re-executing committed work. The lead then replaced the file
   with WO-031 (verified: size 14142→9196 bytes, mtime 10:01→15:48, sha256
   `CB99A717…`). Re-read from disk before acting.
2. **Built the 3.11 acceptance interpreter first**, in the scratchpad
   (`uv venv --python 3.11`, then `uv pip install -r requirements.txt -r requirements-dev.txt`),
   because no 3.11 venv is checked in and every acceptance gate here is two-interpreter. Ready before
   the matrix started.
3. **Ran both suite legs concurrently in the background** (~245 s each) while doing the read-only §0.7
   and §2 verification, rather than serially. Checked first that concurrent runs cannot corrupt
   committed evidence: the gate ledger writes to git-ignored `.artifacts/gate_ledger/` under a
   `<utc-timestamp>-<sha>` run name (`conftest.py:96,115-125,203`). Only the convenience `latest.txt`
   is racy, and it is git-ignored.
4. **First §2 check was too narrow.** I initially searched the partition only for the literal string
   "D39" and found nothing, which is weak evidence — an amendment need not name its D-number. Widened
   to four independent checks (commit history, tree-vs-HEAD diff, the struck phrase's continued
   presence, and a repo-wide search for the amendment's own language including untracked files) before
   declaring the STOP.
5. **Suspected a D-number collision and was wrong.** `git grep D39` hit `evidence/WO-028/` and
   `WO-028-REPORT.md`, which looked like D39 already naming a different ruling — and WO-028's version
   was baked into a production message string. Checking `WO-030-REPORT.md:66-80` showed WO-030 had
   already superseded that placeholder with D38 and renamed the code; `git grep "D39" -- src/` returns
   nothing. **No collision. Recorded because the wrong version of this finding would have been a
   false STOP.**
6. **Running §1's re-verification tool dirtied committed evidence** — caught in `git status`, not by
   any guard. Diffed it to see exactly what was lost, restored with `git checkout`, re-verified the
   tree. Became Finding 4.
7. **Considered producing §3/§4 anyway** on the reasoning that a read-only classification harms
   nothing and would save the lead a round trip. **Rejected**: §2's STOP is pre-committed and §0.1
   forbids discretion, §3.1's criterion is defined by the very ruling that is missing, and a
   classification presented against an uncommitted amendment is the built-vs-operated failure D24
   names. The STOP is the deliverable.
8. **No production edit was attempted**, so the auto-mode classifier was never engaged.

---

## What unblocks this WO

Smallest path — the lead does one of:

1. **Commit the amendment** to `evidence/WO-029/batch_partition.md`: strike "terminate via scripted
   clean-close" from the batch-A entry and add the termination-branch requirement to the B/C entries;
   optionally write the D39 decision doc (`docs/decisions/`) for
   *"a conversion preserves the path, not just the assertions."* Then WO-031 re-runs from §1 and
   proceeds straight through §3/§4 — the §1 baseline in this report (218/218, batch-B membership,
   all 13 identifiers landing) is verified and reusable.
2. **Or rule that the amendment is unnecessary** and amend `instructions.md` §2 to drop the
   precondition — in which case §3/§4 can run immediately.

Independently of that choice, **Finding 4 should be fixed before batch B runs §1 again**, or batch B
will overwrite committed evidence exactly as this WO did.

**STOPPED. Nothing committed. Awaiting the lead.**
