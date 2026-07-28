"""WO-037 §4 BITE PROOF — the archive-readiness guard catches an emitted-undeclared RUNTIME code.

Four artifacts, sha256 exact-restore, both directions.

§4's requirement: *"introduce a throwaway emitted-undeclared runtime code -> guard fails; declare it
-> passes; restore, sha256."*

The mutation is applied on the INDIRECTION path deliberately — a new risk `REASON_*` constant wired
into `check()`'s return. That is the exact route `tests/test_reason_code_vocabulary.py` documents as
its blind spot ("reason_code=<var>: the risk REASON_* constants"), so the proof shows the new guard
covering ground the existing one cannot, rather than duplicating it.

  ARTIFACT 1 — PRISTINE: both guards green.
  ARTIFACT 2 — THE BITE: an undeclared REASON_* constant, WIRED. The archive guard FAILS naming the
      code; the literal-form guard stays GREEN (its documented blind spot, demonstrated).
  ARTIFACT 3 — DECLARED: the same code added to VALID_REASON_CODES -> the archive guard PASSES.
      This is the preservation dual: the guard bans an UNDECLARED archived code, not a new code.
  ARTIFACT 4 — RESTORED + sha256 exact-restore of both production files.

    python tools/wo037_archive_readiness_bite_proof.py

Writes to .artifacts/ (WO-032 §4.1).
"""
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(REPO, "src", "trading", "risk", "engine.py")
DECISION = os.path.join(REPO, "src", "trading", "logkit", "decision.py")
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo037_archive_readiness_bite_proof")

THROWAWAY_CONST = "REASON_VETO_WO037_PROBE"
THROWAWAY_CODE = "RISK_VETO_WO037_PROBE"

# Define the constant beside the real ones AND wire it in one edit — a DEAD constant would not bite
# (it would only land on the known-dead list), so the probe must be genuinely referenced. The tuple
# reference is a Load-context Name, which is exactly what `_wired_risk_constants()` counts as wired.
ENGINE_ANCHOR = '    REASON_VETO_INVALID_INPUT = "RISK_VETO_INVALID_INPUT"'
ENGINE_MUTANT = (ENGINE_ANCHOR
                 + f'\n    {THROWAWAY_CONST} = "{THROWAWAY_CODE}"'
                 + f'\n    _WO037_WIRE = ({THROWAWAY_CONST},)   # WIRED (bite proof)')

