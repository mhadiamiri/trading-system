# WO-028 — connect_fn THREADING (production) — REPORT

**Type:** production implementation (D36). **SHIP IMPACT: YES** — authorized (§0.6 AUTO MODE OFF honored;
every production edit made deliberately). **Base:** HEAD `f2ea05e` = `401d01a` (the WO's stated base) +
WO-027 docs-only close (no `src/` diff) — recorded as a base annotation, not a STOP.

**FRESH-SESSION OVERRIDE (recorded).** The WO header mandates a fresh session. This session had carried
WO-027. The user was told and directed **"resume with this session"** — an explicit override, logged as
the user's choice (as with WO-024/026/027).

**`/context` at START (§0.7):** **17%** (173.1k / 1M) — measured by the user immediately before the WO;
fresh after a `/compact`, well below the STOP threshold.

**Production files changed (sha256 after):**
| file | after |
|---|---|
| `kraken_v2_book.py` | `c98d7da0a34a428e700dbc645e7aff123dd1df13d90ae9c67d5223e55c16cdb6` (was `a9388694…`) |
| `factory.py` | `60cba127ce35c740d568610a9176a607c0b9f46ddc7c321ffce8029023db20a1` |
| `registry.py` | `c3db912ce02c178647419b7746073c9a947f7f0334f0334b54330fe61eecdc68` |
| `live_capture.py` | `50b08c62f3d08145024e4f9a2d018ee9f5ca948c6106cb548815b7a5567e2a94` |
| `logkit/decision.py` | `a65cfa3cfa10b160867e9481d2a6943fed4bb0c61e2d3463460181b2f9d199c4` (see §3 note) |

**Vocabulary declaration (required consequence of §3).** The new `LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN`
message is scanned as an emitted reason code by `tests/test_reason_code_vocabulary.py` (colon form), so
it MUST be declared in the reason-code vocabulary (`logkit/decision.py`) or the completeness guard fails
("EMITTED but NOT DECLARED"). It was declared next to the sibling `LIVE_CAPTURE_UNSUPPORTED`, prefix-free
(`LIVE_CAPABLE_` vs `LIVE_CAPTURE_` diverge at `CAPABLE`/`CAPTURE`). This surfaced as a real failure on the
first full-suite run (1 failed / 216 passed) and was fixed before acceptance — reported per §0.5.

---

## §0.8 — BUILT-VS-OPERATED + the single-anchor confirmation (verified before editing)

Every OPERATED row verified. **The single-anchor check (§0.8's named finding-trigger):**
`websockets.connect is kraken_v2_book._REAL_CONNECT` → **True**, and `websockets.connect` is a stable
object (`websockets.connect is websockets.connect` → True). So there is **ONE anchor**, referenced from
several names — not two different captures. The builder uses the module-local `_REAL_CONNECT` name; the
factory and runner reference the same object via `websockets.connect` (they cannot use the `_REAL_CONNECT`
*name* — see the import-boundary decision below), and every layer default is `is _REAL_CONNECT` (proven
in §2). No two-different-captures finding. No STOP at §0.8.

**Import-boundary decision (reported per §0.8 / §10).** import-linter contracts #3/#4/#5 forbid
`trading.loop` (the runner) from importing `trading.data.adapters.kraken_v2_book`, so the runner **cannot
reference `_REAL_CONNECT` by name**. It references the identical object via `import websockets` /
`websockets.connect`. The factory *could* import `_REAL_CONNECT` without tripping the linter (it is not a
guarded source module), but doing so would violate the factory's own architectural principle ("resolves
adapters by name through the registry; imports no concrete adapter module"), so it too references
`websockets.connect`. **This is not a "second capture" in the sense §0.8 warns about** — it is the same
object by identity, verified. The `_REAL_CONNECT` *name* lives in exactly one module (kraken_v2_book).

---

## §1 — THE FOUR SIGNATURES (before → after, current tree; matched WO-027's paste)

All four matched WO-027's paste (same base commit). Before → after:

1. **`LiveCaptureRunner.__init__`** (live_capture.py) — added `connect_fn=websockets.connect`; stored
   `self._connect_fn = connect_fn`. **`_resolve_feed`** `adapter is None` branch now forwards
   `connect_fn=self._connect_fn` into `create_live_capture_feed`. Injected-adapter branch unchanged.
2. **`create_live_capture_feed`** (factory.py) — added `connect_fn=websockets.connect`; forwarded
   `connect_fn=connect_fn` into the existing `registry.create(...)` call (safe: `is_live_capable` gates
   it so only the kraken_v2 builder is reached). **`create_feed`** — UNCHANGED (see §2.3).
3. **`_build_kraken_v2`** (kraken_v2_book.py) — added `connect_fn=_REAL_CONNECT`, forwarded as
   `KrakenV2BookAdapter(mode=mode, connect_fn=connect_fn)`. **`register`** (registry.py) — added the
   D36-2b validation (§3).
4. **`KrakenV2BookAdapter.__init__`** `connect_fn=None` / `monotonic_clock=None` seam — **UNTOUCHED**
   (§2.2 decision). `_REAL_CONNECT = websockets.connect` (kraken_v2_book.py:50) — UNTOUCHED (the anchor).

---

## §2 — THE THREADING (D36-1b), both paths

**2.1 Builder.** `_build_kraken_v2(…, connect_fn=_REAL_CONNECT)` → `KrakenV2BookAdapter(mode=mode,
connect_fn=connect_fn)`. The default is the module-local `_REAL_CONNECT` (the gate's anchor, not a
re-capture). This is the single point that converts the adapter's ambient-late-resolve into a declared
default held at construction; it serves **both** factory functions (they share this builder — §7).

**2.2 Adapter constructor — decision + gate consequence.** The adapter's `connect_fn=None` default is
**left untouched** (the WO's recommendation): it is the gate-observability seam, and the builder supplies
`_REAL_CONNECT` explicitly. **Consequence:** a builder-constructed adapter now has `_connect_fn is
_REAL_CONNECT` (not `None`). The gate reads it as the REAL transport by identity — which is correct, it
IS the real transport. **Verified the gate still EARLY-RETURNS for it** (no clock injected → the
`not (wall_injected or mono_injected)` early return at kraken_v2_book.py:2433–2434 fires *before* the
COUPLING check), so it does **not** refuse. **Behaviour is unchanged:** `_connect` resolves
`self._connect_fn or websockets.connect`, which is `_REAL_CONNECT or websockets.connect` = `_REAL_CONNECT`
= the same object it resolved when `_connect_fn` was `None`. Only the *held value* changed None →
_REAL_CONNECT; the resolved socket is identical.

**2.3 Factory — both functions.** `create_live_capture_feed` gains `connect_fn` and forwards it (safe:
`is_live_capable` restricts the path to the kraken_v2 builder). **`create_feed` reaches `_build_kraken_v2`
only when `DATA_SOURCE == "kraken_v2"`** (its default is `"simulated"`); it dispatches generically over
`DATA_SOURCE`. **It must NOT — and does not — forward `connect_fn`:** `registry.create` is generic, and
the `simulated`/`kraken_public` builders do not accept `connect_fn` (verified: their signatures are
`(decision_logger)` only) → forwarding would `TypeError`. **1b is still satisfied on the non-live path**
because the declared default lives in the *shared builder*: `create_feed` → `registry.create("kraken_v2")`
→ `_build_kraken_v2()` (no `connect_fn` passed) → the builder's declared `_REAL_CONNECT` default applies →
the adapter holds `_REAL_CONNECT` (declared at construction, not ambient at call time). Verified:
`create_feed()` under `DATA_SOURCE=kraken_v2` yields an active feed with `_connect_fn is _REAL_CONNECT`.
This is the §7 decision-log fact (shared builder = shared edit).

**2.4 Runner.** `connect_fn=websockets.connect` (the anchor object; cannot name `_REAL_CONNECT` per the
import boundary), stored, forwarded in the `adapter is None` branch. Injected-adapter branch unchanged.

**2.5 Registry.** `registry.create` unchanged — generic `**kwargs` passthrough.

**Single-anchor proof (all layer defaults `is _REAL_CONNECT`):** builder default ✓, `create_live_capture_feed`
default ✓, `LiveCaptureRunner.__init__` default ✓, `registry.create("kraken_v2")._connect_fn` ✓,
`create_feed()` active-feed `_connect_fn` ✓ — all `is kraken_v2_book._REAL_CONNECT`.

---

## §3 — REGISTRATION-TIME CONTRACT (D36-2b)

`register(live_capture=True)` now validates at import time (via `inspect.signature`) that the builder
accepts `connect_fn`; absence raises **`LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN`** naming the contract and
its reason (D39 / Principle VII). `live_capture=False` builders are not checked.

**D-NUMBER FLAG (§3):** the message cites **`D39`** as the WO instructed ("leave the D-number as D39 for
the lead to confirm"). **The lead should confirm or reassign D39.**

**The real `_build_kraken_v2` passes the check** (it now accepts `connect_fn`) — verified: `kraken_v2`
registers and `is_live_capable("kraken_v2")` is True at import.

**Bite proof** — `evidence/WO-028/registration_validation_bite_proof.txt`, four artifacts, sha256
exact-restore of `registry.py` (BEFORE == AFTER == `c3db912c…`), both directions:
- **A1 (pristine):** REFUSAL — a throwaway `live_capture=True` builder with no `connect_fn` raises the
  named error; PRESERVATION — the same builder *with* `connect_fn` registers cleanly, and a
  `live_capture=False` builder without `connect_fn` registers cleanly (no over-fire).
- **A2 (necessity):** the guard weakened (`if live_capture and …` → `if False and …`) → the bad builder
  **REGISTERS SILENTLY** (proving the guard, not Python arg-binding, enforces the contract).
- **A3 (restored):** the bad builder raises again. **A4:** sha256 IDENTICAL: YES. **VERDICT: PASS.**

---

## §4 — PRODUCTION SOCKET PATH BEHAVIOURALLY UNCHANGED (D36-1b's burden)

**4.1** The existing suite is 216 unchanged (see §9) — every production caller passing nothing resolves
the same transport it did at `401d01a` (`_connect` resolves `_REAL_CONNECT or websockets.connect` =
`_REAL_CONNECT`, identical to the pre-WO `None or websockets.connect`).

**4.2 The +1 identity test** — `tests/integration/test_clock_injection_gate.py::
test_nonlive_production_default_transport_is_real_connect_by_identity`: constructs through the non-live
production dispatch (`registry.create("kraken_v2")`, and the shared `_build_kraken_v2()` directly) and
asserts `adapter._connect_fn is kv2._REAL_CONNECT`. **Construction only — no socket opened** (if the path
tried to connect, the test would hang/error, which is itself the alarm the WO named). Green on both
interpreters.

---

## §5 — THE ONE AUTHORIZED TEST CHANGE (race #5)

`test_runner_resolves_live_adapter_from_data_source_via_factory` migrated: `patch("websockets.connect",
conn.connect)` **removed**; the transport is now injected as `LiveCaptureRunner(…, connect_fn=conn.connect)`
and threaded through the runner → factory → builder to the adapter. Nothing beyond passing `connect_fn`
through the runner was required (no STOP). **No clock injected** (pass two). **Gate disposition unchanged:
still `EARLY_RETURN`** — the migrated adapter has no clock (`_wall_clock is None`, `_monotonic_clock is
time.monotonic`), so the gate early-returns before the COUPLING check; confirmed in the gate ledger (§9).
No other race touched.

---

## §6 — RE-BASELINE: REASONED EXCLUSION (D36-3)

The when-in-doubt-re-baseline default is **answered, not skipped**: the builder and the threaded
parameters execute **once at construction**, never inside `get_live_market_data`'s per-frame loop. The
changed code is outside the loop's hot path by the standing rule's own boundary (the per-frame emission
loop). **No re-baseline is triggered.** The mean-cycle baseline governs UNIFORM drift measured per-frame;
nothing per-frame changed (`_connect` resolves the identical object as before).

---

## §7 — DECISION LOG
`docs/decisions/2026-07-24-scope-intentions-do-not-survive-a-shared-implementation.md` — ratified verbatim
(the shared-builder / sharing-topology consequence; the call-graph doctrine arriving at scoping).

---

## §8 — SCOPE FENCE (honored)
No clock injection anywhere. No test migrated except race #5's transport. Option (c) / adapter-protocol
seam NOT built (named successor). `registry.create` passthrough untouched. No gate docstring precision
note (r20 ruling 2 still unruled — not added).

---

## §9 — ACCEPTANCE

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest tests/ -p no:randomly -rX` | **217** | **217** |
| `pytest tests/ --randomly-seed=20260731 -rX` | **217** | **217** |

(3.11 strict `CPython 3.11.15` via scratchpad venv; 3.14 dev `CPython 3.14.6`. Each 246s, 0 f/xf/xp. Gate
ledger 41 invocations, 0 unmarkered refusals, 0 stale markers on every leg; snapshots in `evidence/WO-028/`.)

- **Test-count arithmetic:** 216 (base) + 1 (§4.2 identity test) = **217**; race #5 migrated, not added;
  the registration bite proof is a standalone `tools/` instrument (not a suite test).
- Registration validation live; bite proof A+B, four artifacts, sha256 exact-restore (§3).
- `_build_kraken_v2` passes the registration check (stated, §3).
- §4.2 identity test green: non-live default `_connect_fn is _REAL_CONNECT`.
- Race #5 migrated to `connect_fn`, monkeypatch removed, still `EARLY_RETURN` (§5, §9 ledger).
- Gate ledger: **0 unmarkered refusals, 0 stale markers** (snapshot `evidence/WO-028/`).
- `lint-imports` **6/6** (runner imports only `factory`/`websockets`, never `kraken_v2_book`) ·
  `contract_count_check.py` **6/6** · `ruff` **clean** · `annotation_name_scan.py` **0** ·
  `preflight_path_check.py` **pass**.
- Commit, push, local == remote, CI green BOTH legs — run `_[fill]_`.

---

## §10 REPORT ITEMS / STOPPED / attempts
- **`_REAL_CONNECT` single-anchor:** confirmed (§0.8). **§2.2 adapter-default decision:** left `None`;
  gate consequence stated + early-return verified. **`create_feed` reaches the kraken_v2 builder?** yes,
  only under `DATA_SOURCE=kraken_v2`; it does not/‑cannot forward `connect_fn` (generic dispatch); 1b held
  at the shared builder (§2.3). **D-number flag:** D39, lead to confirm (§3).
- **STOPPED at:** the fresh-session mandate (reported; user overrode). No in-implementation STOP: the
  import boundary constrained *how* the anchor is referenced (`websockets.connect`, identical object) but
  did not contradict the ruling; race #5 migrated with nothing beyond the runner seam.
- **Attempts:** the `factory._REAL_CONNECT` named constant was written then reverted in favour of
  referencing `websockets.connect` inline, to avoid the appearance of a second anchor (one retried edit,
  reported per §0.5). Bite proof passed first run. Targeted tests (gate + live_capture) green before the
  full suite.
- **Changed but not asked?** Production: `registry.py`, `kraken_v2_book.py` (builder only), `factory.py`,
  `live_capture.py`, and `logkit/decision.py` (the required vocabulary declaration for the §3 code —
  discovered by the vocabulary guard, not anticipated by the WO; a necessary consequence of introducing
  the code). Tests: race #5 migration + the §4.2 identity test. New: `tools/registration_validation_bite_proof.py`,
  the decision log, `evidence/WO-028/`, this report, `progress.md`. No production logic beyond the seam +
  its declaration.
