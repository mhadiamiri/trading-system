"""WO-050 §6 BITE PROOF — backtest accounting. Four artifacts, sha256 exact-restore.

    python tools/wo050_accounting_bite_proof.py

TWO MUTATIONS, EACH FAILING A DIFFERENT FIX:

  MUTATION R1 — revert force-flat to zeroing the variable with no closing trade (the WO-048 defect,
      and the specimen behind D49). The R1 bite must fail — no trade, non-zero residual — while the
      R1 DUAL (a segment ending flat produces no spurious close) still passes, and R3's pure
      accounting tests are untouched because they never go through the runner.

  MUTATION R3 — revert the position ledger to unmatched cash flow (`+notional` SELL / `−notional`
      BUY, the walking-skeleton figure). The R3 bite must fail on the case where the two methods
      DIVERGE, while R1's runner-level tests still pass — the close still executes, it is only
      valued wrongly.

§0.10 — THE DISCRIMINATION SETS HOLD ONLY SINGLE-PURPOSE TESTS. Broad and contract tests
(`test_segmented_backtest.py`'s S13 anti-splice test, the aggregate contract test) are EXCLUDED and
reported as `broad_failed`, so their failure under a mutation is visible as expected behaviour
rather than mistaken for evidence. WO-049's first run failed precisely by putting broad tests in the
sets; that exclusion is recorded here rather than remembered.

Writes to .artifacts/ (WO-032 §4.1).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEGMENTED = os.path.join(REPO, "src", "trading", "backtest", "segmented.py")
PNL = os.path.join(REPO, "src", "trading", "backtest", "position_pnl.py")
TESTS = "tests/test_backtest_accounting.py tests/test_segmented_backtest.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo050_accounting_bite_proof")

# ── MUTATION R1: the close stops executing (back to zeroing the variable) ─────────────────────
R1_ANCHOR = [
    "            self._execution_client.set_market_state(last_state)",
    "            close_fill = await self._execution_client.place_order(",
]
R1_MUTANT = [
    "            position = dataclasses.replace(position, current_quantity=Decimal('0'))",
    "            close_fill = None if True else await self._execution_client.place_order(",
]

# ── MUTATION R3: realised P&L reverts to unmatched cash flow ──────────────────────────────────
R3_ANCHOR = [
    "        realised = (price - self.average_cost) * closing * direction",
]
R3_MUTANT = [
    "        realised = -(price * closing * direction)   # MUTATED: unmatched cash flow",
]

# SINGLE-PURPOSE sets (§0.10).
R1_BITE = {"test_r1_bite_a_segment_ending_long_produces_a_costed_closing_trade"}
R1_DUAL = {"test_r1_dual_a_segment_ending_flat_produces_no_spurious_close"}
R3_BITE = {
    "test_r3_bite_a_round_trip_realises_the_correct_pnl",
    "test_r3_crossing_zero_does_not_carry_the_old_basis",
    "test_r3_a_short_realises_the_opposite_sign",
}
R4_TESTS = {
    "test_r4_fees_and_slippage_differ_under_the_defaults",
    "test_r4_a_real_fill_produces_different_fee_and_slippage",
}
# BROAD / CONTRACT — excluded from every discrimination set, reported for visibility (§0.10).
BROAD_TESTS = {
    "test_anti_splice_bite_and_preservation_dual",
    "test_the_aggregate_states_why_the_sum_is_valid",
    "test_force_flat_is_a_labelled_event_with_its_declared_cost",
}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _nl(t):
    return "\r\n" if "\r\n" in t else "\n"


def run_tests():
    p = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS.split(), "-p", "no:randomly", "-v",
         "--tb=line", "-q"],
        cwd=REPO, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    failed = set(re.findall(r"(test_\w+)", "\n".join(
        l for l in out.splitlines() if "FAILED" in l)))
    passed = set(re.findall(r"(test_\w+)\s+PASSED", out))
    tail = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    return {
        "returncode": rc,
        "summary": tail[-1].strip() if tail else "(no summary)",
        "r1_bite_failed": sorted(failed & R1_BITE),
        "r1_dual_failed": sorted(failed & R1_DUAL),
        "r3_bite_failed": sorted(failed & R3_BITE),
        "r4_failed": sorted(failed & R4_TESTS),
        "r1_dual_passed": len(passed & R1_DUAL),
        "broad_failed": sorted(failed & BROAD_TESTS),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<18} {v}")
    lines.append(f"  EXPECT: {expectation}")
    return lines + [""]


def _mutate(path, anchor_lines, mutant_lines):
    original = open(path, "rb").read()
    text = original.decode("utf-8")
    nl = _nl(text)
    anchor, mutant = nl.join(anchor_lines), nl.join(mutant_lines)
    assert text.count(anchor) == 1, (
        f"anchor in {os.path.basename(path)} is not unique (found {text.count(anchor)}) — "
        f"refusing to mutate blindly")
    open(path, "wb").write(text.replace(anchor, mutant, 1).encode("utf-8"))
    return original


def main():
    seg_before, pnl_before = sha256(SEGMENTED), sha256(PNL)

    out = ["WO-050 §6 BITE PROOF — BACKTEST ACCOUNTING (R1 close, R3 P&L, R4 cost channels).",
           "Four artifacts, sha256 exact-restore. Two mutations, each failing a DIFFERENT fix.",
           f"  segmented.py    sha256 BEFORE : {seg_before}",
           f"  position_pnl.py sha256 BEFORE : {pnl_before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; nothing failed")

    original = _mutate(SEGMENTED, R1_ANCHOR, R1_MUTANT)
    try:
        out += ["  MUTATION R1: force-flat reverts to zeroing the variable — no closing trade", ""]
        d2 = digest(*run_tests())
    finally:
        open(SEGMENTED, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION R1 (the WO-048 defect restored)", d2,
                 "the R1 BITE fails (no trade, non-zero residual); the R1 DUAL still passes")

    original = _mutate(PNL, R3_ANCHOR, R3_MUTANT)
    try:
        out += ["  MUTATION R3: realised P&L reverts to unmatched cash flow", ""]
        d3 = digest(*run_tests())
    finally:
        open(PNL, "wb").write(original)
    out += block("ARTIFACT 3 — MUTATION R3 (unmatched cash flow restored)", d3,
                 "the R3 BITE fails on the DIVERGING case; R1's runner tests still pass")

    d4 = digest(*run_tests())
    out += block("ARTIFACT 4 — RESTORED", d4, "returncode 0; nothing failed")

    seg_after, pnl_after = sha256(SEGMENTED), sha256(PNL)
    exact = (seg_after == seg_before) and (pnl_after == pnl_before)
    out += ["-- sha256 EXACT-RESTORE --",
            f"  segmented.py    AFTER : {seg_after}",
            f"  position_pnl.py AFTER : {pnl_after}",
            f"  IDENTICAL             : {exact}", ""]

    r1_disc = bool(d2["r1_bite_failed"]) and not d2["r1_dual_failed"] and not d2["r3_bite_failed"]
    r3_disc = bool(d3["r3_bite_failed"]) and not d3["r1_bite_failed"]
    out += [f"  MUTATION R1 discriminates (R1 bite fails, R1 dual + R3 hold) : {r1_disc}",
            f"  MUTATION R3 discriminates (R3 bite fails, R1 holds)          : {r3_disc}",
            "",
            "  §0.10 — BROAD/CONTRACT TESTS ARE EXCLUDED FROM THE DISCRIMINATION SETS.",
            "  They exercise several properties at once, so they fail under either mutation and",
            "  attribute nothing. Reported here as `broad_failed` so their failure is visible as",
            "  EXPECTED rather than mistaken for evidence (WO-049's first run failed by putting",
            "  exactly such tests in the sets).",
            ""]

    ok = (d1["returncode"] == 0 and not d1["r1_bite_failed"] and not d1["r3_bite_failed"]
          and d2["returncode"] != 0 and r1_disc
          and d3["returncode"] != 0 and r3_disc
          and d4["returncode"] == 0 and not d4["r1_bite_failed"] and exact)
    out += [f"VERDICT: {'PASS' if ok else 'FAIL'}"]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    assert exact, "SRC NOT RESTORED — aborting"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
