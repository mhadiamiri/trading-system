"""
WO-037 §4 — ARCHIVE-READINESS OF THE REASON-CODE VOCABULARY.

The corpus ARCHIVES decision records carrying `reason_code`. A code that reaches an archived record
while UNDECLARED makes the archive permanently ungoverned: every later analysis inherits a code with
no definition, and the defect is unfixable after capture. This guard fails CI before that can happen.

It is NOT a duplicate of `test_reason_code_vocabulary.py`. That guard governs the whole vocabulary via
LITERAL forms at the call site, and its own docstring names the hole it cannot cover:

    "reason_code=<var>: the risk REASON_* constants, signal_reason, e.reason_code"

Three sites in production emit `reason_code` INDIRECTLY, and every one of them lands in a decision
record — i.e. in the archive:

    live.py:227   reason_code=signal_reason      <- "LONG_SIGNAL" / "SHORT_SIGNAL"   (live.py:223)
    live.py:248   reason_code=reason_code        <- risk engine REASON_* constants   (engine.py)
    live.py:307   reason_code=e.reason_code      <- KillSwitchEngagedError.reason_code (interface.py:26)

So the literal-form scan governs the vocabulary in general, and this guard governs the ARCHIVE PATH
specifically — including the indirection the other guard declares out of scope.

WHAT IT FOUND WHEN BUILT (WO-037 §3): `engine.py:42` defines
`REASON_VETO_INSUFFICIENT_BALANCE = "RISK_VETO_INSUFFICIENT_BALANCE"`, which is **not declared** in
`VALID_REASON_CODES` and **not referenced anywhere** — it appears exactly once in the repo, at its own
definition. It is therefore not producible today and cannot corrupt an archive. But it sits one line
of wiring away from `check()`'s return, and the moment it is wired it flows through `live.py:248`
into an archived record UNDECLARED, invisible to the literal-form scan. That is what
`test_every_wired_risk_reason_constant_is_declared` exists to catch.
"""

import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
ENGINE = SRC / "trading" / "risk" / "engine.py"
LIVE = SRC / "trading" / "loop" / "live.py"
INTERFACE = SRC / "trading" / "execution" / "interface.py"

from trading.logkit.decision import VALID_REASON_CODES  # noqa: E402


def _declared():
    return {c for codes in VALID_REASON_CODES.values() for c in codes}


# ── the archive path: reason_code values that reach log_decision / log_feed_event ───────────
_LITERAL_ARCHIVED = re.compile(
    r'(?:log_decision|log_feed_event|_log_decision)\s*\([^)]*?reason_code\s*=\s*"([A-Z_][A-Z0-9_]{3,})"',
    re.S)


def _literal_archived_codes():
    """Codes emitted into a decision record as a STRING LITERAL at the call site."""
    found = set()
    for p in sorted(SRC.rglob("*.py")):
        found.update(_LITERAL_ARCHIVED.findall(p.read_text(encoding="utf-8")))
    return found


def _risk_reason_constants():
    """Every `REASON_* = "CODE"` module constant in the risk engine, as {const_name: code}.

    These are the value set of `check()`'s third return, which `live.py:248` passes straight into
    `log_decision(reason_code=...)`. AST, not regex: a constant is an Assign node, and reading it
    that way means a reformat or a line break cannot hide one.
    """
    # NOTE the scope: these are CLASS attributes on RiskEngine, not module-level constants, so this
    # walks the whole tree rather than `tree.body`. A `tree.body`-only walk returns {} silently — the
    # exact shape of a guard that passes because it looked in the wrong place, which is why
    # `test_the_indirection_resolvers_actually_resolve` pins real values.
    tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.startswith("REASON_"):
                    out[t.id] = node.value.value
    return out


def _wired_risk_constants():
    """The risk REASON_* constants actually REFERENCED beyond their own definition — the ones that
    can really be returned by `check()` and so really reach the archive.

    Being class attributes, references are ATTRIBUTE access (`self.REASON_PASS`,
    `RiskEngine.REASON_PASS`), not bare names."""
    consts = _risk_reason_constants()
    tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in consts:
            used.add(node.attr)
        elif isinstance(node, ast.Name) and node.id in consts and not isinstance(
                getattr(node, "ctx", None), ast.Store):
            used.add(node.id)
    return {name: consts[name] for name in used}


def _dead_risk_constants():
    """Defined but never referenced — cannot reach the archive today."""
    consts = _risk_reason_constants()
    wired = _wired_risk_constants()
    return {n: c for n, c in consts.items() if n not in wired}


def _signal_reason_codes():
    """The literal values `signal_reason` can take (live.py:223), read from the ternary."""
    tree = ast.parse(LIVE.read_text(encoding="utf-8"))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id == "signal_reason" and isinstance(node.value, ast.IfExp):
            for branch in (node.value.body, node.value.orelse):
                if isinstance(branch, ast.Constant) and isinstance(branch.value, str):
                    out.add(branch.value)
    return out


