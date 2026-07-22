"""WO-018 §5 — bite proofs on the completeness SCAN itself (the guard). Four proofs, four artifacts
each, sha256, terminating in a real failure with the scan's own assertion text. A guard that cannot
fail is a false guarantee (0.1d).

  1. an emitted-but-undeclared event_type            -> scan FAILS naming it
  2. an emitted-but-undeclared reason_code (NON-COLON) -> scan FAILS naming it   (the escape hatch)
  3. a declared-but-unproducible value                -> scan FAILS naming it
  4. a cross-namespace prefix collision               -> scan FAILS naming both  (*** the WO-013 defect mechanism ***)

Each injection is a single-line edit (CRLF-safe) reverted by exact-byte restore before exit.
"""
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(REPO, "src", "trading", "loop", "live.py")
DEC = os.path.join(REPO, "src", "trading", "logkit", "decision.py")
T = "tests/test_reason_code_vocabulary.py"

# (label, node, file, anchor, injected-line, expected-substring-in-failure)
PROOFS = [
    ("emitted-but-undeclared EVENT_TYPE -> scan fails naming it",
     f"{T}::TestRaisedImpliesDeclared::test_every_emitted_event_type_is_declared", LIVE,
     '                event_type="MARKET_DATA_RECEIVED",',
     '                event_type="MARKET_DATA_RECEIVED",  # BITEPROOF event_type="BITEPROOF_EVENT_XYZZY"',
     "BITEPROOF_EVENT_XYZZY"),
    ("emitted-but-undeclared REASON_CODE (non-colon keyword) -> scan fails naming it",
     f"{T}::TestRaisedImpliesDeclared::test_every_emitted_reason_code_is_declared", LIVE,
     '                reason_code="DATA_RECEIVED",',
     '                reason_code="DATA_RECEIVED",  # BITEPROOF reason_code="BITEPROOF_RC_XYZZY"',
     "BITEPROOF_RC_XYZZY"),
    ("declared-but-unproducible reason_code -> scan fails naming it",
     f"{T}::TestDeclaredImpliesProducible::test_every_declared_reason_code_is_producible", DEC,
     '        "SHORT_SIGNAL",  # Short position signal',
     '        "SHORT_SIGNAL", "BITEPROOF_UNPRODUCIBLE_XYZZY",  # Short position signal',
     "BITEPROOF_UNPRODUCIBLE_XYZZY"),
    ("cross-namespace PREFIX COLLISION -> scan fails naming both",
     f"{T}::TestPrefixFreedomAcrossUnion::test_declared_union_is_prefix_free", DEC,
     '        "payload_error",',
     '        "payload_error", "CHECKSUM",  # BITEPROOF cross-namespace collision',
     "CHECKSUM"),
]


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_test(node):
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run([sys.executable, "-m", "pytest", node, "-p", "no:randomly", "-q", "--no-header"],
                       cwd=REPO, env=env, capture_output=True, text=True)
    return p.returncode, p.stdout


def main():
    out = ["WO-018 §5 BITE PROOFS — the completeness SCAN bites (four artifacts each, sha256)", ""]
    all_ok = True
    for label, node, path, anchor, inject, expect in PROOFS:
        original = open(path, "rb").read()
        assert original.decode().count(anchor) == 1, f"anchor not unique for {label!r} in {path}"
        before = sha256(path)
        out += ["=" * 78, f"PROOF: {label}", f"  test: {node}",
                f"  target: {os.path.relpath(path, REPO)}", f"  sha256 BEFORE: {before}", ""]

        rc1, o1 = run_test(node)
        out += [f"-- ARTIFACT 1 — PASS (clean vocabulary)  [rc={rc1}] --",
                "\n".join(o1.strip().splitlines()[-4:]), ""]

        with open(path, "wb") as f:
            f.write(original.decode().replace(anchor, inject).encode())
        rc2, o2 = run_test(node)
        named = expect in o2
        out += [f"-- ARTIFACT 2 — REAL FAIL (defect injected)  [rc={rc2}] --",
                f"INJECTED: {inject.strip()[:70]!r}",
                f"failure NAMES {expect!r}: {named}",
                "\n".join(l for l in o2.splitlines() if expect in l)[:400], ""]

        with open(path, "wb") as f:
            f.write(original)
        rc3, o3 = run_test(node)
        out += [f"-- ARTIFACT 3 — PASS (injection removed)  [rc={rc3}] --",
                "\n".join(o3.strip().splitlines()[-3:]), ""]

        after = sha256(path)
        exact = (after == before)
        ok = (rc1 == 0 and rc2 != 0 and named and rc3 == 0 and exact)
        all_ok = all_ok and ok
        out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --", f"sha256 AFTER : {after}",
                f"EXACT RESTORE: {'YES — byte-identical' if exact else 'NO'}",
                f"RESULT: A1 PASS={rc1 == 0}  A2 REAL-FAIL={rc2 != 0} (named={named})  A3 PASS={rc3 == 0}  "
                f"A4 sha256-exact={exact}  => {'OK' if ok else 'FAIL'}", ""]
        assert sha256(path) == before, f"{path} NOT RESTORED — aborting"

    out += ["=" * 78, f"ALL FOUR PROOFS: {'OK' if all_ok else 'FAIL'}"]
    text = "\n".join(out)
    dest = os.path.join(REPO, "evidence", "WO-018", "scan_bite_proofs.txt")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\n[written] {os.path.relpath(dest, REPO)}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
