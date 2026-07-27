# WO-030 — CLOCK SEAM THREADING (production, D38) — REPORT

**Type:** production implementation (D38 — the ruling on WO-029's race #5 finding). **SHIP IMPACT: YES**,
authorized. **Base:** HEAD `64e2001`, local == remote, 217/217 both interpreters.

**AUTO MODE (§0.6):** the first edit attempt (`kraken_v2_book.py` builder) was **DENIED by the auto-mode
classifier** while the bar still read ON — confirming auto mode was never off (the `import time` edit
just before read "Allowed by auto mode classifier"). The user then cycled auto mode **off** (shift+tab);
with it off, the four production edits were applied deliberately, **one at a time, each visible** — no
production/auto-mode permission was granted (which would have re-routed edits through the classifier,
defeating §0.6).

**`/context`:** ~33% at START (last reading), well under threshold.

**Production files changed (all five — the four WO-028 touched + decision.py for the §3 rename):**
| file | after sha256 | one-line diff |
|---|---|---|
| `kraken_v2_book.py` | `b06c347e66ded3a739505c7f6598a6de3eb40f38b2019ac2cca3a1c4c3889615` | module-level `import time`; builder gains `monotonic_clock=time.monotonic, wall_clock=None`, forwards mono via ctor + wall post-construction |
| `factory.py` | `103a8ba793c6c1d2bff6012095e9616a9e7ab5d92f428eadd7f2b194a041834c` | `import time`; `create_live_capture_feed` gains + forwards the two clock seams |
| `registry.py` | `5bf833c78fd3b91e055e91c08026da2439801cf124c485928ecf8f492ba38a68` | `_LIVE_FORWARDED_PARAMS` inventory; contract generalized to all three params; code renamed |
| `live_capture.py` | `dab18f67a7f334d746a72d3a34944e7212961fac1685ae09d6973213ef58d0ff` | runner gains + stores + forwards the two clock seams (distinct from its own `_clock`) |
| `logkit/decision.py` | `3d153a110248ec5395d9b74be7631009a53eae966659f7852985e73dcefee337` | reason code renamed `…MISSING_CONNECT_FN` → `…MISSING_FORWARDED_PARAM` (§3) |

---

## §0.8 — BUILT-VS-OPERATED + the seam-detection confirmation
Every OPERATED row verified. The critical §0.8 check — the adapter's `_wall_clock`/`_monotonic_clock`
seams and their injection detection are **as WO-023 left them**: `_wall_clock` default raw `None`,
detection `is not None`; `_monotonic_clock` eager `monotonic_clock or time.monotonic`, detection
`is not time.monotonic` (D35-2 convention block, kraken_v2_book.py:1151–1167). The threading feeds these
exact seams. No STOP.

---

## §1 — signatures (before → after; the WO-028 template intact)
`connect_fn` threading present and intact at base (the "written against its consumers" check passed).
After: the runner, `create_live_capture_feed`, and `_build_kraken_v2` each gain the two clock params
beside `connect_fn`; `register` gains the generalized check beside WO-028's; the adapter constructor's
`monotonic_clock`/`_wall_clock` seam is **UNTOUCHED**.

## §2 — the threading (D38), both paths
- **2.1 Builder** — `monotonic_clock=time.monotonic` (threaded through the CONSTRUCTOR — the adapter's
  eager convention), `wall_clock=None` set post-construction only when injected. **§2.1 DECISION
  (stated):** the wall default is **`None`, not `time.time`** — the D35-2 raw-None convention means
  `time.time` held in `_wall_clock` reads as INJECTED (`is not None`) and would trip COHERENCE on a
  real capture (the §2.2 blocking condition). `time.monotonic` is safe (reads not-injected). This is
  the §0.1 "code wins over the order's literal example" call.
- **2.2 Adapter constructor UNTOUCHED.** Consequence verified empirically: a builder-constructed adapter
  holds `_monotonic_clock is time.monotonic` and `_wall_clock is None` → gate reads BOTH as
  not-injected → **EARLY-RETURNS** on a real capture (no refusal). `_connect`/deadline use the identical
  `time.monotonic`/`time.time` as before — per-frame behaviour byte-identical.
- **2.3 Factory, both functions.** `create_live_capture_feed` forwards both clock seams (safe —
  `is_live_capable` gates to the kraken_v2 builder). **`create_feed` UNCHANGED** — generic over
  `DATA_SOURCE`; `simulated`/`kraken_public` reject the clock kwargs; 1b held at the shared builder
  (verified: `create_feed()` under `DATA_SOURCE=kraken_v2` → adapter clocks are the declared defaults).
- **2.4 Runner.** Gains `monotonic_clock=time.monotonic, wall_clock=None`, stored as `_monotonic_clock`/
  `_wall_clock`, forwarded in the `adapter is None` branch. **Distinct from the runner's own `clock`**
  (`self._clock = clock or time.time`, per-minute bucketing in `run()`) — the threaded seams reach the
  ADAPTER via the factory, never the runner's duration clock. Injected-adapter branch unchanged.
- **2.5 Registry** unchanged (generic `**kwargs`).

**Single-value proof (empirical):** every layer default for monotonic `is time.monotonic`; every wall
default is `None`; a real factory-built adapter early-returns; an injected COHERENT pair (shared token)
+ fake transport reaches the adapter and proceeds.

## §3 — generalized registration contract (D38)
`register(live_capture=True)` now requires the builder accept **every** param in
`_LIVE_FORWARDED_PARAMS = ("connect_fn", "monotonic_clock", "wall_clock")` — the shared builder's
forwarding inventory. **CHOICE (§3):** WO-028's `LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN` was
**GENERALIZED (renamed)** to `LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM` — one load-time code for the
whole contract, not a second (avoids handing the vocabulary-split WO a tangle, §3/§8). The vocabulary
declaration in `logkit/decision.py` was updated to match (the guard requires it declared). **D-number:**
the message cites **`D38`** (this ruling's doctrine — the forwarding-surface-as-inventory); WO-028's
placeholder `D39` is superseded here.

The **real `_build_kraken_v2` passes the generalized check** (accepts all three) — verified.

**Bite proof** — `evidence/WO-030/registration_validation_bite_proof.txt`, four artifacts, sha256
exact-restore of `registry.py` (IDENTICAL), all three directions:
- **A1:** missing-`wall_clock` builder raises, **naming `wall_clock`** (per-parameter, not just
  "has connect_fn"); missing-`connect_fn` still refuses (WO-028 case holds); full + non-live register.
- **A2 (necessity):** inventory weakened to `("connect_fn",)` → wall-missing builder **registers
  silently**. **A3:** restored → raises again. **A4:** sha256 IDENTICAL: YES. **VERDICT: PASS.**

## §4 — production unchanged + factory-boundary observability
- **4.1** existing suite green (see §9); the identity test extended to assert the non-live default
  clocks `_monotonic_clock is time.monotonic` and `_wall_clock is None` at construction (no socket).
- **4.2 (D38's named test)** — `test_factory_built_adapter_is_legible_to_coupling_gate`, through the
  **full runner→factory→builder** path: a COHERENT fake pair + fake transport → gate **PROCEEDS**
  (`PROCEED_COHERENT`, transport opened); a fake clock + REAL transport (spy as `_REAL_CONNECT` by
  identity) → gate **REFUSES COUPLING pre-connection** (`connect_count == 0`). A factory-built adapter
  is as legible to the gate as a directly-built one. **No real socket** in either half. **+1 test.**

## §5 — race #5 NOT converted (honored)
This WO makes race #5 clock-INJECTABLE; it injects no clock into it. §4.2 uses throwaway/fixture
constructions, not the race #5 test. Pass two (WO-029, fresh session) re-enumerates the 26 at HEAD.

## §6 — re-baseline: reasoned exclusion
The threaded clock params execute ONCE at construction, never in `get_live_market_data`'s per-frame
loop — outside the hot-path boundary. The clocks USED per-frame are unchanged in identity
(`time.monotonic`/`time.time`), so per-frame timing is byte-identical. **No re-baseline triggered.**

## §7 — decision log
`docs/decisions/2026-07-25-a-transport-seam-is-not-a-clock-seam.md` — ratified verbatim (+ the
generalizing sentence: the shared builder's forwarding surface is a contract inventory).

---

## §9 — ACCEPTANCE

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest tests/ -p no:randomly -rX` | **218** | **218** |
| `pytest tests/ --randomly-seed=20260801 -rX` | **218** | **218** |

(3.11 strict `CPython 3.11.15`; 3.14 dev `CPython 3.14.6`. Each 246s, 0 f/xf/xp. Gate ledger 43 invocations,
0 unmarkered refusals / 0 stale markers each leg; snapshots in `evidence/WO-030/`.)

- **Test-count arithmetic:** 217 + 1 (§4.2 factory-boundary test) = **218**; §4.1 extended an existing
  test (no add); the bite proof is a standalone `tools/` instrument (not a suite test).
- Generalized contract live; bite proof A+B+C, four artifacts, sha256 exact-restore.
- §4.1 non-live default clocks `is time.monotonic` / `is None`; §4.2 proceed + pre-connection refuse green.
- Gate ledger: 0 unmarkered refusals, 0 stale markers (snapshot `evidence/WO-030/`).
- `lint-imports` 6/6 (runner imports only `factory`/`websockets`, never `kraken_v2_book`) ·
  `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 · `preflight` pass.
- Five production files changed (hashes above); no OTHER production file touched.
- Commit, push, local == remote, CI green BOTH legs — run `30183494157`.

## §10 — STOPPED / attempts
- **STOPPED:** none in-implementation (the §2.1 wall-default decision was a "decide and state" the WO
  delegated, not a blocking STOP — verified detection is preserved). The auto-mode denial halted the
  first edit until the user turned auto mode off (reported).
- **Attempts:** the builder edit was denied once (auto mode on), then applied after the toggle. Bite
  proof passed first run. Targeted tests green before the full suite.
- **Changed but not asked?** the five production files above; tests (`test_clock_injection_gate.py` —
  §4.1 extension + §4.2 test); `tools/registration_validation_bite_proof.py` (generalized); the decision
  log; `evidence/WO-030/`; this report; `progress.md`.
