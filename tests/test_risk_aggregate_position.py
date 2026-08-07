"""
WO-049 §4 (D49) — `max_position_btc` IS THE AGGREGATE POSITION CAP.

D49, verbatim: *"A limit that bounds each order but not the position is not a position limit; it's a
rate limiter wearing one's name."*

§0.9 — **ASSERT THE ECONOMIC EFFECT, NOT THE EVENT RECORD.** Every assertion below is on the
RESULTING POSITION or the approved SIZE that would reach the venue — never on the decision enum or
the reason string alone. WO-048's §6.1 proof checked a label and missed a missing trade; these
assert the ledger consequence. Where a decision code is checked, it is checked *in addition to* the
economic effect, never instead of it.

THE PRESERVATION HALF IS THE DANGEROUS ONE (§4.2). A guard that refuses everything looks correct and
is catastrophic: a position limit that traps you in a position would prevent the system from ever
getting flat, which is strictly worse than the accumulation defect it replaces. That half is
therefore proved at the cap AND beyond it.
"""

from datetime import datetime, UTC
from decimal import Decimal

import pytest

from trading.data.desired_position import DesiredPosition, Side
from trading.logkit.decision import VALID_REASON_CODES
from trading.risk.engine import DeterministicRiskEngine
from trading.risk.position_state import PositionState

CAP = Decimal("1.0")


def _engine(cap=CAP):
    return DeterministicRiskEngine(
        max_position_btc=cap,
        max_daily_loss_pct=Decimal("0.05"),
        account_equity_usd=Decimal("10000"),
    )


def _position(qty):
    return PositionState(
        symbol="BTC/USD", current_quantity=Decimal(str(qty)),
        average_entry_price=Decimal("0"), unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"), daily_pnl=Decimal("0"),
    )


def _order(side, qty):
    return DesiredPosition(
        timestamp=datetime.now(UTC), symbol="BTC/USD", side=side,
        quantity=Decimal(str(qty)), feature_snapshot_hash="h",
    )


def _apply(current, side, approved_size):
    """THE LEDGER CONSEQUENCE: the position that actually results from an approved order.

    Mirrors every real position-update site (`+size if BUY else -size`, runner.py:257/259,
    segmented.py:287). This function is what makes these proofs economic rather than declarative.
    """
    d = Decimal("1") if side is Side.BUY else Decimal("-1")
    return Decimal(str(current)) + d * approved_size


def _resulting(engine, current, side, qty):
    """Run check() and return (decision, resulting_position, approved_size, reason)."""
    decision, order, reason = engine.check(_order(side, qty), _position(current), datetime.now(UTC))
    if order is None:
        return decision.value, Decimal(str(current)), None, reason      # VETO: position unchanged
    return decision.value, _apply(current, side, order.size), order.size, reason


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §4.1 REFUSAL HALF  +  §4.2 PRESERVATION HALF — BOTH IN ONE TEST (S13)
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_aggregate_cap_refusal_and_preservation_in_one_test():
    """S13: both halves, local and direct, so neither can drift from the other.

    REFUSAL (§4.1) — an order that would carry the aggregate PAST the cap is clamped to exactly the
    remaining headroom. Asserted on the RESULTING POSITION equalling the cap, not on a clamp event
    having been logged. At zero headroom the order is VETOED and the position is unchanged.

    PRESERVATION (§4.2) — THE DANGEROUS HALF. At the cap, a REDUCING order still passes UNCLAMPED
    and the position moves toward zero. A limit that traps you in a position is the over-blocking
    nightmare in risk-layer clothing.
    """
    e = _engine()

    # ── REFUSAL: partial headroom -> clamped to EXACTLY the remaining room ──────────────────
    decision, resulting, size, reason = _resulting(e, current="0.7", side=Side.BUY, qty="0.8")
    assert decision == "CLAMP"
    assert resulting == CAP, f"resulting position must equal the cap exactly, got {resulting}"
    assert size == Decimal("0.3"), f"clamped to the remaining headroom 0.3, got {size}"
    assert reason == "RISK_CLAMP_MAX_POSITION"

    # ── REFUSAL: zero headroom -> VETO, and the position DOES NOT MOVE ──────────────────────
    decision, resulting, size, reason = _resulting(e, current="1.0", side=Side.BUY, qty="0.1")
    assert decision == "VETO"
    assert size is None, "a veto must approve no size at all — nothing reaches the venue"
    assert resulting == Decimal("1.0"), "a vetoed order must leave the position untouched"
    assert reason == "RISK_VETO_MAX_POSITION"

    # ── PRESERVATION (THE DANGEROUS HALF): at the cap, a REDUCING order passes UNCLAMPED ────
    decision, resulting, size, reason = _resulting(e, current="1.0", side=Side.SELL, qty="0.4")
    assert decision == "PASS", "a reducing order at the cap MUST pass — never trap the position"
    assert size == Decimal("0.4"), "and it must pass at FULL size, unclamped"
    assert resulting == Decimal("0.6"), "the position moved TOWARD zero"
    assert abs(resulting) < CAP


