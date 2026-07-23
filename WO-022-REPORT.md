# WO-022 — REPORT: Baseline-Test Injection + Gap-Ordering Assertion + Two Declared Records

**Baseline `1ac936b`** (CI run `29979272148`: verification surface green both legs; 8 failed identically
on both with `MEAN_CYCLE_BASELINE_HOST_MISMATCH`). **TESTS + DOCS ONLY — no production behavior changed.**
NO VENUE CONNECTION. **HTTPS: YES** (3.11 clean venv built via uv/pip). Evidence in-line + the decision log.

---

### 1. The injection (§1) — mechanism + the synthetic fixture
8 host-scoped tests now **inject** a baseline via `MEAN_CYCLE_BASELINE_STORE` (the seam `host_baseline`
already documents), instead of relying on the dev machine's ambient `config/mean_cycle_baselines.json`.
The fixture (`tests/integration/conftest.py`, `injected_baseline`) writes a store keyed by
`fingerprint_key(host_fingerprint())` → an **obviously synthetic** record. **Pasted:**

```python
SYNTHETIC_BASELINE_RECORD = {
    "fingerprint": {"machine_id": "FIXTURE-NOT-A-REAL-HOST", "python_version": "0.0.0-fixture",
                    "os": "Fixture OS (synthetic)", "cpu_arch": "fixture-arch"},
    "instrument": "full-loop",
    "mean_cycle_seconds": 0.999999,          # sentinel; NOT the real ~0.1087s figure
    "date": "FIXTURE-NOT-A-REAL-DATE",
    "derivation": "SYNTHETIC WO-022 TEST FIXTURE — ... NOT a real establishment record.",
    "load": "fixture",
    "scope": {"host": "fixture (synthetic)", "instrument": "full-loop (fixture)",
              "resolution": "fixture", "load_work": "fixture"},
    "closed_instrument_ledgers": [{"instrument": "adapter-only", "mean_cycle_seconds": 0.888888,
        "ledger_closed_date": "FIXTURE-NOT-A-REAL-DATE", "superseded": [{"mean_cycle_seconds": 0.777777}]}],
}
```
**Unmistakably synthetic at a glance:** the fingerprint is a *label* not a 16-hex hash, every number is a
repeating-digit sentinel, and the derivation says so in words. It is not a copy of any dev-machine entry.
Applied to the 6 `test_live_capture.py` runner tests (which construct `LiveCaptureRunner`, whose
`_preflight` calls `load_baseline()`) and the 2 gate tests (`test_this_host_resolves_its_injected_baseline`,
`test_active_ledger_schema_is_full_loop_with_the_adapter_only_ledger_closed` — both renamed to drop the
"this host" environment framing; the structural gate now references `injected_baseline`'s values, so it
round-trips the schema through a real JSON store without reading the production config).

### 2. Production behavior UNCHANGED, refusal still bite-proved
No production code path changed (the only production edit is a **docstring**, §3.2). The runner still
refuses on a host with NO baseline: `test_runner_refuses_host_with_no_baseline` still **passes** (verified
in the targeted run: `test_mean_cycle_baseline_gate.py ........` = 8 passed, and the full both-interpreter
runs below). If injection had made the refusal path unreachable that test would fail — it does not.

### 3. §2 — gap-ordering assertion → `<=`
`tests/integration/test_gap_recording.py::test_overlapping_gaps_union_and_collective_close`:
`max(open_a, open_b) < close` → **`<=`**, with the docstring/comment stating **why**: the monotonic
clock's resolution can collapse two opens (and the close) to one value; **identity is carried by `gap_id`**
(a per-run open-sequence counter, asserted distinct), not by temporal separation — which no consumer
requires (`evidence/WO-021/gap_ordering_diagnosis.txt`). The comment explicitly warns against tightening
it back to `<`.

### 4. Two declared records
- **§3.1 decision log** — `docs/decisions/2026-07-23-an-environment-is-strict-along-axes.md`: the
  detector-symmetry entry ("an environment is not strict or lax — it is strict along axes") + the standing
  corollary ("WHEN A TEST FAILS ON EXACTLY ONE ENVIRONMENT … WHICH AXIS IS THIS ENVIRONMENT STRICT ON …
  a single-host failure is a DETECTOR REPORT until diagnosed"). Pasted verbatim in the file.
- **§3.2 declared limit** — zero-duration gaps, in the `GapLedger` docstring
  (`kraken_v2_book.py`), standing form: **caught** (gaps longer than the host tick, accurate duration);
  **not caught** (sub-tick gaps record duration 0 — still real, unmeasured width; never filtered — inclusive
  bounds); **uncaught case** (total gap time under-estimates by ≤ one tick/gap, negligible at observed
  reconnect rates); **scope** (matters most on the Windows corpus host — the coarser tick).

### 5. §4 — reader requirement recorded in `progress.md` (NOT implemented)
Added under a new authoritative **CORPUS PRECONDITIONS (now complete — six)** block: the hard spec
"**A ZERO-DURATION GAP IS A REAL GAP AND TRIGGERS DEFAULT-DENY** … when the reader is built, its bite proof
includes a zero-duration-gap fixture: request a window spanning it without acknowledgment, watch the
refusal," plus the gap-duration resolution limit. Recorded only — confirmed not implemented.

### 6. Verification — BOTH interpreters, both orders
- **3.14 (local working tree):** deterministic → **215 passed (246.65s)**; randomized `--randomly-seed=20260723` → **215 passed (246.52s)**.
- **3.11 (clean venv, Windows — where §2 is verifiable):** deterministic → **215 passed (245.81s)**; randomized
  `--randomly-seed=20260723` → **215 passed (245.92s)**.
- 0 failed / xfailed / xpassed everywhere including Windows/3.11. `lint-imports` 6/6; `contract_count_check`
  6/6; `ruff` clean; `annotation_name_scan` 0. Secret scan: 0. **Delta:** the 8 previously-failing baseline
  tests + the gap-ordering test now pass on 3.11; 2 gate tests renamed. **local == remote HEAD:** in delivery.
- **Real CI (both legs):** __CI__

### 7. Answers
- **Affects what ships?** **NO behavior change.** The only production-file edit is a **docstring** (§3.2 in
  `kraken_v2_book.py`) — it ships as text but changes no runtime behavior; everything else is tests + docs.
- **Hot-path judgment:** **NOT hot path, no re-baseline.** Test-only + a docstring; zero per-frame code
  touched. "When in doubt re-baseline" argued out: nothing on the loop's per-frame path changed.
- **Venue connection?** NO. **HTTPS?** YES (uv/pip built the 3.11 venv).
- **Prose standing in for output?** NO — fixture pasted; both-interpreter runs and CI observation are tool output.
- **Changed but not asked?** None. Files: `tests/integration/conftest.py` (new fixture),
  `tests/integration/test_live_capture.py` (6 signatures), `tests/integration/test_mean_cycle_baseline_gate.py`
  (2 tests), `tests/integration/test_gap_recording.py` (§2), `src/trading/data/adapters/kraken_v2_book.py`
  (§3.2 docstring only), `docs/decisions/2026-07-23-an-environment-is-strict-along-axes.md` (§3.1),
  `progress.md` (§4), this report. `instructions.md` not committed.
- **What could not be completed?** Nothing outstanding pending the CI observation (§6 `__CI__`), which is
  the closure condition and is observed, not believed. Local both-interpreter runs are all green.

---
**STOP for review.** Did not begin the taxonomy migration.
