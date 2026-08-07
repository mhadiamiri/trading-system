"""WO-048 §6.1 BITE PROOF — the backtest CANNOT silently trade across a hole.

    python tools/wo048_antisplice_bite_proof.py

Four artifacts, sha256 exact-restore, TWO independent necessity mutations.

  MUTATION A (U3) — the per-segment FRESH STRATEGY is replaced by ONE instance reused across every
      segment. State then leaks across the hole: segment 2 opens already warm, on a window computed
      partly from data on the far side of a gap nobody could see across.

  MUTATION B (U4) — the observation-only first tick is removed, so the very first frame after a hole
      becomes fillable. This is the trade that "was executable in the model but was NOT executable
      in reality" (WO-047 §2.3).

Each mutation must break the BITE half while leaving the PRESERVATION duals passing. A proof that
fails on everything is as uninformative as one that fails on nothing — and here it matters twice
over, because a backtest that simply never trades would satisfy the bite vacuously. The duals are
what rule that out.

Writes to .artifacts/ (WO-032 §4.1). Anchors are joined with the newline the FILE uses (WO-045's
CRLF lesson).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "backtest", "segmented.py")
TESTS = "tests/test_segmented_backtest.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo048_antisplice_bite_proof")

# ── MUTATION A: kill the per-segment fresh instance (U3) ─────────────────────────────────────
ANCHOR_A = ["        strategy = self._strategy_factory()"]
MUTANT_A = [
    "        if not hasattr(self, '_leaked'):   # MUTATED: one instance reused across segments",
    "            self._leaked = self._strategy_factory()",
    "        strategy = self._leaked",
]

# ── MUTATION B: kill the observation-only first tick (U4) ────────────────────────────────────
ANCHOR_B = [
    "            if not first_tick_skipped:",
    "                first_tick_skipped = True",
]
MUTANT_B = [
    "            if False:   # MUTATED: first tick is fillable — the post-hole trade is allowed",
    "                first_tick_skipped = True",
]

# The BITE half — the anti-splice assertions. Must FAIL under each mutation.
BITE_TESTS = {
    "test_anti_splice_bite_and_preservation_dual",
    "test_the_first_tick_of_a_segment_never_fills",
}
# The PRESERVATION duals — must STILL PASS under both mutations.
DUAL_TESTS = {
    "test_the_loader_refuses_a_window_it_did_not_receive_from_the_reader",
    "test_the_loader_refuses_a_fabricated_segment",
    "test_no_frame_is_yielded_outside_an_approved_segment",
    "test_the_loader_yields_book_state_with_no_fabricated_price_channel",
    "test_a_degenerate_tick_holds_without_dividing",
    "test_the_preregistered_parameters_are_what_the_report_claims",
    "test_the_acknowledgment_set_is_bounded_and_declared",
    "test_the_eligibility_bound_carries_its_derivation",
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
        "bite_failed": sorted(failed & BITE_TESTS),
        "dual_failed": sorted(failed & DUAL_TESTS),
        "dual_passed": len(passed & DUAL_TESTS),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<16} {v}")
    lines.append(f"  EXPECT: {expectation}")
    return lines + [""]


def main():
    original = open(SRC, "rb").read()
    text = original.decode("utf-8")
    nl = _nl(text)
    a_anchor, a_mutant = nl.join(ANCHOR_A), nl.join(MUTANT_A)
    b_anchor, b_mutant = nl.join(ANCHOR_B), nl.join(MUTANT_B)
    for name, anchor in (("A/fresh-instance", a_anchor), ("B/observation-only", b_anchor)):
        assert text.count(anchor) == 1, (
            f"anchor {name} is not unique (found {text.count(anchor)}) — refusing to mutate blindly")
    before = sha256(SRC)

    out = ["WO-048 §6.1 BITE PROOF — THE BACKTEST CANNOT SILENTLY TRADE ACROSS A HOLE.",
           "Four artifacts, sha256 exact-restore. Two independent necessity mutations.",
           f"  file          : {os.path.relpath(SRC, REPO)}",
           f"  tests         : {TESTS}",
           f"  sha256 BEFORE : {before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; bite and duals both hold")

    open(SRC, "wb").write(text.replace(a_anchor, a_mutant, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED (A): {sha256(SRC)}",
                "  MUTATION A (U3): one strategy instance reused — state leaks across the hole", ""]
        d2 = digest(*run_tests())
    finally:
        open(SRC, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION A (U3 necessity)", d2,
                 "the BITE fails (segment 2 opens warm); every DUAL still passes")

    open(SRC, "wb").write(text.replace(b_anchor, b_mutant, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED (B): {sha256(SRC)}",
                "  MUTATION B (U4): first tick fillable — the post-hole trade is allowed", ""]
        d3 = digest(*run_tests())
    finally:
        open(SRC, "wb").write(original)
    out += block("ARTIFACT 3 — MUTATION B (U4 necessity)", d3,
                 "the BITE fails (a fill appears on the first post-gap tick); DUALS still pass")

    d4 = digest(*run_tests())
    out += block("ARTIFACT 4 — RESTORED", d4, "returncode 0; nothing failed")

    after = sha256(SRC)
    exact = after == before
    out += ["-- sha256 EXACT-RESTORE --",
            f"  sha256 AFTER  : {after}",
            f"  IDENTICAL     : {exact}", ""]

    a_disc = bool(d2["bite_failed"]) and not d2["dual_failed"]
    b_disc = bool(d3["bite_failed"]) and not d3["dual_failed"]
    out += [f"  MUTATION A discriminates (bite fails, duals hold): {a_disc}",
            f"  MUTATION B discriminates (bite fails, duals hold): {b_disc}", ""]

    ok = (d1["returncode"] == 0 and not d1["bite_failed"] and not d1["dual_failed"]
          and d2["returncode"] != 0 and a_disc
          and d3["returncode"] != 0 and b_disc
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
