# Decision Log: The Instrument Was Pointed at the Wrong Tree

**Date**: 2026-07-19
**Status**: REMEDIATED (guard landed in WO-010 §2)
**Related WO**: WO-010 §8 entry 2

## What happened

For six work orders, `import-linter` analysed a **stale copy of the repository** at
`C:\Users\mhadi\AppData\Local\Temp\ci-sim2`, pinned at commit `400a28b` — not the
working tree under review.

**Cause:** a WO-008a-R3 Ops instruction cloned the repo to a temp directory and ran
`pip install -e .` *inside the clone*, rebinding the editable install. `pytest` was
unaffected because `pytest.ini` sets `pythonpath = src`, which prepends the real tree.
So tests ran the real code while the linter analysed stale code, and nothing surfaced
the divergence.

## Forensic confirmation

Dependency count is a fingerprint:

| source | files | deps | result |
|---|---|---|---|
| `evidence/WO-008b/preflight_linter.txt` (labelled 43ca600) | 54 | **171** | 4 kept, 0 broken |
| real tree at 400a28b (WO-010 §6) | 54 | **171** | 4 kept, 0 broken |
| real tree at 43ca600 (WO-010 §6) | 54 | **176** | 3 kept, 1 broken |

`171` is `400a28b`'s fingerprint. It appears in evidence labelled `43ca600`. This is
direct confirmation, not inference.

## The recurring class

This is the **fourth costume of one trap: prove you are running the code you think
you are.**

1. Stale module invocation (`python -m trading.loop.live` executing a temp tree)
2. CI building an unknown commit
3. The editable-install rebind to `%TEMP%\ci-sim2`
4. import-linter analysing a different repository

Each was diagnosed separately as a one-off. They are one failure mode.

## Remedy — kill the class, not the costume

WO-010 §2: a **preflight path assertion** that hard-fails if the resolved `trading`
package is not inside the repository working tree.

- `tools/preflight_path_check.py` — standalone, invocable, exit 1 on failure
- `conftest.py` at repo root — `pytest_sessionstart` hook; aborts the session via
  `pytest.exit()` before collection, so it cannot be caught, xfailed, or skipped
- On failure the error names the resolved path and the expected repo root, and
  detects the stale-temp-install signature specifically

Bite proof executed: `evidence/WO-010/preflight_path_assertion_bite_proof.txt`.

## Known gap

The standalone form is **not yet wired into `.github/workflows/ci.yml`**, because
WO-010 OUT OF SCOPE states "Do NOT fix CI. Capture only." Wiring it into CI is
recommended as a follow-up so the guard runs before the import-linter step there too.

## Evidence

- `evidence/WO-010/environment_proof.txt`
- `evidence/WO-010/preflight_path_assertion_bite_proof.txt`
- `evidence/WO-008b-DIAG/environment_fix.txt`
