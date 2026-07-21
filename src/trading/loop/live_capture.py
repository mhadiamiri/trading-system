"""
WO-015 — LIVE-CAPTURE RUNNER (build only; opens NO socket in this WO).

The re-run (WO-008b-B-RERUN §2) assumed an entrypoint that had never existed: get_live_market_data
had only ever been driven by tests with a patched transport. This runner is that entrypoint. It
DRIVES THE INSTRUMENTED TRANSPORT — KrakenV2BookAdapter.get_live_market_data — end-to-end through
Data -> Strategy -> Risk -> Execution(paper), WIRING the existing instruments (gap ledger, failure
capture, host-suspend detection, lag/pong/throughput — all already inside get_live_market_data)
rather than reimplementing them. The re-run forbids changing throughput counting or instruments
once it begins, so everything is wired HERE, before the run, not patched around it.

PREFLIGHT ENFORCEMENT LIVES IN THE RUNNER, not a checklist (checklist-enforced rules are 0-for-N
in this project): it REFUSES a non-paper TRADING_ENV and REFUSES an unconfigured persistence path.
Both are loud, before any connection.

HONEST LIMIT (rule 0.1f): opening a REAL venue socket is production only. Every test and bite proof
here drives SIMULATED transport (websockets.connect patched). This runner has never held a real
socket — that is the re-run's job, under the per-run authorization, on a host that does not suspend.
"""

import time
from typing import Any, Optional, AsyncIterator

# WO-015: the runner resolves the LIVE adapter through the FACTORY/REGISTRY (the sole
# adapter-resolution path, Principle IV/VII). It MUST NOT import a concrete adapter module —
# import-linter forbids trading.loop -> trading.data.adapters.kraken_v2_book. The adapter is a
# duck-typed object here; tests inject one directly (tests are exempt from the boundary).
from trading.data.adapters import factory
from trading.execution.paper import PaperExecutionClient
from trading.loop.live import LiveTradingLoop


class LiveCaptureError(RuntimeError):
    """Preflight refusal — raised BEFORE any connection when the run is unsafe/unrecorded."""


class LiveCaptureRunner:
    """Drives the instrumented live transport + paper loop for a bounded capture window."""

    SYMBOL = "BTC/USD"

    def __init__(
        self,
        persist_path,
        duration_seconds: float,
        trading_env: Optional[str] = None,
        adapter: Optional[Any] = None,     # injected by tests; production resolves via factory
        loop: Optional[LiveTradingLoop] = None,
        clock=None,
    ) -> None:
        """
        Args:
            persist_path: append-only gap-ledger JSONL path (REQUIRED — refused if empty).
            duration_seconds: capture window; get_live_market_data's own bound governs the run.
            trading_env: TRADING_ENV; read from the environment when None. Must be 'paper'.
            adapter/loop: injected for tests; production builds the live adapter + paper loop.
            clock: wall clock for per-minute bucketing (test seam); defaults to time.time.
        """
        self._persist_path = persist_path
        self._duration_seconds = duration_seconds
        if trading_env is None:
            import os
            trading_env = os.environ.get("TRADING_ENV")
        self._trading_env = trading_env
        self._adapter = adapter
        self._loop = loop
        self._clock = clock or time.time
        self._preflight()

    def _preflight(self) -> None:
        # REFUSE a non-paper environment — the order-capable path must be unreachable (Principle
        # IX; the re-run bite-proves it), and a live capture must never risk a real order.
        if self._trading_env != "paper":
            raise LiveCaptureError(
                f"LIVE_CAPTURE_ENV_REFUSED: TRADING_ENV must be 'paper' for a live capture, got "
                f"{self._trading_env!r}. Refusing to run outside paper."
            )
        # REFUSE an unconfigured persistence path — an unpersisted live ledger silently loses
        # every gap on a kill/trip (the WO-014c-3 §0.1 / item-C hazard). The adapter refuses too;
        # this refuses EARLIER, before any component is built.
        if not self._persist_path:
            raise LiveCaptureError(
                "GAP_PERSIST_UNCONFIGURED: live capture requires a gap-ledger persistence path "
                "(persist_path). Refusing to run a silently-unpersisted capture."
            )

    def _resolve_feed(self):
        """Return (adapter, live_feed_iterator). Production goes through the factory/registry (the
        sole adapter-resolution path); tests inject an adapter directly (and configure its path)."""
        if self._adapter is not None:
            adapter = self._adapter
            adapter._gap_persist_path = str(self._persist_path)
            # _persistence_optional stays False: the adapter is the second line of the refusal.
            return adapter, adapter.get_live_market_data(self._duration_seconds)
        return factory.create_live_capture_feed(self._persist_path, self._duration_seconds)

    async def run(self) -> dict:
        """Run the capture. Returns the throughput series + the wired instrumentation.
        Opens no socket itself — get_live_market_data does (real in production, patched in tests)."""
        adapter, feed_iter = self._resolve_feed()
        loop = self._loop or LiveTradingLoop(execution_client=PaperExecutionClient())

        per_minute: dict = {}          # wall-minute index -> MarketStates EMITTED (the §2.2 series)
        run_start_wall = self._clock()

        async def _counting_feed() -> AsyncIterator:
            # Wrap the instrumented feed so the per-MINUTE emitted series is measured at the yield
            # boundary — §2.2's deliverable, which the aggregate rate cannot substitute for.
            async for state in feed_iter:
                minute = int((self._clock() - run_start_wall) // 60)
                per_minute[minute] = per_minute.get(minute, 0) + 1
                yield state

        # Stop-guards set large so get_live_market_data's own duration bound governs the window.
        loop_result = await loop.run(
            max_updates=10 ** 12,
            duration_minutes=(self._duration_seconds / 60.0) + 5.0,
            feed=_counting_feed(),
        )

        last_minute = max(per_minute) if per_minute else -1
        emitted_per_minute = [per_minute.get(i, 0) for i in range(last_minute + 1)]

        ledger = adapter.get_gap_ledger()
        return {
            "venue_name": adapter.venue_name,
            "persist_path": str(self._persist_path),
            "emitted_per_minute": emitted_per_minute,     # the §2.2 per-minute series
            "gap_ledger": ledger,
            "checksum_failure_count": adapter.get_checksum_failure_count(),
            "checksum_failure_captures": adapter.get_checksum_failure_captures(),
            "checksum_failure_summaries": adapter.get_checksum_failure_summaries(),
            "diagnostic_counters": adapter.get_diagnostic_counters(),
            "loop_result": loop_result,
        }
