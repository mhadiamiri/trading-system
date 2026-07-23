"""
WO-015 — the LIVE-CAPTURE RUNNER. Preflight refusals + end-to-end wiring, all on SIMULATED
transport (websockets.connect patched). NO real socket is opened here — that is the re-run's job.
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
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory, REOPEN_FAILURE


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
    separately (test_runner_refuses_host_with_no_baseline)."""
    persist = tmp_path / "gap_ledger.jsonl"
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    runner = LiveCaptureRunner(
        persist_path=persist, duration_seconds=0.25, trading_env="paper",
        adapter=adapter, loop=_paper_loop(),
    )

    # SNAPSHOT (emits) + a valid incremental (emits), then heartbeats keep the link alive.
    factory = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL], "on_drain": "heartbeat"},
    ])

    with patch("websockets.connect", factory.connect):
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
    GAP_PERSIST_UNCONFIGURED refusal is satisfied by configuration, not by opting out."""
    persist = tmp_path / "g.jsonl"
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    runner = LiveCaptureRunner(persist_path=persist, duration_seconds=0.15, trading_env="paper",
                               adapter=adapter, loop=_paper_loop())
    factory = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    with patch("websockets.connect", factory.connect):
        await runner.run()
    assert adapter._persistence_optional is False, "the adapter never opts out; it is configured"
    assert adapter._gap_persist_path == str(persist)


# ── OWED §2 BITE PROOFS ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_short_bounded_run_completes_with_readable_artifacts(tmp_path, injected_baseline):
    """OWED (1): a short bounded run COMPLETES and its artifacts EXIST AND ARE READABLE (0.1i) —
    the gap-ledger JSONL (run_start..run_end) and the per-minute emitted series — not merely that
    a method ran."""
    persist = tmp_path / "gap_ledger.jsonl"
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    runner = LiveCaptureRunner(persist_path=persist, duration_seconds=0.2, trading_env="paper",
                               adapter=adapter, loop=_paper_loop())
    conn = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL], "on_drain": "heartbeat"}])
    with patch("websockets.connect", conn.connect):
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
    (b) an ABNORMAL mid-run disconnect DOES reconnect. Both halves, one test."""
    # ── (a) clean deadline close -> NO reconnect ──
    adapter_a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter_a._persistence_optional = True
    conn_a = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    with patch("websockets.connect", conn_a.connect):
        async for _ in adapter_a.get_live_market_data(duration_seconds=0.15):
            pass
    assert conn_a.connect_count == 1, "reaching the deadline must NOT reconnect (re-run stops at 60m)"
    assert adapter_a.capture_terminated is None
    assert [g for g in adapter_a.get_gap_ledger().gaps
            if g.cause in ("KEEPALIVE_RECONNECT", "VENUE_DISCONNECT")] == [], "no reconnect gap"

    # ── (b) abnormal mid-run disconnect -> DOES reconnect (the dual) ──
    adapter_b = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter_b._persistence_optional = True
    adapter_b._reconnect_sleep = _no_sleep
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    conn_b = ScriptedConnectionFactory([
        {"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"},
        {"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"},
    ])
    with patch("websockets.connect", conn_b.connect):
        async for _ in adapter_b.get_live_market_data(duration_seconds=0.25):
            pass
    assert conn_b.connect_count == 2, "an abnormal disconnect MUST reconnect (not treated as a deadline)"


@pytest.mark.asyncio
async def test_breaker_trip_terminates_run_with_forensic_tail(tmp_path, injected_baseline):
    """OWED (3): a persistent reopen failure trips the breaker; the RUNNER SURFACES the
    termination (forensic tail + retained partial capture), not a crash."""
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._reconnect_sleep = None                 # real tiny sleeps so the DURATION breaker advances
    adapter._reconnect_max_failure_seconds = 0.1
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    conn = ScriptedConnectionFactory(
        [{"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"}] + [REOPEN_FAILURE] * 20)
    runner = LiveCaptureRunner(persist_path=tmp_path / "g.jsonl", duration_seconds=30,
                               trading_env="paper", adapter=adapter, loop=_paper_loop())

    with patch("websockets.connect", conn.connect):
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
    imports a concrete adapter. data_source is the config value ('kraken_v2' here)."""
    persist = tmp_path / "g.jsonl"
    runner = LiveCaptureRunner(persist_path=persist, duration_seconds=0.15, trading_env="paper",
                               adapter=None, loop=_paper_loop(), data_source="kraken_v2")
    conn = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    with patch("websockets.connect", conn.connect):
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
