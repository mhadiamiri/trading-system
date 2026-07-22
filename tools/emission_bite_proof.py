"""WO-013 §1 — bite proofs for the three wired reason-code emissions (four artifacts each, sha256).

Each proof shows the emission is load-bearing: A1 the behavioral test PASSES (the declared code
lands in the decision log); A2 WEAKEN the PRODUCTION emission back to its old undeclared string and
the SAME test REAL-FAILS (the declared code is no longer in the log); A3 RESTORE -> PASS; A4 sha256
confirms byte-identical restore. Terminates in the observable effect (0.1i): the assertion is that
the code IS IN THE DECISION LOG, not that an emit function was called.

NO src change persists: every weakening is reverted by exact-byte restore before exit.
"""
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(REPO, "src", "trading", "loop", "live.py")
IFACE = os.path.join(REPO, "src", "trading", "execution", "interface.py")
T = "tests/integration/test_reason_code_emission.py"

SIGNAL_OLD = '            signal_reason = "LONG_SIGNAL" if desired_position.side.value == "BUY" else "SHORT_SIGNAL"'
SIGNAL_WEAK = '            signal_reason = "STRAT_SIGNAL_BUY" if desired_position.side.value == "BUY" else "STRAT_SIGNAL_SELL"  # WEAKENED'
KS_OLD = '    def __init__(self, reason_code: str = "KILL_SWITCH_ENGAGED") -> None:'
KS_WEAK = '    def __init__(self, reason_code: str = "EXEC_BLOCKED_KILL_SWITCH") -> None:  # WEAKENED'

# (label, node, file, old, weak)
PROOFS = [
    ("LONG_SIGNAL emitted to the decision log", f"{T}::test_long_signal_emitted_to_decision_log",
     LIVE, SIGNAL_OLD, SIGNAL_WEAK),
    ("SHORT_SIGNAL emitted to the decision log", f"{T}::test_short_signal_emitted_to_decision_log",
     LIVE, SIGNAL_OLD, SIGNAL_WEAK),
    ("KILL_SWITCH_ENGAGED emitted + cancellation preserved",
     f"{T}::test_kill_switch_engaged_emitted_and_cancellation_preserved", IFACE, KS_OLD, KS_WEAK),
]


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_test(node):
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run(
        [sys.executable, "-m", "pytest", node, "-p", "no:randomly", "-q", "--no-header"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    return p.returncode, "\n".join(p.stdout.strip().splitlines()[-6:])


def main():
    out = ["WO-013 §1 BITE PROOFS — reason-code emission (four artifacts each, sha256)", ""]
    all_ok = True
    for label, node, path, old, weak in PROOFS:
        original = open(path, "rb").read()
        assert original.decode().count(old) == 1, f"anchor not unique for {label!r} in {path}"
        before = sha256(path)
        out += ["=" * 78, f"PROOF: {label}", f"  test: {node}",
                f"  target: {os.path.relpath(path, REPO)}", f"  sha256 BEFORE: {before}", ""]

        rc1, t1 = run_test(node)
        out += [f"-- ARTIFACT 1 — PASS (declared code lands in the decision log)  [rc={rc1}] --", t1, ""]

        with open(path, "wb") as f:
            f.write(original.decode().replace(old, weak).encode())
        rc2, t2 = run_test(node)
        out += [f"-- ARTIFACT 2 — REAL FAIL (emission weakened to the old undeclared string)  [rc={rc2}] --",
                f"WEAKENING: {old.strip()[:60]!r} -> old string", t2, ""]

        with open(path, "wb") as f:
            f.write(original)
        rc3, t3 = run_test(node)
        out += [f"-- ARTIFACT 3 — PASS (emission restored)  [rc={rc3}] --", t3, ""]

        after = sha256(path)
        exact = (after == before)
        out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --", f"sha256 AFTER : {after}",
                f"EXACT RESTORE: {'YES — byte-identical' if exact else 'NO'}", ""]
        ok = (rc1 == 0 and rc2 != 0 and rc3 == 0 and exact)
        all_ok = all_ok and ok
        out += [f"RESULT: A1 PASS={rc1 == 0}  A2 REAL-FAIL={rc2 != 0}  A3 PASS={rc3 == 0}  "
                f"A4 sha256-exact={exact}  => {'OK' if ok else 'FAIL'}", ""]
        assert sha256(path) == before, f"{path} NOT RESTORED — aborting"

    out += ["=" * 78, f"ALL THREE PROOFS: {'OK' if all_ok else 'FAIL'}"]
    text = "\n".join(out)
    dest = os.path.join(REPO, "evidence", "WO-013", "emission_bite_proofs.txt")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\n[written] {os.path.relpath(dest, REPO)}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
