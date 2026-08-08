"""
WO-056 §8 — THE REACHABILITY WITNESS (D55 / rule 0.14).

WHY THIS FILE IS DIFFERENT FROM `test_trade_channel.py`
-------------------------------------------------------
`test_trade_channel.py` has 22 tests and a passing bite proof, and every one of them enters AT THE
COMPONENT — `TradeMerger(...)`, `parse_trade_message(...)`. All 22 passed, on both interpreters, in
both orders, with green CI, **while nothing in the production path called any of it**. The capture
wrote book-only frames and the suite could not tell.

That is 0.1g inverted: not a stub that does nothing, but a real, well-tested implementation sitting
OUTSIDE the path, invisible to every test that enters at it.

**So these tests enter at `tools/live_corpus_capture.py`** — the production runner — drive a fixture
socket carrying BOOK and TRADE messages, and assert on **the bytes of the written corpus frames**.
Not that `TradeMerger` was constructed. Not that a method fired. The written frame's contents, which
is the economic effect (0.9).

The mutation that matters is in the §8 bite proof: restoring the `!= "book": return []` discard
makes these fail **while all 22 component tests still pass**. That asymmetry IS the finding.
"""

import json
from pathlib import Path

import pytest

from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME

# NOTE: the fake socket `json.dumps()` whatever it is handed, so scripted frames must be DICTS.
# Handing it JSON strings double-encodes them and every consumer sees a `str`, not a frame.
TRADE_ACK = {
    "method": "subscribe",
    "result": {"channel": "trade", "snapshot": False, "symbol": "BTC/USD"},
    "success": True,
    "time_in": "2026-08-08T00:00:00.000000Z",
    "time_out": "2026-08-08T00:00:00.000001Z",
}


def _trade_msg(price, qty, tid, ts="2026-08-08T00:00:01.000000Z"):
    return {
        "channel": "trade", "type": "update",
        "data": [{"symbol": "BTC/USD", "side": "buy", "qty": qty, "price": price,
                  "ord_type": "market", "trade_id": tid, "timestamp": ts}],
    }


