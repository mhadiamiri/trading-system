"""WO-029 §2.0 — RE-VERIFY THE COMMITTED PARTITION'S IDENTIFIERS AT THIS HEAD.

`evidence/WO-029/batch_partition.md` was derived at base `9c084c3`. D34-3's discipline —
"an enumeration is only as good as its identifiers", the ruling that caught race #5 — says a later
batch must RE-DERIVE against the artifact rather than trust it. This is that re-derivation, and it is
the shape batches B and C should reuse: parse the committed table and, for each of the 30 races,
resolve the named test in the file it claims.

WO-032 §1 — THE VERDICT IS KEYED ON **NAME**, NOT LINE.
    The original verdict required every race to sit at its ORIGINAL line, and each batch's conversion
    moves its own file's races (batch A's +92/-15 in `test_live_capture.py` moved races 1-5). So the
    tool reported `25/30 / VERDICT: FAIL` for a partition that was perfectly intact — a FALSE FAIL
    that would have recurred, growing, for every batch after A.

    The stable identifier for a partition that must SURVIVE conversions is the test NAME. D34-3's
    "position beats name" governs FINDING a race in an audit; it does not make a line number a
    durable key across the very edits the partition exists to schedule. So:
      * a race whose NAME does not resolve to a real test is a HARD FAIL — that is a real break;
      * a race that resolves at a DIFFERENT line is reported as `MOVED->n` and is INFORMATIONAL.
    Line numbers are still printed, because knowing where a race went is useful; they no longer gate.

WO-032 §4.1 — THIS INSTRUMENT NEVER WRITES INTO `evidence/`.
    It previously wrote its output straight into `evidence/WO-029/partition_reverified_at_head.txt`,
    a COMMITTED file, so merely running it silently overwrote committed evidence (WO-031 Finding 4 —
    a regression of the WO-026 §2 defect). Output now goes to a git-ignored, run-scoped `.artifacts/`
    path. Reading the committed table is still fine; a READ is not the banned pattern.

Line numbers are read from the COMMIT (`git show <ref>:<path>`), not the working tree, so the check is
stable while a batch is mid-conversion and gives the same answer for anyone re-running it later.

    python tools/wo029_reverify_partition.py [--ref HEAD] [--table PATH]
"""
import argparse
import os
import re
import subprocess
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(REPO, "evidence", "WO-029", "batch_partition.md")
# WO-032 §4.1 — an INSTRUMENT streams to a git-ignored, run-scoped `.artifacts/` path and NEVER into
# `evidence/` (WO-026 §2's doctrine, generalized past the gate ledger by WO-032 §4). Evidence is a
# DELIBERATE snapshot, never an instrument side effect. Guarded: tests/test_evidence_write_boundary.py.
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo029_reverify_partition")
TESTS_DIR = "tests/integration"

# WO-035 §2.2 (D42): the partition's identifier column is now the pytest NODE ID, and the prose
# `file:line + name` moved to a retained-but-superseded column. This row shape follows that change —
# capture the node ID's file and test name, and ignore the historical column entirely. Keying on the
# node ID is the point: it is what pytest itself addresses the test by.
#
# The row number may be bolded (`| **35** |`) — entry 35 is the BOUND->RACE promotion (D40/D41).
ROW = re.compile(
    r"^\|\s*\**(\d+)\**\s*\|\s*`([\w.]+)::([\w]+)`\s*\|\s*([^|]*?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|$",
    re.M)
# 31 rows: the audit's 30 + entry 35, promoted from the bounds block by D40/D41 and landed in the
# artifact by WO-035 §2.1. Clock-injectable 26 -> 27.
EXPECTED = {"CLOCK-INJECTABLE": 27, "ASYNCIO-SLEEP": 3, "ALREADY-CONVERTED": 1}
EXPECTED_ROWS = 31
ASYNCIO_SLEEP_SET = {
    "test_pong_observer_records_rtt_distribution_via_protocol_ping",
    "test_absent_pongs_are_a_signal_not_gappiness",
    "test_starved_lag_sampler_self_reports_degradation",
}
RACE_5 = "test_runner_resolves_live_adapter_from_data_source_via_factory"


def file_at_ref(ref, path):
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=REPO, capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout.splitlines()


