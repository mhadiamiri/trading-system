"""WO-044 §3 bite-proof CHILD — one corpus capture run, driven by a SCRIPTED transport.

Launched twice by `tools/wo044_resume_bite_proof.py`: once as the run that gets KILLED mid-capture,
once as the resume. It exists as its own process on purpose — the seam this proves is an INTER-
PROCESS boundary, and the only honest way to produce one is to actually kill a process. A same-
process simulation would prove the bookkeeping while assuming away the thing under test.

NO NETWORK: `connect_fn` is the scripted fake transport, so no socket is ever opened.
Writes only under the corpus dir it is given (a tmp dir owned by the parent).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME           # noqa: E402
from tools.live_corpus_capture import CorpusCaptureRunner, RotationConfig  # noqa: E402


class _PacedSocket:
    """A scripted socket that SPACES its frames in time.

    The shared fixture delivers a whole script back-to-back, which would make every run span
    milliseconds and reduce the cumulative-hours property to "0 equals 0" — a vacuous proof.
    Spacing the frames gives each run a real measured span, so §3.7's accounting is exercised on
    numbers that can actually be wrong. Once the script drains it emits paced heartbeats, keeping
    the link live so the run ends on its deadline (or, for the killed child, not at all).
    """

    def __init__(self, frames, spacing):
        self._frames = list(frames)
        self._index = 0
        self._spacing = spacing
        self.sent = []
        self.closed = False

    async def send(self, message):
        self.sent.append(json.loads(message))

    async def recv(self):
        await asyncio.sleep(self._spacing)
        if self._index < len(self._frames):
            frame = self._frames[self._index]
            self._index += 1
            return json.dumps(frame)
        return json.dumps({"channel": "heartbeat"})

    async def close(self):
        self.closed = True

    async def ping(self, data=None):
        fut = asyncio.get_event_loop().create_future()
        fut.set_result(0.001)
        return fut


class _PacedConnectionFactory:
    """Drop-in for `websockets.connect` handing out paced sockets. NO NETWORK."""

    def __init__(self, frames, spacing):
        self._frames = frames
        self._spacing = spacing
        self.connect_count = 0
        self.sockets = []

    async def connect(self, *args, **kwargs):
        self.connect_count += 1
        sock = _PacedSocket(self._frames, self._spacing)
        self.sockets.append(sock)
        return sock


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-dir", required=True)
    ap.add_argument("--corpus-id", required=True)
    ap.add_argument("--seam-cause", default=None)
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--frame-spacing", type=float, default=0.5)
    ap.add_argument("--duration-hours", type=float, default=0.02)
    args = ap.parse_args()

    # Each SNAPSHOT_FRAME validates its own CRC32 and emits one MarketState, so N snapshots give N
    # frames — spaced, so the run has a measurable span. Heartbeats after the script keep the link
    # alive so the run ends on its DEADLINE rather than on heartbeat-absence; a killed child simply
    # never reaches that deadline.
    factory = _PacedConnectionFactory([SNAPSHOT_FRAME] * args.frames, args.frame_spacing)

    config = RotationConfig.from_env()
    config.corpus_dir = Path(args.corpus_dir)
    config.corpus_id = args.corpus_id

    runner = CorpusCaptureRunner(
        config=config,
        trading_env="paper",
        connect_fn=factory.connect,
        seam_cause=args.seam_cause,
        duration_hours=args.duration_hours,
    )
    asyncio.run(runner.run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
