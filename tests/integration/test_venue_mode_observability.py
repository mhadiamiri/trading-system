"""
Venue-mode observability (WO-008b-A1 §4).

`venue_name` previously returned the constant `"kraken_v2"` for BOTH live and
fixture modes, so **a live mainnet run and a fixture replay were
indistinguishable in the decision log**. Captured data whose provenance cannot be
established is not honest evidence — Principle VIII (Total Observability &
Provenance).

The load-bearing assertion here is the negative one: a fixture-mode run must
never be recordable as live.

NO NETWORK. `mode="live"` labels provenance only; it opens no connection.
Transport is WO-008b-A2.
"""

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME


class TestVenueModeProvenance:
    """Mode must be unambiguous and must reach the decision log."""

    def test_fixture_mode_reports_fixture_venue(self):
        adapter = KrakenV2BookAdapter()
        assert adapter.mode == KrakenV2BookAdapter.MODE_FIXTURE
        assert adapter.venue_name == "kraken_fixture"

    def test_live_mode_reports_mainnet_venue(self):
        adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
        assert adapter.mode == KrakenV2BookAdapter.MODE_LIVE
        assert adapter.venue_name == "kraken_mainnet"

    def test_fixture_run_can_never_be_recorded_as_live(self):
        """
        THE LOAD-BEARING ASSERTION.

        A fixture replay must be impossible to record as live provenance. Before
        WO-008b-A1 this was untrue by construction: both modes returned the same
        constant, so the audit trail could not tell a replay from a mainnet
        capture.
        """
        fixture_adapter = KrakenV2BookAdapter()
        live_adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)

        assert fixture_adapter.venue_name != live_adapter.venue_name, (
            "fixture and live MUST be distinguishable in the decision log"
        )
        assert fixture_adapter.venue_name != KrakenV2BookAdapter.VENUE_LIVE
        assert "fixture" in fixture_adapter.venue_name
        assert fixture_adapter.venue_name != "kraken_v2", (
            "the old ambiguous constant must not return"
        )

    def test_unknown_mode_is_rejected(self):
        """An unrecognised mode must fail loudly, not default to something."""
        with pytest.raises(ValueError, match="Unknown adapter mode"):
            KrakenV2BookAdapter(mode="mainnet-ish")

    def test_mode_is_logged_at_startup(self, caplog):
        """Mode must be logged at construction so a run's provenance is on record."""
        import logging

        with caplog.at_level(logging.INFO, logger="trading.data.adapters.kraken_v2_book"):
            KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)

        messages = [r.getMessage() for r in caplog.records]
        assert any("mode=live" in m and "venue=kraken_mainnet" in m for m in messages), (
            f"startup mode log missing; captured: {messages}"
        )

    @pytest.mark.asyncio
    async def test_venue_provenance_accompanies_emitted_market_states(self):
        """
        Provenance must be available for every emitted MarketState, in both modes.

        The adapter is the source of `venue_name` that `factory.get_venue_name()`
        feeds into each decision-log record.
        """
        for mode, expected_venue in (
            (KrakenV2BookAdapter.MODE_FIXTURE, "kraken_fixture"),
            (KrakenV2BookAdapter.MODE_LIVE, "kraken_mainnet"),
        ):
            adapter = KrakenV2BookAdapter(mode=mode)
            states = await adapter.process_raw_frame(SNAPSHOT_FRAME)

            assert len(states) == 1
            assert adapter.venue_name == expected_venue, (
                f"mode={mode} must report venue={expected_venue}"
            )
            counters = adapter.get_diagnostic_counters()
            assert counters is not None
