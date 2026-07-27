"""
WO-015 — the LIVE-CAPTURE RUNNER. Preflight refusals + end-to-end wiring, all on SIMULATED
transport (websockets.connect patched). NO real socket is opened here — that is the re-run's job.

WO-029 PASS TWO, BATCH A — this file converts WHOLE (audit races 1-5, the whole of batch A per
`evidence/WO-029/batch_partition.md`; no file is split across batches). Every one of the five drove
its capture window against the HOST'S REAL WALL CLOCK: `duration_seconds=0.15..0.25` raced the
scripted frames, so every in-window assertion gambled on scheduler load (the WO-023 §1 root cause).
Each now injects a COHERENT clock pair from ONE source (`AdvancingClock` — the FakeClock harness
made to move, WO-029 §2.0-bis) through the WO-023/028/030 seams, so the deadline is reached after a
FIXED number of clock reads rather than after a real interval. Termination is still the DEADLINE
(what races 1-5 always observed); only what advances toward it changed. The pre-connection gate
(WO-023 §4) is the live net: a coherent pair on an injected transport PROCEEDS, an incoherent one
REFUSES, so a wrong injection cannot pass silently — every conversion below is PROCEED_COHERENT in
the gate ledger. Measured, not asserted: `evidence/WO-029/clock_control_proof.txt`.
"""

import json

import pytest
from unittest.mock import patch
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedError

from trading.loop.live_capture import LiveCaptureRunner, LiveCaptureError
from trading.loop.live import LiveTradingLoop
from trading.execution.paper import PaperExecutionClient
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL
from tests.fixtures.fake_ws_transport import (
    AdvancingClock, ScriptedConnectionFactory, REOPEN_FAILURE,
)

# WO-029 §2 — the advance-per-monotonic-read for every conversion in this file. The adapter's
# deadline is `_monotonic_clock() + duration_seconds`, so the capture ends after ceil(duration/DELTA)
# reads: a FIXED count, identical every run and every order. 0.01 against these 0.15-0.25s windows
# leaves the scripted book frames a wide margin ahead of the deadline (they land in the first two
# iterations; the deadline fires ~7-12 iterations in), and the margin is MEASURED, not assumed —
# `tools/wo029_clock_control_proof.py` sweeps DELTA and shows the observed window moving with it
# while the emitted deliverable stays pinned.
CLOCK_DELTA = 0.01


async def _no_sleep(_delay):
    return None


class _StubPersistence:
    """Keeps LiveTradingLoop off the Parquet path in tests (its raw-data store is not under test
    here — the gap-ledger JSONL is)."""
    _data_dir = "(stub)"

    def write_event(self, _ms): pass
    def close(self): pass
    def get_file_info(self): return {"path": "(stub)", "exists": False, "event_count": 0, "size_bytes": 0}


def _paper_loop():
    return LiveTradingLoop(execution_client=PaperExecutionClient(), persistence=_StubPersistence())


# ── PREFLIGHT REFUSALS (before any component is built / any socket opens) ──────────
def test_runner_refuses_non_paper_env():
    with pytest.raises(LiveCaptureError, match="LIVE_CAPTURE_ENV_REFUSED"):
        LiveCaptureRunner(persist_path="x.jsonl", duration_seconds=1.0, trading_env="mainnet")


def test_runner_reads_env_and_refuses_when_not_paper(monkeypatch):
    """trading_env=None reads TRADING_ENV from the environment; a non-paper env is refused."""
    monkeypatch.setenv("TRADING_ENV", "mainnet")
    with pytest.raises(LiveCaptureError, match="LIVE_CAPTURE_ENV_REFUSED"):
        LiveCaptureRunner(persist_path="x.jsonl", duration_seconds=1.0, trading_env=None)


def test_runner_refuses_unconfigured_persistence():
    with pytest.raises(LiveCaptureError, match="GAP_PERSIST_UNCONFIGURED"):
        LiveCaptureRunner(persist_path="", duration_seconds=1.0, trading_env="paper")


