"""
WO-014b-1 — _reconnect() PROVEN TO EFFECT through the production transport (rule 0.1i).

THE DEFECT ON RECORD. _reconnect() was `pass` from Phases 1-3 through WO-008b-A1b. The
FR-018 five-consecutive-checksum-failure recovery was certified — in Phases 1-3 and
re-certified in A1b — by proofs that CORRECTLY established the counter reaches five and
the escalation fires (`_reconnect.assert_called_once()`), and TERMINATED AT A CALL-SITE.
Asserting the call and proving the callee acts are different claims. WO-008b-B then ran
sixty minutes with a no-op reconnect: at five failures the code "reconnected" by doing
nothing and continued against a discarded book. Rule 0.1i exists because of this.

This proof drives FIVE REAL checksum failures through get_live_market_data() — the real
transport loop, not process_raw_frame() by hand — and asserts the OBSERVABLE END STATE:
a fresh connection is actually opened, and EMISSION RESUMES on the fresh snapshot it
delivers. It deliberately does NOT assert _reconnect was called; that assertion already
existed and certified nothing.

HONEST FIXTURE LIMIT. Simulated transport (tests/fixtures/fake_ws_transport.py) supplies
the fresh snapshot as Kraken would deliver it AFTER a reconnect+subscribe. The close/reopen
and the subscribe SEND are exercised here; only the isolated live re-run confirms Kraken
actually answers a fresh connection with a fresh snapshot.

NO NETWORK. websockets.connect is replaced wholesale; nothing here opens a socket.
"""

import copy

import pytest

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
from tests.fixtures.kraken_v2_raw_frames import SNAPSHOT_FRAME
from tests.fixtures.fake_ws_transport import ScriptedConnectionFactory
from unittest.mock import patch


def _bad_snapshot():
    """A structurally valid snapshot whose checksum can never match this ladder."""
    bad = copy.deepcopy(SNAPSHOT_FRAME)
    bad["data"][0]["checksum"] = 1
    return bad


@pytest.mark.asyncio
async def test_five_real_failures_reconnect_and_emission_resumes():
    """
    Five real checksum failures -> reconnect -> fresh subscription -> fresh snapshot
    -> checksum validates -> EMISSION RESUMES. Asserted on the end state (rule 0.1i).
    """
    adapter = KrakenV2BookAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)

    # Socket 1: a synchronized book (emits), then FIVE consecutive bad snapshots. Each
    # fails its checksum through the production path, driving consecutive_failures 1->5.
    # Incremental updates are refused while awaiting resync, so — exactly as production
    # accumulates them — the streak is carried on SNAPSHOTS (see A1's §5 semantics).
    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    # Socket 2: the connection the reconnect OPENS. One fresh, valid snapshot.
    socket2 = [SNAPSHOT_FRAME]
    factory = ScriptedConnectionFactory([socket1, socket2])

    # WO-014b-2: under keepalive a silent link no longer ENDS the capture (it would
    # reconnect); the capture ends at its deadline. A short window (well under the default
    # 5s ping / 10s absence) ends the run right after emission resumes, without a spurious
    # keepalive reconnect. The reconnect under test here is checksum-triggered.
    emitted = []
    with patch("websockets.connect", factory.connect):
        async for state in adapter.get_live_market_data(duration_seconds=0.1):
            emitted.append(state)

    # ---- OBSERVABLE END STATE (never "_reconnect was called") ----

    # (1) A reconnect actually HAPPENED: a second, fresh socket was opened and the
    #     failed one was closed. This is the effect WO-008b-B's `pass` never produced.
    assert factory.connect_count == 2, (
        "reconnect must close the failed socket and OPEN A FRESH ONE; "
        f"only {factory.connect_count} connection(s) were opened"
    )
    assert factory.sockets[0].closed is True, "the failed socket must be closed on reconnect"

    # (2) EMISSION RESUMED. Nothing on socket 1 could emit after the first snapshot (the
    #     five failures held the no-emission window open), so a second emitted state can
    #     ONLY be the post-reconnect fresh snapshot pricing again.
    assert len(emitted) == 2, (
        "emission must resume after reconnect: one state from the initial sync, one "
        f"from the post-reconnect fresh snapshot; got {len(emitted)}"
    )

    # (3) The recovery is genuinely complete, not merely attempted.
    assert adapter._awaiting_resync is False, "the no-emission window must be closed"
    assert adapter._local_book.consecutive_failures == 0, "the failure streak must be cleared"
    assert adapter._pending_reconnect is False, "the reconnect flag must have been consumed"

    # (4) The fresh socket carries a real subscription — the producer ran on it.
    assert [m.get("method") for m in factory.sockets[1].sent] == ["unsubscribe", "subscribe"], (
        f"the reopened socket must be resubscribed; sent={factory.sockets[1].sent}"
    )


@pytest.mark.asyncio
async def test_stranded_reconnect_flag_fails_loudly():
    """
    WO-014b-1 WATCHDOG (note 3). A reconnect that is REQUESTED but not EFFECTED is
    silent non-action — the WO-008b-B defect class in a new costume. The transport
    raises RECONNECT_FLAG_STRANDED rather than press on against a discarded book.

    REGRESSION SIMULATION, stated plainly (rule 0.1d): with correct plumbing no input
    sequence can strand the flag — the transport services it in the SAME iteration it
    is set. To exercise the guard we simulate a servicing regression: a _perform_reconnect
    that returns without consuming the flag. This is the same counterfactual technique
    WO-008b-A1b used (temporarily restoring counter-wiping) to prove a guard load-bearing.
    """
    class _StrandingAdapter(KrakenV2BookAdapter):
        async def _perform_reconnect(self, websocket):
            # BUG SIMULATION: a "reconnect" that neither reopens nor clears the flag.
            return websocket

    adapter = _StrandingAdapter(mode=KrakenV2BookAdapter.MODE_LIVE)
    adapter._persistence_optional = True  # WO-014c-3 C: fixture opt-out (no live persistence)
    socket1 = [SNAPSHOT_FRAME] + [_bad_snapshot() for _ in range(5)]
    factory = ScriptedConnectionFactory([socket1])

    with patch("websockets.connect", factory.connect):
        with pytest.raises(RuntimeError, match="RECONNECT_FLAG_STRANDED"):
            async for _ in adapter.get_live_market_data(duration_seconds=30):
                pass
