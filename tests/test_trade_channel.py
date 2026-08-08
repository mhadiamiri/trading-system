"""
WO-054 §2 — THE TRADE CHANNEL: merge semantics, no fabrication, partial-outage recording.

Fixtures only — no socket opens in this WO under any circumstance.

§0.10 — every test is single-purpose so a mutation can attribute its failure.
§0.12 — the outage tests are the falsifier for "no outage occurred": an empty availability ledger
means something only because these show the ledger CAN speak.
"""

from decimal import Decimal

import pytest

from trading.data.trade_channel import (
    SUBSCRIBE_ACK_TIMEOUT_SECONDS, TRADE_OUTAGE_CAUSES, TRADE_SPEC_RETRIEVED_UTC, TRADE_SPEC_URL,
    TradeChannelError, TradeChannelOutage, TradeEvent, TradeMerger, build_subscribe_message,
    build_unsubscribe_message, parse_trade_message,
)

T1 = "2026-08-05T22:00:01.000000+00:00"
T2 = "2026-08-05T22:00:02.000000+00:00"
T3 = "2026-08-05T22:00:03.000000+00:00"


def _msg(*trades):
    return {"channel": "trade", "type": "update", "data": list(trades)}


def _trade(price="64000.0", qty="0.01", tid=1, ts=T1):
    return {"symbol": "BTC/USD", "side": "buy", "qty": qty, "price": price,
            "ord_type": "market", "trade_id": tid, "timestamp": ts}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.1 THE CITED SUBSCRIPTION
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_subscribe_matches_the_cited_spec():
    assert build_subscribe_message("BTC/USD") == {
        "method": "subscribe",
        "params": {"channel": "trade", "symbol": ["BTC/USD"], "snapshot": False},
    }


def test_we_decline_the_historical_snapshot():
    """The snapshot delivers the most recent 50 trades — activity from BEFORE capture began.
    Merging it would fabricate the opening frame's count and volume out of pre-capture trades."""
    assert build_subscribe_message("BTC/USD")["params"]["snapshot"] is False


def test_unsubscribe_matches_the_cited_spec():
    assert build_unsubscribe_message("BTC/USD") == {
        "method": "unsubscribe", "params": {"channel": "trade", "symbol": ["BTC/USD"]},
    }


def test_the_citation_is_recorded_in_code():
    """0.1e: the spec is cited, not recalled. The URL and retrieval date travel with the code."""
    assert TRADE_SPEC_URL == "https://docs.kraken.com/api/docs/websocket-v2/trade"
    assert TRADE_SPEC_RETRIEVED_UTC == "2026-08-08"
    assert SUBSCRIBE_ACK_TIMEOUT_SECONDS == 10.0


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PARSING — every published field, and torn input skipped not guessed
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_parses_every_published_field():
    ev = parse_trade_message(_msg(_trade()))[0]
    assert ev == TradeEvent(symbol="BTC/USD", side="buy", qty=Decimal("0.01"),
                            price=Decimal("64000.0"), ord_type="market", trade_id=1, timestamp=T1)


def test_a_non_trade_message_yields_nothing():
    """The caller feeds every socket message; pre-filtering must not be its job."""
    assert parse_trade_message({"channel": "book", "data": [{"bids": []}]}) == []
    assert parse_trade_message({"method": "subscribe", "success": True}) == []


