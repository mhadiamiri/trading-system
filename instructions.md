# WO-024 PASS ONE — TRANSPORT MIGRATION (mechanical, no clocks)

**START THIS IN A FRESH CLAUDE CODE SESSION.** Ruled by D34/D35. Do not continue an existing one.

BASE: HEAD `9175969` on master (local == remote). 216 passed both orders, both interpreters.
CI green both legs (run 30036599896). import-linter 6/6, contract 6/6, ruff clean, annotation 0.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Where this order and the code disagree, the CODE WINS: STOP and report.
    Do not reconcile silently. This rule has fired three times in this WO family and was right
    every time.
0.2 No monkeypatching to make a guard pass.
0.3 Every guard gets a fail-then-pass bite proof: four artifacts, `sha256` exact-restore.
0.4 Preservation duals mandatory, and **local and direct** — never relying on a neighbouring
    branch to pin a behaviour (ratified doctrine; see §6).
0.5 Report every attempt, including failed and retried ones.
0.6 **AUTO MODE OFF** for every edit to `src/trading/data/adapters/kraken_v2_book.py`.
0.7 If you reach ~70% context, STOP at a clean seam, commit what is green, report. You cannot
    read `/context` yourself — ask the user for a reading rather than estimating.

---

## §0.5 CONTEXT YOU DO NOT HAVE (fresh session briefing)

A pre-connection **clock/transport gate** now exists in `kraken_v2_book.py`
(`_assert_clock_transport_gate`, called from `get_live_market_data` immediately after the
`GAP_PERSIST_UNCONFIGURED` refusal). It enforces:

- **COUPLING** — a fake clock is permitted ONLY where the transport is not the real one.
  The transport is tested **by identity** against `_REAL_CONNECT`, a module-level capture of
  `websockets.connect` taken at import.
- **COHERENCE** — injected clocks must be the one-source coherent pair (shared
  `_coherence_token`, stamped by the `FakeClock` harness), unless the run passes
  `incoherent_clocks_allowed="<reason>"` explicitly. The gate NEVER infers the exception.
- **Early return** — if no clock is injected, the gate returns immediately. This is the path
  every real run and every non-suspend test takes today.

The three seams have **three deliberately different conventions** (D35-2: this asymmetry carries
semantics and is NOT to be normalized):

| Seam | Default | Convention | Resolved | "Injected?" test |
|---|---|---|---|---|
| `_wall_clock` | `None` | raw None | late (`or time.time`) | `is not None` |
| `_monotonic_clock` | `monotonic_clock or time.monotonic` | eagerly resolved | direct call | `is not time.monotonic` |
| `_connect_fn` | `None` | raw None | late (`or websockets.connect`) | `resolved is _REAL_CONNECT` |

`_monotonic_clock`'s eager resolution is **load-bearing**: the suspend test injects a fake wall
against the REAL monotonic, the real monotonic reads as not-injected, coherence evaluates False,
and the named exception becomes required. Do not "tidy" this.

**WHY PASS ONE EXISTS.** The 30-test deterministic conversion needs each test to inject a clock.
Because `_connect_fn` defaults to raw `None`, any test that module-patches `websockets.connect`
reads as a DEFAULT (real) transport to the gate — so injecting a clock into it would refuse on
COUPLING. Every such test must migrate its transport to constructor injection FIRST. D35-1 split
the work: **this pass migrates transport ONLY, injects NO clocks, and must change no behaviour.**

---

## §1 ENUMERATE THE POPULATION BEFORE EDITING ANYTHING

Grep the whole test tree for module-level patching of the transport — every form:
`patch("websockets.connect", …)`, `patch.object(websockets, "connect", …)`, monkeypatch
equivalents, fixture-level patches, and any indirection through a helper.

Produce a table BEFORE any edit: file, test name (or fixture), patch form, and whether the
adapter is constructed before or after the patch. State the COUNT.

Prior soundings put this near 13, but that number is from a partial grep and is NOT authoritative.
**The grep is authoritative.** If the count differs from 13, that is expected — report the real
number. If any patch site is NOT reachable by constructor injection (e.g. the adapter is
constructed inside library code you do not control), **STOP and report** — that is a
seam-completeness finding, not something to work around.

