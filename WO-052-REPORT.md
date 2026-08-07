# WO-052 — Ruling 2 (git witness), 4a (every fee site), 4b (websockets)

**SHIP IMPACT: YES** — `backtest/costs.py` cost defaults changed. Full discipline.

> ## ⛔ §1 STOP — **THE GIT WITNESS DOES NOT EXIST.** Ruling 2 cannot be closed as written.
>
> `/captures/` is **gitignored by deliberate policy**. **Zero corpus files are tracked, in any
> commit, in all of history.** There are no blobs and no trees to compare, so the ruling's remedy
> is unexecutable — not failed, *unexecutable*.
>
> **I did NOT record the ruled provenance line**, because half of it asserts something false. See
> §1.4 for what I recorded instead and what needs your ruling.
>
> **A correction is owed on WO-051**, in §1.5.

---

## §1 THE GIT WITNESS

### §1.1 What the WO asked for, and what git actually holds

| Query | Result |
|---|---|
| `git log --oneline -- captures/corpus_24h/corpus_20260805/` | **empty** |
| `git log --all --oneline -- captures/` | **0 commits, in all history** |
| `git ls-files captures/corpus_24h/corpus_20260805/` | **0 files tracked** |
| `git cat-file -p HEAD^{tree}` | `captures/` **absent from the tree** |
| `git log --all --diff-filter=D -- captures/` | **empty** → never tracked, never removed |
| `git check-ignore -v captures/corpus_24h/corpus_20260805/` | **`.gitignore:63: /captures/`** |

There is no WO-045-era commit to compare against HEAD, because **no commit has ever contained a
corpus file.** Blob-hash equality — which the WO correctly identified as the real proof — has no
operands.

### §1.2 This is not a defect. The ignore is deliberate and correct.

`.gitignore` states the reason at the site (WO-042 §2.3): capture data carries a 90-day minimum
retention and "belongs on disk and in the archive, **never in git history where it could not later
be removed**." The same comment notes the directory was previously untracked *and un-ignored*, so a
plain `git add -A` would have committed the whole corpus wholesale.

**That policy is right and I did not change it.** Ruling 2's remedy was premised on the corpus being
in git. It never was.

### §1.3 The witness that does exist — and it is stronger

The capture wrote its own witness. `CORPUS_MANIFEST.json` records for each of the **38 segments** a
`sha256` with **`hashed_at_capture: true`**, computed by `trading.data.corpus.sha256_file` — plain
streamed SHA-256 over file bytes — **at the moment each segment was closed**.

Verified by the new `tools/corpus_verify.py`:

```
corpus              : captures/corpus_24h/corpus_20260805
segments in manifest: 38
  verified OK       : 38
  MISMATCHED        : 0
  MISSING on disk   : 0
  hashed_at_capture=true : 38 / 38

VERDICT: PASS — every segment matches the SHA-256 recorded when it was captured
```

**This satisfies the standing rule this same WO mints** (§2): the figure is computed by code
committed in the tree it certifies. It is better than the git log the ruling asked for, twice over:

- **per-segment** — a failure names the corrupted file, where a directory digest reports only that
  *something* moved;
- **it dates from capture** — it covers each byte from the moment it was written, an interval no
  later-computed digest can reach back to. A git log would only have witnessed from whenever the
  corpus was first committed, which is never.

**Its honest limit:** it does not prove the *manifest* is unaltered. Someone who rewrote a segment
**and** its manifest entry would pass. Every self-describing artifact has this property. I am
reporting it rather than letting a PASS imply more than it earns.

### §1.4 ⚠ The provenance line — recorded with a correction, needs your ruling

The WO asked me to record, verbatim:

> historical label unverifiable; **interval integrity witnessed by git**; v1 canonical.

**I did not record that.** The middle clause is false, and recording a false witness in a provenance
record is the exact failure this WO exists to stamp out. What I recorded instead, in the decision doc:

