"""
Preflight path assertion (WO-010 §2).

The guard beneath the guards.

Four times this project has been misled by tooling that analysed or executed a
different tree than the one under review: stale module invocation, CI building an
unknown commit, the editable-install rebind to %TEMP%\\ci-sim2, and import-linter
analysing a stale clone for six work orders.

This check answers one question before any other check is trusted:
**is the `trading` package we just imported the one inside this repository?**

Usage:
    python tools/preflight_path_check.py     # standalone, for CI; exit 1 on failure
    from tools.preflight_path_check import assert_package_path_inside_repo
"""

from __future__ import annotations

import sys
from pathlib import Path

# This file is <repo_root>/tools/preflight_path_check.py
REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SRC = REPO_ROOT / "src"


class PreflightPathError(AssertionError):
    """Raised when the resolved trading package lies outside the repo tree."""


def resolve_trading_package_path() -> Path:
    """Import `trading` and return its resolved __init__.py path."""
    import trading

    if getattr(trading, "__file__", None) is None:
        raise PreflightPathError(
            "PREFLIGHT PATH CHECK FAILED: the `trading` package has no __file__ "
            "(namespace package?). Cannot prove which tree is being executed.\n"
            f"  expected inside: {EXPECTED_SRC}"
        )
    return Path(trading.__file__).resolve()


def assert_package_path_inside_repo() -> Path:
    """
    Hard-fail unless the resolved `trading` package is inside <repo>/src.

    Returns the resolved path on success. Raises PreflightPathError otherwise.
    """
    resolved = resolve_trading_package_path()

    if not resolved.is_relative_to(EXPECTED_SRC):
        stale_hint = ""
        if "Temp" in resolved.parts or "temp" in resolved.parts:
            stale_hint = (
                "\n  This looks like a stale editable install pointing at a temp "
                "tree.\n  Remedy: run `pip install -e .` from the repository root, "
                "and remove\n  any leftover __editable__*.pth entries that name a "
                "temp directory."
            )
        raise PreflightPathError(
            "PREFLIGHT PATH CHECK FAILED: the imported `trading` package is NOT "
            "inside this repository.\n"
            f"  resolved path : {resolved}\n"
            f"  expected root : {REPO_ROOT}\n"
            f"  expected under: {EXPECTED_SRC}\n"
            "  Refusing to proceed: any contract or test result produced now would "
            "describe a different tree." + stale_hint
        )

    return resolved


def main() -> int:
    try:
        resolved = assert_package_path_inside_repo()
    except PreflightPathError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: trading package resolves inside the repo tree\n  {resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
