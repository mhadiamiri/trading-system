# Decision Log: a verdict inherits its instrument's coverage (WO-023 §2b)

**Date:** 2026-07-23
**WO:** WO-023 §2b — gate correctness + verdict correction
**Authority:** D31 (honest below-floor ledger entries); the WO-008b-B throughput ruling (VOID, not
PASS, when the instrument measures the wrong path); Principle VIII (observability)
**Related:** [[instrument-competence]], [[a-check-is-bounded-by-the-form-it-matches]],
[[a-guard-can-audit-the-object-model]], the §7 hot-path re-baseline standing rule

---

## The entry

> "The WO-023 foundation's §7 re-baseline recorded the prediction (BELOW FLOOR), then noted honestly
> that the instrument replays `process_raw_frame` + `LiveTradingLoop` and is STRUCTURALLY BLIND to
> `get_live_market_data`'s while-loop where the changed line lives — and then labelled the outcome
> CONFIRMED. That label is wrong, and its wrongness is independent of the number's honesty and of
> whether the prediction is ultimately right. AN INSTRUMENT THAT DOES NOT EXECUTE THE CHANGED LINE
> CANNOT CONFIRM A PREDICTION ABOUT IT. The +0.196 ms delta is a real measurement — of a DIFFERENT
> code path. A VERDICT INHERITS ITS INSTRUMENT'S COVERAGE: measured on an unaffected path, it is NOT
> COVERED / VOID, not CONFIRMED.
>
> This is the SECOND instance of the same error. The first was WO-008b-B: sixty minutes of honest
> throughput data measuring a `pass` stub, ruled VOID rather than PASS because a verdict must measure
> the real path. 'The prediction may still be right' and 'the measurement showed it' are DIFFERENT
> CLAIMS; a report may make only the one its instrument earns. The correct record is an
> instrument-coverage gap — recorded, not closed (no new instrument was built here): no instrument in
> the project currently observes the capture loop's per-iteration cost."

---

**What was done (tests/docs only for §2; §1 is the production gate).** The §7 verdict was corrected in
both the evidence file (`evidence/WO-023-FOUNDATION/hot_path_rebaseline.txt`) and the foundation
report's §7 by APPENDING the correction and PRESERVING the original mis-labelled text — the record of
a mis-labelled verdict is itself evidence (the same treatment as the `progress.md` dated correction).
The coverage gap is recorded as a standing fact: the mean-cycle instrument is a full-loop sleep-wake
lag detector over the replay path; the capture loop's per-iteration deadline check is not on that
path, and no fit instrument for it exists yet (a per-frame timer remains deferred post-corpus, D-item
F). The prediction (below floor) stands as a prediction, unconfirmed.
