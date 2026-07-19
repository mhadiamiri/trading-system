"""
Mainnet / order-capability guard — REAL bite proofs (WO-008b-A1 §3).

WHY THIS FILE EXISTS
--------------------
The previous bite proof for this invariant, `test_settings_validate_blocks_mainnet`
(now quarantined), asserted substrings of ITS OWN LOCAL STRING LITERAL:

    expected_error_text = "TRADING_ENV=mainnet is BLOCKED by constitutional guard"
    assert "BLOCKED" in expected_error_text

It never imported `config.settings`, never called `Settings.validate()`, and never
touched the guard. **It would pass against an empty repository.** Under rule 0.1d
that is a false guarantee — and it was the certifying proof for the single most
safety-critical invariant in the codebase: that no code path can place a
real-money order in Phase 1.

The tests here INTERACT with the mechanism they certify.

SALVAGED: the patching approach in
`evidence/QUARANTINE-WO-008b-A-FABRICATED/tests/test_order_guard_bite_proof.py`
— identified in WO-009 as the strongest of the three quarantined files. Its
`patch.object(Settings, ...)` construction-refusal technique is reused in
`TestOrderCapableGuard` below. Its source-inspection test is NOT reused: reading
source proves text, not behaviour.
"""

import importlib
import os
import sys
from decimal import Decimal
from unittest.mock import patch

import pytest

from config.settings import Settings
from trading.execution.paper import PaperExecutionClient


class TestOrderCapableGuard:
    """Under a non-paper environment, the order-capable path must be unreachable."""

    def test_paper_client_constructs_under_paper_env(self):
        """Baseline: the guard permits what it is supposed to permit."""
        assert Settings.TRADING_ENV == "paper", (
            "this suite assumes .env sets TRADING_ENV=paper"
        )
        client = PaperExecutionClient()
        assert client is not None

    @staticmethod
    def _live_settings():
        """
        Return the Settings class the PRODUCTION CODE will actually consult.

        `paper.py:83` does a FUNCTION-LOCAL `from config.settings import Settings`,
        so it resolves out of `sys.modules` at call time. Other tests in this suite
        (test_live_loop.py, test_boundaries.py, and this file) reload
        `config.settings`, which REBINDS that module to a NEW Settings class object.

        Patching the class imported at the top of this file therefore patches a
        STALE object that the guard no longer reads — the test passes in isolation
        and fails in a full run. Resolving it live here removes that order
        dependence instead of hiding it.
        """
        import config.settings

        return config.settings.Settings

    def test_paper_client_refuses_construction_under_mainnet(self):
        """
        THE BITE. Construction must RAISE when the environment is not paper.

        This calls the real constructor against real Settings state — it does not
        assert on a string it wrote itself.
        """
        live_settings = self._live_settings()
        with patch.object(live_settings, "TRADING_ENV", "mainnet"), \
             patch.object(live_settings, "is_paper_trading", staticmethod(lambda: False)):
            with pytest.raises(ValueError) as exc_info:
                PaperExecutionClient()

        message = str(exc_info.value)
        assert "CANNOT be used" in message, f"unexpected refusal message: {message}"
        assert "mainnet" in message

    def test_paper_client_refuses_construction_under_test_env_when_not_paper(self):
        """The guard keys on is_paper_trading(), not on a hardcoded value list."""
        live_settings = self._live_settings()
        with patch.object(live_settings, "TRADING_ENV", "somethingelse"), \
             patch.object(live_settings, "is_paper_trading", staticmethod(lambda: False)):
            with pytest.raises(ValueError):
                PaperExecutionClient()


class TestSettingsMainnetGuard:
    """`Settings.validate()` must block TRADING_ENV=mainnet at import time."""

    @staticmethod
    def _reload_settings_with_env(value):
        """Reload config.settings under a given TRADING_ENV. Returns the exception or None."""
        original = os.environ.get("TRADING_ENV")
        try:
            os.environ["TRADING_ENV"] = value
            if "config.settings" in sys.modules:
                del sys.modules["config.settings"]
            try:
                import config.settings
                importlib.reload(config.settings)
                return None
            except ValueError as exc:
                return exc
        finally:
            if original is not None:
                os.environ["TRADING_ENV"] = original
            else:
                os.environ.pop("TRADING_ENV", None)
            if "config.settings" in sys.modules:
                del sys.modules["config.settings"]
            import config.settings
            importlib.reload(config.settings)

    def test_paper_env_is_accepted(self):
        """Baseline: paper must load cleanly."""
        assert self._reload_settings_with_env("paper") is None

    def test_mainnet_env_is_blocked(self):
        """
        THE BITE. Importing config.settings with TRADING_ENV=mainnet must RAISE.

        Real import, real guard, real exception — not a string comparison.
        """
        exc = self._reload_settings_with_env("mainnet")

        assert exc is not None, (
            "GUARD DID NOT FIRE: TRADING_ENV=mainnet was accepted. "
            "No code path may reach a real-money venue in Phase 1."
        )
        assert "TRADING_ENV=mainnet is BLOCKED" in str(exc)
        assert "constitutional guard" in str(exc)

    def test_guard_is_not_satisfied_by_string_inspection(self):
        """
        Rule 0.1d regression guard.

        The replaced test passed by inspecting a literal it defined itself. This
        asserts the guard's effect is OBSERVED, by confirming the paper and
        mainnet paths produce genuinely different outcomes.
        """
        paper_result = self._reload_settings_with_env("paper")
        mainnet_result = self._reload_settings_with_env("mainnet")

        assert paper_result is None
        assert isinstance(mainnet_result, ValueError)
        assert type(paper_result) is not type(mainnet_result), (
            "the two environments must produce observably different behaviour; "
            "if they did not, the guard would not be doing anything"
        )
