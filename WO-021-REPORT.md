# WO-021 — REPORT: Annotation-Name Sweep → Targeted Fix → Version Matrix

**Baseline `a869124`** (= `cceb156` code + progress.md docs). Preflight clean (only the lead's
`instructions.md` uncommitted). NO VENUE CONNECTION. **HTTPS: YES** — `uv`/`pip` fetched packages to
build the clean 3.11 and 3.14 venvs. Evidence: `evidence/WO-021/`. Seam commit `121768c` (sweep, standalone).

---

### 1. The sweep — complete error list, every unimported name, the declared limit
`evidence/WO-021/annotation_sweep.txt`. **Two complementary instruments:**
- **3.11 collection (CI-faithful clean venv):** `pytest tests/ --collect-only` →
  `67 tests collected, 31 errors`; **all 31 errors are one root cause** —
  `NameError: name 'AsyncIterator' is not defined` at `kraken_v2_book.py:2300` (the
  `KrakenV2BookAdapter` class body), from the 31 test modules that import it.
- **Static AST scan (`tools/annotation_name_scan.py`, all 39 src modules):** finds **both** sites —
  `kraken_v2_book.py:2300` **and `:2718`**, `AsyncIterator`, and **nothing else**.

**Does the instrument see everything? NO — declared limit (standing form):** the 3.11 collection run
**aborts a class body at its FIRST bad annotation**, so line 2718 (also `AsyncIterator`) is **masked and
never appears**, and any module no test imports is never evaluated. So the WO's premise that "eager
evaluation enumerates the complete set in one run" **does not hold** — collection alone under-reports.
The static scan closes that gap (its own limit: it cannot resolve `from x import *` — none exist here;
it ignores function-local annotations, which Python never evaluates). Together: **complete denominator = 2.**

### 2. Was the count 2, or more? — exactly 2, but 1 was invisible to the CI instrument
**2 instances**, both `AsyncIterator`, both in `kraken_v2_book.py` (2300, 2718). The count equals the two
we tripped over — but that is now **measured, not assumed**: the 3.11 collection instrument alone reported
only **1** and masked the second; **1 of the 2 was invisible to every instrument that actually runs in CI**
until the static scan surfaced it. That is the WO's point about measuring the denominator before fixing.

### 3. The fix — targeted imports only, no `__future__`
One line added to `kraken_v2_book.py`: **`from collections.abc import AsyncIterator`** — the canonical home
since 3.9 (`typing.AsyncIterator` is the deprecated alias); one import covers both sites (2300, 2718).
**No `from __future__ import annotations` was added anywhere.** Report-only: `registry.py` already carries
`from __future__ import annotations` (pre-existing) — left untouched. Post-fix: static scan → **0
findings**; 3.11 `--collect-only` → **215 collected, exit 0**.

### 3b. Standing consequence — the annotation scan wired into CI (lead's update)
`tools/annotation_name_scan.py` is now a CI step on **both legs** ("Annotation-name detector"), running
before pytest. It is the complete-set detector (sees both 2300 and 2718 without aborting); the 3.11 leg is
its behavioral confirmer. On the 3.14 leg it is the ONLY instrument that can see this class (pytest is
masked by PEP 649). Bite-proved in CI form (`evidence/WO-021/annotation_scan_ci_step_bite_proof.txt`,
4 artifacts, sha256): clean → **exit 0**; inject `-> _WO021_CI_UNIMPORTED_NAME` → **exit 1 naming it at
`market_state.py:102`**; restore → exit 0; sha256 BEFORE == AFTER, git diff empty.

### 4. The matrix — `ci.yml` runs 3.11 AND 3.14
Matrix `["3.11", "3.14"]`, `fail-fast: false`, both legs the full gate (preflight → `import-linter lint`
→ both pytest orders). The intent is **commented in `ci.yml`**: 3.11 is the **STRICT/detector** leg (eager
annotation evaluation = permanent detector for a class the 3.14 dev host is structurally blind to; standing
instrumentation, not a compatibility target); 3.14 is the **development** leg (what local runs, so the two
cannot diverge again) — with an explicit "do NOT collapse to one leg and delete the detector."

