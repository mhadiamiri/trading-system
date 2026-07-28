#!/usr/bin/env python3
"""
WO-039 §1: Diagnose which fixture set reaches both hooks through the real path.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from fixtures.fake_ws_transport import ScriptedConnectionFactory
from fixtures.kraken_v2_raw_frames import ALL_BOOK_FRAMES
from fixtures.kraken_v2_captured_frames import ALL_CAPTURED_FRAMES
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter


async def test_fixture(fixture_name, frames):
    """Test if frames reach both hooks."""
    print(f"\nTesting {fixture_name} ({len(frames)} frames):")
    factory = ScriptedConnectionFactory([frames], on_drain="timeout")
    adapter = KrakenV2BookAdapter(
        mode=KrakenV2BookAdapter.MODE_LIVE,
        connect_fn=factory.connect,
    )
    adapter._persistence_optional = True

    states_collected = 0
    raw_received = 0

    async for state in adapter.get_live_market_data(duration_seconds=5.0):
        states_collected += 1
        raw_received = adapter._raw_received
        if states_collected >= 10:
            break

    print(f"  States collected: {states_collected}")
    print(f"  Raw frames received: {raw_received}")
    return states_collected, raw_received


async def main():
    print("=" * 70)
    print("WO-039 §1: FIXTURE PATH DIAGNOSIS")
    print("=" * 70)

    await test_fixture("raw_frames (4 frames)", ALL_BOOK_FRAMES)
    await test_fixture("captured_frames (41 frames)", ALL_CAPTURED_FRAMES)


if __name__ == "__main__":
    asyncio.run(main())
