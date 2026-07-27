"""WO-029 §2.0-bis — bite proof: the self-advancing coherent clock (AdvancingClock) FIRES a deadline
and does NOT fire prematurely. Four artifacts, sha256 exact-restore of the harness (fake_ws_transport.py).

Proven through the ADAPTER's deadline path — the same signal race 4 checks (connect_count == 1, i.e. the
deadline ended the run WITHOUT reconnecting; capture_terminated is None; no KEEPALIVE_RECONNECT/
VENUE_DISCONNECT gap):

  A1 FIRES (positive): a heartbeat-drained run (SNAPSHOT then infinite heartbeats) on an AdvancingClock
     whose advance REACHES the deadline → the run terminates via the DEADLINE (connect_count == 1, no
     reconnect, capture_terminated None), AND the snapshot was processed FIRST (emitted >= 1 — the
     deadline did not fire before the events).
  A1b DOES NOT FIRE PREMATURELY (preservation dual, local & direct): a BOUNDED script (SNAPSHOT + clean
     close) on an AdvancingClock whose advance is too small to reach the deadline → the run CONTINUES,
     processes the snapshot, and ends via the CLEAN CLOSE, not the deadline (capture_terminated None,
     emitted >= 1). Proves the clock does not fire before the threshold.
  A2 NECESSITY (mutate the advance to fire PREMATURELY): make the advance huge → the deadline fires on
     the first check, BEFORE the snapshot → emitted == 0. Proves a too-eager clock makes race 4 pass for
     the wrong reason (the failure this fixture exists to prevent), and that A1's advance is load-bearing.
  A3 RESTORED: A1 fires-after-events again. A4 sha256(fake_ws_transport.py) AFTER == BEFORE.
"""
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "tests", "fixtures", "fake_ws_transport.py")
# WO-032 §4.1 — an INSTRUMENT writes to a git-ignored, run-scoped `.artifacts/` path and NEVER into
# `evidence/` (WO-026 §2's doctrine, generalized past the gate ledger). Evidence is a DELIBERATE
# snapshot, not a side effect of running a tool. Guarded: tests/test_evidence_write_boundary.py.
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "advancing_clock_bite_proof")

ANCHOR = "            self._counter += self._delta      # advance AFTER reading: the deadline-set read sees `start`"
WEAK = "            self._counter += self._delta * 1_000_000      # WEAKENED: fires prematurely (before events)"

# A1 (FIRES) + A1b (not-premature), run in a subprocess so a fresh import picks up the current harness.
CHECK = '''
import asyncio
from websockets.frames import Close
from websockets.exceptions import ConnectionClosedOK
from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import AdvancingClock, ScriptedConnectionFactory
MODE_LIVE = KrakenV2BookAdapter.MODE_LIVE
CLEAN = ConnectionClosedOK(Close(1000, "normal closure"), None)

def _adapter(clk, conn):
    a = KrakenV2BookAdapter(mode=MODE_LIVE, monotonic_clock=clk.monotonic, connect_fn=conn.connect)
    a._persistence_optional = True
    a._wall_clock = clk.wall
    a._heartbeat_absence_timeout = 100.0
    a._app_ping_interval = 100.0
    return a

async def fires():
    clk = AdvancingClock(delta=0.05)     # reaches a 0.15s deadline after a few reads
    conn = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME], "on_drain": "heartbeat"}])
    a = _adapter(clk, conn)
    emitted = [s async for s in a.get_live_market_data(duration_seconds=0.15)]
    reconnect = [g for g in a.get_gap_ledger().gaps if g.cause in ("KEEPALIVE_RECONNECT","VENUE_DISCONNECT")]
    return conn.connect_count, len(emitted), a.capture_terminated, reconnect

async def not_premature():
    clk = AdvancingClock(delta=0.0001)   # too small to reach 0.15 within the bounded script
    conn = ScriptedConnectionFactory([{"frames": [SNAPSHOT_FRAME, CLEAN], "on_drain": "block"}])
    a = _adapter(clk, conn)
    emitted = [s async for s in a.get_live_market_data(duration_seconds=0.15)]
    return conn.connect_count, len(emitted), a.capture_terminated

cc, em, term, rec = asyncio.run(fires())
print(f"FIRES: connect_count={cc} emitted={em} terminated={term} reconnect_gaps={len(rec)}")
cc2, em2, term2 = asyncio.run(not_premature())
print(f"NOT_PREMATURE: connect_count={cc2} emitted={em2} terminated={term2}")
'''


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run():
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run([sys.executable, "-c", CHECK], cwd=REPO, env=env, capture_output=True, text=True,
                       timeout=60)
    return (p.stdout + p.stderr).strip()


