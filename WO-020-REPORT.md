# WO-020 — REPORT: CI Verification-Surface Repair

**Baseline `e8eeaf1`** (b7b18ce + WO-019 evidence). Preflight: `git status --porcelain` showed only the
lead's uncommitted `instructions.md`; 215 both orders / 6-6 / 6-6 / ruff clean carried in.
Changes CI config + a dev-requirements file only — **no source, no tests, no runtime dependency.**
NO VENUE CONNECTION. HTTPS: YES (a fresh `pip install` fetches). Evidence: `evidence/WO-020/`.

---

### 1. §1 import-linter step repaired — bite proof (4 artifacts, sha256, CI's exact command)
`evidence/WO-020/import_linter_step_bite_proof.txt`. Broke a real contract (appended a direct adapter
import to `src/trading/loop/live.py`), ran **CI's exact commands** locally, captured to real files (not
`/dev/null` — Git-Bash's `/dev/null` triggers a local Rich exit-1 artifact absent on ubuntu CI):

| artifact | command | result |
|---|---|---|
| 1 | `import-linter` (BARE — ci.yml line 32 today), contract broken | prints help, **exit 0** — the no-op, proven real |
| 2 | `import-linter lint`, same broken contract | **exit 1**, names 3 broken contracts (`trading.loop.live -> trading.data.adapters.kraken_v2_book (l.454)`) |
| 3 | `import-linter lint`, after byte-exact restore | 6 kept / 0 broken, **exit 0** |
| 4 | exact restore | `git diff` empty; **sha256 BEFORE == AFTER** (`a60a540e…`) — restore via `cp` backup, not `git checkout` (which renormalizes CRLF) |

**Both halves pasted** — the old-form-exits-0 half is the only artifact that ever shows the defect was real.
`ci.yml`: `import-linter` → `import-linter lint`. Confirmed `import-linter lint` exits 0 with full output
when redirected to a real file (as CI captures), so the repair does not introduce a red-while-fine step.

### 2. §2 randomized-ordering gap repaired
`pytest-randomly>=3.12.0` added to `requirements-dev.txt` (it was in the dev env but absent from CI, so CI
never randomized). `ci.yml` now runs **both orders** like the local gate:
- deterministic: `pytest tests/ -p no:randomly -rX --cov=…` (writes coverage);
- randomized: `pytest tests/ -rX` with **`if: always()`** so the seed prints even if the deterministic
  run fails.

**Is the seed visible?** YES — pytest-randomly prints `Using --randomly-seed=N` in the session header by
default (locally observed: `Using --randomly-seed=3923004112`). In CI it will appear in the randomized
step's log. *(Actual-CI paste pending §4 — see below.)*

### 3. §3 D10 folded in
**What D10 asks** (`docs/decisions/2026-07-19-instrument-pointed-at-wrong-tree.md`, WO-010 §2): a preflight
path assertion that hard-fails if the resolved `trading` package is not inside the repo tree; its "Known
gap" states the standalone form is **"not yet wired into `.github/workflows/ci.yml`"** and recommends
wiring it so the guard runs **"before the import-linter step there too."**
**Was it satisfied?** PARTIALLY — `conftest.pytest_sessionstart` runs the identical assertion
(`assert_package_path_inside_repo`) + the contract-count guard, but at the **pytest step, after**
import-linter; D10 specifically wanted it **before**. So I wired the standalone
`python tools/preflight_path_check.py` as a step **before** import-linter (verified non-no-op: it has a
`__main__` → `raise SystemExit(main())`, prints PASS/FAIL, exit 0 here). `pytest_sessionstart` remains as
defense-in-depth at the pytest step.
**Confirmed by CI observation or code reading?** Code reading + the WO-019 clean-venv reproduction (which
showed `[preflight] trading package OK` at `pytest_sessionstart`). **Actual-CI confirmation is pending §4.**

### 4. §4 verify against a real CI run — **COMPLETE** (gh made available post-push; run 29955008418)
`evidence/WO-020/real_ci_run_observation.txt`. `gh` was authenticated in another terminal after the push,
so §4's blocker was resolved and the real run observed directly. **All three repairs confirmed working in
real CI** (job `test (3.11)`, ubuntu, Python 3.11.15):
- **(a) `import-linter lint` actually evaluates contracts** (no longer the bare no-op): step passed with
  `Analyzed 61 files, 206 dependencies … Contracts: 6 kept, 0 broken.`
