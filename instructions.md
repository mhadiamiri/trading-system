# WO-039 — ENABLE-FIX: make the committed instrument observable through the REAL loop. Production.

**AUTO MODE OFF — verify the bottom bar before editing. This edits the capture loop's control flow.**

BASE: HEAD `e6892d9` (instrument committed; CLOSEOUT-3 proved it collects 0 timings through the real
generator). CI green `30389381594`. `kraken_v2_book.py` sha256 `cae3741f…`.

DENOMINATOR/CONTEXT: pass two CLOSED (24+3+3/30). This WO does NOT touch pass two. It fixes the
capture-loop instrument so it can be driven through `get_live_market_data` — the precondition WO-040
(the real baseline) depends on.

SCOPE: add the `enable_instrument` flag; bite-prove a NONZERO timing THROUGH THE REAL ASYNC GENERATOR;
prove flag-off is zero-behavior-change. Commit green, STOP. Do NOT produce the baseline (WO-040).
SHIP IMPACT: **YES** — production edit to `get_live_market_data`'s control flow. Full discipline.
REPORTING: PER-ITEM (D43) — this is corpus-machinery-adjacent (the loop the corpus runs).

WHAT D-r30 RULED that this WO executes:
- The `enable_instrument` flag shape (Ops-recommended, approved): explicit, DEFAULT-OFF, ONE branch,
  ZERO production behavior when unset. Chosen over respect-external-state because the flag keeps
  enablement VISIBLE at a call site production never uses, rather than reintroducing ambient state
  into the loop WO-023 purged of it.
- Acceptance condition (a): the bite proof MUST collect a nonzero timing THROUGH the real async
  generator — fixtures driven through `get_live_market_data` with the flag ON, **entry point stated
  per the ratified standing check** — and its negative half: flag OFF → zero timings, zero observable
  behavior change, hot-path sha256 identical aside from the one branch.
- Acceptance condition (b): the flag-OFF branch cost (one boolean per frame) is reasoned-below-floor
  vs the ~10ms/frame detection limit — it CANNOT be measured by an instrument that doesn't yet observe
  the loop, so it is declared, not measured. WO-040's baseline is then measured WITH the branch
  present, so the reference includes the instrument's own footprint by construction. NO phantom
  subtraction.
- The CLOSEOUT-2 acceptance is WITHDRAWN: 0.542ms and the 10.595ms shift are NOT real-loop
  measurements (direct-construct harness). This WO's bite proof REPLACES that false proof.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins: STOP and report.
0.2 No monkeypatching / no ambient state. The flag is an explicit parameter, not a module global or a
    pre-set attribute the loop reads. If you find yourself making the loop READ external state rather
    than TAKE A PARAMETER, STOP — that is respect-external-state, which D-r30 rejected.
0.3 **THE STANDING ENTRY-POINT CHECK (ratified D-r30):** the bite proof MUST state the ENTRY POINT it
    drove and confirm it is the PRODUCTION PATH (`get_live_market_data`, the async generator), NOT a
    direct-construct harness. A harness that builds `PerFrameRecord()` and calls its methods proves the
    methods work, not that production reaches them. If the proof does not enter through
    `get_live_market_data`, it is VOID and this WO STOPs. Four artifacts, sha256 exact-restore.
0.4 Preservation dual mandatory: flag-ON collects timings (the bite), flag-OFF collects nothing AND
    changes no behavior (the dual), local and direct.
0.5 Report every attempt.
0.6 AUTO MODE OFF — this is `get_live_market_data`. Verify the toggle, do not trust intent.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | `PerFrameRecord` + hooks | **OPERATED** | `e6892d9` — observes NOTHING through the real loop (the defect) |
    | `get_live_market_data` line 2648 re-init (the bug) | **OPERATED** | `e6892d9:2648` — `PerFrameRecord()` fresh, enabled=False, no external enable |
    | Ground-truth fixtures (raw_frames: 4; captured_frames: 41) | **OPERATED** | CLOSEOUT-3 located them; note the checksum-notation issue below |
    | The `enable_instrument` flag + the real-loop bite proof | **THIS WO IS THE BUILDER** | §2/§3 |

---

## §1 CONFIRM STATE + THE ENTRY-POINT DIAGNOSIS
HEAD `e6892d9`, 234 both interpreters, `git diff -- src/` empty. Re-state CLOSEOUT-3's finding from the
code: paste line 2648 and the two hook sites (2902/2962), and confirm the async generator gives no
external enable path today. This is the defect the flag fixes; showing it is the "written against its
consumers" check.

Also confirm which fixture set can drive the real processing path for the bite proof:
- CLOSEOUT-3 found `captured_frames` (41, real checksums) FAILS checksum validation because its floats
  are scientific-notation (`5.1e-05`), rejected by the WO-008b-B guard. `raw_frames` (4, string
  values) processes but self-generated checksums don't validate.
