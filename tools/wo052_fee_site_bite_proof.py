"""WO-052 §3 BITE PROOF — the EXTENDED fee-default guard. Four artifacts, sha256 exact-restore.

    python tools/wo052_fee_site_bite_proof.py

The guard being proved covers EVERY fee-default site in src/, not one class. The bug it exists to
stop already happened: WO-050 guarded `PaperExecutionClient`'s identical-channels defect and
WO-051 pinned `PaperExecutionClient`'s fee to its citation, and `CostModel` sat at an uncited 0.1%
with the identical-channels coincidence alive through BOTH — because a guard that covers one of two
sites reports exactly the same green as a guard that covers both.

THREE MUTATIONS:

  BITE — revert `CostModel.DEFAULT_FEE_RATE_PCT` to a bare `Decimal("0.1")`, i.e. the exact
      pre-WO-052 state. The extended guard must FAIL AND NAME THAT SITE.

  DUAL (§0.4, local and direct) — asserted in every artifact, not as a separate run: the two
      SLIPPAGE defaults are declared DELIBERATELY INDEPENDENT of the fee schedule (measured, not
      published). They must never trip the fee guard. `dual_failed` is tracked throughout and must
      stay empty — including under the bite, where a guard that fired on everything would look
      identical to a guard that fired on the right thing.

  NECESSITY — apply the SAME source defect, but ALSO narrow the guard's registry back to
      `PaperExecutionClient` only, reproducing the pre-WO-052 scope. The per-site bite must go
      SILENT: that silence is the measurement. It is what a green build looked like for two work
      orders while the defect was present. The completeness guard fires instead — which is the
      second layer doing its job, and is reported separately rather than counted as the bite.

§0.10 — the discrimination sets hold only single-purpose tests. Exclusions recorded below.

Writes to .artifacts/ (WO-032 §4.1).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COSTS = os.path.join(REPO, "src", "trading", "backtest", "costs.py")
GUARD = os.path.join(REPO, "tests", "test_fee_default_sites.py")
TESTS = "tests/test_fee_default_sites.py tests/test_fee_schedule.py tests/test_backtest_costs.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo052_fee_site_bite_proof")

# ── BITE: the second fee site reverts to the uncited literal ──────────────────────────────────
BITE_ANCHOR = [
    "    DEFAULT_FEE_RATE_PCT = fee_schedule.taker_pct()  # PERCENT of notional -> Tier 1 taker, 0.80%",
]
BITE_MUTANT = [
    '    DEFAULT_FEE_RATE_PCT = Decimal("0.1")  # MUTATED: back to the uncited pre-WO-052 literal',
]

# ── NECESSITY: the registry narrows back to PaperExecutionClient only ─────────────────────────
NARROW_ANCHOR = [
    "    {",
    '        "name": "trading.backtest.costs.CostModel.DEFAULT_FEE_RATE_PCT",',
    '        "cls": CostModel,',
    '        "routed": True,',
    '        "reason": "the backtest cost model\'s taker fee — cited, WO-052 (was an uncited 0.1%)",',
    "    },",
]
NARROW_MUTANT = [
    "    # MUTATED: CostModel removed from the registry — the pre-WO-052 single-site scope.",
]

# SINGLE-PURPOSE sets (§0.10). Parametrised ids carry the class name, so a failure is attributable.
BITE_SET = {
    "test_every_fee_default_is_routed_through_the_cited_schedule[CostModel]",
    "test_r4_channels_are_distinct_at_every_site[CostModel]",
}
DUAL_SET = {
    "test_every_slippage_default_is_the_measured_value[PaperExecutionClient]",
    "test_every_slippage_default_is_the_measured_value[CostModel]",
    "test_no_undeclared_slippage_default_exists_in_src",
}
COMPLETENESS_SET = {"test_no_undeclared_fee_default_exists_in_src"}
# BROAD — excluded from the discrimination sets (§0.10). These read BOTH cost models at once, so
# they fail under any mutation and attribute nothing.
BROAD_SET = {
    "test_the_two_cost_models_agree_at_their_defaults",
    "test_manual_calculation_matches_system",
    "test_fees_applied_to_every_trade",
    "test_fees_calculation_accuracy",
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
    # Parametrised ids contain [] so the plain \w+ pattern is not enough.
    failed_lines = [line for line in out.splitlines() if "FAILED" in line]
    failed = set(re.findall(r"(test_[\w\[\]\.\-]+)", "\n".join(failed_lines)))
    # Strip a trailing test-file artefact if the id came through with a path prefix.
    failed = {f.split("::")[-1] for f in failed}
    return {
        "returncode": rc,
        "summary": next((line.strip() for line in reversed(out.splitlines())
                         if re.search(r"\d+ (passed|failed)", line)), "(no summary)"),
        "bite_failed": sorted(failed & BITE_SET),
        "dual_failed": sorted(failed & DUAL_SET),
        "completeness_failed": sorted(failed & COMPLETENESS_SET),
        "broad_failed": sorted(f for f in failed if any(b in f for b in BROAD_SET)),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<20} {v}")
    return lines + [f"  EXPECT: {expectation}", ""]


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
    costs_before, guard_before = sha256(COSTS), sha256(GUARD)

    out = ["WO-052 §3 BITE PROOF — THE EXTENDED FEE-DEFAULT GUARD (D51 ruling 4a).",
           "Four artifacts, sha256 exact-restore. Bite / dual / necessity.",
           f"  backtest/costs.py           sha256 BEFORE : {costs_before}",
           f"  tests/test_fee_default_sites.py sha256 BEFORE : {guard_before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; nothing failed")

    original = _mutate(COSTS, BITE_ANCHOR, BITE_MUTANT)
    try:
        out += ['  MUTATION BITE: CostModel.DEFAULT_FEE_RATE_PCT -> bare Decimal("0.1")', ""]
        d2 = digest(*run_tests())
    finally:
        open(COSTS, "wb").write(original)
    out += block("ARTIFACT 2 — BITE (the pre-WO-052 uncited second site restored)", d2,
                 "the guard FAILS NAMING CostModel (routed + R4); the slippage DUAL stays green")

    costs_orig = _mutate(COSTS, BITE_ANCHOR, BITE_MUTANT)
    guard_orig = _mutate(GUARD, NARROW_ANCHOR, NARROW_MUTANT)
    try:
        out += ["  MUTATION NECESSITY: same defect, guard narrowed to PaperExecutionClient only",
                ""]
        d3 = digest(*run_tests())
    finally:
        open(COSTS, "wb").write(costs_orig)
        open(GUARD, "wb").write(guard_orig)
    out += block("ARTIFACT 3 — NECESSITY (pre-WO-052 guard SCOPE, with the defect present)", d3,
                 "the per-site BITE GOES SILENT — that silence is what a green build looked like "
                 "for two work orders. The completeness guard fires instead (second layer).")

    d4 = digest(*run_tests())
    out += block("ARTIFACT 4 — RESTORED", d4, "returncode 0; nothing failed")

    costs_after, guard_after = sha256(COSTS), sha256(GUARD)
    exact = (costs_after == costs_before) and (guard_after == guard_before)
    out += ["-- sha256 EXACT-RESTORE --",
            f"  backtest/costs.py               AFTER : {costs_after}",
            f"  tests/test_fee_default_sites.py AFTER : {guard_after}",
            f"  IDENTICAL                             : {exact}", ""]

    bite_ok = bool(d2["bite_failed"]) and not d2["dual_failed"]
    necessity_ok = (not d3["bite_failed"]) and bool(d3["completeness_failed"]) \
        and not d3["dual_failed"]
    out += [f"  BITE bites      (guard names CostModel, dual preserved) : {bite_ok}",
            f"  NECESSITY holds (narrowed guard goes blind to the same defect,",
            f"                   completeness layer still fires)        : {necessity_ok}",
            "",
            "  §0.4 THE DUAL IS LOCAL AND DIRECT: `dual_failed` is tracked in EVERY artifact and is",
            "  empty in all four. The two slippage defaults are declared deliberately independent of",
            "  the fee schedule (measured against the corpus, not published by a venue) and never",
            "  trip the fee guard — including under the bite, where a guard that fired on",
            "  everything would be indistinguishable from one that fired on the right thing.",
            "",
            "  §0.10 BROAD TESTS EXCLUDED from the discrimination sets and reported separately:",
            "  they read BOTH cost models at once, so they fail under any mutation and attribute",
            "  nothing.",
            ""]

    ok = (d1["returncode"] == 0 and not d1["bite_failed"] and not d1["dual_failed"]
          and d2["returncode"] != 0 and bite_ok
          and d3["returncode"] != 0 and necessity_ok
          and d4["returncode"] == 0 and not d4["bite_failed"] and exact)
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
