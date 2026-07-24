# WO-027 — connect_fn THREADING: INVESTIGATION AND PROPOSAL — REPORT

**Type:** INVESTIGATION. **No production code written.** Implementation waits on a ruling (§4).
**Base:** HEAD `e3533bf` = `4f18459` (the WO stated base) + WO-026 docs-only close (WO-026-REPORT.md,
one evidence file, progress.md — **no `src/` changes**; verified `git diff --name-only 4f18459 e3533bf`).
Recorded as a base annotation, not a STOP: code is identical to the stated base.
**Ship impact: NO.** `kraken_v2_book.py` sha256 `a9388694f0af3d46e596c5aeae50596a9d7ad02da6cc3dd69b3c8da8ea03379b`
**before AND after** (pasted again in §6).

**FRESH-SESSION OVERRIDE (recorded).** The WO header mandates a fresh session ("No override on this
one"). This session had carried WO-026. The user was told this explicitly and directed **"resume with
this session"** — an explicit override of the WO's text, logged here as the user's choice, exactly as
prior fresh-session directives (WO-024, WO-026) were.

**`/context` readings (§0.7):** **requested from the user at START and again at the propose gate; not
supplied** (the user's only input this session was "resume with this session"). Recorded as unsupplied
rather than guessed — the harness does not expose the reading to me. For situational context: this
session had already carried WO-026 to completion (the reason the WO mandated a fresh one), i.e. it is
materially past the ~70% §0.7 STOP threshold — which is precisely why the WO demanded a fresh session
and why this is logged as an explicit user override.

---

## §0.8 — BUILT-VS-OPERATED (D24), verified before any work

| Thing | Declared | Verified this WO |
|---|---|---|
| `tools/snapshot_gate_ledger.py` | OPERATED — NEVER YET EXECUTED | **§1: first real execution — PASSED.** No defect. |
| Gate ledger + `.artifacts/gate_ledger/` | OPERATED | Present in `conftest.py`; guard held (§1 `git status` clean). |
| WO-023 §1 audit (the 30 races) | OPERATED (`86e2a33`) | `evidence/WO-023/wall_clock_race_audit.txt`, 104 lines, read verbatim (§2.3). |
| `LiveCaptureRunner` / `create_live_capture_feed` / `registry.create` | OPERATED (pre-existing) | All three located and pasted (§2). |

No OPERATED row failed to verify → no STOP at §0.8.

---

## §1 — SNAPSHOT TOOL, FIRST REAL EXECUTION

**Command:**
```
python tools/snapshot_gate_ledger.py --wo WO-027 --order deterministic \
    --name gate_ledger_3.14_deterministic.txt
```
(run after a full 3.14 deterministic suite wrote `.artifacts/gate_ledger/latest.txt`)

**Resulting file:** `evidence/WO-027/gate_ledger_3.14_deterministic.txt`

**Provenance header (verbatim):**
```
==============================================================================
PROVENANCE (WO-026 §2 deliberate snapshot) — taken by WO-027
  commit:      e3533bf
  taken (UTC): 2026-07-24T15:59:38Z
  interpreter: CPython 3.14.6
  ordering:    deterministic   seed: unspecified
  source:      C:\Projects\bot\trading-system\.artifacts\gate_ledger\latest.txt
This is a DELIBERATE copy of a run-scoped .artifacts/ ledger. The test session never writes
here (WO-026 §2, mechanically enforced in conftest.py::_assert_ledger_dir_outside_evidence).
==============================================================================
```

**Five fields — all populated with real values, no placeholders:**
- commit: `e3533bf` (real, matches HEAD) · UTC: `2026-07-24T15:59:38Z` (real) · interpreter:
  `CPython 3.14.6` (real) · ordering: `deterministic` (real) · WO: `WO-027` (real, in the header line).
- seed reads `unspecified` — this is **accurate, not a placeholder**: a `-p no:randomly` run has no
  seed. To demonstrate the seed field ALSO populates with a real value, a **second** snapshot was taken
  from the randomized run (`--seed 20260730`) → `evidence/WO-027/gate_ledger_3.14_randomized.txt`
  (header shows `seed: 20260730`).

**Ledger content:** Total gate invocations 41; SUITE-WIDE EARLY_RETURN 35 / PROCEED_COHERENT 1 /
PROCEED_DECLARED 2 / REFUSED_COUPLING 2 / REFUSED_COHERENCE 1; the guard test contributes 6 invocations
(the sixth EARLY_RETURN) — **consistent with WO-025/WO-026 §1**. Unmarkered refusals: `[]`. Stale
markers: `[]`. (§6: 0 unmarkered refusals, 0 stale markers.)

**Guard still holding:** after the full suite run, `git status --porcelain evidence/` showed ONLY
`?? evidence/WO-027/` — the instrument wrote to `.artifacts/` only; nothing under `evidence/` was
touched by the test session. **No defect. No STOP.** The tool works on first execution.

---

## §2 — THE THREE LAYERS (verbatim, with line numbers)

### Layer 1 — `LiveCaptureRunner` (`src/trading/loop/live_capture.py`)

`__init__` (lines 42–73):
```python
42      def __init__(
43          self,
44          persist_path,
45          duration_seconds: float,
46          trading_env: Optional[str] = None,
47          adapter: Optional[Any] = None,     # injected by tests; production resolves via factory
48          loop: Optional[LiveTradingLoop] = None,
49          clock=None,
50          data_source: Optional[str] = None,
51      ) -> None:
...
62          self._persist_path = persist_path
63          self._duration_seconds = duration_seconds
64          if trading_env is None:
65              import os
66              trading_env = os.environ.get("TRADING_ENV")
67          self._trading_env = trading_env
68          self._adapter = adapter
69          self._loop = loop
70          self._clock = clock or time.time
71          self._data_source = data_source
72          self._mean_cycle_baseline = None   # WO-016 §D28: set by _preflight from the host store
73          self._preflight()
```
`_resolve_feed` (lines 109–119) — where the factory call lives:
```python
109     def _resolve_feed(self):
...
112         if self._adapter is not None:
113             adapter = self._adapter
114             adapter._gap_persist_path = str(self._persist_path)
115             # _persistence_optional stays False: the adapter is the second line of the refusal.
116             return adapter, adapter.get_live_market_data(self._duration_seconds)
117         return factory.create_live_capture_feed(
118             self._persist_path, self._duration_seconds, data_source=self._data_source,
119         )
```
`run()` (lines 121–177) constructs nothing venue-specific; it calls `self._resolve_feed()` (line 124)
and later injects the host-scoped baseline onto the adapter by private attr (line 128:
`adapter._mean_cycle_baseline_s = self._mean_cycle_baseline`).

**The exact call at `live_capture.py:117`:** `return factory.create_live_capture_feed(...)` — reached
ONLY when `self._adapter is None`. When a test injects an adapter, the factory is bypassed (line 116).

### Layer 2 — `create_live_capture_feed` (`src/trading/data/adapters/factory.py`, lines 53–93)
```python
53  def create_live_capture_feed(
54      persist_path,
55      duration_seconds: float,
56      decision_logger: DecisionLogger | None = None,
57      data_source: str | None = None,
58  ):
...
78      global _active_feed
79      name = data_source if data_source is not None else Settings.DATA_SOURCE
80      if not registry.is_live_capable(name):
81          raise ValueError(
82              f"LIVE_CAPTURE_UNSUPPORTED: adapter {name!r} does not support live capture. "
83              f"Set DATA_SOURCE to a live-capable adapter (e.g. 'kraken_v2'). Refusing before "
84              f"opening any connection."
85          )
86      feed = registry.create(
87          name,
88          decision_logger=decision_logger,
89          mode="live",
90          gap_persist_path=str(persist_path),
91      )
92      _active_feed = feed
93      return feed, feed.get_live_market_data(duration_seconds)
```
**The exact call at `factory.py:86`:** `feed = registry.create(name, decision_logger=..., mode="live",
gap_persist_path=...)`. It passes **no** transport or clock seam. The signature has no `connect_fn`.

### Layer 3 — `registry.create` (`src/trading/data/adapters/registry.py`, lines 48–54)
```python
48  def create(name: str, **kwargs):
49      """Resolve and construct an adapter by its registered config name."""
50      if name not in _REGISTRY:
51          raise ValueError(
52              f"Unknown data source: {name!r}. Registered: {registered_names()}"
53          )
54      return _REGISTRY[name](**kwargs)
```
**`registry.create` is GENERIC** — it looks the builder up by name in the module-global `_REGISTRY`
(lines 19, 28–40 populate it via the `@register` decorator) and forwards `**kwargs` **verbatim**. It
already threads adapter-specific kwargs (`mode`, `gap_persist_path`) untouched. It needs **no change**
to carry a `connect_fn` — the choke point is the builder, not the registry.

**How the registry is populated:** importing `trading.data.adapters` (`__init__.py`) imports every
adapter module, each of which self-registers at module scope:
- `@register("kraken_public")` → `_build_kraken_public(decision_logger=None)` (kraken_public.py:338)
- `@register("kraken_v2", live_capture=True)` → `_build_kraken_v2(decision_logger=None,
  mode=…MODE_FIXTURE, gap_persist_path=None)` (kraken_v2_book.py:3084) — **builds
  `KrakenV2BookAdapter(mode=mode)`, dropping `connect_fn`/`monotonic_clock`.**
- `@register("simulated")` → `_build_simulated(decision_logger=None)` (simulated_feed.py:110)

---

## §2.1 — Is `registry.create` generic? Every adapter + its constructor.

**Generic.** `create(name, **kwargs)` is adapter-agnostic. Every registered adapter:

| name | builder (signature) | adapter constructor | transport seam today? |
|---|---|---|---|
| `simulated` | `_build_simulated(decision_logger=None)` | `SimulatedMarketFeed(update_interval_ms=1000)` | none (no socket) |
| `kraken_public` | `_build_kraken_public(decision_logger=None)` | `KrakenPublicFeed(decision_logger, reconnect_base_delay=1.0, reconnect_max_delay=60.0)` | **NO seam** — hardcodes `websockets.connect(self.WS_URL)` (kraken_public.py:103) |
| `kraken_v2` | `_build_kraken_v2(decision_logger, mode, gap_persist_path)` | `KrakenV2BookAdapter(mode=MODE_FIXTURE, *, monotonic_clock=None, connect_fn=None)` (:1054) | **YES — `connect_fn`** (only this one) |

**Only `KrakenV2BookAdapter` has `_connect_fn`. Verified.** Note the *builder* `_build_kraken_v2` does
**not** expose it — it constructs `KrakenV2BookAdapter(mode=mode)`, so the seam the adapter offers is
**unreachable through the registry today**. (Secondary finding: `KrakenPublicFeed` opens a *real* socket
with **no** injectable seam at all — but it is not `live_capture`, so it never reaches
`create_live_capture_feed`; out of scope for this threading, recorded for the record.)

## §2.2 — Ambient-state resolutions across the three layers (D35 scope)

D35 requires the threaded seam be constructor-injected at every layer, **with no layer resolving from
ambient state.** Enumerated ambient resolutions on this path today:

1. **Runner** — `trading_env` from `os.environ.get("TRADING_ENV")` when `None` (live_capture.py:64–66):
   env var, read at construction.
2. **Runner** — `self._clock = clock or time.time` (line 70): constructor seam with a module-attribute
   **default** (ambient fallback to `time.time`).
3. **Runner** — mean-cycle baseline via `host_baseline.load_baseline()` (line 98), a host-scoped store
   on disk, then injected onto the adapter at `run()` (line 128). Ambient (host store) → adapter.
4. **Factory** — `name … else Settings.DATA_SOURCE` (factory.py:79; also `create_feed` line 45):
   `Settings.DATA_SOURCE` is a settings-singleton class attribute **computed from `os.getenv` at import**
   (config/settings.py:32–33). Doubly ambient (singleton + env at import).
5. **Registry→builder→adapter (THE transport, and it is in scope):** because `_build_kraken_v2` drops
   `connect_fn`, every registry-built adapter has `_connect_fn = None`, so the adapter resolves the
   transport from the **module global** at call time — `connect_fn = self._connect_fn or
   websockets.connect` (kraken_v2_book.py:2210; gate mirror at :2439) — and the clock from `time.monotonic`
   (default). **On the sole production-shaped construction path (factory→registry), the transport is
   resolved from ambient state by construction.** This is exactly the D35 condition the threading closes.

## §2.3 — How many of the 30 races route through the runner / factory / registry?

**Exactly one.** Method: no test calls `create_live_capture_feed`, `registry.create`, or `create_feed`
directly (grep over `tests/` — zero hits). The factory/registry path is reached **only** via
`LiveCaptureRunner(adapter=None, …)`; with an injected adapter, `_resolve_feed` returns it and bypasses
the factory (live_capture.py:112–116). Matching each of the 30 audit races (by the audit's own
file+line+identifier form) against its runner construction:

- **Race #5** — `test_live_capture.py:197 test_runner_resolves_live_adapter_from_data_source`
  (current name `…_via_factory`, def now at :190; the "site 29" already known) — constructs
  `LiveCaptureRunner(adapter=None, data_source="kraken_v2")` (:195). **ROUTES THROUGH factory →
  registry → `_build_kraken_v2`.** It injects **no** clock, so the gate early-returns, and it relies on
  `patch("websockets.connect", conn.connect)` (:198) to avoid a real socket — i.e. it substitutes the
  transport via **ambient monkeypatch** precisely because no `connect_fn` seam reaches the factory path.
- **Races #1–#3** (`test_live_capture.py:59/98/114`) — use the runner but inject a directly-constructed
  `KrakenV2BookAdapter(connect_fn=factory.connect)` (:69/101/118). Factory **bypassed**.
- **Race #4** (`test_live_capture.py:140`, dual) — no runner at all; calls
  `adapter.get_live_market_data(...)` on a directly-constructed adapter. Factory **bypassed**.
- **All other 25 races** (test_gap_recording, test_host_suspend, test_keepalive, test_failure_cap,
  test_failure_capture, test_protocol_ping, test_throughput, test_reconnect_to_effect,
  test_venue_close_path, test_backoff_breaker, test_pong_observer, test_lag_sampler) — construct
  `KrakenV2BookAdapter` (or call `get_live_market_data`) **directly**; `LiveCaptureRunner` appears in
  none of them. Factory **not reached**.

**Consequence for pass two.** The finding **confirms** the WO's expectation (site 29 is the one) and
does **not** change pass two's shape: the other 29 races already inject `connect_fn` directly, so they
need no factory threading. But the linkage is the point — **race #5 cannot be made clock-deterministic
in pass two without this threading.** Injecting a clock into race #5 (to close it) trips the gate's
**COUPLING** refusal (kraken_v2_book.py:2440) unless a non-real transport is injected too; and today
the runner offers no way to inject `connect_fn`. Monkeypatching `websockets.connect` sidesteps COUPLING
but is the patch-based mitigation the doctrine refuses. **So `connect_fn` threading is the strict
prerequisite for closing race #5.**

## §2.4 — Does anything OUTSIDE tests construct adapters through this path?

**The live-capture path: nothing.** `LiveCaptureRunner` is constructed only in tests (grep `src/` +
`tools/`: the only hit is its own `class` definition). `create_live_capture_feed` is called only by
`live_capture.py:117`. So threading `connect_fn` through the **live** path changes behaviour for **zero
production callers** — it is test-facing today (consistent with the runner's docstring: "has never held
a real socket").

**The non-live path DOES have production callers, and must stay untouched:** `create_feed` →
`registry.create(data_source)` (default mode) is used by production `LiveTradingLoop`
(`trading/loop/live.py:132`), reachable via `trading/loop/live.py:378 main()` and
`tools/establish_mean_cycle_baseline.py:175`. The proposal must **not** alter `create_feed` or
`registry.create`'s behaviour for these. (It does not: the seam rides only on `create_live_capture_feed`
and the `kraken_v2` builder; `registry.create` stays a generic passthrough.)

---

## §3 / §4 — THE PROPOSAL

**Recommended mechanism — Option (a), scoped to the live path.** Thread an explicit, keyword-only
`connect_fn=None` from the runner through the factory to the `kraken_v2` builder to the adapter
constructor; **`registry.create` is unchanged** (its generic `**kwargs` already forwards it).

**Diff shape (files + signatures — NOT applied):**

1. `src/trading/loop/live_capture.py`
   - `LiveCaptureRunner.__init__(..., data_source=None, connect_fn=None)` — store `self._connect_fn`.
   - `_resolve_feed()` (the `adapter is None` branch, line 117): pass `connect_fn=self._connect_fn` into
     `factory.create_live_capture_feed(...)`.
   - The injected-adapter branch (line 112–116) is unchanged (a test injecting an adapter already sets
     its `connect_fn` at construction).
2. `src/trading/data/adapters/factory.py`
   - `create_live_capture_feed(persist_path, duration_seconds, decision_logger=None, data_source=None,
     connect_fn=None)` — forward `connect_fn=connect_fn` in the existing `registry.create(...)` call
     (line 86). `create_feed` (the fixture/sim production path) is **not** touched.
3. `src/trading/data/adapters/kraken_v2_book.py` — the `_build_kraken_v2` builder ONLY (NOT the adapter
   class): `_build_kraken_v2(decision_logger=None, mode=…MODE_FIXTURE, gap_persist_path=None,
   connect_fn=None)` → `KrakenV2BookAdapter(mode=mode, connect_fn=connect_fn)`.
   *(Note: this touches the file `kraken_v2_book.py`, but only its registry builder function, not the
   adapter's own logic. Whether the lead counts the builder as "production logic" is a ruling input;
   the adapter class body is untouched either way.)*
4. `src/trading/data/adapters/registry.py` — **no change.**

**Why this and not the alternatives:**
- The venue-specific seam lands only in venue-specific places: `create_live_capture_feed` is already a
  live-only, `is_live_capable`-gated function (a non-live source refuses at line 80 *before* any
  builder is reached), and `_build_kraken_v2` is already the Kraken builder. `connect_fn` on them is a
  live-capture-transport parameter on the live-capture surface — **not** generic-signature pollution.
- **Runner-boundary observability (§3 constraint) is satisfied exactly.** Threading `connect_fn` all
  the way to the adapter constructor means the gate (`_assert_clock_transport_gate`, which inspects
  `self._connect_fn`) sees the injected transport identically whether the adapter was built through the
  runner or directly. A runner-constructed adapter becomes as inspectable as a directly-constructed one
  — and, crucially, race #5 can then inject a clock+transport and pass COUPLING **without**
  `patch("websockets.connect")`.
- **Import-linter contracts #4/#5 preserved:** the runner still imports only `factory` (never
  `kraken_v2_book`); `registry` remains the sole resolution path. (`connect_fn` is a plain callable
  passed as data — no concrete-adapter import crosses the boundary.)

**Runner-up — Option (c), transport seam in the adapter protocol** — rejected **for now**, named for
later. Declaring transport injection in a shared adapter contract is the *more correct* end-state and is
what should be adopted the moment a **second** live-capable adapter appears. Rejected now because there
is exactly one live adapter; a protocol is upfront surface (define it, retrofit `kraken_v2`, and every
future adapter must satisfy it) with no present payoff. Option (a) forecloses nothing here — (c) is its
natural successor.

**Rejected — Option (b), generic `adapter_kwargs` mapping** — it is untyped and, worse, it makes the
runner boundary **less** inspectable (the runner signature would not name `connect_fn`; you would pass
an opaque dict), which **fails the §3 runner-boundary-observability constraint** directly. Rejected on
that constraint, not merely on taste.

**Cost.** Three signatures gain a `None`-default keyword; one builder line forwards it; ~6–10 lines,
no behaviour change for any existing caller (all defaults preserve today's paths). One new test would
inject `connect_fn` through the runner and assert the gate sees it (replacing race #5's
`patch("websockets.connect")`).

**What it forecloses.** It sets an **implicit contract**: any *future* `live_capture=True` builder must
accept `connect_fn` or `create_live_capture_feed` will `TypeError` when forwarding it. That contract is
today undeclared — the honest weakness of (a), and the exact seam where (c) takes over.

**Principle VII (venue swap = single-module edit) — assessment, stated plainly.** The proposal
**preserves** the single-module-edit property in the mechanical sense: a new venue is still "add one
adapter module (with its `@register` builder), name it in config, nothing else moves" — the builder
that must accept `connect_fn` lives inside that same new module. **But it mildly erodes the "declared,
never inferred" spirit:** the requirement that a live-capable builder accept `connect_fn` is implicit
(enforced only by a runtime `TypeError`), not declared at the registration boundary. **I flag this as a
finding, not a clean bill:** if the lead wants the contract explicit, that is Option (c) (or, minimally,
having `register(live_capture=True)` document/validate the builder's `connect_fn` parameter) — and that
is the ruling this WO surfaces rather than resolves.

**Acceptance criterion I would hold the implementation to:**
- Race #5 (`…_resolves_live_adapter_from_data_source_via_factory`) injects `connect_fn` **through the
  runner** and **removes** `patch("websockets.connect")`; the gate sees the injected transport at the
  adapter boundary (three-field observability at the runner boundary).
- The other 29 races unchanged; the 25 non-runner races untouched.
- `create_feed` / `LiveTradingLoop` / `registry.create` behaviour identical; import-linter 6/6.
- Production default (`connect_fn=None`) → adapter still resolves the real `websockets.connect` (a real
  capture opens a real socket); no production caller changes.
- Both interpreters, both orders, count unchanged; gate ledger 0 unmarkered refusals / 0 stale markers.

**THEN STOP — no code written.** This crosses the Data layer's public surface (the factory) and the
lead rules on it (§4).

---

## §5 — NAMED DEFERRED ITEM (recorded, not acted on)

**WO-TBD — identifier hardening: convert tooling bite-proof scripts from hardcoded nodeids to the
marker/position identifier form.** WO-026 §4.2 found **~12 hardcoded test nodeids across five tooling
bite-proof scripts** (`emission` 3, `instrument_mismatch` 1, `vocabulary_enforcement` 1,
`vocabulary_scan` 4, `wire_string` 3) — WO-025 had reported "exactly one" from a too-narrow search. Per
*an enumeration is only as good as its identifiers* (position beats name, marker beats position,
content-hash beats marker), these should move off hardcoded names. **Not currently blocking.** It
**would** block if any of those five scripts silently passed because a renamed test no longer matched
its hardcoded nodeid (a bite proof that bites nothing). Recorded in `progress.md`.

---

## §6 — ACCEPTANCE

**Suite (216, 0 f/xf/xp each):**

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest tests/ -p no:randomly -rX` | **216** | **216** |
| `pytest tests/ --randomly-seed=20260730 -rX` | **216** | **216** |

(3.11 strict via a scratchpad venv on `CPython 3.11.15`; 3.14 dev = `CPython 3.14.6`, the local host. Each run 246s, 0 failed/xfailed/xpassed.)

- Gate ledger: **0 unmarkered refusals, 0 stale markers** (both snapshots).
- `git status --porcelain evidence/` shows ONLY the intended WO-027 snapshots + evidence/report.
- **`kraken_v2_book.py` sha256 — before == after:**
  before `a9388694f0af3d46e596c5aeae50596a9d7ad02da6cc3dd69b3c8da8ea03379b`
  after  `a9388694f0af3d46e596c5aeae50596a9d7ad02da6cc3dd69b3c8da8ea03379b`
- `lint-imports` **6/6** · `contract_count_check.py` **6/6** · `ruff` **clean** ·
  `annotation_name_scan.py` **0** · `preflight_path_check.py` **pass**.
- **Test-count arithmetic:** WO-027 adds/removes **no** test (investigation: a snapshot + docs only).
  Total **stays 216**.
- Commit / push / CI: _[fill run id]_ — local == remote, CI green BOTH legs.

---

## STOPPED / attempts / changed-but-not-asked
- **STOPPED at:** (1) the fresh-session mandate — reported before any work; user overrode with "resume
  with this session" (recorded). No in-investigation STOP: §0.8 verified, §1 tool passed, the code
  matched the WO's expectations (site 29 is the sole factory-routed race).
- **Attempts:** the snapshot tool ran once and passed; the 3.14 deterministic suite timed out the
  foreground 120s window and was completed in the background (216). No failed/retried edits.
- **Changed but not asked?** Only evidence/docs: `evidence/WO-027/` (two snapshots + this analysis),
  `WO-027-INVESTIGATION-REPORT.md`, `progress.md` (WO-027 block + the §5 named item). **No production
  code. `kraken_v2_book.py` byte-unchanged.**
