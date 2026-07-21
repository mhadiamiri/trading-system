"""WO-016 §D28 — the host-scoped mean-cycle baseline gate.

The UNIFORM drift baseline is a HOST property. The live-capture runner REFUSES to start on a host
with no matching frozen baseline (rather than convict UNIFORM against another machine's reference),
and the machine identifier in the committed record is a HASH, not the raw hostname.
"""
import json
import os

import pytest

from trading.loop import host_baseline
from trading.loop.live_capture import LiveCaptureRunner, LiveCaptureError


def test_fingerprint_is_hashed_and_deterministic():
    fp = host_baseline.host_fingerprint()
    assert set(fp) == {"machine_id", "python_version", "os", "cpu_arch"}
    import platform
    assert fp["machine_id"] != platform.node()          # NOT the raw hostname
    assert len(fp["machine_id"]) == 16 and all(c in "0123456789abcdef" for c in fp["machine_id"])
    assert host_baseline.fingerprint_key(fp) == host_baseline.fingerprint_key(fp)   # deterministic


def test_this_host_has_a_committed_baseline():
    rec = host_baseline.load_baseline()
    assert rec is not None, "this host must have a frozen baseline in config/mean_cycle_baselines.json"
    assert rec["mean_cycle_seconds"] > 0
    assert "fingerprint" in rec and "derivation" in rec


def test_runner_refuses_host_with_no_baseline(tmp_path, monkeypatch):
    """THE REFUSAL. With no baseline for this host, the runner refuses to START — before any
    connection — with the declared reason code, rather than convict UNIFORM against a reference
    from a machine that is not running."""
    empty = tmp_path / "empty_baselines.json"
    empty.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MEAN_CYCLE_BASELINE_STORE", str(empty))
    monkeypatch.setenv("TRADING_ENV", "paper")
    with pytest.raises(LiveCaptureError, match="MEAN_CYCLE_BASELINE_HOST_MISMATCH"):
        LiveCaptureRunner(persist_path="x.jsonl", duration_seconds=10,
                          trading_env="paper", data_source="kraken_v2")


def test_runner_accepts_host_with_a_matching_baseline(tmp_path, monkeypatch):
    """Dual: a store that DOES carry this host's fingerprint lets the runner construct."""
    fp = host_baseline.host_fingerprint()
    store = tmp_path / "baselines.json"
    store.write_text(json.dumps({
        host_baseline.fingerprint_key(fp): {
            "fingerprint": fp, "mean_cycle_seconds": 0.1, "date": "t", "derivation": "t", "load": "t"
        }
    }), encoding="utf-8")
    monkeypatch.setenv("MEAN_CYCLE_BASELINE_STORE", str(store))
    r = LiveCaptureRunner(persist_path="x.jsonl", duration_seconds=10,
                          trading_env="paper", data_source="kraken_v2")
    assert r._mean_cycle_baseline == 0.1
