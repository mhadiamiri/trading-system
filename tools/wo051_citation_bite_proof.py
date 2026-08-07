"""WO-051 §3.3 BITE PROOF — the citation pin. Four artifacts, sha256 exact-restore.

    python tools/wo051_citation_bite_proof.py

The guard being proved: the wired taker fee IS the published rate for the DECLARED tier. Before
WO-051 that fee was a bare float labelled "declared engineering judgement", and it drove 96.3% of
total costs in the only strategy verdict this project has produced. This proof shows the pin
actually bites — that it is not a test which passes for reasons unrelated to what it claims.

TWO MUTATIONS, EACH FAILING A DIFFERENT PROPERTY:

  MUTATION DRIFT — the venue default reverts to a hand-typed `Decimal("0.26")`: exactly the
      pre-WO-051 state, a number resembling a fee with no link to any schedule. The PIN must fail.
      The tier-declaration tests must still PASS — nothing about the schedule or the declared tier
      changed, only the wiring — which is what makes this mutation attributable.

  MUTATION OPTIMISM — `ASSUMED_TIER` moves to "Tier 6" (0.25% taker), a tier that genuinely
      exists in the cited table but which this account cannot substantiate: it asserts $100K of
      30-day volume for a system that has never placed an order. This is the §2.2 failure mode —
      an optimistic tier is a cost assumption wearing a fact's clothing — and it is the one a
      pin on the NUMBER ALONE would miss, because after the mutation the wired constant and the
      looked-up rate still agree perfectly. The TIER set must fail.

That asymmetry is the point of running both: DRIFT proves the number is pinned to the citation,
OPTIMISM proves the citation is pinned to a tier the account can actually claim.

§0.10 — THE DISCRIMINATION SETS HOLD ONLY SINGLE-PURPOSE TESTS. Tests that assert several
properties at once are excluded and reported as `broad_failed`, so their failure under a mutation
is visible as expected rather than mistaken for evidence.

Writes to .artifacts/ (WO-032 §4.1).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER = os.path.join(REPO, "src", "trading", "execution", "paper.py")
SCHEDULE = os.path.join(REPO, "src", "trading", "execution", "fee_schedule.py")
TESTS = "tests/test_fee_schedule.py tests/test_backtest_accounting.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo051_citation_bite_proof")

# ── MUTATION DRIFT: the cited lookup reverts to a hand-typed literal ──────────────────────────
DRIFT_ANCHOR = ["    DEFAULT_FEE_RATE_PCT = fee_schedule.taker_pct()"]
DRIFT_MUTANT = ['    DEFAULT_FEE_RATE_PCT = Decimal("0.26")  # MUTATED: back to a bare literal']

# ── MUTATION OPTIMISM: a better tier than the account can substantiate ────────────────────────
OPTIMISM_ANCHOR = ['ASSUMED_TIER = "Tier 1"']
OPTIMISM_MUTANT = ['ASSUMED_TIER = "Tier 6"  # MUTATED: a tier this account cannot substantiate']

# SINGLE-PURPOSE sets (§0.10).
PIN = {"test_wired_taker_rate_equals_the_cited_schedule_for_the_declared_tier"}
TIER = {
    "test_the_declared_tier_is_the_base_tier_the_account_can_substantiate",
    "test_the_declared_tier_is_the_most_expensive_taker_row_published",
}
R4 = {"test_r4_fees_and_slippage_differ_under_the_defaults"}
# BROAD — excluded from every discrimination set, reported for visibility (§0.10). These read the
# wired constant AND the schedule AND the citation record, so they cannot attribute a failure.
BROAD = {
    "test_the_citation_record_carries_url_and_retrieval_date",
    "test_maker_rate_is_not_wired_into_execution",
    "test_maker_rate_is_recorded_for_the_declared_tier",
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
        line for line in out.splitlines() if "FAILED" in line)))
    passed = set(re.findall(r"(test_\w+)\s+PASSED", out))
    tail = [line for line in out.splitlines() if re.search(r"\d+ (passed|failed)", line)]
    return {
        "returncode": rc,
        "summary": tail[-1].strip() if tail else "(no summary)",
        "pin_failed": sorted(failed & PIN),
        "tier_failed": sorted(failed & TIER),
        "r4_failed": sorted(failed & R4),
        "pin_passed": len(passed & PIN),
        "tier_passed": len(passed & TIER),
        "broad_failed": sorted(failed & BROAD),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<14} {v}")
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
    paper_before, sched_before = sha256(PAPER), sha256(SCHEDULE)

    out = ["WO-051 §3.3 BITE PROOF — THE CITATION PIN (fee rate is cited, and tier-aware).",
           "Four artifacts, sha256 exact-restore. Two mutations, each failing a DIFFERENT property.",
           f"  paper.py        sha256 BEFORE : {paper_before}",
           f"  fee_schedule.py sha256 BEFORE : {sched_before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; nothing failed")

    original = _mutate(PAPER, DRIFT_ANCHOR, DRIFT_MUTANT)
    try:
        out += ['  MUTATION DRIFT: the wired fee reverts to a hand-typed Decimal("0.26")', ""]
        d2 = digest(*run_tests())
    finally:
        open(PAPER, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION DRIFT (the pre-WO-051 uncited literal restored)", d2,
                 "the PIN fails; the TIER tests still pass (the schedule is untouched)")

    original = _mutate(SCHEDULE, OPTIMISM_ANCHOR, OPTIMISM_MUTANT)
    try:
        out += ['  MUTATION OPTIMISM: ASSUMED_TIER moves to "Tier 6" (0.25% taker)', ""]
        d3 = digest(*run_tests())
    finally:
        open(SCHEDULE, "wb").write(original)
    out += block("ARTIFACT 3 — MUTATION OPTIMISM (an unsubstantiable tier declared)", d3,
                 "the TIER tests fail. Note the PIN still passes — constant and lookup agree "
                 "perfectly at the wrong tier, which is exactly why a pin on the NUMBER alone "
                 "would not have caught this")

    d4 = digest(*run_tests())
    out += block("ARTIFACT 4 — RESTORED", d4, "returncode 0; nothing failed")

    paper_after, sched_after = sha256(PAPER), sha256(SCHEDULE)
    exact = (paper_after == paper_before) and (sched_after == sched_before)
    out += ["-- sha256 EXACT-RESTORE --",
            f"  paper.py        AFTER : {paper_after}",
            f"  fee_schedule.py AFTER : {sched_after}",
            f"  IDENTICAL             : {exact}", ""]

    drift_disc = bool(d2["pin_failed"]) and not d2["tier_failed"]
    optimism_disc = bool(d3["tier_failed"]) and not d3["pin_failed"]
    out += [f"  MUTATION DRIFT discriminates    (PIN fails, TIER holds) : {drift_disc}",
            f"  MUTATION OPTIMISM discriminates (TIER fails, PIN holds) : {optimism_disc}",
            "",
            "  §3.4 — the R4 invariant (fees != slippage under the defaults) must survive this WO",
            f"  and does: r4_failed is {d1['r4_failed']} on the pristine tree and "
            f"{d4['r4_failed']} on the restored tree.",
            "",
            "  §0.10 — BROAD TESTS ARE EXCLUDED FROM THE DISCRIMINATION SETS. They read the wired",
            "  constant AND the schedule AND the citation record at once, so they fail under either",
            "  mutation and attribute nothing. Reported as `broad_failed` so their failure is",
            "  visible as EXPECTED rather than mistaken for evidence.",
            ""]

    ok = (d1["returncode"] == 0 and not d1["pin_failed"] and not d1["tier_failed"]
          and d2["returncode"] != 0 and drift_disc
          and d3["returncode"] != 0 and optimism_disc
          and d4["returncode"] == 0 and not d4["pin_failed"] and not d4["tier_failed"]
          and exact)
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