def test_a_malformed_entry_is_skipped_not_guessed():
    """Same treatment a torn JSONL line gets everywhere else: dropped, never repaired."""
    events = parse_trade_message(_msg(_trade(tid=1), {"symbol": "BTC/USD"}, _trade(tid=2)))
    assert [e.trade_id for e in events] == [1, 2]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.3 MERGE SEMANTICS — deltas, and the three states
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_counts_are_per_interval_deltas_not_running_totals():
    """THE SCHEMA DECISION a strategy would silently depend on. Deltas are recorded because any
    rolling window is derivable from them, while a stored rolling total cannot be un-rolled."""
    m = TradeMerger()
    m.observe(parse_trade_message(_msg(_trade(qty="0.01")))[0])
    m.observe(parse_trade_message(_msg(_trade(qty="0.02", tid=2)))[0])
    first = m.snapshot_for_frame(T2)
    assert first["count"] == 2 and first["volume"] == "0.03"

    m.observe(parse_trade_message(_msg(_trade(qty="0.005", tid=3)))[0])
    second = m.snapshot_for_frame(T3)
    assert second["count"] == 1, "the interval RESET; this is not a running total"
    assert second["volume"] == "0.005"


def test_an_interval_with_no_trades_reports_zero_and_a_null_last_price():
    """STATE 2 — listening, nothing traded. `0` is a POSITIVE CLAIM and is the true value; the
    price is null because there was no trade to price."""
    m = TradeMerger()
    snap = m.snapshot_for_frame(T2)
    assert snap["observable"] is True
    assert snap["count"] == 0 and snap["volume"] == "0"
    assert snap["last_price"] is None


def test_last_price_is_never_fabricated_for_a_tradeless_interval():
    """THE D48 SUBSTITUTION AT CAPTURE TIME — the defect this guard exists for. After a real trade,
    a subsequent tradeless interval must NOT inherit that price as its own `last_price`."""
    m = TradeMerger()
    m.observe(parse_trade_message(_msg(_trade(price="64000.0")))[0])
    assert m.snapshot_for_frame(T2)["last_price"] == "64000.0"

    quiet = m.snapshot_for_frame(T3)
    assert quiet["last_price"] is None, "a tradeless interval has NO last price of its own"
    assert quiet["running_last_price"] == "64000.0", "the carried value is separate and named"


def test_the_carried_price_reports_its_own_staleness():
    """`running_last_price` is useful only if a consumer can check how old it is."""
    m = TradeMerger()
    m.observe(parse_trade_message(_msg(_trade(price="64000.0", ts=T1)))[0])
    m.snapshot_for_frame(T1)
    later = m.snapshot_for_frame(T3)
    assert later["running_last_price_age_ms"] == 2000


def test_the_carried_price_is_null_before_the_first_trade_of_the_run():
    m = TradeMerger()
    snap = m.snapshot_for_frame(T2)
    assert snap["running_last_price"] is None
    assert snap["running_last_price_age_ms"] is None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.4 THE MISATTRIBUTION GUARD — null is not zero
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_bite_an_outage_reports_nulls_not_zeros():
    """THE BITE, and the whole point of the module.

    A corpus that wrote `count: 0` during an outage would say "no trades occurred" when it meant
    "the trade channel dropped" — the misattribution family, one channel over. `null` is the
    absence of a claim; `0` is a claim.
    """
    m = TradeMerger()
    m.mark_unobservable("TRADE_CHANNEL_DROPPED", T1, detail="venue unsubscribed the trade channel")
    snap = m.snapshot_for_frame(T2)
    assert snap["observable"] is False
    assert snap["count"] is None, "0 would assert that nothing traded; we could not see"
    assert snap["volume"] is None
    assert snap["last_price"] is None


def test_dual_a_healthy_channel_reports_real_numbers():
    """THE PRESERVATION DUAL (§0.4), local and direct. A merger that nulled everything would pass
    the bite and be useless — the guard must discriminate outage from quiet."""
    m = TradeMerger()
    m.observe(parse_trade_message(_msg(_trade(qty="0.5", price="64100.0")))[0])
    snap = m.snapshot_for_frame(T2)
    assert snap["observable"] is True
    assert snap["count"] == 1 and snap["volume"] == "0.5" and snap["last_price"] == "64100.0"


