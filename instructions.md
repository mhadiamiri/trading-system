# WO-037 — TAXONOMY MIGRATION: certify the reason-code vocabulary the corpus will archive.

BASE: current HEAD on master (WO-036 close) — confirm actual HEAD in §1.
222 both interpreters, CI green both legs (WO-036 run 30365970977).

SCOPE: §2 land two ruled closures (Option-4 disposition + precheck standing doc); §3 enumerate the
full reason-code vocabulary at HEAD; §4 the fix is WHATEVER §3 convicts — certify-if-clean or
repair-if-not. Commit green, STOP.
SHIP IMPACT: **conditional** — §3 is read-only; §4 touches `src/` ONLY if the enumeration convicts a
live defect. If §4 touches production, full discipline. Declared per outcome in §4.

WHY THIS IS CORPUS-BLOCKING (D42): the corpus ARCHIVES decision records carrying reason codes. If the
vocabulary is defective at capture — a code emitted-but-undeclared, declared-but-unproducible, or a
category leak — the archive preserves the defect permanently and every analysis built on the corpus
inherits it. The vocabulary-SPLIT audit (namespace hygiene) is post-corpus per D42; THIS WO is the
narrower corpus-blocking part: the archived vocabulary must be COMPLETE and CONSISTENT, verified
mechanically, before capture. This WO does NOT do the split; it certifies archive-readiness.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report.
0.2 No monkeypatching to make a guard pass.
0.3 Every guard built/touched gets a fail-then-pass bite proof: four artifacts, sha256 exact-restore.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 **D42 STANDING ARTIFACT-RULING CHECK:** §1 confirms every artifact this WO reads reflects all
    rulings since it was written. Two rulings are pending-on-tree — §2 lands them.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | `logkit/decision.py` `VALID_REASON_CODES` | **OPERATED** | pre-existing; WO-028/030 added the load-time code |
    | `test_reason_code_vocabulary.py` completeness guard | **OPERATED** | pre-existing (emitted⇒declared, declared⇒producible) |
    | Option-4 pass-two disposition | **RULED, NOT YET ON TREE** | §2.1 lands it |
    | Red-line precheck standing form | **RULED, NOT YET ON TREE** | §2.2 lands it |
    | The archive-readiness certification of the vocabulary | **THIS WO IS THE BUILDER** | §3/§4 |

    Any OPERATED row not verified → STOP.

---

## §1 CONFIRM HEAD, SUITE, ARTIFACT-CURRENCY
State actual HEAD. `pytest tests/ -p no:randomly -rX` both interpreters → confirm 222.
`wo029_reverify_partition.py` → PASS 31/31, `.artifacts/`, clean after. D42 currency check on
`batch_partition.md` and `audit_node_ids.md`: current per WO-035. Note the two pending-on-tree rulings
(§2) as the currency gap this WO closes.

---

## §2 LAND THE TWO RULED CLOSURES (before §3; own commit)

