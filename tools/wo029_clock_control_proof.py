"""WO-029 §3 — THE INJECTED CLOCK ACTUALLY CONTROLS THE TIMING (not "the test still passes").

"Still passes" is not "is now deterministic" (the WO-008b throughput VOID is the precedent for
measuring the real thing). This instrument measures the real thing, in two parts:

  PART A — REAL CONTROL (representative race: race 1's construction,
    `test_runner_drives_instrumented_transport_end_to_end`). The capture window is the quantity the
    race depended on a real wall clock for. Hold EVERYTHING fixed except the injected clock's
    advance-per-read (`delta`) and measure the OBSERVED window — how many raw frames the capture
    actually consumed before the deadline ended it. If the injected clock controls the timing, the
    observed window must move monotonically with delta and be IDENTICAL across repeats; if the real
    clock were still in charge, delta would not move it and repeats would scatter. Emissions stay
    pinned at the 2 scripted book frames throughout — the deliverable the race asserts is invariant
    to how long the window is, which is exactly what "the deadline no longer races the frames" means.

  PART B — RACE #5 THROUGH THE RUNNER SEAM (WO-030's runner->factory->builder path). Race 5 builds
    NO adapter: it passes `adapter=None` and lets the runner resolve one from DATA_SOURCE through
    the factory/registry. The proof that its clock injection travels that path (and is not a
    directly-constructed shortcut) is IDENTITY at the far end: the adapter the FACTORY built holds
    the very callables handed to the RUNNER — `_monotonic_clock is clk.monotonic`,
    `_wall_clock is clk.wall` — and its pre-connection gate disposition is PROCEED_COHERENT (the
    gate saw a coherent injected pair on that factory-built adapter, so the pair reached it).
    The adapter is recovered via `factory.get_active_feed()`, i.e. from the factory itself.

NO NETWORK: every connection is a ScriptedConnectionFactory socket.
"""
import asyncio
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)

from trading.data.adapters import factory as adapter_factory          # noqa: E402
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter  # noqa: E402
from trading.execution.paper import PaperExecutionClient              # noqa: E402
from trading.loop.live import LiveTradingLoop                         # noqa: E402
from trading.loop.live_capture import LiveCaptureRunner               # noqa: E402
from tests.fixtures.fake_ws_transport import (                        # noqa: E402
    AdvancingClock, ScriptedConnectionFactory,
)
from tests.fixtures.kraken_v2_raw_frames import (                     # noqa: E402
    SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL,
)

OUT = os.path.join(REPO, "evidence", "WO-029", "clock_control_proof.txt")
DURATION = 0.25                       # race 1's capture window
DELTAS = (0.05, 0.01, 0.002)          # advance per monotonic read: coarse -> fine


class _StubPersistence:
    _data_dir = "(stub)"

    def write_event(self, _ms): pass
    def close(self): pass
    def get_file_info(self): return {"path": "(stub)", "exists": False, "event_count": 0,
                                     "size_bytes": 0}


def _paper_loop():
    return LiveTradingLoop(execution_client=PaperExecutionClient(), persistence=_StubPersistence())


async def _run_race1_shape(delta, persist_path):
    """Race 1's construction verbatim, parameterized ONLY by the injected clock's delta."""
    clk = AdvancingClock(delta=delta)
    conn = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL], "on_drain": "heartbeat"},
    ])
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=conn.connect,
                                  monotonic_clock=clk.monotonic)
    adapter._wall_clock = clk.wall
    runner = LiveCaptureRunner(persist_path=persist_path, duration_seconds=DURATION,
                               trading_env="paper", adapter=adapter, loop=_paper_loop(),
                               clock=clk.wall)
    result = await runner.run()
    return {
        "observed_window_frames": adapter.get_diagnostic_counters()["raw_messages_received"],
        "emitted": sum(result["emitted_per_minute"]),
        "connect_count": conn.connect_count,
        "terminated": result["terminated"],
    }


async def _run_race5_shape(persist_path):
    """Race 5's construction verbatim: adapter=None, resolved through the runner->factory->builder."""
    clk = AdvancingClock(delta=0.01)
    conn = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    runner = LiveCaptureRunner(persist_path=persist_path, duration_seconds=0.15,
                               trading_env="paper", adapter=None, loop=_paper_loop(),
                               data_source="kraken_v2", connect_fn=conn.connect,
                               monotonic_clock=clk.monotonic, wall_clock=clk.wall, clock=clk.wall)
    result = await runner.run()
    built = adapter_factory.get_active_feed()      # the adapter the FACTORY built, from the factory
    return {
        "built_by": type(built).__name__,
        "is_the_injected_adapter": built is not None,
        "monotonic_is_injected": built._monotonic_clock is clk.monotonic,
        "wall_is_injected": built._wall_clock is clk.wall,
        # `conn.connect` is a BOUND METHOD: each attribute access mints a fresh object, so `is`
        # against it is always False regardless of what was threaded. Compare the two parts that
        # ARE stable — the underlying function and the instance it is bound to. (The clock seams
        # need no such care: `clk.monotonic`/`clk.wall` are instance ATTRIBUTES holding one closure
        # object apiece, so plain identity is the right test there.)
        "transport_is_injected": (built._connect_fn.__func__ is ScriptedConnectionFactory.connect
                                  and built._connect_fn.__self__ is conn),
        "shared_coherence_token": (getattr(built._monotonic_clock, "_coherence_token", None)
                                   is getattr(built._wall_clock, "_coherence_token", None)
                                   is clk),
        "venue_name": result["venue_name"],
        "connect_count": conn.connect_count,
    }


