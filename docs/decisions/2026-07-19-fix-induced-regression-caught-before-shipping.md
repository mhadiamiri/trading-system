# Decision Log: Fix-Induced Regression Caught Before Shipping

**Date**: 2026-07-19
**Status**: CAUGHT AND CORRECTED WITHIN WO-008b-A1
**Related WO**: WO-008b-A2 §1.2 entry 2

## Statement (project lead, pre-ruled)

> Ordering fix would have silently disabled the 5-failure threshold via
> `reset_for_resync` zeroing the counter inside the discard. Fix-induced regression caught
> before shipping — the rationale for converting order-dependence and interaction detection
> from observation to mechanism.

## What happened

WO-008b-A1 §1 moved checksum validation *after* the update is applied, per amended
FR-018a(b), and added `_enter_resync()` on failure — which discards the book.

`_discard_book()` calls `reset_for_resync()`, which zeroed `consecutive_failures`.

So the corrected failure path did this:

```
failure → record_failure() → counter = 1
        → _enter_resync() → _discard_book() → reset_for_resync() → counter = 0
```

**The recovery path wiped the very counter that gates it.** FR-018's "5 consecutive
failures trigger reconnection" would have become unreachable by construction — rule 0.1d,
a false guarantee — and it would have been introduced *by a fix*, in the same commit that
corrected a real defect.

## This was a regression, not a pre-existing lie

WO-008b-A1b settled the history, because the distinction determines whether other records
need annotating:

- **Before the ordering fix**, the failure branch did **not** discard the book, so
  `reset_for_resync()` never ran on a checksum failure and the counter accumulated
  normally. The threshold was genuinely reachable.
- **Proven by execution**, not inference: the historical test was run in a detached
  worktree at `HEAD~1` and **passes**, asserting both directions (5 → reconnect, 4 → not).

So Phases 1-3's "5-consecutive-failure recovery fires" claim was **true when made**. No
historical annotation required. The defect existed only in the window between the ordering
fix and the counter fix — both inside one unshipped work order.

The counterfactual was demonstrated rather than argued: reinstating the wipe on top of the
new ordering kills the threshold with `assert 0 == 1`.

## The lesson — why this changes practice

Three defects in three consecutive work orders shared one shape: **a mechanism that
appeared to work while touching nothing.**

| defect | how it hid |
|---|---|
| tautological guard test | asserted its own string literal |
| stale-`Settings` patch | passed in isolation, failed only under a particular test order |
| this counter wipe | would have passed every existing test, because the test that covered it was being rewritten in the same commit |

Each was caught by **noticing** — reading output carefully, running the full suite before
committing, following an ambiguity instead of smoothing it. Noticing does not scale and
does not survive a tired reviewer.

**The conversion to mechanism:**

- `ruff F811` — duplicate definitions. Caught a 900-line class duplication within one work
  order of being added.
- `tools/preflight_path_check.py` — is the instrument pointed at the right tree?
- `tools/contract_count_check.py` — did the instrument actually run? Caught its own first
  invalid config.
- **`pytest-randomly`** — order dependence, now declared as a dev dependency (WO-008b-A2
  §1.3) and required in A2's preflight. Deliberately *not* in `addopts`: default and CI
  runs stay deterministic; randomization is invoked explicitly.

Order dependence is the specific case that motivated the last of these, but the general
rule is the point: **if a defect can only be caught by someone paying attention, it will
eventually ship.** Encode it, or accept that it is a matter of time.

## Evidence

- `evidence/WO-008b-A1b/threshold_reachability_history.txt`
- `evidence/WO-008b-A1b/order_dependence_scan.txt`
- `evidence/WO-008b-A2/threshold_bite_proof.txt`
