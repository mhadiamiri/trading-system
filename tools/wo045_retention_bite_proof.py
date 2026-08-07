"""WO-045 §2 BITE PROOF — bounded raw-text retention. Four artifacts, sha256 exact-restore.

    python tools/wo045_retention_bite_proof.py

BITE      drive retention far past the cap -> retention stops growing AND the past-cap count is
          surfaced. The memory bound is MEASURED (sys.getsizeof over the live buffer), not asserted.
DUAL      under the cap -> everything retained, count zero, no behaviour change. A cap that
          truncates early is as wrong as one that never fires.
MUTATION  neuter the cap -> the BITE assertions fail while the DUAL still passes. That asymmetry is
          what proves the cap enforces the bound rather than something adjacent to it.

The mutation reverts `_retain_raw_text` to the unbounded append that WO-044 measured at 35-48 MB/h
— i.e. it restores the exact defect D46 ruled on, and the proof watches the bound disappear.

Writes to .artifacts/ (WO-032 §4.1 — an instrument must not write into the evidence record).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "trading", "data", "adapters", "kraken_v2_book.py")
TESTS = "tests/test_raw_retention_cap.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo045_retention_bite_proof")

# The anchor spans THREE lines, and the source is CRLF on this host. Earlier bite proofs used
# single-line anchors and never met this; a `\n`-joined literal simply does not occur in a CRLF
# file, so the uniqueness assert refused (correctly) rather than mutating something unintended.
# The lines are declared separately and joined with the newline the FILE actually uses.
ANCHOR_LINES = [
    "        if (len(buf) <= self._max_retained_raw_frames",
    "                and self._raw_text_bytes <= self._max_retained_raw_bytes):",
    "            return",
]
MUTANT_LINES = [
    "        if True:   # MUTATED: cap neutered — unbounded append restored (the WO-044 defect)",
    "            return",
]


def _detect_newline(text):
    return "\r\n" if "\r\n" in text else "\n"

# The BITE half — assertions that the bound holds. Must FAIL under the mutation.
BITE_TESTS = {
    "test_retention_stops_growing_at_the_cap_and_evictions_are_counted",
    "test_the_memory_bound_is_MEASURED_not_asserted",
    "test_the_byte_cap_binds_independently_of_the_count_cap",
    "test_the_floor_outranks_both_caps",
    "test_the_cap_announces_once_and_does_not_terminate_the_run",
    "test_the_eviction_count_is_surfaced_in_the_diagnostic_counters",
    "test_frames_captured_reports_reach_not_buffer_size",
}
# The DUAL half — behaviour under the cap. Must STILL PASS under the mutation.
DUAL_TESTS = {
    "test_under_the_cap_everything_is_retained_and_nothing_is_counted",
    "test_exactly_at_the_cap_nothing_is_evicted",
    "test_the_cap_is_declared_with_both_dimensions",
    "test_the_cap_never_starves_its_own_consumer",
    "test_the_reason_code_is_declared",
}

# Drives 200,000 messages of ~600 B through a cap of 50,000 and MEASURES the live buffer.
# Uncapped that is ~120 MB of wire text; capped it must stay at the ceiling.
MEASURE = r"""
import sys
sys.path.insert(0, "src")
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter as A
a = A(mode=A.MODE_LIVE)
a._persistence_optional = True
a.captured_raw_text = []
a._raw_text_bytes = 0
a._raw_text_evicted = 0
a._raw_retention_capped = False
msg = "y" * 600
marks = {}
for i in range(1, 200001):
    a._retain_raw_text(msg)
    if i in (50000, 100000, 200000):
        marks[i] = sum(sys.getsizeof(s) for s in a.captured_raw_text) + sys.getsizeof(a.captured_raw_text)
