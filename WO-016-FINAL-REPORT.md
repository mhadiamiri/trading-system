# WO-016 — FINAL REPORT — Checksum-Failure Diagnosis (offline) + Gappy-Threshold Re-Declaration

**UPDATED for project-lead ruling D26 — the fix is APPROVED (INTERIM) and IMPLEMENTED.** The
original §1 diagnosis (below) stands; the D26 addendum work is in the **"D26 ADDENDUM"** section at
the end (fix implemented, 200/200 regression + bite proof, wire-string feasibility, domain
completeness, proven §3 partition, fixture label, extra decision log). Baseline HEAD `6e977c2`.
NO VENUE CONNECTION. Then STOP for review.

**Headline:** the 234 checksum failures (0.198%) are **ours and specific** — **scientific-notation
formatting of small quantities** in the checksum string, present in **200/200** captures. The
production path reproduces every failure (200/200) and **fixed-point formatting recovers Kraken's
expected checksum for every one (200/200)**. The lead's repeated-price hypothesis is a *correlated
symptom* (27.5%), not the cause.

## 1. Failure-set characterization (`evidence/WO-016/characterization.txt`)
Denominator: **234 failures = 200 full captures + 34 summaries; 234 / 118,043 raw = 0.198%.**
- **Repeated prices in one update: 55/200 = 27.5%** (bids-side 52, asks-side 3). Repeat-count
  distribution {2:30, 3:12, 4:5, 5:4, 6:2, 8:1, 9:1}. A minority — cannot be the common cause.
- **Scientific-notation size in the checksummed top-10 ladder: 200/200 = 100.0%** — the one factor
  in every failure.
- **Time:** 17:13:05Z–18:07:15Z (span 3250s); inter-failure gap median 0.7s, mean 13.9s, max
  416.6s → arrives in **bursts**, not uniformly, not one block.
- **Side:** repeated-price cases bids-heavy; the scientific-notation factor lands on whichever side
  carries a sub-1e-6 residual level.

## 2. Repeated-price semantics — cited (`evidence/WO-016/repeated_price_semantics.txt`)
Kraken v2 book checksum guide (docs.kraken.com/api/docs/guides/spot-ws-book-v2), **verbatim**:
*"Process all price level updates in a message before calculating the checksum."* and
*"Parse `price` and `qty` fields using a decimal or string decoder to preserve full precision
through deserialisation."*
- **Which is it?** **DOCUMENTED SILENCE** on the explicit term "last-wins," but "process all
  updates before the checksum" **entails sequential application** (later same-price entry wins).
  **Behavioral evidence (labelled inference, sovereign for what happened):** our last-wins apply
  produced a book whose fixed-point checksum equals Kraken's expected for all repeated-price
  captures → **our repeated-price handling is correct**; it is not the defect.

## 3. Hypothesis test — which semantics reproduces Kraken's checksum?
Driving the **production** path over each capture's recorded top-10 ladder:
- **Production `str()` formatting → matches COMPUTED 200/200, EXPECTED 0/200** (reproduces the bug).
- **Fixed-point size formatting → matches EXPECTED 200/200.**
One formatting rule reproduces Kraken's expected checksum for every capture ⇒ **the diagnosis is
ours and specific.** No venue-side residue; **no escalation** required (§1.3). Root cause:
`_current_ladder_strings` (`kraken_v2_book.py` ≈ L1216-1217) uses `str(Decimal)`, which renders
small quantities in scientific notation (`Decimal('1.0E-7')→'1.0E-7'`); `compute_checksum` then
yields the fragment `'10E-7'` instead of Kraken's `'10'`, corrupting the CRC. (The ground-truth
vector passed because it feeds decimal *strings* directly, never exercising the Decimal→str path.)

## 4. Replay harness — drives the PRODUCTION path (`tools/replay_checksum_capture.py`)
Confirmed: it **imports and calls** `KrakenV2BookAdapter.apply_snapshot`, `_current_ladder_strings`,
and `compute_checksum` — **not a reimplementation** (rule 0.1h). It seeds a production
`LocalBookData` with a capture's recorded top-10 ladder and drives the exact formatter that failed.
Honest limit (0.1f): the 20 preceding frames cannot rebuild a thousands-of-frames book; the
captured post-update ladder **is** the production ground truth the CRC ran over, so the replay is
faithful. Output: `evidence/WO-016/replay_harness_output.txt` (200/200 reproduce; 200/200 fix-yields-expected).

## 5. The fix — IMPLEMENTED (INTERIM, per ruling D26) — full detail in the D26 ADDENDUM below
Format Decimal price/qty **fixed-point** at the single Decimal→string site (`_current_ladder_strings`:
`format(q, 'f')`/`format(p, 'f')` instead of `str(q)`). Verified to yield expected **200/200**.
- **Interfaces touched:** `_current_ladder_strings` — a **private** method; **no public signature
  change**, no `object.__setattr__`/`type: ignore`/monkeypatch (**rule 0.1a not triggered**).
  `compute_checksum` unchanged (optionally add a labelled sentinel rejecting an `'E'` in a size).
