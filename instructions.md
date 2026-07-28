# WO-036 — KEEPALIVE/PING CLOCK SEAM (production). Closes batch B's last 3. WO-030 pattern.

BASE: current HEAD on master (WO-035 close, `86f0a96`) — confirm actual HEAD in §1.
222 both interpreters, CI green both legs (run 30363939767).

SCOPE: thread the keepalive/ping clock reads `{last_frame, last_ping}` through the seam so batch B's
races 6, 15, 16 become clock-injectable; convert those 3; extend the registration contract to the new
forwarded param(s). Commit green, STOP. **After this: all 27 clock-injectable races converted — pass
two complete.**
SHIP IMPACT: **YES** — production, full discipline (D36-3 / D38). Authorized under the WO-030 pattern.

WHAT WO-031 §4 MEASURED AND RATIFIED (the seam is sized to this, and NOTHING more — D39
seam-sized-to-measurement): the outcome-bearing non-injectable set is exactly two reads,
`last_frame` and `last_ping`, both keepalive/ping PACING, convicting races 6, 15, 16. No
throughput/lag/pong INSTRUMENT read is convicted (that was the §4 STOP-fork that did NOT fire).

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report.
0.2 No monkeypatching to make a guard pass.
0.3 Fail-then-pass bite proof for the extended registration contract: four artifacts, sha256
    exact-restore, both directions.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 **D42 STANDING ARTIFACT-RULING CHECK:** §1 confirms every artifact this WO reads reflects all
    rulings since it was written.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | WO-031 §4 outcome-bearing set `{last_frame,last_ping}`, races 6/15/16 | **OPERATED** | WO-031, ratified |
    | `connect_fn`/`monotonic_clock`/`wall_clock` seams (runner/factory/builder) | **OPERATED** | WO-028 / WO-030 |
    | `register(live_capture=True)` both-seam contract + `_LIVE_FORWARDED_PARAMS` | **OPERATED** | WO-030 §3 |
    | Coherent FakeClock / AdvancingClock harness | **OPERATED** | WO-023 §3 / WO-029 §2.0-bis |
    | Gate + factory-boundary observability | **OPERATED** | WO-023/030 |
    | The keepalive/ping clock seam + its 3 conversions | **THIS WO IS THE BUILDER** | §2–§4 |

    Any OPERATED row not verified → STOP.

---

## §1 CONFIRM HEAD, SUITE, ARTIFACT-CURRENCY, AND THE RED-LINE PRECHECK

State actual HEAD. `pytest tests/ -p no:randomly -rX` both interpreters → confirm 222.
`wo029_reverify_partition.py` → PASS 31/31, `.artifacts/`, clean after. D42 currency check: confirm
`batch_partition.md` reflects batch C = 9 and node-ID identifiers (WO-035 landed this).

**RED-LINE PRECHECK (do before any threading — this gates whether this WO proceeds at Ops authority
or STOPS to escalate):** enumerate every consumer of `last_frame` and `last_ping` in `src/`. For each
read site, state what it feeds. **If EITHER read reaches the gap-ledger, gap-detection timing, the
checksum path, or any corpus-integrity machinery, STOP and escalate** — threading a corpus-integrity
clock is red line (d) and is NOT Ops-authority. WO-031 §4 classified both as keepalive/ping PACING
reads feeding pacing assertions; confirm that from the code, do not inherit it. Expected: both feed
liveness/pacing logic only, no gap-ledger or checksum consumer. State the finding explicitly; proceed
only if clean.

---

## §2 THREAD THE KEEPALIVE/PING CLOCK — SIZED TO THE MEASURED SET (WO-030 pattern)

Thread ONLY the reads WO-031 §4 convicted. Do NOT thread throughput/lag/pong instrument clocks
(not convicted; threading them is speculative surface D39 forbids — incidental residuals stay
unthreaded BY DESIGN, recorded).

2.1 Determine the mechanism from the code: are `last_frame`/`last_ping` currently read from
    `time.monotonic()` directly, or already via `self._monotonic_clock`? Paste the read sites.
    - If they already route through `_monotonic_clock`, the seam EXISTS and these races were
      mis-classified as non-injectable — that is a finding (the WO-030 clock seam already reaches
      them). STOP and report; the conversion may be simpler than a new seam.
    - If they read raw `time.monotonic()`, thread them through the existing `_monotonic_clock` seam
      (the keepalive/ping pacing interval is a monotonic INTERVAL — D25). Declared default unchanged;
      value identical to today's.