---

## §2 THE MIGRATION — MECHANICAL, BEHAVIOUR-PRESERVING

For each site in the §1 table: replace module-level patching with constructor injection,
`connect_fn=<the same fake callable>`. Nothing else changes — no clocks, no assertions, no
timings, no fixtures rewritten.

Constraints:
- **Do not inject any clock.** Not one. Pass one is transport-only; a clock in pass one
  invalidates the acceptance criterion.
- **Do not touch** `tests/integration/test_host_suspend.py::test_host_suspend_recorded_diagnostic_not_terminal`
  — already migrated in the foundation and already declares its exception.
- Reconnection tests: `self._connect_fn` persists across `_connect` calls, so a factory injected
  once serves every reconnect. Verify this explicitly for each reconnect test rather than
  assuming it.
- Bound-method identity pitfall (hit twice already): `spy.connect` yields a NEW object per
  attribute access. Where identity matters, capture ONE bound method and reuse it.
- If any single migration needs anything beyond swapping the patch for `connect_fn=`,
  **STOP and report** before doing it.

Migrate in small committed-green batches if the population is large. State your batching.

---

## §3 THE FALSIFIABLE ACCEPTANCE CRITERION — THE GATE MUST NEVER REFUSE

D35-1 adopted the split specifically because pass one has a complete, falsifiable criterion:
**216 green unchanged AND the gate never fires.** "Never fires" must be MEASURED, not reasoned.

Build a **gate ledger**: an autouse session-scoped test hook that wraps
`_assert_clock_transport_gate` and records, for every invocation across the whole suite:
- test nodeid,
- outcome: `EARLY_RETURN` (no clock) / `PROCEED_DECLARED` (incoherent, named exception) /
  `REFUSED_COUPLING` / `REFUSED_COHERENCE`.

Write the ledger to `evidence/WO-024-PASS1/gate_ledger.txt` and assert at session end:
**`REFUSED_COUPLING == 0` and `REFUSED_COHERENCE == 0`.**

Expected shape after migration: every live-capture test `EARLY_RETURN`; exactly ONE
`PROCEED_DECLARED` (the suspend test); zero refusals. Report the actual counts. **Any refusal
during pass one is BY DEFINITION A FINDING, not friction — STOP and report it.**

**Bite proof for the ledger assertion** (0.3, four artifacts, sha256): mutate ONE migrated test
to re-introduce module patching AND inject a clock → the gate refuses on COUPLING → the ledger
assertion FAILS. Restore, sha256 == pristine, passes. A ledger that cannot fail proves nothing.

The ledger is a pass-one instrument. State in the report whether it should persist into pass two
(Ops's view: yes — it becomes the conversion's live safety net) but do not decide that here.

---

## §4 TWO DECLARATIONS IN PRODUCTION (docs-only; D35-2 and D35-3)

Production edits in this WO are **comments and docstrings only**. No logic changes.

4.1 **The convention declaration** (D35-2). A short comment block at the three seam definitions
    in `__init__` stating each convention and WHY it differs — explicitly recording that
    `_monotonic_clock`'s eager resolution is load-bearing for the named-exception mechanics
    (real monotonic reads as not-injected → coherence False → exception required by name).
    Doctrine line to include: **convention asymmetry that carries semantics is architecture, not
    untidiness; normalize only what is provably decorative.**

4.2 **The declared limit of the coupling check** (D35-3). In the gate docstring: the gate refuses
    the real transport BY IDENTITY, so a hand-written wrapper that delegates to
    `websockets.connect` is not identical to it and would not be refused. State that this
    requires deliberately constructing a bypass, that the guard contract throughout this project
    is *the accidental case refuses; the adversarial insider is out of scope*, and name the tell:
    **any wrapper around the real transport appearing in the tree is a deliberate act, greppable,
    and a STOP-and-ask event under the 0.1a standing rules.**

---

## §5 SCOPE FENCE
- **NO clock injection.** That is pass two.
- **NO taxonomy migration, NO 008c, NO capture-loop instrument, NO corpus.**
- **NO normalizing the three seam conventions** (D35-2 ruled: leave them).
- **NO chasing the wrapper bypass** (D35-3 ruled: declare it).

