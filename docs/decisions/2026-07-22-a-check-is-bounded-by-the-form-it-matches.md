# Decision Log: A check is bounded by the form it matches and the namespace it reads (WO-018)

**Date:** 2026-07-22
**WO:** WO-018 — Event-Type Governance + Closing the raised⇒declared Escape Hatch
**Authority:** Principle VIII (observability)
**Related:** [[instrument-competence]], the WO-013 §0 masking incident

---

> `reason_code` was governed while `event_type` sat entirely ungoverned beside it — and the
> ungoverned namespace is what masked WO-013's defect, because canonical codes read 'producible'
> via their `event_type` literals while the emitted `reason_code` said something else. An
> UNGOVERNED NAMESPACE ADJACENT TO A GOVERNED ONE IS WORSE THAN NO GOVERNANCE: it lets
> canonical-looking literals borrow the governed namespace's credibility. Separately, the
> completeness scan matched only colon-form literals, so `reason_code=` keyword emissions —
> including `EXEC_ORDER_FILLED`, the fill event and the atom of every post-trade audit — lived in
> the detection method's blind spot. Both are the same shape at different altitudes: A CHECK IS
> BOUNDED BY THE FORM IT MATCHES AND THE NAMESPACE IT READS, and everything outside those bounds is
> ungoverned regardless of how governed the system looks. Fixed before the corpus, because a
> decision log speaking a half-governed vocabulary is a defect that would have been ARCHIVED rather
> than merely present.

---

**What was done.** The denominator was stated first (`evidence/WO-018/namespace_enumeration.txt`) and
found the hatch wider than the headline: not 2 but **12** emitted-but-undeclared reason codes (the 5
`FEED_*` and 5 `RISK_*` also lived in the `reason_code=` keyword blind spot). All 12 declared; the
`event_type` namespace declared as `VALID_EVENT_TYPES`; the scan extended to both keyword forms and
both namespaces; the four properties enforced across the **union** (raised⇒declared, declared⇒producible,
prefix-freedom across the union, scan-reads-emitted). Four bite proofs on the scan itself — including the
**cross-namespace prefix collision**, the exact mechanism by which the WO-013 defect hid.

**What was NOT done (SCOPE DISCIPLINE — governance, not redesign).** The `event_type`/`reason_code`
overlap (NO_SIGNAL in both; ORDER_FILLED vs EXEC_ORDER_FILLED; bare PASS/CLAMP/VETO as reason codes;
the feed casing split) is reported (`evidence/WO-018/overlap_finding.txt`) as a **taxonomy finding for a
ruling** — nothing was merged, renamed, or restructured. The RiskDecision enum is the single source of
truth for the risk `event_type` values, guarded mechanically against drift (the declaration cannot
import `risk`, so a test enforces the equality).
