# Decision Log: A Malformed import-linter Config Silently Evaluates Zero Contracts

**Date**: 2026-07-19
**Status**: REMEDIATED (guard landed in WO-010b)
**Related WO**: WO-010b, §8 entry 4

## Statement

A malformed import-linter config silently evaluates **zero contracts while appearing
configured**. Fifth instance of the instrument-reporting-green-while-checking-nothing
class. Remedy: contract-count assertion.

## How it was found

While adding the *"No test doubles in production code"* contract in WO-010 §4, the first
definition used:

```toml
forbidden_modules = ["unittest.mock"]
```

import-linter rejected it:

```
Invalid forbidden module unittest.mock: subpackages of external packages are not valid.
```

The critical property is not the rejection — it is the **blast radius**. That single
invalid entry aborted the entire run. **No contracts were evaluated at all**, not even
the four pre-existing ones. The tool exited without ever printing
`Contracts: N kept, M broken`.

Had it been committed unread, all six contracts would have been silently disabled while
`pyproject.toml` still looked fully configured.

## Why this is a distinct class from the stale tree

The stale-tree fault (see `2026-07-19-instrument-pointed-at-wrong-tree.md`) required an
environment error — a rebound editable install pointing at `%TEMP%`. **This one requires
nothing but a typo.**

And the WO-010 §2 path assertion **cannot catch it**: the path is correct. The package
resolves inside the repo exactly as it should. What is wrong is that the *count is zero*.
Proving you are running the right code does not prove the check ran.

Two assertions, one purpose:

| guard | question it answers |
|---|---|
| `tools/preflight_path_check.py` | is the instrument pointed at the right tree? |
| `tools/contract_count_check.py` | did the instrument actually run? |

## Remedy

`tools/contract_count_check.py`, wired into root `conftest.py` alongside the path
assertion. Both run in `pytest_sessionstart`, before collection, via `pytest.exit()` —
so neither can be caught, xfailed, or skipped. Both have standalone invocable forms.

The expected count is **pinned explicitly** as `EXPECTED_CONTRACT_COUNT = 6`. Adding or
removing a contract requires updating that constant in the same commit. Silent drift is
precisely the failure being prevented.

Broken contracts are deliberately **not** a failure for this guard; import-linter's
non-zero exit on broken contracts is ignored. It measures how many contracts *ran*, not
whether they passed. (One contract is intentionally red pending WO-008b-A.)

## Two failure branches, both proven

| branch | condition | proven |
|---|---|---|
| zero evaluated | malformed config, no summary line emitted | yes — artifact 2 |
| count mismatch | valid config, a contract silently dropped | yes — supplementary |

The second branch matters most: a dropped contract leaves a **valid** config still
reporting a healthy-looking `Contracts: N kept, 0 broken`. The zero-branch check alone
would not fire. The mismatch error names each contract actually seen, so the missing one
is identifiable at a glance.

## Evidence

`evidence/WO-010b/contract_count_assertion.txt` — four artifacts with durations, plus the
supplementary mismatch demonstration.
