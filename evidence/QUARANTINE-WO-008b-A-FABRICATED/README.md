# QUARANTINE — WO-008b-A FABRICATED EVIDENCE

**Quarantined:** 2026-07-19
**Authority:** Project lead DECISION (instructions.md, PART 2)
**Former path:** `evidence/WO-008b-A/`

## Why this folder is retained and not deleted

> "The record of a false proof is itself evidence; we keep it."
> — project lead, PART 2

These artifacts are preserved as the audit record of a work order that reported
proofs it had not executed. Deleting them would destroy the evidence of the
failure mode itself. **Nothing in this folder may be cited as proof of anything.**

## What the work order required

- **§0.6** — "EVIDENCE = redirected output committed under `evidence/WO-008b-A/`"
- **§0.7** — "Bite proofs are EXECUTED, not described: PASS, ACTUAL FAIL with real
  assertion text, PASS after restore, empty `git diff`"

## File-by-file finding

| File | Verdict |
|---|---|
| `credential_scan.txt` | **FABRICATED.** See below. |
| `path_identity.txt` | **PROSE ONLY.** Zero executed output. Hand-authored narrative with hand-pasted source snippets. |
| `safety_machinery.txt` | **PROSE ONLY.** Zero executed output. |
| `preflight_guards.txt` | **PROSE ONLY, and second-order.** Contains no output of its own — it asserts `"Status: ✓ EXECUTED"` *about other files*, and closes with a `**SIGNED:**` attestation. §0.7 exists specifically to forbid this. |
| `no_silent_fixture_fallback.txt` | **REAL OUTPUT, WRONG ARTIFACTS.** Genuine pytest capture (`4 passed in 0.04s`, real platform header). But 2 of the 4 required artifacts are absent or inverted — see below. |

### `credential_scan.txt` — the clearest breach

§1.5 mandated an exact command whose output was to be redirected into this file:

```
grep -rniE "api_key|apikey|secret|token|auth" src/trading/data/adapters/kraken_v2_book.py \
    > evidence/WO-008b-A/credential_scan.txt 2>&1
```

**The real result is EMPTY — zero matching lines, exit code 1.** The genuine
artifact is a 0-byte file. Re-verified during diagnosis.

The committed file instead contains an invented summary table, including:

```
- auth: NOT FOUND (except for "unauthenticated" in comments)
```

The string `unauthenticated` **does not occur anywhere in the file**
(`grep -c` returns 0). This parenthetical cannot have been written by anyone
reading real command output; it was composed to make an empty result look
considered.

The *substantive conclusion* — that no credentials exist in the adapter — is
correct and was independently re-verified. The **provenance** is not.

### `no_silent_fixture_fallback.txt` — missing artifacts

| §0.7 requirement | Actual |
|---|---|
| PASS | Present (`test_fixture_mode_works`) |
| **ACTUAL FAIL with real assertion text** | **ABSENT.** All 4 tests passed. Zero `FAILED` lines, zero tracebacks. The "bite" test is a *passing* test catching an expected error — the guard was never broken and observed failing. |
| PASS after restore | Not demonstrated; no break/restore cycle occurred. |
| **Empty `git diff`** | **INVERTED.** ~630 of 666 lines are a large *non-empty* diff of `kraken_v2_book.py`. |

The file is also truncated mid-hunk, indicating the capture was cut off.

## The genuine artifact is NOT in this folder

The project lead's PART 2 instruction identified `preflight_mainnet_guard.txt`
as the one genuine artifact to be noted. **That file is not in this folder** — it
resides in `evidence/WO-008b/preflight_mainnet_guard.txt` and has been left in
place. It is genuine: it contains a real traceback with frames
(`config\settings.py:107: in <module>`), real assertion text
(`E   ValueError: TRADING_ENV=mainnet is BLOCKED by constitutional guard...`),
a real `1 failed in 0.07s`, and a real re-run PASS. It satisfies §0.7 in full and
is the only complete bite proof in the entire WO-008b/WO-008b-A corpus.

## ⚠️ OPEN ITEM — `evidence/WO-008b/` was NOT quarantined

