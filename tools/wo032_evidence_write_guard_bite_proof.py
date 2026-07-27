"""WO-032 §4.3 — BITE PROOF for the generalized evidence-write guard. Four artifacts, sha256 restore.

The guard (`tests/test_evidence_write_boundary.py`) exists because WO-026's doctrine was enforced by a
`conftest.py` check that could only see ONE path — so `tools/wo029_reverify_partition.py` reintroduced
the banned pattern and nothing fired (WO-031 Finding 4). A guard asserted to "reach tools/" must be
SHOWN to reach tools/.

The throwaway script is `git add -N`'d, because the guard deliberately scans TRACKED tools/ scripts
(§4.2's wording) — an untracked scratch file is nobody's committed-evidence problem, and a bite proof
that skipped the add would prove nothing about the real population.

  ARTIFACT 1 — THE BITE: a throwaway tools/ script whose output path is inside evidence/ → the guard
      FAILS, naming the script AND the path.
  ARTIFACT 2 — PRESERVATION DUAL (local and direct, §0.4): the SAME script writing under .artifacts/
      → the guard PASSES. The guard bans the destination, not the act of writing.
  ARTIFACT 3 — RESTORED: throwaway removed from the index and disk; guard PASSES on the real tree.
  ARTIFACT 4 — sha256 EXACT-RESTORE of the guard module itself (never edited) + a clean `git status`.

    python tools/wo032_evidence_write_guard_bite_proof.py
"""
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, "tests", "test_evidence_write_boundary.py")
THROWAWAY = os.path.join(REPO, "tools", "_wo032_throwaway_probe.py")
THROWAWAY_REL = "tools/_wo032_throwaway_probe.py"
# WO-032 §4.1 — this instrument writes to .artifacts/, never evidence/.
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo032_evidence_write_guard_bite_proof")

BANNED = '''"""Throwaway probe (WO-032 §4.3). Writes into evidence/ — the BANNED pattern."""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "evidence", "WO-032", "throwaway_probe.txt")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("probe\\n")
'''

ALLOWED = '''"""Throwaway probe (WO-032 §4.3). Writes under .artifacts/ — the PERMITTED shape."""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, ".artifacts", "wo032_probe", "throwaway_probe.txt")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("probe\\n")
'''


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def run_guard():
    """Run ONLY the offender test, so the honesty/self-test cases do not mask the signal."""
    p = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_evidence_write_boundary.py::test_no_tools_script_writes_into_evidence",
         "-p", "no:randomly", "-q", "--no-header"],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONUTF8": "1"})
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def summarize(text):
    keep = [ln.rstrip() for ln in text.splitlines()
            if ("_wo032_throwaway_probe" in ln or "TOOLS SCRIPT" in ln
                or ln.startswith("FAILED") or " passed" in ln or " failed" in ln)]
    return keep or ["    (no matching lines)"]


def main():
    before = sha256(GUARD)
    out = ["WO-032 §4.3 BITE PROOF — the generalized evidence-write guard REACHES tools/.",
           "Four artifacts, sha256 exact-restore. Both directions (§0.3/§0.4).",
           f"  guard     : {os.path.relpath(GUARD, REPO)}",
           f"  throwaway : {THROWAWAY_REL}  (git add -N'd: the guard scans TRACKED scripts)",
           f"  sha256 BEFORE (guard) : {before}", ""]

    try:
        # ARTIFACT 1 — the bite.
        open(THROWAWAY, "w", encoding="utf-8").write(BANNED)
        git("add", "-N", THROWAWAY_REL)
        rc1, t1 = run_guard()
        names_script = "_wo032_throwaway_probe.py" in t1
        names_path = "evidence" in t1 and "throwaway_probe.txt" in t1
        out += ["-- ARTIFACT 1 — THE BITE (throwaway writes into evidence/) --",
                f"  returncode : {rc1}   (must be nonzero)",
                f"  guard NAMES the script : {names_script}",
                f"  guard NAMES the path   : {names_path}",
                "  VERBATIM:"] + [f"    {ln}" for ln in summarize(t1)] + [""]

        # ARTIFACT 2 — preservation dual: same script, .artifacts/ destination.
        open(THROWAWAY, "w", encoding="utf-8").write(ALLOWED)
        rc2, t2 = run_guard()
        out += ["-- ARTIFACT 2 — PRESERVATION DUAL (same script, writes under .artifacts/) --",
                f"  returncode : {rc2}   (must be 0)",
                "  => the guard bans the DESTINATION, not the act of writing. A tool that streams to",
                "     .artifacts/ is exactly what the doctrine asks for and is not flagged.",
                "  VERBATIM:"] + [f"    {ln}" for ln in summarize(t2)] + [""]
    finally:
        git("rm", "--cached", "--force", "--quiet", THROWAWAY_REL)
        if os.path.exists(THROWAWAY):
            os.remove(THROWAWAY)

    # ARTIFACT 3 — restored tree.
    rc3, t3 = run_guard()
    out += ["-- ARTIFACT 3 — RESTORED (throwaway removed from index and disk) --",
            f"  returncode : {rc3}   (must be 0)",
            "  VERBATIM:"] + [f"    {ln}" for ln in summarize(t3)] + [""]

    # ARTIFACT 4 — sha256 exact-restore + clean tree.
    after = sha256(GUARD)
    exact = after == before
    status = git("status", "--porcelain", "--untracked-files=all").stdout
    leftover = [ln for ln in status.splitlines() if "_wo032_throwaway_probe" in ln]
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --",
            f"  sha256 AFTER (guard)  : {after}",
            f"  IDENTICAL             : {exact}   (the guard was never edited — only the population)",
            f"  throwaway leftovers   : {leftover or 'none'}", ""]

    ok = (rc1 != 0 and names_script and names_path and rc2 == 0 and rc3 == 0
          and exact and not leftover)
    verdict = "PASS" if ok else "FAIL"
    out += [f"VERDICT: {verdict}"]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
