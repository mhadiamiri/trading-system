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
# WO-025 §3 — MARKER-BASED EXCLUSION (replaces the WO-024 by-name exclusion). The ledger tolerates
# gate refusals ONLY from a test that DECLARES the `gate_refusal_expected` marker ON ITSELF (its own
# S13/D37 bite proof). A marker is an identifier that cannot truncate in transit, unlike a name copied
# between documents (Finding 1 / D34-3: declared, never inferred). The check is bidirectional: a
# refusal from an UNMARKERED test fails, AND a marker on a test that produces NO refusal fails as a
# STALE MARKER — a by-name list's failure mode (it quietly grows until the net catches nothing).
_GATE_MARKER = "gate_refusal_expected"
_MARKERED_NODEIDS: set[str] = set()

# WO-026 §2 — AN INSTRUMENT STREAMS TO AN IGNORED RUN-SCOPED PATH; EVIDENCE IS A DELIBERATE SNAPSHOT.
# The WO-024/025 defect: this hook wrote directly to a COMMITTED evidence path, so every pytest run
# silently overwrote committed evidence — found in a changed-files list, not by any guard (WO-026 §1).
# Fix: the instrument now streams to `.artifacts/gate_ledger/` (git-ignored, run-scoped, NEVER
# committed, plus a `latest.txt`); a human/WO takes a deliberate provenance-stamped snapshot into
# evidence/ at close via tools/snapshot_gate_ledger.py. The output directory is MECHANICALLY forbidden
# from resolving inside evidence/ (the guard, bite-proved WO-026 §3) — enforced, not by convention.
_LEDGER_OUTPUT_DIR = REPO_ROOT / ".artifacts" / "gate_ledger"
_EVIDENCE_DIR = (REPO_ROOT / "evidence").resolve()


def _assert_ledger_dir_outside_evidence(output_dir) -> None:
    """WO-026 §2 (the mechanical guard): the ledger instrument MUST NOT write anywhere under
    evidence/. A test session that streams into a committed evidence path rewrites history on every
    run. Fail loudly if the configured output directory resolves inside evidence/."""
    from pathlib import Path
    resolved = Path(output_dir).resolve()
    if resolved == _EVIDENCE_DIR or resolved.is_relative_to(_EVIDENCE_DIR):
        raise RuntimeError(
            f"GATE_LEDGER_PATH_IN_EVIDENCE: the ledger instrument's output directory {resolved} "
            f"resolves inside {_EVIDENCE_DIR} — a test session must NEVER write under evidence/ "
            f"(WO-026 §2). Point it at a run-scoped .artifacts/ path; evidence is a deliberate "
            f"snapshot at close (tools/snapshot_gate_ledger.py)."
        )


def _run_stamp() -> str:
    """WO-026 §2: `<utc-timestamp>-<short-sha>` for the run-scoped ledger filename (never committed)."""
    import subprocess
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO_ROOT),
                             capture_output=True, text=True, timeout=5).stdout.strip() or "nogit"
    except Exception:
        sha = "nogit"
    return f"{ts}-{sha}"


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Record which test is about to run (so the gate wrapper can attribute its invocations to a
    nodeid — the gate fires during the test body, after this), and whether it declares the
    gate_refusal_expected marker (so the ledger tolerates its refusals, and only its)."""
    global _CURRENT_NODEID
    _CURRENT_NODEID = item.nodeid
    if item.get_closest_marker(_GATE_MARKER) is not None:
        _MARKERED_NODEIDS.add(item.nodeid)


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

    all_counts: Counter = Counter(o for _, o in _GATE_LEDGER)
    refused = [(n, o) for n, o in _GATE_LEDGER if o.startswith("REFUSED_")]
    refused_nodeids = {n for n, _ in refused}
    declared = [n for n, o in _GATE_LEDGER
                if o == "PROCEED_DECLARED" and n not in _MARKERED_NODEIDS]

    # WO-025 §3 — the two directions of the marker-based tolerance.
    # (1) a refusal from an UNMARKERED test is a real gate firing (a finding).
    unmarkered_refusals = [(n, o) for n, o in refused if n not in _MARKERED_NODEIDS]
    # (2) a marker on a test that produced NO refusal is a STALE MARKER (a hole opening quietly).
    stale_markers = sorted(_MARKERED_NODEIDS - refused_nodeids)

    # WO-026 §2 — the mechanical guard: the instrument writes to a run-scoped .artifacts/ path, and
    # NEVER anywhere under evidence/. Validate the configured directory before writing.
    _assert_ledger_dir_outside_evidence(_LEDGER_OUTPUT_DIR)
    _LEDGER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_path = _LEDGER_OUTPUT_DIR / f"{_run_stamp()}.txt"
    latest_path = _LEDGER_OUTPUT_DIR / "latest.txt"
    lines = [
        "WO-024/WO-025 §3 — GATE LEDGER (every _assert_clock_transport_gate invocation).",
        "The gate wrapper delegates to the REAL gate and only records; behaviour is unchanged.",
        f"Total gate invocations recorded: {len(_GATE_LEDGER)}",
        "",
        "SUITE-WIDE outcome counts (every test, markered or not):",
    ]
    for o in ("EARLY_RETURN", "PROCEED_COHERENT", "PROCEED_DECLARED",
              "REFUSED_COUPLING", "REFUSED_COHERENCE", "REFUSED_OTHER"):
        if all_counts.get(o):
            lines.append(f"  {o}: {all_counts[o]}")
    lines += [
        "",
        "WO-025 §3 MARKER-BASED TOLERANCE (declared, never inferred):",
        f"  tests carrying @pytest.mark.{_GATE_MARKER}: {sorted(_MARKERED_NODEIDS)}",
        f"  (1) refusals from UNMARKERED tests (must be empty): {unmarkered_refusals}",
        f"  (2) STALE markers — markered tests with NO refusal (must be empty): {stale_markers}",
        f"  PROCEED_DECLARED (unmarkered): {len(declared)}  -> {declared}",
        "",
        "PER-INVOCATION (nodeid -> outcome):",
    ]
    for nodeid, outcome in _GATE_LEDGER:
        mark = " [markered]" if nodeid in _MARKERED_NODEIDS else ""
        lines.append(f"  {outcome:<17} {nodeid}{mark}")
    body = "\n".join(lines) + "\n"
    run_path.write_text(body, encoding="utf-8")     # WO-026 §2: run-scoped, git-ignored
    latest_path.write_text(body, encoding="utf-8")  # convenience copy (also git-ignored)

    # THE FALSIFIABLE ASSERTION (WO-025 §3) — BOTH directions; the marker set is EXACTLY the
    # tolerated set. A stale marker FAILS (Ops's call), same weight as an unmarkered refusal.
    assert not unmarkered_refusals and not stale_markers, (
        "GATE LEDGER VIOLATION.\n"
        f"  (1) refusals from UNMARKERED tests (a real gate firing): {unmarkered_refusals}\n"
        f"  (2) STALE markers (markered tests that never refused): {stale_markers}\n"
        f"  markered set: {sorted(_MARKERED_NODEIDS)}. See {run_path}."
    )
