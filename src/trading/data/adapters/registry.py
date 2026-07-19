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

from typing import Callable, Dict

_REGISTRY: Dict[str, Callable] = {}


def register(name: str) -> Callable:
    """Decorator registering a builder callable under a config name."""

    def _decorator(builder: Callable) -> Callable:
        if name in _REGISTRY:
            raise ValueError(f"Adapter name already registered: {name!r}")
        _REGISTRY[name] = builder
        return builder

    return _decorator


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
