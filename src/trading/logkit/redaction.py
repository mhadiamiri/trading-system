"""
Capture redaction (WO-011 section 6.2).

Session/connection identifiers on a public venue feed are not credentials and
grant nothing, but captures are redacted BY DEFAULT: the next venue's session
identifier may not be inert, and a redaction applied by hand in one capture script
is a redaction forgotten in the next. This module makes redaction MECHANICAL — one
pattern set that any capture path applies, and a scan the secret-scan step runs.

- redact(text): return capture text with every known identifier value replaced.
- scan(text):   return every UNREDACTED identifier still present (empty == clean).

Adding a new identifier type is one row in REDACTION_PATTERNS; redact() and scan()
both pick it up, so the pattern set is the single source of truth.
"""

import re
from typing import List, Tuple

REDACTED = '"<REDACTED>"'

# (name, pattern). Each pattern captures `"<key>": <value>` in captured JSON text,
# for numeric or quoted identifier values. Group 1 is the key-and-colon prefix;
# group 2 is the value that gets replaced.
_VALUE = r'("?[^",}\s]+"?)'
REDACTION_PATTERNS: List[Tuple[str, "re.Pattern"]] = [
    ("connection_id", re.compile(r'("connection_id"\s*:\s*)' + _VALUE)),
    ("session_id", re.compile(r'("session_id"\s*:\s*)' + _VALUE)),
    ("req_id", re.compile(r'("req_id"\s*:\s*)' + _VALUE)),
]


def redact(text: str) -> str:
    """Replace every known session/connection identifier value with <REDACTED>."""
    for _name, pat in REDACTION_PATTERNS:
        text = pat.sub(lambda m: m.group(1) + REDACTED, text)
    return text


def scan(text: str) -> List[Tuple[str, str]]:
    """
    Return [(identifier_name, matched_text), ...] for every UNREDACTED identifier.

    A match whose value is already the <REDACTED> placeholder is not reported, so
    scan(redact(text)) is empty. A non-empty result means an identifier would ship
    in the clear — the secret-scan step FAILS on that.
    """
    found: List[Tuple[str, str]] = []
    for name, pat in REDACTION_PATTERNS:
        for m in pat.finditer(text):
            if "<REDACTED>" not in m.group(0):
                found.append((name, m.group(0)))
    return found
