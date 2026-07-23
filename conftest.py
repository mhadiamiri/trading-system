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


# ─────────────────────────────────────────────────────────────────────────────
# WO-024 PASS ONE §3 — THE GATE LEDGER (falsifiable acceptance instrument).
#
# The transport-migration's acceptance criterion is "216 green AND the gate never
# fires" — and "never fires" is MEASURED, not reasoned. This session-scoped hook
# WRAPS KrakenV2BookAdapter._assert_clock_transport_gate for the whole suite,
# calls the REAL gate unchanged (pure observation — it does not alter the guard's
# behaviour, so it is not "monkeypatching to make a guard pass"), and records the
# outcome of every invocation. At session end it writes the ledger and asserts
# ZERO refusals across the suite (excluding the gate's OWN test, whose refusals
# are its designed bite proof). Any refusal during pass one is a FINDING.
# ─────────────────────────────────────────────────────────────────────────────

_GATE_LEDGER: list[tuple[str, str]] = []   # (test nodeid, outcome)
_CURRENT_NODEID: str = "<unknown>"
# The guard's OWN test intentionally exercises refusals + a declared proceed (its
# S13/D37 bite proof), so it is excluded from the zero-refusal / one-declared counts.
_GATE_OWN_TEST = "tests/integration/test_clock_injection_gate.py"
_LEDGER_PATH = REPO_ROOT / "evidence" / "WO-024-PASS1" / "gate_ledger.txt"


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Record which test is about to run, so the gate wrapper can attribute its
    invocations to a nodeid (the gate fires during the test body, after this)."""
    global _CURRENT_NODEID
    _CURRENT_NODEID = item.nodeid


@pytest.fixture(scope="session", autouse=True)
def _gate_ledger_recorder():
    """Wrap the pre-connection gate for the whole session; record every outcome;
    at teardown write the ledger and assert zero refusals (excluding the gate's own
    test). The wrapper DELEGATES to the real gate and re-raises its exception
    unchanged — the guard's behaviour is identical with or without this recorder."""
    import time
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    original = KrakenV2BookAdapter._assert_clock_transport_gate

    def _recording_gate(self, incoherent_clocks_allowed):
        wall_injected = self._wall_clock is not None
        mono_injected = self._monotonic_clock is not time.monotonic
        try:
            result = original(self, incoherent_clocks_allowed)
        except ValueError as exc:
            msg = str(exc)
            if "CLOCK_INJECTION_REFUSED: COUPLING" in msg:
                outcome = "REFUSED_COUPLING"
            elif "CLOCK_INJECTION_REFUSED: COHERENCE" in msg:
                outcome = "REFUSED_COHERENCE"
            else:
                outcome = "REFUSED_OTHER"
            _GATE_LEDGER.append((_CURRENT_NODEID, outcome))
            raise
        # Returned without raising — classify how it proceeded.
        if not (wall_injected or mono_injected):
            outcome = "EARLY_RETURN"
        else:
            wall_token = getattr(self._wall_clock, "_coherence_token", None)
            mono_token = getattr(self._monotonic_clock, "_coherence_token", None)
            coherent = (wall_injected and mono_injected
                        and wall_token is not None and wall_token is mono_token)
            outcome = "PROCEED_COHERENT" if coherent else "PROCEED_DECLARED"
        _GATE_LEDGER.append((_CURRENT_NODEID, outcome))
        return result

    KrakenV2BookAdapter._assert_clock_transport_gate = _recording_gate
    try:
        yield
    finally:
        KrakenV2BookAdapter._assert_clock_transport_gate = original
        _write_gate_ledger_and_assert()


def _write_gate_ledger_and_assert() -> None:
    from collections import Counter

    # Suite-wide counts (every invocation), and counts EXCLUDING the guard's own test.
    all_counts: Counter = Counter(o for _, o in _GATE_LEDGER)
    migrated = [(n, o) for n, o in _GATE_LEDGER if not n.startswith(_GATE_OWN_TEST)]
    migrated_counts: Counter = Counter(o for _, o in migrated)
    refused = [(n, o) for n, o in migrated if o.startswith("REFUSED_")]
    declared = [n for n, o in migrated if o == "PROCEED_DECLARED"]

    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "WO-024 PASS ONE §3 — GATE LEDGER (every _assert_clock_transport_gate invocation).",
        "The gate wrapper delegates to the REAL gate and only records; behaviour is unchanged.",
        f"Total gate invocations recorded: {len(_GATE_LEDGER)}",
        "",
        "SUITE-WIDE outcome counts (includes the guard's own test):",
    ]
    for o in ("EARLY_RETURN", "PROCEED_COHERENT", "PROCEED_DECLARED",
              "REFUSED_COUPLING", "REFUSED_COHERENCE", "REFUSED_OTHER"):
        if all_counts.get(o):
            lines.append(f"  {o}: {all_counts[o]}")
    lines += [
        "",
        f"EXCLUDING the guard's own test ({_GATE_OWN_TEST} — its refusals/declared-proceed are its "
        "designed bite proof):",
    ]
    for o in ("EARLY_RETURN", "PROCEED_COHERENT", "PROCEED_DECLARED",
              "REFUSED_COUPLING", "REFUSED_COHERENCE", "REFUSED_OTHER"):
        if migrated_counts.get(o):
            lines.append(f"  {o}: {migrated_counts[o]}")
    lines += [
        "",
        f"REFUSED_COUPLING (excl. guard test): {migrated_counts.get('REFUSED_COUPLING', 0)}",
        f"REFUSED_COHERENCE (excl. guard test): {migrated_counts.get('REFUSED_COHERENCE', 0)}",
        f"PROCEED_DECLARED (excl. guard test): {migrated_counts.get('PROCEED_DECLARED', 0)}  "
        f"-> {declared}",
        "",
        "PER-INVOCATION (nodeid -> outcome):",
    ]
    for nodeid, outcome in _GATE_LEDGER:
        lines.append(f"  {outcome:<17} {nodeid}")
    _LEDGER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # THE FALSIFIABLE ASSERTION (WO-024 §3): zero refusals outside the guard's own test.
    assert not refused, (
        f"GATE FIRED during pass one (transport-only migration) — this is a FINDING, not friction. "
        f"Refusals (excluding the guard's own test): {refused}. See {_LEDGER_PATH}."
    )
