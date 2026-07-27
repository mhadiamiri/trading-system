"""
WO-032 §4.2 — THE EVIDENCE-WRITE PROHIBITION, GENERALIZED TO EVERY PRODUCER.

WO-026 §2 ruled the doctrine: *an instrument streams to an ignored run-scoped path; evidence is a
DELIBERATE snapshot.* Its enforcement was `conftest.py::_assert_ledger_dir_outside_evidence`, which
validates ONE hardcoded path — the gate ledger's — inside `conftest.py`. It cannot see a `tools/`
script.

So three WOs later `tools/wo029_reverify_partition.py` was authored writing straight into
`evidence/WO-029/partition_reverified_at_head.txt`, a COMMITTED file. Merely RUNNING it silently
overwrote committed evidence — rewriting WO-029's `VERDICT: PASS` record into a `FAIL` record. No
guard fired. It was caught by a human reading a changed-files list: the exact detection mode, and the
exact defect, WO-026 existed to eliminate (WO-031 Finding 4).

This guard is the missing half: it scans EVERY tracked `tools/*.py` and fails on any WRITE whose path
resolves inside `evidence/`. A doctrine enforced by a guard scoped to one producer is enforced nowhere
the guard cannot reach.

**READS ARE NOT THE BANNED PATTERN.** `wo029_reverify_partition.py` legitimately READS the committed
partition table, and `replay_checksum_capture.py` legitimately READS a committed capture dump. The
doctrine is about a tool *authoring* evidence as a side effect, so the scan is write-directed: a path
expression naming `evidence/` is flagged only where it is the target of a write.

AST-based, like `test_stub_lint.py`. Comments never appear in an AST, and docstrings are skipped, so
prose mentioning `evidence/` cannot trip it.
"""

import ast
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"

# ── EXAMINED EXCEPTIONS ──────────────────────────────────────────────────────────
# The doctrine has exactly ONE legitimate writer: the DELIBERATE snapshot step. WO-026 built it as
# `tools/snapshot_gate_ledger.py` — writing into evidence/ is its entire purpose, it is never invoked
# by a test session, and it carries its own guard refusing a destination NOT under evidence/. Every
# entry must NAME WHY; `test_evidence_write_allowlist_is_honest` forbids a stale one.
DELIBERATE_SNAPSHOT_ALLOWLIST: dict[str, str] = {
    "snapshot_gate_ledger.py":
        "WO-026 §2 — THE deliberate snapshot tool. Writing into evidence/ is its purpose: it copies "
        "the run-scoped .artifacts/ ledger into evidence/<WO>/ as an authored act. No test session "
        "imports or runs it.",
}

_WRITE_MODES = ("w", "a", "x", "+")
_WRITE_METHODS = ("write_text", "write_bytes")
_COPY_FUNCS = ("copy", "copy2", "copyfile", "move")


def _tracked_tools_scripts() -> list[Path]:
    """Every TRACKED tools/*.py. Tracked, because the prohibition is about what the repo ships —
    an untracked local scratch script is nobody's committed evidence problem."""
    out = subprocess.run(["git", "ls-files", "tools"], cwd=REPO, capture_output=True,
                         text=True, check=True).stdout.split()
    return [REPO / p for p in out if p.endswith(".py")]


def _is_docstring(stmt) -> bool:
    return (isinstance(stmt, ast.Expr) and isinstance(getattr(stmt, "value", None), ast.Constant)
            and isinstance(stmt.value.value, str))


