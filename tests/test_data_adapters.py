"""
Data Adapter Tests (Sprint 2)

Tests for Kraken v2 book adapter with checksum validation.

Constitutional Principles:
- V. No Backtest Without Costs: Observed spread only
- VII. Venue Independence: v2 detail confined to adapter
- VIII. Total Observability: All errors logged with reason codes
"""

# ═══════════════════════════════════════════════════════════════════════════
# DEPRECATED FIXTURES (WO-009 §2.4) — REMOVAL OWNER: WO-008b-A
#
# Every `QuoteUpdate(...)` constructed in this file is a PRE-PARSED OBJECT, not
# a raw Kraken v2 wire frame. Such fixtures never exercise the parse path, and
# they carried a synthetic `sequence` field — a protocol element the Kraken v2
# public book channel does not transmit (see amended FR-018a).
#
# RETAINED deliberately: deleting them here would remove coverage before the
# raw-frame consumer exists. They are superseded by
# tests/fixtures/kraken_v2_raw_frames.py.
#
# WO-008b-A owns: building the raw-frame parse path, rewiring these tests onto
# it, and deleting these fixtures. See evidence/WO-009/tests_requiring_rewire.txt
# ═══════════════════════════════════════════════════════════════════════════

import pytest
import copy
import logging
from contextlib import contextmanager

from tests.fixtures.kraken_v2_raw_frames import (
    SNAPSHOT_FRAME,
    UPDATE_MODIFY_LEVEL,
    UPDATE_DELETE_LEVEL_QTY_ZERO,
    UPDATE_NEW_LEVEL_CAUSES_TRUNCATION,
    SUBSCRIPTION_ACK_FRAME,
    HEARTBEAT_FRAME,
    TRUNCATED_OUT_BID_PRICE,
)


