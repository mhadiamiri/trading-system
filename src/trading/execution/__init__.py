"""
Execution Layer - Order Execution Models and Clients

Constitutional Principles:
- VI. Risk Engine Is Sovereign: Clamp only reduces toward zero
- VII. Venue Independence: Strict abstraction over venue
- IX. Secrets and Safety Rails: No real-money orders
"""

from trading.execution.approved_order import ApprovedOrder
from trading.execution.fill import Fill
from trading.execution.interface import ExchangeClient, KillSwitchEngagedError
from trading.execution.paper import PaperExecutionClient

__all__ = [
    "ApprovedOrder",
    "Fill",
    "ExchangeClient",
    "KillSwitchEngagedError",
    "PaperExecutionClient",
]
