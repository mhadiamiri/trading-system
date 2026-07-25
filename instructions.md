# WO-028 — connect_fn THREADING (production). D36: 1b scope, registration validation, full discipline.

**FRESH CLAUDE CODE SESSION — MANDATORY.** This is a production-module edit on the production import
path (D36 ruling 3). Do not continue a session that has carried prior WOs.

BASE: HEAD `401d01a` on master (local == remote). 216 both orders both interpreters,
CI green both legs (run 30108543326). `kraken_v2_book.py` sha256
`a9388694f0af3d46e596c5aeae50596a9d7ad02da6cc3dd69b3c8da8ea03379b`.

SCOPE: implement the threading, both paths (1b), with registration validation. Commit green, STOP.
SHIP IMPACT: **YES** — production, full discipline (D36-3). This is authorized.

WHAT WAS RULED (d36, do not relitigate):
- **1b** — the seam is constructor-injected at EVERY layer, on BOTH the live and non-live paths;
  the default is a DECLARED default parameter `connect_fn=_REAL_CONNECT` at the builder signature,
  NOT an ambient module-global reach at call time. Same value the code resolves today; different
  mechanism of holding it. The production socket path must be proven behaviourally unchanged.
- **2b** — declare the contract at registration: `register(live_capture=True)` validates that the
  builder accepts `connect_fn`, with an error message naming the contract and its reason. Option
  (c) (transport seam in the adapter protocol) is the named successor for when a second
  live-capable adapter appears — NOT built now.
- **3** — full production discipline. Hot-path re-baseline is a REASONED EXCLUSION (the builder
  runs once at construction, never per-frame), stated as such, not skipped.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins over this order: STOP and report. Four investigations of this
    shape have run; three overturned a ruling made without the file. This one has the file — but
    if the code still contradicts the ruling, STOP.
0.2 No monkeypatching to make a guard pass, and no monkeypatch left where a seam now exists —
    where a test can now inject `connect_fn`, it SHOULD, but that migration is pass two, not here.
    Do not migrate tests in this WO except the one §5 authorizes.
0.3 Fail-then-pass bite proof for the registration validation: four artifacts, `sha256`
    exact-restore.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt, including failed and retried.
0.6 **AUTO MODE OFF** for every production edit. `kraken_v2_book.py`, `factory.py`, `registry.py`,
    `live_capture.py` are all production.
