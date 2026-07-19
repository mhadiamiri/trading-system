WO-008b-A1 ACCEPTED. Three follow-ups before A2 opens. Small, mostly analysis.

=== 1. THE FABRICATED-MARKET-DATA PLACEHOLDER — evidence contamination check ===
You reported: "get_market_data now raises without fixture_data instead of
fabricating a synthetic book. The old placeholder invented market data."

Production code that manufactures fake market data when given none is the most
dangerous defect found in this project, given its premise. Determine whether it
ever executed:
  - When was the fabricating placeholder introduced? Paste git log/blame.
  - Could ANY prior run have entered that path — i.e. called get_market_data
    without fixture_data? Check every call site across history, and any evidence
    run that invoked the adapter without explicit fixtures.
  - If YES for any prior evidence run, name it. That evidence is contaminated and
    must be quarantined per rule 0.6d.
  - If NO, state what proves it — an unreachable path is a latent hazard, not a
    contamination event, and the distinction matters.
Evidence -> evidence/WO-008b-A1b/fabricated_data_reachability.txt

=== 2. THE 5-FAILURE THRESHOLD — was Phases 1-3's claim true when made? ===
Your Finding 1 is ambiguous on one point and I need it precise. You wrote both
"pre-existing in shape but masked" and "FR-018's threshold was unreachable by
construction." Those imply different histories:
  (a) Reachable BEFORE the ordering fix (failure didn't discard the book, so the
      counter survived), and the fix would have broken it -> Phases 1-3's
      "5-consecutive-failure recovery fires" claim was TRUE when made, and you
      caught a fix-induced regression. Good outcome.
  (b) Unreachable all along -> another "proven" claim was false, same class as
      the sequence fiction, and it goes in the decision log with the others.
Answer (a) or (b), with the code path that proves it. Do not smooth this over —
which one it is determines whether another proof in the record needs annotating.
Evidence -> evidence/WO-008b-A1b/threshold_reachability_history.txt

=== 3. TEST ORDER DEPENDENCE — make it mechanical ===
Your Finding 2 (tests passing in isolation, failing in suite, patching a stale
Settings object) is rule 0.1d in a new costume: a proof that never touched the
mechanism. Order-dependence hides exactly that class, so stop relying on noticing
it.
  - Add randomized test ordering (pytest-randomly or equivalent) so order
    dependence surfaces mechanically rather than by luck.
  - Run the suite AT LEAST 3 TIMES with different seeds. Paste each run's summary
    line with duration and seed.
  - Report EVERY test that behaves differently under reordering. Do NOT fix them
    yet unless the fix is trivial and obvious — enumerate first; a cluster would
    be its own work order.
  - If randomization proves impractical (the 237s runtime is already long), say
    so and propose an alternative rather than skipping it.
Evidence -> evidence/WO-008b-A1b/order_dependence_scan.txt

ALSO: log the F811 story in the decision log — a patch script anchored on
"def pause", matched LocalBookData.pause, and duplicated the entire adapter class;
the rule added in WO-009 §4 for a defect already reverted away caught it within
one work order of being added. That is the build-enforced-over-vigilance argument
paying off at the smallest possible scale, and it belongs in the record.

Track as open cleanup (do NOT churn now, rule 0.1a): vestigial sequence
parameters on LocalBookData.

NOT IN SCOPE: no WebSocket, no network. STOP for review.