def main():
    original = open(SRC, "rb").read()
    assert original.decode().count(ANCHOR) == 1, "advance anchor not unique in fake_ws_transport.py"
    before = sha256(SRC)
    out = ["WO-029 §2.0-bis BITE PROOF — AdvancingClock FIRES a deadline (not prematurely); 4 artifacts, sha256",
           f"Harness: {os.path.relpath(SRC, REPO)}  (AdvancingClock — the frozen FakeClock made to move)",
           "Signal = race 4's: connect_count==1 (deadline close, no reconnect) + capture_terminated None",
           f"sha256 BEFORE: {before}", ""]

    r1 = run()
    out += ["-- ARTIFACT 1 — FIRES + DOES-NOT-FIRE-PREMATURELY (pristine) --",
            "  " + r1.replace("\n", "\n  "),
            "  Expect FIRES: connect_count=1 emitted>=1 terminated=None reconnect_gaps=0 (deadline ended it, after the snapshot)",
            "  Expect NOT_PREMATURE: emitted>=1 terminated=None (ran to the snapshot; ended via clean close, deadline not reached)",
            ""]

    open(SRC, "wb").write(original.decode().replace(ANCHOR, WEAK).encode())
    r2 = run()
    out += ["-- ARTIFACT 2 — NECESSITY (advance mutated to fire PREMATURELY: *1_000_000) --",
            "  " + r2.replace("\n", "\n  "),
            "  Expect FIRES: emitted=0 — the deadline fired BEFORE the snapshot (race 4 would pass for the wrong reason)",
            f"  sha256 WHILE MUTATED: {sha256(SRC)}", ""]

    open(SRC, "wb").write(original)
    r3 = run()
    out += ["-- ARTIFACT 3 — RESTORED --", "  " + r3.replace("\n", "\n  "), ""]

    after = sha256(SRC)
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --",
            f"sha256 AFTER:  {after}", f"IDENTICAL: {'YES' if after == before else 'NO'}", ""]

    a1_ok = "FIRES: connect_count=1 emitted=" in r1 and "emitted=0" not in r1.split("FIRES:")[1].split("\\n")[0]
    fires_line = [l for l in r1.splitlines() if l.startswith("FIRES:")]
    notp_line = [l for l in r1.splitlines() if l.startswith("NOT_PREMATURE:")]
    fires_ok = bool(fires_line) and "connect_count=1" in fires_line[0] and "emitted=0" not in fires_line[0] \
        and "terminated=None" in fires_line[0] and "reconnect_gaps=0" in fires_line[0]
    notp_ok = bool(notp_line) and "emitted=0" not in notp_line[0] and "terminated=None" in notp_line[0]
    mut_line = [l for l in r2.splitlines() if l.startswith("FIRES:")]
    mut_ok = bool(mut_line) and "emitted=0" in mut_line[0]
    verdict = "PASS" if (fires_ok and notp_ok and mut_ok and after == before) else "FAIL"
    out += [f"VERDICT: {verdict}"]

    from datetime import datetime, timezone          # WO-032 §4.1 — run-scoped artifact name
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    _body = "\n".join(out) + "\n"
    _run = os.path.join(ARTIFACT_DIR, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for _p in (_run, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(_p, "w", encoding="utf-8").write(_body)
    print("\n".join(out))
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(_run, REPO)} (git-ignored)")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
