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