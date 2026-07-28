# WO-031 (reissued) — PASS TWO, BATCH B CLASSIFICATION + one suspect BOUND re-audit. CLASSIFY ONLY.

BASE: current HEAD on master (WO-032 close, `1b52c53`) — confirm actual HEAD in §1 and use it.
222 both interpreters (218 + WO-032's 4 guard tests), CI green both legs (run from WO-032 §CI).

SCOPE: **CLASSIFY AND STOP.** Converts NOTHING, threads NO seam, edits NO test/src. Produces (1) the
batch-B per-race clock-read classification, and (2) a re-audit of ONE audit BOUND that WO-032 flagged
as behaving like a race. Two committed evidence artifacts + a progress.md block. Nothing else.
SHIP IMPACT: **NO.** Every production and test file byte-unchanged; §6 proves it with the five sha256s.

WHAT CHANGED SINCE WO-031's FIRST ISSUE:
- WO-032 committed the D39 partition amendment and the D39 decision docs, and fixed the reverify tool
  (name-keyed, writes to `.artifacts/`). WO-031's §2 STOP precondition is now SATISFIED — the amended
  `batch_partition.md` exists on the tree. Confirm it (§2) and proceed.
- WO-032's CI leg surfaced a finding (§3-bis below): an audit BOUND behaves like a clock race.

WHAT D39 RULED (the operative METHOD, now committed as
`docs/decisions/2026-07-27-a-residual-clock-read-is-classified-not-waived.md`): for each race,
enumerate every real-clock read on its path; classify OUTCOME-BEARING (an assertion depends on it) vs
INCIDENTAL (interval read, no assertion, harmless under the ms-compressed run); convert only if all
incidental; any outcome-bearing read on a NON-INJECTABLE seam is a PRE-COMMITTED STOP and escalation.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report. A STOP is an EXPECTED OUTCOME here
    (an outcome-bearing non-injectable read, or a reclassified bound) — not a failure.
0.2 No conversions, no seam threading, no test/src edits. Two evidence artifacts + progress.md only.
    If you find yourself editing a test or src file, you have exceeded scope — STOP.
0.3/0.4 No guards built; no bite proof owed. Any classification instrument you write is a re-runnable
    tool that writes to `.artifacts/` (the WO-032 boundary — a tools/ script writing under evidence/
    now FAILS `tests/test_evidence_write_boundary.py`).
0.5 Report every attempt.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | Amended `batch_partition.md` (D39 B/C plan) | **OPERATED** | WO-032 §2 — CONFIRM at §2 before using |
    | D39 method decision doc | **OPERATED** | WO-032 §3 |
    | `wo029_reverify_partition.py` name-keyed, `.artifacts/`-writing | **OPERATED** | WO-032 §1/§4 |
    | WO-023 §1 audit: 30 races + 7 BOUNDS (entries 31–37) | **OPERATED** | `86e2a33` |
    | The batch-B classification + the bound re-audit | **THIS WO IS THE BUILDER** | Does not exist — §3, §3-bis |

    Any OPERATED row not verified → STOP. In particular §2: if the amended partition is NOT on the
    tree, STOP (do not re-run the WO-031-first STOP loop — report that WO-032 §2 did not land).

---

## §1 CONFIRM HEAD, SUITE, PARTITION INTEGRITY
State actual HEAD. `pytest tests/ -p no:randomly -rX` both interpreters → confirm **222**. Run the
FIXED `wo029_reverify_partition.py` → confirm **PASS, 30/30 by name**, writing to `.artifacts/` (a
`git status` after the run must be clean — that is the WO-032 fix; if it dirties evidence/, WO-032 §4
regressed, STOP). State batch B membership from the committed amended partition (13 races across
`test_gap_recording.py`, `test_keepalive.py`, `test_failure_cap.py`, `test_failure_capture.py`).

## §2 CONFIRM THE AMENDED B/C PLAN IS ON THE TREE (the WO-031-first STOP is now cleared)
Confirm `batch_partition.md` contains the D39 amendment WO-032 §2 committed: the "scripted clean-close"
phrase STRUCK from batch A, and the termination-branch requirement ADDED to B and C. If present,
proceed. If absent, STOP — WO-032 §2 did not land and this WO cannot plan against an unamended file.

---

## §3 BATCH-B CLASSIFICATION — per race, every real-clock read (the D39 method)

For each of the 13 batch-B races:
3.1 **Termination branch** the test exercises (deadline / venue-close / failure-cap / breaker / other),
    named from the code. This is the branch a later conversion must KEEP (the D39 acceptance tightening).
3.2 **Every real-clock read on the race's path** — call site (file:line), which clock, INJECTABLE
    (deadline/suspend post-WO-030) or NON-INJECTABLE (keepalive pacing, ping interval, ledger anchor,
    last_frame, throughput/lag/pong instruments, others).
3.3 **Classify each read OUTCOME-BEARING or INCIDENTAL**, with the naming evidence: for each
    outcome-bearing read, the assertion that depends on it; for each incidental, the explicit statement
    that no assertion references it. (The batch-A standard: this is what made the reading a method, not
    a waiver.)
3.4 **Per-race verdict:** ALL INCIDENTAL → CONVERTIBLE (note deadline-path vs own-branch, and flag any
    non-deadline branch needing a fixture that does not yet exist — flag, do not build). ANY
    outcome-bearing on a NON-INJECTABLE read → NOT-YET-CONVERTIBLE, name the exact read(s) to thread.

## §4 THE OUTCOME-BEARING SET — the measurement that sizes the keepalive seam WO (D39 (a))
Aggregate: the set of NON-INJECTABLE reads outcome-bearing for ≥1 batch-B race (this and NOTHING more
is what the keepalive seam WO threads — seam-sized-to-measurement); which races convict each, on which
assertion; and the set incidental everywhere (stays UNTHREADED by design, recorded). State counts: N
convertible now, M not-yet-convertible with reads named. **Fork:** if the outcome-bearing set is the
expected keepalive/ping-pacing shape → Ops scopes the seam WO on existing d39. If it SURPRISES (large,
or touches the throughput/lag/pong INSTRUMENTS not just pacing) → STOP, the count returns to the lead
before any seam WO.

---

## §3-bis RE-AUDIT ONE SUSPECT BOUND (WO-032's CI finding) — CLASSIFY, do not reclassify unilaterally

WO-032's CI leg observed that `test_incremental_persist_survives_unhandled_exception_mid_capture` —
filed by the WO-023 audit as one of the **7 legitimate BOUNDS (entries 31–37), NOT a race** — flinches
on clock rate: at the pre-WO-032 baseline, `AdvancingClock(delta=0.2)` yields no exception,
`delta=0.0001` raises. That is the signature of an outcome-bearing clock dependency, i.e. a race.

**Run the D39 method on this ONE test** exactly as §3.1–3.4 — do NOT reclassify from the symptom alone.
The D39 doc you are operating under says the category comes from the CLASSIFICATION (enumerate reads,
name the assertion), not from a differential observation. So:
- 3.1 its termination branch; 3.2 every real-clock read on its path; 3.3 classify each with the naming
  evidence — specifically, WHICH read the delta=0.2-vs-0.0001 outcome divergence flows from, and WHICH
  assertion observes it; 3.4 verdict.
- Then state the CATEGORY consequence explicitly:
  (a) OUTCOME-BEARING clock read that an assertion rests on → it is a RACE the audit misfiled as a
      BOUND. The clock-injectable denominator becomes 27 (or it is NOT-YET-CONVERTIBLE if the read is
      non-injectable — say which). This is a DENOMINATOR CHANGE → the reclassification ESCALATES to the
      lead; you REPORT it, you do not fold it into a batch.
  (b) the divergence flows from something that is genuinely a BOUND (a timeout the test legitimately
      brackets, no assertion resting on the injected rate) → the audit was right, the symptom is
      benign, record why and leave the category.
- This test is a BATCH C file member's neighbour but is itself a BOUND, not in any batch. **Do not
  convert it, do not touch batch C.** This is a classification-only re-audit.

Record whether the OTHER 6 bounds (entries 31–37) warrant the same re-audit — enumerate them by name
and state, from the audit's own text, whether any shares this one's shape (an injected-clock-rate
dependence). If any does, flag it for its own probe; do not probe them all here unless the shape is
obviously shared. (Enumerate-then-scope, not probe-everything.)

---

## §5 SCOPE FENCE
Converts NO race. Threads NO seam. Edits NO test/src/fixture. Scopes NO downstream WO (produces the
measurements that size them). Touches NO batch C race, NONE of the 3 asyncio.sleep races. Does NOT
reclassify the bound unilaterally — reports the classification and escalates a denominator change.

## §6 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → 222 both interpreters (unchanged — edits no test)
- `wo029_reverify_partition.py` → PASS 30/30 by name, writes `.artifacts/`, `git status` clean after
- `git status --porcelain` shows only the two evidence artifacts + progress.md + instructions.md
- Five src sha256 IDENTICAL (`b06c347e…`,`103a8ba7…`,`5bf833c7…`,`dab18f67…`,`3d153a11…`);
  `git diff -- src/` empty
- `test_evidence_write_boundary.py` PASSES (any classification tool you wrote writes to `.artifacts/`)
- lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass
- `evidence/WO-031/batch_b_clock_read_classification.md` and
  `evidence/WO-031/bound_reaudit_incremental_persist.md` committed
- progress.md WO-031 block appended; commit, push, local == remote, CI green both legs (REAL run
  number — not a placeholder; WO-028 and WO-032 both shipped `<fill>` first)

## §7 REPORT — `WO-031-BATCH-B-CLASSIFICATION-REPORT.md` (overwrite the prior STOP report; note it
supersedes the STOP)
Per-race batch-B classification (branch, read enumeration, outcome/incidental with naming, verdict);
the §4 aggregate (outcome-bearing set, incidental-everywhere set, N/M counts, which fork obtains); the
§3-bis bound re-audit with its category verdict and denominator consequence; the 6-other-bounds
enumeration and whether any needs its own probe; the five unchanged sha256; every attempt; any STOP.

**THEN STOP.** If §4 convicts keepalive-shaped reads → keepalive seam WO next (sized to §4). If §3-bis
reclassifies the bound → the reclassification escalates before it joins any batch. Otherwise batches
B/C convert under the amended partition.