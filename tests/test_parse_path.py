"""
Parse-path tests (WO-008b-A1 §5).

RAW KRAKEN v2 FRAME -> parse -> book application -> MarketState.

This code path had NEVER been under test. Fixtures previously supplied
pre-parsed `QuoteUpdate` objects straight to `_process_quote_update`, so
`_parse_book_frame` was never called by anything, and the fixtures were free to
drift toward whatever the implementation expected rather than toward what Kraken
actually sends. That is how a synthetic `sequence` field — a protocol element the
v2 public book channel does not transmit — came to be "proven".

NO NETWORK. Every frame here is a static dict from
`tests/fixtures/kraken_v2_raw_frames.py`. Transport is WO-008b-A2.

Ground-truth status:
  - SNAPSHOT_FRAME carries Kraken's PUBLISHED checksum 3310070434. Tests using it
    are independently verified.
  - The three UPDATE frames carry SELF-GENERATED checksums; Kraken publishes no
    incremental example. They prove internal consistency only. Independent
    verification of the incremental path is deferred to first live contact (A2).
"""

import copy
from decimal import Decimal

import pytest

from tests.fixtures.kraken_v2_raw_frames import (
    SNAPSHOT_FRAME,
    UPDATE_MODIFY_LEVEL,
    UPDATE_DELETE_LEVEL_QTY_ZERO,
    UPDATE_NEW_LEVEL_CAUSES_TRUNCATION,
    SUBSCRIPTION_ACK_FRAME,
    HEARTBEAT_FRAME,
    TRUNCATED_OUT_BID_PRICE,
    SUBSCRIBED_DEPTH,
)
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, QuoteUpdate


class TestParseBookFrame:
    """The parser itself: raw dict envelope -> QuoteUpdate."""

    def test_parses_snapshot_envelope(self):
        """A v2 snapshot envelope yields one ladder-carrying QuoteUpdate."""
        adapter = KrakenV2BookAdapter()
        updates = adapter._parse_book_frame(SNAPSHOT_FRAME)

        assert len(updates) == 1
        update = updates[0]
        assert update.symbol == "BTC/USD"
        assert update.message_type == QuoteUpdate.TYPE_SNAPSHOT
        assert update.is_snapshot is True
        assert update.checksum == 3310070434, "Kraken's published ground-truth value"
        assert len(update.bids) == SUBSCRIBED_DEPTH
        assert len(update.asks) == SUBSCRIBED_DEPTH

    def test_parses_price_and_qty_as_exact_decimals(self):
        """
        Precision must survive parsing.

        The checksum is computed over the digits exactly as sent, so any float
        round-trip would corrupt it.
        """
        adapter = KrakenV2BookAdapter()
        update = adapter._parse_book_frame(SNAPSHOT_FRAME)[0]

        assert update.bids[0] == (Decimal("45283.5"), Decimal("0.10000000"))
        assert update.asks[0] == (Decimal("45285.2"), Decimal("0.00100000"))
        assert isinstance(update.bids[0][0], Decimal)

    def test_distinguishes_snapshot_from_update(self):
        """`type` must be carried through — the old fixtures omitted it entirely."""
        adapter = KrakenV2BookAdapter()
        snapshot = adapter._parse_book_frame(SNAPSHOT_FRAME)[0]
        update = adapter._parse_book_frame(UPDATE_MODIFY_LEVEL)[0]

        assert snapshot.is_snapshot is True
        assert update.is_snapshot is False
        assert update.message_type == QuoteUpdate.TYPE_UPDATE

    def test_carries_server_timestamp_not_client_clock(self):
        """The server timestamp is preserved, not replaced with local time."""
        adapter = KrakenV2BookAdapter()
        update = adapter._parse_book_frame(SNAPSHOT_FRAME)[0]
        assert update.timestamp == SNAPSHOT_FRAME["data"][0]["timestamp"]

    @pytest.mark.parametrize(
        "frame,label",
        [
            (SUBSCRIPTION_ACK_FRAME, "subscription ack"),
            (HEARTBEAT_FRAME, "heartbeat"),
            ({"channel": "trade", "type": "update", "data": []}, "other channel"),
            ({"channel": "book", "type": "bogus", "data": []}, "unknown type"),
            ("not a dict", "non-dict"),
        ],
    )
    def test_non_book_frames_are_ignored(self, frame, label):
        """Transport chatter must never reach the book."""
        adapter = KrakenV2BookAdapter()
        assert adapter._parse_book_frame(frame) == [], f"{label} must be ignored"

    def test_malformed_element_is_rejected_not_raised(self):
        """A malformed element is dropped and logged, not allowed to crash the feed."""
        adapter = KrakenV2BookAdapter()
        broken = copy.deepcopy(SNAPSHOT_FRAME)
        del broken["data"][0]["checksum"]

        assert adapter._parse_book_frame(broken) == []