- The bite proof does NOT need checksum VALIDATION to pass — it needs the loop to PROCESS frames and
  the instrument to TIME them. State which fixture drives the processing path far enough to reach both
  hooks (frame-received AND ready-to-yield) so a nonzero timing is collected. If NEITHER reaches both
  hooks without checksum failure aborting the frame first, that is a finding — STOP and report (the
  loop may not be drivable to completion by any existing fixture, which changes WO-040's approach too).

---

## §2 ADD THE `enable_instrument` FLAG (D-r30 ruling 1; production edit)
2.1 Add `enable_instrument: bool = False` to `get_live_market_data`'s signature. At line 2648, instead
    of unconditionally `self._per_frame_record = PerFrameRecord()`, create it ENABLED iff the flag is
    set: `PerFrameRecord(enabled=enable_instrument)` (or equivalent single-branch form). DEFAULT-OFF:
    a production call passing nothing gets `enabled=False`, identical to today.
2.2 ONE branch. No other control-flow change. The hooks at 2902/2962 already check `.enabled`; with the
    flag off they stay False and the loop behaves EXACTLY as `e6892d9`. State the diff is this single
    parameter + the one-line construction change and nothing else.
2.3 Confirm no ambient state introduced: the flag is a PARAMETER, enablement is visible at the call
    site, the loop reads no new external attribute/global. (D-r30's reason for the flag over
    respect-external-state.)

---

## §3 THE REAL-LOOP BITE PROOF (0.3/0.4 — replaces the withdrawn CLOSEOUT-2 proof)

Drive fixtures THROUGH `get_live_market_data(enable_instrument=True)` — the production async generator,
the real door — and collect timings.

- **BITE (flag ON):** N frames driven through the real generator with the flag on → instrument collects
  N nonzero timings. Paste the count and the distribution. **State the entry point explicitly:
  "driven through get_live_market_data, the production async generator" — per the standing check.** A
  nonzero timing count through the real door is the anti-VOID proof CLOSEOUT-2 only appeared to give.
- **DUAL (flag OFF):** same frames, same call, flag off (or omitted) → ZERO timings collected AND the
  MarketState output identical to flag-on (the instrument observes, does not alter). Prove behavior
  unchanged: the sequence of yielded states is identical with the flag on vs off.
- Four artifacts (flag-on distribution, flag-off zero-collection, the behavior-identity comparison, the
  sha256 manifest), sha256 exact-restore.
- **Contrast with the withdrawn proof, explicitly:** state that CLOSEOUT-2's proof drove a
  direct-construct harness (never entered get_live_market_data) and this one enters the real generator
  — the difference the standing check now requires every proof to declare.

If the flag-on run collects ZERO timings, the fix did not work — STOP (do not adjust the test to pass).
If it collects timings but the flag-off run BEHAVES differently (different states yielded), the branch
is not zero-cost-when-off — STOP.

---

## §4 RE-BASELINE DISPOSITION (D-r30 condition b)
The flag-OFF per-frame cost is ONE boolean check. It cannot be measured by an instrument that only
observes when the flag is ON — so declare it REASONED-BELOW-FLOOR vs the ~10ms/frame detection limit,
with the boundary cited. Do NOT attempt to measure the off-branch cost (circular). State that WO-040's
baseline will be measured WITH the branch present, so the reference includes the instrument footprint
by construction — no subtraction.

---

## §5 SCOPE FENCE
- Adds the flag + its bite proof ONLY. Does NOT produce the capture-loop baseline (WO-040).
- Does NOT drive a real parse+CRC32+book-update measurement run (that is WO-040's real-frame baseline).
- Does NOT touch pass two, the gap ledger, the checksum path's logic, or any other loop behavior.
- Does NOT cite 0.542ms or 10.595ms as real — annotate them withdrawn (§6).

---

## §6 WITHDRAW THE CLOSEOUT-2 NUMBERS (annotate, not rewrite — D-r30 ruling 3)
In `evidence/WO-038/baseline.json` and the CLOSEOUT-2 report: annotate that 0.542ms and the 10.595ms
shift were measured by a DIRECT-CONSTRUCT harness that never entered `get_live_market_data`, are NOT
real-loop measurements, and are withdrawn as the reference. Preserve them (annotate-not-rewrite) with
the reason and the pointer to this WO's real-loop bite proof. The real baseline number comes in WO-040.
Add the lineage note: this is the WO-023 §7 VOID one level deeper — a confident number measuring a path
that is not the path — now with its mechanical answer (the entry-point standing check).

---

## §7 ACCEPTANCE
- `enable_instrument` flag added; default-off; single branch; no ambient state (parameter, not global)
- Real-loop bite proof: flag-ON collects N nonzero timings THROUGH get_live_market_data (entry point
  stated); flag-OFF collects zero AND yields identical states; four artifacts, sha256 exact-restore
- Off-branch cost declared reasoned-below-floor (not measured); WO-040-includes-footprint note stated
- CLOSEOUT-2 numbers annotated withdrawn in both locations
- `kraken_v2_book.py` before/after sha256 (`cae3741f…` → new) + the one-branch diff; other four src
  identical (`factory.py` `103a8ba7…`, `registry.py` `5bf833c7…`, `live_capture.py` `dab18f67…`,
  `decision.py` `3d153a11…`, `risk/engine.py` `bd0747f…`)
- 234 both interpreters (+ any bite-proof test; state arithmetic); lint 6/6 · contract 6/6 · ruff
  clean · annotation 0 · preflight pass
- `wo029_reverify_partition.py` PASS 31/31
- Commit, push, local == remote, CI GREEN both legs (REAL run number — on the commit containing the
  flag AND the bite-proof test, per the CLOSEOUT-1 lesson)

## §8 REPORT — `WO-039-REPORT.md`
The line-2648 defect shown; the flag diff (single branch); the real-loop bite proof with the entry
point STATED and the flag-on nonzero-timing count + flag-off zero + behavior-identity; the explicit
contrast with the withdrawn direct-construct proof; the off-branch below-floor declaration; the
CLOSEOUT-2 withdrawal annotations; the hot-path sha256; the CI run (real, on the right commit); every
attempt; any STOP.

**THEN STOP.** WO-040 next: drive real fixtures through get_live_market_data(enable_instrument=True),
real parse+CRC32+book-update, produce the first real capture-loop baseline — seven dimensions,
host-suspend verified, the anti-VOID measurement done for real.