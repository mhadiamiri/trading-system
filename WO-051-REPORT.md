# WO-051 — CITE THE FEE

**Result: the declared 0.26% was wrong by 3.08×.** Kraken's published Tier 1 spot taker rate is
**0.80%**. The rate is now cited, tier-aware, and pinned to its source by a test.

**SHIP IMPACT: YES** — cost-model defaults. Full discipline applied.
**WO-050 WAS NOT RECOMPUTED** (§0.1) — see the fence section below.

---

## §0.1 THE HARD FENCE — NO RECOMPUTATION WAS PERFORMED

**I did not compute what WO-050 would have been at 0.80%, and this report contains no such
figure.** WO-050's verdict of **−$2,223,991.19** stands exactly as computed, at the 0.26% that was
in force when it ran. Per D50, 0.8 does not distinguish between changing a strategy parameter and
changing a cost assumption once the number is on the table; correcting a citation is not a licence
to re-derive a published number. **The cited rate applies to FUTURE runs only.**

The delta reported in §2.4 is a delta between two *rates*. It is never applied to a *result*.

---

## §1 STATE CONFIRMED

| Check | Value |
|---|---|
| HEAD at open | `b9d9b45` — WO-050 §7 close |
| Baseline suite | **436 passed, 2 skipped** (3.14.6) — matches the WO's stated 436 |
| `git diff -- src/` | clean |
| lint-imports | 6 kept / 0 broken |
| contract count | PASS — 6 evaluated, 6 expected |
| ruff | All checks passed |
| annotation scan | **0** eager-annotation NameErrors |
| preflight | PASS — `trading` resolves inside the repo tree |
| `wo029_reverify_partition` | **PASS 31/31** |
| `git status --porcelain evidence/` | empty |

### Defaults as WO-050 left them

- `DEFAULT_FEE_RATE_PCT = Decimal("0.26")` — **DECLARED, not cited.** The code comment said so
  plainly: *"I did not verify a published schedule from here."*
- `DEFAULT_SLIPPAGE_FACTOR = Decimal("0.0001")` — 1 bp, **measured** against 50,000 frames of
  `corpus_20260805`. Already evidence-backed, explicitly out of scope, and **untouched**.

### ⚠ STOP (§0.5) — THE CORPUS DIGEST `a025db1e…` IS NOT REPRODUCIBLE

§1 asks me to snapshot the corpus at digest `a025db1e…`. **I could not, and no one can.**

That value is certified in five reports (WO-045 → WO-050), but the code that computed it was never
committed — it lived in throwaway scripts. The *scheme* is gone, so the number cannot be
regenerated from the corpus bytes. I tried **twenty** candidate schemes against the real 88 files
(content-only, path+digest under POSIX / Windows / absolute / four different path roots, several
text-manifest forms, sorted-hash forms, raw-byte concatenations). None reproduces it.

**This is the same defect this WO exists to fix, one level up.** A fee with no citable source and a
digest with no reproducible definition fail identically: a figure everyone repeats and nobody can
check. `a025db1e…` was never a verifiable claim about the corpus — it was a claim about a script
that no longer exists.

So I committed `tools/corpus_digest.py`, which **declares its scheme in code**:

```
v1: h = sha256(); for each file sorted by POSIX relpath:
      h.update(relpath_utf8); h.update(b"\0"); h.update(sha256(file_bytes).digest())
```

| | |
|---|---|
| Corpus | `captures/corpus_24h/corpus_20260805` — 88 files |
| **v1 digest, open and close** | `e3ab1aec321a762848496af13557be0b419a4a3d7161b05b178f21095029ac10` |
| `git status --porcelain` on the corpus | empty at open and close |

The corpus was **read-only throughout** — this WO never opened a corpus file except to hash it.
Byte-level invariance is established for *this* WO by the v1 digest and by git. What is **not**
established, and cannot be, is continuity with the historical `a025db1e…` label. **I am not
certifying that the corpus is unchanged since WO-045 — I am reporting that the historical label
cannot verify it either way.** The lead should rule on whether that needs anything further.

---

## §2 THE CITATION

### §2.1 The published schedule

| Field | Value |
|---|---|
| **Source URL** | https://www.kraken.com/features/fee-schedule |
| **Retrieved** | **2026-08-07** |
| **Product** | Kraken Pro — spot crypto (**advanced trading**, NOT "Instant Buy") |
| **Effective date on the schedule page** | **none published** |
| **Related dated change** | tier *determination* changed **2026-07-09** — your tier is now the best of spot 30-day volume **or** Assets on Platform (AoP). Source: https://support.kraken.com/articles/cross-platform-fee-tier-changes |
| **Basis** | 30-day rolling: "measured and applicable for trades occurring in the last 30 days only" |

