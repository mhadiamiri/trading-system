# WO-030 — CLOCK SEAM THREADING (production). D38: both paths, both-seam registration contract.



BASE: HEAD `64e2001` on master (local == remote). 217 both orders both interpreters, CI green both
legs (WO-028 code `c50b70e` run 30175153052; docs-close `64e2001` run 30176270010).
Production sha256s at base: `kraken_v2_book.py` `c98d7da0…`, `factory.py` `60cba127…`,
`registry.py` `c3db912c…`, `live_capture.py` `50b08c62…`, `logkit/decision.py` `a65cfa3c…`.

SCOPE: thread the clock seam through runner→factory→builder on BOTH paths; extend the registration
contract to require both seams. Commit green, STOP.
SHIP IMPACT: **YES** — production, full discipline (D36-3 / D38). Authorized.

WHAT WAS RULED (d38 — do not relitigate):
- **Option 1** — thread a `monotonic_clock`/`wall_clock` seam through
  `LiveCaptureRunner → create_live_capture_feed → _build_kraken_v2`, exactly parallel to WO-028's
  `connect_fn`, so race #5 becomes clock-injectable. Declared defaults at the builder signature
  (`time.monotonic` / `time.time`), NOT ambient. Both paths (the shared builder, per its doctrine).
- **Both-seam registration contract** — the existing `register(live_capture=True)` validation
  EXTENDS to require BOTH transport AND clock parameters. One gate, one error form, same doctrine
  citation. The contract follows the FORWARDING, not the motivation: any kwarg
  `create_live_capture_feed` forwards is a declared obligation on every live-capable builder.
- **Factory-boundary observability** — a factory-built adapter must be as legible to the coupling
  gate as a directly-constructed one; one explicit test asserts it (§4.2).
- **Re-baseline: reasoned exclusion** — construction-time, not per-frame.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report. This is the fifth production/
    investigation WO of this shape; the last four each corrected a ruling made without the file.
    This one has d38 AND WO-028 as a template — but if the code contradicts either, STOP.
0.2 No monkeypatching to make a guard pass.
0.3 Fail-then-pass bite proof for the extended registration contract: four artifacts, sha256
    exact-restore, BOTH directions.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt, including failed and retried.
0.6 **AUTO MODE OFF** for every production edit. `kraken_v2_book.py`, `factory.py`, `registry.py`,
    `live_capture.py`. (WO-029 twice showed the bar reading ON while the summary said off — VERIFY
    the toggle, do not trust the intention.)
0.7 Report `/context` at START.
0.8 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | WO-028 `connect_fn` threading (the template) | **OPERATED** | Committed `c50b70e`, CI 30175153052 |
    | `register(live_capture=True)` transport validation | **OPERATED** | WO-028 §3, bite-proved |
    | `_wall_clock` / `_monotonic_clock` adapter seams | **OPERATED** | WO-023 foundation |
    | Coherent FakeClock harness (shared token) | **OPERATED** | WO-023 §3 |
    | Coupling gate (`_assert_clock_transport_gate`) | **OPERATED** | WO-023 §2/§2b/§2c |
    | Clock seam through runner/factory/builder + both-seam contract | **THIS WO IS THE BUILDER** | Does not exist — §2, §3 |

    Any OPERATED row not verified as stated → **STOP and report.** In particular confirm the
    adapter's `_wall_clock`/`_monotonic_clock` seams and their injection-detection
    (`is not None` / `is not time.monotonic`) are as WO-023 left them — the threading must feed
    these exact seams.

---

## §1 RE-PASTE THE SIGNATURES AND THE WO-028 TEMPLATE (before editing)

Paste verbatim with line numbers, at THIS HEAD:
- `LiveCaptureRunner.__init__` + `_resolve_feed` (with the `connect_fn` threading WO-028 added — the
  clock threads the SAME way; show it so the parallel is exact)
- `create_live_capture_feed` AND `create_feed` (both — the shared builder means both paths)
- `_build_kraken_v2` (with WO-028's `connect_fn=_REAL_CONNECT` default — the clock defaults sit
  beside it)
