"""WO-016 §D28 — host-scoped mean-cycle baseline: fingerprint + per-host store.

A DECLARED CONSTANT IS ONLY AS PORTABLE AS THE THING IT WAS MEASURED ON. The UNIFORM-drift
baseline (kraken_v2_book.MEAN_CYCLE_BASELINE_SECONDS) is a HOST property — scheduler, Python
build, background load — not a pipeline property. So it is stored PER HOST, fingerprinted, and the
live-capture runner REFUSES to start on a host with no matching baseline (D28.B) rather than
convicting UNIFORM at startup against a reference from a machine that is not running.

The raw hostname is HASHED (0.5-adjacent hygiene: these files are committed; a personal machine
name in the repo is avoidable — not a secret, but unnecessary).
"""
import hashlib
import json
import os
import platform
from typing import Optional

# repo root: src/trading/loop/host_baseline.py -> loop -> trading -> src -> <repo>
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_STORE_PATH = os.path.join(_REPO, "config", "mean_cycle_baselines.json")


def _default_store() -> str:
    """The committed per-host store, overridable by env for tests/tools (idiomatic, like
    DATA_SOURCE/TRADING_ENV — avoids a runner signature change, rule 0.1a)."""
    return os.environ.get("MEAN_CYCLE_BASELINE_STORE") or DEFAULT_STORE_PATH


def host_fingerprint() -> dict:
    """The properties that MAKE THE BASELINE WHAT IT IS. `machine_id` is a TRUNCATED HASH of the
    hostname, never the raw name."""
    return {
        "machine_id": hashlib.sha256(platform.node().encode("utf-8")).hexdigest()[:16],
        "python_version": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
        "cpu_arch": platform.machine(),
    }


def fingerprint_key(fp: Optional[dict] = None) -> str:
    """Stable lookup key for a fingerprint — a truncated hash of the four properties."""
    fp = fp if fp is not None else host_fingerprint()
    return hashlib.sha256(json.dumps(fp, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def load_store(store_path: Optional[str] = None) -> dict:
    path = store_path or _default_store()
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# WO-013 follow-up item 1: INSTRUMENT identity is the sixth scope dimension. A record with no
# `instrument` field predates the dimension and measured the ADAPTER-ONLY boundary (the legacy
# establishment). The active/default instrument is the FULL LOOP (WO-013 B).
LEGACY_INSTRUMENT = "adapter-only"
ACTIVE_INSTRUMENT = "full-loop"
INSTRUMENT_MISMATCH_CODE = "MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH"


def record_instrument(record: dict) -> str:
    """The instrument a baseline record was measured on. Absent field => legacy adapter-only."""
    return (record or {}).get("instrument", LEGACY_INSTRUMENT)


def require_measurement_instrument(measured_instrument: str, record: dict) -> None:
    """WO-013 item 1: REFUSE (not warn) a cross-instrument delta. A measurement on one instrument
    differenced against a baseline on another is UNINTERPRETABLE BY CONSTRUCTION (two boundaries).
    Raises with the declared reason code, same treatment as MEAN_CYCLE_BASELINE_HOST_MISMATCH."""
    stored = record_instrument(record)
    if stored != measured_instrument:
        raise ValueError(
            f"{INSTRUMENT_MISMATCH_CODE}: cannot difference a '{measured_instrument}' measurement "
            f"against a '{stored}' baseline — two instruments, two boundaries, delta uninterpretable. "
            "The loop-boundary ledger opens at entry zero; it is never inherited via a cross-instrument "
            "delta (WO-013 follow-up item 1)."
        )


def load_baseline(store_path: Optional[str] = None, fp: Optional[dict] = None) -> Optional[dict]:
    """Return THIS host's ACTIVE baseline record (matching fingerprint_key) or None if the host has
    none. The active record carries `instrument`; closed different-instrument ledgers are retained on
    it under `closed_instrument_ledgers` (valid for what they measured, not the active reference)."""
    return load_store(store_path).get(fingerprint_key(fp))


def save_baseline(mean_cycle_seconds: float, derivation: str, date: str, load: str,
                  store_path: Optional[str] = None, fp: Optional[dict] = None,
                  scope: Optional[dict] = None, rebaseline: Optional[dict] = None,
                  instrument: str = ACTIVE_INSTRUMENT) -> dict:
    """Write this host's baseline record for INSTRUMENT (default: the full loop). Used by the
    establishment protocol — NOT the runtime capture path.

    NEVER OVERWRITES A DIFFERING FIGURE (WO-017 §5), and NEVER INHERITS ACROSS INSTRUMENTS (WO-013
    item 1):
      - SAME instrument, differing figure -> prior carried into `superseded` (end-dated); the ledger
        of that instrument's performance evolution stays traceable (no orphan figures).
      - DIFFERENT instrument -> the prior ledger CLOSES: it is moved (with its whole `superseded`
        history) into `closed_instrument_ledgers`, annotated, and the new record opens at ENTRY ZERO
        (no `superseded` inherited). A cross-instrument delta is refused, never differenced.
      - SAME figure, same instrument -> a confirmation; refresh the active record.
    """
    path = store_path or _default_store()
    fp = fp if fp is not None else host_fingerprint()
    store = load_store(path)
    key = fingerprint_key(fp)
    prior = store.get(key)

    superseded = []
    closed_ledgers = []
    if prior is not None and record_instrument(prior) != instrument:
        # Instrument boundary changed: CLOSE the prior ledger, OPEN the new one at entry zero.
        closed = {k: v for k, v in prior.items() if k != "closed_instrument_ledgers"}
        closed["ledger_closed_date"] = date
        closed.setdefault(
            "close_reason",
            f"Instrument boundary changed to '{instrument}' on {date}; this '{record_instrument(prior)}' "
            "ledger CLOSES. Its entries remain VALID FOR WHAT THEY MEASURED — not invalidated, never "
            "differenced against the new instrument (WO-013 item 1).")
        closed_ledgers = [closed] + list(prior.get("closed_instrument_ledgers", []))
    elif prior is not None and prior.get("mean_cycle_seconds") != mean_cycle_seconds:
        prior_entry = {k: v for k, v in prior.items()
                       if k not in ("superseded", "closed_instrument_ledgers")}
        prior_entry["scope_end_date"] = date
        prior_entry.setdefault(
            "end_reason",
            f"Superseded by the {date} re-baseline ({mean_cycle_seconds}s); retained (never "
            "overwritten) so the baseline ledger stays traceable (WO-017 §5).")
        superseded = [prior_entry] + list(prior.get("superseded", []))
        closed_ledgers = list(prior.get("closed_instrument_ledgers", []))
    elif prior is not None:
        superseded = list(prior.get("superseded", []))
        closed_ledgers = list(prior.get("closed_instrument_ledgers", []))

    record = {
        "fingerprint": fp,
        "instrument": instrument,
        "mean_cycle_seconds": mean_cycle_seconds,
        "date": date,
        "derivation": derivation,
        "load": load,
    }
    if scope is not None:
        record["scope"] = scope
    if rebaseline is not None:
        record["rebaseline"] = rebaseline
    if superseded:
        record["superseded"] = superseded
    if closed_ledgers:
        record["closed_instrument_ledgers"] = closed_ledgers

    store[key] = record
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=1, sort_keys=True)
    return record