The full table as published (transcribed verbatim into `KRAKEN_SPOT_SCHEDULE`):

| Tier | 30-day vol (USD) / AoP | Maker % | Taker % |
|---|---|---|---|
| **Tier 1** | **$0+ / N/A** | **0.40** | **0.80** |
| Tier 2 | $2.5K+ / N/A | 0.30 | 0.60 |
| Tier 3 | $10K+ / 20k | 0.22 | 0.38 |
| Tier 4 | $25K+ / 50k | 0.20 | 0.35 |
| Tier 5 | $50K+ / 100k | 0.15 | 0.30 |
| Tier 6 | $100K+ / 200k | 0.12 | 0.25 |
| Tier 7 | $250K+ / 400k | 0.10 | 0.22 |
| Tier 8 | $500K+ / 600k | 0.08 | 0.20 |
| Tier 9 | $1M+ / 1m | 0.06 | 0.18 |
| Tier 10 | $2.5M+ / 2.5m | 0.04 | 0.15 |
| Tier 11 | $5M+ / 5m | 0.02 | 0.12 |
| Tier 12 | $10M+ / 10m | 0.0 | 0.10 |
| Pro 1 | $50M+ / 20m | 0.0 | 0.09 |
| Pro 2 | $100M+ / 25m | 0.0 | 0.08 |
| Pro 3 | $250M+ / 50m | 0.0 | 0.07 |
| Pro 4 | $400M+ / 80m | 0.0 | 0.06 |
| Pro 5 | $500M+ / 100m | 0.0 | 0.05 |

**Corroboration.** The base rate moved recently, so I did not accept a single fetch. An independent
search confirms 0.40 / 0.80 as the July-2026 entry tier and states explicitly that older pages
still repeat a 0.25/0.40 starting rate which "is no longer the public entry tier." A second fetch
of Kraken's own support article confirmed the 2026-07-09 tier-determination change. **This matters
for rule 0.1e**: had I trusted recall over retrieval, I would have written a *lower*, obsolete
number and called it a citation.

### §2.2 The declared tier — **Tier 1**, and why

**This system has never placed an order.** Its 30-day spot volume is exactly $0 and it holds no
Assets on Platform. Tier 1 is therefore not a conservative choice — **it is the only tier the
account can substantiate.**

Any better tier would be a cost assumption wearing a fact's clothing. Assuming Tier 6 buys a 3.2×
cheaper fee by asserting $100K of monthly volume that does not exist.

Tier 1 is also self-correcting in the right direction: a strategy that cannot survive Tier 1 might
survive Tier 6 — but it only *reaches* Tier 6 by trading enough to get there, which means paying
Tier 1 on the way in.

### §2.3 The maker rate — recorded, NOT wired

**Tier 1 maker = 0.40%.** Recorded in the schedule and reachable via `fee_schedule.maker_pct()`.
**No execution path uses it**, and a test asserts that (`test_maker_rate_is_not_wired_into_execution`).
Every fill this system prices crosses the spread and is a taker fill (WO-008a-R6 / RULING 5).

It is declared **now**, before D51's parked maker-rebate track wakes up, precisely because citing it
*then* — after seeing what it would save — would be citing to a conclusion.

### §2.4 The delta — a finding

| | |
|---|---|
| Declared (WO-050) | 0.26% |
| **Cited (Tier 1 taker)** | **0.80%** |
| Delta | **+0.54 percentage points** |
| Ratio | **3.0769×** |
| On one 0.1 BTC order at ~$64,600 | $1.68 → **$5.17** per fill |

The declared figure was not a small approximation. It was **less than a third** of the published
rate, and it was the larger of the two cost channels in the only verdict this project has produced —
where fees were **96.3%** of total costs. Two independent errors happened to point the same way: the
old 1-bp-vs-0.1% slippage defect (found in WO-050) and this one both made trading look cheaper than
it is.

Again, per §0.1: **no result was recomputed.**

---

## §3 THE IMPLEMENTATION

### §3.1 / §3.2 — tier-aware, with provenance in code

New module **`src/trading/execution/fee_schedule.py`** holds the URL, the retrieval date, the
product, the tier-rule effective date, the full published table as `FeeTier` rows, and:

```python
ASSUMED_TIER = "Tier 1"

def taker_pct(name: str = ASSUMED_TIER) -> Decimal:
    return tier(name).taker_pct
```

`src/trading/execution/paper.py` no longer types a number:

