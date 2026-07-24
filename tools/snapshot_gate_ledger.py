"""
WO-026 §2 — DELIBERATE gate-ledger snapshot (evidence is authored, not streamed).

The gate ledger instrument (conftest.py) streams to a run-scoped, git-ignored path under
`.artifacts/gate_ledger/` on every pytest run — it NEVER writes under evidence/. Committing evidence
is a separate, DELIBERATE act: this tool copies the latest run-scoped ledger into `evidence/<WO>/`
with a provenance header (commit sha, UTC timestamp, interpreter, seed/ordering, the WO taking it), so
a human or a WO runner decides what becomes evidence and when — not the test session.

    python tools/snapshot_gate_ledger.py --wo WO-026 [--seed 20260729 | --order deterministic] \
        [--source .artifacts/gate_ledger/latest.txt] [--name gate_ledger_snapshot.txt]

NO test session imports or runs this. It only reads an .artifacts/ file and writes ONE evidence file.
"""

import argparse
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = (REPO_ROOT / "evidence").resolve()


def _short_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO_ROOT),
                              capture_output=True, text=True, timeout=5).stdout.strip() or "nogit"
    except Exception:
        return "nogit"


def main() -> int:
    ap = argparse.ArgumentParser(description="Snapshot the run-scoped gate ledger into evidence/.")
    ap.add_argument("--wo", required=True, help="the WO taking the snapshot, e.g. WO-026")
    ap.add_argument("--source", default=str(REPO_ROOT / ".artifacts" / "gate_ledger" / "latest.txt"),
                    help="the run-scoped ledger to snapshot (default: .artifacts/gate_ledger/latest.txt)")
    ap.add_argument("--name", default="gate_ledger.txt", help="destination filename under evidence/<WO>/")
    ap.add_argument("--seed", default=None, help="the randomly-seed used, if any (provenance)")
    ap.add_argument("--order", default=None, help="ordering, e.g. 'deterministic' (provenance)")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        print(f"ERROR: source ledger {src} does not exist — run the suite first.", file=sys.stderr)
        return 2

    dest_dir = REPO_ROOT / "evidence" / args.wo
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / args.name
    # Guard the guard: a snapshot writes INTO evidence/ (that is its job); the INSTRUMENT never does.
    if not dest.resolve().is_relative_to(EVIDENCE_DIR):
        print(f"ERROR: destination {dest} is not under evidence/.", file=sys.stderr)
        return 2

    header = [
        "=" * 78,
        f"PROVENANCE (WO-026 §2 deliberate snapshot) — taken by {args.wo}",
        f"  commit:      {_short_sha()}",
        f"  taken (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"  interpreter: {platform.python_implementation()} {platform.python_version()}",
        f"  ordering:    {args.order or 'unspecified'}   seed: {args.seed or 'unspecified'}",
        f"  source:      {src}",
        "This is a DELIBERATE copy of a run-scoped .artifacts/ ledger. The test session never writes",
        "here (WO-026 §2, mechanically enforced in conftest.py::_assert_ledger_dir_outside_evidence).",
        "=" * 78,
        "",
    ]
    dest.write_text("\n".join(header) + src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"snapshot written: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
