"""WO-044 §3 BITE PROOF — a resume, proved end to end. Four artifacts, sha256 exact-restore.

    python tools/wo044_resume_bite_proof.py

WHAT IT DOES. Runs a capture in a CHILD PROCESS, KILLS that process mid-run (TerminateProcess on
Windows — unblockable, so no `finally` runs and no MANIFEST.json is written: the exact shape of the
two runs the security-policy shutdown ate), then RESUMES under the SAME corpus-id in a second
child. It then proves the six properties §3's bite proof demands:

    P1 the seam is LEDGERED with its declared cause
    P2 the seam duration is the MEASURED true duration (prior last frame -> resumed first frame)
    P3 the resumed run has its OWN preflight record (no inherited preconditions, §3.2)
    P4 no book state crossed the seam — the resumed run took a FRESH snapshot and rebuilt (§3.4)
    P5 the manifest SPANS both runs, every segment hashed (§3.5)
    P6 cumulative hours SUM correctly across the runs (§3.7)

THE MUTATION (what makes this a bite proof rather than a demo). `SeamRecord.duration_seconds` is
mutated to return a constant 0.0 — a SMOOTHED seam, the precise dishonesty §0.4 forbids ("never
smooth a seam, never shorten an outage"). A proof that cannot see that is not a proof. P2 must FAIL
while the others still hold, which also shows the properties are independent rather than one
assertion wearing six hats.

Writes to .artifacts/ (WO-032 §4.1 — an instrument must never write into the evidence record).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "data", "corpus.py")
CHILD = os.path.join(REPO, "tools", "wo044_resume_child.py")
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo044_resume_bite_proof")

ANCHOR = "        return (end - start).total_seconds()"
MUTANT = "        return 0.0   # MUTATED: a SMOOTHED seam — duration no longer measured"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _env():
    # DATA_SOURCE=kraken_v2 selects the LIVE-CAPABLE adapter (.env ships `simulated`, which
    # create_live_capture_feed refuses). No socket is opened regardless: the child injects the
    # scripted transport through connect_fn, and `_REAL_CONNECT` is never reached.
    return dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                TRADING_ENV="paper", CORPUS_AUTO_MODE_CONFIRMED="true",
                DATA_SOURCE="kraken_v2")


def _run_and_kill(corpus_dir, corpus_id, kill_after=6.0):
    """Start a capture child and KILL it mid-run. Returns (killed: bool, stdout).

    The child holds the link open with heartbeats until its deadline, so a kill lands squarely
    inside a live capture — after frames are on disk, before any finalize.
    """
    proc = subprocess.Popen(
        [sys.executable, CHILD, "--corpus-dir", corpus_dir, "--corpus-id", corpus_id,
         "--frames", "8", "--frame-spacing", "0.5", "--duration-hours", "0.05"],
        cwd=REPO, env=_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    time.sleep(kill_after)          # let the preflight finish and frames land
    proc.kill()                     # TerminateProcess — no finally, no MANIFEST.json
    try:
        out = proc.communicate(timeout=30)[0]
    except subprocess.TimeoutExpired:
        out = "(child did not drain stdout)"
    return proc.returncode != 0, out


def _run_to_completion(corpus_dir, corpus_id, seam_cause):
    cmd = [sys.executable, CHILD, "--corpus-dir", corpus_dir, "--corpus-id", corpus_id,
           "--frames", "8", "--frame-spacing", "0.5", "--duration-hours", "0.0017"]
    if seam_cause:
        cmd += ["--seam-cause", seam_cause]
    p = subprocess.run(cmd, cwd=REPO, env=_env(), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    return p.returncode, p.stdout + p.stderr


def scenario():
    """Run the kill+resume scenario in a throwaway dir; return the measured properties."""
    tmp = tempfile.mkdtemp(prefix="wo044_resume_")
    corpus_id = "corpus_biteproof"
    try:
        killed, out_a = _run_and_kill(tmp, corpus_id)
        rc_b, out_b = _run_to_completion(tmp, corpus_id, "POLICY_SHUTDOWN")

        manifest_path = os.path.join(tmp, corpus_id, "CORPUS_MANIFEST.json")
        if not os.path.exists(manifest_path):
            return {"error": "no corpus manifest written",
                    "killed": killed, "rc_b": rc_b, "out_a": out_a[-2000:], "out_b": out_b[-2000:]}
        manifest = json.loads(open(manifest_path, encoding="utf-8").read())

        runs = manifest["runs"]
        seams = manifest["seams"]
        killed_runs = [r for r in runs if not r["finalized"]]
        resumed_runs = [r for r in runs if r["finalized"]]

        seam = seams[0] if seams else None
        # P2: recompute the duration INDEPENDENTLY from the two endpoint stamps, so the property is
        # measured against the record's own bounds rather than trusting the field it reports.
        independent = None
        if seam and seam["prior_last_frame_utc"] and seam["resumed_first_frame_utc"]:
            a = datetime.fromisoformat(seam["prior_last_frame_utc"].replace("Z", "+00:00"))
            b = datetime.fromisoformat(seam["resumed_first_frame_utc"].replace("Z", "+00:00"))
            independent = (b - a).total_seconds()

        # P4: the resumed run's gap ledger carries its OWN run_start anchor — a fresh capture,
        # a fresh book. A carried-over book would have reused the prior run's anchor.
        anchors = []
        for r in runs:
            gl = os.path.join(tmp, corpus_id, r["run_id"], "gap_ledger.json")
            if os.path.exists(gl):
                for line in open(gl, encoding="utf-8"):
                    rec = json.loads(line)
                    if rec.get("event") == "run_start":
                        anchors.append(rec["run_wall_anchor"])
                        break

        segs = [s for r in runs for s in r["segments"]]
        cumulative = manifest["progress"]["cumulative_covered_hours"]
        expected_cumulative = sum(r["covered_seconds"] for r in runs) / 3600.0

        return {
            "killed_mid_run": killed,
            "resume_returncode": rc_b,
            "runs_in_manifest": len(runs),
            "unfinalized_runs": len(killed_runs),
            "finalized_runs": len(resumed_runs),
            # P1
            "P1_seam_ledgered": seam is not None,
            "P1_seam_cause": seam["cause"] if seam else None,
            "P1_seam_reason_code": seam["reason_code"] if seam else None,
            "P1_seam_resolved": seam["resolved"] if seam else None,
            # P2
            "P2_seam_duration_reported": seam["duration_seconds"] if seam else None,
            "P2_seam_duration_independent": independent,
            "P2_duration_is_measured": (
                seam is not None and independent is not None
                and seam["duration_seconds"] is not None
                and abs(seam["duration_seconds"] - independent) < 1e-6
                and independent > 0.0
            ),
            # P3
            "P3_preflight_per_run": all(
                os.path.exists(os.path.join(tmp, corpus_id, r["run_id"], "PREFLIGHT.json"))
                for r in runs),
            "P3_resumed_preflight_is_own": bool(
                resumed_runs and resumed_runs[0]["preflight"].get("run_id")
                == resumed_runs[0]["run_id"]),
            # P4
            "P4_distinct_run_anchors": len(set(anchors)) == len(anchors) and len(anchors) >= 2,
            "P4_anchors": anchors,
            # P5
            "P5_manifest_spans_runs": len(runs) >= 2,
            "P5_every_segment_hashed": bool(segs) and all(len(s["sha256"]) == 64 for s in segs),
            "P5_segments": len(segs),
            # P6. Tolerance is 1e-4 because progress() rounds to 4 decimal places (up to 5e-5 of
            # rounding), and the span must be NON-ZERO or the property is vacuous — "0 == 0" would
            # pass on an accounting that never counted anything.
            "P6_cumulative_hours": cumulative,
            "P6_expected_hours": round(expected_cumulative, 6),
            "P6_sums_correctly": (expected_cumulative > 0.0
                                  and abs(cumulative - expected_cumulative) < 1e-4),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def verdict(d):
    if "error" in d:
        return False
    return all([
        d["killed_mid_run"], d["resume_returncode"] == 0,
        d["P1_seam_ledgered"], d["P1_seam_cause"] == "POLICY_SHUTDOWN", d["P1_seam_resolved"],
        d["P2_duration_is_measured"],
        d["P3_preflight_per_run"], d["P3_resumed_preflight_is_own"],
        d["P4_distinct_run_anchors"],
        d["P5_manifest_spans_runs"], d["P5_every_segment_hashed"],
        d["P6_sums_correctly"],
    ])


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<32} {v}")
    lines.append(f"  VERDICT: {'PASS' if verdict(d) else 'FAIL'}")
    lines.append(f"  EXPECT : {expectation}")
    return lines + [""]


def main():
    original = open(SRC, "rb").read()
    text = original.decode("utf-8")
    assert text.count(ANCHOR) == 1, (
        f"the seam-duration anchor is not unique in corpus.py "
        f"(found {text.count(ANCHOR)}) — refusing to mutate blindly"
    )
    before = sha256(SRC)

    out = ["WO-044 §3 BITE PROOF — RESUME: run, kill the process, resume under the same corpus-id.",
           "Four artifacts, sha256 exact-restore. NO NETWORK (scripted transport).",
           f"  file          : {os.path.relpath(SRC, REPO)}",
           f"  sha256 BEFORE : {before}", ""]

    d1 = scenario()
    out += block("ARTIFACT 1 — PRISTINE (a real kill, a real resume, six properties)", d1,
                 "all six properties hold; seam POLICY_SHUTDOWN with a measured duration")

    open(SRC, "wb").write(text.replace(ANCHOR, MUTANT, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED: {sha256(SRC)}",
                "  MUTATION: SeamRecord.duration_seconds -> constant 0.0 (a SMOOTHED seam)", ""]
        d2 = scenario()
    finally:
        open(SRC, "wb").write(original)

    out += block("ARTIFACT 2 — MUTATED (the BITE: a smoothed seam must NOT pass)", d2,
                 "P2 FAILS (duration no longer measured) while P1/P3/P4/P5 still hold")

    d3 = scenario()
    out += block("ARTIFACT 3 — RESTORED", d3, "all six properties hold again")

    after = sha256(SRC)
    exact = after == before
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --",
            f"  sha256 AFTER  : {after}",
            f"  IDENTICAL     : {exact}", ""]

    # The discrimination: the mutation must break P2 SPECIFICALLY, not everything at once.
    discriminating = (
        not verdict(d2)
        and d2.get("P2_duration_is_measured") is False
        and d2.get("P1_seam_ledgered") is True
        and d2.get("P3_preflight_per_run") is True
        and d2.get("P5_every_segment_hashed") is True
    )
    out += [f"  DISCRIMINATION (mutation breaks P2 only): {discriminating}", ""]

    ok = verdict(d1) and not verdict(d2) and discriminating and verdict(d3) and exact
    out += [f"VERDICT: {'PASS' if ok else 'FAIL'}"]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    assert exact, "SRC NOT RESTORED — aborting"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