# ── END-TO-END WIRING (simulated transport) ───────────────────────────────────────
@pytest.mark.asyncio
async def test_runner_drives_instrumented_transport_end_to_end(tmp_path, injected_baseline):
    """The runner drives get_live_market_data (the instrumented transport the factory path never
    did), through the paper loop, persisting the gap ledger and reporting the per-minute series.
    Baseline INJECTED (WO-022 §1) so this is host-independent; the no-baseline refusal is proved
    separately (test_runner_refuses_host_with_no_baseline).

    WO-029 §2 (race 1, DIRECT). BEFORE: the 0.25s window was real wall time, so whether both book
    frames were consumed before the deadline depended on scheduler load — `emitted_per_minute` was
    a race. AFTER: an AdvancingClock drives BOTH the adapter's monotonic deadline and the runner's
    per-minute bucketing wall, one source, one shared coherence token. Gate: PROCEED_COHERENT."""
    persist = tmp_path / "gap_ledger.jsonl"
    clock = AdvancingClock(delta=CLOCK_DELTA)
    # SNAPSHOT (emits) + a valid incremental (emits), then heartbeats keep the link alive.
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL], "on_drain": "heartbeat"},
    ])
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory.connect,
                                  monotonic_clock=clock.monotonic)
    adapter._wall_clock = clock.wall          # the pair's other half — coherent, same token
    runner = LiveCaptureRunner(
        persist_path=persist, duration_seconds=0.25, trading_env="paper",
        adapter=adapter, loop=_paper_loop(),
        clock=clock.wall,                     # the runner's own per-minute bucketing wall
    )

    result = await runner.run()

    # Drove the INSTRUMENTED live transport (mainnet provenance, real connection object opened).
    assert result["venue_name"] == "kraken_mainnet"
    assert factory.connect_count == 1, "the runner opened the (simulated) live socket exactly once"
    # The per-minute EMITTED series is the deliverable — two states emitted in the (sub-second) run.
    assert sum(result["emitted_per_minute"]) == 2, result["emitted_per_minute"]
    # The gap ledger is wired and its anchor recorded.
    ledger = result["gap_ledger"]
    assert ledger is not None and ledger.run_wall_anchor and ledger.run_monotonic_anchor > 0
    # Persistence is configured and WRITTEN (item C: a live capture must not silently no-op).
    assert persist.exists(), "the gap ledger must be persisted to the configured path"
    records = [json.loads(line) for line in persist.read_text(encoding="utf-8").splitlines() if line.strip()]
    events = [r["event"] for r in records]
    assert events[0] == "run_start" and "run_end" in events
    # Instrumentation surfaced for the re-run's report.
    assert "raw_messages_received" in result["diagnostic_counters"]
    assert result["checksum_failure_count"] == 0


@pytest.mark.asyncio
async def test_runner_persistence_is_not_optional_on_the_adapter(tmp_path, injected_baseline):
    """The runner configures the adapter's persistence path, so the adapter's own
    GAP_PERSIST_UNCONFIGURED refusal is satisfied by configuration, not by opting out.

    WO-029 §2 (race 2, DIRECT). BEFORE: the 0.15s window was real wall time — the run had to
    survive a real interval before the post-run configuration assertions could be read. AFTER: the
    injected coherent pair drives the deadline; the window is a fixed read count. Gate:
    PROCEED_COHERENT."""
    persist = tmp_path / "g.jsonl"
    clock = AdvancingClock(delta=CLOCK_DELTA)
    factory = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory.connect,
                                  monotonic_clock=clock.monotonic)
    adapter._wall_clock = clock.wall
    runner = LiveCaptureRunner(persist_path=persist, duration_seconds=0.15, trading_env="paper",
                               adapter=adapter, loop=_paper_loop(), clock=clock.wall)
    await runner.run()
    assert adapter._persistence_optional is False, "the adapter never opts out; it is configured"
    assert adapter._gap_persist_path == str(persist)


