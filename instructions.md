# WORK ORDER — WO-008b-A3: Fix Checksum Input Rendering; Sweep Substring Assertions; Re-run Smoke

**Status:** ACTIVE. Precedes WO-008b-B.
**Authority:** `.specify/memory/constitution.md` governs. Conflict → STOP and escalate.
**Baseline:** `ebdfcbd` — 119 collected, 111 passed, 8 xfailed, 0 failed, 0 xpassed.
import-linter 6/6, contract count 6/6, ruff clean.
**Standing rules 0.1–0.9 apply in full, unchanged.**

## CONTEXT
WO-008b-A2's smoke failed at criteria 2–4 and CONFIRMED the post-update ordering
fix against live data (1070/1070 post, 0/1070 pre, with negative control). Root
cause of the checksum mismatch is parse-layer rendering: `json.loads` floats
Kraken's numbers before project code runs, so `Decimal(str(5.1e-05))` yields
"0.000051" where Kraken rendered "0.00005100". Declining to fix it after seeing
the number was correct discipline and is why this is a separate work order.

## 1. FIX THE RENDERING AT THE PARSE BOUNDARY

### 1.1 Principle — preserve, do not re-render
The checksum must be computed over **the venue's transmitted representation**,
not over a numeric value we re-render to a format we assume.

Two candidates were named. They are NOT equivalent:
- `json.loads(..., parse_float=Decimal)` — preserves Kraken's exact digits,
  trailing zeros included. Venue-agnostic; carries no assumption.
- Fixed-point 8dp rendering — assumes Kraken always emits 8 decimal places. True
  for BTC/USD; an unverified assumption for other symbols and magnitudes, and
  under rule 0.1e an uncited assumption about venue behavior.

**Ops direction: use `parse_float=Decimal` (preserve) unless you find a concrete
reason it cannot work.** If you find one, STOP AND ASK rather than falling back to
the heuristic.

### 1.2 Also handle integers
A `qty` of `0` arrives as a JSON integer, not a float, so `parse_float` alone will
not cover it. Determine whether `parse_int` (or equivalent) is needed, and report
what Kraken actually sends for zero-quantity deletions — cite the captured frames,
which are now ground truth for exactly this question.

### 1.3 Prove it against BOTH ground truths
- Documented snapshot checksum `3310070434` (Kraken docs) — must still reproduce.
- Live snapshot checksum `3372482100` (captured A2 frames) — must now reproduce.
- All captured incremental frames — Kraken's own checksums must validate.
Paste all three. A fix that satisfies the live value but breaks the documented one
is not a fix.

### 1.4 Bite proof — four artifacts
Test asserting the checksum input preserves the venue's rendering. Reintroduce the
float round-trip → **PASTE THE ACTUAL FAILING OUTPUT** with real assertion text →
restore → PASS → empty diff.
Evidence → `evidence/WO-008b-A3/rendering_bite_proof.txt`

### 1.5 Close the 1071 vs 1070 discrepancy
A2 reports 1071 updates arrived but 1070 replayed. Account for the difference
exactly. If it is benign (e.g. the final frame was truncated at disconnect), say
so with the evidence. Do not leave a one-frame gap unexplained in checksum evidence.

## 2. SWEEP SUBSTRING ASSERTIONS — systemic 0.1d check

`test_no_market_state_guard` passes with its guard disabled because
`EXEC_NO_MARKET_STATE` is a substring of `EXEC_NO_MARKET_STATE_TIMESTAMP` raised by
an adjacent guard. The defect is not that one test — it is **substring matching in
assertions**, which cannot distinguish a code from its own prefix.

- Sweep the full test suite for assertions matching reason codes, error codes, or
  log messages by substring/`in`/`startswith` rather than equality.
- For EACH hit: can it pass when the mechanism it certifies is disabled? Report
  every instance and your determination.
- Convert to exact-match assertions where the answer is yes.
- **Prove the fix bites** for `test_no_market_state_guard` specifically: disable
  its guard → **PASTE THE ACTUAL FAILING OUTPUT** → restore → PASS → empty diff.
- Also check the reason-code vocabulary itself: are any codes prefixes of others?
  If so, that naming is a latent trap independent of any test. Report; do not
  rename without asking (rule 0.1a).
Evidence → `evidence/WO-008b-A3/substring_assertion_sweep.txt`

## 3. RE-RUN THE SMOKE TEST — 2 MINUTES

Full preflight gate first, including the randomized-order suite run with its seed.
Same five pass criteria, same pre-ruled failure interpretation:

**If checksums still fail, do NOT tune and do NOT retry to green.** Stop, capture
frames, diagnose offline. Report the failure.

Report checksums attempted / passed / failed explicitly, plus raw received,
MarketStates emitted, `venue_name`, staleness firings, reconnects.

**Retain this run's frames as an additional ground-truth fixture**, labeled with
its own UTC timestamp and run ID. Do not overwrite A2's — two independently
captured windows are stronger evidence than one.

## 4. VERIFY, COMMIT, PUSH
    pytest tests/ -rX
    import-linter lint
    python tools/contract_count_check.py
    ruff check .
