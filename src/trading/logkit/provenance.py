"""
Provenance Helpers

Utilities for strategy version and feature snapshot tracking.

Constitutional Principles:
- VIII. Total Observability & Provenance: Decision reconstruction
"""

from typing import Optional


def get_strategy_version() -> str:
    """
    Get current strategy version identifier.

    Returns:
        Strategy version string (e.g., "trivial-momentum-v1.0.0")

    Constitutional requirements:
        - Strategy version identifies which logic produced a decision (Principle VIII)
    """
    return "trivial-momentum-v1.0.0"


def validate_snapshot_hash(snapshot_hash: Optional[str]) -> bool:
    """
    Validate feature snapshot hash format.

    Args:
        snapshot_hash: Hash string to validate

    Returns:
        True if valid (non-empty string), False otherwise

    Constitutional requirements:
        - Feature snapshot hash enables decision reconstruction (Principle VIII)
    """
    if snapshot_hash is None:
        return False
    if not isinstance(snapshot_hash, str):
        return False
    return len(snapshot_hash) > 0