- **(b) randomized step's seed is visible:** `Using --randomly-seed=1608462615`.
- **(c) preflight ran:** the new standalone step passed ✓, and `pytest_sessionstart` also printed
  `[preflight] trading package OK: /home/runner/work/.../src/trading/__init__.py` and
  `[preflight] import-linter evaluated 6/6 contracts` — D10 confirmed **by CI observation**, as §3 required.

**The pytest step still fails — expected and out of scope (§4/OUT-OF-SCOPE); reported, not fixed.** But the
premise is now demolished twice over. It is **not** `ModuleNotFoundError` (the shape assumed for ten WOs)
and **not** environmental — it is a **`NameError: name 'AsyncIterator' is not defined`** at
`src/trading/data/adapters/kraken_v2_book.py:2300` (`-> AsyncIterator[MarketState]`), causing
`Interrupted: 31 errors during collection`, exit 2. **H2 confirmed** with mechanism: `AsyncIterator` is
used as a return annotation at lines 2300/2718 but never imported (line 20 imports only
`Optional, List, Dict`; no `from __future__ import annotations`). Python **3.11 evaluates annotations
eagerly** → NameError at class definition; Python **3.14 defers them (PEP 649)** → masked, which is exactly
why the WO-019 local 3.14 run passed 215. The fix (import `AsyncIterator`, or add `from __future__ import
annotations`) is a one-file production change — **left for the version-ruling successor, not touched here.**

### 5. Decision-log entries — `docs/decisions/2026-07-22-verification-steps-can-host-the-defect.md`
Both pasted verbatim: **5.1** ("green-while-checking-nothing at three layers … ANY LAYER THAT REPORTS
VERIFICATION CAN HOST THIS DEFECT") and **5.2** ("AN INFERENCE FROM CI BEHAVIOR IS ONLY AS GOOD AS PROOF
THAT THE CI STEP EXECUTED").

### 6. Verification (local gate)
- Deterministic (`-p no:randomly`): **215 passed (246.01s)**. Randomized (`--randomly-seed=20260722`,
  seed line printed: `Using --randomly-seed=20260722`): **215 passed (246.44s)**.
  0 failed / xfailed / xpassed both orders. **Delta vs 215 baseline: 0** — as expected; this WO changed
  `ci.yml` + `requirements-dev.txt` only, no test or source `.py`. `lint-imports` 6/6; `contract_count_check`
  6/6; `ruff` clean. Secret scan: 0 hits. **local HEAD == remote HEAD:** pushed; hashes in the delivery.
- **Does this affect what ships?** **NO** — CI workflow + dev-only test dependency; no runtime dependency,
  no `pyproject.toml`/source change.

### 7. Answers
- **Venue connection?** NO. **HTTPS?** YES (pip fetches during a fresh install; none performed here beyond
  the WO-019 venv already built — this WO only edits config + requirements).
- **Prose standing in for output?** NO — the bite proof, the linter outputs, and the seed line are pasted
  tool output.
- **Changed but not asked?** None. Files: `.github/workflows/ci.yml` (§1/§2/§3), `requirements-dev.txt`
  (§2), `docs/decisions/2026-07-22-verification-steps-can-host-the-defect.md` (§5),
  `evidence/WO-020/import_linter_step_bite_proof.txt`, this report. `instructions.md` (lead's WO text) not
  committed.
- **What could not be completed, and why?** Nothing outstanding. §4 was momentarily blocked (no `gh`), then
  completed once `gh` was authenticated — the real run (29955008418) was observed and all three repairs
  confirmed. The pytest step still fails, but that is expected/out of scope, and its cause is now IDENTIFIED
  (the `AsyncIterator` NameError above, H2 confirmed) — the fix awaits the lead's version ruling.

---
**STOP for review.** Did not fix the pytest failure or begin the taxonomy migration. Recommend installing
`gh` (or a browser capture) to complete §4 — confirm `import-linter lint` runs with its count, the
randomized seed prints, and the preflight step executes in the real run.
