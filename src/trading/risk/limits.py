"""
Risk Limits Configuration

Configurable hard limits for the risk engine.

Constitutional Principles:
- VI. Risk Engine Is Sovereign: Hard limits live here
"""

from decimal import Decimal


# Default risk limits
DEFAULT_MAX_POSITION_BTC = Decimal("1.0")
DEFAULT_MAX_DAILY_LOSS_PCT = Decimal("0.05")  # 5%
DEFAULT_ACCOUNT_EQUITY_USD = Decimal("10000")


def get_default_limits() -> dict[str, Decimal]:
    """Return default risk limits."""
    return {
        "max_position_btc": DEFAULT_MAX_POSITION_BTC,
        "max_daily_loss_pct": DEFAULT_MAX_DAILY_LOSS_PCT,
        "account_equity_usd": DEFAULT_ACCOUNT_EQUITY_USD,
    }
