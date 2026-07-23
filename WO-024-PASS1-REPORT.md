# WO-024 PASS ONE — TRANSPORT MIGRATION — REPORT

**Base:** `9175969` (worked from `ba082a9`, the §2c docs-close on top of it — identical code state).
**Scope:** transport migration to `connect_fn` + gate ledger + two docs-only declarations. **No clock
injected anywhere.** Pass two (clock injection) NOT begun.

**Fresh-session directive (override, disclosed):** the WO opens "START THIS IN A FRESH CLAUDE CODE
SESSION." This ran in an existing session (foundation + §2b + §2c already done here) at the user's
explicit direction after I surfaced the directive and recommended a fresh session. Recorded as an
override, not silent.

**`/context` reading (0.7):** I cannot invoke `/context` (a user CLI command, not a tool). Requested a
reading from the user; last actual value was 27% before §2b. Reported honestly, not estimated.

---

## §1 — POPULATION (grep is authoritative)

**38 patch sites · 35 distinct tests · 14 files.** All are `patch("websockets.connect", <callable>)`
(single/double quote). Forms `patch.object(websockets,…)`, monkeypatch, direct `websockets.connect=`,
and helper-indirected patches: **none found.** In every site except the two registry cases the adapter
is constructed **before** the patch (test-side, injectable).

**How it differs from the "near 13" sounding:** the 13 was roughly the *file* count of module-patching
live tests; the real **site** population is 38 across 14 files (~3×). Reported as expected per §1.

**Classification:**

| Class | Sites | Disposition |
|---|---|---|
| Cleanly migratable (inline / `_live_adapter()` helper / `_StrandingAdapter` subclass, built before patch) | **34** (32 tests) | migrated to `connect_fn=` |
| Gate's OWN identity mechanism (`test_clock_injection_gate`, 2 sites — co-patch `_REAL_CONNECT`+`websockets.connect`) | 2 | **Excluded** — migrating defeats the guard's bite proof |
| Already migrated (`test_host_suspend_recorded_…`) | — | not in the 38 |
| **SEAM FINDING** `test_runner_resolves_live_adapter_from_data_source_via_factory` (`adapter=None`, registry-resolved) | 1 | **Not test-side reachable** — left as-is (ruled) |
| Out-of-population `test_live_capture_refuses_non_live_capable_data_source` (`adapter=None`, refuses pre-connect) | 1 | never builds an adapter / never connects — left as-is |