# ── OWED §2 BITE PROOFS ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_short_bounded_run_completes_with_readable_artifacts(tmp_path, injected_baseline):
    """OWED (1): a short bounded run COMPLETES and its artifacts EXIST AND ARE READABLE (0.1i) —
    the gap-ledger JSONL (run_start..run_end) and the per-minute emitted series — not merely that
    a method ran.

    WO-029 §2 (race 3, DIRECT). BEFORE: "bounded" meant a real 0.2s wall interval, so the artifacts
    read back from disk were whatever that interval happened to capture. AFTER: the bound is the
    SAME deadline, reached on the injected monotonic seam after a fixed read count — the run is
    still deadline-terminated (`terminated is None`, no breaker trip), just no longer racing the
    host. Gate: PROCEED_COHERENT."""
    persist = tmp_path / "gap_ledger.jsonl"
    clock = AdvancingClock(delta=CLOCK_DELTA)
    conn = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL], "on_drain": "heartbeat"}])
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=conn.connect,
                                  monotonic_clock=clock.monotonic)
    adapter._wall_clock = clock.wall
    runner = LiveCaptureRunner(persist_path=persist, duration_seconds=0.2, trading_env="paper",
                               adapter=adapter, loop=_paper_loop(), clock=clock.wall)
    result = await runner.run()

    # Artifacts readable from disk (not "a flush was called").
    assert persist.exists()
    records = [json.loads(l) for l in persist.read_text(encoding="utf-8").splitlines() if l.strip()]
    events = [r["event"] for r in records]
    assert events[0] == "run_start" and events[-1] == "run_end", events
    run_end = records[-1]
    assert run_end["frames_captured"] >= 1 and run_end["gaps_detected"] == 0
    # The per-minute series exists and totals the emitted states.
    assert sum(result["emitted_per_minute"]) == 2
    assert result["terminated"] is None


@pytest.mark.asyncio
async def test_clean_deadline_close_does_not_reconnect_dual():
    """OWED (2): S13 preservation dual — GOVERNS whether the re-run stops at minute 60.
    (a) reaching the capture DEADLINE ends the run WITHOUT reconnecting;
    (b) an ABNORMAL mid-run disconnect DOES reconnect. Both halves, one test.

    WO-029 §2 (race 4, DIRECT — the deadline-ASSERTION race, §2.0-bis's reason for existing). This
    is the one race whose subject IS the deadline: half (a) asserts that REACHING it ends the run.
    A FROZEN FakeClock cannot convert it — a frozen deadline never fires, and reframing half (a) as
    a scripted clean close would change what the test observes (a §2 STOP). So both halves run on
    the SELF-ADVANCING coherent clock (`AdvancingClock`, bite-proved BOTH directions in
    `evidence/WO-029/advancing_clock_bite_proof.txt`: it fires, and it does not fire prematurely —
    a clock that fired too early would make half (a) pass for the wrong reason, with connect_count
    at 1 because nothing ever ran). BEFORE: both halves raced a real window. AFTER: the deadline
    fires after a fixed read count, far enough in that half (a) serves ~6 heartbeats first and half
    (b)'s reconnect completes with ~10 iterations to spare. Gate: PROCEED_COHERENT (both halves)."""
    # ── (a) clean deadline close -> NO reconnect ──
    clock_a = AdvancingClock(delta=CLOCK_DELTA)
    conn_a = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    adapter_a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=conn_a.connect,
                                    monotonic_clock=clock_a.monotonic)
    adapter_a._wall_clock = clock_a.wall
    adapter_a._persistence_optional = True
    async for _ in adapter_a.get_live_market_data(duration_seconds=0.15):
        pass
    assert conn_a.connect_count == 1, "reaching the deadline must NOT reconnect (re-run stops at 60m)"
    assert adapter_a.capture_terminated is None
    assert [g for g in adapter_a.get_gap_ledger().gaps
            if g.cause in ("KEEPALIVE_RECONNECT", "VENUE_DISCONNECT")] == [], "no reconnect gap"

    # ── (b) abnormal mid-run disconnect -> DOES reconnect (the dual) ──
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    clock_b = AdvancingClock(delta=CLOCK_DELTA)
    conn_b = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])
    adapter_b = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=conn_b.connect,
                                    monotonic_clock=clock_b.monotonic)
    adapter_b._wall_clock = clock_b.wall
    adapter_b._persistence_optional = True
    adapter_b._reconnect_sleep = _no_sleep
    async for _ in adapter_b.get_live_market_data(duration_seconds=0.25):
        pass
    assert conn_b.connect_count == 2, "an abnormal disconnect MUST reconnect (not treated as a deadline)"