# ══════════════════════════════════════════════════════════════════════════════════════════════
# NARROWLY-SCOPED HALVES — each exercises EXACTLY ONE property, so a mutation can discriminate.
#
# The S13 test above deliberately contains both halves and therefore fails under EITHER mutation;
# that makes it a good contract statement and a useless discriminator. The 70-case invariant sweep
# has the same property. These four are single-purpose so the §4.4 mutations can fail different
# ones — which is what proves the cap works rather than merely being present.
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_pure_preservation_small_reduction_at_the_cap():
    """PRESERVATION ONLY. At exactly the cap, a small reducing order passes unclamped.

    Survives the per-order-clamp mutation (which never blocked reductions either) and dies under the
    over-blocking mutation. That is precisely the discrimination the risk layer needs.
    """
    decision, resulting, size, _ = _resulting(_engine(), current="1.0", side=Side.SELL, qty="0.1")
    assert decision == "PASS"
    assert size == Decimal("0.1")
    assert resulting == Decimal("0.9")


def test_pure_preservation_small_reduction_beyond_the_cap():
    """PRESERVATION ONLY. Beyond the cap, a small reducing order still passes unclamped."""
    decision, resulting, size, _ = _resulting(_engine(), current="5.0", side=Side.SELL, qty="0.1")
    assert decision == "PASS"
    assert size == Decimal("0.1")
    assert resulting == Decimal("4.9")


def test_pure_refusal_partial_headroom_clamps_to_the_cap():
    """REFUSAL ONLY. Aggregate-aware clamp: the resulting position lands exactly on the cap."""
    decision, resulting, size, _ = _resulting(_engine(), current="0.7", side=Side.BUY, qty="0.8")
    assert decision == "CLAMP"
    assert size == Decimal("0.3")
    assert resulting == CAP


def test_pure_refusal_zero_headroom_vetoes():
    """REFUSAL ONLY. At the cap an INCREASING order is vetoed and the position does not move."""
    decision, resulting, size, reason = _resulting(_engine(), current="1.0", side=Side.BUY, qty="0.1")
    assert decision == "VETO"
    assert size is None
    assert resulting == Decimal("1.0")
    assert reason == "RISK_VETO_MAX_POSITION"


