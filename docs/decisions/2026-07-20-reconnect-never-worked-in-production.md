# Decision Log: The 5-Failure Recovery Never Worked in Production

**Date**: 2026-07-20
**Status**: FIXED in WO-014b-1 (`_reconnect()` implemented and proven to effect)
**Related WO**: WO-014b-1 §1, §4.1 — split from WO-014b at the §1/§2 seam
**Consequence**: rule 0.1i (a proof of escalation must terminate in an observable effect, not a call-site)

## Statement (project lead, ruled)

> The 5-consecutive-checksum-failure recovery — certified in Phases 1–3, re-certified in
> WO-008b-A1b with a proof that CORRECTLY established the counter reaches five and the
> escalation fires — HAS NEVER WORKED IN PRODUCTION, because the escalation calls a no-op.
> WO-008b-B ran sixty minutes with zero functioning recovery at either level: no snapshot
> request and no working reconnect. The only resync that ever occurred was the venue
> hanging up on us. The A1b proof was not sloppy — it was genuine, and it still certified
> nothing about recovery, because asserting the call and proving the callee acts are
> different claims. This is S10's producer/consumer lesson running in the other direction:
> there, the test fed the producer's output by hand; here, the test verified the producer
> fires and never followed the wire to the consumer. Consequence: rule 0.1i.

## What was actually on the code

`_reconnect()` was a three-line stub whose body was `pass`, from Phases 1-3 through
WO-008b-A1b. It was reached at `kraken_v2_book.py` from inside `_process_quote_update`, on
the branch `if consecutive_failures >= CHECKSUM_FAILURE_THRESHOLD`. So at the fifth
consecutive checksum failure the system "reconnected" by doing nothing, then continued
against a book it had just discarded.

The A1b artifact `threshold_reachability_history.txt` proved — genuinely, by executing the
historical test at `HEAD~1` — that the counter reaches five and `_reconnect.assert_called_once()`
fires. Every word of it is true. It is also silent on the only question that matters for
recovery: **does the callee do anything?** It could not answer that, because the test
replaced `_reconnect` with a `Mock()` and asserted the call. Asserting the call and proving
the callee acts are different claims.

## Relationship to the fix-induced-regression finding

The sibling entry `2026-07-19-fix-induced-regression-caught-before-shipping.md` correctly
concluded that the *threshold was reachable* and that Phases 1-3's "the escalation fires"
claim was true when made — and it remains true. This entry does not overturn that. It
sharpens the boundary the earlier phrasing ("recovery fires") left soft: **the escalation
fired; recovery never happened.** Reaching the counter and calling `_reconnect` was proven;
`_reconnect` doing something was neither proven nor, until now, true.

## The fix (WO-014b-1)

`_reconnect()` now sets `_pending_reconnect`, mirroring the committed `_request_snapshot`
flag pattern (design B). The transport loop (`get_live_market_data`) consumes it: it closes
the socket, reopens via `_connect()`, and hands off to the committed Phase 2.1 producer
`_maybe_resubscribe` for the fresh subscription. A stranded (set-but-unconsumed) flag fails
loudly with reason code `RECONNECT_FLAG_STRANDED` — the same defect class must not reappear
in a new costume.

The proof drives five REAL checksum failures through `get_live_market_data` and asserts the
**observable end state**: a fresh connection is opened, the failed socket is closed, and
**emission resumes** on the fresh snapshot. It does not assert `_reconnect` was called. With
the fix reverted to `pass`, that proof fails at `assert connect_count == 2` — the no-op is
caught, which the call-site assertion never could.

## Scope honesty

Simulated transport. The close/reopen and the subscribe SEND are exercised at fixture level;
only the isolated live re-run confirms Kraken answers a fresh connection with a fresh
snapshot. This slice does NOT address the 1011 keepalive disconnect — that is WO-014b-2,
and the two 1011 hypotheses remain unresolved (WO-014c's instruments discriminate them).

## Evidence

- `evidence/WO-014b/reconnect_to_effect.txt` — four-artifact bite proof, sha256 exact-restore
- `tests/integration/test_reconnect_to_effect.py` — effect-terminating proof + watchdog
- `tests/fixtures/fake_ws_transport.py` — reusable close/reopen transport harness
- `evidence/WO-008b-A1b/threshold_reachability_history.txt` — the annotated call-site certification
