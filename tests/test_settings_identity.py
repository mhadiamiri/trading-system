"""
WO-060 — ONE `Settings` CLASS OBJECT, AND `DATA_SOURCE` READ AT ACCESS TIME.

The defect these pin: `Settings.DATA_SOURCE` was bound at import, so tests that needed a different
value called `importlib.reload(config.settings)` — twelve times in one file. Reload builds a NEW
class object while every module that did `from config.settings import Settings` keeps the OLD one.
Two live classes, one `sys.modules` entry, and a patch that reaches only one of them.

That is why WO-056's reachability witness passed alone and failed in the full suite.
"""

import os


def test_there_is_exactly_one_Settings_class_object():
    """(a) IMPORT-ROUTE HYGIENE. Every route to Settings must reach the same object — this is the
    assertion whose absence let two classes coexist undetected."""
    import config.settings as direct
    from config.settings import Settings as via_from
    from trading.data.adapters import factory

    assert factory.Settings is direct.Settings
    assert via_from is direct.Settings


def test_no_test_mints_a_second_settings_class_by_reload_or_cache_deletion():
    """The reload is what MINTED the second class. Banning it is what keeps (a) true — an identity
    assertion alone would pass right up until the next reload."""
    from pathlib import Path

    offenders = []
    for p in Path("tests").rglob("*.py"):
        # DECLARED EXEMPTIONS. Reloading to APPLY an env change is now unnecessary and mints a
        # duplicate class; reloading to TEST IMPORT-TIME VALIDATION is the guard's own mechanism.
        # Both exempt files are red-line mainnet-guard tests: module-level Settings.validate() is
        # what they exercise, and a reload that RAISES leaves the original module in sys.modules,
        # so no second class survives.
        EXEMPT = set()   # WO-060: none remain — the guard tests call Settings.validate() directly
        if p.name == Path(__file__).name or p.name in EXEMPT:
            continue
        text = p.read_text(encoding="utf-8")
        code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
        # BOTH minting routes, not just one (0.11). `reload()` re-executes the module in place;
        # `del sys.modules[...]` + a later import builds a fresh one. Either leaves modules that
        # did `from config.settings import Settings` holding a class nothing else reads.
        if "reload(config.settings)" in code or "del sys.modules['config.settings']" in code:
            offenders.append(str(p))
    assert offenders == [], (
        f"{offenders} reload config.settings, which mints a second Settings class object. "
        f"Settings now reads os.environ at access time, so there is nothing to reload."
    )


def test_DATA_SOURCE_is_read_at_access_time_not_bound_at_import(monkeypatch):
    """(b) The fix itself: changing the environment changes what production code reads, with no
    reload and no second class."""
    from config.settings import Settings
    from trading.data.adapters import factory

    monkeypatch.setenv("DATA_SOURCE", "kraken_v2")
    assert Settings.DATA_SOURCE == "kraken_v2"
    assert factory.Settings.DATA_SOURCE == "kraken_v2", "the production reader sees it too"
    monkeypatch.setenv("DATA_SOURCE", "simulated")
    assert factory.Settings.DATA_SOURCE == "simulated"


def test_TRADING_ENV_is_also_read_at_access_time():
    """0.11 — FOUR attributes were bound at import, not one, and this is the RED-LINE member: it
    gates the mainnet order path."""
    from config.settings import Settings

    original = os.environ.get("TRADING_ENV")
    try:
        os.environ["TRADING_ENV"] = "test"
        assert Settings.TRADING_ENV == "test"
        assert Settings.is_paper_trading() is False
        os.environ["TRADING_ENV"] = "paper"
        assert Settings.is_paper_trading() is True
    finally:
        if original is None:
            os.environ.pop("TRADING_ENV", None)
        else:
            os.environ["TRADING_ENV"] = original


def test_patching_the_class_attribute_REACHES_production_code():
    """The property the enumeration checks for. `patch.object(Settings, ...)` is how several tests
    express intent; with a setter writing through to the environment, that patch is not decoration
    — the code path actually reads it."""
    from unittest.mock import patch

    from config.settings import Settings
    from trading.data.adapters import factory

    with patch.object(Settings, "DATA_SOURCE", "kraken_v2"):
        assert factory.Settings.DATA_SOURCE == "kraken_v2"
        assert os.environ["DATA_SOURCE"] == "kraken_v2"
    assert factory.Settings.DATA_SOURCE != "kraken_v2", "and it restores"


def test_the_mainnet_guard_still_fires_on_the_live_value():
    """RED-LINE, re-verified after the change. The guard reads `cls.TRADING_ENV`, which now reads
    the environment at access time — so it fires on the CURRENT value rather than one frozen at
    import. Strictly stronger than before."""
    import pytest

    from config.settings import Settings

    original = os.environ.get("TRADING_ENV")
    try:
        os.environ["TRADING_ENV"] = "mainnet"
        with pytest.raises(ValueError, match="TRADING_ENV=mainnet is BLOCKED"):
            Settings.validate()
    finally:
        if original is None:
            os.environ.pop("TRADING_ENV", None)
        else:
            os.environ["TRADING_ENV"] = original


def test_the_guard_still_fires_at_IMPORT_time_verified_in_a_subprocess():
    """The import-time invocation, covered without polluting this process.

    `config/settings.py` calls `Settings.validate()` at module level, so importing it under
    TRADING_ENV=mainnet must raise. Testing that in-process requires deleting and re-importing the
    module, which mints the second class object this WO exists to remove — so it runs in a
    SUBPROCESS instead. The isolation is the point: the property is real, and verifying it must
    not damage the thing being verified.
    """
    import subprocess
    import sys

    env = dict(os.environ, TRADING_ENV="mainnet")
    proc = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import config.settings"],
        capture_output=True, text=True, env=env, timeout=120,
    )
    assert proc.returncode != 0, "importing under TRADING_ENV=mainnet must fail"
    assert "BLOCKED by constitutional guard" in (proc.stderr + proc.stdout)
