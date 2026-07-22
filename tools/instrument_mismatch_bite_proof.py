"""WO-013 item 1 — bite proof: a cross-instrument delta is REFUSED with the declared code
(four artifacts, sha256, terminating in the refusal — 0.1i).

A1 the refusal test PASSES (cross-instrument -> raises MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH);
A2 WEAKEN the guard (disable the raise) and the SAME test REAL-FAILS (no refusal); A3 RESTORE -> PASS;
A4 sha256 confirms byte-identical restore. A refusal that cannot fire on a cross-instrument delta is a
0.1d false guarantee; this shows it is load-bearing (a refusal, not a warning).
"""
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "loop", "host_baseline.py")
NODE = ("tests/integration/test_mean_cycle_baseline_gate.py"
        "::test_instrument_mismatch_is_refused_not_warned")

ANCHOR = "    if stored != measured_instrument:"
WEAK = "    if False:  # WEAKENED: cross-instrument refusal disabled"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_test():
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run(
        [sys.executable, "-m", "pytest", NODE, "-p", "no:randomly", "-q", "--no-header"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    return p.returncode, "\n".join(p.stdout.strip().splitlines()[-8:])


def main():
    original = open(SRC, "rb").read()
    assert original.decode().count(ANCHOR) == 1, "anchor not unique"
    before = sha256(SRC)
    out = ["WO-013 item 1 BITE PROOF — cross-instrument delta REFUSED (four artifacts, sha256)",
           f"Target: {os.path.relpath(SRC, REPO)}::require_measurement_instrument",
           "Reason code: MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH  (refusal, not warning)",
           f"test: {NODE}", "", f"sha256 BEFORE: {before}", ""]

    rc1, t1 = run_test()
    out += [f"-- ARTIFACT 1 — PASS (refusal present: cross-instrument raises the code)  [rc={rc1}] --", t1, ""]

    with open(SRC, "wb") as f:
        f.write(original.decode().replace(ANCHOR, WEAK).encode())
    rc2, t2 = run_test()
    out += [f"-- ARTIFACT 2 — REAL FAIL (refusal disabled: DID NOT RAISE)  [rc={rc2}] --",
            f"WEAKENING: {ANCHOR.strip()!r} -> {WEAK.strip()!r}", t2, ""]

    with open(SRC, "wb") as f:
        f.write(original)
    rc3, t3 = run_test()
    out += [f"-- ARTIFACT 3 — PASS (refusal restored)  [rc={rc3}] --", t3, ""]

    after = sha256(SRC)
    exact = (after == before)
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --", f"sha256 AFTER : {after}",
            f"EXACT RESTORE: {'YES — byte-identical' if exact else 'NO'}", ""]
    ok = (rc1 == 0 and rc2 != 0 and rc3 == 0 and exact)
    out.append(f"RESULT: A1 PASS={rc1 == 0}  A2 REAL-FAIL={rc2 != 0}  A3 PASS={rc3 == 0}  "
               f"A4 sha256-exact={exact}  => {'OK' if ok else 'FAIL'}")

    text = "\n".join(out)
    dest = os.path.join(REPO, "evidence", "WO-013", "instrument_mismatch_bite_proof.txt")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    assert sha256(SRC) == before, "SRC NOT RESTORED — aborting"
    print(text)
    print(f"\n[written] {os.path.relpath(dest, REPO)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