```python
DEFAULT_FEE_RATE_PCT = fee_schedule.taker_pct()  # PERCENT of notional -> Tier 1 taker, 0.80%
```

Changing the assumed fee is now a **declared act**, the same discipline as the reason-code
vocabulary. You change a named tier, or you re-cite the schedule. `tier()` raises `KeyError` on a
name that was never published — you may select a row that exists, you may not invent one.

The stale class docstring ("default 0.1% taker per side", "assumed 0.1% constant") was corrected;
it had been wrong since before WO-050 changed both defaults.

### §3.3 — the pin, and the proof that it bites

`tests/test_fee_schedule.py` — **9 tests**, all single-purpose (§0.10). The pin:

```python
published = fee_schedule.tier(fee_schedule.ASSUMED_TIER).taker_pct
assert PaperExecutionClient.DEFAULT_FEE_RATE_PCT == published
```

**Bite proof `tools/wo051_citation_bite_proof.py` — VERDICT: PASS.** Four artifacts, sha256
exact-restore, two mutations that each fail a *different* property:

| Artifact | Result |
|---|---|
| 1 — PRISTINE | rc 0, 21 passed |
| 2 — MUTATION **DRIFT** (`DEFAULT_FEE_RATE_PCT` back to a bare `Decimal("0.26")`) | rc 1 — **PIN fails**, TIER tests hold |
| 3 — MUTATION **OPTIMISM** (`ASSUMED_TIER = "Tier 6"`) | rc 1 — **TIER tests fail**, PIN holds |
| 4 — RESTORED | rc 0, 21 passed |

```
paper.py        sha256 BEFORE/AFTER : 07a3ba997183fbcd9c4cb1cc3dfff4b4307ee19961b742d9ec73061c20e91c27
fee_schedule.py sha256 BEFORE/AFTER : b60415a37c9b85502b501438a93551c8dc9793b3d4405ef545dbfab9c9fbbadf
IDENTICAL: True
DRIFT discriminates (PIN fails, TIER holds)    : True
OPTIMISM discriminates (TIER fails, PIN holds) : True
```

**Why the second mutation earns its place.** Under OPTIMISM the pin **still passes** — the wired
constant and the looked-up rate agree perfectly, at a tier the account cannot claim. A pin on the
*number alone* would have certified an optimistic fee as cited. That is the §2.2 failure mode, and
it is only caught because the tier itself is asserted.

§0.10 exclusions are recorded in the proof as `broad_failed`: three tests read the wired constant
*and* the schedule *and* the citation record, so they fail under either mutation and attribute
nothing.

### §3.4 — R4 survives ✅

`test_r4_fees_and_slippage_differ_under_the_defaults` reads the class attributes, so it re-verified
automatically and passes: fee fraction **0.008** vs slippage **0.0001**. The channels are now
**80× apart**, further from the WO-048 coincidence than before.

### §3.5 — arithmetic untouched ✅

`compute_execution_costs` was not edited. `tests/integration/test_cost_reconciliation.py` — **4
passed**; it passes explicit rates and is insulated from these defaults by construction.
`test_r4_the_one_cost_implementation_is_unchanged` passes.

---

## EVERY ATTEMPT, AND EVERY FINDING

1. **Twenty digest schemes tried; none reproduces `a025db1e…`.** Reported as a STOP above, and
   `tools/corpus_digest.py` committed so future reports cite a regenerable number.
2. **Did not trust a single fetch.** The cited rate is far from the historically familiar Kraken
   base rate, so I corroborated with an independent search and a second Kraken support article
   before wiring it. Rule 0.1e cuts both ways: the remembered number would have been *lower*.
3. **`support.kraken.com/articles/360000526126` does not contain the table** — it only links to the
   schedule page. Recorded so the next reader does not repeat the fetch.
4. **One existing test failed, correctly, and was superseded — not deleted.**
   `test_r4_the_rates_carry_their_declared_values` asserted `DEFAULT_FEE_RATE_PCT == Decimal("0.26")`
   — a pin on a *declared* value. Re-pinning a literal there would have re-created exactly the
   uncited constant this WO removes, so the fee half was removed **with the reason recorded at the
   site** (D47) and the fee is now pinned to its source in `test_fee_schedule.py`. The slippage half
   is untouched and still asserted.
