"""
WO-050 §6 — BACKTEST ACCOUNTING: R1 the missing close, R3 real P&L, R4 distinct cost channels.

§0.9 — ASSERT THE ECONOMIC EFFECT, NOT THE EVENT RECORD. Every assertion below lands on a trade, a
cost, or a position — never on a flatten event or a log line. R1 exists precisely because a proof
checked a label and missed a missing trade; these do not repeat it.

§0.10 — SINGLE-PURPOSE TESTS IN THE DISCRIMINATION SETS. Tests here are deliberately narrow so a
mutation can attribute its failure. Broad contract tests live in `test_segmented_backtest.py` and
are excluded from the proof's discrimination sets, with the exclusion recorded in the proof.
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading.backtest.position_pnl import Position, PositionLedger
from trading.backtest.segmented import MIN_ELIGIBLE_SEGMENT_FRAMES, SegmentedBacktestRunner
from trading.data.book_state import BookState
from trading.data.corpus_reader import CorpusReader
from trading.execution.paper import PaperExecutionClient
from trading.strategy.book_imbalance import BookImbalanceStrategy

UTC = timezone.utc
ANCHOR_WALL = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
ANCHOR_MONO = 1000.0
RUN_ID = "run_a"


def _wall(s):
    return ANCHOR_WALL + timedelta(seconds=s)


def _frame(ts, bid, ask, bq, aq):
    return {"timestamp": ts.isoformat(), "symbol": "BTC/USD", "bid": str(bid), "ask": str(ask),
            "bid_qty": str(bq), "ask_qty": str(aq),
            "spread": str(Decimal(str(ask)) - Decimal(str(bid)))}


def _build(tmp_path, frames):
    corpus = tmp_path / "c"
    run = corpus / RUN_ID
    run.mkdir(parents=True)
    (run / "gap_ledger.json").write_text("\n".join([
        json.dumps({"event": "run_start", "run_wall_anchor": ANCHOR_WALL.isoformat(),
                    "run_monotonic_anchor": ANCHOR_MONO, "run_start_monotonic": ANCHOR_MONO,
                    "venue": "kraken_mainnet", "mode": "live"}),
        json.dumps({"event": "run_end", "run_end_monotonic": ANCHOR_MONO + 100_000,
                    "frames_captured": len(frames), "gaps_detected": 0, "incomplete": 0}),
    ]) + "\n", encoding="utf-8")
    (run / "corpus_H_20260801T12Z.jsonl").write_text(
        "\n".join(json.dumps(f) for f in frames) + "\n", encoding="utf-8")
    return corpus


def _bid_heavy(n, start_s=0):
    """Persistently bid-heavy -> the strategy goes long and holds a position at segment end."""
    return [_frame(_wall(start_s + i * 0.1), 64000, 64001, "9.0", "1.0") for i in range(n)]


def _balanced(n, start_s=0):
    """Balanced -> imbalance 0 -> HOLD -> the segment ends already flat."""
    return [_frame(_wall(start_s + i * 0.1), 64000, 64001, "1.0", "1.0") for i in range(n)]


async def _run(corpus):
    reader = CorpusReader(corpus)
    window = reader.read_window(_wall(0), _wall(50_000))
    return await SegmentedBacktestRunner(corpus).run(window)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §6.1 R1 — THE CLOSE EXISTS AND COSTS MONEY
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_r1_bite_a_segment_ending_long_produces_a_costed_closing_trade(tmp_path):
    """BITE (single-purpose). A segment that ends holding a position must produce a REAL closing
    TRADE — not a zeroed variable.

    Asserted on the LEDGER: a trade flagged `boundary_close` exists, it has non-zero cost, it is on
    the reducing side, it is stamped at the boundary frame's MARKET time, and the position ends at
    exactly zero. Asserting the flatten EVENT would pass even with no trade at all — which is the
    defect this replaces.
    """
    n = MIN_ELIGIBLE_SEGMENT_FRAMES + BookImbalanceStrategy.WINDOW_TICKS + 200
    frames = _bid_heavy(n)
    corpus = _build(tmp_path, frames)
    result = await _run(corpus)

    seg = result["segments"][0]
    assert seg["trades"] > 0
    assert seg["force_flattened"] is True

    # THE ECONOMIC EFFECT — a real closing trade exists.
    assert seg["boundary_closes"] == 1, "exactly one boundary close per segment that ends open"
    assert result["aggregate"]["boundary_closes"] == 1

    # The position ends at EXACTLY zero, and unrealised is exactly zero (§3.2 — R1's independent
    # check: a non-zero residual would mean the close never executed).
    assert Decimal(seg["final_quantity"]) == 0
    assert Decimal(seg["unrealised_pnl_at_close"]) == 0

    # The close is attributable and carries real economics.
    ev = next(e for e in result["boundary_events"] if e["event"] == "SEGMENT_CLOSE_FORCE_FLAT")
    assert ev["close_side"] == "SELL", "a long position closes by SELLing"
    assert Decimal(ev["close_cost"]) > 0, "the close COSTS MONEY — fees and slippage are real"
    assert Decimal(ev["quantity_flattened"]) > 0
    # MARKET time (D-a): the close is stamped at the boundary frame, not the replay clock.
    assert ev["close_fill_timestamp"] == frames[-1]["timestamp"]
    assert ev["utc"] == frames[-1]["timestamp"]


@pytest.mark.asyncio
async def test_r1_dual_a_segment_ending_flat_produces_no_spurious_close(tmp_path):
    """PRESERVATION DUAL (single-purpose). A segment that never opened a position must NOT emit a
    close. A runner that closed unconditionally would pass the bite and invent trades from nothing.
    """
    n = MIN_ELIGIBLE_SEGMENT_FRAMES + BookImbalanceStrategy.WINDOW_TICKS + 50
    corpus = _build(tmp_path, _balanced(n))
    result = await _run(corpus)

    seg = result["segments"][0]
    assert seg["trades"] == 0, "a balanced book yields no signal, so no trades"
    assert seg["force_flattened"] is False
    assert seg["boundary_closes"] == 0
    assert result["aggregate"]["boundary_closes"] == 0
    assert not [e for e in result["boundary_events"]
                if e["event"] == "SEGMENT_CLOSE_FORCE_FLAT"], "no spurious close"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §6.2 R3 — THE P&L IS POSITION-AWARE
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_r3_bite_a_round_trip_realises_the_correct_pnl():
    """BITE (single-purpose). Buy then sell: realised P&L must be the PRICE DIFFERENCE, not the sum
    of notionals.

    THE DISCRIMINATING CASE. Buy 1 @ 100, sell 1 @ 110:
      average-cost realised P&L = (110 − 100) × 1 = **+10**
      unmatched cash flow       = −100 + 110      = **+10**   ← identical, useless as a test
    So the fixture uses a case where they DIVERGE — buy 2 @ 100, sell 1 @ 110:
      average-cost realised      = (110 − 100) × 1 = **+10**
      unmatched cash flow        = −200 + 110      = **−90**
    The old figure calls a profitable partial close a 90-unit loss, because it books the whole
    purchase as an expense and never matches it against the holding.
    """
    p = Position()
    p = p.apply("BUY", Decimal("2"), Decimal("100"))
    assert p.quantity == Decimal("2") and p.average_cost == Decimal("100")

    p = p.apply("SELL", Decimal("1"), Decimal("110"))
    assert p.realised_pnl == Decimal("10"), "realised on the CLOSED quantity, against average cost"
    assert p.quantity == Decimal("1"), "one unit still held"
    assert p.average_cost == Decimal("100"), "the remainder keeps its basis — a partial close does "
    # ...not re-price what is left.

    # Unrealised is mark-to-market on what remains, and it is NOT realised.
    assert p.unrealised_pnl(Decimal("110")) == Decimal("10")
    assert p.realised_pnl == Decimal("10")


def test_r3_average_cost_reweights_on_increase_and_realises_nothing():
    """Increasing a position realises NOTHING — buying more of what you hold is not a result."""
    p = Position().apply("BUY", Decimal("1"), Decimal("100"))
    p = p.apply("BUY", Decimal("1"), Decimal("200"))
    assert p.average_cost == Decimal("150"), "volume-weighted"
    assert p.realised_pnl == Decimal("0"), "no P&L realises on an increase"


def test_r3_a_short_realises_the_opposite_sign():
    """Closing a SHORT realises (entry − exit): sell high, buy back low, profit."""
    p = Position().apply("SELL", Decimal("1"), Decimal("200"))
    assert p.quantity == Decimal("-1") and p.average_cost == Decimal("200")
    p = p.apply("BUY", Decimal("1"), Decimal("150"))
    assert p.realised_pnl == Decimal("50"), "shorted at 200, covered at 150 -> +50"
    assert p.quantity == 0 and p.average_cost == 0


def test_r3_crossing_zero_does_not_carry_the_old_basis():
    """A sign flip must close the old position and open a NEW one at the trade price.

    Silently keeping the old average cost here would carry a long's basis into a short — a whole
    position priced against a number from the other side of the book.
    """
    p = Position().apply("BUY", Decimal("1"), Decimal("100"))
    p = p.apply("SELL", Decimal("3"), Decimal("120"))
    assert p.realised_pnl == Decimal("20"), "the long closed at +20"
    assert p.quantity == Decimal("-2"), "and a 2-unit short opened"
    assert p.average_cost == Decimal("120"), "at the TRADE price, not the old long's basis"


def test_r3_unrealised_is_exactly_zero_when_flat():
    """§3.2: flat means zero unrealised, by construction rather than by rounding."""
    p = Position()
    assert p.unrealised_pnl(Decimal("64000")) == Decimal("0")
    p = p.apply("BUY", Decimal("1"), Decimal("100")).apply("SELL", Decimal("1"), Decimal("100"))
    assert p.is_flat and p.unrealised_pnl(Decimal("999999")) == Decimal("0")


def test_r3_net_is_realised_minus_costs_with_channels_attributed():
    """§3.3: net = realised − (fees + slippage). Spread is attribution and never additive."""
    led = PositionLedger()
    led.apply_fill({"side": "BUY", "size": 1, "fill_price": 100,
                    "fees": 1, "slippage_cost": 2, "spread_cost": 99})
    led.apply_fill({"side": "SELL", "size": 1, "fill_price": 110,
                    "fees": 1, "slippage_cost": 2, "spread_cost": 99})
    assert led.realised_pnl == Decimal("10")
    assert led.fees == Decimal("2") and led.slippage == Decimal("4")
    assert led.total_costs == Decimal("6"), "spread (198) is NOT in total costs"
    assert led.net_pnl() == Decimal("4"), "10 realised − 6 costs"
    assert led.summary()["method"] == "average_cost"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §6.3 / §4.2 R4 — DISTINCT COST CHANNELS
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_r4_fees_and_slippage_differ_under_the_defaults():
    """PERMANENT GUARD (§4.2). WO-048 reported total_fees == total_slippage_cost == 22,572,628.06
    to the cent, because `fee_rate_pct = 0.1` (a PERCENT) and `slippage_factor = 0.001` (a FRACTION)
    are the same 0.1% of notional. Two channels that always agree cannot be told apart, and a real
    divergence between them would be invisible.

    Cheap, permanent, and it stops the coincidence returning silently.
    """
    fee_fraction = PaperExecutionClient.DEFAULT_FEE_RATE_PCT / Decimal("100")
    slip_fraction = PaperExecutionClient.DEFAULT_SLIPPAGE_FACTOR
    assert fee_fraction != slip_fraction, (
        f"fee and slippage defaults are numerically identical ({fee_fraction}) — the WO-048 "
        f"coincidence has returned"
    )


@pytest.mark.asyncio
async def test_r4_a_real_fill_produces_different_fee_and_slippage():
    """The economic effect, not just the constants: an actual fill must show the two apart."""
    client = PaperExecutionClient()
    client.set_market_state(BookState(
        timestamp=_wall(0), symbol="BTC/USD",
        best_bid=Decimal("64000"), best_ask=Decimal("64001"),
        best_bid_size=Decimal("9"), best_ask_size=Decimal("1")))
    fill = await client.place_order("BTC/USD", "BUY", 0.1, 0.0, kill_switch_engaged=False)
    assert fill["fees"] != fill["slippage_cost"], "the two channels must be distinguishable"
    assert fill["fees"] > fill["slippage_cost"], (
        "fees dominate for liquid top-of-book trading, per the declared rates"
    )
    assert fill["fees"] > 0 and fill["slippage_cost"] > 0


def test_r4_the_rates_carry_their_declared_values():
    """The derivation lives in the code comment; these pin the values it derives."""
    assert PaperExecutionClient.DEFAULT_FEE_RATE_PCT == Decimal("0.26")
    assert PaperExecutionClient.DEFAULT_SLIPPAGE_FACTOR == Decimal("0.0001")


def test_r4_the_one_cost_implementation_is_unchanged():
    """§4.3: defaults changed, ARITHMETIC did not. `compute_execution_costs` stays the sole model
    and total = fees + slippage, with spread as attribution only (WO-011 reconciliation intact)."""
    from trading.execution.costs import compute_execution_costs
    state = BookState(timestamp=_wall(0), symbol="BTC/USD",
                      best_bid=Decimal("64000"), best_ask=Decimal("64001"),
                      best_bid_size=Decimal("9"), best_ask_size=Decimal("1"))
    c = compute_execution_costs("BUY", Decimal("0.1"), state,
                                fee_rate_pct=Decimal("0.26"), slippage_factor=Decimal("0.0001"))
    assert c.total_cost == c.fees + c.slippage_cost, "total is fees + slippage, spread excluded"
    assert c.executed_price == state.best_ask, "BUY pays the ask (WO-008a-R6)"
    assert c.spread_cost == (state.spread / 2) * Decimal("0.1")