2.1 **Option-4 pass-two disposition.** Record in `batch_partition.md` (dated amendment) and a decision
    doc `docs/decisions/2026-07-28-races-6-15-16-not-clock-convertible.md`:
    - Races 6, 15, 16 are DECLARED NOT-CLOCK-CONVERTIBLE — same disposition as the 3 asyncio.sleep
      races — because their outcome-bearing read `last_frame` is the corpus's gap `open_monotonic`
      bound (WO-036 §1), and threading it would put fake-clock reach into corpus-integrity machinery.
    - **Pass two CLOSED: 24 converted + 3 keepalive-blocked (6/15/16) + 3 asyncio.sleep, denominator
      30.** Every disposition named.
    - The rationale VERBATIM as ruled: *making three test conversions deterministic is not worth any
      change to how the corpus records gap windows; options that inject fake time into open_monotonic
      are not a cost-benefit calculation but the red line doing what red lines do.* Note option 3's
      additional defect (decoupling what :2667 made identical — the gap opens when emission stopped,
      not when the threshold tripped).
    - Records that 6/15/16 stay on the flake-doctrine diagnose-before-rerun discipline (the interim
      mitigation for residue structural fixes shouldn't chase).

2.2 **Red-line precheck standing form.** Decision doc
    `docs/decisions/2026-07-28-outcome-bearing-for-whom-consumed-by-what.md`:
    - The call-graph doctrine's final form: a variable can be outcome-bearing for a TEST and
      simultaneously carry unrelated PRODUCTION consumers; the classification that convicts a read for
      a test says nothing about what threading it does to the corpus.
    - WO-031 §4 made NO error — it answered "outcome-bearing for whom." The precheck asked "consumed by
      what." **Both questions are now standing form for any seam threading.** Specimen: `last_frame`,
      outcome-bearing for races 6/15/16, consumed by three gap causes + the throughput instrument.
    - Note the meta-point: this validated the D42 mode on its first firing — standing Ops authority,
      bounded by red lines, and the precheck fired exactly at the (d) boundary, nothing threaded.

---

## §3 ENUMERATE THE FULL REASON-CODE VOCABULARY AT HEAD (read-only; the gate that scopes §4)

Do NOT assume the vocabulary is clean OR broken. Enumerate and classify:

3.1 **The declared set:** every code in `VALID_REASON_CODES` (and any sibling registry). List them.
3.2 **The emitted set:** every uppercase-colon reason string the completeness guard scans as emitted,
    across `src/`. List them with call sites.
3.3 **The four consistency properties, each MEASURED not assumed:**
    - (a) EMITTED ⇒ DECLARED: every emitted code is in the declared set. Name any violation.
    - (b) DECLARED ⇒ PRODUCIBLE: every declared code has a reachable emission path (or is a documented
      load-time/registration code — see (d)). Name any declared code with NO producer.
    - (c) NO DUPLICATE/ALIASED codes (two spellings, one meaning). Name any.
    - (d) CATEGORY: which codes are RUNTIME DECISION reasons (appear in a decision log the corpus
      archives) vs LOAD-TIME/REGISTRATION codes (raised before any decision loop, CANNOT appear in a
      decision log — e.g. `LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM`). This is the leak the
      post-corpus SPLIT audit will home; THIS WO only needs to CATALOG it, because the archive-
      readiness question is "are the RUNTIME codes complete and consistent," and a load-time code
      mixed into the scanned set could mask a real runtime gap. State whether any load-time code's
      presence affects the (a)/(b) verdicts.
3.4 **The archive-readiness question, answered explicitly:** is the set of codes that CAN appear in a
    corpus-archived decision log complete (every producible runtime code declared) and consistent (no
    emitted-undeclared, no aliases)? YES → §4 is certify-only. NO → §4 repairs exactly what's convicted.

Commit the enumeration as `evidence/WO-037/reason_code_vocabulary_audit.md`.

---

## §4 THE FIX — SCOPED TO WHAT §3 CONVICTS

**If §3.4 is YES (archive-ready):** this is a CERTIFY-ONLY WO. Add a mechanical
archive-readiness guard (if one does not already exist) that asserts (a)+(c) for the RUNTIME code set
specifically — so a future emitted-undeclared runtime code fails CI before it can reach a corpus.
Bite proof: introduce a throwaway emitted-undeclared runtime code → guard fails; declare it → passes;
restore, sha256. NO `src/` production change; SHIP IMPACT NO.

**If §3.4 is NO (a live defect):** repair EXACTLY the convicted defect and nothing more. State the
defect, the minimal fix, and the production files touched with before/after sha256. Full discipline;
SHIP IMPACT YES. Do NOT do the category SPLIT (post-corpus) — repair only what makes the RUNTIME
vocabulary complete+consistent for archive. If the only defect is a category leak with no runtime
completeness/consistency violation, that is a SPLIT-audit item (post-corpus) — record it and certify
runtime-readiness without touching it. STOP and report if unsure which bucket a defect falls in.

Either way: the load-time code(s) get a documented marker distinguishing them from runtime codes in
the scanned set, so archive-readiness is checkable without the split (the split re-homes them; this
just labels them). State whether this marker is new or exists.

---

## §5 SCOPE FENCE
- NO vocabulary SPLIT / re-homing / re-prefixing (post-corpus, D42/D37). Catalog and label only.
- NO gate docstring precision note (r20 ruling 2 — rides with the post-corpus split WO).
- NO pass-two race touched (pass two is CLOSED by §2.1).
- NO production change unless §3 convicts a runtime completeness/consistency defect.

---

## §6 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → 222 (+ any guard test §4 adds — state arithmetic), both
  interpreters, 0 f/xf/xp
- `pytest --randomly-seed=<seed>` → same
- Archive-readiness verdict stated (YES certify / NO repair) with the §3 enumeration as evidence
- IF §4 built a guard: bite proof four artifacts, sha256 exact-restore
- IF §4 touched src: touched files' before/after sha256 + diff; untouched five identical. IF NOT:
  `git diff -- src/` empty, five sha256 identical (`b06c347e…`,`103a8ba7…`,`5bf833c7…`,`dab18f67…`,`3d153a11…`)
- `wo029_reverify_partition.py` PASS 31/31
- lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass
- §2's two decision docs + `batch_partition.md` Option-4 amendment committed (own commit, before §3/§4)
- Commit, push, local == remote, CI green both legs (REAL run number)
- `evidence/WO-037/` enumeration committed; progress.md WO-037 block noting PASS TWO CLOSED 24+3+3/30

## §7 REPORT — `WO-037-REPORT.md`
The §2 closures as committed (Option-4 disposition, precheck doc); the full §3 vocabulary enumeration
with the four properties measured and the archive-readiness verdict; the §4 outcome (certify or
repair) with its evidence; the load-time-code labeling; the src sha256 disposition; every attempt; any
STOP; CI run number, real.

**THEN STOP.** Next (corpus-blocking, per-item reporting resumes as we near preconditions):
capture-loop baseline → corpus preconditions → 24h corpus.