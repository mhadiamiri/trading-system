# WORK ORDER — WO-014c-2: Gap Recording (Schema + Taxonomy) + Failure-Targeted Capture

**Status:** ACTIVE. Fresh session. WO-014c-1 COMPLETE at `f74459f`.
**READ FIRST:** `evidence/WO-014b-2/gap_attachment_points.txt` (emission sites, in-scope
fields, and the note that `capture_terminated` at line 1203 is the richest
already-assembled site), then `evidence/WO-014c-1/thresholds_and_branches.txt`.
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.
**Baseline:** `f74459f` — 158 passed deterministic AND randomized (seed 20260725),
0 failed / 0 xfailed / 0 xpassed. import-linter 6/6, contract 6/6, ruff clean.
**NO VENUE CONNECTION.** Simulated transport only. HTTPS doc fetching permitted.

═══════════════════════════════════════════════════════════════
STANDING RULES — permanent
═══════════════════════════════════════════════════════════════
- **0.1** Unspecified → STOP and ask.
- **0.1a** Public interface signature changes, `object.__setattr__`, `# type: ignore`,
  monkey-patching, or any constraint-bypass mechanism → STOP and ask.
- **0.1b** No enforcement-class test may be `xfail`/`skip`/excluded without escalation.
- **0.1c** No `Mock`, stub, fake, or test double in production code paths.
- **0.1d** An enforcement test whose trigger cannot occur is a false guarantee; a
  regression sentinel is legitimate but must be LABELLED.
- **0.1e** Claims about protocols, APIs, venue OR LIBRARY behavior CITE DOCUMENTATION at
  the point of claim. Docs/RFC are THE CLAIM; source inspection is CORROBORATION only.
- **0.1f** Source inspection may SUPPLEMENT a behavioral guarantee; never CONSTITUTE one.
- **0.1g** A stub or unimplemented production path MUST FAIL LOUDLY.
- **0.1h** Bite proofs exercise the PRODUCTION TRIGGER PATH.
- **0.1i** A PROOF OF ESCALATION MUST TERMINATE IN AN OBSERVABLE EFFECT.
- **0.2 / 0.2a** Blockers escalate. Cannot reach gate state → STOP BEFORE PUSH.
- **0.4** Never weaken a guard, invariant, assertion, or threshold.
- **0.5** Never print `.env` or any credential.
- **0.6a–d** Evidence is redirected output; bite proofs carry the summary line WITH
  DURATION; preflight per 0.6c; fabricated evidence invalidates the WO.
- **0.7** Bite proofs EXECUTED: PASS, ACTUAL FAIL with real assertion text, PASS after
  restore, **`sha256` exact-restore**.
- **0.8** Do not tune to green.
- **0.9** "I could not complete X" is a successful outcome. Checkpoint rather than
  half-implement — correct nine times running. **Named seam: after §1 (schema declared
  and committed), before §2.**

## WHY THIS EXISTS

Two ruled deliverables, both of which are **impossible retroactively**:

**Gap recording.** ~116 reconnects/24h was measured with no working keepalive and should
now drop — but every reconnect is still a book discard, resubscribe, resnapshot. STOP
prevents one undisclosed multi-hour hole; it does nothing about many disclosed-to-nobody
multi-second ones. Ruled: *"a gap not recorded when it happens cannot be reconstructed
later."*

**Failure-targeted capture.** WO-008b-B's 3 checksum failures (3 of 14,251 = 0.021%) were
lost to positional sampling. After A3's 1254/1254, **that rate is UNDIAGNOSED and NOT
PRESUMED BENIGN.** By ruling: **no corpus can be blessed until a run's capture shows
whether these are wire-level anomalies or our residual parse/apply bug.**

**SCHEMA-FIRST IS THE RULING.** Specify the schema before either side is built —
otherwise the reader inherits whatever the capture happened to write, which is
fixtures-shaped-to-the-implementation one layer up. Same defect class as `research.md:23`,
at a different altitude.

## OUT OF SCOPE
- The corpus READER and its default-deny acknowledgment API — the corpus WO.
- Stub-lint and the widened precondition sweep (014c-3).
- The 60-minute re-run. **NO VENUE CONNECTION.**

## §1 — DECLARE THE GAP SCHEMA AND CAUSE TAXONOMY (no code; commit before §2)

