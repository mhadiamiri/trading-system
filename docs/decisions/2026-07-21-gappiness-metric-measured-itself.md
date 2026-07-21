# The gappiness metric measured itself (WO-016 §4.3)

**Date:** 2026-07-21 · **Context:** WO-008b-B-RERUN lag-sampler VOID gate · **Author:** project lead

> "The instrument-gappiness VOID gate computed `expected = span/interval`, which assumes
> instantaneous sampler cycles. Real cycles cost ~108.89ms against a 100ms nominal, so a
> HEALTHY, CONTINUOUSLY-SAMPLING instrument showed a systematic ~8.9% deficit — within 2
> points of a VOID it had not earned. The metric was not measuring starvation; it was
> measuring its own loop overhead. Third instance of the family: the VOID run measured a
> stub rather than the feed; this measured cycle cost rather than instrument health. A
> measurement's denominator is part of what it measures, and `expected` derived from an
> idealized model of the measuring apparatus will report the apparatus, not the subject.
> Also on record: Ops's own diagnosis of this defect was wrong about the mechanism and was
> corrected by the executor against data — the adversarial loop running upward."

**Consequence:** the VOID metric is under re-ruling (WO-016 §3); a proposed recorded-gaps
composition with all three rule-0.1j components is on record for the lead's decision.
