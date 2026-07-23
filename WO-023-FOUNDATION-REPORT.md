# WO-023 §2 — FOUNDATION REPORT: Three-Field Pre-Connection Clock Gate

**Baseline:** `0fd13fe` on master (local == remote at start). **Ship impact: YES** (production
change authorized by RULING D34). **Scope: FOUNDATION ONLY** — the 30-test conversion and the
original WO-023 §3/§4/§5 remain for a FRESH session; not begun here.

**Headline:** the two injectable seams (`_monotonic_clock`, `_connect_fn`), the coherent `FakeClock`
harness, the three-field pre-connection gate with the declared `CLOCK_INJECTION_REFUSED` code, its
three-assertion bite proof, and the one authorized test migration all landed green. **216 passed,
0 failed / 0 xfailed / 0 xpassed on BOTH interpreters, BOTH orders.** One CODE-WINS finding surfaced
at Checkpoint A and is reported below (§1 named two deadline lines; the code has three).

---

## §1 — THE `_monotonic_clock` SEAM (RULING D34-1) + the Checkpoint-A finding

`__init__` gained `monotonic_clock=None`; `self._monotonic_clock = monotonic_clock or time.monotonic`
(local `import time`, matching the file's idiom — no module-level import added, no `from __future__`).
Rationale comment at the deadline set records D25: **a duration is an INTERVAL; D25 puts intervals on
MONOTONIC** — so the deadline runs on `_monotonic_clock`, NOT `_wall_clock` (line 1136: the wall clock
is the suspend detector's and can jump).

### CODE-WINS FINDING (Checkpoint A: "if not 215, that is a finding")
The order said "Route BOTH deadline lines" and named **two** (`kraken_v2_book.py:2388` set,
`:2434` guard). The CODE has a **THIRD** deadline consumer:

    :2593  remaining = deadline - time.time()      # bounds the recv timeout (feeds :2599 recv_timeout)

Routing only the two named lines left this third site subtracting **wall-clock `time.time()`** from a
now-**monotonic** `deadline` — monotonic minus epoch → a huge negative `remaining` → immediate
`break` → **raw=0 frames, 0 gaps**. Checkpoint A on the two-line version was **NOT 215** (6 transport
tests failed, e.g. `test_gap_ledger_persisted_readable_from_disk`: `0 gaps; got ['run_start',
'run_end']`). "The deadline" is defined by everything that reads `deadline`, not by a count in the
order. I routed the third site through `_monotonic_clock` as the **forced completion of D34-1** (the
only coherent state: every deadline consumer on one clock), and report it here rather than reconcile
silently (rule 0.1). Enumerated all three `deadline` reads to confirm none remain on `time.time()`;
`self._start_time = time.time()` (:2359) is a wall PROVENANCE marker, not a deadline consumer, and is
left untouched per "do not touch `_wall_clock`'s consumers".

**Checkpoint A (corrected, all three lines routed) + §2:** `pytest tests/ -p no:randomly` →
**216 passed** on 3.14 (`evidence/WO-023-FOUNDATION/checkpointB_seams_3.14.txt` shows the combined
seam run at 215 before §5's test existed; the 216 figure is the full acceptance run). The seam is
backward-compatible once the third line is routed.

---

## §2 — THE `_connect_fn` SEAM (RULING D34-2): call sites + binding decision

**Every `_connect_fn` call site changed — there is exactly ONE.** `_connect()` (`kraken_v2_book.py`,
formerly the bare `await websockets.connect(...)`) now resolves:

    connect_fn = self._connect_fn or websockets.connect
    return await connect_fn(self.WS_URL, open_timeout=15, close_timeout=5,
                            ping_interval=..., ping_timeout=...)

(Confirmed by grep: `websockets.connect` appears only at this one call site inside the adapter.)

### Binding decision (Checkpoint B): **LATE binding.** Justification:
`__init__` stores the **RAW injection**: `self._connect_fn = connect_fn` (default **None**), and the
`or websockets.connect` resolution happens at the **call site**. This is required and does NOT
conflict with the gate:

- **Late binding is required for the suite to hold.** Existing tests `patch("websockets.connect",
  factory.connect)` **after** constructing the adapter. Eager `self._connect_fn = connect_fn or
  websockets.connect` in `__init__` would capture the **unpatched** callable, and the module patch
  would never take → those tests would attempt real connections. Resolving late (inside `_connect`,
  where `import websockets` sees the patched module attribute) keeps all 13 module-patching tests
  green.
- **It does NOT conflict with the gate's ability to detect a default transport.** The gate keys on
  the **injection sentinel** `self._connect_fn is None`, not on the resolved callable. A test that
  module-patches `websockets.connect` but injects no clock is a **default clock + default (None)
  transport** to the gate → coupling passes → suite green. The "real transport" case the gate must
  refuse is exactly `_connect_fn is None` paired with a non-default clock. So the object can finally
  **name its own transport** (decision log 1), and no STOP was warranted.

**Checkpoint B:** `pytest tests/ -p no:randomly` → **216 passed** (module-level monkeypatching still
works). Evidence: the both-order acceptance runs below.

---

## §3 — THE COHERENT `FakeClock` HARNESS (GUARD 2)

`tests/fixtures/fake_ws_transport.py` was **EXTENDED, not rebuilt** (the WO-014b surface is intact;
`FakeWebSocket`, `ScriptedConnectionFactory`, `REOPEN_FAILURE`, `starve_event_loop` unchanged). Added:

- `FakeClock` — ONE counter driving BOTH `wall` and `monotonic`, each = counter + a **fixed base**
  (monotonic base small = ORDERS; wall base a unix epoch = LOCATES — D25 holding inside the fake).
  `advance(delta)` moves both by the same delta. **Coherent is the DEFAULT construction.** Both
  readers carry a shared `_coherence_token` (the FakeClock instance) so the gate can PROVE one
  source rather than infer it.
- `incoherent_clock_pair(...)` — the **explicitly-named** incoherent construction (never the default
  path): by default a fake wall against the REAL `time.monotonic` (the suspend shape), sharing no
  token.

---

## §4 — THE GATE + `CLOCK_INJECTION_REFUSED` (RULINGS D34-2/D34-3)

### 4.1 Reason code — vocabulary proof
`CLOCK_INJECTION_REFUSED` declared in `src/trading/logkit/decision.py` `VALID_REASON_CODES["DATA"]`,
carrying the ruled invariant VERBATIM in its comment:

> A NON-DEFAULT CLOCK IS PERMITTED ONLY WHERE THE TRANSPORT IS ALSO NON-DEFAULT.
> A REAL TRANSPORT WITH A FAKE CLOCK REFUSES, PRE-CONNECTION, WITH THE DECLARED CODE.

**Vocabulary properties proved (both, both literal forms):** `tests/test_reason_code_vocabulary.py`
→ **11 passed**. `raised⇒declared` (the gate emits the colon form `"CLOCK_INJECTION_REFUSED: …"`,
seen by `_RC_COLON`); `declared⇒producible` (emitted in `kraken_v2_book.py`, outside the declaration
site); prefix-free across the union (`CLOCK_` is a unique stem). The kwarg-form scanner runs over the
whole tree; no keyword emission of this code exists, so no undeclared kwarg form leaks.

### 4.2 The gate — `_assert_clock_transport_gate(incoherent_clocks_allowed)`
Placed in `get_live_market_data` **immediately after `GAP_PERSIST_UNCONFIGURED`** (same
pre-connection discipline), it inspects the three constructor-injected fields:

1. **COUPLING** — if either clock is non-default (`_wall_clock is not None` OR `_monotonic_clock is
   not time.monotonic`) then `_connect_fn` MUST be non-default (`is not None`); else refuse
   `CLOCK_INJECTION_REFUSED: COUPLING`.
2. **COHERENCE** — injected clocks must be the one-source pair (both non-default AND sharing a
   `_coherence_token`); else refuse `CLOCK_INJECTION_REFUSED: COHERENCE`, UNLESS
   `incoherent_clocks_allowed` is non-empty.

No injected clock → returns immediately (the default path every real run and non-suspend test takes).
The payload names WHICH assertion failed — one code, diagnosable.

### 4.3 The named exception (RULING D34-3)
`get_live_market_data` takes `incoherent_clocks_allowed: str = ""`. The gate reads the argument; it
never infers the exception from the injection pattern. Every incoherent run is greppable by its
declaration.

---

## §5 — THE BITE PROOF (three assertions, one test; four artifacts, sha256)

`tests/integration/test_clock_injection_gate.py::test_clock_injection_gate` — all three in one test:
1. **REFUSAL** — real transport (default `_connect_fn`) + a coherent fake clock → refuses
   `CLOCK_INJECTION_REFUSED: COUPLING`, and `spy.connect_count == 0` proves **pre-connection**.
2. **PRESERVATION** — fake transport + coherent `FakeClock` pair → PROCEEDS (connects, prices the
   snapshot).
3. **THE EXCEPTION'S OWN DUAL** — identical incoherent injection (fake wall / real monotonic): WITH
   `incoherent_clocks_allowed="suspend-detector-test"` → PROCEEDS; WITHOUT → refuses
   `CLOCK_INJECTION_REFUSED: COHERENCE`, `connect_count == 0`.

**Four artifacts, sha256 exact-restore** (`evidence/WO-023-FOUNDATION/bite_proof_clock_gate.txt`):
- PRISTINE sha256 = `83ccaeb0b9f44a76fd33d6c5df98a256e3ddae298ad85641b6e79627984ef677`
- **Artifact 1** — PASS on pristine.
- **Artifact 2** — MUTATION A (whole gate neutered, early `return`) → assertion 1 (COUPLING) FAILS
  `DID NOT RAISE`; restore sha256 == pristine.
- **Artifact 2b** — MUTATION B (coherence branch → `False`, coupling intact) → assertion 3b
  (COHERENCE) FAILS `DID NOT RAISE` while assertion 1 still passes (branches independent); restore
  sha256 == pristine.
- **Artifact 3** — PASS after restore. **Artifact 4** — final sha256 == pristine (IDENTICAL: YES).

The self-terminating spy (snapshot + clean close) makes a neutered gate fail **fast**, never hang.

---

## §6 — THE ONE AUTHORIZED TEST EDIT

`tests/integration/test_host_suspend.py::test_host_suspend_recorded_diagnostic_not_terminal` migrated:
transport injected via `connect_fn=factory.connect` (no module patch); the run declares
`incoherent_clocks_allowed="suspend-detector-test"`; the fake wall (`_JumpClock`) still runs against
the REAL monotonic (the incoherent pair the detector needs). Docstring states it is the SOLE
enumerated incoherent customer and why. Migration required **nothing beyond the two new seams** (no
finding about seam completeness). The other two tests in the file are unchanged (they inject no clock
→ default path). Verified: `test_host_suspend.py` → 3 passed with the gate active.

---

## §7 — HOT-PATH RE-BASELINE (`evidence/WO-023-FOUNDATION/hot_path_rebaseline.txt`)

**PREDICTION (recorded FIRST): BELOW FLOOR / UNDETECTABLE.** Two grounds: (1) magnitude — one C-level
clock call swapped for an attribute load + one C-level call (~tens of ns/iter) vs the ~10 ms/frame
effective floor; (2) coverage — the instrument replays `process_raw_frame` + `LiveTradingLoop`, NOT
`get_live_market_data`'s while-loop where line 2467 lives, so it is structurally blind to the change.

**MEASUREMENT:** full-loop replay, 60 s, 1959/min (representative). mean_cycle **108.913 ms** vs stored
**108.717 ms**, delta **+0.196 ms**, SIGNAL 0.196 / NOISE 2.000 / **RATIO 0.10 → BELOW FLOOR,
UNDETECTABLE.** **CONFIRMED.** No `--write` (a below-floor change is not a legitimate re-baseline; D31).

---

## §8 — DECISION LOG — THREE ENTRIES (`docs/decisions/2026-07-23-*.md`)
1. `a-guard-can-audit-the-object-model.md`
2. `a-ruling-about-a-seam-must-be-written-against-its-consumers.md`
3. `the-exception-must-be-requested-by-name.md`

---

## §9 — ACCEPTANCE (all held before commit)

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest -p no:randomly -rX` | **216 passed**, 0 failed/xfailed/xpassed | **216 passed**, same |
| `pytest --randomly-seed=20260723 -rX` | **216 passed**, same | **216 passed**, same |

- `lint-imports` → **6 kept, 0 broken** (Forbid loop→adapters, Registry sole resolver, No test
  doubles in production, + 3 layering contracts)
- `python tools/contract_count_check.py` → **PASS, 6/6**
- `ruff check .` → **All checks passed!**
- `python tools/annotation_name_scan.py` → **0**
- `python tools/preflight_path_check.py` → **PASS**

**Test-count arithmetic:** baseline **215**; §5 adds ONE test (`test_clock_injection_gate`, three
assertions in one function) → **+1**; §6 EDITS one test in place → **+0**. **New count = 216** (stated
explicitly, not "unchanged").

Secret scan: no credentials/tokens/keys/session-ids added (tests, docs, a reason-code string, and two
clock/transport seams only). **Commit / push / CI:** __COMMIT_CI__

---

## §10 — REQUIRED ANSWERS
- **Affects what ships? YES** — production change (D34-authorized): two injectable seams, the
  deadline routed onto monotonic (three sites), and the pre-connection gate in `kraken_v2_book.py`
  plus one declared reason code in `decision.py`. Behavior for a DEFAULT-constructed adapter (real
  runs) is unchanged: no clock/transport injected → the gate returns immediately and the deadline
  runs on `time.monotonic` exactly as `time.time()` did for a real interval.
- **Hot-path judgment:** the per-iteration deadline guard is hot-path by the standing rule's letter;
  re-baselined (§7), BELOW FLOOR / UNDETECTABLE, prediction confirmed.
- **Venue connection? NO.** **HTTPS? NO.** All transport simulated (`fake_ws_transport`); no socket
  opened (the establishment replay runs without a socket).
- **Prose standing in for output? NO** — every claim backed by a pasted run or an evidence artifact.
- **Changed but not asked?** `instructions.md` was already modified at session start (it carries the
  WO assignment text — not my edit); committed as the WO record. Otherwise: only the files this WO
  specifies (production seams+gate, the reason code, the FakeClock fixture, the migrated test, the
  new bite-proof test, three decision logs, evidence, this report, progress.md). No other file.
- **STOPPED at:** the Checkpoint-A finding (§1) — reported and resolved as the forced completion of
  D34-1, not halted, because D34-1 already ruled the deadline onto monotonic and line 2593 is
  manifestly a deadline consumer.

**THEN STOP.** The 30-test conversion is NOT begun.