def test_the_carried_price_survives_an_outage_with_its_age():
    """Declared in the schema: nulling it would discard true information. `observable: False` is
    what stops a reader treating it as current."""
    m = TradeMerger()
    m.observe(parse_trade_message(_msg(_trade(price="64000.0", ts=T1)))[0])
    m.snapshot_for_frame(T1)
    m.mark_unobservable("TRADE_CHANNEL_DROPPED", T2)
    snap = m.snapshot_for_frame(T3)
    assert snap["running_last_price"] == "64000.0"
    assert snap["running_last_price_age_ms"] == 2000


def test_an_outage_opens_and_closes_in_the_availability_ledger():
    m = TradeMerger()
    m.mark_unobservable("TRADE_CHANNEL_SUBSCRIBE_FAILED", T1, detail="no ack within 10.0s")
    assert m.ledger()[0]["resolved"] is False
    m.mark_observable(T3)
    entry = m.ledger()[0]
    assert entry["resolved"] is True and entry["closed_utc"] == T3
    assert entry["cause"] == "TRADE_CHANNEL_SUBSCRIBE_FAILED"


def test_recovery_resumes_real_counting():
    m = TradeMerger()
    m.mark_unobservable("TRADE_CHANNEL_DROPPED", T1)
    m.mark_observable(T2)
    m.observe(parse_trade_message(_msg(_trade(qty="0.25")))[0])
    snap = m.snapshot_for_frame(T3)
    assert snap["observable"] is True and snap["count"] == 1 and snap["volume"] == "0.25"


def test_an_undeclared_outage_cause_is_refused():
    """The vocabulary discipline: an outage under an unnamed cause is an unattributable hole."""
    with pytest.raises(TradeChannelError, match="TRADE_CHANNEL_CAUSE_UNDECLARED"):
        TradeChannelOutage(cause="TRADE_CHANNEL_SILENT", opened_utc=T1)


def test_silence_is_not_a_declared_cause():
    """⚠ DELIBERATE. A subscribed channel that stops producing is indistinguishable from a market
    in which nothing traded. A silence timeout would fabricate outages on every quiet night — the
    same misattribution running backwards. Pinned so it cannot be added without confronting this."""
    assert TRADE_OUTAGE_CAUSES == ("TRADE_CHANNEL_SUBSCRIBE_FAILED", "TRADE_CHANNEL_DROPPED")
    assert not any("SILENT" in c for c in TRADE_OUTAGE_CAUSES)


def test_a_trade_arriving_during_a_recorded_outage_is_refused():
    """A contradiction between the availability ledger and the frames. Refusing beats silently
    choosing which one to believe — either choice makes the two disagree permanently."""
    m = TradeMerger()
    m.mark_unobservable("TRADE_CHANNEL_DROPPED", T1)
    with pytest.raises(TradeChannelError, match="TRADE_CHANNEL_CAUSE_UNDECLARED"):
        m.observe(parse_trade_message(_msg(_trade()))[0])


def test_a_partial_interval_is_discarded_when_the_channel_drops():
    """The interval was only partly observed; reporting it as a complete delta would understate
    activity by an unknown amount."""
    m = TradeMerger()
    m.observe(parse_trade_message(_msg(_trade(qty="0.9")))[0])
    m.mark_unobservable("TRADE_CHANNEL_DROPPED", T2)
    m.mark_observable(T2)
    snap = m.snapshot_for_frame(T3)
    assert snap["count"] == 0, "the partly-seen interval was dropped, not reported as complete"


def test_trade_outage_is_not_a_gap_cause():
    """§2.4: GAP_CAUSES is a RULED, EXHAUSTIVE set and a trade outage is not a gap — the book keeps
    emitting validated states. Recording one would subtract book coverage that was never lost."""
    from trading.data.adapters.kraken_v2_book import GAP_CAUSES
    for cause in TRADE_OUTAGE_CAUSES:
        assert cause not in GAP_CAUSES
    assert len(GAP_CAUSES) == 5, "the ruled four plus HOST_SUSPEND (WO-015 addendum A)"
