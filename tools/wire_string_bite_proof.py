"""WO-017 §1.6 — bite-proof harness for wire-string retention (four artifacts, sha256).

For each of the three guards, prove it BITES: A1 the target test PASSES with the guard
present; A2 WEAKEN the guard in src and the SAME test REAL-FAILS; A3 RESTORE and it PASSES
again; A4 sha256 confirms the restore is byte-identical. A guard whose removal changes no
test is decorative (0.1d); these are load-bearing.

  (a) checksum input == transmitted text  -> weaken .wire consumption to a str() re-render
  (b) missing wire string RAISES           -> weaken the no-fallback guard condition away
  (c) scientific-notation frame validates  -> weaken .wire consumption to a str() re-render

NO src change persists: every weakening is reverted by exact-byte restore before exit.
"""
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "data", "adapters", "kraken_v2_book.py")
TESTFILE = "tests/integration/test_wire_string_retention.py"

# Each proof: (label, node_id, (old_substring, weakened_substring)). Single-line anchors so
# the working tree's CRLF line endings (core.autocrlf) do not defeat the match. The qty side
# is weakened because proof (a) inspects bids[0][1] (the qty column).
WIRE_CONSUME_OLD = '        qw = getattr(qty, "wire", None)'
WIRE_CONSUME_WEAK = '        qw = str(qty)  # WEAKENED: re-render instead of consuming .wire'
GUARD_OLD = "        if pw is None or qw is None:"
GUARD_WEAK = "        if False:  # WEAKENED: no-fallback guard disabled"

PROOFS = [
    ("(a) checksum input == transmitted text, not a re-render",
     f"{TESTFILE}::test_checksum_input_is_transmitted_text_not_a_rerender",
     (WIRE_CONSUME_OLD, WIRE_CONSUME_WEAK)),
    ("(b) missing wire string RAISES CHECKSUM_WIRE_STRING_MISSING (no fallback)",
     f"{TESTFILE}::test_missing_wire_string_raises_declared_code",
     (GUARD_OLD, GUARD_WEAK)),
    ("(c) scientific-notation frame round-trips and validates",
     f"{TESTFILE}::test_scientific_notation_frame_round_trips_and_validates",
     (WIRE_CONSUME_OLD, WIRE_CONSUME_WEAK)),
]


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_test(node_id):
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run(
        [sys.executable, "-m", "pytest", node_id, "-p", "no:randomly", "-q",
         "--no-header", "-o", "cache_dir=.pytest_cache"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    tail = "\n".join(p.stdout.strip().splitlines()[-8:])
    return p.returncode, tail


def main():
    out = []
    out.append("WO-017 §1.6 BITE PROOFS — wire-string retention (four artifacts each, sha256)")
    out.append(f"Target: {os.path.relpath(SRC, REPO)}")
    out.append("Reason code (b): CHECKSUM_WIRE_STRING_MISSING (no-fallback guard, load-bearing)")
    out.append("")

    original = open(SRC, "rb").read()
    before = sha256(SRC)
    out.append(f"sha256 BEFORE (all proofs): {before}")
    out.append("")

    all_ok = True
    for label, node_id, (old, weak) in PROOFS:
        assert original.decode().count(old) == 1, f"anchor not unique for {label!r}"
        out.append("=" * 78)
        out.append(f"PROOF {label}")
        out.append(f"  test: {node_id}")
        out.append("")

        # A1 — guard present, PASS
        rc1, t1 = run_test(node_id)
        out.append(f"-- ARTIFACT 1 — PASS (guard present)  [rc={rc1}] --")
        out.append(t1)
        out.append("")

        # A2 — weaken, REAL FAIL
        weakened = original.decode().replace(old, weak).encode()
        with open(SRC, "wb") as f:
            f.write(weakened)
        rc2, t2 = run_test(node_id)
        out.append(f"-- ARTIFACT 2 — REAL FAIL (guard weakened)  [rc={rc2}] --")
        out.append(f"WEAKENING: {old.strip().splitlines()[0]!r} -> {weak.strip().splitlines()[0]!r}")
        out.append(t2)
        out.append("")

        # A3 — restore, PASS
        with open(SRC, "wb") as f:
            f.write(original)
        rc3, t3 = run_test(node_id)
        out.append(f"-- ARTIFACT 3 — PASS (guard restored)  [rc={rc3}] --")
        out.append(t3)
        out.append("")

        # A4 — sha256 exact restore
        after = sha256(SRC)
        exact = (after == before)
        out.append("-- ARTIFACT 4 — sha256 EXACT-RESTORE --")
        out.append(f"sha256 AFTER : {after}")
        out.append(f"EXACT RESTORE: {'YES — byte-identical' if exact else 'NO'}")
        out.append("")

        ok = (rc1 == 0 and rc2 != 0 and rc3 == 0 and exact)
        all_ok = all_ok and ok
        out.append(f"RESULT: A1 PASS={rc1 == 0}  A2 REAL-FAIL={rc2 != 0}  "
                   f"A3 PASS={rc3 == 0}  A4 sha256-exact={exact}  => {'OK' if ok else 'FAIL'}")
        out.append("")

    out.append("=" * 78)
    out.append(f"ALL THREE PROOFS: {'OK' if all_ok else 'FAIL'}")

    text = "\n".join(out)
    dest = os.path.join(REPO, "evidence", "WO-017", "bite_proofs.txt")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    # final safety: src must be byte-identical to how we found it
    assert sha256(SRC) == before, "SRC NOT RESTORED — aborting"
    print(text)
    print(f"\n[written] {os.path.relpath(dest, REPO)}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
