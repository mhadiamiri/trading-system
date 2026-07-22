"""WO-013 §2 — bite proof for the FULLY-ENFORCED declared=>producible check (four artifacts, sha256).

Prove the enforcement BITES now that the known-set exemption is gone: A1 the producibility test
PASSES; A2 INJECT a declared-but-unproducible code into VALID_REASON_CODES and the SAME test
REAL-FAILS (naming the injected code); A3 RESTORE and it PASSES; A4 sha256 confirms byte-identical
restore. A check that cannot fail on a declared-but-unproducible code is a 0.1d false guarantee;
this shows it is load-bearing.

NO src change persists: the injection is reverted by exact-byte restore before exit.
"""
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "logkit", "decision.py")
NODE = ("tests/test_reason_code_vocabulary.py::TestReasonCodeCompleteness"
        "::test_every_declared_code_is_producible")

# Single-line anchor (CRLF-safe). Inject a bogus declared code that appears NOWHERE in production
# as a literal, so property 2 must flag it as unproducible.
ANCHOR = '        "SHORT_SIGNAL",  # Short position signal'
INJECT = ANCHOR + '\n        "BITEPROOF_NEVER_EMITTED_XYZZY",  # WEAKENED: declared but no code path emits it'


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_test():
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run(
        [sys.executable, "-m", "pytest", NODE, "-p", "no:randomly", "-q", "--no-header"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    tail = "\n".join(p.stdout.strip().splitlines()[-8:])
    return p.returncode, tail


def main():
    original = open(SRC, "rb").read()
    assert original.decode().count(ANCHOR) == 1, "anchor not unique"
    before = sha256(SRC)

    out = ["WO-013 §2 BITE PROOF — declared=>producible enforcement (four artifacts, sha256)",
           f"Target: {os.path.relpath(SRC, REPO)}  (inject a declared-but-unproducible code)",
           f"test: {NODE}", "", f"sha256 BEFORE: {before}", ""]

    rc1, t1 = run_test()
    out += [f"-- ARTIFACT 1 — PASS (exemption removed; every declared code producible)  [rc={rc1}] --", t1, ""]

    with open(SRC, "wb") as f:
        f.write(original.decode().replace(ANCHOR, INJECT).encode())
    rc2, t2 = run_test()
    out += [f"-- ARTIFACT 2 — REAL FAIL (declared-but-unproducible code injected)  [rc={rc2}] --",
            'INJECTED: "BITEPROOF_NEVER_EMITTED_XYZZY" into VALID_REASON_CODES', t2, ""]

    with open(SRC, "wb") as f:
        f.write(original)
    rc3, t3 = run_test()
    out += [f"-- ARTIFACT 3 — PASS (injection removed)  [rc={rc3}] --", t3, ""]

    after = sha256(SRC)
    exact = (after == before)
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --", f"sha256 AFTER : {after}",
            f"EXACT RESTORE: {'YES — byte-identical' if exact else 'NO'}", ""]

    ok = (rc1 == 0 and rc2 != 0 and rc3 == 0 and exact)
    out.append(f"RESULT: A1 PASS={rc1 == 0}  A2 REAL-FAIL={rc2 != 0}  A3 PASS={rc3 == 0}  "
               f"A4 sha256-exact={exact}  => {'OK' if ok else 'FAIL'}")

    text = "\n".join(out)
    dest = os.path.join(REPO, "evidence", "WO-013", "enforcement_bite_proof.txt")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    assert sha256(SRC) == before, "SRC NOT RESTORED — aborting"
    print(text)
    print(f"\n[written] {os.path.relpath(dest, REPO)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
