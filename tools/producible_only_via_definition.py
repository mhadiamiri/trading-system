#!/usr/bin/env python3
"""WO-018 follow-up item A (REPORT ONLY): count declared codes that are NOT
reachable-as-emitted by a literal — i.e. the current `declared => producible` scan
passes them only because their string appears in production source at a NON-EMIT site
(a `NAME = "CODE"` definition, a comment, or a docstring), never at a genuine emit site.

This is exactly the workload the successor WO's TIGHTENED producibility scan inherits
(the lead's ruling: producible == REACHABLE-AS-EMITTED — trace to a RETURN / EMIT / RAISE
site, not to a definition). Read-only analysis; changes no behaviour.

Method — grounded in the scan's OWN instrument, no new heuristic for "emit":
  A code has a genuine EMIT-SITE literal iff it is matched by the same three regexes the
  vocabulary scan uses to build its EMITTED sets:
      _RC_COLON  "CODE:            (raise/f-string colon form)
      _RC_KWARG  reason_code="CODE"
      _ET_KWARG  event_type="CODE"
  A declared code with ZERO such matches in src/ (excluding decision.py) is 'producible
  only via a non-emit occurrence'. For each, we then show WHERE its literal actually sits
  (definition / comment / docstring-or-prose) so the finding is concrete.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DECLARATION_SITE = "decision.py"

sys.path.insert(0, str(SRC))
from trading.logkit.decision import VALID_REASON_CODES, VALID_EVENT_TYPES  # noqa: E402

# The scan's own emit-site matchers (verbatim from tests/test_reason_code_vocabulary.py).
_RC_COLON = re.compile(r'"([A-Z][A-Z0-9_]{3,}):')
_RC_KWARG = re.compile(r'reason_code(?:\s*:\s*\w+)?\s*=\s*"([A-Z_][A-Z0-9_]{3,})"')
_ET_KWARG = re.compile(r'event_type\s*=\s*"([A-Za-z_][A-Za-z0-9_]{2,})"')

_DEFN = re.compile(r'^[A-Za-z_]\w*(\s*:\s*[^=]+?)?\s*=\s*(["\'])(.+?)\2\s*(#.*)?$')


def declared(ns):
    out = []
    for group in ns.values():
        out.extend(group)
    return sorted(set(out))


def src_files():
    return [p for p in sorted(SRC.rglob("*.py")) if p.name != DECLARATION_SITE]


def emit_site_codes():
    """Codes with a genuine emit-site literal (the scan's EMITTED notion, literal-only)."""
    rc, et = set(), set()
    for p in src_files():
        text = p.read_text(encoding="utf-8")
        rc.update(_RC_COLON.findall(text))
        rc.update(_RC_KWARG.findall(text))
        et.update(_ET_KWARG.findall(text))
    return rc, et


def classify_line(line, code):
    """Precise per-occurrence kind. Emit-site kinds use the scan's OWN regexes so the
    label matches exactly what the completeness scan can and cannot see."""
    if code in _RC_COLON.findall(line):
        return "EMIT-rc-colon"
    if code in _RC_KWARG.findall(line):
        return "EMIT-rc-kwarg"
    if code in _ET_KWARG.findall(line):
        return "EMIT-et-kwarg"   # emit in the OTHER namespace when listed under reason_code
    s = line.strip()
    m = _DEFN.match(s)
    if m and m.group(3) == code:
        return "DEFN"            # NAME = "CODE" module constant or enum member
    hash_i = line.find("#")
    code_i = line.find(code)
    if hash_i != -1 and hash_i < code_i:
        return "COMMENT"
    return "PROSE/VAR"           # docstring, list-membership, or variable-assignment literal


def occurrences(code):
    """Where the literal "code"/'code' appears (excl decision.py), classified."""
    out = []
    lit1, lit2 = f'"{code}"', f"'{code}'"
    litc1, litc2 = f'"{code}:', f"'{code}:"
    for p in src_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not (lit1 in line or lit2 in line or litc1 in line or litc2 in line):
                continue
            out.append((classify_line(line, code), f"{p.relative_to(ROOT).as_posix()}:{i}", line.strip()))
    return out


rc_emit, et_emit = emit_site_codes()

print("===== reason_code: declared but NO emit-site literal =====")
rc_declared = declared(VALID_REASON_CODES)
rc_gap = [c for c in rc_declared if c not in rc_emit]
for c in rc_gap:
    occ = occurrences(c)
    kinds = ",".join(sorted({k for k, _, _ in occ})) or "NONE-OUTSIDE-decision.py"
    print(f"  {c}   [{kinds}]")
    for k, where, txt in occ:
        print(f"      {k:9} {where}   {txt}")

print("\n===== event_type: declared but NO emit-site (_ET_KWARG) literal =====")
et_declared = declared(VALID_EVENT_TYPES)
et_gap = [c for c in et_declared if c not in et_emit]
for c in et_gap:
    occ = occurrences(c)
    kinds = ",".join(sorted({k for k, _, _ in occ})) or "NONE-OUTSIDE-decision.py"
    note = "  (emitted via RiskDecision.value -- enum-drift guard covers it)" if c in {"PASS", "CLAMP", "VETO"} else ""
    print(f"  {c}   [{kinds}]{note}")
    for k, where, txt in occ:
        print(f"      {k:9} {where}   {txt}")

print("\n===== SUMMARY =====")
print(f"reason_code declared: {len(rc_declared)}; with NO emit-site literal: {len(rc_gap)}")
print(f"    {rc_gap}")
print(f"event_type declared: {len(et_declared)}; with NO emit-site literal: {len(et_gap)}")
print(f"    {et_gap}")
print(f"\nTightening workload (declared codes not reachable-as-emitted by literal): "
      f"{len(set(rc_gap) | set(et_gap))} distinct strings "
      f"({len(rc_gap)} reason_code + {len(et_gap)} event_type)")
