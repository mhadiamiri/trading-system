"""WO-029 §4 — THE SAFETY NET DID NOT GO SLACK AS THE POPULATION IT GUARDS GREW.

Batch A took five tests from "injects no clock" (gate EARLY_RETURN) to "injects a coherent pair"
(gate PROCEED_COHERENT). That is exactly the change that could quietly turn the net into scenery:
the ledger's suite-wide assertion is "zero refusals from unmarkered tests", and a batch that adds
five injections is a batch that adds five chances for a WRONG injection to slip through unnoticed.
This is NOT a new guard — the gate and the ledger are WO-023/024/025 and unchanged. It re-runs the
existing net against the NEW population and shows it still catches a wrong injection.

THE BITE: corrupt ONE batch-A conversion (race 1) so its wall and monotonic come from TWO
AdvancingClock instances instead of one — an INCOHERENT pair, the precise failure mode a careless
conversion produces (both clocks look fake and plausible; only the shared `_coherence_token`
distinguishes one source from two). Expect BOTH halves of the net to fire:
  (i) the gate REFUSES pre-connection with CLOCK_INJECTION_REFUSED: COHERENCE, so the test fails;
  (ii) the session-end ledger assertion FAILS naming the nodeid, so a refusal cannot be lost even
       if someone were to swallow the test-level failure.

Four artifacts, sha256 exact-restore of the mutated file.
"""
import hashlib
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "tests", "integration", "test_live_capture.py")
OUT = os.path.join(REPO, "evidence", "WO-029", "ledger_still_bites_bite_proof.txt")
NODEID = ("tests/integration/test_live_capture.py::"
          "test_runner_drives_instrumented_transport_end_to_end")

ANCHOR = "    adapter._wall_clock = clock.wall          # the pair's other half — coherent, same token"
MUTANT = ("    adapter._wall_clock = AdvancingClock(delta=CLOCK_DELTA).wall   # MUTATED: a SECOND "
          "source -> mismatched coherence token")


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_suite():
    """Run the batch-A file; return (returncode, combined output). The ledger's assertion lives in
    the session-scoped fixture's teardown, so the whole file (not one test) must be the unit."""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integration/test_live_capture.py",
         "-p", "no:randomly", "-rX", "--tb=line", "-q"],
        cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=600,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    """The three facts this proof turns on, extracted so the artifact is readable."""
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
    assert text.count(ANCHOR) == 1, "race 1's coherent-pair anchor is not unique in the batch-A file"
    before = sha256(SRC)

    out = [
        "WO-029 §4 BITE PROOF — THE GATE LEDGER STILL BITES AFTER BATCH A (4 artifacts, sha256)",
        f"Mutated file: {os.path.relpath(SRC, REPO)}",
        f"Victim race : race 1 — {NODEID}",
        "Mutation    : wall from a SECOND AdvancingClock -> both clocks injected, tokens MISMATCHED",
        "Net under test: WO-023 §4 gate (COHERENCE branch) + WO-024/025 §3 session-end ledger",
        f"sha256 BEFORE: {before}",
        "",
    ]

    rc1, o1 = run_suite()
    d1 = digest(rc1, o1)
    out += block("ARTIFACT 1 — PRISTINE (the net is quiet because the batch is correct)", d1,
                 "returncode 0, 10 passed, no refusal, no ledger violation")

    open(SRC, "wb").write(text.replace(ANCHOR, MUTANT).encode("utf-8"))
    rc2, o2 = run_suite()
    d2 = digest(rc2, o2)
    out += [f"  sha256 WHILE MUTATED: {sha256(SRC)}", ""]
    out += block("ARTIFACT 2 — MUTATED (the bite: an incoherent pair must NOT pass silently)", d2,
                 "returncode != 0, gate REFUSED COHERENCE, ledger violation naming the nodeid")
    out += ["  VERBATIM — the ledger's session-end assertion:"]
    grab, keep = False, []
    for line in o2.splitlines():
        if "GATE LEDGER VIOLATION" in line:
            grab = True
        if grab:
            keep.append("    " + line.rstrip())
        if grab and "markered set:" in line:
            break
    out += (keep or ["    (the ledger assertion did not fire — see ARTIFACT 2 flags above)"]) + [""]

    open(SRC, "wb").write(original)
    rc3, o3 = run_suite()
    d3 = digest(rc3, o3)
    out += block("ARTIFACT 3 — RESTORED", d3, "returncode 0, 10 passed, net quiet again")

    after = sha256(SRC)
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --",
            f"sha256 AFTER:  {after}",
            f"IDENTICAL: {'YES' if after == before else 'NO'}", ""]

    pristine_ok = (d1["returncode"] == 0 and not d1["gate_refused_coherence"]
                   and not d1["ledger_assertion_fired"])
    bite_ok = (d2["returncode"] != 0 and d2["gate_refused_coherence"]
               and d2["ledger_assertion_fired"] and d2["ledger_names_the_nodeid"])
    restored_ok = (d3["returncode"] == 0 and not d3["ledger_assertion_fired"])
    verdict = "PASS" if (pristine_ok and bite_ok and restored_ok and after == before) else "FAIL"
    out += [f"VERDICT: {verdict}"]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
