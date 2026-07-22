# WO-013 FOLLOW-UP — items 1, 2, 3 (post-acceptance ruling)

**Baseline:** `10784cb`. **NO VENUE CONNECTION.** The lead ruled four items; **did 1, 2, 3** (item 4 —
event_type governance — is approved and sequenced next but explicitly *do not begin*). Item 2 surfaced a
significant instrument-fitness finding, reported below.

---

## 1 — INSTRUMENT IDENTITY is the SIXTH scope dimension (and my B report had violated it)
The B report differenced a WIDENED measurement against the ADAPTER-ONLY baseline (`SIGNAL 0.791 / NOISE 1.0
/ RATIO 0.79`) and compared `108.714 vs 108.979` — two instruments, two boundaries: **uninterpretable by
construction**, not merely noisy. Fixed:
- **Instrument added to the record's scope and identity.** `host_baseline` records now carry `instrument`;
  a legacy record (no field) reads as `adapter-only`. Scope is now host / load / source / duration /
  resolution / **instrument** — enumeration **OPEN** (recorded in the store + progress.md: interrogate every
  anomalous delta for an undeclared dimension before reading it as signal).
- **Cross-instrument delta REFUSED, not warned** — declared reason code `MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH`
  (decision.py, same commit), same treatment as the host mismatch. `require_measurement_instrument` raises; the
  establishment tool refuses before differencing. **Bite proof** (`evidence/WO-013/instrument_mismatch_bite_proof.txt`,
  four artifacts, sha256, terminating in the refusal): A1 refusal fires → A2 guard disabled, REAL-FAIL (did not
  raise) → A3 restore → A4 byte-identical. **OK.**
- **Adapter-only ledger CLOSED** (into `closed_instrument_ledgers`, annotated) — entries **remain valid for what
  they measured**, never invalidated. **Loop-boundary ledger OPENED at ENTRY ZERO** = **108.717 ms** (median of 9
  full-loop runs), established from scratch, **never inherited via a cross-instrument delta**. `save_baseline` now
  encodes this: a different-instrument write closes the prior ledger and opens at entry zero (guard test added).
- **The two cross-instrument comparisons WITHDRAWN** from the store's B assessment (annotated, not deleted, with
  why they are uninterpretable). The "loop overhead is small" conclusion is instead established without
  cross-instrument differencing — by item 2's containment proof and the full-loop ledger standing on its own
  entry-zero baseline.

## 2 — CONTAINMENT PROOF (behavioral), and a significant CALIBRATION finding
My B claim that the widened instrument "times adapter + strategy.decide + risk.check + emission" was
source-inspection (0.1f). Proved behaviorally by injecting a known per-frame delay into the **loop** path (a
line only the full-loop instrument runs), sweeping below and above the ~30.6 ms/frame inter-frame budget.
`evidence/WO-013/containment_bite_proof.txt` (four artifacts, sha256 exact-restore):

| injected/frame | widened mean_cycle | rise | vs 2.0 ms floor | achieved |
|---|---|---|---|---|
| 0 (baseline) | 108.801 ms | — | — | 1958/min |
| 10 ms | 110.771 ms | **+1.97 ms** | BELOW floor (RATIO 0.98) | 1958/min |
| 40 ms | 205.302 ms | **+96.5 ms** | ABOVE floor (RATIO 48) | **1469/min** (rate drop) |
| restored | 107.527 ms | ~0 | — | 1958/min |

- **ENCLOSURE CONFIRMED** — the 40 ms/frame loop injection moves the widened mean_cycle enormously; the
  adapter-only instrument never runs the line, so it could not. The loop **is** in the timed path.
