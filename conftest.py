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

from tools.preflight_path_check import (  # noqa: E402
    PreflightPathError,
    assert_package_path_inside_repo,
)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Abort the session unless the trading package is the one in this repo."""
    try:
        resolved = assert_package_path_inside_repo()
    except PreflightPathError as exc:
        # exit() aborts collection outright — this cannot be caught by a test,
        # marked xfail, or skipped.
        pytest.exit(f"\n{exc}\n", returncode=1)
    else:
        print(f"\n[preflight] trading package OK: {resolved}")