DECLARE_ANCHOR = '        "RISK_VETO_INVALID_INPUT",  # vetoed: invalid desired-position input'
DECLARE_MUTANT = (DECLARE_ANCHOR + f'\n        "{THROWAWAY_CODE}",  # WO-037 bite proof (throwaway)')


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(node):
    p = subprocess.run(
        [sys.executable, "-m", "pytest", node, "-p", "no:randomly", "-q", "--no-header", "--tb=line"],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONUTF8": "1"}, timeout=600)
    out = (p.stdout or "") + (p.stderr or "")
    tail = [l.strip() for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    return p.returncode, (tail[-1] if tail else "(no summary)"), out


ARCHIVE = "tests/test_archive_readiness.py"
LITERAL = "tests/test_reason_code_vocabulary.py"


def block(title, rc_a, sum_a, rc_l, sum_l, names, expectation):
    return [f"-- {title} --",
            f"  archive-readiness guard : rc={rc_a}  {sum_a}",
            f"  literal-form guard      : rc={rc_l}  {sum_l}",
            f"  archive guard NAMES {THROWAWAY_CODE} : {names}",
            f"  EXPECT: {expectation}", ""]


def main():
    eng_before, dec_before = sha256(ENGINE), sha256(DECISION)
    eng_orig = open(ENGINE, "rb").read()
    dec_orig = open(DECISION, "rb").read()
    eng_text = eng_orig.decode("utf-8")
    dec_text = dec_orig.decode("utf-8")
    assert eng_text.count(ENGINE_ANCHOR) == 1, "engine anchor not unique"
    assert dec_text.count(DECLARE_ANCHOR) == 1, "declaration anchor not unique"

    out = ["WO-037 §4 BITE PROOF — the archive-readiness guard bites an emitted-undeclared runtime code.",
           "Four artifacts, sha256 exact-restore, both directions.",
           "The mutation rides the INDIRECTION path (a wired risk REASON_* constant) — the route the",
           "literal-form guard documents as its blind spot — so this proves NEW coverage, not overlap.",
           f"  engine.py   sha256 BEFORE : {eng_before}",
           f"  decision.py sha256 BEFORE : {dec_before}", ""]

    try:
        # ARTIFACT 1 — pristine
        rc_a, s_a, _ = run(ARCHIVE)
        rc_l, s_l, _ = run(LITERAL)
        out += block("ARTIFACT 1 — PRISTINE", rc_a, s_a, rc_l, s_l, False,
                     "both guards green")

        # ARTIFACT 2 — the bite: undeclared + wired
        open(ENGINE, "wb").write(eng_text.replace(ENGINE_ANCHOR, ENGINE_MUTANT, 1).encode("utf-8"))
        rc_a2, s_a2, o_a2 = run(ARCHIVE)
        rc_l2, s_l2, _ = run(LITERAL)
        names = THROWAWAY_CODE in o_a2
        out += block("ARTIFACT 2 — THE BITE (undeclared REASON_* constant, WIRED)",
                     rc_a2, s_a2, rc_l2, s_l2, names,
                     "archive guard FAILS naming the code; literal-form guard stays GREEN "
                     "(its documented blind spot)")
        verbatim = [l.strip() for l in o_a2.splitlines() if THROWAWAY_CODE in l and "assert" not in l]
        out += ["  VERBATIM:"] + [f"    {l}" for l in verbatim[:4]] + [""]

        # ARTIFACT 3 — preservation dual: declare it, guard passes
        open(DECISION, "wb").write(
            dec_text.replace(DECLARE_ANCHOR, DECLARE_MUTANT, 1).encode("utf-8"))
        rc_a3, s_a3, _ = run(ARCHIVE)
        rc_l3, s_l3, _ = run(LITERAL)
        out += block("ARTIFACT 3 — PRESERVATION DUAL (same code, now DECLARED)",
                     rc_a3, s_a3, rc_l3, s_l3, False,
                     "archive guard PASSES — it bans an UNDECLARED archived code, not a new code")
    finally:
        open(ENGINE, "wb").write(eng_orig)
        open(DECISION, "wb").write(dec_orig)

    # ARTIFACT 4 — restored + sha256
    rc_a4, s_a4, _ = run(ARCHIVE)
    rc_l4, s_l4, _ = run(LITERAL)
    eng_after, dec_after = sha256(ENGINE), sha256(DECISION)
    exact = eng_after == eng_before and dec_after == dec_before
    out += block("ARTIFACT 4 — RESTORED", rc_a4, s_a4, rc_l4, s_l4, False, "both green again")
    out += ["-- sha256 EXACT-RESTORE --",
            f"  engine.py   AFTER : {eng_after}",
            f"  decision.py AFTER : {dec_after}",
            f"  BOTH IDENTICAL    : {exact}", ""]

    ok = (rc_a == 0 and rc_a2 != 0 and names and rc_l2 == 0
          and rc_a3 == 0 and rc_a4 == 0 and exact)
    out += [f"VERDICT: {'PASS' if ok else 'FAIL'}"]
    if ok:
        out += ["",
                "NOTE the literal-form guard stayed GREEN through ARTIFACT 2. That is not a defect in",
                "it — it is the documented reason_code=<var> blind spot, demonstrated. The archive",
                "guard exists precisely to cover that route into the corpus."]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    assert exact, "PRODUCTION FILES NOT RESTORED — aborting"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
