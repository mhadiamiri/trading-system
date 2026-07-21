# WO-016 — FINAL REPORT — Checksum-Failure Diagnosis (offline) + Gappy-Threshold Re-Declaration

**STOPPED AT THE §1 SEAM (rule 0.9).** Diagnosis + citation + hypothesis test + replay harness are
done and the fix is PROPOSED, NOT IMPLEMENTED — awaiting approval before §2. §3 (threshold
re-declaration), §4 (decision logs), §5 (verify), §6 (this report) are complete. No production code
was changed. Baseline HEAD `6e977c2`. NO VENUE CONNECTION.

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

## 5. The fix — PROPOSED, NOT IMPLEMENTED (gated at the §1 seam)
Format Decimal price/qty **fixed-point** at the single Decimal→string site (`_current_ladder_strings`:
`format(q, 'f')`/`format(p, 'f')` instead of `str(q)`). Verified to yield expected **200/200**.
- **Interfaces touched:** `_current_ladder_strings` — a **private** method; **no public signature
  change**, no `object.__setattr__`/`type: ignore`/monkeypatch (**rule 0.1a not triggered**).
  `compute_checksum` unchanged (optionally add a labelled sentinel rejecting an `'E'` in a size).
- **§2 requirements (post-approval):** replay all 200 captures to **200/200** as a permanent
  regression fixture; bite proof (four artifacts, sha256: revert → replay FAILS with real output →
  restore → 200/200); retain artifacts as an immutable fixture (do not overwrite A2/A3).
- **Not done this session by ruling** (0.9 seam) — awaiting approval.

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
**STOP at the §1 seam for approval before implementing the fix (§2). Then STOP again for review.**
Do NOT proceed to WO-013 or the corpus.
