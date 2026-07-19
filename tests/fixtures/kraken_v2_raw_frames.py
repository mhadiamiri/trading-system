"""
Raw Kraken v2 book frames (WO-009 §2).

These fixtures are **raw v2 dict envelopes matching Kraken's documented schema**
— what the WebSocket actually delivers on the wire. They are NOT pre-parsed
`QuoteUpdate` objects.

WHY THIS FILE EXISTS
--------------------
The Phase 1-3 fixtures supplied `QuoteUpdate` OBJECTS directly, so
`_parse_book_message` was never exercised by any test, and the fixtures drifted
toward whatever the implementation expected rather than toward what the venue
sends. That is how a synthetic `sequence` field — a protocol element Kraken's
public book channel does not transmit — came to be "proven".

Raw frames put the parse path under test. The fixtures now describe the
protocol, not the implementation.

PROVENANCE LABELLING — read before trusting any checksum here
-------------------------------------------------------------
Every fixture below is labelled either:

    # GROUND TRUTH: Kraken docs <url>
        the checksum is Kraken's own published value, independent of our code

    # SELF-GENERATED — not independent verification
        the checksum was computed by THIS project's compute_checksum(). It
        confirms internal consistency ONLY. It cannot detect a shared
        misunderstanding of Kraken's algorithm, because the same code produced
        both sides of the comparison.

**Kraken's documentation publishes a checksum for the SNAPSHOT case only.**
No documented UPDATE (incremental) message with a checksum value is available.
Therefore genuine independent verification of the INCREMENTAL path is NOT
possible from documentation, and becomes the job of first live contact in
WO-008b-A. This is stated plainly rather than papered over with another
self-generated value labelled as ground truth.

STATUS: fixtures only. No consumer exists yet — building the raw-frame parse
path is WO-008b-A. See evidence/WO-009/tests_requiring_rewire.txt.
"""

from __future__ import annotations

# Kraken accepts depth 10, 25, 100, 500 or 1000. This project pins depth 10
# (amended FR-018a §(e)): the CRC32 covers the top 10 levels per side
# regardless of subscribed depth, so 10 is the smallest legal value supplying
# exactly the ladder the checksum needs.
SUBSCRIBED_DEPTH = 10

SYMBOL = "BTC/USD"


# ═══════════════════════════════════════════════════════════════════════════
# 1. SNAPSHOT — GENUINE KRAKEN GROUND TRUTH
# ═══════════════════════════════════════════════════════════════════════════
# GROUND TRUTH: Kraken docs https://docs.kraken.com/api/docs/guides/spot-ws-book-v2/
# Every price, qty and the checksum below are copied verbatim from Kraken's
# published worked example. checksum 3310070434 is Kraken's own value.
SNAPSHOT_FRAME = {
    "channel": "book",
    "type": "snapshot",
    "data": [
        {
            "symbol": "BTC/USD",
            "bids": [
                {"price": "45283.5", "qty": "0.10000000"},
                {"price": "45283.4", "qty": "1.54582015"},
                {"price": "45282.1", "qty": "0.10000000"},
                {"price": "45281.0", "qty": "0.10000000"},
                {"price": "45280.3", "qty": "1.54592586"},
                {"price": "45279.0", "qty": "0.07990000"},
                {"price": "45277.6", "qty": "0.03310103"},
                {"price": "45277.5", "qty": "0.30000000"},
                {"price": "45277.3", "qty": "1.54602737"},
                {"price": "45276.6", "qty": "0.15445238"},
            ],
            "asks": [
                {"price": "45285.2", "qty": "0.00100000"},
                {"price": "45286.4", "qty": "1.54571953"},
                {"price": "45286.6", "qty": "1.54571109"},
                {"price": "45289.6", "qty": "1.54560911"},
                {"price": "45290.2", "qty": "0.15890660"},
                {"price": "45291.8", "qty": "1.54553491"},
                {"price": "45294.7", "qty": "0.04454749"},
                {"price": "45296.1", "qty": "0.35380000"},
                {"price": "45297.5", "qty": "0.09945542"},
                {"price": "45299.5", "qty": "0.18772827"},
            ],
            # GROUND TRUTH: Kraken's published checksum for the book above.
            "checksum": 3310070434,
            # Server-sent timestamp (NOT client-generated datetime.now(UTC)).
            "timestamp": "2026-07-19T14:00:00.000000Z",
        }
    ],
}

