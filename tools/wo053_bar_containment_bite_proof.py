"""WO-053 §3.1 BITE PROOF — a bar never spans a gap. Four artifacts, sha256 exact-restore.

    python tools/wo053_bar_containment_bite_proof.py

THE PROPERTY. A bar is built from the frames of exactly ONE segment. A bar that straddled a gap
would average a price from before a hole with one from after it and report the result as a
60-second observation — the splice defect (D20) reappearing one layer ABOVE the default-deny
reader, where the reader cannot see it.

THE MUTATION (as specified by §3.1): remove the boundary check from `SegmentBarBuilder.add`.

  BITE — the two containment tests must FAIL: a frame two hours outside the segment is silently
      bucketed instead of refused, so a gap-spanning bar becomes constructible.

  DUAL — the tests for legitimate in-segment bars must still PASS under the mutation. This is the
      measurement that makes the bite mean something: a builder that refused EVERYTHING would fail
      the bite tests too, and a proof that only checked "something failed" could not tell the two
      apart. `dual_failed` is tracked in every artifact and must be empty in all four.

  NECESSITY — the mutation is removal of exactly one check. Under it the DUAL still passes and the
      BITE fails, so the check is doing precisely the work claimed for it and no more: it is
      necessary for containment and irrelevant to normal bar construction.

WHY THE SECOND MECHANISM DOES NOT RESCUE IT (worth stating, because it looks like it should).
Bars are also anchored per segment, which makes a gap-spanning bucket hard to EXPRESS. But
alignment is arithmetic on a timestamp, and arithmetic never complains: given a foreign frame it
computes a bucket index and carries on. That is exactly why the explicit refusal exists, and why
removing it must be observable. If the mutation did NOT bite, the alignment would be carrying the
guarantee alone and the check would be decoration.

§0.10 — the discrimination sets hold only single-purpose tests. Exclusions recorded below.

Writes to .artifacts/ (WO-032 §4.1).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARS = os.path.join(REPO, "src", "trading", "data", "bars.py")
TESTS = "tests/test_bars.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo053_bar_containment_bite_proof")

# ── THE MUTATION: the boundary check is removed ───────────────────────────────────────────────
ANCHOR = [
    "        if ts < self._segment.start_utc or ts > self._segment.end_utc:",
]
MUTANT = [
    "        if False:   # MUTATED: boundary check removed — foreign frames now bucket silently",
]

# SINGLE-PURPOSE sets (§0.10).
BITE_SET = {
    "test_bite_a_frame_from_outside_the_segment_is_refused",
    "test_bite_a_frame_before_the_segment_start_is_refused",
}
DUAL_SET = {
    "test_dual_a_bar_entirely_inside_a_segment_builds_normally",
    "test_dual_every_frame_of_a_full_segment_is_accepted",
    "test_partial_trailing_bar_is_discarded_never_emitted",
    "test_bar_ohlc_reflects_the_frames_it_contains",
    "test_bars_are_aligned_to_the_segment_not_the_wall_clock_epoch",
}
# BROAD / UNRELATED — excluded from the discrimination sets and reported for visibility (§0.10).
# The signal and parameter tests never touch the bar builder's bounds, so they attribute nothing
# about containment either way.
BROAD_SET = {
    "test_threshold_is_the_registered_multiple_of_the_round_trip_cost",
    "test_registered_parameters_are_exactly_as_pre_registered",
    "test_u4_the_first_closed_bar_of_a_segment_cannot_trade",
    "test_u4_dual_the_second_closed_bar_can_trade",
}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _nl(t):
    return "\r\n" if "\r\n" in t else "\n"


def run_tests():
    p = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS.split(), "-p", "no:randomly", "-v",
         "--tb=line", "-q"],
        cwd=REPO, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    failed_lines = [line for line in out.splitlines() if "FAILED" in line]
    failed = {f.split("::")[-1] for f in re.findall(r"(test_[\w\[\]\.\-]+)",
                                                    "\n".join(failed_lines))}
    passed = set(re.findall(r"(test_\w+)\s+PASSED", out))
    return {
        "returncode": rc,
        "summary": next((line.strip() for line in reversed(out.splitlines())
                         if re.search(r"\d+ (passed|failed)", line)), "(no summary)"),
        "bite_failed": sorted(failed & BITE_SET),
        "dual_failed": sorted(failed & DUAL_SET),
        "dual_passed": len(passed & DUAL_SET),
        "broad_failed": sorted(failed & BROAD_SET),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<14} {v}")
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
    before = sha256(BARS)
    out = ["WO-053 §3.1 BITE PROOF — A BAR NEVER SPANS A GAP.",
           "Four artifacts, sha256 exact-restore. One mutation: the boundary check is removed.",
           f"  bars.py sha256 BEFORE : {before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; nothing failed")

    original = _mutate(BARS, ANCHOR, MUTANT)
    try:
        out += ["  MUTATION: SegmentBarBuilder.add's BAR_FRAME_OUTSIDE_SEGMENT check removed", ""]
        d2 = digest(*run_tests())
    finally:
        open(BARS, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION (a gap-spanning bar becomes constructible)", d2,
                 "BOTH bite tests fail (a foreign frame is silently bucketed); the DUAL still "
                 "passes, proving the check is necessary for containment and irrelevant to "
                 "normal bar construction")

    d3 = digest(*run_tests())
    out += block("ARTIFACT 3 — RESTORED", d3, "returncode 0; nothing failed")

    after = sha256(BARS)
    exact = after == before
    out += ["-- sha256 EXACT-RESTORE --",
            f"  bars.py AFTER : {after}",
            f"  IDENTICAL     : {exact}", ""]

    # ARTIFACT 4 — the property demonstrated DIRECTLY, not only through the suite: build a bar from
    # frames that straddle a two-hour hole and show the refusal is what stops it.
    direct = _direct_demonstration()
    out += ["-- ARTIFACT 4 — DIRECT DEMONSTRATION (the economic object, not the test result) --"]
    out += [f"  {line}" for line in direct["lines"]]
    out += [f"  EXPECT: the builder REFUSES; no Bar object spanning the hole is ever constructed",
            ""]

    bites = sorted(BITE_SET) == d2["bite_failed"]
    dual_holds = not d2["dual_failed"]
    out += [f"  MUTATION bites (BOTH containment tests fail) : {bites}",
            f"  DUAL holds under the mutation               : {dual_holds} "
            f"({d2['dual_passed']}/{len(DUAL_SET)} passed)",
            f"  DIRECT demonstration refused                : {direct['refused']}",
            "",
            "  §0.4 THE DUAL IS LOCAL AND DIRECT: `dual_failed` is tracked in every artifact and is",
            "  empty in all of them. A builder that refused every frame would fail the bite tests",
            "  too — the dual is what distinguishes containment from breakage.",
            "",
            "  §0.10 BROAD/UNRELATED TESTS EXCLUDED from the discrimination sets: the signal and",
            "  registered-parameter tests never touch the builder's bounds and attribute nothing.",
            ""]

    ok = (d1["returncode"] == 0 and not d1["bite_failed"] and not d1["dual_failed"]
          and d2["returncode"] != 0 and bites and dual_holds
          and d3["returncode"] == 0 and not d3["bite_failed"]
          and direct["refused"] and exact)
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


def _direct_demonstration():
    """Construct the actual splice attempt on the RESTORED tree and record what happens."""
    sys.path.insert(0, os.path.join(REPO, "src"))
    from datetime import timedelta
    from decimal import Decimal

    from trading.data.bars import BarError, SegmentBarBuilder
    from trading.data.book_state import BookState
    from trading.data.corpus_reader import Segment

    t0 = datetime(2026, 8, 5, 22, 0, 0, tzinfo=timezone.utc)

    def frame(offset, mid):
        m = Decimal(mid)
        return BookState(timestamp=t0 + timedelta(seconds=offset), symbol="BTC/USD",
                         best_bid=m - Decimal("0.5"), best_ask=m + Decimal("0.5"),
                         best_bid_size=Decimal("1"), best_ask_size=Decimal("1"))

    seg = Segment(start_utc=t0, end_utc=t0 + timedelta(seconds=300), run_id="20260805220327")
    b = SegmentBarBuilder(0, seg, 60)
    b.add(frame(0, "64000"))
    lines = ["segment  : [22:00:00 .. 22:05:00]  (bar interval 60s)",
             "frame A  : 22:00:00  mid 64000   -> accepted, opens bar 0",
             "frame B  : 00:00:00 (+2h)  mid 71000   -> the far side of the 2.1h seam"]
    try:
        b.add(frame(7200, "71000"))
        lines.append("RESULT   : ACCEPTED — a bar now mixes prices across a two-hour hole")
        return {"lines": lines, "refused": False}
    except BarError as e:
        lines.append(f"RESULT   : REFUSED — {str(e).splitlines()[0][:96]}")
        lines.append("           no Bar spanning the hole was constructed")
        return {"lines": lines, "refused": True}


if __name__ == "__main__":
    raise SystemExit(main())
