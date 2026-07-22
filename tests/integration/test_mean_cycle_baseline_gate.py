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


def test_this_host_active_ledger_is_full_loop_with_the_adapter_only_ledger_closed():
    """WO-013 item 1: the ACTIVE ledger is the full-loop (widened) instrument, opened at entry zero.
    The adapter-only ledger CLOSED into closed_instrument_ledgers — retained (valid for what it
    measured), never invalidated — and it carries the WO-017 re-baseline history (0.107923 with its
    superseded 0.108886). The sixth scope dimension (instrument) and fifth (resolution) are present."""
    rec = host_baseline.load_baseline()
    assert rec["instrument"] == "full-loop"
    assert rec["mean_cycle_seconds"] == 0.108717           # loop-boundary entry zero (median of 9)
    assert "superseded" not in rec, "entry zero: no cross-instrument history inherited"
    assert "instrument" in rec["scope"] and "resolution" in rec["scope"] and "load_work" in rec["scope"]

    closed = rec["closed_instrument_ledgers"]
    assert closed and closed[0]["instrument"] == "adapter-only"
    assert closed[0]["mean_cycle_seconds"] == 0.107923     # the adapter-only ledger's last active figure
    assert closed[0]["ledger_closed_date"]                 # closed, not invalidated
    # its own WO-017 history is retained inside the closed ledger
    assert closed[0]["superseded"][0]["mean_cycle_seconds"] == 0.108886


def test_save_baseline_never_overwrites_a_differing_figure(tmp_path, monkeypatch):
    """WO-017 §5 (durable): save_baseline carries a DIFFERING prior figure into `superseded`
    (end-dated) rather than overwrite it; a same-figure re-run just refreshes and does not
    manufacture a spurious superseded entry."""
    store = tmp_path / "s.json"
    monkeypatch.setenv("MEAN_CYCLE_BASELINE_STORE", str(store))
    fp = host_baseline.host_fingerprint()

    r1 = host_baseline.save_baseline(0.100000, "d1", "2026-01-01", "l1", fp=fp)
    assert r1["mean_cycle_seconds"] == 0.100000 and "superseded" not in r1

    r2 = host_baseline.save_baseline(0.090000, "d2", "2026-02-02", "l2", fp=fp)
    assert r2["mean_cycle_seconds"] == 0.090000
    assert [s["mean_cycle_seconds"] for s in r2["superseded"]] == [0.100000]
    assert r2["superseded"][0]["scope_end_date"] == "2026-02-02"    # end-dated with the new date

    # a THIRD, differing figure prepends and preserves the whole ledger (newest-first)
    r3 = host_baseline.save_baseline(0.080000, "d3", "2026-03-03", "l3", fp=fp)
    assert [s["mean_cycle_seconds"] for s in r3["superseded"]] == [0.090000, 0.100000]

    # a same-figure re-run (confirmation) does NOT add a spurious entry
    r4 = host_baseline.save_baseline(0.080000, "d4", "2026-04-04", "l4", fp=fp)
    assert [s["mean_cycle_seconds"] for s in r4["superseded"]] == [0.090000, 0.100000]
    assert host_baseline.load_baseline(fp=fp)["mean_cycle_seconds"] == 0.080000


def test_instrument_mismatch_is_refused_not_warned():
    """WO-013 item 1: a cross-instrument delta is REFUSED with the declared code — a measurement on
    one boundary differenced against a baseline on another is uninterpretable by construction."""
    adapter_only = {"instrument": "adapter-only", "mean_cycle_seconds": 0.107923}
    with pytest.raises(ValueError, match="MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH"):
        host_baseline.require_measurement_instrument("full-loop", adapter_only)
    # same instrument passes (no raise)
    host_baseline.require_measurement_instrument("adapter-only", adapter_only)
    # a legacy record (no instrument field) reads as adapter-only, so full-loop still refuses
    with pytest.raises(ValueError, match="MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH"):
        host_baseline.require_measurement_instrument("full-loop", {"mean_cycle_seconds": 0.1})
    assert host_baseline.record_instrument({}) == "adapter-only"


def test_save_baseline_closes_prior_ledger_on_instrument_change(tmp_path, monkeypatch):
    """WO-013 item 1: a DIFFERENT-instrument write CLOSES the prior ledger (into
    closed_instrument_ledgers, valid for what it measured) and OPENS the new one at ENTRY ZERO —
    never inheriting a cross-instrument delta into `superseded`."""
    store = tmp_path / "s.json"
    monkeypatch.setenv("MEAN_CYCLE_BASELINE_STORE", str(store))
    fp = host_baseline.host_fingerprint()

    # adapter-only ledger with some history
    host_baseline.save_baseline(0.108000, "d1", "2026-01-01", "l1", fp=fp, instrument="adapter-only")
    host_baseline.save_baseline(0.107900, "d2", "2026-02-02", "l2", fp=fp, instrument="adapter-only")
    rec = host_baseline.load_baseline(fp=fp)
    assert rec["instrument"] == "adapter-only" and len(rec["superseded"]) == 1

    # cross to full-loop: prior ledger CLOSES, new opens at entry zero (no inherited superseded)
    rec2 = host_baseline.save_baseline(0.108714, "d3", "2026-03-03", "l3", fp=fp, instrument="full-loop")
    assert rec2["instrument"] == "full-loop"
    assert rec2["mean_cycle_seconds"] == 0.108714
    assert "superseded" not in rec2, "entry zero: no cross-instrument history inherited"
    assert len(rec2["closed_instrument_ledgers"]) == 1
    closed = rec2["closed_instrument_ledgers"][0]
    assert closed["instrument"] == "adapter-only"
    assert closed["mean_cycle_seconds"] == 0.107900          # the closed ledger's last active figure
    assert closed["ledger_closed_date"] == "2026-03-03"
    assert len(closed["superseded"]) == 1                    # its own history retained, not invalidated

    # same-instrument re-baseline now supersedes WITHIN the full-loop ledger (not the closed one)
    rec3 = host_baseline.save_baseline(0.108500, "d4", "2026-04-04", "l4", fp=fp, instrument="full-loop")
    assert [s["mean_cycle_seconds"] for s in rec3["superseded"]] == [0.108714]
    assert len(rec3["closed_instrument_ledgers"]) == 1       # still there, unchanged


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
