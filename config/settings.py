"""
Configuration Settings

Load settings from environment variables and provide defaults.

Constitutional Principles:
- VII. Venue Independence: DATA_SOURCE selects market data feed
- IX. Secrets and Safety Rails: TRADING_ENV gates execution only
"""

import os
from typing import Literal
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings:
    """
    Application settings loaded from environment.

    Constitutional requirements:
    - DATA_SOURCE selects market data feed (may point at mainnet public feed)
    - TRADING_ENV gates execution only (paper/mainnet)
    - No credentials required for public data feeds (Principle IX)
    - No code path can place real orders while TRADING_ENV=paper
    """

    # Data source: selects market data feed (independent of execution)
    # Options: simulated, kraken_public, kraken_v2 (Sprint 2: T004 prepared, raises NotImplementedError until T009-T019)
    DATA_SOURCE: Literal["simulated", "kraken_public", "kraken_v2"] = os.getenv(
        "DATA_SOURCE", "simulated"
    )

    # Trading environment: gates execution only (not data access)
    # Options: paper, mainnet, test
    # Default to paper for safety - requires explicit override for mainnet
    # test: paper-equivalent mode for testing suspenders guard only
    TRADING_ENV: Literal["paper", "mainnet", "test"] = os.getenv(
        "TRADING_ENV", "paper"
    )

    # Data persistence
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")

    @classmethod
    def validate(cls) -> None:
        """
        Validate settings.

        Raises:
            ValueError: If settings are invalid

        Constitutional requirements:
        - DATA_SOURCE must be valid
        - TRADING_ENV=paper is default (safe), mainnet requires explicit override
        - No credentials are required for public data feeds
        """
        if cls.DATA_SOURCE not in ("simulated", "kraken_public", "kraken_v2"):
            raise ValueError(
                f"Invalid DATA_SOURCE: {cls.DATA_SOURCE}. "
                f"Must be 'simulated', 'kraken_public', or 'kraken_v2'."
            )

        if cls.TRADING_ENV not in ("paper", "mainnet", "test"):
            raise ValueError(
                f"Invalid TRADING_ENV: {cls.TRADING_ENV}. "
                f"Must be 'paper', 'mainnet', or 'test'."
            )

        # CONSTITUTIONAL GUARD (Principle IX, Phase-1 Scope):
        # Real-money trading is OUT OF SCOPE for Phase 1.
        # TRADING_ENV=mainnet is blocked to prevent accidental real-money orders.
        # This guard can only be relaxed by a constitutional amendment or
        # explicit Strategy & Roadmap decision for Phase 3.
        if cls.TRADING_ENV == "mainnet":
            raise ValueError(
                "TRADING_ENV=mainnet is BLOCKED by constitutional guard. "
                "Phase 1 scope permits paper trading only. "
                "No code path can place real-money orders in Phase 1. "
                "To proceed with real-money execution, a constitutional amendment "
                "or explicit Strategy & Roadmap decision for Phase 3 is required. "
                "See .specify/memory/constitution.md Principle IX and Phase-1 Scope."
            )

        # No credentials should be required for any data source (public feeds only)

    @classmethod
    def using_live_feed(cls) -> bool:
        """Check if using live feed (vs simulated)."""
        return cls.DATA_SOURCE in ("kraken_public", "kraken_v2")

    @classmethod
    def is_paper_trading(cls) -> bool:
        """
        Check if running in paper trading mode.

        Returns True only for TRADING_ENV=paper.
        Returns False for mainnet and test, allowing suspenders guard to be tested.
        """
        return cls.TRADING_ENV == "paper"


# Validate on import
Settings.validate()
