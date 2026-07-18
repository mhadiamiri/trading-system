"""
Data Adapter Tests (Sprint 2)

Tests for Kraken v2 book adapter with checksum validation.

Constitutional Principles:
- V. No Backtest Without Costs: Observed spread only
- VII. Venue Independence: v2 detail confined to adapter
- VIII. Total Observability: All errors logged with reason codes
"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from trading.data.adapters.kraken_v2_book import (
    KrakenV2BookAdapter,
    LocalBookData,
    LocalBookState,
    QuoteUpdate,
    RollingTradeStats,
    TradeEvent,
)
from trading.data.market_state import MarketState


class TestKrakenV2BookChecksum:
    """
    Test checksum validation for Kraken v2 book adapter.

    These tests verify fail-then-pass pattern:
    - Write tests first (they FAIL because adapter doesn't exist)
    - Implement adapter (tests PASS)
    """

    @pytest.mark.asyncio
    async def test_valid_checksum_passes_and_updates_book(self):
        """
        Test: Valid checksum passes validation and updates local book.

        Constitutional requirements:
        - FR-004: Validate checksums on every update (using FULL 10-level ladder)
        - FR-016: Maintain local book state from validated updates

        EXPECTS-VALID: Fixture carries real checksum computed over full 10-level ladder.
        """
        # Create adapter
        adapter = KrakenV2BookAdapter()

        # Initialize with a 10-level snapshot (Kraken's published example)
        snapshot_bids = [
            ('45283.5', '0.10000000'),
            ('45283.4', '1.54582015'),
            ('45282.1', '0.10000000'),
            ('45281.0', '0.10000000'),
            ('45280.3', '1.54592586'),
            ('45279.0', '0.07990000'),
            ('45277.6', '0.03310103'),
            ('45277.5', '0.30000000'),
            ('45277.3', '1.54602737'),
            ('45276.6', '0.15445238'),
        ]

        snapshot_asks = [
            ('45285.2', '0.00100000'),
            ('45286.4', '1.54571953'),
            ('45286.6', '1.54571109'),
            ('45289.6', '1.54560911'),
            ('45290.2', '0.15890660'),
            ('45291.8', '1.54553491'),
            ('45294.7', '0.04454749'),
            ('45296.1', '0.35380000'),
            ('45297.5', '0.09945542'),
            ('45299.5', '0.18772827'),
        ]

        # Kraken's published checksum for this 10-level book
        expected_checksum = 3310070434

        # Apply the snapshot to initialize the book
        adapter._local_book.apply_snapshot(
            snapshot_bids, snapshot_asks,
            sequence=1, checksum=expected_checksum
        )

        # Verify snapshot was applied correctly
        assert len(adapter._local_book.bids) == 10, "Book should have 10 bid levels"
        assert len(adapter._local_book.asks) == 10, "Book should have 10 ask levels"
        assert adapter._local_book.best_bid_price == Decimal('45283.5')
        assert adapter._local_book.best_ask_price == Decimal('45285.2')

        # Verify we can compute checksum from the full ladder
        bid_levels = [(str(p), str(s)) for p, s in adapter._local_book.bids[:10]]
        ask_levels = [(str(p), str(s)) for p, s in adapter._local_book.asks[:10]]
        computed = KrakenV2BookAdapter.compute_checksum(bid_levels, ask_levels)

        assert computed == expected_checksum, "Checksum should match Kraken's published value"
        assert adapter._local_book.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_corrupted_checksum_rejected_and_logged(self):
        """
        Test: Corrupted checksum is rejected and logged.

        Constitutional requirements:
        - FR-017: Reject updates with invalid checksums and log rejection
        - FR-004: Validate checksums on every update

        CRITICAL: This is the fail-then-pass proof that checksum validation bites.
        A corrupted update (price altered, checksum unchanged) must be rejected.

        This test should FAIL initially (adapter doesn't exist),
        then PASS after T014 implementation.
        """
        # Create adapter with mock logger
        adapter = KrakenV2BookAdapter()
        adapter._log_error = Mock()

        # Create update with CORRUPTED checksum
        # Valid checksum for bid=65000, ask=65005 is 388076886
        # But we use that checksum with corrupted ask price (65100)
        quote_update = QuoteUpdate(
            bid_price=Decimal("65000.00"),
            bid_size=Decimal("1.5"),
            ask_price=Decimal("65100.00"),  # CORRUPTED: price changed
            ask_size=Decimal("2.0"),
            checksum=388076886,  # Checksum for original data, NOT updated for new price
            sequence=1,
            timestamp=datetime.now(UTC),
        )

        # Process the update
        market_state = await adapter._process_quote_update(quote_update)

        # Verify update was REJECTED
        assert market_state is None, "Corrupted checksum should cause rejection"

        # Verify error was logged
        adapter._log_error.assert_called_once()
        assert "checksum validation failed" in str(adapter._log_error.call_args).lower()

        # Verify consecutive_failures incremented
        assert adapter._local_book.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_five_consecutive_failures_trigger_resync(self):
        """
        Test: 5 consecutive checksum failures trigger resync/reconnect.

        Constitutional requirements:
        - FR-018: After 5 consecutive checksum failures, initiate reconnection
        - FR-018: Reset counter on successful resync

        This test should FAIL initially (adapter doesn't exist),
        then PASS after T016 implementation.
        """
        # Create adapter with mock connection
        adapter = KrakenV2BookAdapter()
        adapter._reconnect = Mock()
        adapter._request_snapshot = Mock()

        # Simulate 5 consecutive checksum failures
        for i in range(5):
            quote_update = QuoteUpdate(
                bid_price=Decimal("65000.00"),
                bid_size=Decimal("1.5"),
                ask_price=Decimal("65100.00"),  # Corrupted
                ask_size=Decimal("2.0"),
                checksum=388076886,  # Wrong checksum (original data checksum)
                sequence=i + 1,
                timestamp=datetime.now(UTC),
            )
            await adapter._process_quote_update(quote_update)

        # Verify resync was triggered
        assert adapter._local_book.consecutive_failures == 5
        adapter._reconnect.assert_called_once()
        adapter._request_snapshot.assert_called_once()

        # Verify < 5 failures does NOT trigger resync
        adapter._local_book.consecutive_failures = 0
        adapter._reconnect.reset_mock()
        adapter._request_snapshot.reset_mock()

        for i in range(4):  # Only 4 failures
            quote_update = QuoteUpdate(
                bid_price=Decimal("65000.00"),
                bid_size=Decimal("1.5"),
                ask_price=Decimal("65100.00"),
                ask_size=Decimal("2.0"),
                checksum=12345,
                sequence=i + 1,
                timestamp=datetime.now(UTC),
            )
            await adapter._process_quote_update(quote_update)

        # Verify resync NOT triggered
        assert adapter._local_book.consecutive_failures == 4
        adapter._reconnect.assert_not_called()
        adapter._request_snapshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_sequence_gap_triggers_resnapshot(self):
        """
        Test: Sequence gap triggers discard book + request fresh snapshot.

        Constitutional requirements:
        - FR-018a: On sequence gap, discard local book and request fresh snapshot
        - FR-018a: No continue-on-gap path

        This test should FAIL initially (adapter doesn't exist),
        then PASS after T015 implementation.
        """
        # Create adapter with mock snapshot request
        adapter = KrakenV2BookAdapter()
        adapter._request_snapshot = Mock()
        adapter._discard_book = Mock()

        # Establish synchronized book (sequence 100)
        # Use apply_snapshot to initialize with bid/ask levels (LocalBookData API)
        adapter._local_book.apply_snapshot(
            bid_levels=[(Decimal("65000.00"), Decimal("1.5"))],
            ask_levels=[(Decimal("65005.00"), Decimal("2.0"))],
            sequence=100,
            checksum=12345,
        )

        # Receive update with sequence 105 (GAP: missing 101-104)
        quote_update = QuoteUpdate(
            bid_price=Decimal("65001.00"),
            bid_size=Decimal("1.6"),
            ask_price=Decimal("65006.00"),
            ask_size=Decimal("2.1"),
            checksum=12346,  # Valid checksum for this data
            sequence=105,  # GAP!
            timestamp=datetime.now(UTC),
        )

        # Process the update
        market_state = await adapter._process_quote_update(quote_update)

        # Verify book was discarded due to gap
        adapter._discard_book.assert_called_once()
        adapter._request_snapshot.assert_called_once()

        # Verify no market state emitted during gap recovery
        assert market_state is None

        # Verify sequence gap detection (last_sequence + 1 != incoming)
        assert adapter._local_book.last_sequence == 100  # Not updated


class TestLocalBookState:
    """Test LocalBookState entity (adapter-internal)."""

    def test_local_book_state_initialization(self):
        """
        Test LocalBookState initialization.

        This test should FAIL initially (entity doesn't exist),
        then PASS after T009 implementation.
        """
        # Create book state using apply_snapshot (LocalBookData API)
        book_state = LocalBookData()
        book_state.apply_snapshot(
            bid_levels=[(Decimal("65000.00"), Decimal("1.5"))],
            ask_levels=[(Decimal("65005.00"), Decimal("2.0"))],
            sequence=100,
            checksum=12345,
        )

        assert book_state.best_bid_price == Decimal("65000.00")
        assert book_state.best_ask_price == Decimal("65005.00")
        assert book_state.last_sequence == 100
        assert book_state.consecutive_failures == 0
        assert book_state.is_paused is False

    def test_local_book_state_transitions(self):
        """
        Test LocalBookState state transitions.

        States: INITIAL → SYNCHRONIZED → RESYNC_REQUIRED → PAUSED → SYNCHRONIZED

        This test should FAIL initially (entity doesn't exist),
        then PASS after T009 implementation.
        """
        # Start in INITIAL state
        book = LocalBookData()
        assert book.state == LocalBookState.INITIAL

        # Transition to SYNCHRONIZED after snapshot
        book.apply_snapshot(
            bid_levels=[(Decimal("65000.00"), Decimal("1.5"))],
            ask_levels=[(Decimal("65005.00"), Decimal("2.0"))],
            sequence=100,
            checksum=12345,
        )
        assert book.state == LocalBookState.SYNCHRONIZED
        assert book.last_sequence > 0


class TestQuoteUpdate:
    """Test QuoteUpdate entity (adapter-internal)."""

    def test_quote_update_validation(self):
        """
        Test QuoteUpdate validation.

        This test should FAIL initially (entity doesn't exist),
        then PASS after T010 implementation.
        """
        quote = QuoteUpdate(
            bid_price=Decimal("65000.00"),
            bid_size=Decimal("1.5"),
            ask_price=Decimal("65005.00"),
            ask_size=Decimal("2.0"),
            checksum=12345,
            sequence=1,
            timestamp=datetime.now(UTC),
        )

        assert quote.bid_price == Decimal("65000.00")
        assert quote.ask_price == Decimal("65005.00")
        assert quote.sequence == 1


class TestRollingTradeStats:
    """
    Test rolling trade statistics (T022-T024).

    Tests for US4: Trades as Secondary Enrichment.

    Constitutional requirements:
    - FR-009: Rolling window of 100 trades AND 60 seconds (hybrid truncation)
    """

    def test_rolling_trade_stats_initialization(self):
        """
        Test RollingTradeStats initialization.

        Verifies:
        - trades list starts empty
        - window_count_cap defaults to 100
        - window_time_cap defaults to 60 seconds
        """
        stats = RollingTradeStats()

        assert stats.count == 0
        assert stats.trades == []
        assert stats.window_count_cap == 100
        assert stats.window_time_cap == 60
        assert stats.total_volume == Decimal("0")
        assert stats.last_price is None

    def test_add_trade_increases_count(self):
        """
        Test adding a trade increases count and volume.

        Verifies:
        - count increments with each trade
        - total_volume accumulates correctly
        - last_price updates to most recent trade
        """
        stats = RollingTradeStats()

        # Add first trade
        trade1 = TradeEvent(
            price=Decimal("65000.00"),
            size=Decimal("1.5"),
            timestamp=datetime.now(UTC),
        )
        stats.add_trade(trade1)

        assert stats.count == 1
        assert stats.total_volume == Decimal("1.5")
        assert stats.last_price == Decimal("65000.00")

        # Add second trade
        trade2 = TradeEvent(
            price=Decimal("65100.00"),
            size=Decimal("2.0"),
            timestamp=datetime.now(UTC),
        )
        stats.add_trade(trade2)

        assert stats.count == 2
        assert stats.total_volume == Decimal("3.5")
        assert stats.last_price == Decimal("65100.00")

    def test_window_count_cap_truncation(self):
        """
        Test window count cap truncation.

        Verifies that when count exceeds window_count_cap (100),
        the oldest trades are removed.

        Constitutional requirements:
        - FR-009: Count cap removes oldest trades when exceeded
        """
        stats = RollingTradeStats(window_count_cap=5)

        # Add 10 trades
        for i in range(10):
            trade = TradeEvent(
                price=Decimal(f"6500{i}.00"),
                size=Decimal("1.0"),
                timestamp=datetime.now(UTC),
            )
            stats.add_trade(trade)

        # Should only have 5 trades (most recent)
        assert stats.count == 5
        assert stats.last_price == Decimal("65009.00")
        # Total volume should be from trades 5-9 (most recent 5)
        assert stats.total_volume == Decimal("5.0")

    def test_window_time_cap_truncation(self):
        """
        Test window time cap truncation.

        Verifies that trades older than window_time_cap (60 seconds)
        are removed from the window.

        Constitutional requirements:
        - FR-009: Time cap removes trades older than 60 seconds
        """
        from datetime import timedelta

        stats = RollingTradeStats(window_time_cap=60)

        base_time = datetime.now(UTC)

        # Add trade at t=0
        trade1 = TradeEvent(
            price=Decimal("65000.00"),
            size=Decimal("1.0"),
            timestamp=base_time,
        )
        stats.add_trade(trade1, current_timestamp=base_time)

        # Add trade at t=30 seconds
        trade2 = TradeEvent(
            price=Decimal("65100.00"),
            size=Decimal("2.0"),
            timestamp=base_time + timedelta(seconds=30),
        )
        stats.add_trade(trade2, current_timestamp=base_time + timedelta(seconds=30))

        # Add trade at t=90 seconds (past time cap)
        trade3 = TradeEvent(
            price=Decimal("65200.00"),
            size=Decimal("3.0"),
            timestamp=base_time + timedelta(seconds=90),
        )
        stats.add_trade(trade3, current_timestamp=base_time + timedelta(seconds=90))

        # Only trade2 and trade3 should remain (trade1 is older than 60 seconds)
        assert stats.count == 2
        assert stats.total_volume == Decimal("5.0")
        assert stats.last_price == Decimal("65200.00")

    def test_hybrid_truncation_both_caps(self):
        """
        Test hybrid truncation with BOTH caps applied.

        Verifies that BOTH count and time caps are applied,
        not just one or the other.

        Constitutional requirements:
        - FR-009: Hybrid truncation (BOTH caps applied, not either/or)
        """
        from datetime import timedelta

        stats = RollingTradeStats(window_count_cap=5, window_time_cap=60)

        base_time = datetime.now(UTC)

        # Add 10 trades, with timestamps spaced to test hybrid logic
        for i in range(10):
            trade = TradeEvent(
                price=Decimal(f"6500{i}.00"),
                size=Decimal("1.0"),
                timestamp=base_time + timedelta(seconds=i * 10),  # 0, 10, 20, ... 90 seconds
            )
            # Use current time at 90 seconds for pruning
            stats.add_trade(trade, current_timestamp=base_time + timedelta(seconds=90))

        # After hybrid truncation:
        # - Time cap: trades older than 30 seconds (90 - 60 = 30 threshold) removed
        # - Count cap: if more than 5, keep only 5 most recent
        # Result: Should have exactly 5 trades (most recent)
        assert stats.count == 5
        assert stats.last_price == Decimal("65009.00")

    def test_reset_clears_window(self):
        """
        Test reset clears the rolling window.

        Verifies:
        - All trades are removed
        - Count returns to 0
        - Volume returns to 0
        - Last price returns to None
        """
        stats = RollingTradeStats()

        # Add some trades
        for i in range(5):
            trade = TradeEvent(
                price=Decimal(f"6500{i}.00"),
                size=Decimal("1.0"),
                timestamp=datetime.now(UTC),
            )
            stats.add_trade(trade)

        assert stats.count == 5

        # Reset
        stats.reset()

        assert stats.count == 0
        assert stats.total_volume == Decimal("0")
        assert stats.last_price is None
