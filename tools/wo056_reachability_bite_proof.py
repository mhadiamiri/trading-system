"""WO-056 §8 BITE PROOF — THE REACHABILITY WITNESS. Four artifacts, sha256 exact-restore.

    python tools/wo056_reachability_bite_proof.py

FIXTURES ONLY. No socket opens in this WO under any circumstance.

WHAT IS BEING PROVED, AND WHY IT IS NOT AN ORDINARY BITE PROOF
--------------------------------------------------------------
An ordinary bite proof shows a guard fires when the thing it guards breaks. This one shows
something sharper, ruled by D55: **that the existing tests were structurally incapable of seeing
the defect at all.**

WO-054 shipped `trade_channel.py` with 22 tests and its own passing bite proof, on green CI, both
interpreters, both orders — and nothing in the production path called any of it. Every one of those
22 tests enters AT THE COMPONENT, so every one of them passed while the component was unreachable.

THE MUTATION: restore `if raw_frame.get("channel") != "book": return []` — the discard that made
the trade channel unreachable, exactly as it stood at WO-055.

THE ASYMMETRY IS THE FINDING:

    reachability witness (enters at tools/live_corpus_capture.py)  ->  FAILS
    trade_channel unit tests (enter at TradeMerger/parse_*)        ->  ALL 22 STILL PASS

If both sets failed, the mutation would just be "a broken build" and would prove nothing about
where the blindness lived. If both passed, the witness would be decoration. Only the asymmetry
demonstrates that the unit tests were blind to non-reachability and that the witness is not.

THE DUAL (§4.2, ruled explicitly by D55): the BOOK path must not degrade. Under the mutation the
book frames still write their seven original fields — proving the mutation removed *reachability of
the trade channel* and nothing else, so the witness's failure is attributable to that and not to a
generally broken capture.

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
ADAPTER = os.path.join(REPO, "src", "trading", "data", "adapters", "kraken_v2_book.py")
WITNESS = "tests/test_trade_capture_wiring.py"
COMPONENT = "tests/test_trade_channel.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo056_reachability_bite_proof")

# ── THE MUTATION: the WO-055 discard, restored ───────────────────────────────────────────────
ANCHOR = [
    "        self._demux_non_book(raw_frame)",
]
MUTANT = [
    '        if raw_frame.get("channel") != "book":   # MUTATED: the WO-055 discard, restored',
    "            return []",
]

# SINGLE-PURPOSE sets (§0.10).
WITNESS_BITE = {
    "test_bite_a_trade_stream_reaches_the_written_corpus_frames",
    "test_bite_the_traded_volume_is_the_sum_over_the_interval",
}
# The book path's preservation dual — must hold UNDER the mutation (§4.2).
WITNESS_DUAL = {
    "test_dual_a_book_only_stream_still_writes_the_seven_original_fields",
}
# BROAD — excluded from the discrimination sets and reported for visibility (§0.10). These read
# both the trades sub-object and the ack state at once, so they attribute nothing on their own.
BROAD = {
    "test_dual_no_trades_records_a_positive_claim_of_zero",
    "test_without_an_ack_the_corpus_says_it_could_not_see",
    "test_transport_chatter_does_not_become_market_data",
    "test_an_unrecognised_channel_does_not_corrupt_the_frame",
    "test_a_nacked_subscribe_records_a_declared_outage",
}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _nl(t):
    return "\r\n" if "\r\n" in t else "\n"


def run(target):
    p = subprocess.run(
        [sys.executable, "-m", "pytest", target, "-p", "no:randomly", "-v", "--tb=line", "-q"],
        cwd=REPO, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    failed_lines = [line for line in out.splitlines() if "FAILED" in line]
    failed = {f.split("::")[-1] for f in re.findall(r"(test_[\w\[\]\.\-]+)",
                                                    "\n".join(failed_lines))}
    summary = next((line.strip() for line in reversed(out.splitlines())
                    if re.search(r"\d+ (passed|failed)", line)), "(no summary)")
    return {"returncode": rc, "summary": summary, "failed": failed}


def snapshot():
    """Run BOTH suites and report each separately — the asymmetry is the measurement."""
    wrc, wout = run(WITNESS)
    crc, cout = run(COMPONENT)
    w, c = digest(wrc, wout), digest(crc, cout)
    return {
        "witness_returncode": w["returncode"],
        "witness_summary": w["summary"],
        "witness_bite_failed": sorted(w["failed"] & WITNESS_BITE),
        "witness_dual_failed": sorted(w["failed"] & WITNESS_DUAL),
        "witness_broad_failed": sorted(w["failed"] & BROAD),
        "component_returncode": c["returncode"],
        "component_summary": c["summary"],
        "component_failed": sorted(c["failed"]),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<24} {v}")
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
    before = sha256(ADAPTER)
    out = ["WO-056 §8 BITE PROOF — THE REACHABILITY WITNESS (D55 / rule 0.14).",
           "FIXTURES ONLY — no socket opens in this WO.",
           "Four artifacts, sha256 exact-restore. ONE mutation: the WO-055 discard, restored.",
           f"  kraken_v2_book.py sha256 BEFORE : {before}", ""]

    d1 = snapshot()
    out += block("ARTIFACT 1 — PRISTINE", d1,
                 "both suites green; the witness sees the trades sub-object in written frames")

    original = _mutate(ADAPTER, ANCHOR, MUTANT)
    try:
        out += ['  MUTATION: process_raw_frame regains `if channel != "book": return []`',
                "            — trade_channel becomes unreachable from the production path", ""]
        d2 = snapshot()
    finally:
        open(ADAPTER, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION (the WO-055 state restored)", d2,
                 "THE ASYMMETRY: the WITNESS bite FAILS while ALL 22 COMPONENT TESTS STILL PASS. "
                 "The book-path DUAL also still passes, so the failure is attributable to lost "
                 "reachability and not to a generally broken capture.")

    d3 = snapshot()
    out += block("ARTIFACT 3 — RESTORED", d3, "both suites green again")

    after = sha256(ADAPTER)
    exact = after == before
    out += ["-- sha256 EXACT-RESTORE --",
            f"  kraken_v2_book.py AFTER : {after}",
            f"  IDENTICAL               : {exact}", ""]

    # ARTIFACT 4 — the reachability cell itself, asserted as a fact about the tree (0.14).
    call_site = _reachability_cell()
    out += ["-- ARTIFACT 4 — THE REACHABILITY CELL (0.14) --"]
    out += [f"  {line}" for line in call_site["lines"]]
    out += ["  EXPECT: a NAMED production call site, not an empty cell", ""]

    bite_ok = bool(d2["witness_bite_failed"])
    component_blind = (d2["component_returncode"] == 0 and not d2["component_failed"])
    dual_ok = not d2["witness_dual_failed"]
    out += [f"  WITNESS bites under the mutation                 : {bite_ok}",
            f"  COMPONENT TESTS STAY GREEN under the same mutation: {component_blind}",
            f"  BOOK-PATH DUAL holds under the mutation           : {dual_ok}",
            "",
            "  ── THE ASYMMETRY IS THE FINDING ────────────────────────────────────────────────",
            "  22 component tests + their own passing bite proof + green CI on both legs and both",
            "  orders ALL stayed green while trade_channel was unreachable, because every one of",
            "  them enters AT THE COMPONENT. The witness enters at tools/live_corpus_capture.py",
            "  and asserts the WRITTEN FRAME's contents, so it sees what they structurally cannot.",
            "",
            "  §4.2 THE PRESERVATION DUAL, ruled explicitly by D55: the book path still writes its",
            "  seven original fields under the mutation, which is what makes the witness's failure",
            "  ATTRIBUTABLE to lost reachability rather than to a broken capture.",
            "",
            "  §0.10 BROAD TESTS EXCLUDED from the discrimination sets and reported separately.",
            ""]

    ok = (d1["witness_returncode"] == 0 and d1["component_returncode"] == 0
          and d2["witness_returncode"] != 0 and bite_ok and component_blind and dual_ok
          and d3["witness_returncode"] == 0 and d3["component_returncode"] == 0
          and call_site["ok"] and exact)
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


def _reachability_cell():
    """0.14: name the production call site, and prove it is in the tree."""
    path = os.path.join(REPO, "tools", "live_corpus_capture.py")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    hits = [(i + 1, ln.strip()) for i, ln in enumerate(lines)
            if "adapter.trade_snapshot_for_frame(" in ln]
    out = ["thing            : trading.data.trade_channel (TradeMerger, ledger, schema)",
           "reached from     : tools/live_corpus_capture.py"]
    for lineno, text in hits:
        out.append(f"  call site      : live_corpus_capture.py:{lineno}  {text}")
    if not hits:
        out.append("  call site      : *** EMPTY — OPEN DEFECT (0.14) ***")
    return {"lines": out, "ok": bool(hits)}


if __name__ == "__main__":
    raise SystemExit(main())
