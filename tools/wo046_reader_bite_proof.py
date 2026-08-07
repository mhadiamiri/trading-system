"""WO-046 §4 BITE PROOF — the default-deny corpus reader. Four artifacts, sha256 exact-restore.

    python tools/wo046_reader_bite_proof.py

TWO INDEPENDENT NECESSITY MUTATIONS, each caught by its OWN half of the suite. A proof that fails
on everything is as uninformative as one that fails on nothing.

  MUTATION A (§4.1) — neuter the gap check: `unacknowledged` is forced empty, so every window is
      served regardless of what it spans. The REFUSAL half must fail; the PRESERVATION duals must
      still pass. This is D20 itself under test — with the check gone, "the only way to get
      gap-spanning data is to have written code that asked for it" becomes false.

  MUTATION B (§4.4) — make acknowledgment a BLANKET accept: the cause-class comparison is removed,
      so acknowledging any class admits every class. Only the CLASS-AWARENESS tests may fail; the
      refusal half must be untouched, because a blanket acknowledgment still refuses a request that
      acknowledged nothing.

Writes to .artifacts/ (WO-032 §4.1). Anchors are joined with the newline the FILE uses — the source
is CRLF on this host, and a `\n`-joined multi-line literal simply does not occur in it (WO-045
learned this the loud way, via a uniqueness assert that refused to mutate).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "data", "corpus_reader.py")
TESTS = "tests/test_corpus_reader.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo046_reader_bite_proof")

# ── MUTATION A: default-deny neutered ────────────────────────────────────────────────────────
ANCHOR_A = ["        unacknowledged = [d for d in hits if not any(a.accepts(d) for a in acks)]"]
MUTANT_A = ["        unacknowledged = []   # MUTATED: default-deny neutered — everything is served"]

# ── MUTATION B: acknowledgment no longer class-aware ─────────────────────────────────────────
ANCHOR_B = [
    "        if d.cause != self.cause:",
    "            return False",
]
MUTANT_B = [
    "        if False:   # MUTATED: blanket accept — acknowledgment is no longer class-aware",
    "            return False",
]

# The REFUSAL half — default-deny assertions. Must FAIL under mutation A.
REFUSAL_TESTS = {
    "test_d20_refusal_and_preservation_in_one_test",
    "test_a_zero_duration_gap_is_a_real_gap_and_refuses",
    "test_inclusive_bounds_a_boundary_touching_the_gap_still_refuses",
    "test_inclusive_bounds_hold_for_a_nonzero_gap_too",
    "test_a_seam_refuses_by_default_and_serves_when_acknowledged",
    "test_seams_and_gaps_share_one_refusal_path",
    "test_an_open_ended_gap_denies_every_window_from_its_open_onward",
    "test_an_open_ended_gap_needs_its_own_deliberate_acknowledgment",
    "test_the_reader_writes_nothing",
}
# The PRESERVATION duals — must STILL PASS under mutation A.
DUAL_TESTS = {
    "test_a_window_clear_of_every_gap_serves_without_acknowledgment",
    "test_continuous_data_across_a_gap_is_not_expressible",
    "test_an_acknowledgment_naming_an_impossible_class_fails_loudly",
    "test_the_reader_module_opens_nothing_for_writing",
    "test_the_readonly_coverage_query_reports_without_writing",
    "test_an_incomplete_ledger_denies_everything",
    "test_a_torn_ledger_line_marks_the_run_incomplete",
}
# CLASS-AWARENESS — must FAIL under mutation B (and only these).
CLASS_TESTS = {
    "test_acknowledging_class_a_does_not_admit_class_b",
    "test_there_is_no_blanket_acknowledgment",
}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _detect_newline(text):
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
        "summary": tail[-1].strip() if tail else "(no summary line)",
        "refusal_failed": sorted(failed & REFUSAL_TESTS),
        "dual_failed": sorted(failed & DUAL_TESTS),
        "dual_passed_count": len(passed & DUAL_TESTS),
        "class_failed": sorted(failed & CLASS_TESTS),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<20} {v}")
    lines.append(f"  EXPECT: {expectation}")
    return lines + [""]


def main():
    original = open(SRC, "rb").read()
    text = original.decode("utf-8")
    nl = _detect_newline(text)
    a_anchor, a_mutant = nl.join(ANCHOR_A), nl.join(MUTANT_A)
    b_anchor, b_mutant = nl.join(ANCHOR_B), nl.join(MUTANT_B)
    for name, anchor in (("A/default-deny", a_anchor), ("B/class-awareness", b_anchor)):
        assert text.count(anchor) == 1, (
            f"anchor {name} is not unique (found {text.count(anchor)}) — refusing to mutate blindly"
        )
    before = sha256(SRC)

    out = ["WO-046 §4 BITE PROOF — THE DEFAULT-DENY CORPUS READER.",
           "Four artifacts, sha256 exact-restore. Two independent necessity mutations.",
           f"  file          : {os.path.relpath(SRC, REPO)}",
           f"  tests         : {TESTS}",
           f"  sha256 BEFORE : {before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1,
                 "returncode 0; nothing failed; refusal half and duals both hold")

    open(SRC, "wb").write(text.replace(a_anchor, a_mutant, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED (A): {sha256(SRC)}",
                "  MUTATION A: default-deny neutered — `unacknowledged` forced empty", ""]
        d2 = digest(*run_tests())
    finally:
        open(SRC, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION A (D20 necessity)", d2,
                 "the REFUSAL half FAILS; every PRESERVATION dual still PASSES")

    open(SRC, "wb").write(text.replace(b_anchor, b_mutant, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED (B): {sha256(SRC)}",
                "  MUTATION B: blanket accept — the cause-class comparison removed", ""]
        d3 = digest(*run_tests())
    finally:
        open(SRC, "wb").write(original)
    out += block("ARTIFACT 3 — MUTATION B (class-awareness necessity)", d3,
                 "ONLY the class-awareness tests fail; the refusal half is untouched")

    d4 = digest(*run_tests())
    out += block("ARTIFACT 4 — RESTORED", d4, "returncode 0; nothing failed")

    after = sha256(SRC)
    exact = after == before
    out += ["-- sha256 EXACT-RESTORE --",
            f"  sha256 AFTER  : {after}",
            f"  IDENTICAL     : {exact}", ""]

    a_disc = bool(d2["refusal_failed"]) and not d2["dual_failed"]
    b_disc = bool(d3["class_failed"]) and not d3["refusal_failed"] and not d3["dual_failed"]
    out += [f"  MUTATION A discriminates (refusal fails, duals hold) : {a_disc}",
            f"  MUTATION B discriminates (class only, refusal intact): {b_disc}", ""]

    ok = (d1["returncode"] == 0 and not d1["refusal_failed"] and not d1["dual_failed"]
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
