# WORK ORDER — WO-009b: Complete the FR-018a Amendment Across Sibling Artifacts

**Status:** ACTIVE. WO-008b-A remains HELD.
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.
**Baseline:** `03b7460` — 81 collected, 73 passed, 8 xfailed, 0 failed, 0 xpassed.
import-linter 5 kept / 1 broken (mock rule, expected red). Contract count 6/6.
**Standing rules 0.1–0.9 apply in full, unchanged.**

## WHY THIS EXISTS
WO-009 amended `spec.md` correctly, but Ops scoped §1 to that file alone. Six
sibling artifacts still mandate sequence tracking — the "half-amended spec is its
own fictional reality" condition §1.3 exists to detect. Refusing to expand scope
and escalating was correct. This completes the amendment.

Scope error was Ops's, for the third time: scoping to the file in mind rather
than the change's actual footprint.

## 1. AMEND THE SIX SIBLINGS

Bring each into agreement with the amended FR-018a (CRC32 sole mechanism,
post-update ordering, every-update validation, no-emission window, depth 10):

- **`research.md:23`** — "v2 provides snapshot/sequence numbers for gap
  detection." This is FACTUALLY UNTRUE of the public book channel and is the
  ORIGIN of the entire defect class. Correct it, and add an inline note recording
  that it was the origin — do NOT silently fix it. Cite Kraken's docs.
- **`data-model.md`** — remove `LocalBookState.last_sequence` and
  `QuoteUpdate.sequence`; replace the state-machine edge
  `SYNCHRONIZED --sequence_gap_detected--> RESYNC_REQUIRED` with a
  checksum-divergence edge matching the amended recovery semantics, including the
  no-emission window.
- **`plan.md`**, **`quickstart.md` (Scenario 4)**, **`tasks.md` (T008/T011/T015/T018)**
  — bring into agreement.
- **`contracts/data-adapter.yml`** — see §2, handle separately.

Preserve superseded text by strike-through rather than deletion, per WO-009's
established pattern. History is annotated, not laundered.

## 2. THE CONTRACT CHANGE — flag prominently for ratification

`contracts/data-adapter.yml` defines `class SequenceGapError` and reason code
`SEQUENCE_GAP_RESNAPSHOT` — an error type and reason code for an event that
CANNOT OCCUR on this channel (rule 0.1d: a false guarantee).

Ops reads their removal as a direct consequence of the ruled amendment rather
than a new decision, so proceed. BUT this touches the adapter contract surface,
which rule 0.1a treats as interface. Therefore:
- Make the change.
- Report it SEPARATELY and PROMINENTLY in the final report as an interface change
  requiring project-lead ratification, with before/after pasted.
- If the project lead vetoes, it reverts. Do not bury it in a file list.
- State what replaces them: is there a checksum-divergence error type and reason
  code, and does it follow the existing reason-code convention? If none exists,
  say so — creating one may belong to WO-008b-A.

## 3. FIX THE F811 DUPLICATE
`tests/test_boundaries.py` — `import importlib` appears twice. F811 flagged it
legitimately. Fix it now (it is a genuine defect the new rule caught, and rule
0.8's "don't tune to green" does not apply to fixing a real duplicate the rule
correctly identified). Paste F811 clean afterward.

## 4. DETAIL THE FIVE BLOCKING DEFECTS
`tests_requiring_rewire.txt` mentions "5 implementation defects that block the
rewire" without enumerating them here. List each: what it is, which file and line,
and why it blocks. These scope WO-008b-A, so I need them explicit.
Evidence → `evidence/WO-009b/blocking_defects.txt`

## 5. DECISION LOG — one entry
"A single false sentence in `research.md:23` — 'v2 provides sequence numbers for
gap detection' — propagated into a spec requirement, a data model, a contract
error class, a task list, and a fixture, and from there into six work orders of
'proven' claims. Research artifacts are load-bearing: an unverified factual claim
about an external protocol is a defect at the same severity as a code defect.
Standing consequence: protocol claims in research artifacts must cite vendor
documentation."

## 6. VERIFY, COMMIT, PUSH
Preflight gate per rule 0.6c (status classified, worktree list showing only main,
package path inside repo, baseline stated against `03b7460`).
    pytest tests/ -rX
    import-linter lint
    python tools/contract_count_check.py
    ruff check .
Required: baseline unchanged (81/73/8); import-linter 5 kept / 1 broken (expected);
contract count 6/6; F811 clean. Secret scan, push, paste local vs remote HEAD.

## 7. FINAL REPORT — then STOP
1. Paste each amended sibling's changed section. Confirm all six agree with
   FR-018a.
2. **§2 CONTRACT CHANGE — paste before/after prominently.** What replaces
   `SequenceGapError` / `SEQUENCE_GAP_RESNAPSHOT`, if anything?
3. Paste the `research.md:23` correction with its origin note.
4. Paste F811 clean after fixing the duplicate.
5. **Enumerate the five blocking implementation defects** — file, line, why blocking.
6. Paste the decision log entry.
7. Paste §6 verification, all four commands, plus local/remote HEAD.
8. **Any residual sequence references anywhere in `specs/002-quote-level-data/`?**
   Paste the grep. YES/NO.
9. **Is any file in `evidence/WO-009b/` prose standing in for output?** YES/NO.
10. **What did you change that you were not asked to change?** Every file, or "none."
11. **What could not be completed, and why?**

Do NOT implement the WebSocket. Mock(), FR-017, venue-mode observability, and the
mainnet-guard test remain WO-008b-A. STOP for human review.

--------------------------------------------------------------------------

ADDENDUM TO WO-009b — §2 completeness check (project lead ruling)

Veto DECLINED — the SequenceGapError / SEQUENCE_GAP_RESNAPSHOT removal is
ratified. Proceed as written, plus this:

A contract purge that leaves consumers referencing the purged vocabulary just
relocates the fiction. Before declaring §2 done, grep the FULL tree for both
identifiers and report every hit:

    grep -rn "SequenceGapError\|SEQUENCE_GAP_RESNAPSHOT" . \
        > evidence/WO-009b/purge_completeness.txt 2>&1
    cat evidence/WO-009b/purge_completeness.txt

Cover specifically: reason-code enums, log-parsing helpers, docs, and any test
asserting the code's EXISTENCE (a test asserting a dead reason code exists is
rule 0.1d again). Report each hit and its disposition, or confirm zero remain.

ALSO — new standing rule, add to the boilerplate for all future work orders:

**0.1e RESEARCH ARTIFACTS ARE LOAD-BEARING.** Any claim about an external
protocol, API, or venue behavior must cite the vendor's documentation at the
point of claim. Uncited protocol claims may not flow into requirements.
`/speckit-analyze` should treat an uncited protocol claim in a spec as a blocking
finding, same class as a principle violation.

Apply 0.1e while amending research.md in §1: every protocol claim you touch gets
a citation, not just the one you're correcting.