"""WO-044 §4 BITE PROOF — the 15-minute outage policy. Four artifacts, sha256 exact-restore.

    python tools/wo044_outage_bite_proof.py

The §4 tests are green. Green proves nothing until the code is broken and the tests are watched to
fail, so this drives TWO independent mutations against `kraken_v2_book.py` and checks that each one
is caught by the RIGHT test — a proof that fails on everything is as uninformative as one that
fails on nothing.

  MUTATION A — the ruled window reverts to the old T=600s.
      Must break the two window assertions and NOTHING ELSE. This is the regression that would
      silently reintroduce the failure that killed run `20260729190849` at 611 seconds.

  MUTATION B — the host-suspend divergence bound is raised out of reach (43s -> 1e9), so a suspend
      is no longer detected.
      Must break the §4.3 INDEPENDENCE test and NOT the preservation dual. This is the dangerous
      direction: widening what the breaker tolerates makes long outages ordinary, and if the
      suspend detector went quiet inside one, the corpus would relabel "the machine was asleep" as
      "we were patiently waiting" — and trust windows D24 says must be VOIDed. The mutation makes
      that failure concrete rather than hypothetical.

Writes to .artifacts/ (WO-032 §4.1).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "data", "adapters", "kraken_v2_book.py")
TESTS = "tests/integration/test_outage_policy.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo044_outage_bite_proof")

WINDOW_ANCHOR = "    RECONNECT_MAX_FAILURE_SECONDS = 900.0"
WINDOW_MUTANT = "    RECONNECT_MAX_FAILURE_SECONDS = 600.0   # MUTATED: back to the old window"

SUSPEND_ANCHOR = "    HOST_SUSPEND_DIVERGENCE_SECONDS = 43.0"
SUSPEND_MUTANT = ("    HOST_SUSPEND_DIVERGENCE_SECONDS = 1e9   # MUTATED: suspend never detected")

WINDOW_TESTS = {
    "test_the_outage_window_is_fifteen_minutes",
    "test_the_old_ten_minute_window_would_have_killed_run_two",
}
INDEPENDENCE_TEST = "test_a_suspend_during_an_outage_still_voids"
PRESERVATION_TEST = "test_no_suspend_recorded_when_only_the_network_is_out"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_tests():
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-p", "no:randomly", "-v", "--tb=line", "-q"],
        cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=900,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    failed = set(re.findall(r"(test_\w+)\s+FAILED", out)) | set(
        re.findall(r"FAILED .*?::(test_\w+)", out))
    passed = set(re.findall(r"(test_\w+)\s+PASSED", out))
    tail = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    return {
        "returncode": rc,
        "summary": tail[-1].strip() if tail else "(no summary line)",
        "failed_tests": sorted(failed),
        "window_tests_failed": sorted(failed & WINDOW_TESTS),
        "independence_failed": INDEPENDENCE_TEST in failed,
        "preservation_passed": PRESERVATION_TEST in passed,
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<24} {v}")
    lines.append(f"  EXPECT: {expectation}")
    return lines + [""]


def main():
    original = open(SRC, "rb").read()
    text = original.decode("utf-8")
    for anchor, name in ((WINDOW_ANCHOR, "window"), (SUSPEND_ANCHOR, "suspend bound")):
        assert text.count(anchor) == 1, (
            f"the {name} anchor is not unique in kraken_v2_book.py "
            f"(found {text.count(anchor)}) — refusing to mutate blindly"
        )
    before = sha256(SRC)

    out = ["WO-044 §4 BITE PROOF — the 15-minute outage policy, two independent mutations.",
           "Four artifacts, sha256 exact-restore. NO NETWORK (scripted transport).",
           f"  file          : {os.path.relpath(SRC, REPO)}",
           f"  tests         : {TESTS}",
           f"  sha256 BEFORE : {before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0, all 6 pass, nothing failed")

    # ── MUTATION A ────────────────────────────────────────────────────────────────────────────
    open(SRC, "wb").write(text.replace(WINDOW_ANCHOR, WINDOW_MUTANT, 1).encode("utf-8"))
    try:
        d2 = digest(*run_tests())
    finally:
        open(SRC, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION A: window reverted to the old T=600s", d2,
                 "the two WINDOW tests fail; the independence + preservation proofs are untouched")

    # ── MUTATION B ────────────────────────────────────────────────────────────────────────────
    open(SRC, "wb").write(text.replace(SUSPEND_ANCHOR, SUSPEND_MUTANT, 1).encode("utf-8"))
    try:
        d3 = digest(*run_tests())
    finally:
        open(SRC, "wb").write(original)
    out += block("ARTIFACT 3 — MUTATION B: suspend bound raised out of reach (43s -> 1e9)", d3,
                 "the §4.3 INDEPENDENCE proof fails; the preservation dual still PASSES")

    d4 = digest(*run_tests())
    out += block("ARTIFACT 4 — RESTORED", d4, "returncode 0, all 6 pass again")

    after = sha256(SRC)
    exact = after == before
    out += ["-- sha256 EXACT-RESTORE --",
            f"  sha256 AFTER  : {after}",
            f"  IDENTICAL     : {exact}", ""]

    # DISCRIMINATION: each mutation is caught by its OWN test, not by a blanket collapse.
    a_discriminates = (d2["window_tests_failed"] == sorted(WINDOW_TESTS)
                       and not d2["independence_failed"])
    b_discriminates = d3["independence_failed"] and d3["preservation_passed"] \
        and not d3["window_tests_failed"]
    out += [f"  MUTATION A discriminates (window tests only)      : {a_discriminates}",
            f"  MUTATION B discriminates (independence, not dual) : {b_discriminates}", ""]

    ok = (d1["returncode"] == 0 and not d1["failed_tests"]
          and d2["returncode"] != 0 and a_discriminates
          and d3["returncode"] != 0 and b_discriminates
          and d4["returncode"] == 0 and not d4["failed_tests"] and exact)
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
