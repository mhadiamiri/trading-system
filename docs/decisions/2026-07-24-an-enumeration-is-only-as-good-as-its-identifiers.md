# Decision Log: an enumeration is only as good as its identifiers (WO-025)

**Date:** 2026-07-24
**WO:** WO-025 — ledger closeout + marker-based exclusion (ruled by D35)
**Authority:** D34-3 (declared, never inferred); the record-keeping failure-mode family
**Related:** [[a-check-is-bounded-by-the-form-it-matches]], [[incidental-coverage-is-not-coverage]],
[[an-environment-is-strict-along-axes]], the WO-023 §1 audit, WO-024 pass one §1 seam finding

---

## The entry (ratified verbatim)

> An enumeration is only as good as its identifiers. The WO-023 §1 audit's list was correct and
> complete; its entry for race #5 recorded a TRUNCATED test name, so a full-name grep returned
> nothing and the absence of a match was read as absence of the race. Standing consequence: a
> name-match against an enumerated list must match on the list's OWN identifier form (file+line,
> or a normalized/substring match), and a negative identifier-match is NOT a finding until the
> identifier form has been verified.
>
> Specimen: site 29, `test_runner_resolves_live_adapter_from_data_source_via_factory` — missed by
> full-name grep, found by file+line (test_live_capture.py:190, audit-era 197).
>
> The general rule underneath: **the strongest identifier is the one closest to the artifact —
> position beats name, marker beats position, content-hash beats marker.**

---

## The family it completes

This entry completes a family of three failure modes of the project's OWN record-keeping — the
records the project keeps about itself, each of which has now failed once and been ruled:

1. **Incomplete denominators** — *an audit without a denominator audits what it noticed*: a sample
   read as a census (the WO-022 flake was one instance of a 30-race class; the WO-023 §1 audit built
   the denominator that made the class visible).
2. **Uncited recall** — *a fact re-asserted from memory is a new claim, not a citation*: a figure
   restated without re-reading its source is not evidence of the source.
3. **Unfaithful identifiers** — *an enumeration is only as good as its identifiers* (this entry): a
   correct list whose entries are matched on the wrong identifier form yields a false negative that
   reads as a clean result.

---

**What was done under this doctrine (WO-025).** The gate ledger's by-name exclusion — a name copied
between documents, exactly the truncation-prone identifier this entry warns against — was replaced
with an on-the-test `@pytest.mark.gate_refusal_expected` marker (an identifier that cannot truncate in
transit), asserted bidirectionally (an unmarkered refusal fails; a stale marker fails). The audit's
race #5 (`test_runner_resolves_…_via_factory`) was resolved by file+line match, not full-name grep,
which is how it was found at all.