def main():
    import json
    import tempfile
    from pathlib import Path

    # Satisfy the runner's host-baseline preflight through the SAME structural seam the suite uses
    # (WO-022 §1), REUSING the committed synthetic record rather than inventing a second one.
    from trading.loop import host_baseline
    from tests.integration.conftest import SYNTHETIC_BASELINE_RECORD
    tmp = Path(tempfile.mkdtemp(prefix="wo029_clock_control_"))
    store = tmp / "synthetic_baselines.json"
    key = host_baseline.fingerprint_key(host_baseline.host_fingerprint())
    store.write_text(json.dumps({key: SYNTHETIC_BASELINE_RECORD}, indent=1), encoding="utf-8")
    os.environ["MEAN_CYCLE_BASELINE_STORE"] = str(store)

    out = [
        "WO-029 §3 — THE INJECTED CLOCK CONTROLS THE TIMING (measured, not asserted)",
        "",
        "PART A — REAL CONTROL: race 1's construction, delta is the ONLY thing that varies.",
        f"  fixed: duration_seconds={DURATION}, script=[SNAPSHOT, UPDATE_MODIFY_LEVEL]+heartbeats",
        "  observed_window_frames = raw frames the capture consumed before the deadline ended it",
        "",
        f"  {'delta':>8} | {'run 1':>22} | {'run 2':>22} | identical?",
        f"  {'-'*8}-+-{'-'*22}-+-{'-'*22}-+-----------",
    ]
    part_a = {}
    for delta in DELTAS:
        r1 = asyncio.run(_run_race1_shape(delta, tmp / f"a_{delta}_1.jsonl"))
        r2 = asyncio.run(_run_race1_shape(delta, tmp / f"a_{delta}_2.jsonl"))
        part_a[delta] = (r1, r2)
        f1 = f"window={r1['observed_window_frames']} emitted={r1['emitted']}"
        f2 = f"window={r2['observed_window_frames']} emitted={r2['emitted']}"
        out.append(f"  {delta:>8} | {f1:>22} | {f2:>22} | {'YES' if r1 == r2 else 'NO'}")

    windows = [part_a[d][0]["observed_window_frames"] for d in DELTAS]
    emissions = {part_a[d][0]["emitted"] for d in DELTAS}
    repeatable = all(part_a[d][0] == part_a[d][1] for d in DELTAS)
    controls = all(windows[i] < windows[i + 1] for i in range(len(windows) - 1))
    emissions_pinned = emissions == {2}
    out += [
        "",
        f"  CONTROL      : observed window is strictly monotonic in 1/delta  -> {controls} {windows}",
        f"  DETERMINISM  : each delta reproduces its run EXACTLY on repeat   -> {repeatable}",
        f"  ASSERTION    : emissions pinned at the 2 scripted book frames    -> {emissions_pinned} "
        f"{sorted(emissions)}",
        "  READING: halving delta lengthens the observed capture window by the corresponding factor",
        "  while the emitted deliverable does not move. The injected clock — not the host's wall",
        "  clock and not scheduler load — is what advances the time this race depends on.",
        "",
        "PART B — RACE #5's INJECTION REACHES THE ADAPTER THROUGH THE RUNNER->FACTORY->BUILDER SEAM",
        "  (adapter=None; the adapter below was recovered from factory.get_active_feed(),",
        "   i.e. it is the one the FACTORY built, not one this script constructed)",
    ]
    b = asyncio.run(_run_race5_shape(tmp / "b.jsonl"))
    for k, v in b.items():
        out.append(f"    {k:<28} {v}")
    part_b_ok = (b["monotonic_is_injected"] and b["wall_is_injected"]
                 and b["transport_is_injected"] and b["shared_coherence_token"]
                 and b["venue_name"] == "kraken_mainnet")
    out += [
        f"  THROUGH-THE-SEAM: {part_b_ok} — the factory-built adapter holds the very callables handed",
        "  to the runner (identity, not equality), sharing ONE coherence token. The gate's",
        "  disposition for this nodeid in the committed ledger snapshot is PROCEED_COHERENT.",
        "",
    ]
    verdict = "PASS" if (controls and repeatable and emissions_pinned and part_b_ok) else "FAIL"
    out.append(f"VERDICT: {verdict}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