def test_the_cap_is_two_sided():
    """The cap is a MAGNITUDE: a short breaches it exactly as a long does."""
    e = _engine()
    decision, resulting, size, _ = _resulting(e, current="-0.7", side=Side.SELL, qty="0.8")
    assert decision == "CLAMP"
    assert resulting == -CAP, f"the short is capped at -1.0, got {resulting}"
    assert size == Decimal("0.3")

    decision, resulting, size, reason = _resulting(e, current="-1.0", side=Side.SELL, qty="0.1")
    assert decision == "VETO" and reason == "RISK_VETO_MAX_POSITION"
    assert resulting == Decimal("-1.0")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §4.2 (continued) — BEYOND the cap, reduction must still work
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("current,side,qty,expected_size,expected_resulting", [
    ("5.0", Side.SELL, "0.1", Decimal("0.1"), Decimal("4.9")),    # long beyond cap, reduce
    ("-5.0", Side.BUY, "0.1", Decimal("0.1"), Decimal("-4.9")),   # short beyond cap, reduce
    ("5.0", Side.SELL, "4.0", Decimal("4.0"), Decimal("1.0")),    # reduce all the way to the cap
    ("5.0", Side.SELL, "5.0", Decimal("5.0"), Decimal("0.0")),    # reduce to exactly FLAT
])
def test_beyond_the_cap_a_reducing_order_still_passes(current, side, qty,
                                                      expected_size, expected_resulting):
    """A position ABOVE the cap — from a config change or a prior state — must remain reducible.

    This is the case that would strand a real system. If a cap is lowered while a position is open,
    or a position somehow exceeds the cap, the risk layer must not refuse the very orders that would
    bring it back into compliance.
    """
    decision, resulting, size, _ = _resulting(_engine(), current, side, qty)
    assert decision == "PASS", "reduction from beyond the cap must never be blocked"
    assert size == expected_size, "and must not be clamped"
    assert resulting == expected_resulting
    assert abs(resulting) < abs(Decimal(current)), "the position moved toward zero"


def test_a_reduction_that_overshoots_is_capped_on_the_far_side_but_still_reduces():
    """An order that crosses zero and would build a NEW position past the cap is clamped — to the
    opposite cap, never below the amount that reduces.

    The reduction itself is never restricted; only the new exposure built beyond zero is.
    """
    decision, resulting, size, _ = _resulting(_engine(), current="1.0", side=Side.SELL, qty="3.0")
    assert decision == "CLAMP"
    assert resulting == Decimal("-1.0"), "capped at the opposite bound, not refused"
    assert size == Decimal("2.0"), "1.0 to get flat + 1.0 of new short = the far cap"
    assert size < Decimal("3.0"), "clamped strictly smaller"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §4.3 CLAMP-ONLY-REDUCES-TOWARD-ZERO
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("current", ["0", "0.5", "1.0", "5.0", "-0.5", "-1.0", "-5.0"])
@pytest.mark.parametrize("side", [Side.BUY, Side.SELL])
@pytest.mark.parametrize("qty", ["0.1", "0.5", "1.0", "3.0", "10.0"])
def test_the_clamp_never_increases_never_flips_never_converts(current, side, qty):
    """Exhaustive over 70 (position, side, size) combinations. Three invariants, all economic:

      1. NEVER INCREASES — the approved size never exceeds the requested size.
      2. NEVER FLIPS A SIDE — the approved side is the requested side.
      3. NEVER CONVERTS A REDUCING ORDER INTO AN INCREASING ONE — if the order reduced |position|,
         the approved version still reduces it.
    """
    e = _engine()
    requested = Decimal(qty)
    decision, order, _ = e.check(_order(side, qty), _position(current), datetime.now(UTC))

    if order is None:
        # A VETO approves nothing. It may only occur on an INCREASING order (never a reducing one).
        d = Decimal("1") if side is Side.BUY else Decimal("-1")
        assert (d * Decimal(current)) >= 0, (
            f"a VETO blocked a REDUCING order (position {current}, side {side.value}) — "
            f"that would trap the position"
        )
        return

    # 1. never increases
    assert order.size <= requested, f"clamp increased the order: {order.size} > {requested}"
    assert order.size > 0, "an approved order must have a positive size"
    # 2. never flips a side
    assert order.side == side.value
    # 3. never converts reducing -> increasing
    start = Decimal(current)
    resulting = _apply(current, side, order.size)
    d = Decimal("1") if side is Side.BUY else Decimal("-1")
    if (d * start) < 0:                                  # the request REDUCED exposure
        assert abs(resulting) < abs(start) or resulting == 0 or abs(resulting) <= CAP, (
            f"a reducing order became increasing: {start} -> {resulting}"
        )
    # And the cap is respected unless we started outside it (in which case we moved toward it).
    assert abs(resulting) <= max(CAP, abs(start)), (
        f"resulting {resulting} exceeds both the cap and the starting exposure {start}"
    )


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §4.5 THE WO-048 CONDITION, REPRODUCED — the regression the fixtures never reached
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_repeated_same_side_orders_plateau_at_the_cap():
    """WO-048's accumulation pattern: 738,510 same-side 0.1 BTC orders in ONE segment.

    Under the old per-order clamp every order passed a 1.0 BTC "limit" untouched and the position
    grew without bound. Here the position must PLATEAU at the cap and never exceed it.

    This is the condition the fixtures never reached and the corpus did. It is pinned so it can
    never return.
    """
    e = _engine()
    position = Decimal("0")
    approved_total = Decimal("0")
    vetoes = 0

    for _ in range(1000):                       # 1000 x 0.1 BTC against a 1.0 BTC cap
        decision, order, reason = e.check(
            _order(Side.BUY, "0.1"), _position(position), datetime.now(UTC))
        if order is None:
            vetoes += 1
            assert reason == "RISK_VETO_MAX_POSITION"
            continue                            # position unchanged
        position = _apply(position, Side.BUY, order.size)
        approved_total += order.size
        assert position <= CAP, f"position exceeded the cap: {position}"

    assert position == CAP, f"the position must PLATEAU at exactly the cap, got {position}"
    assert approved_total == CAP, "total approved size equals the cap — nothing extra got through"
    assert vetoes == 990, f"the 990 orders past the cap were all vetoed, got {vetoes}"


