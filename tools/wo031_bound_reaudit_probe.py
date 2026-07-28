"""WO-031 §3-bis — RE-AUDIT INSTRUMENT for the suspect audit BOUND.

`test_incremental_persist_survives_unhandled_exception_mid_capture` is filed by the WO-023 audit
among the 7 legitimate BOUNDS (entries 31-37, NOT races) with the justification
`dur=0.25, injected crash ends it`. WO-032's CI leg observed it flinch on injected clock RATE.

D39 says the category comes from the CLASSIFICATION — enumerate the reads, name the assertion — NOT
from a differential observation. This instrument supplies the mechanical half of that classification:
it shows WHICH read the divergence flows from and HOW FAR the run got before the deadline cut it.

WHY THE READ IS PINNED, not guessed: `AdvancingClock` advances its counter on every MONOTONIC read,
and the adapter routes `_monotonic_clock` to exactly three sites —
    kraken_v2_book.py:2548   deadline = self._monotonic_clock() + duration_seconds
    kraken_v2_book.py:2594   while self._monotonic_clock() < deadline
    kraken_v2_book.py:2727   remaining = deadline - self._monotonic_clock()
— all three the DEADLINE seam, all INJECTABLE post-WO-023/WO-030. Every other real-clock read on the
path is raw `time.monotonic()`/`time.time()`, which this fixture does not touch at all. So a behaviour
change under the fixture CANNOT flow from a non-injectable read.

The frames-reached counters below turn that from an argument into a measurement: they show the run
ending EARLIER in the script as the clock advances faster.

    python tools/wo031_bound_reaudit_probe.py

Writes to .artifacts/ (WO-032 §4.1 — a tools/ script never writes under evidence/).
"""
import asyncio
import copy
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)

ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo031_bound_reaudit")

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter          # noqa: E402
from tests.fixtures.fake_ws_transport import (                               # noqa: E402
    AdvancingClock, ScriptedConnectionFactory,
)
from tests.fixtures.kraken_v2_raw_frames import (                            # noqa: E402
    SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL,
)

DURATION = 0.25          # exactly what the test under audit uses


async def _no_sleep(_delay):
    return None


def build(path, clock):
    """The adapter the test builds, verbatim (test_ledger_persistence.py::_live_adapter + script)."""
    corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
    corrupted["data"][0]["bids"][0]["price"] = "45283.7"     # real checksum failure -> gap opens
    crash = RuntimeError("injected unhandled crash mid-capture")
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, corrupted, crash], "on_drain": "block"},
    ])
    kw = {"monotonic_clock": clock.monotonic} if clock is not None else {}
    a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory.connect, **kw)
    if clock is not None:
        a._wall_clock = clock.wall            # coherent partner, shared token (batch-A pattern)
    a._reconnect_sleep = _no_sleep
    a._heartbeat_absence_timeout = 100.0
    a._app_ping_interval = 100.0
    a._gap_persist_path = str(path)
    return a, factory


async def run_once(path, clock):
    a, factory = build(path, clock)
    raised, emitted = None, 0
    try:
        async for _ in a.get_live_market_data(duration_seconds=DURATION):
            emitted += 1
    except RuntimeError as e:
        raised = str(e)
    ledger = a.get_gap_ledger()
    return {
        "raised": raised,
        "emitted": emitted,
        # HOW FAR INTO THE SCRIPT the run got — frame 2 is the corrupted update (opens the gap),
        # frame 3 is the crash. This is the measurement that localises where the deadline cut.
        "frame2_reached (checksum failure seen)": a.get_checksum_failure_count() >= 1,
        "gap_opened": (ledger.gaps_detected if ledger else 0),
        "frame3_reached (crash propagated)": raised is not None,
        "capture_terminated": a.capture_terminated,
    }


def main():
    import tempfile
    tmp = tempfile.mkdtemp()
    out = [
        "WO-031 §3-bis — RE-AUDIT of an audit BOUND: "
        "test_incremental_persist_survives_unhandled_exception_mid_capture",
        f"Audit filing: 7 legitimate BOUNDS, entry `test_ledger_persistence.py:82`, "
        f"justification \"dur={DURATION}, injected crash ends it\".",
        "",
        "The script is [SNAPSHOT, corrupted(checksum fail), RuntimeError]; on_drain=block.",
        "The test's observing assertion is `pytest.raises(RuntimeError, match=...)`, which requires",
        "the loop to DRAIN FRAME 3 before the deadline guard exits the while loop.",
        "",
        "AdvancingClock advances ONLY on monotonic reads; `_monotonic_clock` is used at exactly three",
        "sites (kraken_v2_book.py:2548 set, :2594 guard, :2727 recv-timeout) — all the DEADLINE seam,",
        "all INJECTABLE. No non-injectable read is touched by this fixture, so any divergence below is",
        "attributable to the deadline read and to nothing else.",
        "",
    ]

    rows = [
        ("real clock (what CI runs)", None),
        ("AdvancingClock(delta=0.2)", AdvancingClock(delta=0.2)),
        ("AdvancingClock(delta=0.05)", AdvancingClock(delta=0.05)),
        ("AdvancingClock(delta=0.01)", AdvancingClock(delta=0.01)),
        ("AdvancingClock(delta=0.0001)", AdvancingClock(delta=0.0001)),
    ]
    results = []
    for i, (label, clk) in enumerate(rows):
        r = asyncio.run(run_once(os.path.join(tmp, f"{i}.jsonl"), clk))
        results.append((label, r))
        out.append(f"-- {label} --")
        for k, v in r.items():
            out.append(f"     {k:<38} {v}")
        out.append("")

    fired = [lab for lab, r in results if not r["frame3_reached (crash propagated)"]]
    reached = [lab for lab, r in results if r["frame3_reached (crash propagated)"]]
    out += [
        "CONCLUSION",
        f"  crash NOT reached (deadline ended the run first) : {fired}",
        f"  crash reached (the audit's assumed path)         : {reached}",
        "",
        "  The outcome the test asserts (`pytest.raises(RuntimeError)`) flips purely on the rate of",
        "  an INJECTABLE deadline read. The audit's justification — 'injected crash ends it' — holds",
        "  only when the loop wins a race against the deadline; it is not a property of the script.",
        "  => the deadline read is OUTCOME-BEARING for this test (D39), i.e. this is a RACE, and",
        "     because the read is INJECTABLE it is CLOCK-INJECTABLE/CONVERTIBLE, not NOT-YET.",
        "",
        "  DENOMINATOR CONSEQUENCE: clock-injectable 26 -> 27. This ESCALATES to the lead (§3-bis);",
        "  it is NOT folded into a batch by this WO.",
    ]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
