# WO-027 — connect_fn THREADING: INVESTIGATION AND PROPOSAL. NO IMPLEMENTATION.

**FRESH CLAUDE CODE SESSION — MANDATORY.** The prior session measured 68% at WO-026's START and
has since carried a full WO. No override on this one.

BASE: HEAD `4f18459` on master (local == remote). 216 both orders both interpreters,
CI green both legs (run 30092138390).

SCOPE: **INVESTIGATE, EXERCISE ONE TOOL, PROPOSE, STOP.** No production logic changes.
SHIP IMPACT: **NO.** `kraken_v2_book.py` must be byte-unchanged; report sha256 before and after
(expected `a9388694f0af3d46e596c5aeae50596a9d7ad02da6cc3dd69b3c8da8ea03379b`).

WHY THIS IS AN INVESTIGATION: D35 ruled the threading its own production WO before pass two. Ops
declines to specify the mechanism, because Ops cannot see the three layers and specifying from
recall is the failure mode already logged this week (*a fact re-asserted from memory is a new
claim, not a citation*). You propose from the code. This is the shape that produced the WO-023
foundation's three corrections, each of which overturned a ruling made without reading the file.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report.
0.2 No monkeypatching to make a guard pass.
0.3 Fail-then-pass bite proof for any guard: four artifacts, `sha256` exact-restore.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 AUTO MODE OFF for any production file. (Nothing in this WO should edit one.)
0.7 Report your `/context` reading at START and at the propose gate. Ask the user for it.
0.8 **BUILT-VS-OPERATED DECLARATION (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | `tools/snapshot_gate_ledger.py` | **OPERATED — NEVER YET EXECUTED** | Built WO-026 §2, committed `ef986dd`. §1 is its first real run. |
    | Gate ledger + `.artifacts/gate_ledger/` | **OPERATED** | WO-024 §3, WO-025 §3, WO-026 §2; path guard bite-proved `ef986dd` |
    | WO-023 §1 audit (the 30 races) | **OPERATED** | Committed `86e2a33` |
    | `LiveCaptureRunner` / `create_live_capture_feed` / `registry.create` | **OPERATED** | Pre-existing production |

    Any OPERATED row that does not exist or is not verified as stated → **STOP and report.**

---

## §1 CARRY-OVER — EXERCISE THE SNAPSHOT TOOL FOR REAL (first execution)

`tools/snapshot_gate_ledger.py` was built in WO-026 and **has never been run.** No snapshot
artifact exists. A tool that exists in the file and has never executed is the `_request_snapshot()`
shape, and this one is now the mechanism the entire evidence layer depends on.

Run a full suite (which writes a run-scoped ledger to `.artifacts/gate_ledger/`), then invoke the
tool to snapshot that ledger into `evidence/WO-027/`.

Report: the exact command, the resulting file path, and **the provenance header verbatim** —
commit sha, UTC timestamp, interpreter, seed/ordering, WO. Confirm all five fields are populated
with real values and none are placeholders or empty.

If the tool errors, produces an empty or malformed header, or writes anywhere unexpected:
**report it as a defect and STOP.** Do not fix it inline — a tool whose first execution fails is
a finding about WO-026's acceptance, not a chore.

Then confirm `git status --porcelain evidence/` shows ONLY the intended new snapshot — the WO-026
guard must still be holding.

---

## §2 THE INVESTIGATION — ENUMERATE THE THREE LAYERS FROM THE CODE

Paste **verbatim, with line numbers**, for each layer:

1. `LiveCaptureRunner` — its `__init__`, its `run()`, and the exact call at `live_capture.py:117`.
2. `create_live_capture_feed` — full signature and body, and the exact call at `factory.py:86`.
3. `registry.create` — full signature and body, plus how the registry is populated (what
   registers, and with what).

Then answer, from the code and not from reasoning about intent:

**2.1** Is `registry.create` GENERIC across adapters, or Kraken-specific? Enumerate **every**
adapter currently registered, with its constructor signature. Which of them accept a
transport-like seam today? (Expected: only `KrakenV2BookAdapter` has `_connect_fn`. Verify.)

**2.2** Does any layer resolve the transport, the clock, or any other seam from AMBIENT STATE —
module globals, environment variables, settings singletons, class attributes, or defaults
computed at import? Enumerate every such resolution across the three layers. D35 requires the
threaded seam be **constructor-injected at every layer it crosses, with no layer resolving from
ambient state**, so an existing ambient resolution anywhere on the path is in scope to report
even if it is not the transport.

**2.3** How many of the audit's 30 races route through `LiveCaptureRunner` / the factory /
the registry? Site 29 is known to. **Name every other one that does**, by file+line matched
against the audit's own identifier form — not by test name, per the ratified entry. If others
route through it, the threading unblocks more than one race and that changes pass two's shape.

**2.4** Does anything OUTSIDE the tests construct adapters through this path — production entry
points, CLI, the capture runner used for real captures? Name them. The threading must not change
behaviour for any of them.

---

## §3 THE DESIGN QUESTION YOU ARE PROPOSING AGAINST

If `registry.create` is generic, then threading a Kraken-specific `connect_fn` through it is an
architectural change to the Data layer's public surface, not a plumbing edit. The options Ops can
see, offered as a starting point and **not** as a menu you must pick from:

- **(a)** an explicit `connect_fn` parameter at each layer, passed through to the adapter —
  simple, but puts a venue-specific seam in a generic signature;
- **(b)** a generic `adapter_kwargs` mapping threaded through — flexible, but untyped and close
  to ambient;
- **(c)** the transport seam declared in the adapter protocol/interface so it is part of the
  contract every adapter satisfies rather than a special case;
- **(d)** something the code makes obvious that Ops cannot see from here.

**Introspecting which adapters accept `connect_fn` and passing it conditionally is INFERENCE and
is refused** — D34-3, and the gate's own doctrine: declared, never inferred.

Constraints any proposal must satisfy:
- constructor-injected at **every** layer it crosses; no layer resolves the transport from
  ambient state (D35);
- the gate's three-field observability must hold **at the runner boundary**, not only at the
  adapter's — a caller constructing through the runner must be as inspectable as one constructing
  the adapter directly;
- Principle VII: the venue swap must remain a single-module edit. State explicitly whether your
  proposal preserves that or erodes it. **If it erodes it, say so plainly** — that is a finding
  worth more than a clean-looking proposal.

---

## §4 PROPOSE AND STOP

Produce: the recommended mechanism, its diff shape (files and signatures, not applied), what it
costs, what it forecloses, and the acceptance criterion you would hold it to. Include the runner-up
option and why you rejected it.

Then **STOP.** Write no production code. Do not begin the implementation even if the proposal
seems obvious — this crosses a layer boundary and the lead rules on it.

If at any point the code contradicts something in this WO, **STOP at that point and report**
rather than reconciling. Three of the last four such stops overturned a ruling.

---

## §5 NAMED DEFERRED ITEM (record, do not act)

WO-026 §4.2 found **~12 hardcoded test nodeids across five tooling bite-proof scripts**
(`emission` 3, `instrument_mismatch` 1, `vocabulary_enforcement` 1, `vocabulary_scan` 4,
`wire_string` 3) — WO-025 had reported "exactly one" from a too-narrow search.

Record in `progress.md` as a NAMED item, not a footnote:
**WO-TBD — identifier hardening: convert tooling bite-proof scripts from hardcoded nodeids to the
marker/position identifier form** (per *an enumeration is only as good as its identifiers*:
position beats name, marker beats position, content-hash beats marker). State that it is not
currently blocking and what would make it block (any of those five scripts silently passing
because a renamed test no longer matches).

---

## §6 ACCEPTANCE (investigation WO — evidence and docs only)
- `pytest tests/ -p no:randomly -rX` → **216**, 0 f/xf/xp · `--randomly-seed=20260730` → same
- BOTH interpreters (3.11 strict, 3.14 dev)
- `git status --porcelain evidence/` shows ONLY the intended WO-027 snapshot + evidence files
- Gate ledger: 0 unmarkered refusals, 0 stale markers
- `kraken_v2_book.py` sha256 identical before/after — paste both
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0
  · `preflight_path_check.py` pass
- Test count unchanged at 216, arithmetic stated
- Commit the investigation evidence standalone (as WO-023 §1 did), push, local == remote,
  CI green BOTH legs via `gh run view`
- Append a WO-027 block to `progress.md`

## §7 REPORT — `WO-027-INVESTIGATION-REPORT.md`
The §1 snapshot command, path and verbatim provenance header; the three layers pasted with line
numbers; answers to 2.1–2.4 with evidence; the proposal with diff shape, cost, what it forecloses,
the Principle VII assessment, and the runner-up; the named deferred item as recorded; your
`/context` at start and at the gate; every attempt; any STOP.

**THEN STOP.** Implementation waits on a ruling.