- **§2 requirements (post-approval):** replay all 200 captures to **200/200** as a permanent
  regression fixture; bite proof (four artifacts, sha256: revert → replay FAILS with real output →
  restore → 200/200); retain artifacts as an immutable fixture (do not overwrite A2/A3).
- **DONE per D26:** implemented in `_current_ladder_strings` (labelled INTERIM), **200/200**
  regression (`test_checksum_capture_replay.py`), four-artifact sha256 bite proof
  (`evidence/WO-016/bite_proof.txt`). See the D26 ADDENDUM section.

## 6. Threshold re-declaration (`evidence/WO-016/gappy_threshold_redeclaration.txt`) — nothing implemented (0.4/3.1)
Four figures, with arithmetic:

| Metric | Value | Derivation |
|---|---|---|
| (i) naive `(span/interval − actual)/expected` | **8.16%** | (35,999 − 33,062)/35,999 — measures per-cycle overhead (108.89 vs 100 ms), not health |
| (ii) connected-time-corrected | **7.93%** | (35,908 − 33,062)/35,908; excludes 9.159s true disconnect — barely moves (insufficient) |
| (iii) recorded-gaps / window (proposal) | **0.08%** | 2.88s recorded missed-wake time / 3600s |
| (iv) connected time / wall (lead's (b)) | **99.75%** | (3614.63 − 9.159)/3614.63; companion validated-emission uptime 93.95% |

**Case for recorded-gaps + limits:** it measures real missed wakes only — immune to per-cycle
overhead and disconnect-idle, and **does not drift with capture length** (the corpus-scale
property). Limit: it can't see uniform sub-`LAG_GAP_FACTOR` starvation; the complementary
elevated-lag-distribution metric (median 8.97ms, p95 13.6ms, elevated 0.04%) covers that. **Two
questions, two metrics.** **Three components per 0.1j** for the proposal: per-sample bound = wake
overrun ≥ `LAG_GAP_FACTOR`×interval; aggregation window = the measurement window; verdict fraction
= VOID if Σ(recorded-gap)/window > F (proposed F=10%, **the lead rules the number**).

## 7. Decision-log entries (§4)
Three entries written verbatim to `docs/decisions/2026-07-21-*.md`:
`execution-reached-not-worked` (4.1), `threshold-declaration-completeness` (4.2 → ratified 0.1j),
`gappiness-metric-measured-itself` (4.3). My correction to `discrimination.txt` stands as an
annotation (accepted; never rewritten).

## 8. Verification (`evidence/WO-016/verify.txt`)
- Deterministic `-p no:randomly`: **190 passed in 246.35s (4:06)**. Randomized
  `--randomly-seed=20260725`: **190 passed in 247.13s (4:07)**. 0 failed/xfailed/xpassed both
  orders. lint-imports **6 kept / 0 broken**; contract **6/6**; ruff **All checks passed**.
  **No delta** (no production/test change — only a tool + evidence + decision logs added). No new
  reason code. Secret scan of all added files: 0 hits. Committed + pushed to `master`; **local HEAD
  == remote HEAD** (SHA in the session hand-off).

## 9. Venue connection? **NO.** HTTPS doc fetch? **YES**
No socket to any venue was opened. HTTPS doc fetch: Kraken v2 book checksum guide (via the fetcher)
+ one web search to locate it — permitted, not venue contact.

## 10. Prose standing in for output? **NO.**
Every figure traces to `evidence/WO-016/{characterization,replay_harness_output,diagnosis,
repeated_price_semantics,gappy_threshold_redeclaration,verify}.txt` and the reproducible harness.

## 11. Changed but not asked? **None.**
Added (all WO-mandated): `tools/replay_checksum_capture.py` (§1.4 deliverable),
`evidence/WO-016/*`, `docs/decisions/2026-07-21-*.md` (§4), `WO-016-FINAL-REPORT.md` (§6).
**No production code changed.** `instructions.md` carries the lead's WO-016 text (their edit, left
uncommitted — not mine to commit).

## 12. What could not be completed, and why?
- **The fix (§2)** — deliberately NOT done: rule 0.9 seam requires approval first. Proposed and
  fully validated (200/200), awaiting the lead's go.
- **The VOID-metric verdict fraction (F)** — a declared threshold; the lead rules the number
  (0.4/3.1). Proposal with all three 0.1j components is on record.
- Everything else in §1/§3/§4/§5 is complete.

---

# D26 ADDENDUM — FIX IMPLEMENTED + FOLLOW-UP RULINGS

Project-lead ruling **D26** approved the fix (INTERIM) and added four report items. All done below.

