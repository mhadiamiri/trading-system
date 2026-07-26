"""WO-030 §3 — bite proof: the GENERALIZED live-capable registration contract (D38) is load-bearing.

Generalizes WO-028's connect_fn bite proof: register(live_capture=True) now requires the builder to
accept EVERY parameter the live path forwards (registry._LIVE_FORWARDED_PARAMS: connect_fn,
monotonic_clock, wall_clock). Four artifacts, sha256 exact-restore of the guard file (registry.py),
BOTH directions:

  A1 GUARD PRESENT (pristine):
       - REFUSAL (per-parameter): a throwaway live_capture=True builder missing ONLY `wall_clock`
         (but having connect_fn + monotonic_clock) raises LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM,
         the message naming `wall_clock` SPECIFICALLY (proves the check is per-parameter, not just
         "has connect_fn"). A builder missing `connect_fn` still refuses (WO-028's case still holds).
       - PRESERVATION: a builder with ALL THREE registers cleanly; a live_capture=False builder with
         NONE registers cleanly (no over-fire).
       - the REAL `_build_kraken_v2` passes the generalized check (it accepts all three, §2).
  A2 GUARD WEAKENED (necessity of the CLOCK params): shrink _LIVE_FORWARDED_PARAMS to ("connect_fn",)
       — the WO-028 behaviour — and the wall_clock-missing builder REGISTERS SILENTLY. Proves the clock
       params in the inventory are what enforce the generalized contract, not arg-binding.
  A3 GUARD RESTORED: the wall_clock-missing builder raises again.
  A4 sha256(registry.py) AFTER == BEFORE (byte-identical restore).

Each check runs in a FRESH subprocess (registry is module-global). No suite test is added.
"""
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "data", "adapters", "registry.py")
OUT = os.path.join(REPO, "evidence", "WO-030", "registration_validation_bite_proof.txt")

ANCHOR = '_LIVE_FORWARDED_PARAMS = ("connect_fn", "monotonic_clock", "wall_clock")'
WEAK = '_LIVE_FORWARDED_PARAMS = ("connect_fn",)  # WEAKENED: clock params no longer required'

# live_capture=True, missing ONLY wall_clock (has connect_fn + monotonic_clock).
CHECK_MISSING_WALL = '''
from trading.data.adapters import registry
try:
    @registry.register("bite_missing_wall", live_capture=True)
    def _b(decision_logger=None, connect_fn=None, monotonic_clock=None):
        return object()
    print("REGISTERED_NO_RAISE")
except TypeError as e:
    print("RAISED_CODE:", str(e).split(":", 1)[0])
    print("NAMES_WALL_CLOCK:", "wall_clock" in str(e))
    print("FULL_MSG:", str(e))
'''

# live_capture=True, missing connect_fn (WO-028's original case — must still refuse).
CHECK_MISSING_CONNECT = '''
from trading.data.adapters import registry
try:
    @registry.register("bite_missing_connect", live_capture=True)
    def _b(decision_logger=None, monotonic_clock=None, wall_clock=None):
        return object()
    print("REGISTERED_NO_RAISE")
except TypeError as e:
    print("RAISED_CODE:", str(e).split(":", 1)[0], "| names connect_fn:", "connect_fn" in str(e))
'''

# preservation: all three present, and a non-live builder with none.
CHECK_PRESERVE = '''
from trading.data.adapters import registry
@registry.register("bite_good", live_capture=True)
def _good(decision_logger=None, connect_fn=None, monotonic_clock=None, wall_clock=None):
    return object()
@registry.register("bite_nonlive")
def _nonlive(decision_logger=None):
    return object()
print("PRESERVE_OK: full live builder + non-live builder both registered")
print("REAL _build_kraken_v2 live_capable:", registry.is_live_capable("kraken_v2"))
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
    assert original.decode().count(ANCHOR) == 1, "guard anchor (_LIVE_FORWARDED_PARAMS) not unique"
    before = sha256(SRC)
    out = ["WO-030 §3 BITE PROOF — generalized live-capable registration contract (D38), 4 artifacts, sha256",
           f"Guard file: {os.path.relpath(SRC, REPO)}  (register(): the _LIVE_FORWARDED_PARAMS check)",
           "Contract code: LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM  (generalized from WO-028's connect_fn code)",
           f"sha256 BEFORE: {before}", ""]

    r_wall = run(CHECK_MISSING_WALL)
    r_conn = run(CHECK_MISSING_CONNECT)
    r_pre = run(CHECK_PRESERVE)
    out += ["-- ARTIFACT 1 — GUARD PRESENT (pristine) --",
            "  [refusal, per-param] live builder missing ONLY wall_clock:",
            "    " + r_wall.replace("\n", "\n    "),
            "  [refusal] live builder missing connect_fn (WO-028 case still holds):",
            "    " + r_conn.replace("\n", "\n    "),
            "  [preserve] full live builder + non-live builder:",
            "    " + r_pre.replace("\n", "\n    "), ""]

    open(SRC, "wb").write(original.decode().replace(ANCHOR, WEAK).encode())
    r_weak = run(CHECK_MISSING_WALL)
    out += ["-- ARTIFACT 2 — GUARD WEAKENED (necessity of clock params: inventory -> ('connect_fn',)) --",
            "  wall_clock-missing builder now:", "    " + r_weak.replace("\n", "\n    "),
            f"  sha256 WHILE WEAKENED: {sha256(SRC)}", ""]

    open(SRC, "wb").write(original)
    r_restored = run(CHECK_MISSING_WALL)
    out += ["-- ARTIFACT 3 — GUARD RESTORED --",
            "  wall_clock-missing builder again:", "    " + r_restored.replace("\n", "\n    "), ""]

    after = sha256(SRC)
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --",
            f"sha256 AFTER:  {after}", f"IDENTICAL: {'YES' if after == before else 'NO'}", ""]

    verdict = ("PASS" if ("RAISED_CODE: LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM" in r_wall
                          and "NAMES_WALL_CLOCK: True" in r_wall
                          and "RAISED_CODE: LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM" in r_conn
                          and "PRESERVE_OK" in r_pre
                          and "REGISTERED_NO_RAISE" in r_weak
                          and "RAISED_CODE: LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM" in r_restored
                          and after == before) else "FAIL")
    out += [f"VERDICT: {verdict}"]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
