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

---

**DECLARED LIMIT — the variable-indirection residual (WO-018 follow-up B).** The §1 enumeration was a
one-time semantic pass; the completeness scan is the ONGOING guard, and it matches LITERAL forms only.
Stated in the HOST_SUSPEND / active-probe form — what is caught, what is not, what the uncaught case
looks like:

- **CAUGHT:** every reason_code / event_type emitted as a string LITERAL at the call site
  (`"CODE:"`, `reason_code="CODE"`, `event_type="CODE"`).
- **NOT CAUGHT:** an emission through VARIABLE INDIRECTION whose value is not a literal at the call site
  — `reason_code=<var>`, `reason_code=self.SOME_CONST`, `reason_code=e.reason_code`,
  `event_type=decision.value`. The scan does not statically resolve the variable to its string.
- **What the uncaught case looks like:** a future emission adds `reason_code=new_var` where `new_var`
  holds an UNDECLARED string. `raised⇒declared` reads only literals, so it never sees `new_var`, and the
  code ships as a **governed system emitting an ungoverned code** — the colon-form blind spot one level
  in. (Symmetric half, reported in follow-up A: `declared⇒producible` is satisfied for a declared code by
  its CONSTANT DEFINITION, or even a COMMENT/DOCSTRING mention, not only by a genuine emit — 13 declared
  reason codes and 3 event_types currently pass with no emit-site literal at all. The successor WO's
  tightened *reachable-as-emitted* scan closes that half; not fixed here.)
- **What covers the gap today, and what does not:** the one-time §1 pass resolved the current indirected
  values and DECLARED them; the enum-drift guard `test_event_type_risk_values_match_enum` pins ONLY the
  RiskDecision event_types emitted as `event_type=decision.value`. NEITHER covers a NEW indirection
  introduced after this pass — that is the standing residual, load-bearing until the tightened scan lands.

---

**DOCTRINE LINE — prose-as-use, ruled independent (WO-018 follow-up, 2026-07-22).** Verbatim:

> "PROSE MAY ANNOTATE EVIDENCE, NEVER CONSTITUTE IT. Written for evidence files as rule 0.6a, it now
> applies to static scans and eventually to anything that greps. The vocabulary scan accepted a
> DEFINITION as production, and beneath that accepted a COMMENT as production: delete the definition,
> keep the comment, three codes still pass. That is a step below the self-asserting string-literal test
> of WO-008b-A1, which at least lived in a test file — this is DOCUMENTATION LOAD-BEARING INSIDE A
> MECHANICAL PROPERTY."

**NEW STANDING RULE 0.1k (recorded in `docs/standing-rules.md`).** A BEHAVIORAL PROOF IS SOVEREIGN OVER A
STATIC SCAN — if the tightened scan flags a code with a passing behavioral proof, the scan is wrong, not
the code. Evidence-competence hierarchy: **BEHAVIORAL DEMONSTRATION > STATIC REACHABILITY > DEFINITION >
PROSE.** This is why the dead/live split (`evidence/WO-018/dead_live_split.txt`) resolves the 11
live-but-invisible codes by INLINE ANNOTATION citing their behavioral proofs rather than by building a
third static-scan iteration to chase constant/enum/variable indirection: a third iteration would
subordinate the sovereign evidence class (behavioral) to the inferior one (static reachability), inverting
0.1k. The pattern the lead named — *each audit of the instrument finds it committing a subtler version of
the crime it polices* — ends when liveness is settled by demonstration, not by making the scan ever
cleverer at reading source.
