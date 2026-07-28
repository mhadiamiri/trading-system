"""WO-037 §3 — ENUMERATE AND CLASSIFY THE REASON-CODE VOCABULARY AT HEAD (read-only).

The corpus ARCHIVES decision records carrying reason codes. If the vocabulary is defective at capture
— emitted-but-undeclared, declared-but-unproducible, aliased, or a category leak that masks one of
those — the archive preserves the defect permanently.

This instrument MEASURES, it does not assume. It reuses the OPERATED scanners from
`tests/test_reason_code_vocabulary.py` rather than re-implementing them, so the enumeration and the
standing guard cannot drift apart (a second scanner would be a second source of truth).

The classification this WO adds on top is (d) CATEGORY — for each declared code, HOW is it emitted?

    ARCHIVABLE   reaches a decision record: `log_decision(reason_code=...)` /
                 `log_feed_event(reason_code=...)`. These are the codes a corpus analysis will see.
    RAISED       carried in an exception message (`raise X("CODE: ...")`). Never a decision record's
                 reason_code field by itself.
    LOGGED       carried in a logger line (`logger.error(f"CODE: ...")`). Same.

The archive-readiness question is about the ARCHIVABLE set: is it complete and consistent? A code
that can only ever be RAISED or LOGGED cannot appear in an archived decision record, so it cannot
corrupt the archive — but it sits in the same declared registry and the same scan, which is exactly
how it could MASK a real gap in the archivable set. Hence: catalog, then verify the properties hold
for the archivable subset specifically.

    python tools/wo037_vocabulary_audit.py

Writes to .artifacts/ (WO-032 §4.1).
"""
import os
import re
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)

ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo037_vocabulary_audit")

# The OPERATED scanners, imported — not re-implemented.
from tests.test_reason_code_vocabulary import (                              # noqa: E402
    _declared_reason_codes, _declared_event_types,
    _emitted_reason_codes, _emitted_event_types,
    _production_source_text, _is_producible, _prefix_collisions, _src_files,
)

# How a code reaches a DECISION RECORD (what the corpus archives) vs merely an exception or a log line.
ARCHIVABLE = re.compile(r'(?:log_decision|log_feed_event)\s*\([^)]*reason_code\s*=\s*"([A-Z_][A-Z0-9_]{3,})"',
                        re.S)
RAISED = re.compile(r'raise\s+\w+\s*\(\s*\n?\s*[fr]?"([A-Z][A-Z0-9_]{3,}):')
LOGGED = re.compile(r'(?:logger\.\w+|_log_error|_log_\w+)\s*\(\s*\n?\s*[fr]?"([A-Z][A-Z0-9_]{3,}):')


def emission_sites(code):
    """Every production site mentioning this code, with the file:line and the raw line."""
    hits = []
    for p in _src_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if code in line:
                hits.append((p.name, i, line.strip()))
    return hits


