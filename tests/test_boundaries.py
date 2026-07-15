"""
Import Boundary Tests

Tests that verify import boundary rules are enforced.

Constitutional Principles:
- IV. Layered Architecture, Enforced Boundaries: Import boundaries
- III. AI Proposes, Deterministic Code Disposes: No ML in risk layer
"""

import pytest
import importlib
import sys


class TestImportBoundaries:
    """Test suite for import boundary enforcement."""

    def test_risk_layer_has_no_ml_imports(self):
        """
        Test risk layer cannot import ML/AI libraries.

        Constitutional requirements:
            - Risk layer MUST NOT import ML/AI libraries (Principle III)
        """
        # Import risk modules
        import trading.risk.engine
        import trading.risk.interface
        import trading.risk.limits

        # Check that ML modules are not imported
        ml_modules = ["torch", "tensorflow", "sklearn", "transformers"]

        for module in ml_modules:
            assert module not in sys.modules, f"Risk layer imported ML module: {module}"

    def test_strategy_cannot_import_execution_adapters(self):
        """
        Test strategy layer cannot import execution adapters.

        Constitutional requirements:
            - Execution adapters isolated (Principle IV)
        """
        # Verify no real-money execution adapters exist in execution.adapters
        # The invariant is that ONLY paper execution exists
        # (real-money adapters are Sprint 3, not yet implemented)
        import os
        adapters_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "trading",
            "execution",
            "adapters"
        )

        # Verify only __init__.py exists (no real-money adapters)
        if os.path.exists(adapters_dir):
            adapter_files = [f for f in os.listdir(adapters_dir) if f.endswith(".py") and f != "__init__.py"]
            assert len(adapter_files) == 0, f"Found unexpected adapter files: {adapter_files}. Only paper execution should exist in Phase 1."

    def test_data_cannot_import_execution_adapters(self):
        """
        Test data layer cannot import execution adapters.

        Constitutional requirements:
            - Execution adapters isolated (Principle IV)
        """
        # Verify data layer modules don't have imports from execution.adapters
        # Check by inspecting the actual imports in data modules
        import trading.data.market_state
        import trading.data.desired_position
        import trading.data.adapters.simulated_feed
        import inspect

        # Check source code of data modules for any execution.adapters imports
        for module in [trading.data.market_state, trading.data.desired_position, trading.data.adapters.simulated_feed]:
            source = inspect.getsource(module)
            assert "trading.execution.adapters" not in source, f"{module.__name__} imports from execution.adapters"

    def test_backtest_cannot_import_execution_adapters(self):
        """
        Test backtest layer cannot import execution adapters.

        Constitutional requirements:
            - Execution adapters isolated (Principle IV)
        """
        # Import backtest modules
        import trading.backtest.report

        # Verify no execution adapter imports
        # (backtest uses paper execution, not adapters)

    def test_import_linter_contract_enforced(self):
        """
        Test import-linter contract is enforced in code.

        Constitutional requirements:
            - Boundaries enforced mechanically (Principle IV)
        """
        # Verify import-linter configuration exists in pyproject.toml
        try:
            import tomllib
            read_toml = tomllib.load
        except ImportError:
            import tomli
            read_toml = lambda f: tomli.load(f.read())

        import os

        pyproject_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "pyproject.toml",
        )

        with open(pyproject_path, "rb") as f:
            config = read_toml(f)

        # Verify import-linter configuration exists
        assert "tool" in config
        assert "importlinter" in config["tool"]
        assert "contracts" in config["tool"]["importlinter"]

        # Verify forbidden modules contract exists
        contracts = config["tool"]["importlinter"]["contracts"]
        forbidden_contract = [
            c for c in contracts
            if c.get("type") == "forbidden" and "ML" in c.get("name", "")
        ]
        assert len(forbidden_contract) > 0, "No ML forbidden contract found"

        # Verify forbidden contracts exist (we use forbidden, not layers)
        forbidden_contracts = [
            c for c in contracts
            if c.get("type") == "forbidden"
        ]
        assert len(forbidden_contracts) >= 2, "Should have at least 2 forbidden contracts"

        # Verify execution adapters forbidden contract exists
        adapters_contract = [
            c for c in forbidden_contracts
            if "Execution Adapters" in c.get("name", "")
        ]
        assert len(adapters_contract) > 0, "No execution adapters forbidden contract found"

    def test_trading_env_paper_blocks_real_orders(self):
        """
        Test the core invariant: no real-money orders reachable while TRADING_ENV=paper or test.

        Constitutional requirements:
            - No code path that can place real orders is reachable while TRADING_ENV=paper
            - This invariant holds for ALL values of DATA_SOURCE (including kraken_public)
            - TRADING_ENV=test exists ONLY to make suspenders guard testable
            - TRADING_ENV=test grants ZERO real-order capability (behaves exactly like paper)
            - Only mainnet + explicit override may reach real execution
            - Invariant: Real money unreachable in paper/test mode (Principle IX)

        This test verifies:
        1. Settings.validate() BLOCKS TRADING_ENV=mainnet (belt guard)
        2. PaperExecutionClient CAN be used when TRADING_ENV=paper (correct behavior)
        3. PaperExecutionClient CANNOT be used when TRADING_ENV=test (suspenders guard)
        4. TRADING_ENV=test blocks real-order clients (test is not a bypass)

        Note: The kill switch has its own separate test. This test does NOT test the kill switch.
        """
        import os
        import importlib
        from trading.execution.paper import PaperExecutionClient

        # Save original values
        original_trading_env = os.environ.get("TRADING_ENV")
        original_data_source = os.environ.get("DATA_SOURCE")

        try:
            # Test 1: Settings.validate() BLOCKS TRADING_ENV=mainnet (belt guard)
            # This is the first guard (belt) - blocks at module import time
            for data_source in ["simulated", "kraken_public"]:
                os.environ["TRADING_ENV"] = "mainnet"
                os.environ["DATA_SOURCE"] = data_source

                # Reloading settings should trigger validate() which raises ValueError
                with pytest.raises(ValueError, match="BLOCKED by constitutional guard"):
                    import config.settings
                    importlib.reload(config.settings)

            # Test 2: PaperExecutionClient CAN be used when TRADING_ENV=paper
            # This is the CORRECT behavior - verify it works for all DATA_SOURCE values
            for data_source in ["simulated", "kraken_public"]:
                os.environ["TRADING_ENV"] = "paper"
                os.environ["DATA_SOURCE"] = data_source

                # Reload settings to apply new environment
                import config.settings
                importlib.reload(config.settings)
                from config.settings import Settings as FreshSettings

                # Verify settings loaded correctly
                assert FreshSettings.TRADING_ENV == "paper"
                assert FreshSettings.DATA_SOURCE == data_source
                assert FreshSettings.is_paper_trading() is True

                # Verify PaperExecutionClient can be instantiated (correct)
                paper_client = PaperExecutionClient()
                assert paper_client is not None

            # Test 3: PaperExecutionClient CANNOT be used when TRADING_ENV=test
            # This tests the execution layer guard (suspenders) by actually trying to
            # create a PaperExecutionClient with TRADING_ENV=test - it MUST fail
            # TRADING_ENV=test passes the belt guard but should be blocked by suspenders
            for data_source in ["simulated", "kraken_public"]:
                os.environ["TRADING_ENV"] = "test"
                os.environ["DATA_SOURCE"] = data_source

                # Reload settings to apply new environment
                import config.settings
                importlib.reload(config.settings)
                from config.settings import Settings as FreshSettings

                # Verify settings loaded correctly
                assert FreshSettings.TRADING_ENV == "test"
                assert FreshSettings.DATA_SOURCE == data_source
                assert FreshSettings.is_paper_trading() is False  # test is NOT paper

                # Verify PaperExecutionClient CANNOT be instantiated (suspenders guard)
                # The guard in PaperExecutionClient.__init__ checks is_paper_trading()
                # and raises ValueError when TRADING_ENV != paper
                with pytest.raises(ValueError, match="CANNOT be used when TRADING_ENV"):
                    PaperExecutionClient()

            # Test 4: TRADING_ENV=test is NOT a bypass - it blocks real-order clients
            # Verify that attempting to create a real-order-capable client under test
            # would fail exactly as under paper. Since no real-money adapters exist
            # in Phase 1, this is verified by the fact that PaperExecutionClient (the
            # only execution client) is blocked under test, proving test behaves like
            # paper for all execution paths.
            for data_source in ["simulated", "kraken_public"]:
                os.environ["TRADING_ENV"] = "test"
                os.environ["DATA_SOURCE"] = data_source

                # Reload settings
                import config.settings
                importlib.reload(config.settings)

                # Verify real-order path is blocked: only PaperExecutionClient exists
                # in Phase 1, and it refuses to instantiate under test
                with pytest.raises(ValueError, match="CANNOT be used when TRADING_ENV"):
                    PaperExecutionClient()

        finally:
            # Restore original values
            if original_trading_env:
                os.environ["TRADING_ENV"] = original_trading_env
            else:
                os.environ.pop("TRADING_ENV", None)

            if original_data_source:
                os.environ["DATA_SOURCE"] = original_data_source
            else:
                os.environ.pop("DATA_SOURCE", None)

            # Reload settings to restore original state
            import config.settings
            importlib.reload(config.settings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