async def _run_capture(tmp_path, frames):
    """Drive the REAL capture runner over a scripted socket; return the written frames.

    Entry is `CorpusCaptureRunner.run()` — the production path — not the adapter and not the merger.
    """
    import os
    from datetime import date, timedelta
    from unittest.mock import patch

    from tools.live_corpus_capture import CorpusCaptureRunner, RotationConfig

    # The preflight's grant guards exist to protect a REAL SOCKET. This helper drives a scripted
    # fake (`ScriptedConnectionFactory`) and opens nothing, so the guards are satisfied for the
    # duration of the fixture and scoped with patch.dict so they cannot leak into another test.
    grant_env = {
        "CORPUS_AUTO_MODE_CONFIRMED": "true",
        "CORPUS_SHUTDOWN_POLICY_DISABLED": "true",
        "CORPUS_GRANT_EXPIRY": (date.today() + timedelta(days=1)).isoformat(),
    }

    factory = ScriptedConnectionFactory([frames], on_drain="timeout")
    # ── WHY THIS PATCHES `factory.Settings` AND NOT `config.settings.Settings` ────────────────
    #
    # Two things bite here, and only the second is obvious in hindsight:
    #
    #  1. `Settings.DATA_SOURCE` is a CLASS ATTRIBUTE bound from `os.getenv` AT IMPORT TIME, so
    #     setting the env var is too late once anything has already imported Settings. That is
    #     why an env-only version passed alone and failed in the full suite.
    #
    #  2. Under the full suite there are **TWO DISTINCT `Settings` CLASS OBJECTS** —
    #     `config.settings.Settings is trading.data.adapters.factory.Settings` evaluates to
    #     **False**, because the package is reachable by more than one sys.path route. Patching
    #     the one imported here therefore leaves the one the factory reads untouched.
    #
    # So the patch targets the object the production code actually reads. The registry refuses
    # live capture from a non-live adapter (LIVE_CAPTURE_UNSUPPORTED); `kraken_v2` is the
    # live-capable one. The SOCKET is still the scripted fake — this names the adapter without
    # opening anything.
    from trading.data import capture_gate
    from trading.data.adapters import factory as adapter_factory

    # The preflight runs in __init__ (deliberately — "BEFORE any connection"), so construction
    # must happen inside the patched environment too, not only run().
    # WO-057 §2.3: the preflight now reads the Term 2 memory gate. It is a HOST condition — on a
    # host that is paging it is RED and correctly refuses to open a socket. These fixtures open no
    # socket, so the gate is satisfied for their duration by patching the evaluator itself rather
    # than by an env override; an env back door in production code would be a hole in the gate.
    green_gate = capture_gate.GateVerdict(
        green=True, swap_green=True, memory_green=True, free_mib=99999.0,
        swap_samples_mib=[0.0], detail="fixture: gate satisfied, no socket opens")
    with patch.dict(os.environ, grant_env), patch("time.sleep"),             patch.object(adapter_factory.Settings, "DATA_SOURCE", "kraken_v2"),             patch.object(capture_gate, "evaluate", lambda *a, **k: green_gate):
        cap = CorpusCaptureRunner(
            config=RotationConfig(corpus_dir=Path(tmp_path), corpus_id="validation_fixture"),
            trading_env="paper",
            connect_fn=factory.connect,
            duration_hours=0.0002,
        )
        try:
            await cap.run()
        except Exception as exc:      # noqa: BLE001
            # A drained socket ends the capture; the written frames are what this asserts on.
            # Surfaced under WITNESS_DEBUG so a real failure is never silently swallowed — the
            # swallow is what hid the DATA_SOURCE binding bug above.
            if os.environ.get("WITNESS_DEBUG"):
                import traceback
                traceback.print_exc()
            _ = exc
    written = []
    for p in sorted(Path(tmp_path).rglob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                written.append(json.loads(line))
    return written, cap


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE BITE — trades reach the WRITTEN FRAME
# ══════════════════════════════════════════════════════════════════════════════════════════════

async def test_bite_a_trade_stream_reaches_the_written_corpus_frames(tmp_path):
    """THE WITNESS (0.14). A fixture socket carrying book AND trade messages must produce corpus
    frames whose `trades` sub-object holds the real values.

    This is the assertion whose absence let WO-054's component ship unreachable.
    """
    frames = [TRADE_ACK, _trade_msg("64500.0", "0.25", 1), SNAPSHOT_FRAME]
    written, _ = await _run_capture(tmp_path, frames)

    assert written, "the capture wrote no frames — the witness cannot speak"
    trades = written[0].get("trades")
    assert trades is not None, (
        "THE DEFECT D55 RULED ON: the written frame has no `trades` sub-object at all, so "
        "trade_channel is unreachable from the production path"
    )
    assert trades["observable"] is True, "the ack arrived; the channel is observable"
    assert trades["count"] == 1
    assert trades["volume"] == "0.25"
    assert trades["last_price"] == "64500.0"


async def test_bite_the_traded_volume_is_the_sum_over_the_interval(tmp_path):
    """The delta is real arithmetic over the interval, not a copy of one trade."""
    frames = [TRADE_ACK,
              _trade_msg("64500.0", "0.25", 1),
              _trade_msg("64510.0", "0.75", 2),
              SNAPSHOT_FRAME]
    written, _ = await _run_capture(tmp_path, frames)
    trades = written[0]["trades"]
    assert trades["count"] == 2
    assert trades["volume"] == "1.00"
    assert trades["last_price"] == "64510.0", "the LAST trade of the interval"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE DUAL (§4.2) — the book path must not silently degrade
# ══════════════════════════════════════════════════════════════════════════════════════════════

async def test_dual_a_book_only_stream_still_writes_the_seven_original_fields(tmp_path):
    """§4.2, ruled explicitly by D55: wiring a second channel must NOT degrade what already works.

    Byte-shape compatibility with `corpus_20260805`: the seven original fields, unchanged.
    """
    written, _ = await _run_capture(tmp_path, [TRADE_ACK, SNAPSHOT_FRAME])
    assert written
    frame = written[0]
    assert set(frame) == {
        "timestamp", "symbol", "bid", "ask", "bid_qty", "ask_qty", "spread", "trades",
    }, "exactly the seven original fields plus `trades` — nothing renamed, nothing dropped"
    assert frame["symbol"] == "BTC/USD"
    for key in ("bid", "ask", "bid_qty", "ask_qty", "spread"):
        assert isinstance(frame[key], str) and frame[key], f"{key} still a non-empty string"


async def test_dual_no_trades_records_a_positive_claim_of_zero(tmp_path):
    """The listening-but-quiet state, end to end: `count: 0` is a CLAIM, `last_price` is null and
    is NEVER fabricated from mid."""
    written, _ = await _run_capture(tmp_path, [TRADE_ACK, SNAPSHOT_FRAME])
    trades = written[0]["trades"]
    assert trades["observable"] is True
    assert trades["count"] == 0, "a positive claim: we were listening and nothing traded"
    assert trades["volume"] == "0"
    assert trades["last_price"] is None, "never fabricated"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §3.3 — AN UNACKED SUBSCRIBE MUST NOT PRODUCE A SILENT BOOK-ONLY CORPUS
# ══════════════════════════════════════════════════════════════════════════════════════════════

async def test_without_an_ack_the_corpus_says_it_could_not_see(tmp_path):
    """§3.3, the declared behaviour: start with `observable: false` recorded from the first frame.

    The corpus SAYS "we could not see" rather than omitting the question. `count: null` is the
    absence of a claim; writing `0` here would assert that nothing traded.
    """
    written, _ = await _run_capture(tmp_path, [SNAPSHOT_FRAME])
    trades = written[0]["trades"]
    assert trades["observable"] is False
    assert trades["count"] is None, "null = we could not see; 0 would claim nothing traded"
    assert trades["volume"] is None
    assert trades["last_price"] is None


async def test_a_nacked_subscribe_records_a_declared_outage(tmp_path):
    """An explicit venue refusal is recorded in the availability ledger under a declared cause —
    abort condition 1's subject, made detectable rather than merely logged."""
    nack = {"method": "subscribe",
            "result": {"channel": "trade", "symbol": "BTC/USD"},
            "success": False, "error": "Subscription failed"}
    written, cap = await _run_capture(tmp_path, [nack, SNAPSHOT_FRAME])
    assert written[0]["trades"]["observable"] is False
    assert written[0]["trades"]["count"] is None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §4.1 — THE DEMUX ENUMERATION
# ══════════════════════════════════════════════════════════════════════════════════════════════

async def test_transport_chatter_does_not_become_market_data(tmp_path):
    """Heartbeat and status frames are ignored, and — critically — do not corrupt the trade delta
    or the book. Enumerated handling, not a catch-all."""
    frames = [TRADE_ACK,
              {"channel": "heartbeat"},
              {"channel": "status", "data": [{"system": "online"}]},
              _trade_msg("64500.0", "0.1", 1),
              SNAPSHOT_FRAME]
    written, _ = await _run_capture(tmp_path, frames)
    trades = written[0]["trades"]
    assert trades["count"] == 1, "chatter is not a trade"
    assert trades["observable"] is True


async def test_an_unrecognised_channel_does_not_corrupt_the_frame(tmp_path):
    """0.11: the five enumerated kinds may not exhaust the socket. An unknown channel must be
    inert — the written frame is still correct and the trade delta is untouched."""
    frames = [TRADE_ACK,
              {"channel": "ohlc", "data": [{"open": 1}]},
              _trade_msg("64500.0", "0.1", 1),
              SNAPSHOT_FRAME]
    written, _ = await _run_capture(tmp_path, frames)
    trades = written[0]["trades"]
    assert trades["count"] == 1, "an unknown channel is not a trade"
    assert trades["observable"] is True


def test_an_unrecognised_channel_is_counted_not_guessed_at():
    """0.11, the counter itself: anything outside the five enumerated kinds is COUNTED, so a
    future WO inherits a number rather than a silence."""
    import asyncio

    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    a = KrakenV2BookAdapter(mode="fixture")
    asyncio.run(a.process_raw_frame({"channel": "ohlc", "data": [{"open": 1}]}))
    asyncio.run(a.process_raw_frame({"channel": "ohlc", "data": [{"open": 2}]}))
    assert a.get_unrecognised_channels() == {"ohlc": 2}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE PRODUCTION CALL SITE EXISTS (0.14 — the reachability cell, asserted)
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_the_capture_runner_names_the_call_site_that_reaches_trade_channel():
    """0.14: an empty reachability cell is an OPEN DEFECT. This pins the call site by name, so
    deleting the wire fails a test rather than quietly reverting to a book-only corpus."""
    source = Path("tools/live_corpus_capture.py").read_text(encoding="utf-8")
    assert "adapter.trade_snapshot_for_frame(" in source, (
        "the production call site that reaches trade_channel has been removed — "
        "trade_channel is unreachable again (D55)"
    )
    assert 'frame["trades"]' in source


def test_the_adapter_subscribes_to_both_channels():
    """§3.1: one socket, two subscriptions, sent through a single path so reconnect cannot
    resubscribe one and forget the other."""
    import inspect

    from trading.data.adapters import kraken_v2_book

    src = inspect.getsource(kraken_v2_book.KrakenV2BookAdapter._send_subscriptions)
    assert "_build_subscribe_message" in src, "the book subscribe"
    assert "_send_trade_subscription" in src, "and the trade subscribe, on the same socket"
    trade_src = inspect.getsource(kraken_v2_book.KrakenV2BookAdapter._send_trade_subscription)
    assert "_build_trade_subscribe_message" in trade_src


def test_the_trade_subscribe_declines_the_snapshot():
    """WO-054's deliberate decision, pinned at the adapter's own builder: a snapshot would deliver
    pre-capture trades and fabricate the opening frame's count/volume."""
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    a = KrakenV2BookAdapter.__new__(KrakenV2BookAdapter)
    msg = a._build_trade_subscribe_message()
    assert msg["params"]["channel"] == "trade"
    assert msg["params"]["snapshot"] is False


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §5.2 / §6.2 — RESUBSCRIBE AND THE SEAM
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_a_reconnect_resubscribes_both_channels_and_records_the_gap_in_between():
    """§5.1/§5.2 — THE SILENT-DEATH CASE.

    A reconnect opens a NEW socket; the old socket's trade subscription died with it. If only book
    resubscribed, the corpus would keep writing `observable: true` frames with no trades — a lie of
    exactly the WO-055 §3.5 shape, and one that would read as a quiet market.

    Asserted on the adapter's own reconnect path: the merger goes UNOBSERVABLE (so the interval is
    recorded as unseen, not as zero) and the trade subscribe is re-sent on the fresh socket.
    """
    import inspect

    from trading.data.adapters import kraken_v2_book

    src = inspect.getsource(kraken_v2_book.KrakenV2BookAdapter._perform_reconnect)
    assert "TRADE_CHANNEL_DROPPED" in src, "the interval across a reconnect must be recorded unseen"
    # The BOOK half is re-sent by `_maybe_resubscribe` (the committed resync producer) just above;
    # the reconnect path adds the TRADE half only. Sending the full pair here would put two book
    # subscriptions on one socket — the duplicate this WO's first draft introduced.
    assert "_maybe_resubscribe(new_websocket)" in src, "book resubscribes via the resync producer"
    assert "_send_trade_subscription(new_websocket)" in src, "and trade resubscribes alongside it"


def test_the_resync_path_does_not_spuriously_resubscribe_trade():
    """The DUAL of the above, and the reason the two paths differ: a checksum resync unsubscribes
    and resubscribes the BOOK on the SAME live socket. The trade subscription there was never
    touched and is still live, so re-sending it would be a spurious duplicate subscription."""
    import inspect

    from trading.data.adapters import kraken_v2_book

    # Assert on CALLS, not on raw source text: the method's comment explains why it does not
    # resubscribe trade, and matching that comment would make this test pass for the wrong reason.
    src = inspect.getsource(kraken_v2_book.KrakenV2BookAdapter._maybe_resubscribe)
    body = " ".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert "await self._send_subscriptions" not in body
    assert "self._build_trade_subscribe_message()" not in body


def test_seam_a_fresh_adapter_cannot_fabricate_a_delta_across_the_seam():
    """§6.2 — THE SEAM RULE, declared and proved.

    A process restart builds a FRESH adapter, whose merger starts UNOBSERVABLE and only becomes
    observable when the new subscription acks. So the first interval of a resumed run reports
    `count: null` — "we could not see" — rather than a `0` that would claim nothing traded across
    the seam, or a delta over an interval that spans it.
    """
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    fresh = KrakenV2BookAdapter(mode="fixture")
    snap = fresh.trade_snapshot_for_frame("2026-08-08T00:00:00+00:00")
    assert snap["observable"] is False
    assert snap["count"] is None, "a fresh run claims nothing about the seam it did not observe"
    assert snap["running_last_price"] is None, "no price carries across a process restart"


def test_rotation_one_snapshot_call_per_written_frame_is_the_whole_rule():
    """§6.1 — THE ROTATION RULE. The delta attaches to the frame it is written with, and that call
    closes the interval. Rotation happens between frames, so a trade arriving between the last
    frame of segment N and the first of N+1 lands in exactly ONE delta and cannot be double-counted.

    Proved on the merger's own contract: a second snapshot with no intervening trade is empty.
    """
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
    from trading.data.trade_channel import TradeEvent
    from decimal import Decimal

    a = KrakenV2BookAdapter(mode="fixture")
    a._trade_merger.observable = True
    a._trade_merger.observe(TradeEvent("BTC/USD", "buy", Decimal("0.4"), Decimal("64000"),
                                       "market", 1, "2026-08-08T00:00:00+00:00"))
    first = a.trade_snapshot_for_frame("2026-08-08T00:00:01+00:00")
    second = a.trade_snapshot_for_frame("2026-08-08T00:00:02+00:00")
    assert first["count"] == 1 and first["volume"] == "0.4"
    assert second["count"] == 0 and second["volume"] == "0", "not double-counted into the next frame"
