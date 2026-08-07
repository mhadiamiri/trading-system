"""
Desired Position Data Model

Constitutional Principles:
- III. AI Proposes, Deterministic Code Disposes: No confidence field
- VIII. Total Observability & Provenance: feature_snapshot_hash included
"""

from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


class Side(Enum):
    """Order side direction."""
    BUY = "BUY"      # Long position
    SELL = "SELL"    # Short position
    HOLD = "HOLD"    # No position / flat


@dataclass(frozen=True)
class DesiredPosition:
    """
    Strategy's desired position output.

    Invariants:
    - quantity > 0 if side == Side.BUY
    - quantity < 0 if side == Side.SELL
    - quantity == 0 if side == Side.HOLD
    - feature_snapshot_hash is computed from the MarketState

    ═══════════════════════════════════════════════════════════════════════════════════════════
    ⚠ DATED ANNOTATION — 2026-08-07 (WO-050 §5.3, D47 form: annotate at the site, do not rewrite)

    THE TWO INVARIANTS ABOVE ABOUT SIGN ARE FALSE. They describe a convention this system has
    never used, and the code does the opposite:

      - `DeterministicRiskEngine.check` VETOES any `quantity <= 0` with RISK_VETO_INVALID_INPUT.
        A SELL obeying "quantity < 0" is therefore REJECTED AS MALFORMED — the invariant does not
        merely go unenforced, it is actively contradicted.
      - Every strategy emits a POSITIVE magnitude for both sides
        (`trivial.py:70`, `book_imbalance.py:123`).
      - Every position-update site takes direction from `side`, not from the sign of quantity:
        `+size if BUY else -size` (`runner.py:257/259`, `segmented.py:287`,
        `position_pnl.Position.apply`).

    THE ACTUAL CONVENTION: **`quantity` is an UNSIGNED MAGNITUDE; `side` carries the direction.**

    WHAT THE STALE FORM WOULD CAUSE. An author who believes the docstring writes a SELL as
    `quantity=Decimal("-0.1")`. The risk engine vetoes it as invalid input, so the strategy
    silently stops trading in one direction — a system that only ever goes long, with no error, no
    log line, and a plausible-looking P&L. The failure is invisible precisely because the veto is
    a legitimate code path doing its job on malformed input.

    NOT REWRITTEN, deliberately: the original text is the record of a false claim, and the record
    is itself evidence. The same claim survives at its ORIGIN,
    `specs/001-walking-skeleton/contracts/strategy.py:75-77`, annotated identically — this is the
    third document-vs-code contradiction in this family, and *detail reads as authority*: a
    three-line invariant block looks more authoritative than a one-line veto, which is why it was
    believed for so long.

    NOTE the contrast with `PositionState.current_quantity` ("Positive=long, negative=short"),
    which IS signed and IS correct. A POSITION is signed; an ORDER QUANTITY is not. Conflating the
    two is what made this stale form look plausible.
    ═══════════════════════════════════════════════════════════════════════════════════════════

    Constitutional requirement (Principle III: AI Proposes, Deterministic Code Disposes):
    - No confidence field: This is a latent hook for ML scores to enter live decision path
    - A trivial rule-based strategy has no meaningful confidence value
    """
    timestamp: datetime
    symbol: str
    side: Side
    quantity: Decimal
    feature_snapshot_hash: str  # Hash of MarketState this decision acted on
