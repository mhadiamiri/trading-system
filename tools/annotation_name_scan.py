#!/usr/bin/env python3
"""WO-021 §1 — the COMPLETE annotation-name denominator (static, complements 3.11 collection).

WHY THIS EXISTS: the 3.11 `pytest --collect-only` run is the WO's named instrument, but it has a
hard limit — a class/module body aborts at its FIRST unimported annotation name, so every later
eager-evaluated annotation in that same class/module is MASKED (kraken_v2_book.py:2300 hides 2718),
and modules that no test imports are never evaluated at all. This static scan reads EVERY src module
and finds EVERY name used in an eager-evaluated annotation position that is not imported/defined at
module scope and is not a builtin — i.e. every name that WOULD raise NameError under eager (3.11)
annotation evaluation, whether or not collection happened to reach it.

EAGER-EVALUATED positions checked (evaluated at def/class/module load, so 3.11 raises there):
  - function argument + return annotations (any nesting) — evaluated when the `def` executes;
  - module-level and class-level variable annotations (AnnAssign).
NOT checked (not evaluated at runtime, so never a NameError):
  - function-LOCAL variable annotations (`x: Foo` inside a body) — Python never evaluates these;
  - string / forward-ref annotations (`-> "MarketState"`) — a str literal, not a name lookup.
A module with `from __future__ import annotations` defers ALL annotations -> reported, never flagged.

This is a static approximation: it treats any name bound anywhere at module scope as "available"
(so it will not flag a genuine forward-order edge case), and it cannot resolve `from x import *`
(such a module is reported as UNSCANNABLE, its declared limit). Its job is the DENOMINATOR, checked
against the 3.11 collection run, not to replace it.
"""
import ast
import builtins
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
BUILTINS = set(dir(builtins)) | {"None", "True", "False", "__debug__"}


def module_bound_names(tree):
    """Names available at module scope: imports, top-level defs/classes, top-level assignments."""
    bound = set()
    star = False
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                bound.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name == "*":
                    star = True
                else:
                    bound.add(a.asname or a.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in ast.walk(node):
                if isinstance(t, ast.Name):
                    bound.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
    # names bound anywhere at class scope too (class-level annotations see them)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bound.add(node.name)
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    bound.add(b.name)
                elif isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name):
                    bound.add(b.target.id)
                elif isinstance(b, ast.Assign):
                    for t in ast.walk(b):
                        if isinstance(t, ast.Name):
                            bound.add(t.id)
    return bound, star


def eager_annotations(tree):
    """Yield (annotation_node) for every eager-evaluated annotation position."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            for arg in [*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg]:
                if arg and arg.annotation is not None:
                    yield arg.annotation
            if node.returns is not None:
                yield node.returns
    # module- and class-level AnnAssign (NOT function-local)
    def anns_in(body):
        for n in body:
            if isinstance(n, ast.AnnAssign) and n.annotation is not None:
                yield n.annotation
    yield from anns_in(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield from anns_in(node.body)


def names_in_annotation(ann):
    """Every Name id referenced in an annotation (skips string forward-refs)."""
    out = []
    for n in ast.walk(ann):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.append((n.id, n.lineno))
    return out


findings = []       # (file, line, name)
future_files = []   # files with `from __future__ import annotations`
unscannable = []    # files with `from x import *`

for path in sorted(SRC.rglob("*.py")):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    rel = path.relative_to(ROOT).as_posix()
    if any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
           and any(a.name == "annotations" for a in n.names) for n in tree.body):
        future_files.append(rel)
        continue
    bound, star = module_bound_names(tree)
    if star:
        unscannable.append(rel)
    seen = set()
    for ann in eager_annotations(tree):
        for name, line in names_in_annotation(ann):
            if name in bound or name in BUILTINS:
                continue
            key = (rel, line, name)
            if key not in seen:
                seen.add(key)
                findings.append(key)

print("WO-021 §1 — STATIC ANNOTATION-NAME DENOMINATOR (complements 3.11 collection)")
print("=" * 78)
print(f"src modules scanned: {sum(1 for _ in SRC.rglob('*.py'))}")
print(f"modules with `from __future__ import annotations` (deferred, not flagged): "
      f"{future_files or 'none'}")
print(f"modules with `from x import *` (UNSCANNABLE — declared limit): {unscannable or 'none'}")
print("")
print(f"NAMES USED IN AN EAGER ANNOTATION BUT NOT IMPORTED/DEFINED (would NameError on 3.11): "
      f"{len(findings)}")
for rel, line, name in findings:
    print(f"  {rel}:{line}   {name}")
print("")
if findings:
    from collections import Counter
    print("by name:")
    for name, c in Counter(n for _, _, n in findings).most_common():
        print(f"  {name}: {c}")
sys.exit(1 if findings else 0)
