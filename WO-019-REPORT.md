# WO-019 — REPORT: CI Failure Diagnosis via Clean-Environment Reproduction

**Baseline `b7b18ce`. Diagnosis only — no source, CI, or `pyproject.toml` change.** NO VENUE CONNECTION.
Evidence: `evidence/WO-019/` (`diagnosis.txt`, `clean_venv_314_result.txt`, `ci_import_linter_is_noop.txt`,
`interpreters_available.txt`).

---

### 1. What CI actually does (quoted from `.github/workflows/ci.yml`)
- **runner** `ubuntu-latest`; **python** `"3.11"` (matrix; CI reports 3.11.15); **workdir** repo root.
- **install (order):** `pip install --upgrade pip` → `pip install setuptools wheel` →
  `pip install -r requirements-dev.txt` → `pip install -e .`
- **steps:** checkout → setup-python → install → **`import-linter`** (bare, line 32) →
  **`pytest --cov=src/trading --cov-report=xml --cov-report=term`** (bare, line 35) → upload coverage.
- Note: pytest is invoked **bare** — no `tests/` path, no `-p no:randomly`.

### 2. Clean-venv result on 3.14 — **PASS**
Faithful reproduction: `git archive HEAD` → scratch dir, fresh venv on 3.14.6 (**not** the dev env),
CI's install sequence verbatim, then CI's exact commands.
- Install: all four steps clean (editable wheel built for `trading-system 0.1.0`).
- pytest (bare, clean venv, 3.14.6): **collected 215 → 215 passed in 247.03s → exit 0.**
  **No `ModuleNotFoundError`, no collection failure.** (`pytest.ini` sets `testpaths = tests`, so the
  root `test_*.py` debug scripts are never collected — in dev or CI.)
- The described failure **does not reproduce** in a clean fresh install on 3.14. *(An earlier "exit 120"
  was a broken-pipe artifact of piping to `head`, not a failure — the un-piped run is authoritative.)*
- **No traceback to paste — the 3.14 clean run is green.**

### 3. 3.11 result — **could not run (blocker, per §44)**
`py -0` shows only **3.14** (default) and **3.13** — **no 3.11 installed.** Reported as a blocker rather
than worked around; 3.13 is not substituted (it cannot reveal a 3.11-specific *added-module* failure,
since the 3.14 run passed). `gh` CLI is also not installed, so the actual CI log could not be fetched
from the shell. **H2 is therefore untested.**

### 4. Which hypothesis holds — **H1 refuted; H2 untested; neither confirmed**
- **H1 (packaging, fails on any fresh install):** **REFUTED** — a genuinely clean install + CI's bare
  invocation passes on 3.14.
- **H2 (version, fails only on 3.11):** **UNTESTED** — no 3.11 interpreter.
- Per §4: a fresh install is not itself broken; if CI is still red, the failure is confined to the 3.11
  interpreter and/or the ubuntu runner, neither testable on this machine.

### 5. The missing module and why it resolves locally — **none identified; no guess offered (§62)**
No code path that would `ModuleNotFoundError` on 3.11 or on Linux was found: conftest's import chain
(`tools.*`) is pure stdlib and it puts `REPO_ROOT` on `sys.path`; **no platform-conditional imports**
exist (grep for winreg/msvcrt/fcntl/pwd/… = none); `tomllib` is stdlib since 3.11; packaging is standard
`find where=["src"]` and the editable install exposed every subpackage. **Load-bearing caveat:** the
"failing since WO-009" premise predates the WO-010 work that *added* `conftest.py`, the `sys.path`/`tools`
wiring, and the preflight path guards — the exact class of fix a collection-time import error calls for.
The premise may be **stale** (already fixed); this cannot be confirmed without the CI log or a 3.11 run.

### 6. Proposed fix (NOT implemented)
- **Unblock the diagnosis** (pick one): **(A)** install Python 3.11 (`py` 3.11 / python.org /
  `uv python install 3.11`) and re-run the identical clean-venv reproduction on 3.11 — one command from
  the H2 traceback or its refutation; **(B)** fetch the latest failing run's log via `gh run view
  --log-failed` (non-browser) — confirms whether CI is still red and the exact error.
- **Separate CI defects (propose only, out of scope per §23 — do NOT edit CI now):**
  CI's `import-linter` step is a **no-op** on import-linter 2.x (bare command prints help, exits 0; the
  real check is `import-linter lint` / conftest) → change to `import-linter lint`. And **`pytest-randomly`
  is missing from `requirements-dev.txt`** (present in the dev env, used by the local gate) → CI never
  exercises "both orders". Files that *would* change: `.github/workflows/ci.yml`, `requirements-dev.txt`.
  **Affects what ships?** No — both are CI/dev-tooling, not runtime deps.

### 7. Did I change anything?
**No source, CI, or `pyproject.toml` change.** Added evidence + this report only:
`evidence/WO-019/{diagnosis.txt, clean_venv_314_result.txt, ci_import_linter_is_noop.txt,
interpreters_available.txt}`, `WO-019-REPORT.md`. (`instructions.md` carries the lead's WO text —
uncommitted, never by me.) The reproduction ran in a scratch dir, leaving the working tree untouched.

### 8. Venue connection? **NO.** HTTPS? **YES** — a fresh `pip install` fetched packages from PyPI.

### 9. Prose standing in for output? **NO** — the CI steps are quoted from the workflow file; the
clean-venv result, the import-linter no-op, and the interpreter list are pasted tool output.

### 10. What could not be completed, and why?
The **3.11 leg** — no 3.11 interpreter installed (`py -0`: 3.14, 3.13 only), and `gh` is absent so the CI
log could not be fetched. H2 stays untested and no traceback exists to paste, because the 3.14 clean run
is green. The blocker is the missing interpreter, reported rather than worked around (§44).

---
**STOP for review.** Do not edit CI config, `pyproject.toml`, or source. Recommend the lead choose (A) a
3.11 run or (B) the CI-log fetch to obtain the traceback the version ruling waits on.
