# WO-012 decision log

Two entries.

---

## 1. Guard surfaces attract 0.1d instances

The mainnet guard (`Settings.validate`) and the paper-execution boundary
(`PaperExecutionClient.__init__`) drew **two independent generations** of false
certification: the self-asserting string literal replaced in WO-008b-A1, and then
the four `test_live_loop.py` source greps removed in WO-012. The pattern is not
coincidence: proving *"the system refuses Y"* behaviorally is harder than proving
*"the system does X"*, because you must drive the system into the forbidden state
and watch it refuse. The mechanism is legible, so implementers reach for
`inspect.getsource` precisely where it is least acceptable — a textual check of a
behavioral claim, the worst quadrant.

Standing consequence: **rule 0.1f** (source inspection may SUPPLEMENT a behavioral
guarantee, never CONSTITUTE one), and **one behavioral bite proof per guard
surface** — the guard driven into the forbidden state and watched to fail, under
randomized ordering. A present-but-dead guard (strings intact, effect removed) —
which a grep cannot see — must make the behavioral test fail. WO-012 §3 demonstrates
exactly that for the mainnet, paper-execution, and cost surfaces.

---

## 2. An audit without a denominator audits what it noticed

Third instance of this defect class:
1. the reason-code vocabulary check that examined the DECLARED list only, while the
   real collision lived in production raise strings (WO-011 §5);
2. the RULING 8 enumeration that asked "would this test BREAK under the refactor?"
   instead of "is this test VALID?" — two different questions;
3. this audit, which had to extract the COMPLETE guard-surface list from the
   constitution and specs BEFORE classifying any test, so coverage is measured
   against the full set rather than against what happened to be noticed.

Standing consequence: **audits state their denominator first.** WO-012 §1 produced
`guard_surface_denominator.txt` before touching a single test, and the closure count
is reported as "N of M, here are the M−N and why" — including the one genuinely
uncovered surface (kill-switch-preserves-cancellations), named rather than hidden by
a padded total.

---

## 3. A denominator's SHAPE can be a blind spot, not only its length (WO-012b)

"A denominator's SHAPE can be a blind spot, not only its length. WO-012's
guard-surface enumeration asked for claims of the form 'the system refuses X' and
therefore could not see 'even when X, the system must still permit Y.' S13
(kill-switch preserves cancellations) went uncovered for that reason. Standing
consequence: guard-surface enumerations cover BOTH REFUSALS AND PRESERVATIONS. The
failure mode of a preservation guarantee is over-blocking, which for kill-switch
semantics means being unable to cancel resting orders during the exact emergency the
switch exists for."

Third instance of "an audit without a denominator audits what it noticed" — and the
first about the denominator's SHAPE rather than its completeness. S13 is closed in
WO-012b with a paired behavioral test (blocking AND preservation certified together)
and an over-blocking bite proof; the preservation-guarantee re-sweep found no other
runtime preservation guarantee (FR-023/024/025 "MUST remain unchanged" are
interface-stability constraints, not runtime "still permit Y when X" guarantees).

**Appended (WO-012c):** "Every refusal-shaped guarantee should be checked for an
embedded dual: what must still work when this guard fires?" WO-012b's phrase-sweep
found one dual (S12/S13); WO-012c read the 12 refusal surfaces for SHAPE and found
five more (S4, S5, S6, S7, S10), each certified with a paired test and an
over-blocking bite proof.

---

## 4. Textual matching cannot FIND a behavioral claim any more than it can certify one (WO-012c)

"WO-012b's preservation sweep searched for phrasings and found one; reading the
constitution for shape found more. Textual matching cannot certify a behavioral
claim (rule 0.1f) and cannot reliably FIND one either — the sweep missed duals for
the same reason the greps it replaced missed behavior. Standing consequence:
enumerations state which method found each hit, and semantic reading is the primary
method where the property is behavioral."

---

## 5. A bite proof's defeat mechanism can itself be fragile (WO-012c)

"A bite proof's defeat mechanism can itself be fragile. A monkeypatch target was
missed under sys.modules churn, making the defeat order-dependent and the proof
unreliable in one direction. Standing consequence: defeat mechanisms are structural
(dependency injection) rather than patch-based wherever possible."

Concretely: WO-012's `test_zero_cost_path_is_detectable_behaviorally` monkeypatched
`trading.execution.paper.compute_execution_costs` and passed deterministically but
failed under seed 20260721 (the patch missed the module the runner actually used).
WO-012b refactored it to dependency injection. WO-012c's over-blocking bite proofs
use structural file perturbation (sha256-restored), never a monkeypatch.