### D26.1 — The fix (APPROVED, INTERIM, IMPLEMENTED)
- `src/trading/data/adapters/kraken_v2_book.py::_current_ladder_strings` now renders
  `format(p,'f')`/`format(q,'f')` (fixed-point) instead of `str()`, **labelled INTERIM in-code**:
  it makes the re-render CORRECT; it does not ELIMINATE re-rendering (which FR-018a(f) prohibits in
  letter). Private method; **no public signature change** (0.1a not triggered); nothing weakened (0.4).
- **Acceptance (ruled): 200/200.** `tests/integration/test_checksum_capture_replay.py` replays all
  200 captured artifacts through the **production** path and validates each to Kraken's expected
  checksum — **200/200** (before the fix: 0/200). Permanent regression test added (not xfail/skip, 0.1b).
- **Bite proof** (`evidence/WO-016/bite_proof.txt`, rules 0.7/0.1i): A1 PASS (200/200) → A2 revert
  `format→str` → **real FAIL** (0/200, assertion text) → A3 restore → PASS → **A4 sha256 byte-identical**.
- **Fixture retained + labelled** (D26.4): `tests/fixtures/kraken_v2_checksum_captures_wo016.json`
  (200 captures, evidentiary bounds), labelled *"witnesses SMALL-QUANTITY RENDERING and
  REPEATED-PRICE APPLICATION"* — accretion doctrine; **A2/A3 not overwritten**.

### D26.2 — Wire-string feasibility (REPORT ONLY — `evidence/WO-016/wire_string_feasibility.txt`)
**FEASIBLE at acceptable cost (outcome (a)) → its own WO.** The apply path **REPLACES** qty
(`apply_incremental_update`:478), never synthesizes — so every book qty is a transmitted value, and
the wire string exists. `parse_float=Decimal` already receives the **raw token text** (:2363) and
discards it at parse — retention is **plumbing, not architecture** (a `WireDecimal` carrying `.src`;
~20 short strings live; no signature change). Implementing it **closes FR-018a(f) literally** and the
defect class dies structurally. Recommend a dedicated WO; the gap is named, not implicit.

### D26.3 — Domain completeness (REPORT ONLY — `evidence/WO-016/domain_completeness.txt`)
`format(x,'f')` reproduces Kraken's transmitted string **for the observed/realistic domain** — every
fixed-point decimal, **trailing zeros** (`0.00005100` preserved via `parse_float=Decimal`), **integer
qty** (`5`, `5.00000000`), **exponent extremes** (`1E-8`→`0.00000001`), verified 200/200 + edge cells.
It is **not** a proof over the *entire* domain: the one unproven cell is a **non-fixed-point wire
token** (JSON scientific notation), unobserved and doc-silent — precisely what makes the fix INTERIM
and what the wire-string structural fix (D26.2) closes by construction.

### D26.§3 — Partition PROVEN + numeric bound (`evidence/WO-016/partition_proof.txt`)
Numeric missed-wake bound (0.1j): `LAG_GAP_FACTOR 2.0 × 0.1s` ⇒ a wake is missed when its interval
**≥ 200 ms**. **Partition of the 8.16% deficit, proven by identity** (actual × mean_cycle ≡ span):
mean cycle **108.886 ms** → **2,908 samples (8.08%) per-cycle overhead** (measurement artifact) +
**29 samples (0.080%) recorded missed-wakes** (real transient loop-busy) + **~0 disconnect-idle**
(29 + 2,908 = 2,937 ✓). **Rule on the partition:** the VOID gate must measure the 0.080%
(recorded missed-wakes), not the overhead-dominated 8.16%. Verdict fraction F remains the lead's number.

### D26.5 — Decision log (verbatim, added)
`docs/decisions/2026-07-21-certification-bounded-by-fixture-content.md` — *"A fixture cannot witness
a code path its data does not reach…"* (ratified verbatim).

### Updated answers to §6 items
- **8. Verification (post-fix):** `evidence/WO-016/verify_postfix.txt` — both orders (seed 20260725),
  **192 passed** (190 + 2 new regression tests), 0 failed/xfailed/xpassed; lint-imports 6/6, contract
  6/6, ruff clean. Delta = the 2 new tests, explained. Local == remote HEAD (SHA in session hand-off).
- **11. Changed but not asked?** Beyond §1: `src/…/kraken_v2_book.py` (the approved D26 fix),
  `tests/integration/test_checksum_capture_replay.py`, `tests/fixtures/kraken_v2_checksum_captures_wo016.json`,
  `docs/decisions/2026-07-21-certification-bounded-by-fixture-content.md`, and the D26 evidence files.
  All D26-mandated. `instructions.md` carries the lead's WO/D26 text (their edit, uncommitted).
- **12. Not completed:** the **structural** FR-018a(f) fix (wire-string) — feasible, scoped to its
  own WO by ruling; and the VOID verdict-fraction F — the lead's number.

---
**STOP for review** (the fix is implemented per D26; the structural wire-string fix and the VOID-F
number are the lead's next calls). Do NOT proceed to WO-013 or the corpus.