---

## §6 DECISION LOG — ONE ENTRY, RATIFIED VERBATIM

`docs/decisions/2026-07-24-incidental-coverage-is-not-coverage.md`:

> A guard branch can be pinned only incidentally by a neighbouring branch — incidental coverage
> is coverage until the neighbour changes, and then it is nothing, silently.

Specimen: WO-023 §2c Mutation D (deleting the gate's early return) was caught by six unrelated
tests through the COHERENCE branch and by zero tests through COUPLING; the coupling branch's
preservation of the production path was pinned only by its neighbour. Standing consequence,
joining the S13 family as its coverage-topology corollary: **a branch's preservation dual must be
local and direct.**

---

## §7 ACCEPTANCE — ALL MUST HOLD BEFORE COMMIT
- `pytest tests/ -p no:randomly -rX` → **216 passed**, 0 failed / 0 xfailed / 0 xpassed
- `pytest tests/ --randomly-seed=20260726 -rX` → same
- BOTH interpreters (3.11 strict, 3.14 dev)
- **Gate ledger: 0 REFUSED_COUPLING, 0 REFUSED_COHERENCE, exactly 1 PROCEED_DECLARED**
- Ledger bite proof: four artifacts, sha256 exact-restore
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff check .` clean ·
  `annotation_name_scan.py` 0 · `preflight_path_check.py` pass
- Test count: state it explicitly with arithmetic. Migration alone is +0; the ledger may add
  nothing or one session-level check — say which.
- Commit, push, local == remote, CI green BOTH legs via `gh run view`
- Append a WO-024 pass-one block to `progress.md`; do not rewrite existing content

---

## §8 REPORT — `WO-024-PASS1-REPORT.md`
Must contain: the §1 population table with the real count and how it differs from 13; the
per-site migration list; the explicit reconnect-persistence verification; the gate ledger counts
and its file; the ledger bite proof verbatim with sha256 lines; both declaration texts as
committed; the §7 gate output pasted verbatim; the test-count arithmetic; your ledger-persistence
recommendation for pass two; every attempt including failures; and any point you STOPPED.

**THEN STOP.** Pass two (clock injection) is NOT begun.


-----
Update:

# WO-025 — LEDGER CLOSEOUT + MARKER-BASED EXCLUSION

BASE: tree clean at `1402c8a` on master. 216 both orders both interpreters, CI green both legs.
Gate ledger: 0 refusals.

Ruled by D35 (r21 response): this runs NOW as its own small WO, independent of the `connect_fn`
threading WO and of pass two. Parallel-eligible.

SCOPE: §1–§5. Commit green, STOP.
SHIP IMPACT: **NO** — tests, conftest, evidence and docs only. `kraken_v2_book.py` must be
byte-unchanged at the end; report its sha256 before and after.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Where this order and the code disagree, the CODE WINS: STOP and report.
0.2 No monkeypatching to make a guard pass.
0.3 Every guard gets a fail-then-pass bite proof: four artifacts, `sha256` exact-restore.
0.4 Preservation duals mandatory, and **local and direct** — never pinned by a neighbouring
    branch.
0.5 Report every attempt, including failed and retried ones.
0.6 AUTO MODE OFF for any production file.
0.7 Report your `/context` reading; ask the user for it rather than estimating.
0.8 **BUILT-VS-OPERATED DECLARATION (ratified standing rule, D24).** Named Ops failure mode:
    *orders written to OPERATE a thing the order was implicitly supposed to BUILD.*

    | Thing | Status | Built & verified where |
    |---|---|---|
    | Gate ledger + `evidence/WO-024-PASS1/gate_ledger.txt` | **OPERATED** | Built WO-024 pass one §3, bite-proved, committed `b8f18b3` |
    | `test_clock_injection_gate` (carries the marker in §3) | **OPERATED** | Built WO-023 §2/§2b/§2c, 5 assertions / 4 mutations |
    | Marker-based exclusion mechanism | **THIS WO IS THE BUILDER** | Does not exist — see §3 |

    If any OPERATED row does not exist or is not verified as stated, **STOP and report.**

---

## §1 THE LEDGER ARITHMETIC DOES NOT CLOSE

The pass-one report states **41 gate invocations**, then accounts for `EARLY_RETURN` 34 +
`PROCEED_DECLARED` 1 + the guard test's 5 (`REFUSED_COUPLING`×2, `REFUSED_COHERENCE`×1,
`PROCEED_DECLARED`×1, `PROCEED_COHERENT`×1) = **40**. One invocation is unaccounted for.

Resolve it **from `evidence/WO-024-PASS1/gate_ledger.txt`, not from memory or recomputation.**
Either the 41 is a slip (correct it in the report and annotate the evidence file) or there is a
41st invocation nobody has named — report its nodeid and outcome.

Do not "fix" it by re-running and reporting whatever the new run says. The question is what the
committed evidence file contains.

---

## §2 THE SITES 29/30 LEDGER LINES — SHOWN, NOT ASSERTED

The pass-one report asserted these dispositions from the source, which the WO forbade. Extract
and paste the ACTUAL lines from the ledger file:

- site 29 `test_runner_resolves_live_adapter_from_data_source_via_factory`
  (test_live_capture.py:190) → expected `EARLY_RETURN` (no clock injected in pass one)
- site 30 `test_live_capture_refuses_non_live_capable_data_source` → expected **no gate
  invocation at all** (refuses at `LIVE_CAPTURE_UNSUPPORTED` before the gate)

If either differs from expectation, **STOP and report.** Note for context, not for action here:
site 29 is now known to be audit race **#5 of 30**, corpus-critical, and is blocked on the
`connect_fn` threading WO. Its pass-one disposition is still expected to be `EARLY_RETURN`
because pass one injected no clocks. **Do not migrate it. Do not inject a clock into it.**

---

## §3 THE MARKER-BASED EXCLUSION — THIS WO IS THE BUILDER (0.8)

This mechanism does not exist. It is subject to full build discipline (0.3, 0.4), not treated as
a configuration tweak on the existing ledger.

### The defect
The ledger's session-end assertion excludes the guard's own test **BY NAME**. A by-name exclusion
list inside a safety net is the shape that quietly grows until the net catches nothing — and D35
identified it as the structural fix for the class Finding 1 exposed: **a marker on the test is an
identifier that cannot truncate in transit**, unlike a name copied between documents.

### Build
Replace the by-name exclusion with an explicit marker a test must declare on itself, e.g.
`@pytest.mark.gate_refusal_expected`. Register it properly (no unknown-mark warnings under
`-W error` if that is the project's setting — check, don't assume).

The ledger's session-end check asserts BOTH directions:
1. **No refusal from an unmarkered test.** `REFUSED_COUPLING == 0` and `REFUSED_COHERENCE == 0`
   across every test that does NOT carry the marker.
2. **The marker set is exactly the tolerated set.** A test carrying the marker that produces NO
   refusal is also reported — a stale marker is a hole opening quietly, the same failure the
   by-name list had. Ops's call on whether a stale marker FAILS or WARNS: make it **FAIL**, and
   if that turns out to be impractical for a legitimate reason, STOP and report the reason
   rather than downgrading it silently.

State which tests carry the marker. Expected: exactly one (`test_clock_injection_gate`).

### Bite proof — four artifacts, sha256 exact-restore, BOTH directions (0.4)
The previous ledger bite proof is INVALIDATED by the mechanism change and must be re-run, not
cited.

- **Mutation A — refusal from an unmarkered test.** Take a migrated test, drop its `connect_fn`
  and module-patch the transport, inject an incoherent clock → the gate fires → the session-end
  assertion FAILS naming that nodeid. Note per pass one's 0.1 finding (b): under identity keying
  this fires **COHERENCE**, not COUPLING. The ledger records the actual outcome regardless of
  type; do not hard-code the expected refusal type in the assertion.
- **Mutation B — the stale-marker direction.** Add the marker to a test that produces no
  refusal → the session-end check FAILS on the stale marker. This is the preservation dual made
  **local and direct** rather than pinned by mutation A.
- Restore after each; `sha256` == pristine; final artifact PASS.

### Adopt the identifier form where it reaches
D35: adopt the marker as the enumeration-identifier form wherever it reaches. Do NOT retrofit
anything else in this WO — record in the report which other by-name enumerations exist in the
test tree (grep for name-matched lists in conftest, CI config, or tooling) so a later WO can be
written against a real list. **Enumerate, do not convert.**

---

## §4 DECISION LOG — RATIFIED VERBATIM, PLUS ONE SENTENCE

`docs/decisions/2026-07-24-an-enumeration-is-only-as-good-as-its-identifiers.md`:

> An enumeration is only as good as its identifiers. The WO-023 §1 audit's list was correct and
> complete; its entry for race #5 recorded a TRUNCATED test name, so a full-name grep returned
> nothing and the absence of a match was read as absence of the race. Standing consequence: a
> name-match against an enumerated list must match on the list's OWN identifier form (file+line,
> or a normalized/substring match), and a negative identifier-match is NOT a finding until the
> identifier form has been verified.
>
> Specimen: site 29, `test_runner_resolves_live_adapter_from_data_source_via_factory` — missed by
> full-name grep, found by file+line (test_live_capture.py:190, audit-era 197).
>
> The general rule underneath: **the strongest identifier is the one closest to the artifact —
> position beats name, marker beats position, content-hash beats marker.**

Record in the entry that it completes a family with *an audit without a denominator audits what
it noticed* and *a fact re-asserted from memory is a new claim, not a citation*: the three
failure modes of the project's own record-keeping — incomplete denominators, uncited recall,
unfaithful identifiers.

---

## §5 ANNOTATE, DO NOT DELETE (standing form)

The WO-024 closeout's §2 instructed comments at sites 29/30 stating the threading is "currently
NOT a blocker." That premise is INVERTED — site 29 is race #5 and the threading is a
prerequisite. Per D35, **annotate the original instruction rather than deleting it.**

In `progress.md`, append a dated annotation recording: the original instruction, that its premise
was inverted by the audit name-match, and that it re-issues after the `connect_fn` threading WO
lands. Do not write the comments at sites 29/30 in this WO.

Also record the sequence as ruled: **`connect_fn` threading WO → this WO (parallel-eligible) →
pass two (26 clock-injectable races, three `asyncio.sleep` races excluded BY ENUMERATION) →
`asyncio.sleep` investigation WO (default: resolve before corpus) → capture-loop baseline WO →
taxonomy migration → 008c → 24h corpus.**

---

## §6 SCOPE FENCE
- NO transport migration. NO clock injection. NO touching site 29 or 30's construction.
- NO `connect_fn` threading through the runner/registry — that is its own WO.
- NO gate docstring precision note. **That was r20's ruling 2 and has NOT been ruled.** If you
  believe it has, STOP and cite where.
- NO production logic changes of any kind.

---

## §7 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → **216 passed**, 0 f/xf/xp
- `pytest tests/ --randomly-seed=20260728 -rX` → same
- BOTH interpreters (3.11 strict, 3.14 dev)
- Marker mechanism live; marker set reported and asserted in both directions
- Bite proof RE-RUN under the marker mechanism: mutations A and B, four artifacts,
  sha256 exact-restore
- `kraken_v2_book.py` sha256 IDENTICAL before and after — paste both
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0
  · `preflight_path_check.py` pass
- Test count: state the arithmetic explicitly
- Commit, push, local == remote, CI green BOTH legs via `gh run view`
- Append a WO-025 block to `progress.md`

## §8 REPORT — `WO-025-REPORT.md`
The resolved 41-vs-40 arithmetic with the evidence-file lines; sites 29/30 ledger lines verbatim;
the marker mechanism, its registration, and which tests carry it; both bite-proof mutations with
sha256 lines; the by-name-enumeration inventory (enumerated, not converted); the decision log
entry as committed; the progress.md annotation; `kraken_v2_book.py` before/after sha256; the §7
gate output verbatim; every attempt; any STOP.

**THEN STOP.**