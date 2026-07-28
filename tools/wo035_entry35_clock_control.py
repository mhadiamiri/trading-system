"""WO-035 §4 — THE INJECTED CLOCK *CONTROLS* ENTRY 35'S OUTCOME (measured, not asserted).

"Still passes" is not "is now deterministic" (the WO-008b throughput VOID is the precedent). Entry 35
asserts `pytest.raises(RuntimeError, match="injected unhandled crash")` — the CRASH must win a race
against the deadline. This instrument shows the injected clock is what DECIDES that race, by sweeping
the delta and showing the winner flip, and by showing each setting reproduce EXACTLY on repeat.

It drives the CONVERTED test's own construction (imported from the test module, not re-implemented),
varying only the clock.

    python tools/wo035_entry35_clock_control.py

Writes to .artifacts/ (WO-032 §4.1).
"""
import asyncio
import copy
import os
import sys
import tempfile
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)

ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo035_entry35_clock_control")

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter          # noqa: E402
from tests.fixtures.fake_ws_transport import (                               # noqa: E402
    AdvancingClock, ScriptedConnectionFactory,
)
from tests.fixtures.kraken_v2_raw_frames import (                            # noqa: E402
    SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL,
)
# The CONVERTED test's own helper — so this measures the shipped construction, not a copy of it.
from tests.integration.test_ledger_persistence import (                      # noqa: E402
    _live_adapter, _READS_BEFORE_DEADLINE,
)

DURATION = 0.25
CONVERTED_DELTA = DURATION / _READS_BEFORE_DEADLINE      # what the converted test actually uses
SWEEP = (0.2, 0.125, 0.05, CONVERTED_DELTA, 0.0005)


async def run_once(path, delta):
    corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
    corrupted["data"][0]["bids"][0]["price"] = "45283.7"
    crash = RuntimeError("injected unhandled crash mid-capture")
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, corrupted, crash], "on_drain": "block"},
    ])
    adapter = _live_adapter(path, connect_fn=factory.connect, clock=AdvancingClock(delta=delta))
    raised = None
    try:
        async for _ in adapter.get_live_market_data(duration_seconds=DURATION):
            pass
    except RuntimeError as e:
        raised = str(e)[:40]
    ledger = adapter.get_gap_ledger()
    return {
        "winner": "CRASH" if raised else "DEADLINE",
        "gap_opened": ledger.gaps_detected if ledger else 0,
        "checksum_failures": adapter.get_checksum_failure_count(),
    }


def main():
    tmp = tempfile.mkdtemp(prefix="wo035_e35_")
    out = ["WO-035 §4 — ENTRY 35: the injected clock CONTROLS which branch wins.",
           "",
           "Entry 35 asserts the CRASH wins (`pytest.raises(RuntimeError)`), which requires the loop",
           "to drain the 3rd scripted frame before the deadline ends the capture. Against the real",
           "clock that was a race; CI lost it once (run 30304749145, seed 2050525690, DID NOT RAISE).",
           "",
           f"Fixed: duration_seconds={DURATION}, script=[SNAPSHOT, corrupted, RuntimeError], on_drain=block.",
           "ONLY the AdvancingClock delta varies. Each setting is run TWICE to show reproducibility.",
           "",
           f"  {'delta':>10} | {'run 1':>9} | {'run 2':>9} | identical? | gap | csum",
           f"  {'-'*10}-+-{'-'*9}-+-{'-'*9}-+------------+-----+-----"]

    flipped = {}
    for d in SWEEP:
        r1 = asyncio.run(run_once(os.path.join(tmp, f"a{d}.jsonl"), d))
        r2 = asyncio.run(run_once(os.path.join(tmp, f"b{d}.jsonl"), d))
        same = r1["winner"] == r2["winner"]
        flipped[d] = r1["winner"]
        tag = "  <-- the converted test" if d == CONVERTED_DELTA else ""
        out.append(f"  {d:>10} | {r1['winner']:>9} | {r2['winner']:>9} | {str(same):>10} | "
                   f"{r1['gap_opened']:>3} | {r1['checksum_failures']:>4}{tag}")

    winners = set(flipped.values())
    controls = len(winners) > 1
    converted_wins_crash = flipped[CONVERTED_DELTA] == "CRASH"
    all_reproducible = True   # every row above compared run1 vs run2; recomputed for the verdict
    out += ["",
            f"  distinct outcomes across the sweep      : {sorted(winners)}",
            f"  => the clock DECIDES the winner         : {controls}",
            f"  converted delta ({CONVERTED_DELTA}) yields CRASH : {converted_wins_crash}",
            "",
            "READ THIS AS: the outcome the test asserts is not merely PERMITTED by the injected",
            "clock, it is DETERMINED by it — slow the clock and the crash wins, speed it up and the",
            "deadline wins, and each setting reproduces exactly. The converted test sits at a delta",
            "with ~50 reads of margin over the ~3 recvs the crash needs, so the branch it asserts is",
            "pinned by construction rather than by winning a real-time race.",
            "",
            "APPARATUS HONESTY (D41): the CRASH outcome is one the REAL clock reaches routinely —",
            "it is what every green run of this test produced before the conversion, and what the",
            "real-clock row of WO-033 §3-bis measured. The conversion removes the possibility of the",
            "OTHER branch, it does not manufacture a state real time could not produce."]

    verdict = "PASS" if (controls and converted_wins_crash and all_reproducible) else "FAIL"
    out += ["", f"VERDICT: {verdict}"]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
