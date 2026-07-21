# WO-016 ADDENDUM 4 (D29) — REPORT: baseline scope declared in full

Ruling **D29** — VETO DECLINED (the load-scope correction is accepted). Three scope refinements +
decision log. All declaration updates; **no `src/` production-code or test change**. No venue
connection. Baseline `139e16e`. Then STOP.

## A. Replay rate declared with its scope (0.1j)
`tools/establish_mean_cycle_baseline.py` + `config/mean_cycle_baselines.json` now label the rate:
**"~1,959 msg/min — representative of OBSERVED 60-MINUTE LOAD (WO-008b-B-RERUN)"** (not a universal
constant). **Re-declaration triggers:** (i) the corpus host faces a materially different sustained
rate; (ii) a future capture observes a materially different rate → the rate is RE-DECLARED, DATED,
old scope ANNOTATED, never silently replaced. **"Materially different" (numeric):** a sustained
rate outside **±20% of 1,959/min (<1,567 or >2,351/min)**. Derivation: measured mean_cycle varied
**<0.2% across a ~28% rate span** (1,531/min→108.798ms, 1,959/min→108.894ms), so within ±20% the
baseline holds; beyond it, re-declare.

## B. Replay source pinned
Named in the protocol declaration **and** the baseline record: the source is the WO-009 §2
ground-truth fixture `tests/fixtures/kraken_v2_raw_frames.py` (SNAPSHOT_FRAME + UPDATE_MODIFY_LEVEL)
— **pinned by identity, immutable, NOT recency/convention-picked** — calibrating against the LOAD of
run **`WO-008b-B-RERUN-20260721T170944Z`** (its rate). The drift path (picking a capture by recency)
is closed: the frames are a hardcoded, committed fixture. Honest note: the run's OWN retained frames
cannot be replayed standalone (they need the multi-thousand-frame prior book they accreted against —
replaying them cold only manufactures checksum failures), so a pinned valid fixture at the pinned
rate is the comparability anchor. Two hosts baselined a month apart now use identical input.

## C. Declared duration == validated duration
**WARMUP DURATION default reduced 120 s → 60 s** — the duration actually validated (this host:
108.894 ms, +0.0% vs standing; re-confirmed this session at 108.704 ms, −0.2%). Derivation: ~600 lag
samples at the 100 ms interval, far above the ~100 for a stable mean. No 120 s run is now claimed;
declared figure and validated figure are the same figure (D29 §C).

## D. Decision log + accretion dividend
`docs/decisions/2026-07-21-baselines-attract-scope-errors.md` (verbatim): *"a baseline is nothing
BUT scope… enumerate host, load, source, duration."* Recorded the **third accretion dividend**: the
same recorded hour now calibrates instruments on machines it never ran on, and establishment needs
**no venue connection / no socket authorization** — keeping the socket boundary clean and making host
provisioning a pure Ops operation. Every baseline dimension is now enumerated in the record's
`scope` object (host / load / source_run_id / duration).

## E. Verification
`evidence/WO-016/verify_d29.txt`: **202 passed** deterministic (247.06s) **and** randomized
(seed 20260725, 246.98s), 0 failed/xfailed/xpassed; lint-imports **6/6**; contract **6/6**; ruff
clean. **Delta: none in the test set** — only the declaration, the store record, the tool, and docs
changed (no `src/` or `tests/` code). No new reason code. Secret scan 0 hits (store confirmed
hash-only, no raw hostname). Committed + pushed to `master`; **local HEAD == remote HEAD** (SHA in
the session hand-off).

## Closing
- **Venue connection?** NO. **HTTPS doc fetch?** NO.
- **Prose standing in for output?** NO — the scope declarations live in the tool, the committed
  store record, and `evidence/WO-016/baseline_establishment.txt` (re-run at the 60 s default).
- **Changed but not asked?** None. D29-mandated: `tools/establish_mean_cycle_baseline.py`,
  `config/mean_cycle_baselines.json`, the decision log, this report. `instructions.md` carries the
  lead's WO/D29 text (their edit, uncommitted).
- **What could not be completed?** Nothing in D29. Still open by prior ruling (separate WOs): the
  structural wire-string FR-018a(f) closure, then WO-013 → CI → 008c → corpus.

---
**STOP for review.** Do NOT proceed to WO-013 or the corpus.