0.7 Report your `/context` reading at START. Ask the user; do not guess.
0.8 **BUILT-VS-OPERATED DECLARATION (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | `_REAL_CONNECT` module capture | **OPERATED** | Built WO-023 §2b (`959e832`) — the gate's identity anchor |
    | `_assert_clock_transport_gate` (three-field) | **OPERATED** | WO-023 §2/§2b/§2c, 5 assertions / 4 mutations |
    | `register` / `_REGISTRY` / `is_live_capable` | **OPERATED** | Pre-existing registry (`registry.py`) |
    | `_build_kraken_v2` / `create_live_capture_feed` / `create_feed` / `LiveCaptureRunner` | **OPERATED** | Pre-existing production |
    | `connect_fn` threading + registration validation | **THIS WO IS THE BUILDER** | Does not exist — §2, §3 |

    Any OPERATED row not verified as stated → **STOP and report.** In particular: confirm
    `_REAL_CONNECT` is the SAME anchor the gate compares against, so the builder's declared default
    and the gate's identity test refer to one object. If they are two different captures of
    `websockets.connect`, that is a finding — report before proceeding.

---

## §1 FIRST — RE-PASTE THE FOUR SIGNATURES AS THEY ARE NOW

Before editing, paste verbatim with line numbers, from the current tree (not from WO-027's report,
which was a prior commit):
- `LiveCaptureRunner.__init__` and `_resolve_feed`
- `create_live_capture_feed` AND `create_feed` (both — 1b touches the non-live path)
- `_build_kraken_v2` (the `@register` builder) and the `register` decorator itself
- `KrakenV2BookAdapter.__init__`'s `connect_fn` / `monotonic_clock` seam, and `_REAL_CONNECT`

If any signature differs from WO-027's paste, note it. The base is the same commit, so they should
match; confirming closes the "written against its consumers" risk.

---

## §2 THE THREADING — BOTH PATHS (D36-1b)

Declared default, one value, every layer:

2.1 **Builder** (`_build_kraken_v2`, kraken_v2_book.py). Add `connect_fn=_REAL_CONNECT` to the
    builder signature and forward it: `KrakenV2BookAdapter(mode=mode, connect_fn=connect_fn, …)`.
    `_REAL_CONNECT` MUST be the gate's existing anchor — import/reference the same object, do not
    re-capture `websockets.connect` a second time. The builder's default is now DECLARED and equal
    to the value the adapter resolves ambiently today.

2.2 **Adapter constructor.** The adapter already has `connect_fn=None` resolving to
    `websockets.connect` at call time. Decide and state explicitly: does the adapter's default stay
    `None` (late-resolved) while the BUILDER supplies `_REAL_CONNECT`, or does the adapter's default
    also become `_REAL_CONNECT`? D36-1b is about the builder holding a declared default; the adapter
    seam already exists. **Recommended:** leave the adapter's `None` default untouched (it is the
    gate-observability seam and changing it risks the gate's `is _REAL_CONNECT` logic), and have the
    builder pass `_REAL_CONNECT` explicitly. State the consequence for the gate: a builder-constructed
    adapter now has `_connect_fn is _REAL_CONNECT` (not None), so the gate reads it as the REAL
    transport by identity — which is correct, it IS the real transport. Verify the gate still
    early-returns for it (no clock injected) rather than refusing.

2.3 **Factory, both functions.** `create_live_capture_feed(…, connect_fn=_REAL_CONNECT)` forwarding
    into `registry.create(…, connect_fn=connect_fn)`. AND `create_feed` — trace whether `create_feed`
    reaches `_build_kraken_v2`; if it does, it must forward the declared default too (1b: the
    non-live production path must hold the declared default, not resolve ambiently). If `create_feed`
    does NOT reach the kraken_v2 builder, state that and the point is moot for it — report which.

2.4 **Runner.** `LiveCaptureRunner.__init__(…, connect_fn=_REAL_CONNECT)`, stored, forwarded in the
    `_resolve_feed` `adapter is None` branch into `create_live_capture_feed`. The injected-adapter
    branch is unchanged (an injected adapter carries its own `connect_fn`).

2.5 **Registry.** `registry.create` stays generic `**kwargs` passthrough — NO change (D36 confirmed;
    WO-027 established it forwards verbatim).

**The value must be identical to today's resolved value at every layer.** No production caller
passing nothing may see a different transport than it does now. That is the whole point of "declared
default, same value."

---

## §3 THE REGISTRATION-TIME CONTRACT (D36-2b) — THIS WO IS THE BUILDER

`register(live_capture=True)` must validate, AT REGISTRATION (import time), that the decorated
builder accepts a `connect_fn` parameter. A live-capable builder without it is rejected the moment
it enters the system, not at a later forwarding `TypeError`.

- Inspect the builder's signature (`inspect.signature`) for a `connect_fn` parameter.
- On absence, raise at registration with a message that NAMES THE CONTRACT AND ITS REASON, verbatim
  shape: `LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN: builder <name> is registered live_capture=True
  but does not accept 'connect_fn'. Live-capable builders must accept connect_fn so the transport is
  a declared seam, not an ambient default — see D39 / Principle VII.`
  (Use whatever decision number the lead assigns; if unknown, cite "Principle VII" and leave the D-
  number as `D39` for the lead to confirm — flag it in the report.)
- `live_capture=False` (or unset) builders are NOT subject to the check.

### Bite proof — four artifacts, sha256 exact-restore, BOTH directions (0.3, 0.4)
- **Mutation A (refusal half):** a throwaway builder decorated `@register("x", live_capture=True)`
  with NO `connect_fn` param → registration RAISES the named error at import. Prove the message
  names the contract.
- **Mutation B (preservation half, local and direct):** the SAME throwaway builder WITH a
  `connect_fn` param → registers cleanly. And: a `live_capture=False` builder without `connect_fn`
  → registers cleanly (the check does not over-fire on non-live builders).
- Restore; sha256 == pristine; final artifact PASS.

State whether `_build_kraken_v2` — the real one — passes the check after §2 (it must; it now
accepts `connect_fn`). If it does not, §2 is incomplete.

---

## §4 PROVE THE PRODUCTION SOCKET PATH IS BEHAVIOURALLY UNCHANGED (D36-1b's burden)

D36 placed this burden explicitly. Two witnesses:

4.1 **The existing suite** — 216 unchanged, both orders, both interpreters. Any production caller
    passing nothing resolves the same transport it did at `401d01a`.
4.2 **One explicit new test** — assert that on the non-live production path, the default transport
    the adapter holds after construction through `create_feed`/`_build_kraken_v2` **is `_REAL_CONNECT`
    by identity**. This is the test D36 named: the declared default IS the real transport, proven by
    `is`, not by behaviour. Place it with the gate/identity tests. It is the +1 to the count.

Do NOT open a real socket to prove this. Construct through the production path and inspect
`adapter._connect_fn is _REAL_CONNECT`. If construction through that path tries to connect, STOP —
that is a finding about the builder doing I/O at construction, which it must not.

---

## §5 THE ONE AUTHORIZED TEST CHANGE

Race #5 (`test_runner_resolves_live_adapter_from_data_source_via_factory`, test_live_capture.py:190)
currently uses `patch("websockets.connect", …)` because no `connect_fn` seam reached the runner.
That seam now exists. **You MAY migrate race #5 to inject `connect_fn` through the runner and remove
the monkeypatch — but ONLY the transport migration, NO clock injection** (clock injection is pass
two). This proves the threading reaches the runner boundary end to end.

If migrating it requires anything beyond passing `connect_fn` through the runner, STOP and report —
that is a finding about the threading's completeness. Do NOT touch any other race. Do NOT inject a
clock into race #5; that is pass two and would trip nothing useful here.

State explicitly whether race #5, post-migration, still injects no clock and therefore still
early-returns at the gate. Its gate disposition must remain `EARLY_RETURN`.

---

## §6 RE-BASELINE — REASONED EXCLUSION (D36-3, do not skip the reasoning)
The standing rule's when-in-doubt-re-baseline default is ANSWERED, not ignored: the builder and the
threaded parameters execute ONCE at construction, never inside `get_live_market_data`'s per-frame
loop. The changed code is outside the loop's hot path by the rule's own boundary. **No re-baseline
is triggered.** State this as a reasoned exclusion in the report with the boundary cited; do not
silently omit it.

---

## §7 DECISION LOG — ONE ENTRY, RATIFIED VERBATIM
`docs/decisions/2026-07-24-scope-intentions-do-not-survive-a-shared-implementation.md`:

> A shared builder makes "the live path" and "the production path" the same edit — scope intentions
> do not survive a shared implementation. Ruling D36-1 existed only because one builder
> (`_build_kraken_v2`) serves both `create_live_capture_feed` and `create_feed`; a change scoped to
> "live" could not be confined to live without splitting the builder. General consequence: **scope
> claims are checked against the implementation's sharing topology, not the caller's intent** — the
> call-graph doctrine arriving at scoping decisions.

---

## §8 SCOPE FENCE
- NO clock injection anywhere (pass two).
- NO migrating any test except race #5's transport (§5).
- NO building option (c) / the adapter protocol seam (named successor, not now).
- NO touching `registry.create`'s passthrough.
- NO gate docstring precision note (r20 ruling 2 STILL unruled — STOP and cite if you disagree).

---

## §9 ACCEPTANCE
- `pytest tests/ -p no:randomly -rX` → **217** (216 + the §4.2 identity test), 0 f/xf/xp
- `pytest tests/ --randomly-seed=20260731 -rX` → same
- BOTH interpreters (3.11 strict, 3.14 dev)
- Registration validation live; bite proof mutations A + B, four artifacts, sha256 exact-restore
- `_build_kraken_v2` passes the registration check; stated
- §4.2 identity test green: non-live default `is _REAL_CONNECT`
- Race #5 migrated to `connect_fn`, monkeypatch removed, still `EARLY_RETURN` at the gate
- Gate ledger: 0 unmarkered refusals, 0 stale markers
- `lint-imports` 6/6 (runner still imports only `factory`, never `kraken_v2_book`) ·
  `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 ·
  `preflight_path_check.py` pass
- Test-count arithmetic stated: 216 + 1 (§4.2) = 217; race #5 migrated not added
- Commit, push, local == remote, CI green BOTH legs via `gh run view`
- Snapshot the gate ledger into `evidence/WO-028/` via `tools/snapshot_gate_ledger.py` (the WO-026
  discipline — deliberate snapshot, not an evidence-path write)
- Append a WO-028 block to `progress.md`

## §10 REPORT — `WO-028-REPORT.md`
The four signatures before/after; the `_REAL_CONNECT` single-anchor confirmation; the §2.2 adapter-
default decision and its gate consequence; whether `create_feed` reaches the kraken_v2 builder; the
registration validation and its bite proof verbatim with sha256; the §4.2 identity test; race #5's
migration and its retained `EARLY_RETURN`; the reasoned re-baseline exclusion; the ledger snapshot
path and provenance header; the §9 gate output verbatim; the D-number flag from §3; every attempt;
any STOP.

**THEN STOP.** §3 small WO / pass two follow, in fresh sessions.