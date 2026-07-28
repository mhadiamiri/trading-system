# WO-034 — PASS TWO, BATCH C: node-ID regeneration + convert the 9 measured races.

BASE: current HEAD on master (WO-033 close, `2ece73f`) — confirm actual HEAD in §1 and use it.
222 both interpreters, CI green both legs (run 30321861387).

SCOPE: **§2 regenerate identifiers (classify/verify only); §3 convert batch C's 9 races.** Commit
green, STOP. Batch C is the LAST conversion batch; after it, all 27 clock-injectable races are done.
SHIP IMPACT: **NO** — tests, conftest, evidence, a tools/ hygiene pass. Every `src/` file
byte-unchanged; §6 proves it with the five sha256s.

DENOMINATOR (settled, all-measured, per D40+D41): clock-injectable **27**, bounds **6**, total **30**.
Batch C = **9 races**: its original 8 + **entry 35** (`test_ledger_persistence.py`
`test_incremental_persist_survives_unhandled_exception_mid_capture`, reclassified BOUND→RACE, D41).

WHAT D41 RULED that shapes this WO:
- **Identifier regeneration (promoted to ruled):** the audit's 30 identifiers migrate to pytest NODE
  IDs, collected via pytest's OWN collection, never grepped from source text. Node IDs are
  position-and-structure-faithful, truncation-immune, and see class-bound methods natively (entry 36
  was a method on `TestNoSilentFallback`, invisible to `^def test_`). Fold into batch C planning,
  where identifiers become load-bearing again.
- **The apparatus-honesty rule (ratified doctrine, applies to every conversion here):** before reading
  a measurement (or a green test) as a system property, ask which invariants of the real system the
  apparatus broke to obtain it. A conversion injects a fake clock, which breaks clock-lockstep — so
  every converted assertion must be checked that it rests on a state the REAL clock can reach, not on
  a decoupling artifact. A test that passes only because fake-deadline-time outran a real-clock
  terminator is tuned-to-green, the sign-reversed twin of the δ=5.0 tuned-to-red the pass just refused.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report. Do not reconcile silently.
0.2 No monkeypatching to make a guard pass; migrate transport to the seam in the same edit where a
    clock is injected (COUPLING trips otherwise).
0.3 Every guard/assertion touched gets a fail-then-pass bite proof: four artifacts, sha256
    exact-restore.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt, including failures and retries.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | Amended `batch_partition.md` (D39 B/C plan) | **OPERATED** | WO-032 §2 |
    | Measured denominator 27/6/30, batch C = 9 | **OPERATED** | D40 + D41 |
    | `AdvancingClock` + coherent FakeClock harness | **OPERATED** | WO-029 §2.0-bis / WO-023 §3 |
    | Clock + transport seams (runner/factory/builder) | **OPERATED** | WO-028 / WO-030 |
    | Gate ledger + marker + `.artifacts/` boundary guard | **OPERATED** | WO-024/025/026/032 |
    | Entry 35's own conversion (deadline-vs-crash race) | **THIS WO CONVERTS** | §3 |
    | Node-ID identifier regeneration of the audit's 30 | **THIS WO IS THE BUILDER** | Does not exist — §2 |

    Any OPERATED row not verified → STOP.

---

## §1 CONFIRM HEAD, SUITE, MEMBERSHIP
State actual HEAD. `pytest tests/ -p no:randomly -rX` both interpreters → confirm **222**. Run
`wo029_reverify_partition.py` → PASS 30/30 by name, `.artifacts/`, clean after. State batch C's 9
members from the amended partition + entry 35:
`test_ledger_persistence.py` (12, 35), `test_host_suspend.py` (14 — the non-foundation one),
`test_protocol_ping.py` (22–23), `test_throughput.py` (24), `test_reconnect_to_effect.py` (25),
`test_venue_close_path.py` (26), `test_backoff_breaker.py` (27). Confirm 9; if it differs, STOP.

---

## §2 REGENERATE THE AUDIT'S 30 IDENTIFIERS AS PYTEST NODE IDS (D41, this WO builds it)

2.1 **Collect, do not grep.** Use pytest's own collection (`--collect-only -q` or the collection API)
    to obtain the node ID (`path::Class::method` or `path::function`) for each of the 30 audit races.
    A `tools/` script that runs collection and matches audit entries to collected node IDs — NEVER a
    regex over source text. Writes to `.artifacts/` (WO-032 boundary).
2.2 **Diff against the prose list.** For each of the 30, put the audit's prose identifier beside the
    collected node ID. The FOUR known mismatches (entries 5, 28, 31, 36 — truncations; 36 a class
    method) must appear. **Any mismatch BEYOND those four is a FINDING** — a race the audit misidentified
    that nobody has caught — STOP and report it before converting anything.