> historical label unverifiable; **interval integrity witnessed by the capture-time per-segment
> SHA-256 in CORPUS_MANIFEST.json (38/38 verified, `hashed_at_capture=true`), not by git — git has
> never tracked the corpus**; v1 canonical.

A second reason not to write it verbatim into the corpus: **§1 says "record in the corpus's
provenance", but the corpus is the ratified read-only artifact.** Editing `CORPUS_MANIFEST.json`
would both violate the standing never-write rule and change the v1 digest `e3ab1aec…` that §5
requires to be unchanged. The instruction is self-conflicting at that point. I recorded the line in
`docs/decisions/` instead and left the corpus byte-untouched. **Your ruling needed on both choices.**

### §1.5 ⚠ CORRECTION TO WO-051

WO-051's report cited, as corroboration that the corpus was untouched:

> `git status --porcelain` on the corpus | empty at open and close

**That was not evidence.** An ignored path *always* reports clean — the command could not have
produced non-empty output. I presented a query that cannot fail as though it had passed a test.

The invariance claim itself still holds, on better grounds: the v1 digest `e3ab1aec…` is identical
across WO-051 and WO-052, and now 38/38 capture-time hashes verify. But the *git* half of that
sentence should be struck, and I have recorded it as a specimen in the decision doc:

> **An empty result from a query that cannot fail is not evidence.**

It is the same defect the WO existed to fix, committed by the WO that was fixing it.

---

## §2 THE STANDING RULE — committed

`docs/decisions/2026-08-07-an-integrity-figure-is-computed-by-committed-code.md`, D51 ruling 2,
minted with the doctrine block verbatim as specified, plus the §1 corollary above and the
apply-guidance.

---

## §3 4a — EVERY FEE DEFAULT ROUTED, GUARD EXTENDED

### §3.1 THE FULL ENUMERATION (§0.11 — enumerated, not assumed)

**The count is not two.** Scanning `src/`, `tools/`, `tests/`, `config/`, `specs/`, `.env.example`
and every `*.toml/yaml/json/ini`:

#### Code — production defaults in `src/`

| # | Site | Before | Disposition |
|---|---|---|---|
| 1 | `execution/paper.py:74` `DEFAULT_FEE_RATE_PCT` | `fee_schedule.taker_pct()` = 0.80% | **routed** (WO-051) |
| 2 | `execution/paper.py:76` `DEFAULT_SLIPPAGE_FACTOR` | `0.0001` | **deliberately independent** — measured vs corpus, not venue-published |
| 3 | `backtest/costs.py:79` `DEFAULT_FEE_RATE_PCT` | **`0.1`  (uncited, 8× low)** | **→ ROUTED (this WO)** |
| 4 | `backtest/costs.py:81` `DEFAULT_SLIPPAGE_FACTOR` | **`0.001`** | **→ FIXED to measured `0.0001`** |
| 5 | `execution/fee_schedule.py` `KRAKEN_SPOT_SCHEDULE` | Tier 1: 0.80 taker / 0.40 maker | **the source of truth** |

Sites 3 and 4 together *were* the WO-048 identical-channels coincidence: `0.1` percent and `0.001`
fraction are **the same 0.001 of notional**. Verified before the fix:

```
CostModel fee 0.1% -> 0.001 ; slippage 0.001 ; IDENTICAL CHANNELS: True
Paper     fee 0.80% -> 0.008; slippage 0.0001; IDENTICAL CHANNELS: False
```

#### Config — a dead knob

| # | Site | Value | Disposition |
|---|---|---|---|
| 6 | `.env.example:24` / `quickstart.md:55` `EXECUTION_FEE_RATE_PCT=0.1` | commented out | **⚠ IMPLEMENTED NOWHERE.** No code reads it. It configures nothing and only misinforms — advertising a rate now 8× low. Left in place (removing it is a doc change beyond scope) but **pinned by a test** so it cannot be silently wired up carrying its stale default. |

