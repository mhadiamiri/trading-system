"""WO-032 §1.3 — BITE PROOF for the name-keyed partition verdict. Four artifacts, sha256 exact-restore.

WO-032 §1 changed `wo029_reverify_partition.py`'s verdict from LINE identity to NAME resolution,
because each batch's conversion moves its own file's races and the line-keyed verdict therefore
produced a FALSE FAIL (25/30 at WO-029 batch A's HEAD, growing with every later batch).

Loosening a verdict is exactly the move that must be bite-proved, because the cheap way to make a
check pass is to stop checking. Both directions are proved here:

  ARTIFACT 1 — PRESERVATION DUAL (local and direct, §0.4): the PRISTINE committed table, whose
      races 1-5 sit at post-conversion moved lines, now PASSES on name resolution. This is the false
      FAIL being gone — the whole point of the change.
  ARTIFACT 2 — THE BITE: rename one race in the table to a test that does not exist. A real
      partition break MUST still FAIL, and the failure must NAME the broken race.
  ARTIFACT 3 — RESTORED: the table back, verdict PASS again.
  ARTIFACT 4 — sha256 EXACT-RESTORE of the mutated table.

    python tools/wo032_namekey_bite_proof.py
"""
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(REPO, "evidence", "WO-029", "batch_partition.md")
TOOL = os.path.join(REPO, "tools", "wo029_reverify_partition.py")
# WO-032 §4.1 — this instrument writes to .artifacts/, never evidence/.
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo032_namekey_bite_proof")

ANCHOR = "test_keepalive_reconnect_gap_recorded"
BROKEN = "test_this_race_does_not_exist_anywhere"


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def run_tool(table=None):
    cmd = [sys.executable, TOOL] + (["--table", table] if table else [])
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1"})
    verdict = next((ln for ln in (p.stdout or "").splitlines() if ln.startswith("VERDICT:")), "<none>")
    resolved = next((ln.strip() for ln in (p.stdout or "").splitlines()
                     if "names RESOLVED" in ln), "<none>")
    return p.returncode, verdict, resolved


def main():
    before = sha256(TABLE)
    # BINARY read/write throughout. A text-mode round-trip on Windows translates newlines and the
    # "restored" file is a DIFFERENT BYTE SEQUENCE — the sha256 exact-restore check catches it, but
    # the honest fix is to never re-encode the file we are only supposed to be putting back.
    pristine = open(TABLE, "rb").read()
    out = ["WO-032 §1.3 BITE PROOF — the reverify verdict keys on NAME; a real break still bites.",
           "Four artifacts, sha256 exact-restore. Both directions (§0.3/§0.4).",
           f"  table : {os.path.relpath(TABLE, REPO)}",
           f"  tool  : {os.path.relpath(TOOL, REPO)}",
           f"  sha256 BEFORE : {before}", ""]

    # ARTIFACT 1 — preservation dual: pristine table, post-conversion moved lines, PASSES on name.
    rc1, v1, r1 = run_tool()
    out += ["-- ARTIFACT 1 — PRESERVATION DUAL (pristine table; races 1-5 at MOVED lines) --",
            f"  returncode : {rc1}",
            f"  {r1}",
            f"  {v1}",
            "  => the line-keyed FALSE FAIL is gone: a partition intact by name PASSES.", ""]

    # ARTIFACT 2 — the bite: a race name that resolves to nothing must FAIL, and be NAMED.
    #
    # The mutation is applied to a COPY under .artifacts/, never to the committed table (which the
    # WO's own wording asks for: "mutate the partition table's COPY"). An earlier revision mutated
    # the committed file in place and restored it byte-exactly — that restored correctly, but it
    # still made this script a `tools/` script that WRITES INTO evidence/, and the §4.2 guard
    # rightly failed it. Routing through --table removes the write entirely rather than exempting
    # it, and makes the exact-restore check stronger: the committed table is never opened for
    # writing at all, so ARTIFACT 4 proves untouched rather than put-back.
    assert ANCHOR.encode() in pristine, f"anchor {ANCHOR!r} not in the table — aborting before mutation"
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    mutated = os.path.join(ARTIFACT_DIR, "mutated_table_copy.md")
    open(mutated, "wb").write(pristine.replace(ANCHOR.encode(), BROKEN.encode(), 1))
    try:
        rc2, v2, r2 = run_tool(mutated)
    finally:
        if os.path.exists(mutated):
            os.remove(mutated)
    names_it = BROKEN in v2
    out += ["-- ARTIFACT 2 — THE BITE (one race renamed to a nonexistent test) --",
            f"  mutation   : {ANCHOR}  ->  {BROKEN}",
            f"  returncode : {rc2}   (must be 1)",
            f"  {r2}",
            f"  {v2}",
            f"  verdict NAMES the broken race : {names_it}",
            "  => an unresolvable NAME is still a hard FAIL. The verdict was re-keyed, not weakened.",
            ""]

    # ARTIFACT 3 — restored.
    rc3, v3, r3 = run_tool()
    out += ["-- ARTIFACT 3 — RESTORED --",
            f"  returncode : {rc3}",
            f"  {r3}",
            f"  {v3}", ""]

    # ARTIFACT 4 — sha256 exact-restore (here: proof the committed table was never written at all).
    after = sha256(TABLE)
    exact = after == before
    dirty = subprocess.run(["git", "status", "--porcelain", "--", os.path.relpath(TABLE, REPO)],
                           cwd=REPO, capture_output=True, text=True).stdout.strip()
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE (committed table NEVER opened for writing) --",
            f"  sha256 AFTER  : {after}",
            f"  IDENTICAL     : {exact}",
            f"  git status    : {dirty or 'clean'}",
            "  => the mutation lived in a .artifacts/ copy; this script writes nothing under",
            "     evidence/, so tests/test_evidence_write_boundary.py passes on it.", ""]

    ok = (rc1 == 0 and rc2 == 1 and rc3 == 0 and names_it and exact and not dirty
          and "PASS" in v1 and "FAIL" in v2 and "PASS" in v3)
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
    assert exact and not dirty, "COMMITTED TABLE WAS MODIFIED — aborting"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
