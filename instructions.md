# WO-035 — Land the D42 artifact amendments, then CONVERT batch C's 9 races. One session.

BASE: current HEAD on master (WO-034 §2.2 STOP close, `e12d6d2`) — confirm actual HEAD in §1.
222 both interpreters, CI green both legs (run 30358810306).

SCOPE: §2 land three ratified artifact amendments (mechanical); §3 convert batch C's 9 races against
node-ID identifiers; §4 determinism + ledger bite. Commit green, STOP. Batch C is the LAST conversion
batch — after it, 24 of 27 clock-injectable races are done (batch B's 3 await the keepalive seam WO).
SHIP IMPACT: **NO** — tests, conftest, evidence, docs. Every `src/` file byte-unchanged; §6 proves it.

DENOMINATOR (settled all-measured, D40+D41): clock-injectable 27, bounds 6, total 30. Batch C = 9.

WHAT D42 RATIFIED that this WO executes:
- The 9-mismatch identifier finding; `evidence/WO-034/audit_node_ids.md` is CANONICAL (committed,
  37/37 resolve). Prose identifiers superseded; historical audit annotated, not rewritten.
- Both `batch_partition.md` amendments: fold entry 35 (batch C 8→9); restate race identifiers as
  node IDs.
- **Standing step (now doctrine):** every WO's §1 confirms the artifact it reads reflects all rulings
  since it was written. Applied here and added to the template.
- Log entry (adopted verbatim): *a regeneration must read the original, not a restatement of it;
  before trusting a diff, confirm both sides derive from the source, not from each other's corrections.*

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report.
0.2 No monkeypatching to make a guard pass; migrate transport to the seam where a clock is injected.
0.3 Every guard/assertion touched gets a fail-then-pass bite proof: four artifacts, sha256 exact-restore.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 **STANDING ARTIFACT-RULING CHECK (D42):** §1 confirms every artifact this WO reads reflects all
    rulings since it was written. If any lag is found, land the amendment before proceeding (this WO's
    §2 IS that landing for the partition).
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | `audit_node_ids.md` canonical identifier set | **OPERATED** | WO-034 §2, committed, ratified D42 |
    | Measured denominator 27/6/30, batch C = 9 | **OPERATED** | D40+D41+D42 |
    | `AdvancingClock` + coherent FakeClock harness | **OPERATED** | WO-029 §2.0-bis / WO-023 §3 |
    | Clock + transport seams (runner/factory/builder) | **OPERATED** | WO-028 / WO-030 |
    | Gate ledger + marker + `.artifacts/` boundary guard | **OPERATED** | WO-024/025/026/032 |
    | Batch C's 9 conversions incl. entry 35 | **THIS WO CONVERTS** | §3 |
    | Partition amendments (8→9, node-ID identifiers) | **THIS WO LANDS** | §2 |

---

## §1 CONFIRM HEAD, SUITE, MEMBERSHIP, ARTIFACT-CURRENCY (D42 standing check)
State actual HEAD. `pytest tests/ -p no:randomly -rX` both interpreters → confirm 222.
`wo029_reverify_partition.py` → PASS, `.artifacts/`, clean after.
**Artifact-currency check:** confirm `batch_partition.md` currently reads batch C = 8 (the lag D42
amends) and that `audit_node_ids.md` is committed and canonical. State batch C's 9 members by their
CANONICAL NODE IDs from `audit_node_ids.md` (not prose names): races 12, 35, 14, 22, 23, 24, 25, 26,
27. Confirm 9; if it differs, STOP.

---

## §2 LAND THE THREE RATIFIED AMENDMENTS (mechanical; do before §3, which reads them)

2.1 **Fold entry 35 into `batch_partition.md`:** batch C 8 → 9, entry 35
    (`test_ledger_persistence.py::test_incremental_persist_survives_unhandled_exception_mid_capture`)
    added with its BOUND→RACE reclassification noted (D40/D41). Dated amendment annotation citing D42.
2.2 **Restate the partition's race identifiers as node IDs** from `audit_node_ids.md`. Prose names
    annotated as superseded, not deleted (historical record preserved).
2.3 **Add the standing artifact-ruling check to the WO template** (wherever §0/§1 boilerplate lives in
    the repo's WO conventions, if tracked; if the template is not a tracked file, record the standing
    step in `docs/decisions/` as the operating rule). Decision doc
    `docs/decisions/2026-07-27-a-ruling-is-not-in-force-until-its-artifact-is-committed.md` carrying
    the D42 standing step and the "regeneration reads the original" log entry verbatim.
2.4 Commit §2 as its own commit before §3 (clean separation: the amendment landing is verifiable
    independent of the conversion). State the commit sha.

---

## §3 CONVERT BATCH C'S 9 RACES (against node-ID identifiers)

Per race, on its OWN termination branch (kept, asserted before AND after — D39):
- Inject a COHERENT clock pair via the harness — `AdvancingClock` for deadline-firing races, frozen
  `FakeClock` where advance isn't needed. FACTORY-BUILT inject through the runner seams; DIRECT at
  construction. State construction path per race.
- **Entry 35** — the deadline-vs-crash RACE that began the bound re-audit. Make the outcome
  DETERMINISTIC: the asserted winner (crash or deadline) pinned by the injected clock, not by the
  real-time race. Reference WO-033 §3-bis's measured `delta` boundary; set it deterministically. State
  which outcome the test asserts and how the clock now guarantees it.
- Migrate any lingering transport monkeypatch to the seam in the same edit (0.2).
- **APPARATUS-HONESTY CHECK per assertion (D41):** state, per race, that the converted assertion rests
  on a state the REAL clock can reach — not a fake-clock decoupling artifact. A test green only because
  two injected-vs-real clocks decoupled is tuned-to-green; name the check, don't just assert green.
- **Do NOT weaken an assertion to pass under the fake clock.** If the fake clock changes what the test
  observes → STOP and report (finding about the test's original correctness).

Per-race in report: node ID, construction path, kept branch (asserted before+after), before/after time
driver, transport migration if any, gate ledger disposition, apparatus-honesty statement.

---

## §4 DETERMINISM PROOF + LEDGER STILL BITES
- Batch C under 5 seeds randomized + `-p no:randomly`, both interpreters, all green. Paste seeds.
- Representative control demo on **entry 35**: advancing/setting the clock is what determines
  crash-wins-vs-deadline-wins — the injected clock CONTROLS the outcome, not merely permits a pass.
- Ledger still bites (§0.3): corrupt one batch-C injection to an INCOHERENT pair → gate refuses,
  ledger session-end assertion FAILS naming the nodeid. Restore; sha256 == pristine; passes.

---

## §5 SCOPE FENCE
- Batch C's 9 only. NO batch A/B race re-touched. NO keepalive-blocked race (B's M=3: 6/15/16 — those
  await the keepalive seam WO, separate).
- The 3 asyncio.sleep races untouched.
- NO production logic changes. NO new reason codes. NO gate docstring precision note (deferred to the
  post-corpus vocabulary-split WO per D42). NO assertion weakened.

---

## §6 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → 222 (batch C converts, doesn't add/remove) unless a conversion
  legitimately splits/merges — state arithmetic. 0 f/xf/xp.
- `pytest --randomly-seed=<5 seeds>` → all green, both interpreters.
- `batch_partition.md` reads batch C = 9 with node-ID identifiers; §2 landed as its own commit.
- Gate ledger: 0 unmarkered refusals, 0 stale markers; batch-C dispositions as stated.
- Ledger-still-bites bite proof: four artifacts, sha256 exact-restore.
- Five `src/` sha256 IDENTICAL (`b06c347e…`,`103a8ba7…`,`5bf833c7…`,`dab18f67…`,`3d153a11…`);
  `git diff -- src/` empty.
- lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass.
- Commit (conversion, separate from §2's), push, local == remote, CI green both legs (REAL run number).
- `evidence/WO-035/` conversion evidence + gate ledger snapshot committed.
- progress.md WO-035 block.

## §7 REPORT — `WO-035-REPORT.md`
The §2 amendment commit sha and the three landed changes; the per-race batch-C conversion table (node
ID, construction path, kept branch, apparatus-honesty statement); entry 35's determinism mechanism;
§4 determinism proof (5 seeds + entry-35 control demo) and ledger-bite proof; five unchanged sha256;
every attempt; any STOP; CI run number, real.

**THEN STOP.** After this: 24/27 converted. Next (Ops-ruled, digest-reported per D42): keepalive seam
WO closes B's 3 → all 27 done → taxonomy migration → capture-loop baseline → corpus preconditions
(where reporting tightens back to per-item under the four red lines).