`config/settings.py` has **no** fee or slippage setting at all — confirmed, not assumed.

#### Specs / docs — declared 0.1%, now stale

| # | Site |
|---|---|
| 7 | `specs/001-walking-skeleton/spec.md:18, :99 (FR-017), :143` |
| 8 | `specs/001-walking-skeleton/quickstart.md:254` |
| 9 | `specs/001-walking-skeleton/research.md:119` |
| 10 | `specs/001-walking-skeleton/checklists/requirements.md:71` |

**Not edited — reported.** These are the frozen walking-skeleton specification; FR-017 says fees are
"configurable, default 0.1%". Rewriting a ratified spec is not in this WO's scope, and D47 says
annotate at the site rather than rewrite. **They are now wrong** and the lead should rule on whether
FR-017 is amended or the divergence is recorded as intentional.

#### Tests — explicit rates, deliberately independent

`tests/integration/test_cost_reconciliation.py` passes its own `FEE_RATE`/`SLIPPAGE` explicitly and
is insulated from the defaults by construction — that is the point of a reconciliation test.

### §3.2 / §3.3 The fix

`CostModel` now reads `DEFAULT_FEE_RATE_PCT = fee_schedule.taker_pct()` and
`DEFAULT_SLIPPAGE_FACTOR = Decimal("0.0001")`. The slippage figure is **reused, not re-derived**
(§3.3) — it is anchored to 50,000 corpus frames and already evidence-backed. Both defects are closed
by the same edit, with the full derivation recorded at the site.

### §3.4 The extended guard — `tests/test_fee_default_sites.py` (10 tests)

Not per-class. It **discovers** sites by AST-walking `src/` for `DEFAULT_FEE_RATE_PCT` /
`DEFAULT_SLIPPAGE_FACTOR` class assignments and reconciles them against a declared registry, so a
**new** unrouted fee default fails by name. AST rather than regex because both files carry long
comments that mention these constants.

Every site is routed **or** declared independent with its reason — no third state. The dual
(independent slippage) is still *pinned*: independent must not mean unchecked.

### Bite proof — `tools/wo052_fee_site_bite_proof.py`, **VERDICT: PASS**

| Artifact | Result |
|---|---|
| 1 — PRISTINE | rc 0, 34 passed |
| 2 — **BITE** (`CostModel` fee → bare `Decimal("0.1")`) | rc 1 — fails **naming `[CostModel]`**; `dual_failed []` |
| 3 — **NECESSITY** (same defect **+** registry narrowed to `PaperExecutionClient`) | rc 1 — **`bite_failed []` — the per-site guard goes SILENT**; completeness guard fires instead |
| 4 — RESTORED | rc 0, 34 passed |

```
backtest/costs.py               sha256 BEFORE/AFTER : bf3f8841f64dee164a98995852e05f9f85eee769cf88f4923556373ab3816fc6
tests/test_fee_default_sites.py sha256 BEFORE/AFTER : abe6ad7756a51de2e819547bdeb4f1fcdefd3f1aa1a164637410bc65583389bd
IDENTICAL: True
BITE bites      (guard names CostModel, dual preserved) : True
NECESSITY holds (narrowed guard blind, completeness fires) : True
```

**Artifact 3 is the measurement that matters.** With the defect present and the guard at its
pre-WO-052 scope, the per-site check reports nothing. *That silence is what a green build looked
like for two work orders while `CostModel` sat at an uncited 0.1%.* The completeness guard fires
instead — the second layer working, reported separately rather than counted as the bite.

**Honest note on the bite set:** only the *routed* half of the bite fired, not
`test_r4_channels_are_distinct_at_every_site[CostModel]`. The mutation reverts the fee alone, so
`0.001` vs `0.0001` remained distinct. The R4 half fires only when both channels revert. The proof
required `bite_failed` non-empty, which it is, and I am recording which member fired rather than
implying both did.