2.3 **Commit the node-ID table** as `evidence/WO-034/audit_node_ids.md` — the audit's first
    structure-faithful identifier set. Note it supersedes the prose identifiers for all future
    enumeration (reverify tool, batch planning) — but do NOT rewrite the historical audit; annotate
    that node IDs are now canonical.
2.4 This is classify/verify only — it converts no race and edits no test. If regeneration surfaces a
    misidentification that changes the denominator, that ESCALATES (like entry 35) — report, do not
    fold.

---

## §3 CONVERT BATCH C'S 9 RACES

Per race, on its OWN termination branch (the amended partition's keep-the-branch requirement; branch
asserted before AND after, per D39):
- Inject a COHERENT clock pair (shared token) via the harness — `AdvancingClock` for deadline-firing
  races, frozen `FakeClock` where the test does not need the clock to advance. FACTORY-BUILT races
  inject through the runner seams; DIRECT races at construction. State each race's construction path.
- **Entry 35 is the notable one** — it is the deadline-vs-crash RACE this whole bound re-audit began
  with. Its conversion must make the outcome DETERMINISTIC: the crash must reliably win (or the
  deadline must reliably win — whichever the test asserts), pinned by the injected clock rather than
  by which wins the real-time race. Reference WO-033 §3-bis's measurement: the `delta` that determines
  the outcome is known; the conversion sets it deterministically. State which outcome the test asserts
  and how the injected clock now guarantees it.
- Migrate any lingering transport monkeypatch to the seam in the same edit (0.2).
- **Apply the apparatus-honesty check (D41) to every converted assertion:** state, per race, that the
  assertion rests on a state the REAL clock can reach — not on a fake-clock decoupling artifact. A
  converted test that passes only because two injected-vs-real clocks were decoupled is tuned-to-green;
  name the check explicitly, do not just assert green.
- **Do NOT weaken an assertion to pass under the fake clock.** If the fake clock changes what the test
  observes, that is a finding about the test's original correctness — STOP and report.

Per-race in the report: construction path, termination branch (kept, asserted before+after), before/
after time driver, transport migration if any, gate ledger disposition, and the apparatus-honesty
statement.

---

## §4 DETERMINISM PROOF + LEDGER STILL BITES
- Batch C under **5 seeds** randomized + `-p no:randomly`, both interpreters, all green. Paste seeds.
- For ≥1 representative race (entry 35 preferred, since it is the race that motivated the re-audit),
  show the injected clock CONTROLS the outcome — advancing/setting the clock is what determines
  crash-wins-vs-deadline-wins — not merely that it passes.
- **Ledger still bites (§0.3):** corrupt one batch-C injection to an INCOHERENT pair → gate refuses,
  ledger session-end assertion FAILS naming the nodeid. Restore; sha256 == pristine; passes.

---

## §5 SCOPE FENCE
- Batch C's 9 races only. NO batch A/B race re-touched. NO keepalive-blocked race (batch B's M=3,
  races 6/15/16 — those wait on the keepalive seam WO, running separately).
- The 3 asyncio.sleep races NOT touched.
- NO production logic changes. NO new reason codes (vocabulary split is later).
- NO gate docstring precision note (r20 ruling 2 → vocabulary-split WO, D37).
- NO weakening any assertion to fit the fake clock.

---

## §6 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → 222 (batch C converts, does not add/remove) unless a conversion
  legitimately splits/merges — state arithmetic. 0 f/xf/xp.
- `pytest --randomly-seed=<5 seeds>` → all green, both interpreters.
- Node-ID table committed; diff shows exactly the 4 known mismatches (any 5th = STOP, already handled).
- Gate ledger: 0 unmarkered refusals, 0 stale markers; batch-C dispositions as stated.
- Ledger-still-bites bite proof: four artifacts, sha256 exact-restore.
- Five `src/` sha256 IDENTICAL (`b06c347e…`,`103a8ba7…`,`5bf833c7…`,`dab18f67…`,`3d153a11…`);
  `git diff -- src/` empty.
- lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass.
- `wo029_reverify_partition.py` PASS (now node-ID-aware if you wired §2 into it — state whether you
  did; if not, it still passes by name).
- Commit, push, local == remote, CI green both legs (REAL run number).
- `evidence/WO-034/` (node-ID table + batch-C conversion evidence) committed; gate ledger snapshotted.
- progress.md WO-034 block appended.

## §7 REPORT — `WO-034-REPORT.md`
The §2 node-ID table with the prose diff (the 4 known mismatches confirmed, any 5th escalated); the
per-race batch-C conversion table with construction path, kept branch, and the apparatus-honesty
statement per race; entry 35's determinism mechanism specifically; the §4 determinism proof (5 seeds +
representative control demo) and ledger-bite proof; the five unchanged sha256; every attempt; any STOP;
the CI run number, real.

**THEN STOP.** After batch C: 24 of 27 clock-injectable races converted (batch B's 3 await the
keepalive seam WO). Next: keepalive seam WO closes B's M=3 → all 27 done → vocabulary-split audit.