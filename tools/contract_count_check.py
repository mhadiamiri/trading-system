"""
Contract-count assertion (WO-010b).

The second guard beneath the guards.

`tools/preflight_path_check.py` proves the instrument is pointed at the right
tree. It cannot prove the instrument actually RAN. A malformed import-linter
config — e.g. `forbidden_modules = ["unittest.mock"]`, which is rejected because
subpackages of external packages are not valid — causes import-linter to abort
having evaluated ZERO contracts, while the config still *looks* configured.

That is the same meta-defect as the stale tree (green while checking nothing),
but it needs no environment error at all: a typo does it, and the path assertion
cannot catch it because the path is correct and the COUNT is zero.

This check asserts that the expected NUMBER of contracts was actually evaluated.

Note: broken contracts are NOT a failure here. As of WO-010 one contract is
intentionally red ("No test doubles in production code", pending WO-008b-A).
This guard is about *how many contracts ran*, not whether they passed.

Usage:
    python tools/contract_count_check.py     # standalone, for CI; exit 1 on failure
    from tools.contract_count_check import assert_contract_count
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# ── PINNED EXPECTED CONTRACT COUNT ──────────────────────────────────────────
# The number of contracts declared in [tool.importlinter] in pyproject.toml.
# Stated explicitly and deliberately: if a contract is added or removed, this
# number MUST be updated in the same commit. A silent drift here is exactly the
# failure this guard exists to prevent.
#
# 6 = ML-in-risk, execution-adapters, v2-book-checksum, loop-adapters,
#     registry-sole-path, no-test-doubles
EXPECTED_CONTRACT_COUNT = 6
# ────────────────────────────────────────────────────────────────────────────

_SUMMARY_RE = re.compile(r"Contracts:\s+(\d+)\s+kept,\s+(\d+)\s+broken", re.I)
_RESULT_LINE_RE = re.compile(r"^\s*(.+?)\s+(KEPT|BROKEN)\s*$", re.M)


class ContractCountError(AssertionError):
    """Raised when import-linter did not evaluate the expected contract count."""


def _import_linter_executable() -> str:
    """Locate the import-linter console script (same one CI invokes)."""
    for name in ("import-linter", "lint-imports"):
        found = shutil.which(name)
        if found:
            return found
    raise ContractCountError(
        "CONTRACT COUNT ASSERTION FAILED: import-linter executable not found on "
        "PATH.\n  Looked for: import-linter, lint-imports\n"
        "  Cannot verify contracts ran at all."
    )


def run_import_linter() -> str:
    """Run import-linter and return combined stdout+stderr (exit code ignored).

    Exit code is deliberately ignored: import-linter exits non-zero when
    contracts are BROKEN, which is not what this guard measures.
    """
    proc = subprocess.run(
        [_import_linter_executable(), "lint"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return proc.stdout + proc.stderr


def assert_contract_count(output: str | None = None) -> int:
    """
    Hard-fail unless import-linter evaluated exactly EXPECTED_CONTRACT_COUNT
    contracts. Returns the evaluated count on success.
    """
    if output is None:
        output = run_import_linter()

    match = _SUMMARY_RE.search(output)
    if match is None:
        raise ContractCountError(
            "CONTRACT COUNT ASSERTION FAILED: import-linter produced NO contract "
            "summary line.\n"
            "  ZERO contracts were evaluated — the instrument reported nothing "
            "while appearing configured.\n"
            f"  expected contracts: {EXPECTED_CONTRACT_COUNT}\n"
            "  This usually means the [tool.importlinter] config is malformed.\n"
            "  ----- import-linter output -----\n"
            + "\n".join(f"  | {line}" for line in output.strip().splitlines())
        )

    kept, broken = int(match.group(1)), int(match.group(2))
    evaluated = kept + broken

    if evaluated != EXPECTED_CONTRACT_COUNT:
        named = [f"{n} [{s}]" for n, s in _RESULT_LINE_RE.findall(output)]
        raise ContractCountError(
            "CONTRACT COUNT ASSERTION FAILED: wrong number of contracts "
            "evaluated.\n"
            f"  expected : {EXPECTED_CONTRACT_COUNT}\n"
            f"  evaluated: {evaluated}  ({kept} kept, {broken} broken)\n"
            "  A contract was added or removed without updating "
            "EXPECTED_CONTRACT_COUNT in tools/contract_count_check.py,\n"
            "  or part of the config failed to load.\n"
            "  contracts seen:\n"
            + "\n".join(f"    - {n}" for n in named)
        )

    return evaluated


def main() -> int:
    try:
        evaluated = assert_contract_count()
    except ContractCountError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: import-linter evaluated {evaluated} contracts (expected "
          f"{EXPECTED_CONTRACT_COUNT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