### 5. §4 bite proof — strict leg is a detector, not a second run
`evidence/WO-021/strict_leg_detector_bite_proof.txt` — 4 artifacts, sha256, **both halves pasted**:
| # | step | result |
|---|---|---|
| 1 | inject `-> _WO021_BITEPROOF_UNIMPORTED`, **3.11** collect | `NameError: name '_WO021_BITEPROOF_UNIMPORTED' is not defined`, **exit 2** — detector fired |
| 2 | same injection, **3.14** collect | **215 collected, exit 0 — masked** (this half is *why the matrix exists*) |
| 3 | restore, both legs collect | 3.11 = 215/exit 0; 3.14 = 215/exit 0 |
| 4 | exact restore | **sha256 BEFORE == AFTER** (`347a08c7…`) |

### 6. Decision log — `docs/decisions/2026-07-22-interpreter-is-a-scope-dimension.md`
Both entries verbatim: **5.1** ("THE DEVELOPMENT HOST'S INTERPRETER IS A SCOPE DIMENSION OF EVERY LOCAL
GREEN … CI's value was COVERAGE OF A BLIND SPOT LOCAL STRUCTURALLY CANNOT COVER"); **5.2** ("FILE-SCOPE
SYMPTOM SUPPRESSION IS REFUSED ON THE SAME GROUNDS AS TEST-SCOPE SYMPTOM SUPPRESSION").

### 7. Verification — BOTH interpreters locally (the gate is NOT fully met — see below)
- **3.14 (local working tree):** deterministic `-p no:randomly` → **215 passed (248.41s)**; randomized
  `--randomly-seed=20260722` → **215 passed (246.63s)**. 0 failed/xfailed/xpassed. Green.
- **3.11 (clean venv, scratch): COLLECTION green** (215 collected) — the annotation fix works. But the
  **FULL 3.11 suite = 9 failed / 206 passed** (244.74s, isolated re-run — real, not contention flakes).
- `lint-imports` 6/6; `contract_count_check` 6/6; `ruff` clean. Secret scan: 0. Annotation-fix delta on
  3.14: 0 (one import line; no test added/removed).
- **Real CI:** I initially stopped before push (0.2a). The lead's update then **accepted the in-scope work
  and ruled: push it** (the annotation fix is independent of both findings, correct, complete; 3.11 red on
  the 8+1 out-of-scope failures is expected, not a regression — it is the next WO's work). **Pushed
  (`1ac936b`); real CI run `29979272148` observed, both legs:**
  - **Verification steps GREEN on BOTH legs:** preflight ✓, `import-linter lint` ✓, and the new
    **Annotation-name detector ✓** — the scan runs and passes in CI on 3.11 and 3.14.
  - **3.14 leg:** 8 failed / 207 passed (det 241.95s; rand 240.73s, seed `1343253163`).
  - **3.11 leg:** 8 failed / 207 passed (det 242.76s; rand 240.61s, seed `3203092373`).
  - **All 8 failures on BOTH legs are `MEAN_CYCLE_BASELINE_HOST_MISMATCH`** (CI fingerprint =
    Linux/`b553a51a…`, no match) — **confirming the prediction that the host-scoped baseline fails on
    every CI host regardless of interpreter, 3.14 included.** The annotation fix works: pytest now gets
    past collection (215 collected, 207 pass), failing only at runtime on the 8 baseline tests.
  - **The monotonic gap-ordering test PASSES on CI (both legs)** — it failed only on the Windows dev host
    (coarse tick); on Linux the clock is fine. That is exactly the §11 diagnosis: a Windows
    clock-resolution artifact, not a 3.11 or matrix defect. So CI shows **8**, not 9.

**THE 9 FAILURES ARE ALL OUT OF SCOPE — none is an annotation-name defect**
(`evidence/WO-021/py311_full_suite_out_of_scope_failures.txt`). The matrix's strict leg did its job and
surfaced a second, unrelated class:
- **8 of 9 — host-scoped mean-cycle baseline (WO-016 D28/D29).** `host_baseline` fingerprints the host by
  `machine_id + python_version + os + cpu_arch`. On 3.11 the fingerprint (`6b34b1f1…`, python 3.11.15)
  has no entry in `config/mean_cycle_baselines.json` (which holds one entry, `ba47c96a…`, python 3.14.6),
  so `LiveCaptureRunner` refuses (`MEAN_CYCLE_BASELINE_HOST_MISMATCH`) and the gate test hard-asserts a
  baseline exists. **Sharp consequence:** the baseline is pinned to the *dev machine*, so these 8 tests
  would fail on the GitHub CI runner (a different machine, Linux) on **both** legs, 3.14 included — "CI
  green on both legs" is **not achievable as designed**; the annotation fix merely UNMASKED it (CI never
  reached these tests before, because collection failed first).
- **1 of 9 — monotonic-clock timestamp collision**, 3.11-specific:
  `test_overlapping_gaps_union_and_collective_close`, `assert 37750.5 < 37750.5` (two gaps got identical
  `open_monotonic`). Separate diagnosis; not annotation-related.

### 8. Does this affect what ships? **YES** — a production source file (`kraken_v2_book.py`) changed
(import-only). `ci.yml` also changed (§3 matrix). `tools/` + evidence are non-shipping.

### 9. Hot-path judgment — **NOT hot path, no re-baseline.** The change is a module-level `import` executed
once at module load, not per frame; zero per-frame work. Argued out explicitly: an import statement cannot
alter per-frame cost. (`get_live_market_data` is unchanged except that its return annotation now resolves.)

### 10. Answers
- **Venue connection?** NO. **HTTPS?** YES (venv builds fetched from PyPI).
- **Prose standing in for output?** NO — sweep, bite proof, and both-interpreter runs are pasted tool output.
- **Changed but not asked?** None. Files (all UNPUSHED; only the §1 seam `121768c` is a local commit):
  `src/trading/data/adapters/kraken_v2_book.py` (§2 fix), `.github/workflows/ci.yml` (§3 matrix),
  `tools/annotation_name_scan.py` + `evidence/WO-021/annotation_sweep.txt` (§1 seam, committed),
  `evidence/WO-021/strict_leg_detector_bite_proof.txt` (§4),
  `evidence/WO-021/py311_full_suite_out_of_scope_failures.txt` (§6 finding),
  `docs/decisions/2026-07-22-interpreter-is-a-scope-dimension.md` (§5), this report. `instructions.md` not committed.
- **What could not be completed, and why?** §6's closure condition — **CI green on both legs** — was NOT
  reached, so per **0.2a I stopped before push (nothing pushed)**. The in-scope annotation work is complete
  and verified (3.14 both orders green, 3.11 collection green, static scan 0, §4 detector bite proof). The
  blocker is entirely out of scope: 8 host-scoped-baseline tests that cannot pass off the dev machine (a
  WO-016 design consequence affecting BOTH CI legs) + 1 monotonic-timing test. **These need the lead's
  ruling** — how host-scoped baseline tests should behave off the dev host (skip-when-absent / xfail /
  establish a CI baseline / mark local-only), and the timing test — before this can close and CI can go green.

### 11. Gap-ordering diagnosis (lead update §3 — report only, NOT fixed)
`evidence/WO-021/gap_ordering_diagnosis.txt`. The failing assert (line 271):
`max(open_a, open_b) < close` → on a coarse Windows monotonic tick both opens and the shared close
collapse to `37750.5`, so `37750.5 < 37750.5` fails. **Consumer enumeration** (each with its ordering
invariant): `duration_s` needs `close >= open` (tie-tolerant); `complete`/`incomplete`/`gaps_detected`
need no order; the `gaps` **list order is append == gap_id order** (not a clock compare — a tie doesn't
reorder it), and the failing test itself indexes `gaps[0]/gaps[1]` off that structural order; the
default-deny corpus reader does **interval intersection / span overlap** (order-independent, tie-tolerant);
persistence is per-event append; `test_host_suspend.py:74` already asserts `close >= open` (`>=`);
`test_ledger_persistence` keys on `gap_id`. **`gap_id` is already a per-run open-sequence counter**
(`gap_id=self._gap_seq; self._gap_seq+=1`).
**Answer: (a) — the test encodes an invariant no consumer holds.** No consumer needs strict temporal
separation; the design is tie-tolerant by construction ("union query, not containment"). The correct
(unimplemented) fix is `<=`, relying on the already-asserted distinct `gap_ids` for identity. **(b) is
unnecessary** — the per-process sequence counter it proposes already exists as `gap_id`; therefore **no
amendment to D25's clock doctrine** is needed. This is a **production** clock-resolution question (equally
present on 3.14 and the corpus host), not a matrix artifact. Not implemented, per the ruling.

---
**STATUS per the lead's update:** in-scope annotation work pushed (approved); the annotation scan wired
into CI + bite-proved; the 8 host-scoped-baseline failures ruled to a separate **injection WO** (INJECT a
synthetic baseline — NOT begun here); the gap-ordering failure is **diagnosed report-only** below (§11).
**STOP after the push and the diagnosis.** Did NOT begin the injection WO or the taxonomy migration.
