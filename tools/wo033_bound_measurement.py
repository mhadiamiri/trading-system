"""WO-033 — BOUND MEASUREMENT PASS: measure all 6 remaining audit BOUNDS (entries 31-34, 36-37).

D40 ruled: *bound-versus-race is a measurement, not a margin argument; a bound classified by prose
ratio is a race pending measurement.* Entry 35 was already flipped by WO-031 §3-bis. This instrument
executes the measurement on the other six. It CLASSIFIES; it converts nothing.

TWO DESIGNS, by claim-kind (the distinction is honored in the measurement, never used to exempt a
bound from being measured):

  §3.A ZERO-CONSULTATION (entries 36, 37 — "terminates BEFORE the deadline is consulted")
      A COUNTING CLOCK is injected through the same `monotonic_clock` seam a conversion would use,
      so nothing in src/ is edited. It counts every consultation of the deadline clock AND records
      the kraken_v2_book.py LINE that made each call, so the result names WHICH of the three pinned
      deadline sites was reached (:2548 set / :2594 guard / :2727 recv-timeout) rather than only how
      many times. count == 0 => the structural claim is OBSERVED, not asserted.

  §3.B RATIO / FRAMES-REACHED (entries 31-34 — "~300x margin")
      WO-031 §3-bis's form. Drive each test's real path under the real clock (measuring the ACTUAL
      elapsed time to the terminator, which replaces the audit's prose ratio with a number), then
      under `AdvancingClock` across a delta spread, recording whether the terminator still precedes
      the deadline.

The counting clock is COHERENT (it carries the inner clock's `_coherence_token` on both readers), so
the pre-connection gate PROCEEDs rather than refusing and masking the count (WO-031 §Attempt 6).

    python tools/wo033_bound_measurement.py

Writes to .artifacts/ (WO-032 §4.1 — a tools/ script never writes under evidence/).
"""
import asyncio
import copy
import json
import os
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)

ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo033_bound_measurement")
ADAPTER_SRC = "kraken_v2_book.py"

from websockets.frames import Close                                           # noqa: E402
from websockets.exceptions import ConnectionClosedError                       # noqa: E402

from trading.data.adapters.kraken_v2_book import (                            # noqa: E402
    KrakenV2BookAdapter, CircuitBreakerTripped,
)
from tests.fixtures.fake_ws_transport import (                                # noqa: E402
    AdvancingClock, FakeClock, ScriptedConnectionFactory, REOPEN_FAILURE,
)
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME                # noqa: E402

DELTAS = (0.0001, 0.01, 0.05, 0.5, 5.0)


# ─────────────────────────────────────────────────────────────────────────────
# The counting clock (§3.A). Coherent, so the gate proceeds; instrumented, so a
# consultation names its call site.
# ─────────────────────────────────────────────────────────────────────────────
class CountingClock:
    """A COHERENT clock pair that counts deadline-clock consultations and their call sites.

    Wraps `AdvancingClock` so coherence (shared `_coherence_token`, D25 offsets) is inherited from
    the operated harness rather than re-implemented. `delta=0.0` makes it frozen — for a
    zero-consultation measurement the clock must not change behaviour, only observe it.
    """

    def __init__(self, delta=0.0):
        # delta == 0 => FROZEN. `AdvancingClock` deliberately refuses delta<=0 ("a deadline that
        # never advances cannot fire"), which is right for its purpose and wrong for this one: a
        # zero-consultation probe must OBSERVE without perturbing. `FakeClock` is the frozen member
        # of the same coherent family (same shared-token construction, same D25 offsets), so the
        # measurement inherits coherence from the operated harness either way.
        self._inner = AdvancingClock(delta=delta) if delta else FakeClock()
        self.count = 0
        self.sites = {}

        def _monotonic():
            self.count += 1
            for frame in reversed(traceback.extract_stack()):
                if frame.filename.endswith(ADAPTER_SRC):
                    self.sites[frame.lineno] = self.sites.get(frame.lineno, 0) + 1
                    break
            return self._inner.monotonic()

        # The SAME token object the inner clock stamps on its wall reader, so the gate's
        # COHERENCE check sees one source and PROCEEDs (a refusal would mask the count).
        _monotonic._coherence_token = self._inner
        self.monotonic = _monotonic
        self.wall = self._inner.wall


def _bad_snapshot():
    bad = copy.deepcopy(SNAPSHOT_FRAME)
    bad["data"][0]["checksum"] = 1
    return bad


def _attach(adapter, clock):
    if clock is not None:
        adapter._monotonic_clock = clock.monotonic
        adapter._wall_clock = clock.wall
    return adapter


# ─────────────────────────────────────────────────────────────────────────────
# §3.A — entries 36 and 37
# ─────────────────────────────────────────────────────────────────────────────
async def entry36(clock):
    """test_no_silent_fallback.py:25 test_connection_failure_raises_and_does_not_replay_fixtures"""
    async def _boom(*args, **kwargs):
        raise OSError("simulated: connection refused")

    a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=_boom)
    a._persistence_optional = True
    _attach(a, clock)
    emitted, raised = [], None
    try:
        async for s in a.get_live_market_data(duration_seconds=5):
            emitted.append(s)
    except ConnectionError as e:
        raised = f"ConnectionError: {str(e)[:60]}"
    except Exception as e:                                    # noqa: BLE001 — report, don't mask
        raised = f"{type(e).__name__}: {str(e)[:60]}"
    return {"terminator": raised, "emitted": len(emitted)}


