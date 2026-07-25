"""WO-028 §3 — bite proof: the LIVE-CAPABLE registration contract (D36-2b) is load-bearing.

Four artifacts, sha256 exact-restore of the guard file (registry.py), BOTH directions:

  A1 GUARD PRESENT (pristine):
       - REFUSAL:      a throwaway `@register("x", live_capture=True)` builder with NO `connect_fn`
                       param raises LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN at registration.
       - PRESERVATION: the SAME builder WITH a `connect_fn` param registers cleanly; AND a
                       `live_capture=False` builder without `connect_fn` registers cleanly (the check
                       does not over-fire on non-live builders).
       - the REAL `_build_kraken_v2` passes the check (it now accepts connect_fn, §2).
  A2 GUARD WEAKENED (necessity): disable the raise in registry.py -> the SAME bad builder REGISTERS
       SILENTLY (DID NOT RAISE). Proves the guard is what enforces the contract, not Python's own
       argument binding (which would only TypeError LATER, at a forwarding call).
  A3 GUARD RESTORED: the bad builder raises again.
  A4 sha256(registry.py) AFTER == BEFORE (byte-identical restore).

Each check runs in a FRESH subprocess (the registry is module-global; a fresh import picks up the
current — weakened or restored — registry.py and starts with a clean _REGISTRY). No suite test is
added: this is a standalone instrument, so the suite count is unchanged (§9: 216 + 1 §4.2 = 217).
"""
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "data", "adapters", "registry.py")
OUT = os.path.join(REPO, "evidence", "WO-028", "registration_validation_bite_proof.txt")

ANCHOR = '        if live_capture and "connect_fn" not in inspect.signature(builder).parameters:'
WEAK = '        if False and "connect_fn" not in inspect.signature(builder).parameters:  # WEAKENED'

# A live_capture=True builder with NO connect_fn — the contract violation the guard must catch.
CHECK_BAD = '''
from trading.data.adapters import registry
try:
    @registry.register("bite_bad", live_capture=True)
    def _bad(decision_logger=None):
        return object()
    print("REGISTERED_NO_RAISE")
except TypeError as e:
    print("RAISED_CODE:", str(e).split(":", 1)[0])
    print("FULL_MSG:", str(e))
'''

# Preservation: a conforming live builder AND a non-live builder without connect_fn both register.
CHECK_PRESERVE = '''
from trading.data.adapters import registry
@registry.register("bite_good", live_capture=True)
def _good(decision_logger=None, connect_fn=None):
    return object()
@registry.register("bite_nonlive")            # live_capture unset -> NOT checked
def _nonlive(decision_logger=None):
    return object()
print("PRESERVE_OK: good_live + nonlive both registered")
# and the REAL builder passes the check (imported the package above triggers its registration):
print("REAL _build_kraken_v2 registered live_capable:", registry.is_live_capable("kraken_v2"))
'''


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(snippet):
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run([sys.executable, "-c", snippet], cwd=REPO, env=env,
                       capture_output=True, text=True)
    return (p.stdout + p.stderr).strip()


def main():
    original = open(SRC, "rb").read()
    assert original.decode().count(ANCHOR) == 1, "guard anchor not unique in registry.py"
    before = sha256(SRC)
    out = ["WO-028 §3 BITE PROOF — live-capable registration contract (D36-2b), four artifacts, sha256",
           f"Guard file: {os.path.relpath(SRC, REPO)}  (register(): the live_capture connect_fn check)",
           "Contract code: LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN",
           f"sha256 BEFORE: {before}", ""]

    # A1 — pristine: refusal fires, preservation holds
    r_bad = run(CHECK_BAD)
    r_pre = run(CHECK_PRESERVE)
    out += ["-- ARTIFACT 1 — GUARD PRESENT (pristine) --",
            "  [refusal]  bad live builder (no connect_fn):", "    " + r_bad.replace("\n", "\n    "),
            "  [preserve] good live builder + non-live builder:", "    " + r_pre.replace("\n", "\n    "),
            ""]

    # A2 — weaken the guard: the bad builder now registers silently
    open(SRC, "wb").write(original.decode().replace(ANCHOR, WEAK).encode())
    r_weak = run(CHECK_BAD)
    out += ["-- ARTIFACT 2 — GUARD WEAKENED (necessity: `if live_capture and ...` -> `if False and ...`) --",
            "  bad live builder now:", "    " + r_weak.replace("\n", "\n    "),
            f"  sha256 WHILE WEAKENED: {sha256(SRC)}", ""]

    # A3 — restore: the bad builder raises again
    open(SRC, "wb").write(original)
    r_restored = run(CHECK_BAD)
    out += ["-- ARTIFACT 3 — GUARD RESTORED --",
            "  bad live builder again:", "    " + r_restored.replace("\n", "\n    "), ""]

    # A4 — sha256 exact-restore
    after = sha256(SRC)
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --",
            f"sha256 AFTER:  {after}",
            f"IDENTICAL: {'YES' if after == before else 'NO'}", ""]

    verdict = ("PASS" if ("RAISED_CODE: LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN" in r_bad
                          and "REGISTERED_NO_RAISE" in r_weak
                          and "RAISED_CODE: LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN" in r_restored
                          and after == before) else "FAIL")
    out += [f"VERDICT: {verdict}"]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
