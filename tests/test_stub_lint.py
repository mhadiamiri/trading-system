"""
WO-014c-3 §1 — STUB-LINT: make rule 0.1g ("a stub or unimplemented production path MUST FAIL
LOUDLY") MECHANICAL.

A production function whose body is just `pass`, a bare `return`, `...`, or ONLY a docstring
(WO-014c-3 addendum E) is a no-op — the exact shape that let `_request_snapshot(): pass` zero
48 of 60 minutes and `_reconnect(): pass`
make the five-failure recovery never work. Both are now implemented; this lint is what stops the
third instance. It scans every production module under src/ and FAILS on any stub-bodied function
that is not a LEGITIMATE, EXAMINED exception — because "an unexamined exception is how 0.1g gets
its own 0.1d" (a false guarantee), every allowance names why.

This is a pytest guard (AST-based), NOT an import-linter contract, so it does not change the
import-linter contract count (EXPECTED_CONTRACT_COUNT stays 6).
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"


def _is_docstring(stmt) -> bool:
    return (isinstance(stmt, ast.Expr) and isinstance(getattr(stmt, "value", None), ast.Constant)
            and isinstance(stmt.value.value, str))


def _stub_kind(node) -> str | None:
    """Return 'pass' | 'bare-return' | 'ellipsis' | 'docstring-only' if the function body is a
    no-op, else None. WO-014c-3 addendum E: a body that is ONLY a docstring is also a silent
    no-op that returns None — 0.1g's defect definition exactly (a production path that silently
    succeeds at doing nothing), and the shape a stub takes when someone leaves an explanatory
    comment where the implementation should be."""
    body = node.body
    had_docstring = bool(body) and _is_docstring(body[0])
    if had_docstring:
        body = body[1:]
    if len(body) == 0:
        # Nothing remained after the docstring: the body was ONLY a docstring.
        return "docstring-only" if had_docstring else None
    if len(body) != 1:
        return None
    s = body[0]
    if isinstance(s, ast.Pass):
        return "pass"
    if isinstance(s, ast.Return) and s.value is None:
        return "bare-return"
    if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis:
        return "ellipsis"
    return None


def _has_abstractmethod(node) -> bool:
    for d in node.decorator_list:
        name = ast.unparse(d)
        if name.endswith("abstractmethod"):
            return True
    return False


def find_stub_functions(root: Path):
    """Every stub-bodied function under `root`. Each: (relpath, lineno, qualname, kind,
    is_abstractmethod)."""
    out = []
    for p in sorted(root.rglob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = _stub_kind(node)
                if kind:
                    rel = p.relative_to(root).as_posix()
                    out.append((rel, node.lineno, node.name, kind, _has_abstractmethod(node)))
    return out


# ── EXAMINED EXCEPTIONS ──────────────────────────────────────────────────────────
# RULE (justified once, applies to all @abstractmethod stubs): an @abstractmethod body is
# NEVER executed. abc.ABCMeta refuses to instantiate any subclass that has not overridden it
# (TypeError at construction), so a `pass`/`...` body is the INTERFACE DECLARATION — the
# concrete adapter/engine/strategy supplies the real body — not an unimplemented production
# path. This is the exact legitimate case 0.1g's ruling names ("protocol stubs on ABCs").
#
# EXPLICIT allowlist for any NON-abstractmethod stub that is nonetheless legitimate. Every entry
# is (relpath, function_name) -> justification. EMPTY today: the tree has no such case. A future
# entry must NAME WHY; the honesty test below forbids stale entries.
EXAMINED_STUB_ALLOWLIST: dict[tuple[str, str], str] = {}


def _unexamined_stubs():
    return [
        h for h in find_stub_functions(SRC)
        if not h[4] and (h[0], h[2]) not in EXAMINED_STUB_ALLOWLIST
    ]


def test_no_unexamined_stub_bodied_production_functions():
    """0.1g mechanical: no stub-bodied production function outside the examined exceptions."""
    unexamined = _unexamined_stubs()
    assert unexamined == [], (
        "UNEXAMINED STUB-BODIED production function(s) — 0.1g requires a stub to FAIL LOUDLY, "
        "not sit silently as a no-op (the _request_snapshot/_reconnet defect class):\n"
        + "\n".join(f"  {r}:{ln}  {name}()  body={kind}" for r, ln, name, kind, _abs in unexamined)
        + "\nImplement it, or add an EXAMINED_STUB_ALLOWLIST entry that NAMES WHY it is a no-op."
    )


def test_allowlist_is_honest():
    """No stale allowlist entry: every explicit exception must still exist AND still be a stub
    (else it is silently suppressing nothing, or hiding a now-implemented function)."""
    current = {(r, name) for r, _ln, name, _k, _abs in find_stub_functions(SRC)}
    stale = [k for k in EXAMINED_STUB_ALLOWLIST if k not in current]
    assert stale == [], f"stale EXAMINED_STUB_ALLOWLIST entries (no longer stub/exist): {stale}"


def test_abstractmethod_stubs_are_the_only_examined_class():
    """Report/pin the current legitimate set: all stub bodies in the tree are @abstractmethod
    interface declarations. If this changes, the diff forces a fresh examination."""
    stubs = find_stub_functions(SRC)
    non_abstract = [(r, ln, name, kind) for r, ln, name, kind, is_abs in stubs if not is_abs]
    assert non_abstract == [], (
        f"a NON-abstractmethod stub appeared — examine it (do not wave it through): {non_abstract}"
    )
    # And there really are abstractmethod interface stubs (the check is exercising real inputs).
    assert any(is_abs for *_x, is_abs in stubs), "expected @abstractmethod interface stubs to exist"


def test_detector_actually_fires_on_a_real_stub():
    """Rule 0.1d: prove the scanner flags a genuine stub rather than trusting an empty result."""
    src = ("def f():\n    pass\n\ndef g():\n    return 1\n\n@abstractmethod\ndef h():\n    ...\n\n"
           "def k():\n    \"\"\"TODO: write the ledger.\"\"\"\n")
    tree = ast.parse(src)
    kinds = {n.name: _stub_kind(n) for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert kinds["f"] == "pass"              # a real no-op is detected
    assert kinds["g"] is None                # a function that does work is NOT flagged
    assert kinds["h"] == "ellipsis"          # ... body detected (allowed via abstractmethod)
    assert kinds["k"] == "docstring-only"    # addendum E: a docstring-only body is a stub