def test_the_plateau_releases_when_the_position_is_reduced():
    """The dual of the plateau: once reduced, headroom reappears. A cap that never releases would
    be a one-way ratchet — correct-looking and useless."""
    e = _engine()
    position = CAP                              # at the cap: blocked
    _, order, _ = e.check(_order(Side.BUY, "0.1"), _position(position), datetime.now(UTC))
    assert order is None

    _, order, _ = e.check(_order(Side.SELL, "0.5"), _position(position), datetime.now(UTC))
    position = _apply(position, Side.SELL, order.size)
    assert position == Decimal("0.5")

    _, order, _ = e.check(_order(Side.BUY, "0.1"), _position(position), datetime.now(UTC))
    assert order is not None, "headroom must reappear once the position is reduced"
    assert _apply(position, Side.BUY, order.size) == Decimal("0.6")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# vocabulary + determinism
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_the_new_veto_code_is_declared():
    assert "RISK_VETO_MAX_POSITION" in VALID_REASON_CODES["RISK"]
    assert DeterministicRiskEngine.REASON_VETO_MAX_POSITION == "RISK_VETO_MAX_POSITION"


def test_the_clamp_reuses_the_existing_code():
    """§3.4: reuse where it fits. The clamp path keeps RISK_CLAMP_MAX_POSITION unchanged."""
    assert DeterministicRiskEngine.REASON_CLAMP_MAX_POSITION == "RISK_CLAMP_MAX_POSITION"
    assert "RISK_CLAMP_MAX_POSITION" in VALID_REASON_CODES["RISK"]


def test_check_is_deterministic():
    """§3.5: same inputs -> same outputs. No adaptive sizing, no heuristics, no clock dependence."""
    e = _engine()
    results = [_resulting(e, "0.7", Side.BUY, "0.8") for _ in range(50)]
    assert len(set(results)) == 1, f"check() is not deterministic: {set(results)}"
