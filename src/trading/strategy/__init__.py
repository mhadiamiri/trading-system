"""
Strategy Layer - Trading Strategy Models and Implementations

Constitutional Principles:
- III. AI Proposes, Deterministic Code Disposes: No confidence field
"""

from trading.strategy.interface import Strategy
from trading.strategy.trivial import TrivialMomentumStrategy

# Re-export data models for convenience
from trading.data.desired_position import DesiredPosition, Side

__all__ = ["DesiredPosition", "Side", "Strategy", "TrivialMomentumStrategy"]