**The seam finding (verified):** `connect_fn` threads through **neither** `LiveCaptureRunner` nor
`create_live_capture_feed`/`registry.create` (live_capture.py:117 → factory.py:86). The two
`adapter=None` tests resolve the adapter via the registry inside `runner.run()`, so a test-side
`connect_fn` cannot reach it without a production change (out of this WO's "mechanical, no behaviour
change" scope). **Ruled (user, as lead relay): migrate the 34, leave sites 29/30 as documented
findings.** In pass one both are harmless — site 29 injects no clock → gate early-returns; site 30
refuses before the gate. Threading `connect_fn` through the runner is a separate seam WO if pass two
ever needs a clock in the registry-resolution test.

---

## §2 — THE MIGRATION (34 sites / 32 tests / 13 files)

Mechanical pattern applied per site: move the fake construction (`ScriptedConnectionFactory` / spy /
`_boom`) above the adapter; pass `connect_fn=<the same callable>` to `KrakenV2BookAdapter(...)` (or the
`_live_adapter(...)` helper, which gained a `connect_fn=None` param threaded to the constructor);
remove `with patch("websockets.connect", …)` and de-indent its body. **Nothing else changed** — no
clocks, no assertions, no timings, no fixtures, no frame scripts.

| File | Tests | Sites |
|---|---|---|
| test_backoff_breaker.py | transient reopen, persistent breaker | 2 |
| test_failure_cap.py | count cap, byte cap, one-line summaries | 3 |
| test_failure_capture.py | ruled-field capture, every-failure | 2 |
| test_gap_recording.py | keepalive, checksum resync, breaker ladder, venue disconnect, terminal breaker, overlapping, incomplete | 7 |
| test_ledger_persistence.py | persisted-readable, crash-mid-capture, refuses-when-unset (inline) | 3 |
| test_host_suspend.py | no_host_suspend_under_normal_timing ONLY | 1 |
| test_keepalive.py | heartbeat absence, app ping/pong | 2 |
| test_live_capture.py | 5 inline-adapter tests (dual test = 2 pairs conn_a/conn_b) | 6 |
| test_no_silent_fallback.py | connection-failure-raises (`connect_fn=_boom`) | 1 |
| test_protocol_ping.py | ping params, protocol-close recovery | 2 |
| test_reconnect_to_effect.py | five-failures (inline), stranded (`_StrandingAdapter` subclass) | 2 |
| test_throughput.py | receive-to-process latency | 1 |
| test_venue_close_path.py | 1 test / 2 pairs (factory_a↔adapter_a, factory_b↔adapter_b, injected separately) | 2 |

`_StrandingAdapter` **inherits** `__init__` (only overrides `_perform_reconnect`), so
`connect_fn=factory.connect` passes straight through — verified.

### Reconnect-persistence verification (§2 requirement, verified per test)
`self._connect_fn` is a stored field set once at construction and resolved at EACH `_connect` call
(`connect = self._connect_fn or websockets.connect`, kraken_v2_book.py:2190), so ONE injected factory
serves every reconnect. Verified NOT by assumption but by the reconnect tests passing with their
multi-socket assertions intact — the 16 reconnect sites (factories with 2–21 socket scripts:
backoff_breaker ×2, keepalive ×2, gap_recording ×4, ledger_persistence, live_capture ×2,
protocol_ping, reconnect_to_effect, venue_close_path ×2) all pass, asserting `connect_count` /
`sockets` / `failed_attempts` reach their scripted counts across reconnects. The dual-adapter tests
(`test_clean_deadline_close…`, `test_venue_close…`) inject a SEPARATE factory per adapter
(conn_a↔adapter_a, conn_b↔adapter_b), not collapsed.

### Attempts / stops
**No site required anything beyond the swap; nothing was reverted or worked around.** The one STOP was
§1's seam finding (sites 29/30), ruled before any edit.

---

## §3 — THE GATE LEDGER (falsifiable acceptance instrument)

`conftest.py::_gate_ledger_recorder` (session-scoped, autouse) wraps
`KrakenV2BookAdapter._assert_clock_transport_gate`, **delegates to the real gate unchanged** (pure
observation — not "monkeypatching to make a guard pass"; the guard's behaviour is identical with or
without the recorder), and records every invocation's outcome. At session end it writes
`evidence/WO-024-PASS1/gate_ledger.txt` and **asserts zero refusals** across the suite, EXCLUDING the
guard's own test (`test_clock_injection_gate`), whose refusals are its designed S13/D37 bite proof.

**Measured shape (full suite, 41 gate invocations):** `EARLY_RETURN` 34 · `PROCEED_DECLARED` **1**
(the suspend test, sole) · `REFUSED_COUPLING` **0** · `REFUSED_COHERENCE` **0** (both excluding the
guard test). The guard's own test contributes its designed `REFUSED_COUPLING`×2 / `REFUSED_COHERENCE`×1
/ `PROCEED_DECLARED`×1 / `PROCEED_COHERENT`×1, all excluded. This is exactly §3's expected shape.

### Ledger bite proof (`evidence/WO-024-PASS1/ledger_bite_proof.txt`) — a ledger that cannot fail proves nothing
Four artifacts, sha256 exact-restore of the mutated test
(`576745bd2a58479c6534494c491db3ecc59c81359269de547e41f5a48324bb7e`):
- **Artifact 1** — pristine → **2 passed** (ledger assertion holds).
- **Artifact 2** — mutation (per §3 recipe: drop `connect_fn` → module-patch the transport; inject an
  incoherent wall clock) → the mutated test FAILS on `CLOCK_INJECTION_REFUSED` **AND** the session-end
  ledger teardown ERRORS: **"GATE FIRED during pass one … Refusals … [(…test_throughput…,
  'REFUSED_COHERENCE')]"**. Restore sha256 == pristine.
- **Artifact 3** — after restore → **2 passed**. **Artifact 4** — final sha256 == pristine (IDENTICAL).

### 0.1 FINDING — the WO's bite recipe says "COUPLING"; the code fires "COHERENCE"
§3 (and §0.5) state that re-introducing module patching + a clock refuses on **COUPLING**. That is the
SUPERSEDED sentinel model. Under the **identity** keying WO-023 §2b installed, a module-patched
transport resolves to the **patched fake**, which is **not** `_REAL_CONNECT`, so COUPLING does NOT
fire — the injected incoherent clock refuses on **COHERENCE** (a coherent clock would `PROCEED_COHERENT`
with no refusal). COUPLING fires only with the **genuine real transport** (no patch, no `connect_fn`) +
a clock. The bite still bites (the gate fires, the ledger assertion fails); only the WO's refusal LABEL
was inaccurate. Reported per 0.1 (code wins). The ledger records the actual outcome regardless of type.

---

## §4 — TWO PRODUCTION DECLARATIONS (docs-only; kraken_v2_book.py)

