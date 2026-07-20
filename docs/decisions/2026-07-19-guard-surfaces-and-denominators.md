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
