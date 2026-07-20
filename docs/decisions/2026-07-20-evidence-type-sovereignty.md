# Decision Log: Evidence-Type Sovereignty — Observed vs Documented

**Date**: 2026-07-20
**Status**: RULED (WO-014b-2 §3 / §4.2, deferred from the WO-014b split)
**Related WO**: WO-014b-2 §1 (keepalive); rule 0.1e
**Companion**: [2026-07-20-reconnect-never-worked-in-production.md] (§4.1, the other split entry)

## Statement (project lead, ruled)

> Observed behavior and documented behavior are different evidence types, and each has
> claims only it can support. The captured hour is SOVEREIGN FOR WHAT HAPPENED — it
> falsified our checksum-ordering assumption in A2 when documentation alone had not. The
> documentation is SOVEREIGN FOR WHAT THE PROTOCOL IS — layer structure, offered
> mechanisms, negative existence claims. `research.md:23` was the failure of citing
> nothing; WO-014 nearly failed by citing the WRONG EVIDENCE TYPE: a real capture,
> honestly taken, structurally incapable of showing that two same-named mechanisms exist
> at different layers. Had the design proceeded on the observed hour alone, it would have
> shipped a keepalive satisfying the wrong layer; the re-run would have reproduced the
> 1011; and — the compounding part — the starvation discrimination would have been
> corrupted, because a disconnect recurring 'despite keepalive' would have falsely
> retired the protocol hypothesis and aimed the investigation at starvation that wasn't
> there. The instrumentation armed to distinguish two hypotheses would have been
> discriminating between a true one and a strawman. Rule 0.1e therefore enforces not only
> that claims are sourced, but that they are sourced from EVIDENCE COMPETENT TO SUPPORT
> THEM. Economics, for the third time inside the work order that adopted the rule: the
> fetch cost minutes; the wrong keepalive would have cost a 60-minute live run, a
> contaminated discrimination, and a follow-up chasing a phantom.

## Why this entry sits with the keepalive work

WO-014b-2 §1 is exactly the design the statement warns about. The captured hour showed
Kraken's heartbeat at ~1/s and showed our resync never fired — sovereign facts about
what happened. But "Kraken's ping is an APPLICATION-level mechanism, distinct from the
WS PROTOCOL-level ping that threw the 1011" is a claim about *protocol layer structure*,
which no capture can establish — only the documentation can. The keepalive built this
slice reflects the distinction in code:

- §1.1 heartbeat-absence and §1.2 application ping/pong are the **application-layer**
  keepalive the observed hour and the docs jointly support.
- §1.3 — deliberate, cited `ping_interval`/`ping_timeout` on the library's **protocol**
  ping, and a bite proof that exercises that layer — is held as the checkpoint seam
  precisely because it is the layer the 1011 lived at, and a weakened proof of it would
  corrupt WO-014c's starvation discrimination (the strawman the statement describes).

## The rule this ratifies

Rule 0.1e is not "cite something." It is "cite from evidence COMPETENT TO SUPPORT THE
CLAIM." Observation is sovereign for what happened; documentation for what the protocol
is. This slice applied the rule twice more:

- The keepalive layer distinction was taken from documentation, not the capture.
- The backoff/breaker figures could NOT be taken from documentation — Kraken's WS
  connection-rate limits are DOCUMENTED SILENCE (evidence/WO-014b-2/rate_limits_research.txt)
  — so they are declared engineering judgment, not dressed as a citation.

## This slice does NOT resolve the 1011

Stated for the record: the application keepalive proven here is necessary but not
sufficient. The 1011 was a protocol-level timeout; both hypotheses (missing pong vs
event-loop starvation) remain open. WO-014c builds the discriminating instruments and
the live re-run rules it.

## Evidence
- `evidence/WO-014b-2/keepalive_1_1_1_2.txt` — §1.1/§1.2 bite proofs
- `evidence/WO-014b-2/backoff_breaker.txt` — §2 bite proofs
- `evidence/WO-014b-2/rate_limits_research.txt` — documented-silence finding
- `evidence/WO-014/lifecycle_proposal.txt` — the verbatim Kraken doc quotes (RULING 1)