**4.1 (D35-2) — the three-seam convention block** at the seam definitions in `__init__`, declaring
each convention (`_wall_clock` raw None/late; `_monotonic_clock` eager `time.monotonic`/direct;
`_connect_fn` raw None/late) and WHY `_monotonic_clock`'s eager resolution is **load-bearing** (real
monotonic reads as not-injected → coherence False → the named exception becomes required). Doctrine
line committed verbatim: *convention asymmetry that carries semantics is ARCHITECTURE, not untidiness;
normalize only what is provably decorative.* (Also reconciled a stale §2b-era clause on `_connect_fn`
that still described the pre-identity `is None` sentinel keying — docs-only accuracy fix.)

**4.2 (D35-3) — the declared limit of the coupling check** in the gate docstring: the check refuses the
real transport BY IDENTITY, so a hand-written WRAPPER delegating to `websockets.connect` is a different
object, not `_REAL_CONNECT`, and would NOT be refused; defeating the guard requires deliberately
constructing a bypass. Committed contract: *THE ACCIDENTAL CASE REFUSES; THE ADVERSARIAL INSIDER IS OUT
OF SCOPE*, and the tell — *any wrapper around the real transport in the tree is a deliberate act,
greppable, a STOP-AND-ASK event under the 0.1a standing rules.*

No logic changed (§4 is comments/docstrings only): import OK, ruff clean, gate test + migrated sample
green after the edits.

---

## §6 — DECISION LOG
`docs/decisions/2026-07-24-incidental-coverage-is-not-coverage.md` — the ratified entry verbatim, with
the WO-023 §2c Mutation-D specimen and the coverage-topology corollary (*a branch's preservation dual
must be LOCAL and DIRECT*).

---

## §7 — ACCEPTANCE

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest -p no:randomly -rX` | **216**, 0 f/xf/xp | **216**, 0 f/xf/xp |
| `pytest --randomly-seed=20260726 -rX` | **216**, 0 f/xf/xp | **216**, 0 f/xf/xp |

- **Gate ledger:** 0 `REFUSED_COUPLING`, 0 `REFUSED_COHERENCE`, exactly 1 `PROCEED_DECLARED` (excl.
  guard test) — the session-end assertion passes on every leg.
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 ·
  `preflight_path_check.py` pass · reason-code vocabulary 11 passed.
- Ledger bite proof: four artifacts, sha256 exact-restore (above).
- **Commit / push / CI:** batches `b8f18b3` (migration+ledger) + `959e832` (docs) on master, pushed, local == remote. **CI run `30043854493` GREEN on BOTH legs** — test (3.11) + test (3.14) success.

### Test-count arithmetic
Migration is **+0** (swaps patch for `connect_fn`, adds/removes no test). The gate ledger adds **no
test** — it is a session-scoped conftest fixture + a teardown assertion, not a collected test item.
**Total stays 216** (batch 1 measured 216 with the ledger active). The ledger's teardown assertion is
an additional session-level check, not a 217th test.

### Ledger-persistence recommendation for pass two (Ops's view: YES; lead decides)
**Recommend the ledger PERSIST into pass two as the conversion's live safety net.** As pass two injects
clocks, any test that trips the gate is caught immediately and LOCALLY by the ledger assertion, naming
the exact nodeid — the §6 doctrine (local-and-direct) applied at suite scale, instead of an incidental
downstream failure. **One adjustment for pass two:** the "exactly 1 `PROCEED_DECLARED`" expectation is a
pass-one shape; pass two will legitimately grow `PROCEED_COHERENT` (coherent injected pairs) and may add
named `PROCEED_DECLARED` customers. The **invariant that must hold** is `REFUSED_COUPLING == 0 and
REFUSED_COHERENCE == 0` (excl. the guard's own test) — that stays the safety net; the proceed-shape
counts become reported diagnostics, not assertions. Not decided here.

---

## STOPPED / attempts / changed-but-not-asked
- **STOPPED at:** §1's seam finding (sites 29/30) — surfaced before any edit, ruled by the user.
- **0.1 findings reported:** (a) the seam gap (connect_fn doesn't thread through the runner/registry);
  (b) the bite recipe's "COUPLING" is "COHERENCE" under identity keying.
- **Changed but not asked?** Only: the 13 migrated test files, `conftest.py` (ledger), `kraken_v2_book.py`
  (docs-only §4 declarations + one stale-comment reconciliation), the new decision log, this report,
  `progress.md` (pass-one block), and `evidence/WO-024-PASS1/`. `instructions.md` carries the WO text
  (present at session start). No production logic changed.

**THEN STOP.** Pass two (clock injection) is NOT begun.
