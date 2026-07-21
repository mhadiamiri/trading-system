# A declared constant is only as portable as the thing it was measured on (WO-016 D28 §E)

**Date:** 2026-07-21 · **Context:** WO-016 §B mean-cycle drift baseline · **Author:** project lead

> "A DECLARED CONSTANT IS ONLY AS PORTABLE AS THE THING IT WAS MEASURED ON. The drift baseline
> is host-scoped the way the ~116 disconnects/24h figure was keepalive-scoped and the 18s
> staleness bound was cadence-scoped. Third instance of the shape. Consequence: EVERY DECLARED
> FIGURE STATES ITS SCOPE OF VALIDITY ALONGSIDE ITS DERIVATION — a number that outlives its
> context becomes a quiet lie with a citation. Corollary found while implementing this: scope
> includes LOAD as well as host, since a baseline measured idle would convict every loaded run."

**Implemented (WO-016 §D28):** the mean-cycle drift baseline is now a per-host, fingerprinted
record (`config/mean_cycle_baselines.json`, machine id **hashed**); the live-capture runner REFUSES
to start on a host with no matching baseline (`MEAN_CYCLE_BASELINE_HOST_MISMATCH`, bite-proved); and
the establishment protocol (`tools/establish_mean_cycle_baseline.py`) measures a host's baseline
under REPRESENTATIVE LOAD (~1,959 msg/min replay), because the load corollary makes an idle-loop
baseline convict every real run. Any change of host — or of load regime — is a 0.4 re-declaration.