- **ATTENUATION — the calibration finding the ruling anticipated (reported, NOT adjusted).** `mean_cycle =
  span / actual_samples` is the mean **sleep-wake (event-loop lag)** cycle — a **starvation/responsiveness**
  metric (its WO-014c-1 purpose), **not a per-frame CPU meter**. Below the ~30.6 ms/frame budget the pacer
  leaves idle slack, so a per-frame block delays the sampler's wake only by ~its residual-on-arrival: **10 ms/frame
  → +1.97 ms** (transfer 0.055, and *below* the 2.0 ms floor). It rises sharply only at **saturation** (40 ms/frame
  → +96.5 ms, and the rate drops). Injected 10 ms → measured +1.97 ms is ~5% of the naive `inj × frames/cycle`
  = full attenuation, exactly the "materially less than injected" case the ruling said to report.

## 3 — RESOLUTION as a DECLARED LIMIT in per-frame terms (corrected by item 2)
Item 3's naive arithmetic (2.0 ms cycle floor ÷ ~3.3 frames/cycle ≈ 0.6 ms/frame) assumes a **linear**
transfer. Item 2 measured that it is **not** linear. The declared limit, in the HOST_SUSPEND form (what is
caught / not / what the uncaught case looks like), put in the store scope, the tool docstring, and progress.md:
- **CYCLE floor = 2.0 ms** — CONSERVATIVE: set *above* the largest observed noise excursion (1.586 ms), so noise
  is never read as signal (a floor set too tight manufactures false signal). **n = 9, provisional**; ~**20–30 runs**
  would firm the outlier *rate* and let the floor be a tail percentile rather than a single observed outlier.
- **Effective per-frame detection floor ≈ 10 ms/frame** (not 0.6 ms): measured sensitivity ~0.2 ms-cycle per
  ms-frame ⇒ 2.0 / 0.2 ≈ 10 ms/frame. **Caught:** per-frame cost approaching saturation (~30 ms/frame; the rate
  also drops). **NOT caught:** anything below ~10 ms/frame. **The uncaught case looks like:** a WO adds
  0.3–1 ms/frame, mean_cycle does not move, the gate reports compliance while per-frame throughput cost silently
  rose. Reviewer-known in advance.
- **FINDING flagged for a ruling (reported, NOT begun):** `mean_cycle` is a lag/starvation detector; a direct
  per-frame timer would be the fit instrument for per-frame-cost gating. This is the same shape as item 4 — its
  own WO if the lead concurs.

## Verification (`evidence/WO-013/verify_items123.txt`)
- Deterministic **212 passed** (245.73 s); randomized `--randomly-seed=20260728` **212 passed** (246.18 s);
  0 failed / xfailed / xpassed both orders.
- **Delta vs 210 (+2):** `test_instrument_mismatch_is_refused_not_warned`, `test_save_baseline_closes_prior_
  ledger_on_instrument_change` (item 1 guards); the WO-017-ledger gate test was rewritten in place for the new
  full-loop/closed-ledger structure (net +2, no removals).
- `lint-imports` **6/6**; contract **6/6**; `ruff` clean. **New reason code declared same commit:**
  `MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH`. **Secret scan:** 0 hits.
- **Venue connection? NO. HTTPS fetch? NO. Prose standing in for output? NO** — the ledger figures, the noise
  floor, and the containment transfer function are all from captured establishment runs (pasted).
- **Changed but not asked?** Only what items 1–3 require: `decision.py` (reason code), `host_baseline.py`
  (instrument identity + refusal + close-on-instrument-change), `config/mean_cycle_baselines.json` (ledgers
  restructured, floors, withdrawals), `tools/establish_mean_cycle_baseline.py` (refusal + corrected floor),
  `test_mean_cycle_baseline_gate.py` (+2 guards, 1 rewrite), `progress.md`, the two new bite-proof harnesses,
  `evidence/WO-013/*`, this report. `instructions.md` carries the lead's text (uncommitted, never by me).

---
**STOP for review.** Item 4 (event_type governance) is approved and sequenced next but NOT begun. Also
surfaced for a ruling: `mean_cycle`'s per-frame attenuation (a direct per-frame timer as the fit instrument).
Then: CI capture + version ruling → CI green → 008c → 24-h corpus.