# Kraken's published intermediate strings for the snapshot above, retained so a
# checksum implementation can be debugged against the venue's own worked example
# rather than against our output.
# GROUND TRUTH: Kraken docs https://docs.kraken.com/api/docs/guides/spot-ws-book-v2/
GROUND_TRUTH_ASKS_STRING = (
    "45285210000045286415457195345286615457110945289615456091145290215890660"
    "452918154553491452947445474945296135380000452975994554245299518772827"
)
GROUND_TRUTH_BIDS_STRING = (
    "4528351000000045283415458201545282110000000452810100000004528031545925864527907990000"
    "45277633101034527753000000045277315460273745276615445238"
)


# ═══════════════════════════════════════════════════════════════════════════
# 2. UPDATE — MODIFY AN EXISTING LEVEL
# ═══════════════════════════════════════════════════════════════════════════
# SELF-GENERATED — not independent verification.
# Applies to SNAPSHOT_FRAME. Top bid 45283.5 qty 0.10000000 -> 0.25000000.
# Kraken publishes no incremental checksum example, so 2800903109 was computed
# by this project's own compute_checksum() over the POST-UPDATE book. It proves
# internal consistency only.
UPDATE_MODIFY_LEVEL = {
    "channel": "book",
    "type": "update",
    "data": [
        {
            "symbol": "BTC/USD",
            "bids": [{"price": "45283.5", "qty": "0.25000000"}],
            "asks": [],
            "checksum": 2800903109,  # SELF-GENERATED — not independent verification
            "timestamp": "2026-07-19T14:00:01.000000Z",
        }
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# 3. UPDATE — DELETION VIA qty: 0   (Kraken's primary level-removal mechanism)
# ═══════════════════════════════════════════════════════════════════════════
# SELF-GENERATED — not independent verification.
# Applies to SNAPSHOT_FRAME. qty "0.00000000" at 45283.5 REMOVES that level;
# it does not set the size to zero. The post-update book therefore holds 9 bids.
# This mechanism was never exercised by any prior fixture.
UPDATE_DELETE_LEVEL_QTY_ZERO = {
    "channel": "book",
    "type": "update",
    "data": [
        {
            "symbol": "BTC/USD",
            "bids": [{"price": "45283.5", "qty": "0.00000000"}],
            "asks": [],
            "checksum": 1166728830,  # SELF-GENERATED — not independent verification
            "timestamp": "2026-07-19T14:00:02.000000Z",
        }
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# 4. UPDATE — TRUNCATION TO SUBSCRIBED DEPTH
# ═══════════════════════════════════════════════════════════════════════════
# SELF-GENERATED — not independent verification.
# Applies to SNAPSHOT_FRAME. A new best bid 45283.9 is inserted. The book must
# be truncated back to SUBSCRIBED_DEPTH (10), which silently drops the worst
# bid 45276.6. Kraken does NOT send qty:0 for levels falling out of scope, so a
# client that truncates incorrectly diverges with no explicit signal — the
# checksum is the only thing that catches it.
UPDATE_NEW_LEVEL_CAUSES_TRUNCATION = {
    "channel": "book",
    "type": "update",
    "data": [
        {
            "symbol": "BTC/USD",
            "bids": [{"price": "45283.9", "qty": "0.50000000"}],
            "asks": [],
            "checksum": 3593913726,  # SELF-GENERATED — not independent verification
            "timestamp": "2026-07-19T14:00:03.000000Z",
        }
    ],
}

# The level silently dropped by fixture 4, for assertion convenience.
TRUNCATED_OUT_BID_PRICE = "45276.6"


# ═══════════════════════════════════════════════════════════════════════════
# 5. NON-BOOK FRAMES — the parse path must not treat these as book data
# ═══════════════════════════════════════════════════════════════════════════
# GROUND TRUTH (shape): Kraken docs https://docs.kraken.com/api/docs/websocket-v2/book/
SUBSCRIPTION_ACK_FRAME = {
    "method": "subscribe",
    "result": {"channel": "book", "depth": 10, "snapshot": True, "symbol": "BTC/USD"},
    "success": True,
    "time_in": "2026-07-19T13:59:59.000000Z",
    "time_out": "2026-07-19T13:59:59.001000Z",
}

HEARTBEAT_FRAME = {"channel": "heartbeat"}


# Convenience groupings ------------------------------------------------------

ALL_BOOK_FRAMES = [
    SNAPSHOT_FRAME,
    UPDATE_MODIFY_LEVEL,
    UPDATE_DELETE_LEVEL_QTY_ZERO,
    UPDATE_NEW_LEVEL_CAUSES_TRUNCATION,
]

GROUND_TRUTH_FRAMES = [SNAPSHOT_FRAME]

SELF_GENERATED_FRAMES = [
    UPDATE_MODIFY_LEVEL,
    UPDATE_DELETE_LEVEL_QTY_ZERO,
    UPDATE_NEW_LEVEL_CAUSES_TRUNCATION,
]
