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


class _SettingsMeta(type):
    # ── WO-060: READ AT ACCESS TIME, NOT AT IMPORT TIME ──────────────────────────────────────
    #
    # THE DEFECT THIS CLOSES. These four were bound once, at import:
    #
    #     DATA_SOURCE = os.getenv("DATA_SOURCE", "simulated")     # evaluated at import
    #
    # So a test that needed a different value could not simply set the environment — the class
    # attribute was already frozen. `tests/integration/test_live_loop.py` worked around it with
    # `importlib.reload(config.settings)`, TWELVE times. Reload re-executes the module and builds a
    # NEW `Settings` class object, while every module that had done `from config.settings import
    # Settings` — `trading.data.adapters.factory` among them — kept a reference to the OLD one.
    #
    # The result was TWO LIVE `Settings` CLASSES with one entry in `sys.modules`:
    #
    #     factory.Settings is config.settings.Settings   ->   False
    #
    # and therefore a patch applied to one that never reached the code reading the other. That is
    # what made WO-056's reachability witness pass alone and fail in the full suite.
    #
    # Reading `os.environ` at ACCESS time removes the reason to reload, which removes the second
    # class object, which removes the whole failure mode. The environment becomes the single source
    # of truth rather than a value copied once and diverged from thereafter.
    #
    # ⚠ FOUR ATTRIBUTES WERE BOUND THIS WAY, NOT ONE (0.11). `TRADING_ENV` is among them, and it
    # is the RED-LINE surface: it gates the mainnet order path. A stale `TRADING_ENV` on a class
    # object that production code still holds is the most consequential form of this defect, not
    # the least.

    @property
    def DATA_SOURCE(cls) -> str:
        """Selects the market data feed (independent of execution)."""
        return os.getenv("DATA_SOURCE", "simulated")

    @DATA_SOURCE.deleter
    def DATA_SOURCE(cls) -> None:
        # `patch.object` sees no entry in Settings.__dict__ (the property lives on the metaclass),
        # treats the attribute as created, and DELETES it on exit. Without a deleter that is an
        # AttributeError at teardown. Deleting restores the declared default.
        os.environ.pop("DATA_SOURCE", None)

    @DATA_SOURCE.setter
    def DATA_SOURCE(cls, value: str) -> None:
        # A SETTER, deliberately. `patch.object(Settings, "DATA_SOURCE", ...)` is how several
        # tests express "run this with a different source", and without a setter that raises
        # AttributeError. Writing through to the environment means such a patch reaches the
        # production code path instead of decorating a class attribute nothing reads — which is
        # the property the WO-060 enumeration exists to check.
        os.environ["DATA_SOURCE"] = str(value)

    @property
    def TRADING_ENV(cls) -> str:
        """Gates EXECUTION only, never data access. Defaults to paper."""
        return os.getenv("TRADING_ENV", "paper")

    @TRADING_ENV.deleter
    def TRADING_ENV(cls) -> None:
        # `patch.object` sees no entry in Settings.__dict__ (the property lives on the metaclass),
        # treats the attribute as created, and DELETES it on exit. Without a deleter that is an
        # AttributeError at teardown. Deleting restores the declared default.
        os.environ.pop("TRADING_ENV", None)

    @TRADING_ENV.setter
    def TRADING_ENV(cls, value: str) -> None:
        os.environ["TRADING_ENV"] = str(value)

    @property
    def DATA_DIR(cls) -> str:
        return os.getenv("DATA_DIR", "data")

    @DATA_DIR.deleter
    def DATA_DIR(cls) -> None:
        # `patch.object` sees no entry in Settings.__dict__ (the property lives on the metaclass),
        # treats the attribute as created, and DELETES it on exit. Without a deleter that is an
        # AttributeError at teardown. Deleting restores the declared default.
        os.environ.pop("DATA_DIR", None)

    @DATA_DIR.setter
    def DATA_DIR(cls, value: str) -> None:
        os.environ["DATA_DIR"] = str(value)

    @property
    def LOG_DIR(cls) -> str:
        return os.getenv("LOG_DIR", "logs")

    @LOG_DIR.deleter
    def LOG_DIR(cls) -> None:
        # `patch.object` sees no entry in Settings.__dict__ (the property lives on the metaclass),
        # treats the attribute as created, and DELETES it on exit. Without a deleter that is an
        # AttributeError at teardown. Deleting restores the declared default.
        os.environ.pop("LOG_DIR", None)

    @LOG_DIR.setter
    def LOG_DIR(cls, value: str) -> None:
        os.environ["LOG_DIR"] = str(value)


class Settings(metaclass=_SettingsMeta):
    """
    Application settings loaded from environment.

    Constitutional requirements:
    - DATA_SOURCE selects market data feed (may point at mainnet public feed)
    - TRADING_ENV gates execution only (paper/mainnet)
    - No credentials required for public data feeds (Principle IX)
    - No code path can place real orders while TRADING_ENV=paper
    """


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