def _names_evidence(node) -> bool:
    """True if this expression subtree contains a string literal naming the evidence/ directory —
    i.e. it is building a path into evidence/. Docstrings are excluded by the caller."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            v = sub.value.replace("\\", "/")
            if v == "evidence" or v.startswith("evidence/") or "/evidence/" in v:
                return True
    return False


def _evidence_tainted_names(tree) -> set[str]:
    """Names assigned a path expression that reaches into evidence/ (`OUT = os.path.join(REPO,
    "evidence", ...)`), so a later `open(OUT, "w")` is recognised as an evidence write.

    Taint PROPAGATES through intermediates and is iterated to a fixpoint, because the real shape is
    routinely two-step — `snapshot_gate_ledger.py` does `dest_dir = REPO / "evidence" / wo` and then
    `dest = dest_dir / name`, and only `dest` is ever written. A single non-propagating pass sees the
    literal on `dest_dir`, misses `dest`, and clears the file. (Found by this module's own honesty
    test, which reported the one known deliberate writer as exempt-but-not-writing.)"""
    assigns = [(n.targets if isinstance(n, ast.Assign) else [n.target], n.value)
               for n in ast.walk(tree)
               if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None]
    tainted: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for targets, value in assigns:
            reaches = _names_evidence(value) or any(
                isinstance(sub, ast.Name) and sub.id in tainted for sub in ast.walk(value))
            if not reaches:
                continue
            for t in targets:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Name) and sub.id not in tainted:
                        # Keep the assignment source, so the failure can name the PATH and not just
                        # the variable — "-> OUT" sends the reader hunting; the resolved expression
                        # is the thing a reviewer actually needs to see.
                        tainted[sub.id] = ast.unparse(value)
                        changed = True
    return tainted


def _resolved_evidence_path(node, tainted: dict[str, str]) -> str | None:
    """The evidence path this write-target resolves to, or None if it does not reach evidence/.
    Either the target names evidence/ inline, or it reaches it through a tainted name (including
    wrappers like `os.path.dirname(OUT)`); in the latter case return that name's assignment."""
    if node is None:
        return None
    if _names_evidence(node):
        return ast.unparse(node)
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in tainted:
            return f"{sub.id} = {tainted[sub.id]}"
    return None


def _write_targets(tree, tainted: dict[str, str]):
    """Yield (lineno, description, target_node) for every write-shaped call in the module."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")

        if fname == "open":
            mode = ""
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value)
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = str(kw.value.value)
            if any(m in mode for m in _WRITE_MODES) and node.args:
                yield node.lineno, f'open(..., "{mode}")', node.args[0]

        elif fname in _WRITE_METHODS and isinstance(fn, ast.Attribute):
            yield node.lineno, f"Path.{fname}()", fn.value

        elif fname in _COPY_FUNCS and len(node.args) > 1:
            yield node.lineno, f"shutil.{fname}() destination", node.args[1]

        elif fname in ("makedirs", "mkdir") and node.args:
            yield node.lineno, f"{fname}()", node.args[0]


def evidence_writes(path: Path):
    """Every write in `path` whose target resolves inside evidence/.
    Each: (lineno, what, target_expr, resolved_evidence_path)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    # Strip module/class/function docstrings so prose about evidence/ is never scanned.
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and _is_docstring(body[0]):
            node.body = body[1:]
    tainted = _evidence_tainted_names(tree)
    hits = []
    for ln, what, tgt in _write_targets(tree, tainted):
        resolved = _resolved_evidence_path(tgt, tainted)
        if resolved is not None:
            hits.append((ln, what, ast.unparse(tgt), resolved))
    return hits


def _offenders():
    out = []
    for p in sorted(_tracked_tools_scripts()):
        if p.name in DELIBERATE_SNAPSHOT_ALLOWLIST:
            continue
        for ln, what, snippet, resolved in evidence_writes(p):
            out.append((p.relative_to(REPO).as_posix(), ln, what, snippet, resolved))
    return out


def test_no_tools_script_writes_into_evidence():
    """WO-026 §2's doctrine, mechanically enforced across every producer — not just the gate ledger.

    An instrument must stream to a git-ignored run-scoped `.artifacts/` path. Evidence is authored by
    a deliberate snapshot step, never produced as a side effect of running a tool."""
    offenders = _offenders()
    assert offenders == [], (
        "TOOLS SCRIPT(S) WRITE INTO evidence/ — running the tool would silently overwrite COMMITTED "
        "evidence (WO-026 §2 doctrine; WO-031 Finding 4 is the regression this guard exists to stop):"
        "\n" + "\n".join(f"  {rel}:{ln}  {what}  ->  {snippet}\n      resolves to: {resolved}"
                         for rel, ln, what, snippet, resolved in offenders)
        + "\nWrite to a git-ignored run-scoped path under .artifacts/ instead, and snapshot into "
          "evidence/ deliberately. If the script IS a deliberate snapshot tool, add a "
          "DELIBERATE_SNAPSHOT_ALLOWLIST entry that NAMES WHY."
    )