5. **⚠ FINDING — the WO-048 identical-channels coincidence is STILL ALIVE in `backtest/costs.py`.**
   `CostModel.DEFAULT_FEE_RATE_PCT = 0.1` (percent) and `DEFAULT_SLIPPAGE_FACTOR = 0.001` (fraction)
   are **the same 0.001 of notional** — verified:
   ```
   CostModel fee 0.1% -> 0.001 ; slippage 0.001 ; IDENTICAL CHANNELS: True
   Paper     fee 0.80% -> 0.008 ; slippage 0.0001 ; IDENTICAL CHANNELS: False
   ```
   WO-050's R4 fix and its permanent guard cover **only** `PaperExecutionClient`. `CostModel` also
   still carries an **uncited 0.1% fee**, now divergent from the cited 0.80%.
   **NOT FIXED — deliberately out of scope** (§SCOPE is the taker fee; changing it would ripple into
   five test files whose expectations are written against 0.1%). It is reachable from production
   code but is only ever constructed bare in tests, so no shipped path uses those defaults today.
   **Recommend a follow-up WO** to route `CostModel`'s defaults through `fee_schedule` and extend
   the R4 guard to cover it.
6. **⚠ FINDING — `pyproject.toml` and `requirements.txt` disagree.** `websockets` is required at
   import time by 13 test modules but is absent from `[project.dependencies]`, so a venv built with
   `uv pip install -e ".[dev]"` — the documented acceptance path — **fails collection with 13
   errors**. Resolved for this WO by additionally installing `requirements.txt`; recorded because it
   will bite the next person. Pre-existing, not introduced here.

---

## §5 ACCEPTANCE

- [x] Published schedule cited — URL, retrieval date **2026-08-07**, effective-date status, full tier table
- [x] Declared tier **Tier 1** stated with reasoning; **maker 0.40% recorded, not wired** (asserted)
- [x] Rate is tier-aware with provenance in code; test pins constant == citation; **bite proof PASS**
- [x] Fees ≠ slippage still asserted (0.008 vs 0.0001); **WO-011 reconciliation passes** (4 passed)
- [x] **No recomputation of WO-050** — stated explicitly (§0.1 above)
- [x] Corpus digest identical — v1 `e3ab1aec…`, 88 files, git-clean at open and close
      (with the `a025db1e…` STOP reported above)
- [x] Test count with arithmetic, both interpreters, both orders — below
- [x] lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

### Test count arithmetic

```
  436  baseline at HEAD b9d9b45 (3.14, confirmed by a full run before any edit)
+   9  tests/test_fee_schedule.py (new)
±   0  test_r4_the_rates_carry_their_declared_values — superseded in place, not removed
─────
  445  expected
```

| Leg | Order A (declaration) | Order B (seed 51051) |
|---|---|---|
| Python 3.14.6 | **445 passed, 2 skipped** (315.49s) | **445 passed, 2 skipped** (312.08s) |
| Python 3.11.15 | **445 passed, 2 skipped** (311.99s) | **445 passed, 2 skipped** (307.81s) |

All four legs agree with the arithmetic. The 3.11 leg ran in a throwaway `uv` venv, removed after.

### CI — **run `31224446780`, GREEN both legs** (commit `8e3997c`)

Counts read from the job logs, not the summary badge:

| Job | Deterministic (`-p no:randomly`) | Randomised |
|---|---|---|
| `test (3.11)` — id 93015762296, 10m31s | **445 passed, 2 skipped** (306.02s) | **445 passed, 2 skipped** (301.54s) |
| `test (3.14)` — id 93015762537, 10m41s | **445 passed, 2 skipped** (305.72s) | **445 passed, 2 skipped** (303.15s) |

Eight independent runs (four local, four CI) all report 445/2. The only annotation is a Node.js 20
deprecation notice on the checkout/setup-python/codecov actions — pre-existing, unrelated to this WO.

**Note on WO-050's close commit.** WO-050 §7.1 required CI green *before* the run, which was
satisfied by run `31214886348` on `605a4e6`. Its post-run commit `b9d9b45` also went green
independently — run `31216247330`, 10m54s — so no CI gap is left behind this WO's base.

---

## FILES

| File | Disposition |
|---|---|
| `src/trading/execution/fee_schedule.py` | **NEW** — the citation, the table, the declared tier |
| `src/trading/execution/paper.py` | **CHANGED** — fee is a lookup; stale docstring corrected |
| `tests/test_fee_schedule.py` | **NEW** — 9 single-purpose tests |
| `tests/test_backtest_accounting.py` | **CHANGED** — superseded fee pin, reason recorded at the site |
| `tools/wo051_citation_bite_proof.py` | **NEW** — four artifacts, PASS |
| `tools/corpus_digest.py` | **NEW** — declares a reproducible digest scheme |
| `captures/corpus_24h/corpus_20260805/` | **READ-ONLY — untouched** |
