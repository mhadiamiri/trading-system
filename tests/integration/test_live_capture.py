"""
WO-015 — the LIVE-CAPTURE RUNNER. Preflight refusals + end-to-end wiring, all on SIMULATED
transport (websockets.connect patched). NO real socket is opened here — that is the re-run's job.
"""

import json

import pytest
from unittest.mock import patch

from trading.loop.live_capture import LiveCaptureRunner, LiveCaptureError
from trading.loop.live import LiveTradingLoop
from trading.execution.paper import PaperExecutionClient
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME, UPDATE_MODIFY_LEVEL
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory


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
async def test_runner_drives_instrumented_transport_end_to_end(tmp_path):
    """The runner drives get_live_market_data (the instrumented transport the factory path never
    did), through the paper loop, persisting the gap ledger and reporting the per-minute series."""
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
async def test_runner_persistence_is_not_optional_on_the_adapter(tmp_path):
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


@pytest.mark.asyncio
async def test_runner_resolves_live_adapter_via_factory(tmp_path):
    """PRODUCTION path (no injected adapter): the runner resolves a LIVE adapter through the
    factory/registry — the sole adapter-resolution path (Principle IV/VII, import-linter-enforced).
    The runner never imports a concrete adapter; create_live_capture_feed resolves the v2 book
    adapter (the only live-capable, instrumented source)."""
    persist = tmp_path / "g.jsonl"
    runner = LiveCaptureRunner(persist_path=persist, duration_seconds=0.15, trading_env="paper",
                               adapter=None, loop=_paper_loop())
    conn = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    with patch("websockets.connect", conn.connect):
        result = await runner.run()
    assert result["venue_name"] == "kraken_mainnet", "the factory resolved a LIVE mainnet adapter"
    assert conn.connect_count == 1
    assert persist.exists(), "the factory-built adapter persisted its ledger"
