# Decision Log: Discrimination Rests Entirely on Declared Instruments

**Date**: 2026-07-20
**Status**: RULED (WO-014c-1 Phase C.1)
**Related WO**: WO-014c-1 (lag sampler, pong observer, receive-latency); rules 0.1e, 0.1d
**Companions**: [2026-07-20-evidence-type-sovereignty.md], [2026-07-20-reconnect-never-worked-in-production.md]

## Statement (project lead, ruled)

> With `ping_timeout=None` the library pings but never closes, so the 1011-on-missed-pong
> signal is unobservable by construction: 'no 1011 recurrence' is equally consistent with
> fixing it and with silencing the reporter. We traded observability for stability, and the
> pre-ruled interpretation had been priced against the old observability. Discrimination now
> rests entirely on declared instruments. The structural point: **liveness detection has
> moved into the failure domain it is meant to detect** — a starved event loop starves the
> heartbeat detector too. Every in-process detector shares its process's domain; this is a
> limit to DECLARE, not a flaw to fix, and it is why the lag sampler must degrade visibly and
> why gappy-instruments-VOID is a ruled branch. Constitutionally, the library's
> close-on-missed-pong was a liveness judgment delegated to code we do not instrument; this
> project's arc has been repatriating judgments from places we cannot observe into places we
> can. Corollary: **gappy instruments can NOMINATE a hypothesis; only clean instruments can
> CONVICT one.**

## What the instruments are (WO-014c-1)

- **Lag sampler (PRIMARY)** — `_sample_event_loop_lag` + `LagSampleRecord`. Sleep-overrun on
  the shared `time.monotonic()` clock; SELF-REPORTS (`expected` vs `actual`, `missed`, gap
  timestamps), so its own silence under load is a positive signal, not "healthy because quiet."
- **Pong observer** — `_observe_protocol_pong` + `PongRecord`. Sanctioned `ws.ping()` (RFC 6455
  §5.5.2 control frame — the protocol layer, not the app ping). Four counters; GAPPY is failed
  SENDS only; an ABSENT pong is a SIGNAL (Branch 1/3), never gappiness.
- **Receive-to-process latency + message-rate completeness** — `ThroughputRecord`. Per-second
  latency and message counts; reports its own silent seconds so a nomination can state whether
  the message data at gap timestamps is trustworthy.

All three share `time.monotonic()` (§A.2) so the cross-record correlation the branches rest on
is sound. `INSTRUMENTS_GAPPY` is the declared VOID reason code (branch 5).

## The rule this ratifies

Rule 0.1d in a new form: an instrument that stops recording under load, and reports nothing,
is a false guarantee — silence reads as health. The visible-degradation record makes the
in-process detector's own domain-sharing limit operational rather than hidden. And the
nominate/convict corollary keeps a VOID run informative: a gappy record cannot convict a
hypothesis, but its gap timestamps — correlated on the shared clock — can nominate one for a
directed follow-up.

## Scope

WO-014c-1 builds and declares the instruments and thresholds; it does NOT interpret a run —
there is no run (NO VENUE CONNECTION). The five ruled branches and the cross-product live in
`evidence/WO-014c-1/thresholds_and_branches.txt`. Gap recording / schema / the 60-minute
re-run are later (014c-2/3 and the re-run).

## Evidence
- `evidence/WO-014c-1/thresholds_and_branches.txt` — thresholds + branch enumeration
- `evidence/WO-014c-1/lag_sampler.txt`, `pong_observer.txt`, `throughput.txt` — bite proofs
- `evidence/WO-014c-1/instrument_proposal.txt` — approved design + cited survey
