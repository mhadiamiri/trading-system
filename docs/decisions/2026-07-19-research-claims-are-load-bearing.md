# Decision Log: Research Artifacts Are Load-Bearing

**Date**: 2026-07-19
**Status**: STANDING CONSEQUENCE ADOPTED
**Related WO**: WO-009b §5

## Statement

A single false sentence in `research.md:23` — *"v2 provides sequence numbers for gap
detection"* — propagated into a spec requirement, a data model, a contract error class, a
task list, and a fixture, and from there into six work orders of "proven" claims. Research
artifacts are load-bearing: **an unverified factual claim about an external protocol is a
defect at the same severity as a code defect.**

**Standing consequence: protocol claims in research artifacts must cite vendor
documentation.**

## The propagation path

```
research.md:23  "v2 provides ... sequence numbers for gap detection"   ← FALSE
        │
        ├─> spec.md FR-018a          "MUST track sequence numbers"
        ├─> data-model.md            LocalBookState.last_sequence, QuoteUpdate.sequence
        ├─> data-adapter.yml         class SequenceGapError, SEQUENCE_GAP_RESNAPSHOT
        ├─> tasks.md                 T008, T011, T015, T018
        ├─> quickstart.md            Scenario 4: Sequence Gap → Resnapshot
        └─> test fixtures            synthetic monotonic `sequence` values
                    │
                    └─> six work orders of "sequence-gap detection proven"
```

Every artifact downstream was *internally consistent* with every other. The system was
coherent, tested, and green — about a protocol that does not exist.

## It was not one sentence

The WO-009b audit found the same research block also specified:

| research.md claim | reality |
|---|---|
| `wss://ws.kraken.com` | that is the **v1** endpoint; v2 is `wss://ws.kraken.com/v2` |
| `{"name":"book","subscription":{"depth":1}}` | **v1 framing**, and depth 1 is **illegal** (10/25/100/500/1000) |
| "Sequence numbers in message headers" | none are transmitted |
| docs link `docs.kraken.com/websockets/` | the **v1** documentation |

**Three of the five defects blocking the WO-008b-A rewrite trace directly to this block**
— the v1 endpoint, `BOOK_DEPTH = 1`, and the `sequence` field. The implementation was not
careless. It faithfully built what the research artifact specified.

## Why this is severity-equivalent to a code defect

A code defect fails visibly: a test breaks, a run errors. A false research claim fails
*invisibly* — it produces a coherent system built on a wrong premise, and every test that
should have caught it was itself derived from the same premise. Fixtures were written to
match the claim, so they could not contradict it.

This is the same structural failure as the stale-tree episode
(`2026-07-19-instrument-pointed-at-wrong-tree.md`): a measurement apparatus that agrees
with itself and never touches reality. There, the linter analysed the wrong tree. Here,
the tests validated against the wrong protocol. In both cases everything was green.

## Standing consequence — the rule

**Protocol claims in research artifacts must cite vendor documentation**, with the source
URL recorded inline at the point of claim. A protocol assertion without a citation is to
be treated as unverified and may not be built upon.

Applied retroactively in WO-009b: every corrected line in `research.md` now carries a
`docs.kraken.com` citation, and the false original is preserved by strike-through with an
ORIGIN NOTE rather than deleted.

## What could not be verified even now

Kraken publishes a checksum for the **snapshot** case only. No documented incremental
example exists, so independent verification of the incremental path is **not achievable
from documentation** — it becomes the job of first live contact in WO-008b-A. Recorded
plainly rather than closed with another self-generated value.

## Evidence

- `specs/002-quote-level-data/research.md` — corrections with ORIGIN NOTEs
- `evidence/WO-009b/blocking_defects.txt`
- `evidence/WO-009/ground_truth_sources.txt`
