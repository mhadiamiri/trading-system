"""
Adapter registry (WO-010 §5).

Adapters self-register under a config name; the factory resolves by name.

This exists so that no module outside `trading.data.adapters` needs to import a
concrete adapter module. A lazy/function-local import was explicitly rejected:
it would hide the dependency from static analysis, which is the exact defect
shape this remediation is about.

This is also Sprint 3's venue-swap mechanism: add one adapter module, it
registers itself, config names it, nothing else moves.
"""

from __future__ import annotations

from typing import Callable, Dict, Set

_REGISTRY: Dict[str, Callable] = {}
# WO-015 review: adapters that support a LIVE capture (an instrumented real-socket transport,
# get_live_market_data + gap ledger + discrimination). Declared at registration — EXPLICIT
# capability, not inferred by catching a builder's kwarg TypeError (which could mask real bugs).
# The factory checks this BEFORE building, so a live capture of a non-live source refuses
# cleanly and specifically instead of connecting to the wrong venue or crashing cryptically.
_LIVE_CAPABLE: Set[str] = set()


def register(name: str, *, live_capture: bool = False) -> Callable:
    """Decorator registering a builder callable under a config name. `live_capture=True` declares
    the adapter supports a live capture (WO-015)."""

    def _decorator(builder: Callable) -> Callable:
        if name in _REGISTRY:
            raise ValueError(f"Adapter name already registered: {name!r}")
        _REGISTRY[name] = builder
        if live_capture:
            _LIVE_CAPABLE.add(name)
        return builder

    return _decorator


def is_live_capable(name: str) -> bool:
    """WO-015: whether the named adapter declared support for a live capture."""
    return name in _LIVE_CAPABLE


def create(name: str, **kwargs):
    """Resolve and construct an adapter by its registered config name."""
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown data source: {name!r}. Registered: {registered_names()}"
        )
    return _REGISTRY[name](**kwargs)


def registered_names() -> list[str]:
    """Sorted list of registered config names."""
    return sorted(_REGISTRY)