print("MEASURED_AT_50K_BYTES", marks[50000])
print("MEASURED_AT_100K_BYTES", marks[100000])
print("MEASURED_AT_200K_BYTES", marks[200000])
print("RETAINED_ENTRIES", len(a.captured_raw_text))
print("EVICTED", a._raw_text_evicted)
print("CAPPED", a._raw_retention_capped)
"""


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _env():
    return dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")


def run_tests():
    p = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-p", "no:randomly", "-v", "--tb=line", "-q"],
        cwd=REPO, env=_env(), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=900,
    )
    return p.returncode, (p.stdout + p.stderr)


def run_measure():
    p = subprocess.run([sys.executable, "-c", MEASURE], cwd=REPO, env=_env(),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    out = {}
    for line in (p.stdout or "").splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[0]] = parts[1]
    if not out:
        out["ERROR"] = (p.stdout + p.stderr)[-400:]
    return out


def digest(rc, out, measured):
    failed = set(re.findall(r"(test_\w+)\s+FAILED", out)) | set(
        re.findall(r"FAILED .*?::(test_\w+)", out))
    passed = set(re.findall(r"(test_\w+)\s+PASSED", out))
    tail = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    d = {
        "returncode": rc,
        "summary": tail[-1].strip() if tail else "(no summary line)",
        "bite_failed": sorted(failed & BITE_TESTS),
        "dual_passed": sorted(passed & DUAL_TESTS),
        "dual_failed": sorted(failed & DUAL_TESTS),
    }
    d.update(measured)
    return d


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<26} {v}")
    lines.append(f"  EXPECT: {expectation}")
    return lines + [""]


def main():
    original = open(SRC, "rb").read()
    text = original.decode("utf-8")
    nl = _detect_newline(text)
    anchor = nl.join(ANCHOR_LINES)
    mutant = nl.join(MUTANT_LINES)
    assert text.count(anchor) == 1, (
        f"the cap's early-return anchor is not unique (found {text.count(anchor)}) — "
        f"refusing to mutate blindly"
    )
    before = sha256(SRC)

    out = ["WO-045 §2 BITE PROOF — BOUNDED RAW-TEXT RETENTION.",
           "Four artifacts, sha256 exact-restore. The memory bound is MEASURED, not asserted.",
           f"  file          : {os.path.relpath(SRC, REPO)}",
           f"  tests         : {TESTS}",
           f"  measurement   : 200,000 x ~600 B messages through a 50,000-frame cap",
           f"  sha256 BEFORE : {before}", ""]

    d1 = digest(*run_tests(), run_measure())
    out += block("ARTIFACT 1 — PRISTINE (bite + dual both hold; bound MEASURED)", d1,
                 "returncode 0; no bite failure; measured bytes FLAT from 50k->200k messages")

    open(SRC, "wb").write(text.replace(anchor, mutant, 1).encode("utf-8"))
    try:
        out += [f"  sha256 WHILE MUTATED: {sha256(SRC)}",
                "  MUTATION: the cap's enforcement is neutered — unbounded append restored", ""]
        d2 = digest(*run_tests(), run_measure())
    finally:
        open(SRC, "wb").write(original)

    out += block("ARTIFACT 2 — MUTATED (NECESSITY: the bite must fail, the dual must not)", d2,
                 "bite assertions FAIL; dual STILL PASSES; measured bytes GROW with run length")

    d3 = digest(*run_tests(), run_measure())
    out += block("ARTIFACT 3 — RESTORED", d3, "returncode 0; bound holds again")

    after = sha256(SRC)
    exact = after == before
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --",
            f"  sha256 AFTER  : {after}",
            f"  IDENTICAL     : {exact}", ""]

    # The MEASURED bound, stated as the arithmetic a reader can check.
    try:
        p50, p200 = int(d1["MEASURED_AT_50K_BYTES"]), int(d1["MEASURED_AT_200K_BYTES"])
        m50, m200 = int(d2["MEASURED_AT_50K_BYTES"]), int(d2["MEASURED_AT_200K_BYTES"])
        bound_holds = p200 <= p50 * 1.02
        mutant_grows = m200 > m50 * 2
        out += ["-- THE MEASURED BOUND --",
                f"  PRISTINE  50k -> 200k messages : {p50:,} B -> {p200:,} B   "
                f"(flat: {bound_holds})",
                f"  MUTATED   50k -> 200k messages : {m50:,} B -> {m200:,} B   "
                f"(grows: {mutant_grows})",
                f"  the mutant retains {m200 / max(p200, 1):.1f}x more at 200k messages", ""]
    except (KeyError, ValueError):
        bound_holds = mutant_grows = False
        out += ["-- THE MEASURED BOUND --", "  (measurement unavailable — see artifacts)", ""]

    discriminating = bool(d2["bite_failed"]) and not d2["dual_failed"]
    out += [f"  DISCRIMINATION (mutation breaks the bite, not the dual): {discriminating}", ""]

    ok = (d1["returncode"] == 0 and not d1["bite_failed"]
          and d2["returncode"] != 0 and discriminating and bound_holds and mutant_grows
          and d3["returncode"] == 0 and not d3["bite_failed"] and exact)
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