def _kill_switch_default_code():
    """`KillSwitchEngagedError.__init__(reason_code: str = "KILL_SWITCH_ENGAGED")` — the value
    `live.py:307` archives when no explicit code is supplied."""
    tree = ast.parse(INTERFACE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for d in node.args.defaults:
                if isinstance(d, ast.Constant) and isinstance(d.value, str) and d.value.isupper():
                    return {d.value}
    return set()


def archivable_codes():
    """Every reason code that CAN appear in a corpus-archived decision record — literal call sites
    plus the three resolved indirection sources."""
    return (_literal_archived_codes()
            | set(_wired_risk_constants().values())
            | _signal_reason_codes()
            | _kill_switch_default_code())


# ── the guards ─────────────────────────────────────────────────────────────────────────────
def test_every_archivable_reason_code_is_declared():
    """(a) for the ARCHIVE PATH: nothing can reach an archived decision record undeclared.

    This covers the variable-indirection sites the literal-form scan documents as out of scope, so a
    future `reason_code=<var>` carrying an ungoverned code fails CI rather than shipping into a
    permanent archive."""
    undeclared = sorted(archivable_codes() - _declared())
    assert undeclared == [], (
        "reason code(s) can reach a CORPUS-ARCHIVED decision record but are NOT DECLARED in "
        f"VALID_REASON_CODES: {undeclared}\n"
        "An undeclared code in the archive is permanent — every later analysis inherits a code with "
        "no definition. Declare it, or stop emitting it."
    )


def test_archivable_codes_are_prefix_free():
    """(c) for the ARCHIVE PATH: no archived code is a prefix of another, so a consumer that matches
    on prefixes cannot conflate two causes."""
    codes = sorted(archivable_codes())
    collisions = [(a, b) for a in codes for b in codes if a != b and b.startswith(a)]
    assert collisions == [], f"prefix collisions inside the archivable set: {collisions}"


def test_every_wired_risk_reason_constant_is_declared():
    """The risk engine's REASON_* constants are the value set of `check()`'s reason, which
    `live.py:248` passes straight into an archived decision record. Every WIRED one must be declared.

    Constants that are defined but never referenced cannot reach the archive today; they are reported
    by `test_dead_risk_reason_constants_are_known` rather than failed here, so this guard fires at the
    moment one is wired — which is the moment it starts mattering."""
    wired = _wired_risk_constants()
    undeclared = sorted(code for code in wired.values() if code not in _declared())
    assert undeclared == [], (
        f"risk REASON_* constant(s) are WIRED into check()'s return but NOT DECLARED: {undeclared}\n"
        "live.py:248 passes check()'s reason straight to log_decision(reason_code=...), so this "
        "would reach a corpus-archived record undeclared, via the indirection the literal-form scan "
        "cannot see."
    )


# WO-037 §3 finding, recorded as an EXAMINED set rather than silently tolerated. Each entry is a
# reason-code constant that exists in the risk engine but is referenced nowhere, so it cannot reach
# the archive. It is NOT declared, and it does not need to be while it stays dead — but it is one
# line of wiring away from an undeclared archived code, which is why it is pinned here by name.
KNOWN_DEAD_RISK_CONSTANTS = {
    "REASON_VETO_INSUFFICIENT_BALANCE": (
        "engine.py:42. Defined, never referenced — appears exactly once in the repo. Not declared "
        "in VALID_REASON_CODES and not producible, so it cannot corrupt an archive today. WO-037 §3 "
        "reported it; the lead assigns its bucket (declare it, or delete it). Until then this entry "
        "keeps it visible and test_every_wired_risk_reason_constant_is_declared fails the moment it "
        "is wired."
    ),
}


def test_dead_risk_reason_constants_are_known():
    """No UNEXAMINED dead reason-code constant. A new one appearing is a finding — it is either a
    code someone forgot to wire, or one they forgot to delete, and both are worth seeing."""
    dead = set(_dead_risk_constants())
    unexamined = sorted(dead - set(KNOWN_DEAD_RISK_CONSTANTS))
    assert unexamined == [], (
        f"UNEXAMINED dead risk reason-code constant(s): {unexamined}\n"
        "Wire it, delete it, or add a KNOWN_DEAD_RISK_CONSTANTS entry naming why it exists."
    )
    stale = sorted(n for n in KNOWN_DEAD_RISK_CONSTANTS if n not in dead)
    assert stale == [], (
        f"stale KNOWN_DEAD_RISK_CONSTANTS entries (now wired or deleted): {stale}"
    )


def test_the_indirection_resolvers_actually_resolve():
    """Rule 0.1d — prove the resolvers return real values rather than trusting an empty set.

    An archive guard whose resolvers silently returned nothing would pass on any tree, which is the
    failure mode that makes a green guard worthless."""
    assert _signal_reason_codes() == {"LONG_SIGNAL", "SHORT_SIGNAL"}, _signal_reason_codes()
    assert _kill_switch_default_code() == {"KILL_SWITCH_ENGAGED"}, _kill_switch_default_code()
    wired = _wired_risk_constants()
    assert "REASON_PASS" in wired and wired["REASON_PASS"] == "RISK_PASS", wired
    assert len(wired) >= 5, f"expected the wired risk reason set, got {wired}"
    assert _literal_archived_codes(), "no literal archived codes found — the scan is broken"
    # And the archivable set is a real superset of the literal-only view: the indirection matters.
    assert archivable_codes() - _literal_archived_codes(), (
        "resolving the indirection added nothing — either the resolvers broke or live.py changed"
    )
