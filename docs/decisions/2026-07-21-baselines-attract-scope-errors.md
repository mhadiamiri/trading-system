# Baselines attract scope errors (WO-016 D29 §D)

**Date:** 2026-07-21 · **Context:** WO-016 §D28/D29 mean-cycle baseline · **Author:** project lead

> "BASELINES ATTRACT SCOPE ERRORS THE WAY GUARD SURFACES ATTRACT 0.1d INSTANCES — because a
> baseline is nothing BUT scope: a number whose entire meaning is the conditions of its
> measurement. Second scope error in three exchanges from the same machinery (host scope
> missed, then load scope missed, the latter written into the ruling that fixed the former).
> Consequence: every baseline declaration enumerates its scope dimensions explicitly — host,
> load, source, duration — rather than declaring a value and leaving scope to inference."

**Implemented (WO-016 §D29):** the baseline record and the establishment protocol now enumerate
all four scope dimensions — HOST (fingerprint), LOAD (~1,959 msg/min, scoped "representative of
OBSERVED 60-MINUTE LOAD (WO-008b-B-RERUN)", with a numeric re-declaration trigger at ±20%), SOURCE
(the replay fixture is pinned by identity; the load run-id `WO-008b-B-RERUN-20260721T170944Z` is
named in the record), and DURATION (60 s, the duration actually validated). Nothing is left to
inference.

## The accretion dividend (third instance, recorded)
The SAME recorded hour (WO-008b-B-RERUN) that closed the small-quantity rendering defect and armed
the 200-capture regression fixture now also CALIBRATES INSTRUMENTS ON MACHINES IT NEVER RAN ON.
Design consequence worth stating: baseline establishment on a new host needs **NO VENUE CONNECTION
and NO SOCKET AUTHORIZATION** (it replays recorded frames through the production loop), which keeps
the socket boundary clean — per-run, venue-touching, the lead's to grant — and makes host
provisioning a pure Ops operation.
