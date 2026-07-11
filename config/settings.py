"""
Configuration Settings

Load settings from environment variables and provide defaults.

Constitutional Principles:
- IX. Secrets and Safety Rails: Credentials from .env only
"""

import os
from typing import Literal
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings:
    """
    Application settings loaded from environment.

    Credential handling:
    - All credentials read from .env only (Principle IX)
    - .env.example shows variable names only
    """

    # Trading environment (testnet only for safety)
    TRADING_ENV: Literal["testnet", "mainnet"] = os.getenv(
        "TRADING_ENV", "testnet"
    )

    # Feed type selection
    FEED_TYPE: Literal["simulated", "bybit_testnet"] = os.getenv(
        "FEED_TYPE", "simulated"
    )

    # Bybit API credentials (for testnet)
    BYBIT_API_KEY: str = os.getenv("BYBIT_API_KEY", "")
    BYBIT_API_SECRET: str = os.getenv("BYBIT_API_SECRET", "")

    # Data persistence
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")

    @classmethod
    def validate(cls) -> None:
        """
        Validate settings.

        Raises:
            ValueError: If settings are invalid
        """
        if cls.TRADING_ENV not in ("testnet", "mainnet"):
            raise ValueError(f"Invalid TRADING_ENV: {cls.TRADING_ENV}")

        if cls.TRADING_ENV == "mainnet":
            raise ValueError(
                "Mainnet is not allowed in development. "
                "Set TRADING_ENV=testnet in .env"
            )

        if cls.FEED_TYPE == "bybit_testnet":
            if not cls.BYBIT_API_KEY or not cls.BYBIT_API_SECRET:
                raise ValueError(
                    "BYBIT_API_KEY and BYBIT_API_SECRET required "
                    "when FEED_TYPE=bybit_testnet"
                )

    @classmethod
    def using_live_feed(cls) -> bool:
        """Check if using live feed."""
        return cls.FEED_TYPE == "bybit_testnet"


# Validate on import
Settings.validate()