@pytest.mark.asyncio
async def test_breaker_trip_terminates_run_with_forensic_tail(tmp_path, injected_baseline):
    """OWED (3): a persistent reopen failure trips the breaker; the RUNNER SURFACES the
    termination (forensic tail + retained partial capture), not a crash."""
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    conn = ScriptedConnectionFactory(
        [{"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"}] + [REOPEN_FAILURE] * 20)
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=conn.connect)
    adapter._reconnect_sleep = None                 # real tiny sleeps so the DURATION breaker advances
    adapter._reconnect_max_failure_seconds = 0.1
    runner = LiveCaptureRunner(persist_path=tmp_path / "g.jsonl", duration_seconds=30,
                               trading_env="paper", adapter=adapter, loop=_paper_loop())

    result = await runner.run()   # must NOT raise — the runner surfaces the trip

    term = result["terminated"]
    assert term is not None, "the breaker trip must be surfaced by the runner, not crash"
    assert term["reason_code"] == "RECONNECT_CIRCUIT_BREAKER_TRIPPED"
    assert term["retry_ladder"] and term["last_validated_book"], "forensic tail present"
    assert "TRUNCATED-HONEST WINDOW" in term["evidentiary_bounds"]
    assert term["frames_captured"] > 0, "the partial capture is retained"
    assert any(g.terminal for g in result["gap_ledger"].gaps), "a terminal gap is recorded"


@pytest.mark.asyncio
async def test_runner_resolves_live_adapter_from_data_source_via_factory(tmp_path, injected_baseline):
    """PRODUCTION path (no injected adapter): the runner resolves the LIVE adapter FROM DATA_SOURCE
    through the factory/registry — the sole adapter-resolution path (Principle IV/VII). It never
    imports a concrete adapter. data_source is the config value ('kraken_v2' here).

    WO-028 §5: the transport is now INJECTED through the runner's `connect_fn` seam (threaded to the
    builder) instead of `patch("websockets.connect", …)`. This exercises the threading end to end at
    the runner boundary.

    WO-029 §2 (race 5, the SOLE FACTORY-BUILT race). This test builds no adapter, so it could not be
    converted at construction — it needed WO-030 (D38) to thread `monotonic_clock`/`wall_clock`
    through runner -> create_live_capture_feed -> _build_kraken_v2, parallel to WO-028's transport
    seam. That is why race 5 was the finding that produced WO-030 and why it rejoined the 26. BEFORE:
    the 0.15s window was real wall time. AFTER: the coherent pair goes in at the RUNNER boundary and
    comes out held by the adapter the FACTORY built — proved by identity at the far end in
    `evidence/WO-029/clock_control_proof.txt` PART B, and by this nodeid's PROCEED_COHERENT
    disposition in the gate ledger (the gate ran on the factory-built adapter and saw the pair)."""
    persist = tmp_path / "g.jsonl"
    clock = AdvancingClock(delta=CLOCK_DELTA)
    conn = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    runner = LiveCaptureRunner(persist_path=persist, duration_seconds=0.15, trading_env="paper",
                               adapter=None, loop=_paper_loop(), data_source="kraken_v2",
                               connect_fn=conn.connect,
                               monotonic_clock=clock.monotonic, wall_clock=clock.wall,
                               clock=clock.wall)
    result = await runner.run()
    assert result["venue_name"] == "kraken_mainnet", "the factory resolved a LIVE mainnet adapter"
    assert conn.connect_count == 1
    assert persist.exists(), "the factory-built adapter persisted its ledger"


@pytest.mark.asyncio
async def test_live_capture_refuses_non_live_capable_data_source(tmp_path, injected_baseline):
    """WO-015 review: DATA_SOURCE naming a NON-live-capable adapter REFUSES specifically and
    BEFORE opening any connection — never connects to the wrong venue, never a cryptic TypeError."""
    persist = tmp_path / "g.jsonl"
    runner = LiveCaptureRunner(persist_path=persist, duration_seconds=0.15, trading_env="paper",
                               adapter=None, loop=_paper_loop(), data_source="simulated")
    conn = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    with patch("websockets.connect", conn.connect):
        with pytest.raises(ValueError, match=r"LIVE_CAPTURE_UNSUPPORTED.*'simulated'.*does not support live capture"):
            await runner.run()
    assert conn.connect_count == 0, "it must refuse BEFORE opening any connection"