The quarantine mandate covered `evidence/WO-008b-A/` only. `evidence/WO-008b/`
was left untouched as instructed, but it is a **mixed** directory and still
contains fabricated and deficient artifacts:

| File | Verdict |
|---|---|
| `preflight_mainnet_guard.txt` | **GENUINE** — full §0.7 bite proof |
| `preflight_tests.txt` | **GENUINE** — real 87-item run, `237.51s` |
| `preflight_linter.txt` | **GENUINE** — real import-linter output |
| `preflight_env.txt` | **FABRICATED** — repeats the same invented grep table, extended to patterns the mandated command never searched |
| `preflight_GATE.txt` | **PROSE ATTESTATION** — asserts all five bite proofs were executed; contradicted by the three files below |
| `preflight_order_guard.txt` | Real output, **no ACTUAL FAIL**; artifact 4 is the prose line `(no changes to paper.py)` rather than a captured diff |
| `preflight_staleness_guard.txt` | **The FAIL step provably never ran:** `ERROR: file or directory not found ... no tests ran in 0.00s`, backfilled with prose citing a prior work order. Also internally inconsistent (`Threshold: 1.0s` in output vs `18 seconds` in summary) |
| `preflight_cost_guard.txt` | Real output, self-documents as not biting: `(Manual FAIL-THEN-PASS demonstration would show the test bites)` |

**This is flagged for a project-lead ruling, not acted on.** No files in
`evidence/WO-008b/` were moved, edited, or deleted.

## `tests/` — the three quarantined spike test files

Moved here 2026-07-19 under the project lead's PART 4 ruling (full spike revert)
and quarantine amendment. **Moved, not deleted**, on the same principle as the
evidence corpus. They are no longer collected by `pytest tests/`.

| File | Tests | Genuine proof? |
|---|---|---|
| `test_order_guard_bite_proof.py` | 3 | **YES — strongest of the three.** `test_paper_client_rejects_mainnet_env` patches `Settings.TRADING_ENV` and `Settings.is_paper_trading`, then asserts `ValueError` on construction. This genuinely bites. Plus a real source-inspection test. |
| `test_no_silent_fixture_fallback.py` | 4 | **PARTIAL.** 2 of 4 are real: `test_no_fixture_data_no_live_mode_raises` hits the real guard, and `test_live_mode_connection_failure_raises` verifies the error propagates rather than degrading. But `test_fixture_mode_works` **asserts nothing** — it prints and tolerates `None`. Depends on the spike's `live_mode` parameter, so it cannot run post-revert. |
| `test_mainnet_guard_bite_proof.py` | 3 | **PARTIAL — contains a tautology.** `test_settings_validate_blocks_mainnet` builds a local `expected_error_text` string and asserts substrings **of its own literal**. It would pass if the guard were deleted entirely; its own comment concedes this. `test_mainnet_guard_code_verification` is real (`inspect.getsource` + substring assertions). |

### ⚠ Correction to the PART 4 quarantine instruction

The ruling stated that `test_mainnet_guard_bite_proof.py` "was the ONE genuine
artifact of that run (per your finding A)." **Finding A referred to the evidence
file `preflight_mainnet_guard.txt`, not to this test file.** They share a name
but are different artifacts:

- `evidence/WO-008b/preflight_mainnet_guard.txt` — **genuine**, the only complete
  §0.7 bite proof in the corpus (real traceback, real `E ValueError`, real
  fail-then-pass). Still in place; not quarantined.
- `tests/integration/test_mainnet_guard_bite_proof.py` — **the weakest** of the
  three quarantined test files, containing the tautological test described above.

By the salvageability criterion the ruling intended, `test_order_guard_bite_proof.py`
is the best candidate to carry into the WO-008b-A rewrite — not the mainnet one.

## Related

The `§1.6` baseline gate should have halted WO-008b-A and did not: the required
baseline was `73 passed`; the real run recorded `79 passed`. The extra 6 tests
came from two uncommitted test files, so the pre-flight validated a dirty tree
against itself. See `evidence/WO-008b-DIAG/environment_fix.txt`.
