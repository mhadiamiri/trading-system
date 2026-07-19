"""
Root conftest (WO-010 §2).

Runs the preflight path assertion at session start, before any test executes.
Placed at the repository root so it loads for every pytest invocation and cannot
be bypassed by selecting a subdirectory or a single test file.

If the `trading` package resolves outside this repository, the session is aborted
immediately: test results describing a different tree are worse than no results,
because they report green.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent

# `pythonpath = src` (pytest.ini) puts src/ on the path but not the repo root,
# so make tools/ importable without altering the package layout.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.contract_count_check import (  # noqa: E402
    EXPECTED_CONTRACT_COUNT,
    ContractCountError,
    assert_contract_count,
)
from tools.preflight_path_check import (  # noqa: E402
    PreflightPathError,
    assert_package_path_inside_repo,
)


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Two assertions, one purpose (WO-010 §2, WO-010b):
    prove the instrument is pointed at the right thing, AND that it actually ran.

    Both abort the session via pytest.exit() before collection, so neither can be
    caught by a test, marked xfail, or skipped.
    """
    # Guard 1 — are we running the code we think we are?
    try:
        resolved = assert_package_path_inside_repo()
    except PreflightPathError as exc:
        pytest.exit(f"\n{exc}\n", returncode=1)
    print(f"\n[preflight] trading package OK: {resolved}")

    # Guard 2 — did the contract checker actually evaluate anything?
    # A malformed config makes import-linter report nothing while still
    # appearing configured; guard 1 cannot see that, because the path is fine
    # and the COUNT is zero.
    try:
        evaluated = assert_contract_count()
    except ContractCountError as exc:
        pytest.exit(f"\n{exc}\n", returncode=1)
    print(f"[preflight] import-linter evaluated {evaluated}/"
          f"{EXPECTED_CONTRACT_COUNT} contracts")