2.2 If a NEW forwarded parameter is required (i.e. keepalive pacing needs a clock distinct from the
    deadline's `_monotonic_clock`), add it in the WO-030 shape: declared default at the builder,
    forwarded through runner→factory→builder both paths, `_LIVE_FORWARDED_PARAMS` extended.
    **Ops expectation: NO new parameter is needed — keepalive pacing is a monotonic interval and the
    existing `_monotonic_clock` seam should carry it.** If you find a new param IS needed, that is a
    finding about why keepalive time is separate from deadline time — STOP and report before adding it.
2.3 Adapter constructor default logic UNTOUCHED (WO-028/030 §2.2 precedent). Every layer default =
    today's resolved value; no production caller sees a different clock.

---

## §3 REGISTRATION CONTRACT (only if §2.2 adds a param)
If §2 threads through the existing `_monotonic_clock` with no new forwarded param, the contract is
UNCHANGED — state that and skip to §4. If a new param was added (against expectation), extend
`_LIVE_FORWARDED_PARAMS` and the `register(live_capture=True)` validation to require it, with the
bite proof in the WO-030 §3 shape (four artifacts, sha256, both directions, plus a necessity
mutation). Reuse the generalized reason code; introduce NO new load-time code.

---

## §4 CONVERT RACES 6, 15, 16 (their termination branches, apparatus-honesty per D41)
For each: inject the coherent clock pair driving the now-injectable keepalive/ping reads; keep the
race on its own termination branch (asserted before+after); state the before/after time driver and
the apparatus-honesty statement (the assertion rests on a state the real clock can reach — the
keepalive pacing outcome is now clock-controlled, not a decoupling artifact). Migrate any transport
monkeypatch to the seam in the same edit. Do NOT weaken an assertion; if the fake clock changes what
the test observes → STOP.

State each race's node ID (from `audit_node_ids.md`), construction path, and gate ledger disposition.

---

## §5 DETERMINISM + PRODUCTION-UNCHANGED + LEDGER BITE
- Races 6/15/16 under 5 seeds + `-p no:randomly`, both interpreters, all green. Paste seeds.
- Representative control demo: the injected clock CONTROLS the keepalive/ping pacing outcome one of
  these races asserts (advancing the clock drives the pacing, not merely permits a pass).
- If §2 touched production: the existing suite 222 unchanged is the production-unchanged witness for
  the non-keepalive paths; plus assert (identity, no socket) that a default-constructed adapter's
  keepalive clock read is the real `time.monotonic()` held as before.
- Ledger still bites: corrupt one of the 3 injections to an incoherent pair → gate refuses, ledger
  session-end assertion fails naming the nodeid. Restore; sha256 == pristine.

---

## §6 SCOPE FENCE
- Races 6/15/16 only. NO other race re-touched. The 3 asyncio.sleep races untouched.
- Thread ONLY `{last_frame, last_ping}` — NO throughput/lag/pong instrument clock (unconvicted).
- NO new reason code. NO gate docstring note (deferred to post-corpus vocabulary WO, D42).
- NO assertion weakened. NO speculative seam surface beyond the measured set.

---

## §7 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → 222 (converts, doesn't add/remove — state arithmetic), 0 f/xf/xp
- `pytest --randomly-seed=<5 seeds>` → all green, both interpreters
- Gate ledger: 0 unmarkered refusals, 0 stale markers; races 6/15/16 dispositions stated
- Ledger-still-bites bite proof: four artifacts, sha256 exact-restore
- IF §2 touched src: the touched file(s) reported with before/after sha256 + one-line diff each; all
  UNtouched src files sha256-identical (`b06c347e…`,`103a8ba7…`,`5bf833c7…`,`dab18f67…`,`3d153a11…`).
  IF §2 touched no src (threading was test-side only because the seam already reached the reads): all
  five identical, `git diff -- src/` empty.
- `wo029_reverify_partition.py` PASS 31/31
- lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass
- Commit, push, local == remote, CI green both legs (REAL run number)
- `evidence/WO-036/` conversion evidence + gate ledger snapshot committed
- progress.md WO-036 block, noting **PASS TWO COMPLETE: 27/27 clock-injectable races converted**

## §8 REPORT — `WO-036-REPORT.md`
The §1 red-line precheck finding (what last_frame/last_ping feed, confirmed no corpus-integrity
consumer); the §2 mechanism (existing seam vs new param, with the finding if 2.1/2.2 surprised); the
registration-contract disposition; the 3 conversions with node IDs, kept branches, apparatus-honesty;
§5 determinism + control demo + production-unchanged witness + ledger bite; the src sha256 disposition;
every attempt; any STOP; the CI run number, real. State plainly: **pass two complete, 27/27.**

**THEN STOP.** Next (corpus-blocking queue, D42): taxonomy migration → capture-loop baseline → corpus
preconditions (reporting tightens to per-item under the four red lines).