async def entry37(clock):
    """test_no_silent_fallback.py:51 test_live_method_refuses_fixture_mode_adapter"""
    a = KrakenV2BookAdapter()          # fixture mode — the refusal is the point
    _attach(a, clock)
    raised = None
    try:
        async for _ in a.get_live_market_data(duration_seconds=1):
            pass
    except ValueError as e:
        raised = f"ValueError: {str(e)[:60]}"
    except Exception as e:                                    # noqa: BLE001
        raised = f"{type(e).__name__}: {str(e)[:60]}"
    return {"terminator": raised, "emitted": 0}


# ─────────────────────────────────────────────────────────────────────────────
# §3.B — entries 31, 32, 33, 34
# ─────────────────────────────────────────────────────────────────────────────
def _breaker_adapter(factory, clock):
    a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory.connect)
    a._persistence_optional = True
    a._reconnect_jitter = lambda: 1.0
    a._reconnect_backoff_base = 0.01
    a._reconnect_backoff_cap = 0.04
    a._reconnect_sleep = None                 # REAL tiny sleeps — the duration breaker needs them
    a._reconnect_max_failure_seconds = 0.1
    return _attach(a, clock)


async def entry31(clock):
    """test_backoff_breaker.py:86 test_persistent_reopen_failure_trips_breaker_loud_with_forensic_tail"""
    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    factory = ScriptedConnectionFactory([socket1] + [REOPEN_FAILURE] * 20)
    a = _breaker_adapter(factory, clock)
    return await _drive(a, 30, CircuitBreakerTripped, "CircuitBreakerTripped")


async def entry32(clock):
    """test_gap_recording.py:195 test_terminal_venue_disconnect_breaker_gap_recorded"""
    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    factory = ScriptedConnectionFactory(
        [{"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"}] + [REOPEN_FAILURE] * 20)
    a = _breaker_adapter(factory, clock)
    return await _drive(a, 30, CircuitBreakerTripped, "CircuitBreakerTripped")


async def entry34(clock):
    """test_reconnect_to_effect.py:99 test_stranded_reconnect_flag_fails_loudly"""
    class _StrandingAdapter(KrakenV2BookAdapter):
        async def _perform_reconnect(self, websocket):
            return websocket                  # BUG SIMULATION, exactly as the test does

    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    factory = ScriptedConnectionFactory([socket1])
    a = _StrandingAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=factory.connect)
    a._persistence_optional = True
    _attach(a, clock)
    return await _drive(a, 30, RuntimeError, "RECONNECT_FLAG_STRANDED")


async def _drive(adapter, duration, exc_type, label):
    t0 = time.monotonic()
    reached, detail = False, None
    try:
        async for _ in adapter.get_live_market_data(duration_seconds=duration):
            pass
        detail = "ran to completion (DEADLINE ended it) — terminator NOT reached"
    except exc_type as e:
        reached, detail = True, f"{label}: {str(e)[:50]}"
    except Exception as e:                                    # noqa: BLE001
        detail = f"UNEXPECTED {type(e).__name__}: {str(e)[:50]}"
    return {"terminator_reached": reached, "elapsed_s": round(time.monotonic() - t0, 4),
            "detail": detail, "deadline_s": duration}


async def entry33(clock):
    """test_live_capture.py:232 test_breaker_trip_terminates_run_with_forensic_tail (via the RUNNER)."""
    from trading.loop.live_capture import LiveCaptureRunner
    from tests.integration.test_live_capture import _paper_loop

    unexpected = ConnectionClosedError(Close(1011, "internal error"), None)
    conn = ScriptedConnectionFactory(
        [{"frames": [SNAPSHOT_FRAME, unexpected], "on_drain": "block"}] + [REOPEN_FAILURE] * 20)
    a = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE, connect_fn=conn.connect)
    a._reconnect_sleep = None
    a._reconnect_max_failure_seconds = 0.1
    _attach(a, clock)
    tmp = Path(tempfile.mkdtemp(prefix="wo033_e33_"))
    runner = LiveCaptureRunner(persist_path=tmp / "g.jsonl", duration_seconds=30,
                               trading_env="paper", adapter=a, loop=_paper_loop())
    t0 = time.monotonic()
    result = await runner.run()          # must NOT raise — the runner surfaces the trip
    term = result.get("terminated")
    return {"terminator_reached": term is not None,
            "elapsed_s": round(time.monotonic() - t0, 4),
            "detail": (f"runner surfaced {term['reason_code']}" if term
                       else "runner returned with terminated=None (DEADLINE ended it)"),
            "deadline_s": 30}


