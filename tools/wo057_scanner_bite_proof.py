"""WO-057 §4.4 BITE PROOF — the scanner's three-outcome distinction. Four artifacts, exact-restore.

    python tools/wo057_scanner_bite_proof.py

FIXTURES ONLY. No socket opens in this WO.

WHAT IS BEING PROVED
--------------------
Not merely that the scanner finds a fabricated price — that is the easy half. The thing being
proved is that it **refuses to call an unanswerable question clean**.

THE MUTATION: collapse NOT_APPLICABLE into CLEAN — i.e. report a corpus with nothing to examine as
"zero fabricated prices". That is precisely the WO-055 false green, restored.

THE ASYMMETRY, which is the point:

    the fabrication BITE        -> still passes under the mutation
    the correct-corpus DUAL     -> still passes under the mutation
    the NOT_APPLICABLE case     -> FAILS

A scanner that only found violations would satisfy the first two and still be the tool that
reported "§3.5 PASS — zero fabricated prices" over a book-only corpus. The third assertion is the
entire value this scanner adds over the naive one, and the mutation isolates it.

§0.10 — the discrimination sets hold only single-purpose tests; exclusions recorded below.

Writes to .artifacts/ (WO-032 §4.1).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCANNER = os.path.join(REPO, "tools", "corpus_fabrication_scan.py")
TESTS = "tests/test_abort_detectors.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo057_scanner_bite_proof")

# ── THE MUTATION: NOT_APPLICABLE collapses into CLEAN ────────────────────────────────────────
ANCHOR = [
    "    if examinable == 0:",
    "        outcome = NOT_APPLICABLE",
]
MUTANT = [
    "    if False:   # MUTATED: NOT_APPLICABLE collapsed into CLEAN — the WO-055 false green",
    "        outcome = NOT_APPLICABLE",
]

# SINGLE-PURPOSE sets (§0.10).
NA_CASE = {"test_the_third_case_a_book_only_corpus_is_NOT_APPLICABLE_not_clean"}
FABRICATION_BITE = {"test_bite_a_fabricated_last_price_is_found_and_named"}
CORRECT_DUAL = {"test_dual_a_correct_corpus_is_clean_with_a_non_zero_examined_count"}
# BROAD — excluded from the discrimination sets, reported for visibility (§0.10). These read the
# outcome AND the counts AND the detail text, so they attribute nothing on their own.
BROAD = {
    "test_every_report_states_examined_of_examinable",
    "test_an_unobservable_frame_is_not_examinable_for_fabrication",
    "test_the_report_carries_its_falsifier_and_distinguishes_the_two_zeros",
    "test_a_traded_interval_with_no_price_is_reported_separately_not_as_fabrication",
    "test_the_running_last_price_is_not_treated_as_fabrication",
}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _nl(t):
    return "\r\n" if "\r\n" in t else "\n"


def run_tests():
    p = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-p", "no:randomly", "-v", "--tb=line", "-q"],
        cwd=REPO, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    failed_lines = [line for line in out.splitlines() if "FAILED" in line]
    failed = {f.split("::")[-1] for f in re.findall(r"(test_[\w\[\]\.\-]+)",
                                                    "\n".join(failed_lines))}
    return {
        "returncode": rc,
        "summary": next((line.strip() for line in reversed(out.splitlines())
                         if re.search(r"\d+ (passed|failed)", line)), "(no summary)"),
        "na_case_failed": sorted(failed & NA_CASE),
        "fabrication_bite_failed": sorted(failed & FABRICATION_BITE),
        "correct_dual_failed": sorted(failed & CORRECT_DUAL),
        "broad_failed": sorted(failed & BROAD),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<26} {v}")
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
    before = sha256(SCANNER)
    out = ["WO-057 §4.4 BITE PROOF — THE SCANNER'S THREE-OUTCOME DISTINCTION.",
           "FIXTURES ONLY. Four artifacts, sha256 exact-restore.",
           "ONE mutation: NOT_APPLICABLE collapsed into CLEAN — the WO-055 false green, restored.",
           f"  corpus_fabrication_scan.py sha256 BEFORE : {before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; nothing failed")

    original = _mutate(SCANNER, ANCHOR, MUTANT)
    try:
        out += ["  MUTATION: a corpus with nothing examinable now reports CLEAN", ""]
        d2 = digest(*run_tests())
    finally:
        open(SCANNER, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION (the false green restored)", d2,
                 "the NOT_APPLICABLE case FAILS while the fabrication BITE and the correct-corpus "
                 "DUAL both still PASS — the asymmetry that isolates what this scanner adds")

    d3 = digest(*run_tests())
    out += block("ARTIFACT 3 — RESTORED", d3, "returncode 0; nothing failed")

    after = sha256(SCANNER)
    exact = after == before
    out += ["-- sha256 EXACT-RESTORE --",
            f"  corpus_fabrication_scan.py AFTER : {after}",
            f"  IDENTICAL                        : {exact}", ""]

    live = _live_corpus_demonstration()
    out += ["-- ARTIFACT 4 — THE REAL CORPUS (§4.3), read-only --"]
    out += [f"  {line}" for line in live["lines"]]
    out += ["  EXPECT: NOT_APPLICABLE on the book-only ratified corpus — the positive "
            "demonstration that the false green is now impossible", ""]

    na_ok = bool(d2["na_case_failed"])
    others_hold = not d2["fabrication_bite_failed"] and not d2["correct_dual_failed"]
    out += [f"  NOT_APPLICABLE case fails under the collapse : {na_ok}",
            f"  fabrication BITE and correct DUAL still pass : {others_hold}",
            f"  real corpus returns NOT_APPLICABLE           : {live['ok']}",
            "",
            "  ── WHY THE ASYMMETRY IS THE PROOF ───────────────────────────────────────────────",
            "  A scanner that only found violations would satisfy the bite AND the dual, and would",
            "  still be the tool that reported '§3.5 PASS — zero fabricated prices' over a",
            "  book-only corpus. Only the third case distinguishes 'the query spoke and found",
            "  nothing' from 'the query could not speak'.",
            "",
            "  §0.10 BROAD TESTS EXCLUDED from the discrimination sets and reported separately.",
            ""]

    ok = (d1["returncode"] == 0 and not d1["na_case_failed"]
          and d2["returncode"] != 0 and na_ok and others_hold
          and d3["returncode"] == 0 and not d3["na_case_failed"]
          and live["ok"] and exact)
    out += [f"VERDICT: {'PASS' if ok else 'FAIL'}"]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    assert exact, "SCANNER NOT RESTORED — aborting"
    return 0 if ok else 1


def _live_corpus_demonstration():
    """Run the RESTORED scanner against the ratified corpus. Read-only."""
    sys.path.insert(0, os.path.join(REPO, "tools"))
    from pathlib import Path

    from corpus_fabrication_scan import NOT_APPLICABLE, scan

    root = Path(REPO) / "captures" / "corpus_24h" / "corpus_20260805"
    if not root.is_dir():
        return {"lines": ["corpus absent — cannot demonstrate"], "ok": False}
    report = scan(root)
    return {
        "lines": [
            f"corpus            : {report['corpus']}",
            f"frames total      : {report['frames_total']:,}",
            f"frames EXAMINABLE : {report['frames_examinable']}",
            f"frames EXAMINED   : {report['frames_examined']}",
            f"OUTCOME           : {report['outcome']}",
            f"  {report['detail'][:150]}",
        ],
        "ok": report["outcome"] == NOT_APPLICABLE,
    }


if __name__ == "__main__":
    raise SystemExit(main())