§0.4 **the dual is local and direct**: `dual_failed` is tracked in *all four* artifacts and is empty
in every one — including under the bite, where a guard that fired on everything would look identical
to one that fired on the right thing.

§0.10 exclusions recorded in the proof as `broad_failed`
(`test_the_two_cost_models_agree_at_their_defaults` and three arithmetic tests read both models at
once, so they attribute nothing).

### §3.5 Test churn — **the predicted count was also an assumption**

The WO expected "five test files carry expectations written against 0.1%." A full-tree scan found
**one file, three tests**, all in `tests/test_backtest_costs.py`:
`test_fees_applied_to_every_trade`, `test_fees_calculation_accuracy`,
`test_manual_calculation_matches_system`.

The five *files* construct `CostModel()` bare; only these three assert against the rate.

Each was fixed by **deriving the expectation from `CostModel.DEFAULT_FEE_RATE_PCT`** rather than
re-pinning a new literal, with the reason recorded at each site (D47). Re-pinning `0.80` would have
recreated exactly the uncited constant this WO removes, and would go stale the next time the
schedule changes. Each test's actual subject — that a hand-written formula reproduces the system —
is preserved exactly and is now independent of what the rates happen to be.

### §3.6 Arithmetic untouched ✅

`compute_execution_costs` not edited. `test_cost_reconciliation.py` — **4 passed**;
`test_r4_the_one_cost_implementation_is_unchanged` — passed.

---

## §4 4b — THE DOCUMENTED ACCEPTANCE PATH

### §4.1 Before / after

| | `pyproject.toml` `[project.dependencies]` | `requirements.txt` |
|---|---|---|
| **before** | pyarrow, pydantic, python-dotenv, pyyaml, httpx | …+ **`websockets>=12.0`** |
| **after** | …+ **`websockets>=12.0`** | unchanged |

Constraint matches `requirements.txt` exactly. Added to `[project.dependencies]`, not `[dev]` — it
is imported by `src/trading/data/adapters/`, so it is a runtime dependency.

### §4.2 Proof through the documented path alone

Fresh venv, **the documented command only, no `requirements.txt` fallback**:

```
$ uv venv .venv_doc_path --python 3.11
$ uv pip install --python .venv_doc_path/Scripts/python.exe -e ".[dev]"
 + websockets==17.0.1
 + trading-system==0.1.0 (from file:///C:/Projects/bot/trading-system)

$ python -m pytest --collect-only -q
======================== 457 tests collected in 0.35s =========================
```

**457 collected, zero errors** — against 13 collection errors before. The full acceptance run below
was executed **in this same venv**, so the documented path is exercised end-to-end, not just
installed.

### §4.3 Other missing runtime deps — enumerated (§0.11)

AST-walked every import in `src/`, `tests/`, `tools/`, `config/` and compared against `pyproject`:

| Module | Verdict |
|---|---|
| `websockets` | **WAS MISSING** — 13 files incl. `src/` → **added to `[project.dependencies]`** |
| `psutil` | **WAS MISSING** — declared only in `requirements-dev.txt`; used by `tools/live_corpus_capture.py` (WO-043 grant condition 1) and `tools/measure_real_loop_baseline.py` → **added to `[dev]`**. It fails *loudly* (`LOAD_SENSOR_UNAVAILABLE`) rather than at collection, which is why it hid longer. |
| `tomli` | **correctly absent** — a guarded `except ImportError` fallback for pre-3.11; the project requires ≥3.11 where `tomllib` is stdlib, so it is unreachable. Not a gap. |
| `pyarrow`, `pydantic`, `dotenv`, `pytest` | already declared |
| `tests`, `tools`, `fixtures` | local packages, not third-party |

---

## EVERY ATTEMPT