### 1.1 Cause taxonomy — ruled set, exhaustive
`KEEPALIVE_RECONNECT`, `CHECKSUM_RESYNC`, `BREAKER_RETRY_LADDER`, `VENUE_DISCONNECT`.
- Map each to the **exact emission site** already identified in
  `gap_attachment_points.txt`.
- If a gap-producing path exists that fits none of these, **STOP AND REPORT** — do not
  invent a fifth cause. The taxonomy is ruled.
- State whether `capture_terminated` (the richest assembled site) is a distinct cause or
  an instance of `BREAKER_RETRY_LADDER`, with reasoning.

### 1.2 Schema — shaped against real emission sites
Per record, at minimum: **bounding timestamps** (`time.monotonic()`, the shared clock
from 014c-1 — plus a wall-clock anchor recorded ONCE per run so gaps are locatable in
calendar time without correlating across mixed bases), **cause**, **duration**, **last
validated book state**, and whether emission resumed.

Shape it against `capture_terminated`'s already-assembled fields rather than inventing a
schema and retrofitting.

### 1.3 The schema must make CONTINUITY CHECKABLE
The corpus reader is default-deny: it cannot emit a window spanning a gap without
explicit acknowledgment. That is only implementable if the schema lets a reader answer
*"does the interval [t0, t1] intersect any recorded gap?"* cheaply and totally.
- State how the schema supports that query.
- **Do NOT build the reader.** Specify what it will need.

Evidence → `evidence/WO-014c-2/gap_schema.txt`
**Commit and push §1 standalone before §2.** It is the declarative record two work orders
depend on, and it should exist independently of the capture code.

## §2 — IMPLEMENT GAP RECORDING

Emit a record at every site in the taxonomy.
- **Every gap-producing path emits, or the path is reported as unable to** — a silently
  unrecorded gap is the failure this WO exists to prevent.
- **Bite proof per cause, four artifacts each**, `sha256`, terminating in the observable
  effect (0.1i): drive the real production trigger, observe the record written with all
  schema fields populated. **Do not hand-feed** (0.1h).
- **Completeness accounting**, consistent with 014c-1's instruments: the gap ledger
  reports its own integrity — if a gap was detected but its record could not be completed,
  that is stated, not dropped.
- Declare any new reason code in the same commit.

## §3 — FAILURE-TARGETED CHECKSUM CAPTURE

On **every** checksum failure, persist:
- the **raw wire text** of the failing frame, verbatim
- the **local book state** at failure — both ladders, at subscribed depth
- **expected** (Kraken's) and **computed** checksums
- the **preceding N frames** for reconstruction — **state and justify N**
- UTC timestamp **and** monotonic timestamp, plus sequence position in the run

Redact via the mechanical redaction module.
**Bite proof:** inject a synthetic checksum failure through the production path and show
the full artifact written with every field. Four artifacts, `sha256`.

**Do not sample positionally.** Positional sampling is precisely what lost the three
failures we now need.

## §4 — VERIFY, COMMIT, PUSH
    pytest tests/ -p no:randomly -rX
    pytest tests/ --randomly-seed=<state it> -rX
    lint-imports
    python tools/contract_count_check.py
    ruff check .
0 failed / 0 xfailed / 0 xpassed BOTH orders. Explain every delta against `f74459f`.
Per 0.2a stop before push if you cannot reach it. Secret scan, push, paste HEADs.

## §5 — FINAL REPORT — then STOP
1. **Taxonomy** — all four causes mapped to emission sites. Any path fitting none? Is
   `capture_terminated` distinct or an instance?
2. **Schema** — paste it. Confirm the monotonic clock plus the once-per-run wall anchor.
   How does it support the reader's interval-intersection query?
3. **Gap recording** — bite proof per cause, four artifacts each, exercising the
   production trigger.
4. **Ledger completeness** — can it report a gap whose record could not be completed?
5. **Failure capture** — paste a synthetic failure artifact showing every field. What N,
   and why?
6. Reason codes declared in the same commit?
7. Verification: both runs with seeds and durations, deltas, linter, contract count,
   ruff, local/remote HEAD.
8. **Venue connection?** YES/NO. **HTTPS doc fetch?** YES/NO.
9. **Prose standing in for output?** YES/NO.
10. **Changed but not asked?** Every file, or "none."
11. **What could not be completed, and why?**

STOP for review. Do NOT proceed to 014c-3 or the re-run.