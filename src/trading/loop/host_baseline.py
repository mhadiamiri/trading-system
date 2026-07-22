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


def load_baseline(store_path: Optional[str] = None, fp: Optional[dict] = None) -> Optional[dict]:
    """Return THIS host's baseline record (matching fingerprint_key) or None if the host has none."""
    return load_store(store_path).get(fingerprint_key(fp))


def save_baseline(mean_cycle_seconds: float, derivation: str, date: str, load: str,
                  store_path: Optional[str] = None, fp: Optional[dict] = None,
                  scope: Optional[dict] = None, rebaseline: Optional[dict] = None) -> dict:
    """Write this host's baseline record. Used by the establishment protocol
    (tools/establish_mean_cycle_baseline.py) — NOT by the runtime capture path.

    NEVER OVERWRITES A DIFFERING FIGURE (WO-017 §5): if a record already exists for this host
    and its mean_cycle_seconds differs, that prior record is carried into the new record's
    `superseded` ledger — annotated with `scope_end_date` and an end reason — ahead of any
    superseded entries it already carried. The baseline history thus stays a traceable ledger
    of the pipeline's performance evolution (no orphan figures). A re-run at the SAME figure
    (a confirmation, not a re-declaration) simply refreshes the active record. `scope` and
    `rebaseline` (when given) are recorded verbatim on the active record.
    """
    path = store_path or _default_store()
    fp = fp if fp is not None else host_fingerprint()
    store = load_store(path)
    key = fingerprint_key(fp)
    prior = store.get(key)

    superseded = []
    if prior is not None and prior.get("mean_cycle_seconds") != mean_cycle_seconds:
        prior_entry = {k: v for k, v in prior.items() if k != "superseded"}
        prior_entry["scope_end_date"] = date
        prior_entry.setdefault(
            "end_reason",
            f"Superseded by the {date} re-baseline ({mean_cycle_seconds}s); retained (never "
            "overwritten) so the baseline ledger stays traceable (WO-017 §5).")
        superseded = [prior_entry] + list(prior.get("superseded", []))
    elif prior is not None:
        superseded = list(prior.get("superseded", []))

    record = {
        "fingerprint": fp,
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

    store[key] = record
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=1, sort_keys=True)
    return record