1. **§1 executed as instructed and returned nothing** — then confirmed *four independent ways*
   (`ls-files`, `log --all`, `HEAD^{tree}`, deletion-filter) that the emptiness meant "never
   tracked", not "unchanged". Not accepting the first empty result is the whole lesson of §1.5.
2. **Searched for the real witness** rather than reporting only a blocker — found the capture-time
   manifest hashes, verified 38/38, and committed the verifier.
3. **Declined to record the ruled provenance line verbatim** (§1.4) and flagged both reasons.
4. **Enumerated fee sites across six file types**, not just `src/*.py` — which is how the dead
   `EXECUTION_FEE_RATE_PCT` knob and the four stale spec declarations surfaced.
5. **Checked the WO's own predicted churn count** instead of trusting it: one file, three tests, not
   five files.
6. **Verified the identical-channels claim numerically before fixing it**, rather than trusting the
   WO's description.
7. **Ran the §4.2 proof in a venv built by the documented command alone**, then used that same venv
   for the 3.11 acceptance leg, so the fix is exercised rather than asserted.

---

## §5 ACCEPTANCE

- [ ] **Ruling 2 closed — NO. STOP reported (§1).** Git cannot witness the corpus; the remedy is
      unexecutable. A stronger witness (38/38 capture-time hashes) is supplied and verified, the
      provenance line is recorded with the false clause corrected, and **your ruling is needed.**
- [x] Standing-rule doc committed
- [x] Full fee-default enumeration reported — **10 sites across code, config and specs**; every
      production site routed or declared-independent with its reason
- [x] `CostModel` channels distinct, fee cited; **guard extended to all sites**; bite proof **PASS**
      with discriminating mutations and a local, direct dual
- [x] Documented path builds and collects from `pyproject.toml` alone (**457 collected, 0 errors**);
      other missing deps enumerated (`psutil` found and fixed; `tomli` correctly absent)
- [x] WO-011 reconciliation passes; corpus v1 digest `e3ab1aec…` **unchanged**, 88 files
- [x] Test count with arithmetic, both interpreters, both orders — below
- [x] lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31 · evidence clean

### Test count arithmetic

```
  445  baseline at HEAD 2c5b6cd (WO-051 close, CI 31224446780)
+  10  tests/test_fee_default_sites.py (new)
±   0  three tests in test_backtest_costs.py rewritten in place, not added or removed
─────
  455  expected  (+ 2 skipped = 457 collected)
```

| Leg | Order A (declaration) | Order B (seed 52052) |
|---|---|---|
| Python 3.14.6 | **455 passed, 2 skipped** (309.43s) | **455 passed, 2 skipped** (309.66s) |
| Python 3.11.15 (documented-path venv) | **455 passed, 2 skipped** (309.09s) | **455 passed, 2 skipped** (308.29s) |

The 3.11 legs ran in `.venv_doc_path` — the venv built by the documented command alone (§4.2) — so
the dependency fix is proven by the acceptance run itself. Venv removed afterwards.

### CI

_pending — filled in on the close commit_

---

## FILES

| File | Disposition |
|---|---|
| `docs/decisions/2026-08-07-an-integrity-figure-is-computed-by-committed-code.md` | **NEW** — D51 ruling 2 |
| `tools/corpus_verify.py` | **NEW** — verifies 38/38 capture-time hashes |
| `src/trading/backtest/costs.py` | **CHANGED** — fee routed, slippage fixed to measured 1 bp |
| `tests/test_fee_default_sites.py` | **NEW** — the extended, self-discovering guard (10 tests) |
| `tests/test_backtest_costs.py` | **CHANGED** — 3 tests derive rates instead of hard-coding |
| `tools/wo052_fee_site_bite_proof.py` | **NEW** — bite / dual / necessity, PASS |
| `pyproject.toml` | **CHANGED** — `websockets>=12.0` runtime, `psutil>=5.9.0` dev |
| `captures/corpus_24h/corpus_20260805/` | **READ-ONLY — untouched**, verified twice |