@contextmanager
def caplog_at_error():
    """Capture ERROR records emitted by the adapter's real logger (FR-017)."""
    records = []

    class _Collector(logging.Handler):
        def emit(self, record):
            records.append(record)

    adapter_logger = logging.getLogger("trading.data.adapters.kraken_v2_book")
    handler = _Collector(level=logging.ERROR)
    adapter_logger.addHandler(handler)
    previous = adapter_logger.level
    adapter_logger.setLevel(logging.ERROR)
    try:
        yield records
    finally:
        adapter_logger.removeHandler(handler)
        adapter_logger.setLevel(previous)
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
        Test: a corrupted book frame is rejected AND the rejection is logged.

        REWIRED WO-008b-A1 §5: drives the REAL PARSE PATH with a raw v2 frame
        instead of a pre-parsed QuoteUpdate. The parser was previously never
        exercised by any test.

        Constitutional requirements:
        - FR-017: reject updates with invalid checksums AND log the rejection
        - FR-018a(b): checksum is validated over the POST-update book
        - FR-018a(d): no MarketState emitted once the book is unverified
        """
        adapter = KrakenV2BookAdapter()

        # Establish a book from Kraken's GROUND-TRUTH snapshot.
        states = await adapter.process_raw_frame(SNAPSHOT_FRAME)
        assert len(states) == 1, "ground-truth snapshot must validate and emit"

        # Corrupt an update: alter the price but keep the original checksum.
        corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
        corrupted["data"][0]["bids"][0]["price"] = "45283.7"

        with caplog_at_error() as records:
            out = await adapter.process_raw_frame(corrupted)

        assert out == [], "corrupted update must NOT emit a MarketState"
        assert adapter._local_book.consecutive_failures == 1
        assert adapter._awaiting_resync is True, (
            "FR-018a(d): a failed checksum must open the no-emission window"
        )

        # FR-017: the rejection must actually be LOGGED. Before WO-008b-A1 this
        # went into a Mock in __init__ and was silently discarded.
        assert any("Checksum validation failed" in r.getMessage() for r in records), (
            "FR-017 requires the rejection to be logged; "
            f"captured records: {[r.getMessage() for r in records]}"
        )

    @pytest.mark.asyncio
    async def test_five_consecutive_failures_trigger_reconnect(self):
        """
        Test: 5 consecutive checksum failures trigger reconnection.

        REWIRED WO-008b-A1 §5, and the SEMANTICS CHANGED as a direct consequence
        of amended FR-018a(d):

          BEFORE: a failure left the book in place; failures accumulated on
                  incremental updates until 5 triggered resync.
          NOW:    the FIRST failure immediately discards the book and opens the
                  no-emission window (resync is instant, not deferred to 5).
                  Incremental updates are then refused outright, so failures can
                  only continue accumulating on SNAPSHOTS — and the 5-failure
                  threshold now governs the stronger action, RECONNECT.

        This is a strengthening, not a weakening: recovery starts sooner, and the
        threshold still gates the heavier remedy.

        Constitutional requirements:
        - FR-018: 5 consecutive failures initiate reconnection
        - FR-018a(d): unverified book emits nothing
        """
        adapter = KrakenV2BookAdapter()
        adapter._reconnect = Mock()

        bad_snapshot = copy.deepcopy(SNAPSHOT_FRAME)
        bad_snapshot["data"][0]["checksum"] = 1  # never valid for this ladder

        for attempt in range(1, 5):
            out = await adapter.process_raw_frame(bad_snapshot)
            assert out == [], "an unvalidated snapshot must not emit"
            assert adapter._local_book.consecutive_failures == attempt
            adapter._reconnect.assert_not_called()

        # Fifth consecutive failure crosses the threshold.
        await adapter.process_raw_frame(bad_snapshot)
        assert adapter._local_book.consecutive_failures == 5
        adapter._reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_emission_until_fresh_snapshot_validates(self):
        """
        Test FR-018a(d): the no-emission window.

        NEW in WO-008b-A1 §1. From a checksum failure until a fresh snapshot is
        applied AND validates, NO MarketState may be emitted. A book in an
        unverified state must not price anything (Principle V).
        """
        adapter = KrakenV2BookAdapter()
        assert len(await adapter.process_raw_frame(SNAPSHOT_FRAME)) == 1

        corrupted = copy.deepcopy(UPDATE_MODIFY_LEVEL)
        corrupted["data"][0]["checksum"] = 999
        assert await adapter.process_raw_frame(corrupted) == []
        assert adapter._awaiting_resync is True

        # A well-formed incremental must STILL be refused: the book is unverified.
        assert await adapter.process_raw_frame(UPDATE_MODIFY_LEVEL) == [], (
            "incremental updates must not be trusted to repair an unverified book"
        )
        assert adapter._awaiting_resync is True

        # Only a VALIDATING snapshot reopens emission.
        states = await adapter.process_raw_frame(SNAPSHOT_FRAME)
        assert len(states) == 1, "a validated snapshot must close the window"
        assert adapter._awaiting_resync is False

    # ────────────────────────────────────────────────────────────────────
    # DELETED WO-008b-A1 §5: test_sequence_gap_triggers_resnapshot
    #
    # The Kraken v2 PUBLIC book channel transmits NO sequence number, so this
    # test's trigger condition CANNOT OCCUR in production. Under rule 0.1d that
    # makes it a FALSE GUARANTEE, not merely an obsolete test — it reported green
    # for a mechanism that never existed.
    #
    # NOT xfailed or skipped (rule 0.1b would require escalation for that, and it
    # would leave the false guarantee in the suite). Deleted outright.
    # Superseded by test_no_emission_until_fresh_snapshot_validates and
    # test_five_consecutive_failures_trigger_reconnect, which exercise checksum
    # divergence — the detector Kraken actually provides, and a broader one.
    # ────────────────────────────────────────────────────────────────────


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
        Test QuoteUpdate structural validation.

        REWIRED WO-008b-A1 §5 for the redesigned ladder-carrying entity. The
        `sequence` field is GONE — Kraken's public book channel never sent it.
        """
        quote = QuoteUpdate(
            symbol="BTC/USD",
            message_type=QuoteUpdate.TYPE_SNAPSHOT,
            bids=[(Decimal("65000.00"), Decimal("1.5"))],
            asks=[(Decimal("65005.00"), Decimal("2.0"))],
            checksum=12345,
            timestamp=datetime.now(UTC),
        )

        assert quote.validate_basic() is True
        assert quote.is_snapshot is True
        assert quote.bids[0][0] == Decimal("65000.00")
        assert quote.asks[0][0] == Decimal("65005.00")
        assert not hasattr(quote, "sequence"), (
            "sequence must not exist: Kraken v2 public book transmits no such field"
        )

    def test_quote_update_rejects_malformed(self):
        """A non-positive price or an empty snapshot side must fail validation."""
        bad_price = QuoteUpdate(
            symbol="BTC/USD", message_type=QuoteUpdate.TYPE_UPDATE,
            bids=[(Decimal("0"), Decimal("1.0"))], asks=[],
            checksum=1, timestamp=datetime.now(UTC),
        )
        assert bad_price.validate_basic() is False

        empty_snapshot = QuoteUpdate(
            symbol="BTC/USD", message_type=QuoteUpdate.TYPE_SNAPSHOT,
            bids=[], asks=[], checksum=1, timestamp=datetime.now(UTC),
        )
        assert empty_snapshot.validate_basic() is False

    def test_quote_update_accepts_qty_zero_as_deletion(self):
        """qty == 0 is Kraken's level-DELETION marker and must remain legal."""
        deletion = QuoteUpdate(
            symbol="BTC/USD", message_type=QuoteUpdate.TYPE_UPDATE,
            bids=[(Decimal("45283.5"), Decimal("0"))], asks=[],
            checksum=1, timestamp=datetime.now(UTC),
        )
        assert deletion.validate_basic() is True


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
