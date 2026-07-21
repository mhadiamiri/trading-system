"""
No silent fixture fallback (WO-008b-A2 §2.4).

A failed live connection must RAISE. It must never quietly replay fixtures and
present the result as live data — that would be the fabrication path's failure
mode wearing a different coat: the system LOOKING alive while disconnected from
reality.

NO NETWORK in these tests. The connection is failed deliberately by patching the
transport call, so nothing here opens a socket.
"""

from unittest.mock import patch

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME


class TestNoSilentFallback:
    """A broken connection fails loudly."""

    @pytest.mark.asyncio
    async def test_connection_failure_raises_and_does_not_replay_fixtures(self):
        """
        THE BITE. When the socket cannot be opened, the run must RAISE.

        It must not emit a single MarketState — emitting even one would mean
        fixture data had been presented as live.
        """
        adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
        adapter._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)

        async def _boom(*args, **kwargs):
            raise OSError("simulated: connection refused")

        emitted = []
        with patch("websockets.connect", _boom):
            with pytest.raises(ConnectionError) as exc_info:
                async for state in adapter.get_live_market_data(duration_seconds=5):
                    emitted.append(state)

        assert emitted == [], (
            "a failed connection emitted MarketStates — fixtures were replayed as live"
        )
        message = str(exc_info.value)
        assert "connection FAILED" in message
        assert "never fall back to fixtures" in message

    @pytest.mark.asyncio
    async def test_live_method_refuses_fixture_mode_adapter(self):
        """Mode is explicit. A fixture adapter cannot be coaxed into a live run."""
        adapter = KrakenV2BookAdapter()  # fixture mode

        with pytest.raises(ValueError, match="requires mode='live'"):
            async for _ in adapter.get_live_market_data(duration_seconds=1):
                pass

    @pytest.mark.asyncio
    async def test_fixture_path_cannot_be_labelled_live(self):
        """
        A fixture replay retains fixture provenance end to end.

        Even a live-MODE adapter fed fixtures reports what it actually is at the
        point where it matters — the fixture path and the live path are separate
        methods, so a fixture replay can never traverse get_live_market_data().
        """
        adapter = KrakenV2BookAdapter()
        states = [s async for s in adapter.get_market_data(fixture_data=[SNAPSHOT_FRAME])]

        assert len(states) == 1
        assert adapter.venue_name == "kraken_fixture"
        assert adapter.venue_name != "kraken_mainnet"

    @pytest.mark.asyncio
    async def test_no_fixture_data_raises_rather_than_fabricating(self):
        """
        The removed fabrication path must stay removed.

        Called with no frames, the adapter raises instead of inventing a book.
        """
        adapter = KrakenV2BookAdapter()

        with pytest.raises(ValueError, match="requires fixture_data"):
            async for _ in adapter.get_market_data(fixture_data=None):
                pass
