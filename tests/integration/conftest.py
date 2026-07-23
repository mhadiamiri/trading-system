"""WO-022 §1 — structural injection of a host baseline for host-INDEPENDENT tests.

Eight tests conflated CODE BEHAVIOR ("with no baseline for this host, the runner refuses" — testable
anywhere, bite-proved, passing) with an ENVIRONMENT FACT ("a baseline exists for this host" — ambient
config the dev machine happened to supply). That is 0.1h one level out: a test relying on a precondition
the ENVIRONMENT supplies rather than CONSTRUCTING it. It stayed invisible until the matrix ran the same
suite on a second host (Linux CI), where the same 8 failed identically on BOTH legs.

Fix: the tests INJECT the baseline structurally, via `MEAN_CYCLE_BASELINE_STORE` (the same seam
host_baseline already documents for tests/tools). PRODUCTION BEHAVIOR IS UNCHANGED — the runner still
refuses on a host with NO baseline (test_runner_refuses_host_with_no_baseline, still passing). The
injected record is OBVIOUSLY SYNTHETIC (fixture-labeled, sentinel numbers) so no future reader mistakes
test scaffolding for a real calibration record — fixture-fidelity doctrine applied to config.
"""
import json

import pytest

from trading.loop import host_baseline

# UNMISTAKABLY SYNTHETIC — a fixture, not a copy of any real dev-machine entry. Every field announces
# itself: the fingerprint is a label not a 16-hex hash, the numbers are repeating-digit sentinels, and
# the derivation says so in words. It carries the full schema (full-loop active + a CLOSED adapter-only
# ledger with its own superseded history) so the structural gate test round-trips through a real JSON
# store without depending on the dev host's ambient config.
SYNTHETIC_BASELINE_RECORD = {
    "fingerprint": {
        "machine_id": "FIXTURE-NOT-A-REAL-HOST",
        "python_version": "0.0.0-fixture",
        "os": "Fixture OS (synthetic)",
        "cpu_arch": "fixture-arch",
    },
    "instrument": "full-loop",
    "mean_cycle_seconds": 0.999999,          # sentinel; NOT the real ~0.1087s establishment figure
    "date": "FIXTURE-NOT-A-REAL-DATE",
    "derivation": "SYNTHETIC WO-022 TEST FIXTURE — injected so host-independent tests do not depend on "
                  "the dev machine's ambient calibration. NOT a real establishment record.",
    "load": "fixture",
    "scope": {
        "host": "fixture (synthetic)",
        "instrument": "full-loop (fixture)",
        "resolution": "fixture",
        "load_work": "fixture",
    },
    "closed_instrument_ledgers": [{
        "instrument": "adapter-only",
        "mean_cycle_seconds": 0.888888,      # sentinel
        "ledger_closed_date": "FIXTURE-NOT-A-REAL-DATE",
        "superseded": [{"mean_cycle_seconds": 0.777777}],   # sentinel
    }],
}


@pytest.fixture
def injected_baseline(tmp_path, monkeypatch):
    """Point MEAN_CYCLE_BASELINE_STORE at a store carrying the SYNTHETIC baseline under THIS host's
    fingerprint key, so load_baseline()/the runner resolve it without reading the production store.
    Returns the record so tests can assert the values that round-tripped (proving they read the
    injected synthetic store, not the ambient one)."""
    store = tmp_path / "synthetic_baselines.json"
    key = host_baseline.fingerprint_key(host_baseline.host_fingerprint())
    store.write_text(json.dumps({key: SYNTHETIC_BASELINE_RECORD}, indent=1), encoding="utf-8")
    monkeypatch.setenv("MEAN_CYCLE_BASELINE_STORE", str(store))
    return SYNTHETIC_BASELINE_RECORD
