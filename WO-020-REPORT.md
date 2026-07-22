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

### 4. §4 verify against a real CI run — **BLOCKED (reported, not worked around)**
`gh` is not installed (confirmed: `command -v gh` empty) and the repo is private with no `GITHUB_TOKEN`,
so the real run's log cannot be fetched from the shell. Per §69 this is reported as a **blocker** rather
than substituting a local run for a CI observation. The push below triggers CI; observing that
**(a)** `import-linter lint` evaluates contracts with its count, **(b)** the randomized step's seed, and
**(c)** the preflight step run — requires `gh run view` (install `gh`) or the browser capture. The local
bite proof establishes the commands behave correctly; it does **not** establish CI executed them (that is
exactly 5.2's doctrine, and it applies to this WO's own closure).

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
- **What could not be completed, and why?** §4 real-CI observation — `gh` unavailable, repo private, no
  token. Reported as a blocker (§69), not substituted. The pytest step itself may still fail in CI for the
  reason WO-019 could not reproduce (no local 3.11); that is expected and OUT OF SCOPE — the point here is
  that the VERIFICATION steps now verify.

---
**STOP for review.** Did not fix the pytest failure or begin the taxonomy migration. Recommend installing
`gh` (or a browser capture) to complete §4 — confirm `import-linter lint` runs with its count, the
randomized seed prints, and the preflight step executes in the real run.