def main():
    text = _production_source_text()
    declared_rc = set(_declared_reason_codes())
    declared_et = set(_declared_event_types())
    emitted_rc = set(_emitted_reason_codes())
    emitted_et = set(_emitted_event_types())

    archivable = set(ARCHIVABLE.findall(text))
    raised = set(RAISED.findall(text))
    logged = set(LOGGED.findall(text))

    out = ["WO-037 §3 — REASON-CODE VOCABULARY, ENUMERATED AND CLASSIFIED AT HEAD",
           "Scanners reused from tests/test_reason_code_vocabulary.py (no second source of truth).",
           ""]

    # ── 3.1 declared ────────────────────────────────────────────────────────
    out += ["=" * 78, "3.1 THE DECLARED SET", "=" * 78,
            f"  reason codes : {len(declared_rc)}",
            f"  event types  : {len(declared_et)}", ""]
    for c in sorted(declared_rc):
        out.append(f"    RC  {c}")
    out.append("")
    for c in sorted(declared_et):
        out.append(f"    ET  {c}")
    out.append("")

    # ── 3.2 emitted ─────────────────────────────────────────────────────────
    out += ["=" * 78, "3.2 THE EMITTED SET (literal forms the guard scans)", "=" * 78,
            f"  reason codes emitted : {len(emitted_rc)}",
            f"  event types emitted  : {len(emitted_et)}", ""]
    for c in sorted(emitted_rc):
        sites = emission_sites(c)
        first = f"{sites[0][0]}:{sites[0][1]}" if sites else "(no site)"
        out.append(f"    RC  {c:<48} {len(sites):>2} site(s), first {first}")
    out.append("")

    # ── 3.3 the four properties, MEASURED ───────────────────────────────────
    a_viol = sorted(emitted_rc - declared_rc)
    a_viol_et = sorted(emitted_et - declared_et)
    b_viol = sorted(c for c in declared_rc if not _is_producible(c, text))
    b_viol_et = sorted(c for c in declared_et if not _is_producible(c, text))
    c_viol = _prefix_collisions(sorted(declared_rc | declared_et))

    out += ["=" * 78, "3.3 THE FOUR CONSISTENCY PROPERTIES — MEASURED", "=" * 78,
            f"  (a) EMITTED => DECLARED   reason codes : "
            f"{'CLEAN' if not a_viol else 'VIOLATION ' + str(a_viol)}",
            f"  (a) EMITTED => DECLARED   event types  : "
            f"{'CLEAN' if not a_viol_et else 'VIOLATION ' + str(a_viol_et)}",
            f"  (b) DECLARED => PRODUCIBLE reason codes: "
            f"{'CLEAN' if not b_viol else 'VIOLATION ' + str(b_viol)}",
            f"  (b) DECLARED => PRODUCIBLE event types : "
            f"{'CLEAN' if not b_viol_et else 'VIOLATION ' + str(b_viol_et)}",
            f"  (c) PREFIX-FREE across the union       : "
            f"{'CLEAN' if not c_viol else 'VIOLATION ' + str(c_viol)}",
            ""]

    # ── 3.3(d) category ─────────────────────────────────────────────────────
    out += ["=" * 78,
            "3.3(d) CATEGORY — how each DECLARED reason code reaches the world",
            "=" * 78,
            "  ARCHIVABLE = reaches a decision record (log_decision/log_feed_event reason_code=).",
            "               ONLY these can appear in a corpus-archived decision log.",
            "  RAISED     = carried in an exception message only.",
            "  LOGGED     = carried in a logger line only.",
            "  (a code may be more than one; ARCHIVABLE is what decides archive-relevance)",
            ""]
    cat = {}
    for c in sorted(declared_rc):
        tags = []
        if c in archivable:
            tags.append("ARCHIVABLE")
        if c in raised:
            tags.append("RAISED")
        if c in logged:
            tags.append("LOGGED")
        if not tags:
            tags.append("INDIRECT-ONLY")     # emitted via a variable, or via event_type only
        cat[c] = tags
        out.append(f"    {'/'.join(tags):<28} {c}")
    out.append("")

    arch_set = {c for c, t in cat.items() if "ARCHIVABLE" in t}
    nonarch = {c for c, t in cat.items() if "ARCHIVABLE" not in t}

    # ── 3.4 archive readiness ───────────────────────────────────────────────
    arch_emitted_undeclared = sorted(c for c in archivable if c not in declared_rc)
    arch_prefix = _prefix_collisions(sorted(arch_set))
    ready = not arch_emitted_undeclared and not arch_prefix and not a_viol and not a_viol_et

    out += ["=" * 78, "3.4 ARCHIVE-READINESS", "=" * 78,
            f"  ARCHIVABLE codes (can appear in an archived decision record) : {len(arch_set)}",
            f"  NON-archivable declared codes (raise/log/indirect only)      : {len(nonarch)}",
            "",
            f"  archivable EMITTED but UNDECLARED : "
            f"{arch_emitted_undeclared or 'none'}",
            f"  archivable prefix collisions      : {arch_prefix or 'none'}",
            "",
            f"  VERDICT: {'ARCHIVE-READY (YES)' if ready else 'NOT ARCHIVE-READY (NO)'}",
            ""]
    out += ["  The archivable set:"]
    for c in sorted(arch_set):
        out.append(f"      {c}")
    out += ["", "  Declared but NOT archivable (cannot corrupt an archived decision record):"]
    for c in sorted(nonarch):
        out.append(f"      {'/'.join(cat[c]):<20} {c}")

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