def test_evidence_write_allowlist_is_honest():
    """No stale exemption: every allowlisted script must still exist AND still write into evidence/.
    A stale entry silently suppresses nothing — or, worse, pre-authorises a script that has since
    stopped being a snapshot tool."""
    tracked = {p.name for p in _tracked_tools_scripts()}
    missing = sorted(n for n in DELIBERATE_SNAPSHOT_ALLOWLIST if n not in tracked)
    assert missing == [], f"stale DELIBERATE_SNAPSHOT_ALLOWLIST entries (script no longer tracked): {missing}"

    not_writing = sorted(
        n for n in DELIBERATE_SNAPSHOT_ALLOWLIST
        if not evidence_writes(TOOLS / n)
    )
    assert not_writing == [], (
        "stale DELIBERATE_SNAPSHOT_ALLOWLIST entries — these no longer write into evidence/, so the "
        f"exemption is suppressing nothing and should be removed: {not_writing}"
    )


def test_detector_actually_fires_on_a_real_evidence_write(tmp_path):
    """Rule 0.1d — prove the scanner FIRES on the real shape rather than trusting an empty result.

    Reproduces the exact WO-031 Finding 4 shape (module constant into evidence/, then `open(..,'w')`)
    plus the wrappers, and the two shapes that must NOT be flagged: a READ from evidence/, and a
    write to `.artifacts/`."""
    banned = tmp_path / "banned.py"
    banned.write_text(
        'import os\n'
        'REPO = "/repo"\n'
        'OUT = os.path.join(REPO, "evidence", "WO-029", "x.txt")\n'
        'def main():\n'
        '    os.makedirs(os.path.dirname(OUT), exist_ok=True)\n'
        '    open(OUT, "w", encoding="utf-8").write("x")\n',
        encoding="utf-8")
    hits = evidence_writes(banned)
    assert hits, "the detector missed the exact WO-031 Finding 4 shape"
    assert any('open(..., "w")' in what for _ln, what, _s, _r in hits)
    assert any("makedirs" in what for _ln, what, _s, _r in hits)
    # The finding must NAME THE PATH, not just the variable — §4.3 requires "script and path".
    assert all("evidence" in resolved for *_x, resolved in hits), (
        f"the finding must resolve the write target to its evidence/ path: {hits}"
    )

    allowed = tmp_path / "allowed.py"
    allowed.write_text(
        'import os\n'
        'REPO = "/repo"\n'
        'TABLE = os.path.join(REPO, "evidence", "WO-029", "batch_partition.md")   # a READ\n'
        'ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "thing")\n'
        'def main():\n'
        '    table = open(TABLE, encoding="utf-8").read()\n'
        '    os.makedirs(ARTIFACT_DIR, exist_ok=True)\n'
        '    open(os.path.join(ARTIFACT_DIR, "latest.txt"), "w").write(table)\n',
        encoding="utf-8")
    assert evidence_writes(allowed) == [], (
        "reading from evidence/ and writing to .artifacts/ must NOT be flagged — the doctrine bans "
        "authoring evidence as a side effect, not reading committed evidence"
    )

    pathlib_write = tmp_path / "pathlib_write.py"
    pathlib_write.write_text(
        'from pathlib import Path\n'
        'DEST = Path("/repo") / "evidence" / "WO-013" / "x.txt"\n'
        'DEST.write_text("x")\n',
        encoding="utf-8")
    assert evidence_writes(pathlib_write), "the detector must also see Path.write_text()"

    # Taint must survive an intermediate — the two-step shape the real snapshot tool uses, and the
    # shape a single non-propagating pass silently clears.
    two_step = tmp_path / "two_step.py"
    two_step.write_text(
        'from pathlib import Path\n'
        'def main(wo, name):\n'
        '    dest_dir = Path("/repo") / "evidence" / wo\n'
        '    dest = dest_dir / name\n'
        '    dest.write_text("x")\n',
        encoding="utf-8")
    assert evidence_writes(two_step), (
        "the detector must propagate taint through an intermediate path variable"
    )


def test_the_gate_ledger_conftest_guard_still_exists():
    """This guard GENERALIZES the WO-026 guard; it does not replace it. The conftest guard validates
    the ledger's directory at RUNTIME (a computed path this static scan cannot evaluate), so both are
    load-bearing — belt and suspenders on the same doctrine."""
    conftest = (REPO / "conftest.py").read_text(encoding="utf-8")
    assert "_assert_ledger_dir_outside_evidence" in conftest, (
        "the WO-026 runtime ledger guard disappeared — this static scan does NOT cover it "
        "(it cannot evaluate a runtime-computed output directory)"
    )