Explain every test-count delta against `ebdfcbd`. Secret scan including captured
frames. Push, paste local vs remote HEAD.

## 5. FINAL REPORT — then STOP
1. Which rendering fix did you use, and why? Confirm no assumption about Kraken's
   decimal places was encoded.
2. Integers/`qty: 0` — what does Kraken actually send? Cite the captured frames.
3. Paste all three ground-truth reproductions: documented `3310070434`, live
   `3372482100`, and captured incrementals.
4. Rendering bite proof — four artifacts with durations.
5. **The 1071 vs 1070 discrepancy — accounted for exactly.**
6. Substring sweep — every hit, every determination, the conversions made, the
   `test_no_market_state_guard` bite proof, and whether any reason code is a
   prefix of another.
7. **Smoke results vs all five criteria**, numbers pasted. Checksums attempted /
   passed / failed.
8. Raw received, emitted, `venue_name`, staleness firings, reconnects. Label any
   rate a smoke observation.
9. New frames retained? Paste the fixture header. Confirm A2's were not overwritten.
10. Paste §4 verification with the delta explained.
11. **Did any credential appear in ANY output, log, evidence file, or captured
    frame?** YES/NO.
12. **Was any order placed at any venue?** YES/NO.
13. **Is any file in `evidence/WO-008b-A3/` prose standing in for output?** YES/NO.
14. **What did you change that you were not asked to change?** Every file, or "none."
15. **What could not be completed, and why?**

ADDENDUM TO WO-008b-A3 — three additions, ruled by the project lead.
WO-008b-A3 is APPROVED AS DRAFTED. Everything in it stands. These add to it.

=== A. FR-018a AMENDMENT — rides with this WO, no separate order ===
Add to FR-018a, as a principle rather than an implementation note. Ruled text:

  "Checksum input MUST derive from the venue's transmitted representation;
   re-rendering a parsed numeric value into an assumed format is prohibited as
   checksum input."

Reasoning to record with it: an 8dp re-rendering is an UNCITED ASSUMPTION ABOUT
VENUE BEHAVIOR — rule 0.1e applied to number formatting instead of protocol
fields. It holds for BTC/USD today and breaks silently on the first symbol or
price magnitude Kraken renders differently. "Breaks silently" here means every
checksum mismatches and the book never validates — we now know exactly what that
looks like, because we watched it for two minutes.

`parse_float=Decimal` is CONFIRMED as the ruled fix, with the STOP-and-ask
fallback exactly as §1.1 states. Run /speckit-analyze after amending and confirm
no sibling artifact contradicts the new clause.

=== B. PREFIX-FREEDOM IS NOW A NAMING RULE — pre-ruled, do not stall ===
§2 told you to report-not-rename on the reason-code vocabulary. Ruling in advance:

  NO REASON CODE MAY BE A PREFIX OF ANOTHER REASON CODE.

- Add a mechanical check: a test iterating the full reason-code vocabulary and
  asserting prefix-freedom. It goes in the suite so the rule outlives everyone's
  memory of why it exists.
- Rationale beyond the current bug: even with every assertion converted to
  exact-match, prefix-overlapping codes stay a latent trap for every future grep,
  log query, and dashboard filter. The VOCABULARY must be safe, not merely today's
  assertions against it.
- If the sweep finds EXEC_NO_MARKET_STATE / EXEC_NO_MARKET_STATE_TIMESTAMP is the
  ONLY collision, you may execute the rename under this ruling — with the standard
  grep-for-orphans completeness check afterward (every consumer, log parser, doc,
  and test updated; zero references to the old code remain).
- If there are MULTIPLE collisions, report them and STOP before renaming — a
  cluster is its own work order.
- Bite proof for the new check, four artifacts: introduce a deliberate prefix
  collision -> PASTE THE ACTUAL FAILING OUTPUT -> remove -> PASS -> empty diff.

=== C. REPORT ITEM 3 CARRIES ITS OWN DENOMINATOR ===
State the COUNT of captured incrementals validated, not just "incrementals
validate." Evidence should carry its denominator: "N of N captured incremental
checksums reproduced" — so the claim is auditable without opening the fixture.

=== D. DECISION LOG — two entries, verbatim where quoted ===
1. "Fixing after seeing the number and re-running to green is exactly how a wrong
   assumption survives contact." Recorded as the reason WO-008b-A2 declined to fix
   the rendering defect in the run that discovered it.
2. "The fixture was more correct than reality." kraken_v2_raw_frames.py warned
   that a float round-trip would corrupt the checksum and stored prices as strings
   for that reason; the production parse path was committing exactly that round
   trip. The fixture-fidelity work from WO-009 was paying before the socket opened.

=== E. STANDING PATTERN RATIFIED ===
Every live window captured is KEPT, LABELED, and IMMUTABLE. Ground truth accretes;
it is never replaced. A3's frames are an additional fixture alongside A2's, with
their own UTC timestamp and run ID.

Everything else in WO-008b-A3 proceeds as written. Do NOT run the 60-minute
capture. STOP for human review.





