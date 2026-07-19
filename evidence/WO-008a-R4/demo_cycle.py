"""
Quick demonstration of full 4-layer cycle with visible costs.
"""
import asyncio
import os
from datetime import datetime, UTC
from decimal import Decimal

# Force simulated feed
os.environ["DATA_SOURCE"] = "simulated"

from trading.loop.live import LiveTradingLoop
from trading.data.market_state import MarketState

async def main():
    """Run a short cycle with visible output."""
    loop = LiveTradingLoop()

    print("=" * 60)
    print("WO-008a-R4: Full Cycle Demonstration with Cost Fix")
    print("=" * 60)

    # Run with a few updates to see at least one fill
    result = await loop.run(max_updates=100, duration_minutes=1)

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
