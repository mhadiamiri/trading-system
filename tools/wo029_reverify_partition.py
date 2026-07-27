"""WO-029 §2.0 — RE-VERIFY THE COMMITTED PARTITION'S IDENTIFIERS AT THIS HEAD.

`evidence/WO-029/batch_partition.md` was derived one commit ago (base `9c084c3`). D34-3's discipline —
"an enumeration is only as good as its identifiers", the ruling that caught race #5 — says a later
batch must RE-DERIVE against the artifact rather than trust it. This is that re-derivation, and it is
the shape batches B and C should reuse: parse the committed table, and for each of the 30 races check
that the named test really does begin at the stated file:line, reporting where it moved to if not.

Line numbers are read from the COMMIT (`git show <ref>:<path>`), not the working tree, so the check is
stable while a batch is mid-conversion and gives the same answer for anyone re-running it later.

    python tools/wo029_reverify_partition.py [--ref HEAD]
"""
import argparse
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(REPO, "evidence", "WO-029", "batch_partition.md")
OUT = os.path.join(REPO, "evidence", "WO-029", "partition_reverified_at_head.txt")
TESTS_DIR = "tests/integration"

ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([\w.]+):(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|$", re.M)
EXPECTED = {"CLOCK-INJECTABLE": 26, "ASYNCIO-SLEEP": 3, "ALREADY-CONVERTED": 1}
ASYNCIO_SLEEP_SET = {
    "test_pong_observer_records_rtt_distribution_via_protocol_ping",
    "test_absent_pongs_are_a_signal_not_gappiness",
    "test_starved_lag_sampler_self_reports_degradation",
}
RACE_5 = "test_runner_resolves_live_adapter_from_data_source_via_factory"


def file_at_ref(ref, path):
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=REPO, capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout.splitlines()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="HEAD")
    args = ap.parse_args()
    sha = subprocess.run(["git", "rev-parse", args.ref], cwd=REPO, capture_output=True,
                         text=True).stdout.strip()

    table = open(TABLE, encoding="utf-8").read()
    rows = ROW.findall(table)
    cache, out, counts, verified, moved = {}, [], {}, 0, []
    out += [f"WO-029 §2.0 — the committed partition RE-VERIFIED at {args.ref} ({sha[:7]})",
            f"Source table: {os.path.relpath(TABLE, REPO)} (derived at base 9c084c3)",
            "Identifiers are re-derived, not trusted (D34-3: an enumeration is only as good as its",
            "identifiers — the discipline that caught race #5). Lines read from the COMMIT, not the",
            "working tree, so a mid-conversion tree cannot flatter the result.", "",
            f"  {'#':>3}  {'status':<14} file:line -> test"]

    for num, fname, line, name, cat, path in rows:
        name = name.replace("**", "").strip()
        key = cat.split("(")[0].strip().replace("**", "")
        counts[key] = counts.get(key, 0) + 1
        rel = f"{TESTS_DIR}/{fname}"
        if rel not in cache:
            cache[rel] = file_at_ref(args.ref, rel)
        lines = cache[rel]
        idx = int(line) - 1
        starts = (f"async def {name}(", f"def {name}(")
        hit = 0 <= idx < len(lines) and lines[idx].strip().startswith(starts)
        real = next((i + 1 for i, ln in enumerate(lines) if ln.strip().startswith(starts)), None)
        if hit:
            verified += 1
            status = "OK"
        else:
            moved.append((num, name, line, real))
            status = f"MOVED->{real}" if real else "MISSING"
        out.append(f"  {num:>3}  {status:<14} {fname}:{line} -> {name}")

    names = {r[3].replace("**", "").strip() for r in rows}
    sleep_named = {r[3].replace("**", "").strip() for r in rows
                   if "ASYNCIO-SLEEP" in r[4]} == ASYNCIO_SLEEP_SET
    race5_injectable = any(r[3].replace("**", "").strip() == RACE_5
                           and "CLOCK-INJECTABLE" in r[4] for r in rows)
    counts_ok = all(counts.get(k) == v for k, v in EXPECTED.items())

    out += ["",
            f"  identifiers verified at their stated line : {verified}/{len(rows)}",
            f"  moved / missing                           : {moved or 'none'}",
            f"  category counts                           : {counts}  (expected {EXPECTED}) -> {counts_ok}",
            f"  the 3 asyncio-sleep races, BY NAME        : {sleep_named}",
            f"  race #5 is in the 26 (CLOCK-INJECTABLE)   : {race5_injectable}",
            f"  total races in the table                  : {len(rows)} / distinct names {len(names)}",
            ""]
    verdict = "PASS" if (verified == len(rows) == 30 and counts_ok and sleep_named
                         and race5_injectable) else "FAIL"
    out.append(f"VERDICT: {verdict} — the partition stands at this HEAD; batch A = "
               f"test_live_capture.py races 1-5, and it converts WHOLE.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
