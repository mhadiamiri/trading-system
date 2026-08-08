"""WO-058 §2.3 BITE PROOF — the Term 2 gate reads FLOW, not STOCK. Four artifacts, exact-restore.

    python tools/wo058_flow_gate_bite_proof.py

FIXTURES ONLY — the gate is driven through its injected sampler; nothing touches a socket.

WHAT IS BEING PROVED
--------------------
Not that the gate can go RED — WO-057's gate could do that, which was the problem. The thing being
proved is that it goes RED for the RIGHT QUANTITY.

    FLOW  = pages/sec serviced from disk. An ongoing RATE. This is D46's mechanism.
    STOCK = swap bytes parked in the pagefile. Windows retains these proactively.

A host can hold half a gigabyte of stock and read ZERO pages per second — which is exactly this
host. WO-057 gated on the stock, and a capture the host was always able to run looked impossible
for a second time.

THE MUTATION: gate on STOCK instead of FLOW, i.e. restore WO-057's criterion.

THE ASYMMETRY:

    the BITE  (real paging -> RED)                     -> still passes under the mutation
    the DUAL  (zero flow, large stock -> GREEN)        -> FAILS

Both criteria reject a genuinely paging host, so the bite alone cannot tell them apart. Only the
dual — the pre-ruled case, and the entire reason for D58 ruling 3 — distinguishes them.

§0.10 — the discrimination sets hold only single-purpose tests; exclusions recorded below.

Writes to .artifacts/ (WO-032 §4.1).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(REPO, "src", "trading", "data", "capture_gate.py")
TESTS = "tests/test_capture_gate.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo058_flow_gate_bite_proof")

# ── THE MUTATION: gate on STOCK instead of FLOW (WO-057's criterion, restored) ────────────────
ANCHOR = [
    "        mean_flow = sum(flow_samples) / len(flow_samples)",
    "        flow_green = (max(flow_samples) <= MAX_PAGING_FLOW_PER_SAMPLE",
    "                      and mean_flow <= MAX_PAGING_FLOW_MEAN)",
]
MUTANT = [
    "        # MUTATED: gate on STOCK, not FLOW — WO-057's criterion restored.",
    "        flow_green = (stock_bytes == 0)",
]

# SINGLE-PURPOSE sets (§0.10).
DUAL = {"test_DUAL_green_when_flow_is_zero_but_STOCK_is_large"}
BITE = {"test_BITE_red_when_the_host_is_actually_paging"}
FAIL_CLOSED = {"test_the_gate_FAILS_CLOSED_when_the_counter_cannot_be_read"}
# BROAD — excluded from the discrimination sets and reported for visibility (§0.10). These read
# several fields of the verdict at once and attribute nothing on their own.
BROAD = {
    "test_green_when_paging_flow_is_zero_and_memory_clears_the_floor",
    "test_the_two_halves_are_reported_separately",
    "test_the_verdict_records_the_evidence_not_just_the_answer",
    "test_a_low_trickle_below_the_per_sample_bound_still_fails_on_the_mean",
    "test_red_when_free_memory_is_below_the_declared_floor",
}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _nl(t):
    return "\r\n" if "\r\n" in t else "\n"


def run_tests():
    p = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-p", "no:randomly", "-v", "--tb=line", "-q"],
        cwd=REPO, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    failed_lines = [line for line in out.splitlines() if "FAILED" in line]
    failed = {f.split("::")[-1] for f in re.findall(r"(test_[\w\[\]\.\-]+)",
                                                    "\n".join(failed_lines))}
    return {
        "returncode": rc,
        "summary": next((line.strip() for line in reversed(out.splitlines())
                         if re.search(r"\d+ (passed|failed)", line)), "(no summary)"),
        "dual_failed": sorted(failed & DUAL),
        "bite_failed": sorted(failed & BITE),
        "fail_closed_failed": sorted(failed & FAIL_CLOSED),
        "broad_failed": sorted(failed & BROAD),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<22} {v}")
    return lines + [f"  EXPECT: {expectation}", ""]


def _mutate(path, anchor_lines, mutant_lines):
    original = open(path, "rb").read()
    text = original.decode("utf-8")
    nl = _nl(text)
    anchor, mutant = nl.join(anchor_lines), nl.join(mutant_lines)
    assert text.count(anchor) == 1, (
        f"anchor in {os.path.basename(path)} is not unique (found {text.count(anchor)}) — "
        f"refusing to mutate blindly")
    open(path, "wb").write(text.replace(anchor, mutant, 1).encode("utf-8"))
    return original


def main():
    before = sha256(GATE)
    out = ["WO-058 §2.3 BITE PROOF — THE TERM 2 GATE READS FLOW, NOT STOCK.",
           "FIXTURES ONLY. Four artifacts, sha256 exact-restore.",
           "ONE mutation: gate on STOCK instead of FLOW — WO-057's criterion, restored.",
           f"  capture_gate.py sha256 BEFORE : {before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; nothing failed")

    original = _mutate(GATE, ANCHOR, MUTANT)
    try:
        out += ["  MUTATION: flow_green = (stock_bytes == 0)  — the STOCK criterion", ""]
        d2 = digest(*run_tests())
    finally:
        open(GATE, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION (gating on STOCK)", d2,
                 "the pre-ruled DUAL fails (zero flow + large stock now reads RED) while the BITE "
                 "still passes — both criteria reject a genuinely paging host, so only the dual "
                 "tells them apart")

    d3 = digest(*run_tests())
    out += block("ARTIFACT 3 — RESTORED", d3, "returncode 0; nothing failed")

    after = sha256(GATE)
    exact = after == before
    out += ["-- sha256 EXACT-RESTORE --",
            f"  capture_gate.py AFTER : {after}",
            f"  IDENTICAL             : {exact}", ""]

    live = _live_reading()
    out += ["-- ARTIFACT 4 — THIS HOST, MEASURED (the pre-ruled case, live) --"]
    out += [f"  {line}" for line in live["lines"]]
    out += ["  EXPECT: the very configuration the dual describes — zero flow, non-zero stock", ""]

    dual_ok = bool(d2["dual_failed"])
    bite_holds = not d2["bite_failed"]
    out += [f"  DUAL fails under stock-gating (the pre-ruled case) : {dual_ok}",
            f"  BITE still passes under stock-gating              : {bite_holds}",
            "",
            "  ── WHY THE ASYMMETRY IS THE PROOF ───────────────────────────────────────────────",
            "  A genuinely paging host is RED under BOTH criteria, so the bite cannot distinguish",
            "  them. The dual is the only test that separates 'the host is paging' from 'the host",
            "  is holding pagefile bytes it is not reading' — and that distinction is exactly what",
            "  made a runnable capture look impossible twice.",
            "",
            "  §0.10 BROAD TESTS EXCLUDED from the discrimination sets and reported separately.",
            ""]

    ok = (d1["returncode"] == 0 and not d1["dual_failed"] and not d1["bite_failed"]
          and d2["returncode"] != 0 and dual_ok and bite_holds
          and d3["returncode"] == 0 and not d3["dual_failed"]
          and exact)
    out += [f"VERDICT: {'PASS' if ok else 'FAIL'}"]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    assert exact, "GATE NOT RESTORED — aborting"
    return 0 if ok else 1


def _live_reading():
    """One real reading of both quantities on this host. No socket; performance counter + psutil."""
    sys.path.insert(0, os.path.join(REPO, "src"))
    import psutil

    from trading.data import capture_gate

    flow = capture_gate.read_paging_flow()
    stock_mib = psutil.swap_memory().used / (1024 ** 2)
    free_mib = psutil.virtual_memory().available / (1024 ** 2)
    return {
        "lines": [
            f"FLOW  ({capture_gate.PAGING_FLOW_COUNTER}) : "
            f"{'unreadable' if flow is None else f'{flow:.2f} pages/sec'}   <- GATES",
            f"STOCK (swap bytes in use)          : {stock_mib:.0f} MiB          <- CONTEXT ONLY",
            f"FREE  memory                       : {free_mib:.0f} MiB "
            f"(floor {capture_gate.MIN_FREE_MEMORY_MIB:.0f})",
        ],
        "ok": True,
    }


if __name__ == "__main__":
    raise SystemExit(main())
