# WO-025 — LEDGER CLOSEOUT + MARKER-BASED EXCLUSION — REPORT

**Base:** tree clean at `1402c8a`. **Scope:** §1–§5, tests/conftest/evidence/docs only.
**Ship impact: NO** — `kraken_v2_book.py` byte-unchanged: sha256
`a9388694f0af3d46e596c5aeae50596a9d7ad02da6cc3dd69b3c8da8ea03379b` **before AND after**.

**§0.8 built-vs-operated:** the two OPERATED rows verified present — `evidence/WO-024-PASS1/gate_ledger.txt`
exists (built WO-024 §3, committed `b8f18b3`); `test_clock_injection_gate` exists (one def). The
marker mechanism (§3) is the row THIS WO builds.

**`/context` (0.7):** I cannot invoke `/context` (user CLI command). Requested a reading from the user;
last actual was 27% before §2b. This session has now carried five WOs — a fresh session is advisable.

---

## §1 — THE LEDGER ARITHMETIC, RESOLVED FROM THE COMMITTED EVIDENCE

The committed `evidence/WO-024-PASS1/gate_ledger.txt` records **41** invocations. Reading the file
(not recomputing): the guard test `test_clock_injection_gate` appears **SIX** times, not five —

```
REFUSED_COUPLING  tests/integration/test_clock_injection_gate.py::test_clock_injection_gate
PROCEED_COHERENT  tests/integration/test_clock_injection_gate.py::test_clock_injection_gate
PROCEED_DECLARED  tests/integration/test_clock_injection_gate.py::test_clock_injection_gate
REFUSED_COHERENCE tests/integration/test_clock_injection_gate.py::test_clock_injection_gate
REFUSED_COUPLING  tests/integration/test_clock_injection_gate.py::test_clock_injection_gate
EARLY_RETURN      tests/integration/test_clock_injection_gate.py::test_clock_injection_gate
```

**The unaccounted 41st invocation is the guard test's own `EARLY_RETURN`** — from **assertion 5**
(WO-023 §2c's DEFAULT-PATH PRESERVATION: real transport + no clock injected → the gate early-returns).
The pass-one report accounted the guard test as contributing **5** outcomes (its 2 coupling refusals +
1 coherence refusal + 1 declared + 1 coherent) and missed that assertion 5 also invokes the gate. The
guard test contributes **6**. The **41 total is correct** — it is the report's *accounting* (34 + 1 +
5 = 40) that was the slip. Correct suite-wide arithmetic, from the file:

    EARLY_RETURN 35 + PROCEED_DECLARED 2 + PROCEED_COHERENT 1 + REFUSED_COUPLING 2 + REFUSED_COHERENCE 1 = 41
    = guard test's 6  +  (34 EARLY_RETURN + 1 PROCEED_DECLARED from all other tests) = 6 + 35 = 41.

Corrected in the pass-one report's accounting is out of this WO's scope (that report is committed
history); the correct accounting is recorded here and in the WO-025 progress block.

---

## §2 — SITES 29/30 LEDGER LINES (SHOWN, NOT ASSERTED)

Extracted verbatim from `evidence/WO-024-PASS1/gate_ledger.txt`:

    EARLY_RETURN      tests/integration/test_live_capture.py::test_runner_resolves_live_adapter_from_data_source_via_factory

- **site 29** → `EARLY_RETURN` — matches expectation (no clock injected in pass one).
- **site 30** (`test_live_capture_refuses_non_live_capable_data_source`) → **no line at all** — it makes
  no gate invocation, matching expectation (it refuses at `LIVE_CAPTURE_UNSUPPORTED` before the gate).

Neither differs from expectation → no STOP. (Context, not acted on here: site 29 is now known — via
the audit name-match — to be race #5 of 30, corpus-critical, blocked on the `connect_fn` threading WO.
Its pass-one disposition is still `EARLY_RETURN` because pass one injected no clock. Not migrated, no
clock injected.)

---

## §3 — THE MARKER-BASED EXCLUSION (BUILT)

### The change
- **Registered** `gate_refusal_expected` in `pytest.ini` `markers =` (required — `--strict-markers` is
  set; an unregistered mark would error).
