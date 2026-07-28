"""WO-035 §4 — THE GATE LEDGER STILL BITES AFTER BATCH C. Four artifacts, sha256 exact-restore.

Not a new guard: proof the existing safety net did not go slack as the population it guards grew from
batch A's 5 races to 5 + 13-classified + batch C's 9. A wrong clock injection must still be caught,
loudly, by name — never pass silently.

The mutation targets batch C's own file: `_live_adapter`'s wall reader is repointed at a SECOND
`AdvancingClock`, so the pair no longer shares a `_coherence_token`. The pre-connection gate must
REFUSE on COHERENCE, and the session-end ledger assertion must FAIL naming the offending nodeid.

    python tools/wo035_ledger_still_bites.py

Writes to .artifacts/ (WO-032 §4.1).
"""
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "tests", "integration", "test_ledger_persistence.py")
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo035_ledger_still_bites")
NODEID = ("tests/integration/test_ledger_persistence.py::"
          "test_gap_ledger_persisted_readable_from_disk")

ANCHOR = "        adapter._wall_clock = clock.wall        # the coherent partner (shared token) — gate PROCEEDs"
MUTANT = ("        adapter._wall_clock = AdvancingClock(delta=0.005).wall   # MUTATED: a SECOND "
          "source -> mismatched coherence token")


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_suite():
    """Run batch C's ledger file. The ledger's assertion lives in the session-scoped fixture's
    teardown, so the whole FILE (not one test) is the unit."""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integration/test_ledger_persistence.py",
         "-p", "no:randomly", "-rX", "--tb=line", "-q"],
        cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=600,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    tail = [l for l in out.splitlines() if re.search(r"^\d+ (passed|failed)|passed|failed|error", l)]
    return {
        "returncode": rc,
        "summary": tail[-1].strip() if tail else "(no summary line)",
        "gate_refused_coherence": "CLOCK_INJECTION_REFUSED: COHERENCE" in out,
        "ledger_assertion_fired": "GATE LEDGER VIOLATION" in out,
        "ledger_names_the_nodeid": NODEID in out and "REFUSED_COHERENCE" in out,
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<26} {v}")
    lines.append(f"  EXPECT: {expectation}")
    return lines + [""]


def main():
    original = open(SRC, "rb").read()
    text = original.decode("utf-8")
    assert text.count(ANCHOR) == 1, "batch C's coherent-pair anchor is not unique in the ledger file"
    before = sha256(SRC)

    out = ["WO-035 §4 BITE PROOF — the gate ledger STILL BITES after batch C.",
           "Four artifacts, sha256 exact-restore. The net is proved on batch C's OWN file.",
           f"  file   : {os.path.relpath(SRC, REPO)}",
           f"  nodeid : {NODEID}",
           f"  sha256 BEFORE : {before}", ""]

    d1 = digest(*run_suite())
    out += block("ARTIFACT 1 — PRISTINE (the net is quiet because the injections are correct)", d1,
                 "returncode 0, all passed, no refusal, no ledger violation")

    open(SRC, "wb").write(text.replace(ANCHOR, MUTANT, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED: {sha256(SRC)}", ""]
        d2 = digest(*run_suite())
        rc2, out2 = run_suite()
        keep = [l.strip() for l in out2.splitlines()
                if "GATE LEDGER VIOLATION" in l or ("REFUSED_COHERENCE" in l and "::" in l)]
    finally:
        open(SRC, "wb").write(original)

    out += block("ARTIFACT 2 — MUTATED (the BITE: an incoherent pair must NOT pass silently)", d2,
                 "nonzero returncode, gate REFUSES on COHERENCE, ledger assertion fires NAMING the nodeid")
    out += ["  VERBATIM — the ledger's session-end assertion:"]
    out += [f"    {l}" for l in (keep or ["    (the ledger assertion did not fire — see flags above)"])]
    out += [""]

    d3 = digest(*run_suite())
    out += block("ARTIFACT 3 — RESTORED", d3, "returncode 0, all passed, net quiet again")

    after = sha256(SRC)
    exact = after == before
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --",
            f"  sha256 AFTER  : {after}",
            f"  IDENTICAL     : {exact}", ""]

    ok = (d1["returncode"] == 0 and not d1["ledger_assertion_fired"]
          and d2["returncode"] != 0 and d2["gate_refused_coherence"]
          and d2["ledger_assertion_fired"] and d2["ledger_names_the_nodeid"]
          and d3["returncode"] == 0 and not d3["ledger_assertion_fired"] and exact)
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