def write_artifact(body: str) -> str:
    """WO-032 §4.1: run-scoped file plus a `latest.txt` convenience copy, both git-ignored."""
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = os.path.join(ARTIFACT_DIR, f"{stamp}.txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    return run_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--table", default=TABLE,
                    help="partition table to verify (defaults to the committed one)")
    args = ap.parse_args()
    sha = subprocess.run(["git", "rev-parse", args.ref], cwd=REPO, capture_output=True,
                         text=True).stdout.strip()

    table = open(args.table, encoding="utf-8").read()
    rows = ROW.findall(table)
    cache, out, counts, at_stated_line, moved, missing = {}, [], {}, 0, [], []
    out += [f"WO-029 §2.0 — the committed partition RE-VERIFIED at {args.ref} ({sha[:7]})",
            f"Source table: {os.path.relpath(args.table, REPO)} (derived at base 9c084c3)",
            "Identifiers are re-derived, not trusted (D34-3: an enumeration is only as good as its",
            "identifiers — the discipline that caught race #5). Lines read from the COMMIT, not the",
            "working tree, so a mid-conversion tree cannot flatter the result.",
            "WO-032 §1: the verdict keys on NAME RESOLUTION. A moved line is informational (each",
            "batch's own conversion moves its file's races); an UNRESOLVABLE NAME is a hard FAIL.",
            "WO-035 §2.2 (D42): identifiers read from the partition's NODE ID column; the prose",
            "file:line column is retained there as superseded history and is NOT parsed.", "",
            f"  {'#':>3}  {'status':<14} node id"]

    for num, fname, name, prose, cat, path in rows:
        key = cat.split("(")[0].strip().replace("**", "")
        counts[key] = counts.get(key, 0) + 1
        rel = f"{TESTS_DIR}/{fname}"
        if rel not in cache:
            cache[rel] = file_at_ref(args.ref, rel)
        lines = cache[rel]
        starts = (f"async def {name}(", f"def {name}(")
        real = next((i + 1 for i, ln in enumerate(lines) if ln.strip().startswith(starts)), None)
        if real:
            at_stated_line += 1
            status = f"OK@{real}"
        else:
            missing.append((num, name, fname, prose))
            status = "MISSING"
        out.append(f"  {num:>3}  {status:<14} {TESTS_DIR}/{fname}::{name}")

    names = {r[2] for r in rows}
    resolved = at_stated_line + len(moved)
    sleep_named = {r[2] for r in rows if "ASYNCIO-SLEEP" in r[4]} == ASYNCIO_SLEEP_SET
    race5_injectable = any(r[2] == RACE_5
                           and "CLOCK-INJECTABLE" in r[4] for r in rows)
    counts_ok = all(counts.get(k) == v for k, v in EXPECTED.items())

    out += ["",
            f"  names RESOLVED to a real test  (GATES)    : {resolved}/{len(rows)}",
            f"  unresolvable names             (GATES)    : {missing or 'none'}",
            f"  ...of those, at their stated line (info)  : {at_stated_line}/{len(rows)}",
            f"  ...moved by a conversion          (info)  : {moved or 'none'}",
            f"  category counts                           : {counts}  (expected {EXPECTED}) -> {counts_ok}",
            f"  the 3 asyncio-sleep races, BY NAME        : {sleep_named}",
            f"  race #5 is CLOCK-INJECTABLE               : {race5_injectable}",
            f"  total races in the table                  : {len(rows)} / distinct names {len(names)} "
            f"(expected {EXPECTED_ROWS} = the audit's 30 + entry 35, D40/D41)",
            ""]
    ok = (resolved == len(rows) == EXPECTED_ROWS and len(names) == EXPECTED_ROWS and not missing
          and counts_ok and sleep_named and race5_injectable)
    verdict = "PASS" if ok else "FAIL"

    # WO-032 §1.2 — the trailing line REFLECTS the verdict. It previously asserted "the partition
    # stands…converts WHOLE" unconditionally, so a FAIL run still read as reassurance to anyone
    # skimming the last line (the instrument-competence family).
    if ok:
        out.append(f"VERDICT: {verdict} — all {len(rows)} races resolve by name; the partition stands "
                   f"at this HEAD. Moved lines: {len(moved)} (informational).")
    else:
        why = []
        if missing:
            why.append(f"{len(missing)} name(s) do not resolve to any test: "
                       + ", ".join(f"#{n} {nm} (expected in {f})" for n, nm, f, _ln in missing))
        if len(names) != len(rows):
            why.append(f"duplicate names ({len(names)} distinct out of {len(rows)} rows)")
        if not counts_ok:
            why.append(f"category counts {counts} != expected {EXPECTED}")
        if not sleep_named:
            why.append("the 3 asyncio-sleep races do not match the expected set BY NAME")
        if not race5_injectable:
            why.append("race #5 is not CLOCK-INJECTABLE in the table")
        if len(rows) != 30:
            why.append(f"the table has {len(rows)} rows, expected 30")
        out.append(f"VERDICT: {verdict} — THE PARTITION IS BROKEN AT THIS HEAD. " + "; ".join(why))

    body = "\n".join(out) + "\n"
    run_path = write_artifact(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored; evidence is a "
          f"deliberate snapshot, never an instrument side effect)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