class TestParsePathEndToEnd:
    """Raw frame -> parse -> book -> MarketState, through the real pipeline."""

    @pytest.mark.asyncio
    async def test_ground_truth_snapshot_validates_and_emits(self):
        """
        THE independently-verified proof in this file.

        Kraken's published snapshot must validate against its published checksum
        and produce a MarketState with the observed bid/ask.
        """
        adapter = KrakenV2BookAdapter()
        states = await adapter.process_raw_frame(SNAPSHOT_FRAME)

        assert len(states) == 1
        state = states[0]
        assert state.best_bid == Decimal("45283.5")
        assert state.best_ask == Decimal("45285.2")
        assert state.symbol == "BTC/USD"
        assert state.best_ask > state.best_bid, "spread must be positive"
        assert adapter._local_book.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_incremental_update_modifies_level(self):
        """An update amends the book and re-validates over the post-update ladder."""
        adapter = KrakenV2BookAdapter()
        await adapter.process_raw_frame(SNAPSHOT_FRAME)

        states = await adapter.process_raw_frame(UPDATE_MODIFY_LEVEL)

        assert len(states) == 1
        assert adapter._local_book.bids[0] == (Decimal("45283.5"), Decimal("0.25000000"))

    @pytest.mark.asyncio
    async def test_qty_zero_deletes_the_level(self):
        """
        `qty: 0` REMOVES a price level — Kraken's primary deletion mechanism.

        Never exercised by any fixture before WO-009.
        """
        adapter = KrakenV2BookAdapter()
        await adapter.process_raw_frame(SNAPSHOT_FRAME)
        assert len(adapter._local_book.bids) == 10
        assert adapter._local_book.bids[0][0] == Decimal("45283.5")

        states = await adapter.process_raw_frame(UPDATE_DELETE_LEVEL_QTY_ZERO)

        assert len(states) == 1, "a valid deletion still emits a MarketState"
        assert len(adapter._local_book.bids) == 9, "the level must be REMOVED"
        prices = [p for p, _ in adapter._local_book.bids]
        assert Decimal("45283.5") not in prices
        assert adapter._local_book.bids[0][0] == Decimal("45283.4"), "next level promoted"

    @pytest.mark.asyncio
    async def test_book_truncates_to_subscribed_depth(self):
        """
        A new best level pushes the worst one out, silently.

        Kraken does NOT send `qty: 0` for levels falling out of scope, so a client
        that truncates incorrectly diverges with no explicit signal — the checksum
        is the only thing that catches it.
        """
        adapter = KrakenV2BookAdapter()
        await adapter.process_raw_frame(SNAPSHOT_FRAME)

        states = await adapter.process_raw_frame(UPDATE_NEW_LEVEL_CAUSES_TRUNCATION)

        assert len(states) == 1
        assert len(adapter._local_book.bids) == SUBSCRIBED_DEPTH
        assert adapter._local_book.bids[0][0] == Decimal("45283.9"), "new best bid"
        prices = [str(p) for p, _ in adapter._local_book.bids]
        assert TRUNCATED_OUT_BID_PRICE not in prices, "worst level must be dropped"

    @pytest.mark.asyncio
    async def test_non_book_frame_emits_nothing(self):
        """Acks and heartbeats produce no MarketState and disturb no state."""
        adapter = KrakenV2BookAdapter()
        await adapter.process_raw_frame(SNAPSHOT_FRAME)
        depth_before = len(adapter._local_book.bids)

        assert await adapter.process_raw_frame(HEARTBEAT_FRAME) == []
        assert await adapter.process_raw_frame(SUBSCRIPTION_ACK_FRAME) == []
        assert len(adapter._local_book.bids) == depth_before

    @pytest.mark.asyncio
    async def test_checksum_is_validated_after_applying_not_before(self):
        """
        FR-018a(b): ordering is the guarantee.

        Direct evidence: the update fixtures' checksums were computed over the
        POST-update ladder. They validate under apply-then-check. Under the old
        check-then-apply ordering the pre-update ladder would be checksummed
        instead, which is a different value — so this passing at all demonstrates
        the ordering in force.

        HONEST LIMIT: this is self-consistency, NOT independent verification.
        The fixture checksum encodes our own ordering assumption on both sides.
        Only a real Kraken update frame can settle it — WO-008b-A2.
        """
        adapter = KrakenV2BookAdapter()
        await adapter.process_raw_frame(SNAPSHOT_FRAME)

        pre_update_bids, pre_update_asks = adapter._current_ladder_strings()
        pre_update_checksum = KrakenV2BookAdapter.compute_checksum(
            pre_update_bids, pre_update_asks
        )
        declared = UPDATE_MODIFY_LEVEL["data"][0]["checksum"]

        assert pre_update_checksum != declared, (
            "the pre-update ladder must NOT match the update's checksum — "
            "if it did, this test could not distinguish the two orderings"
        )

        states = await adapter.process_raw_frame(UPDATE_MODIFY_LEVEL)
        assert len(states) == 1, "post-update ladder must match the declared checksum"

        post_update_bids, post_update_asks = adapter._current_ladder_strings()
        assert KrakenV2BookAdapter.compute_checksum(
            post_update_bids, post_update_asks
        ) == declared