- **Carried by exactly one test:** `@pytest.mark.gate_refusal_expected` on `test_clock_injection_gate`
  (the guard's own S13/D37 bite proof — the only test that intentionally makes the gate refuse).
- **`conftest.py`:** `pytest_runtest_setup` records the marker per test into `_MARKERED_NODEIDS`; the
  session-end `_write_gate_ledger_and_assert` replaces the by-name exclusion with a **bidirectional**
  assertion:
  1. **No refusal from an UNMARKERED test** — `unmarkered_refusals` must be empty.
  2. **No STALE MARKER** — a markered test that produced NO refusal is a hole opening quietly;
     `_MARKERED_NODEIDS − refused_nodeids` must be empty. **A stale marker FAILS** (Ops's call), the
     same weight as an unmarkered refusal.

The wrapper still DELEGATES to the real gate and only records (0.2 — not making a guard pass; behaviour
unchanged). The ledger reports the markered set both ways.

### Bite proof — four artifacts, sha256 exact-restore, BOTH directions
(`evidence/WO-025/ledger_bite_proof.txt`; the WO-024 by-name bite proof is INVALIDATED by the
mechanism change and re-run here, not cited.) Pristine `test_throughput.py` sha256
`576745bd2a58479c6534494c491db3ecc59c81359269de547e41f5a48324bb7e`:
- **Artifact 1** — pristine → **2 passed** (no markered test in this file; no refusal → both directions clean).
- **Mutation A** (drop `connect_fn` → module-patch + inject an incoherent clock; the test is UNMARKERED)
  → the gate fires and the session-end teardown ERRORS: **`(1) refusals from UNMARKERED tests …
  [(…test_receive_to_process_latency…, 'REFUSED_COHERENCE')]`**. Restore sha256 == pristine. (Per 0.1
  finding (b): fires COHERENCE, not COUPLING; the assertion does not hard-code the type.)
- **Mutation B** (add the marker to a test that makes NO refusal) → the session-end teardown ERRORS:
  **`(2) STALE markers … ['…test_receive_to_process_latency…']`**. Restore sha256 == pristine. This is
  the preservation dual, local and direct (0.4).
- **Artifact 4** — after restore → **2 passed**; final sha256 == pristine (IDENTICAL: YES).

### Adopt the identifier form where it reaches (enumerate, not convert)
Grep for by-name test enumerations elsewhere in the tree: the only other hardcoded test-node
identifier found is **`tools/vocabulary_enforcement_bite_proof.py:18`** — `NODE =
"tests/test_reason_code_vocabulary.py::TestReasonCodeCompleteness…"`, a by-name nodeid in a tooling
bite-proof script. Recorded for a later identifier-hardening WO; NOT converted here (§3).

---

## §4 — DECISION LOG
`docs/decisions/2026-07-24-an-enumeration-is-only-as-good-as-its-identifiers.md` — the ratified entry
verbatim + the family sentence (incomplete denominators / uncited recall / unfaithful identifiers),
committed as written.

## §5 — ANNOTATE, DO NOT DELETE
`progress.md` carries the dated annotation: the WO-024 closeout §2 instruction is SUSPENDED, its
premise INVERTED (site 29 is race #5, so the `connect_fn` threading is a pass-two PREREQUISITE); the
sites-29/30 comments were NOT written; the instruction re-issues (corrected) after the threading WO.
The ruled sequence and the NAMED deferred item (WO-TBD: thread `connect_fn` through
LiveCaptureRunner/create_live_capture_feed/registry.create) are recorded there. No comments written at
sites 29/30 (§5/§6 fence).

---

## §6 — SCOPE FENCE (honored)
No transport migration, no clock injection, no touching site 29/30 construction, no `connect_fn`
threading, **no gate docstring precision note** (r20 ruling 2 has NOT been ruled — I did not add it),
no production logic change. `kraken_v2_book.py` sha256 identical before/after.

---

## §7 — ACCEPTANCE

| Gate | 3.11 (strict) | 3.14 (dev) |
|---|---|---|
| `pytest -p no:randomly -rX` | **216**, 0 f/xf/xp | **216**, 0 f/xf/xp |
| `pytest --randomly-seed=20260728 -rX` | **216**, 0 f/xf/xp | **216**, 0 f/xf/xp |

- **Marker mechanism live:** markered set = `['…test_clock_injection_gate']`; (1) unmarkered refusals
  `[]`; (2) stale markers `[]` — asserted both directions on every leg.
- `lint-imports` 6/6 · `contract_count_check.py` 6/6 · `ruff` clean · `annotation_name_scan.py` 0 ·
  `preflight_path_check.py` pass.
- Bite proof re-run under the marker mechanism: mutations A + B, four artifacts, sha256 exact-restore.
- `kraken_v2_book.py` sha256 BEFORE `a9388694…` == AFTER `a9388694…` (IDENTICAL).
- **Test-count arithmetic:** WO-025 adds **no test** and removes none — the marker is a decorator on an
  existing test; the mechanism change is in conftest + pytest.ini. **Total stays 216.**
- **Commit / push / CI:** committed `94bbf0f` on master, pushed, local == remote. **CI run `30069882143` GREEN on BOTH legs** — test (3.11) + test (3.14) success.

---

## STOPPED / attempts / changed-but-not-asked
- **STOPPED at:** nothing in WO-025 (§1 and §2 matched expectation; §3–§5 completed). The prior §1
  name-match STOP (site 29 = race #5) is recorded and drove §5's annotation.
- **Every attempt (0.5):** the bite proof was authored and run once per direction; no failed/retried
  edits. The §1 arithmetic was resolved by reading the committed ledger, not by re-running.
- **Changed but not asked?** Only: `conftest.py` (marker mechanism), `pytest.ini` (marker registration),
  `tests/integration/test_clock_injection_gate.py` (one marker decorator), the new decision log, this
  report, `progress.md` (WO-025 block + annotation), and `evidence/WO-025/` + the regenerated
  `evidence/WO-024-PASS1/gate_ledger.txt`. `instructions.md` carries the WO text. **No production logic.**
