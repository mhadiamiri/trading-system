WO-010 ACCEPTED. Excellent work, and the self-disclosures are the reason it is
accepted rather than audited further.

ONE ADDITION BEFORE WO-009 — close the class your §4 discovery opened.

Your finding: forbidden_modules = ["unittest.mock"] was rejected as invalid and
ABORTED THE ENTIRE LINT RUN, evaluating ZERO contracts while appearing
configured. That is the same meta-defect as the stale tree — the instrument
reports green while checking nothing — but it needs no environment error at all.
A typo in the config does it, and ruling 4's path assertion cannot catch it
because the path is correct and the COUNT is zero.

REQUIRED (small, build-enforced):
1. Add a check asserting the EXPECTED NUMBER of contracts was actually evaluated
   by import-linter. Hard-fail if the evaluated count is zero or does not match
   the expected count. Pin the expected count as an explicit, stated value.
2. Bite proof, four artifacts with durations: deliberately break the contract
   config (reintroduce an invalid form) -> PASTE THE ACTUAL FAILING OUTPUT
   showing the count assertion firing -> restore -> PASS -> empty git diff.
3. Place it alongside the §2 preflight path assertion so both run before
   contracts and tests. Two assertions, one purpose: prove the instrument is
   pointed at the thing AND that it actually ran.
   Evidence -> evidence/WO-010b/contract_count_assertion.txt

ALSO:
- Note in the decision log as a fourth entry: "A malformed import-linter config
  silently evaluates zero contracts while appearing configured. Fifth instance of
  the instrument-reporting-green-while-checking-nothing class. Remedy:
  contract-count assertion."
- RULE CORRECTION, my error: rule 0.6c's "empty pre-status" applies to the
  PREFLIGHT GATE before work begins, not to post-work verification. Your §9
  correction was right. The rule now reads that way.

NOT IN SCOPE: still no Mock removal, no CI fix, no spec amendment, no WebSocket.
Report and STOP.