RATIO = [(31, "test_persistent_reopen_failure_trips_breaker_loud_with_forensic_tail", entry31),
         (32, "test_terminal_venue_disconnect_breaker_gap_recorded", entry32),
         (33, "test_breaker_trip_terminates_run_with_forensic_tail", entry33),
         (34, "test_stranded_reconnect_flag_fails_loudly", entry34)]
STRUCTURAL = [(36, "test_connection_failure_raises_and_does_not_replay_fixtures", entry36),
              (37, "test_live_method_refuses_fixture_mode_adapter", entry37)]


def main():
    # The runner's host-baseline preflight, through the same structural seam the suite uses.
    from trading.loop import host_baseline
    from tests.integration.conftest import SYNTHETIC_BASELINE_RECORD
    tmp = Path(tempfile.mkdtemp(prefix="wo033_"))
    store = tmp / "synthetic_baselines.json"
    key = host_baseline.fingerprint_key(host_baseline.host_fingerprint())
    store.write_text(json.dumps({key: SYNTHETIC_BASELINE_RECORD}, indent=1), encoding="utf-8")
    os.environ["MEAN_CYCLE_BASELINE_STORE"] = str(store)

    out = ["WO-033 — BOUND MEASUREMENT PASS: the 6 remaining audit BOUNDS, measured.",
           "D40: bound-versus-race is a measurement, not a margin argument.",
           "Entry 35 is settled (flipped by WO-031 §3-bis) and is NOT touched here.", ""]
    verdicts = {}

    # ── §3.A ────────────────────────────────────────────────────────────────
    out += ["=" * 78,
            "§3.A ZERO-CONSULTATION PROBE — entries 36, 37",
            "=" * 78,
            "A coherent COUNTING clock is injected through the `monotonic_clock` seam (no src edit).",
            "The three deadline sites, pinned by WO-031 §3-bis:",
            "    :2548 deadline set   |   :2594 deadline guard   |   :2727 recv timeout",
            f"For reference, `_connect()` is awaited at {ADAPTER_SRC}:2529 — BEFORE the deadline is",
            "set at :2548. Any test terminating during connect therefore cannot reach a deadline read.",
            ""]
    for num, name, fn in STRUCTURAL:
        clk = CountingClock(delta=0.0)       # frozen: observe, do not perturb
        res = asyncio.run(fn(clk))
        genuine = clk.count == 0
        verdicts[num] = "BOUND-measured" if genuine else "RACE-flipped"
        out += [f"-- ENTRY {num} · {name} --",
                f"     terminator                        {res['terminator']}",
                f"     MarketStates emitted              {res['emitted']}",
                f"     deadline-clock consultations      {clk.count}",
                f"     consultation sites (line: count)  {clk.sites or 'none'}",
                f"     VERDICT                           {verdicts[num]}"
                + ("  — the structural claim is OBSERVED: the deadline clock is never read"
                   if genuine else "  — 'never consulted' is FALSE; D39 classification required"),
                ""]

    # ── §3.B ────────────────────────────────────────────────────────────────
    out += ["=" * 78,
            "§3.B RATIO / FRAMES-REACHED PROBE — entries 31, 32, 33, 34",
            "=" * 78,
            "Real clock first: the ACTUAL elapsed time to the terminator, which replaces the audit's",
            "prose '~300x' with a number. Then AdvancingClock across a delta spread.",
            ""]
    for num, name, fn in RATIO:
        out.append(f"-- ENTRY {num} · {name} --")
        real = asyncio.run(fn(None))
        margin = (real["deadline_s"] / real["elapsed_s"]) if real["elapsed_s"] else float("inf")
        out += [f"     REAL CLOCK: terminator_reached={real['terminator_reached']}  "
                f"elapsed={real['elapsed_s']}s  deadline={real['deadline_s']}s",
                f"       {real['detail']}",
                f"       MEASURED MARGIN = deadline / elapsed = {margin:,.0f}x",
                "",
                f"       {'delta':>8} | {'terminator reached':>19} | {'elapsed_s':>9} | detail"]
        flipped_at = []
        for d in DELTAS:
            r = asyncio.run(fn(CountingClock(delta=d)))
            if not r["terminator_reached"]:
                flipped_at.append(d)
            out.append(f"       {d:>8} | {str(r['terminator_reached']):>19} | "
                       f"{r['elapsed_s']:>9} | {r['detail'][:52]}")
        genuine = not flipped_at
        verdicts[num] = "BOUND-measured" if genuine else f"deadline wins at delta={flipped_at}"
        out += ["",
                f"     VERDICT  {verdicts[num]}",
                ""]

    out += ["=" * 78, "§3.C AGGREGATE", "=" * 78]
    for num in (31, 32, 33, 34, 36, 37):
        out.append(f"  entry {num}: {verdicts[num]}")
    flips = [n for n, v in verdicts.items() if v.startswith("RACE")]
    out += ["",
            f"  flips (structural claim falsified): {flips or 'none'}",
            "  NOTE: a delta at which the deadline wins is reported above as a MEASUREMENT, not",
            "  automatically as a flip — see the report's stated reading of §3.B's verdict rule.",
            ""]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