- `register` (with WO-028's transport validation — the clock check extends THIS)
- `KrakenV2BookAdapter.__init__`'s `_wall_clock` / `_monotonic_clock` seam and their defaults

If any differs from expectation, note it. Same base as the WO-028 report, so `connect_fn`'s
threading should be present and intact; confirming it is the "written against its consumers" check.

---

## §2 THREAD THE CLOCK SEAM — EXACTLY PARALLEL TO connect_fn (D38, D36-1b)

Declared defaults, both paths, feeding the adapter's existing seams:

2.1 **Builder** (`_build_kraken_v2`): add `monotonic_clock=time.monotonic, wall_clock=time.time`
    to the signature, forward as `KrakenV2BookAdapter(mode=mode, connect_fn=connect_fn,
    monotonic_clock=monotonic_clock, wall_clock=wall_clock)`. Declared defaults equal to what the
    adapter resolves today. **Decide and STATE** whether the builder default for `monotonic_clock`
    should be `time.monotonic` (matching the adapter's eager-resolve convention) — note WO-023 made
    the adapter's `_monotonic_clock` EAGERLY resolved (`monotonic_clock or time.monotonic`) and
    that eager resolution is LOAD-BEARING for the suspend exception. The builder default must not
    break that. If passing `time.monotonic` explicitly changes the adapter's injected-vs-default
    detection (`is not time.monotonic`), STOP — that is a finding about the seam interaction.

2.2 **Adapter constructor**: UNTOUCHED (same decision as WO-028 §2.2 for `connect_fn`). The
    builder supplies the declared defaults; the adapter's own `_wall_clock=None` /
    `_monotonic_clock` defaults and their detection logic stay exactly as WO-023 left them. State
    the consequence: a builder-constructed adapter now holds `time.monotonic`/`time.time` explicitly
    — verify the gate still reads it as NOT-injected (default clock) and EARLY-RETURNS, because a
    real capture injects no fake clock. If a builder-supplied `time.monotonic` reads as INJECTED
    (tripping coherence/coupling on a real capture), that is a blocking finding — STOP.

2.3 **Factory, both functions**: `create_live_capture_feed(…, monotonic_clock=time.monotonic,
    wall_clock=time.time)`, forwarded into `registry.create(…)`. For `create_feed`: same treatment
    WO-028 gave `connect_fn` — it reaches `_build_kraken_v2` only under `DATA_SOURCE=kraken_v2`, and
    it must NOT forward the clock kwargs (the `simulated`/`kraken_public` builders don't accept
    them; forwarding TypeErrors). 1b is satisfied because the DECLARED DEFAULT lives in the shared
    builder — `create_feed → registry.create("kraken_v2") → _build_kraken_v2()` with no clock passed
    → the builder's declared defaults apply. Verify: `create_feed()` under `DATA_SOURCE=kraken_v2`
    yields an adapter whose clocks are the declared defaults, held at construction.

2.4 **Runner**: `LiveCaptureRunner.__init__(…, monotonic_clock=time.monotonic, wall_clock=time.time)`,
    stored, forwarded in the `adapter is None` branch. Injected-adapter branch unchanged. Note the
    runner already has a `clock` param (`self._clock = clock or time.time`, live_capture.py:70) used
    for its OWN duration accounting — do NOT conflate it with the threaded seam; state how the two
    relate and confirm the threaded clocks reach the ADAPTER, not the runner's duration clock.

2.5 **Registry**: unchanged — generic `**kwargs` passthrough.

**Every layer default must equal today's resolved value.** No production caller passing nothing sees
a different clock than it does now. Declared default, same value.

---

## §3 EXTEND THE REGISTRATION CONTRACT TO BOTH SEAMS (D38)

`register(live_capture=True)` currently validates the builder accepts `connect_fn`. Extend it to
require the builder accept **all** parameters the live path forwards: `connect_fn`, `monotonic_clock`,
`wall_clock`. One gate, one error form, same doctrine citation:
    LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM: builder <name> registered live_capture=True but
    does not accept forwarded live-path parameter(s): <missing list>. Live-capable builders must
    accept every parameter create_live_capture_feed forwards, so each is a declared seam not an
    ambient default — see <D-entry> / Principle VII.
(Reuse or rename WO-028's `LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN` — state which. If you generalize
the code name, that is a reason-code change: the vocabulary guard will require it declared. Handle it
per WO-028's precedent BUT note it for the vocabulary-split WO — do NOT introduce a second load-time
code that the split then has to untangle. Prefer generalizing the existing one over adding a new one;
state your choice and why.)

`live_capture=False` builders remain unchecked.

### Bite proof — four artifacts, sha256 exact-restore, BOTH directions (0.3, 0.4)
- **Mutation A (refusal):** a throwaway `live_capture=True` builder missing `wall_clock` (but having
  `connect_fn` + `monotonic_clock`) → registration RAISES, the message naming the MISSING param
  specifically (proving the check is per-parameter, not just "has connect_fn"). Also show a builder
  missing `connect_fn` still refuses (WO-028's case still holds under the generalized check).
- **Mutation B (preservation):** a builder with ALL THREE registers cleanly; a `live_capture=False`
  builder missing all three registers cleanly (no over-fire).
- **Mutation C (necessity):** weaken the new clock-param check to a no-op → the wall_clock-missing
  builder registers SILENTLY → proves the check, not arg-binding, enforces it.
- Restore each; sha256 == pristine; final PASS.

Confirm the REAL `_build_kraken_v2` passes the generalized check after §2.

---

## §4 PROVE PRODUCTION UNCHANGED + FACTORY-BOUNDARY OBSERVABILITY (D38's named test)

4.1 **Production socket path unchanged** — existing suite 217 unchanged both orders both
    interpreters; plus assert (identity, no socket) that the non-live production default clocks are
    `time.monotonic`/`time.time` held at construction through `create_feed`/`_build_kraken_v2`.

4.2 **The factory-boundary observability test D38 named** — build via the FULL
    runner→factory→builder path (not a directly-constructed adapter) and assert the coupling gate
    sees the injected seams identically:
    - injected fake COHERENT clock pair + injected fake transport (`connect_fn`), through the runner
      → gate PROCEEDS (`PROCEED_COHERENT`);
    - injected fake clock + DEFAULT (real) transport, through the runner → gate REFUSES on COUPLING,
      **pre-connection** (connect callable never invoked).
    This is the whole point of the exercise: the gate's guarantees cross the factory boundary
    intact. A factory-built adapter is as legible to the gate as a directly-built one. Place it with
    the gate/identity tests. It is a +1 (or +N) to the count — state the arithmetic.

Do NOT open a real socket in either test. If construction through the path attempts a connection,
STOP — the builder must do no I/O at construction.

---

## §5 RACE #5 IS NOT CONVERTED HERE
This WO makes race #5 clock-INJECTABLE; it does NOT inject a clock into it. That is WO-029 batch A,
which re-enumerates the full 26 at HEAD after this lands (D38 named the denominator: 26). Do NOT
convert race #5 or any pass-two race in this WO. §4.2's tests use throwaway/fixture constructions,
not the race #5 test itself. If tempted to "just convert #5 while the seam is fresh," STOP — that
crosses into pass two and breaks the batch denominator.

---

## §6 RE-BASELINE — REASONED EXCLUSION (D36-3 / D38)
The threaded clock params execute ONCE at construction, never in `get_live_market_data`'s per-frame
loop. Outside the hot path by the standing rule's boundary. **No re-baseline triggered** — stated as
a reasoned exclusion with the boundary cited, not skipped. (Note distinctly: the clocks the adapter
USES per-frame are unchanged in identity — same `time.monotonic`/`time.time` — so per-frame timing
behaviour is byte-identical; the change is only WHERE the default is declared.)

---

## §7 DECISION LOG — ONE ENTRY, RATIFIED VERBATIM + THE GENERALIZING SENTENCE
`docs/decisions/2026-07-25-a-transport-seam-is-not-a-clock-seam.md`:

> A transport seam is not a clock seam; each injected dependency crosses the runner/factory/builder
> boundary on its own or not at all. Unblocking a factory-built race for its transport (WO-028's
> connect_fn) did not unblock it for its clock; the clock needed the identical threading.
>
> Sixth specimen of a-figure-traveled-as-prose (WO-027's "26" was 25 until this WO); second sourced
> from the shared builder (D36 was the first).
>
> Generalizing, since the builder will be the crossing point for every future seam:
> **the shared builder's forwarding surface is a contract inventory — every kwarg it forwards is a
> declared obligation on every live-capable builder, and the registration gate is that inventory's
> enforcement.** When a third seam needs the crossing, the checklist question is already written:
> "what else does the shared builder forward, and does every live-capable builder accept it?"

---

## §8 SCOPE FENCE
- NO pass-two conversion — race #5 and all 26 stay for WO-029.
- NO new load-time reason code if the existing one can be generalized (§3) — avoid handing the
  vocabulary-split WO a second tangle.
- NO gate docstring precision note (r20 ruling 2 folds into the vocabulary-audit WO per D37).
- NO adapter-protocol seam (option (c), still the named successor, not now).

---

## §9 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → 217 + §4.2's tests (state N and arithmetic), 0 f/xf/xp
- `pytest tests/ --randomly-seed=<seed>` → same, both interpreters
- Extended registration contract live; bite proof A+B+C, four artifacts, sha256 exact-restore
- `_build_kraken_v2` passes the generalized check; stated
- §4.1 non-live default clocks are `time.monotonic`/`time.time` by identity; §4.2 factory-boundary
  observability (proceed + pre-connection refuse) green
- Gate ledger: 0 unmarkered refusals, 0 stale markers
- `lint-imports` 6/6 (runner still imports only `factory`/`websockets`, never `kraken_v2_book`) ·
  `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 ·
  `preflight_path_check.py` pass
- The FOUR unchanged production files sha256-IDENTICAL before/after; the TWO changed
  (`kraken_v2_book.py`, `factory.py`, `registry.py`, `live_capture.py` — the same four WO-028
  touched) reported with new hashes and a one-line diff summary each. `logkit/decision.py` changes
  only if a reason code is added/renamed (§3) — state which.
- Commit, push, local == remote, CI green BOTH legs via `gh run view` (paste run number — not a
  placeholder; WO-028 shipped with `_[fill]_`)
- Snapshot gate ledger into `evidence/WO-030/` via `tools/snapshot_gate_ledger.py`
- Append a WO-030 block to `progress.md`

## §10 REPORT — `WO-030-REPORT.md`
Signatures before/after; the §2.1 eager-resolve interaction decision; the §2.2 gate-reads-default
verification; `create_feed` both-path handling; the generalized registration code choice and its
bite proof verbatim with sha256; §4.1 + §4.2 with the observability test; the reasoned re-baseline
exclusion; the CI run number (real); the production-file hashes; every attempt; any STOP.

**THEN STOP.** WO-029 batch A (full 26, re-enumerated at HEAD) is next, fresh session.