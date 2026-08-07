"""WO-049 §4.4 BITE PROOF — the aggregate position cap. Four artifacts, sha256 exact-restore.

    python tools/wo049_risk_bite_proof.py

TWO MUTATIONS, EACH FAILING A DIFFERENT HALF. That is the whole design: in the risk layer a guard
that refuses everything looks correct and is catastrophic, so it is not enough to show that removing
the check breaks something — it must also be shown that OVER-BLOCKING breaks something else.

  MUTATION A (§4.4a) — revert check() to the per-order clamp, ignoring current_quantity: exactly the
      WO-048 defect. The REFUSAL half must fail (the cap stops binding, the position accumulates)
      while the PRESERVATION half still passes — reduction was never blocked by the old code either.

  MUTATION B (§4.4b) — refuse ALL orders at or beyond the cap, including reducing ones. The
      PRESERVATION half must fail while the REFUSAL half still passes. This is the over-blocking
      nightmare: a position limit that traps you in a position, which is strictly more dangerous
      than the accumulation bug it replaces.

If a single mutation broke both halves, the proof would not distinguish "the cap works" from "the
cap is merely present". Two mutations, two different failures, is what makes it discriminating.

Writes to .artifacts/ (WO-032 §4.1). Anchors joined with the newline the FILE uses (WO-045's lesson).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "risk", "engine.py")
TESTS = "tests/test_risk_aggregate_position.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo049_risk_bite_proof")

# ── MUTATION A: back to the per-order clamp (the WO-048 defect) ───────────────────────────────
ANCHOR_A = [
    "        if increasing:",
    "            # Headroom is what remains before |position| reaches the cap.",
    "            headroom = cap - abs(current)",
]
MUTANT_A = [
    "        if True:   # MUTATED: per-order clamp — current_quantity ignored (the WO-048 defect)",
    "            # Headroom is what remains before |position| reaches the cap.",
    "            headroom = cap",
]

# ── MUTATION B: refuse everything at the cap, including reductions (over-blocking) ────────────
ANCHOR_B = ["        increasing = (direction * current) >= 0"]
MUTANT_B = ["        increasing = True   # MUTATED: everything blocks at the cap, even reductions"]

# ── CLASSIFICATION: only NARROWLY-SCOPED tests can discriminate ───────────────────────────────
#
# A test that exercises BOTH halves fails under EITHER mutation and therefore distinguishes
# nothing. Two such tests exist deliberately — the S13 contract test (§4.1/§4.2 in one, as the WO
# requires) and the 70-case invariant sweep — and both are EXCLUDED from the sets below for exactly
# that reason. Their failure under both mutations is correct behaviour, not evidence.
#
# This classification was itself corrected during the WO: the first attempt used the broad tests and
# neither mutation discriminated, because every set failed under both. The proof caught it.
REFUSAL_TESTS = {
    "test_pure_refusal_partial_headroom_clamps_to_the_cap",
    "test_pure_refusal_zero_headroom_vetoes",
    "test_repeated_same_side_orders_plateau_at_the_cap",
    "test_the_cap_is_two_sided",
}
PRESERVATION_TESTS = {
    "test_pure_preservation_small_reduction_at_the_cap",
    "test_pure_preservation_small_reduction_beyond_the_cap",
}
# Both-halves tests: expected to fail under either mutation; reported, never used to discriminate.
BOTH_HALVES_TESTS = {
    "test_aggregate_cap_refusal_and_preservation_in_one_test",
    "test_the_clamp_never_increases_never_flips_never_converts",
}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _nl(text):
    return "\r\n" if "\r\n" in text else "\n"


def run_tests():
    p = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-p", "no:randomly", "-v", "--tb=line", "-q"],
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
        "refusal_failed": sorted(failed & REFUSAL_TESTS),
        "preservation_failed": sorted(failed & PRESERVATION_TESTS),
        "refusal_passed": len(passed & REFUSAL_TESTS),
        "preservation_passed": len(passed & PRESERVATION_TESTS),
        "both_halves_failed": sorted(failed & BOTH_HALVES_TESTS),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<22} {v}")
    lines.append(f"  EXPECT: {expectation}")
    return lines + [""]


def main():
    original = open(SRC, "rb").read()
    text = original.decode("utf-8")
    nl = _nl(text)
    a_anchor, a_mutant = nl.join(ANCHOR_A), nl.join(MUTANT_A)
    b_anchor, b_mutant = nl.join(ANCHOR_B), nl.join(MUTANT_B)
    for name, anchor in (("A/per-order-clamp", a_anchor), ("B/over-block", b_anchor)):
        assert text.count(anchor) == 1, (
            f"anchor {name} is not unique (found {text.count(anchor)}) — refusing to mutate blindly")
    before = sha256(SRC)

    out = ["WO-049 §4.4 BITE PROOF — max_position_btc IS THE AGGREGATE POSITION CAP.",
           "Four artifacts, sha256 exact-restore. TWO mutations, each failing a DIFFERENT half.",
           f"  file          : {os.path.relpath(SRC, REPO)}",
           f"  tests         : {TESTS}",
           f"  sha256 BEFORE : {before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; both halves hold")

    open(SRC, "wb").write(text.replace(a_anchor, a_mutant, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED (A): {sha256(SRC)}",
                "  MUTATION A: per-order clamp restored — current_quantity ignored", ""]
        d2 = digest(*run_tests())
    finally:
        open(SRC, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION A (the WO-048 defect restored)", d2,
                 "the REFUSAL half FAILS; the PRESERVATION half still PASSES")

    open(SRC, "wb").write(text.replace(b_anchor, b_mutant, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED (B): {sha256(SRC)}",
                "  MUTATION B: over-blocking — reductions refused at the cap too", ""]
        d3 = digest(*run_tests())
    finally:
        open(SRC, "wb").write(original)
    out += block("ARTIFACT 3 — MUTATION B (over-blocking: the position TRAP)", d3,
                 "the PRESERVATION half FAILS; the REFUSAL half still PASSES")

    d4 = digest(*run_tests())
    out += block("ARTIFACT 4 — RESTORED", d4, "returncode 0; nothing failed")

    after = sha256(SRC)
    exact = after == before
    out += ["-- sha256 EXACT-RESTORE --",
            f"  sha256 AFTER  : {after}",
            f"  IDENTICAL     : {exact}", ""]

    a_disc = bool(d2["refusal_failed"]) and not d2["preservation_failed"]
    b_disc = bool(d3["preservation_failed"]) and not d3["refusal_failed"]
    out += [f"  MUTATION A discriminates (refusal fails, preservation holds) : {a_disc}",
            f"  MUTATION B discriminates (preservation fails, refusal holds) : {b_disc}",
            "",
            "  The two mutations fail DIFFERENT halves. That asymmetry is what distinguishes",
            "  'the cap works' from 'the cap is merely present' — and it is what proves the",
            "  preservation half discriminates OVER-BLOCKING, the dangerous risk-layer failure.",
            ""]

    ok = (d1["returncode"] == 0 and not d1["refusal_failed"] and not d1["preservation_failed"]
          and d2["returncode"] != 0 and a_disc
          and d3["returncode"] != 0 and b_disc
          and d4["returncode"] == 0 and not d4["refusal_failed"] and exact)
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
