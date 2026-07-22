# WO-013 FOLLOW-UP — items A, B, C (post-acceptance)

**Baselines:** A at `1fb96c1` (the named seam); B/C atop it. **NO VENUE CONNECTION.** The re-baseline
finding was larger than the WO; the lead ruled three items. All fold into the baseline protocol.

---

## A — The noise floor: a MANDATORY declaration (fifth scope dimension = RESOLUTION)
*(committed at the named seam `1fb96c1`)*
- **A.1 declared** from within-session vs cross-session spread on unchanged adapter code: within-session
  ~0.3 ms (1σ), ~0.6–0.8 ms p2p; **cross-session ~1.0 ms** (WO-017 session 107.961 ms vs WO-013 session
  108.979 ms, adapter byte-identical). Operational floor **1.0 ms** (adapter) → **1.5 ms** (widened, B).
  Added to the store `scope.resolution` and the tool's protocol declaration (0.1j).
- **A.2 standing report form** wired into the tool: every delta prints **SIGNAL / NOISE FLOOR / RATIO**;
  RATIO < 1 → recorded with **sign explicitly unestablished**, ledger keeps the entry (it bounds the effect).
- **A.3 WO-017 ledger entry annotated** (never rewritten) with the ruled text: *"Recorded, SIGN NOT
  ESTABLISHED … the honest reading is 'wire-string retention costs approximately nothing'."* Its headline
  −0.963 ms delta re-reads as **SIGNAL 0.963 / NOISE 1.0 / RATIO 0.96 → inside the floor**.
- **A.4 interleaved within-session A/B reported** (not implemented; pre-approved): mechanics, cost, and the
  conclusion that within-session (~0.3 ms) < cross-session (~1.0 ms), so interleaving **buys resolution**
  for deltas ≳0.5–0.6 ms by cancelling the cross-session term; sub-0.5 ms stays below floor. WO-017's six
  run values and their spread are included. `evidence/WO-013/noise_floor_and_ab_report.txt`.

## B — Instrument-scope mismatch: WIDEN THE INSTRUMENT
The rule governs "the loop's hot path"; the instrument timed only `adapter.process_raw_frame` — a subset
(a 0.1g-family defect: a rule whose instrument covers a subset of its scope reports compliance over the
whole scope). **Widened** (the lead's strong preference, no fallback needed): `establish_full_loop` replays
the pinned frame through the **real `LiveTradingLoop`** (0.1h — production loop, not a mimic) with the
event-loop lag sampler — the same instrument a live capture uses — so it times **adapter + strategy.decide
+ risk.check + emission**. Now the **default** (`--adapter-only` = legacy). Rule text (`progress.md`) and
instrument coverage now name the **same boundary** — closure met.
- **Widened establishment** (4×60 s, ~1957/min): 108.519 / 108.711 / 108.912 / 110.303 ms, core mean
  **108.714 ms**. Widened vs stored 107.923: **SIGNAL 0.791 / NOISE 1.0 / RATIO 0.79 → below floor, sign
  unestablished**; the widened core is even slightly **below** the same-session adapter-only mean
  (108.714 vs 108.979) — **loop overhead is below the noise floor** (consistent with WO-017's +0.008 ms
  live-vs-replay). Not re-declared to a below-floor, different-instrument figure (A.2).
- **Stored 107.923 retained, scope annotated adapter-only**; widened noise floor re-established
  (within-session core ~0.2 ms, heavier tails → ~1.5 ms operational, provisional n=4); a widened
  `assessment` entry added. `evidence/WO-013/widened_instrument.txt`. **A future per-frame `live.py`
  change is now visible to the re-baseline** — the gap the ruling closes.

## C — Two emitted-but-undeclared codes + an ungoverned namespace (report only) + one-line fix
`evidence/WO-013/event_type_governance_report.txt`:
- **(i)** `DATA_RECEIVED` and `EXEC_ORDER_FILLED` are **reason_codes** (emitted `reason_code=` values),
  undeclared and invisible to the colon-form `_raised_codes` scan → `raised ⇒ declared` still has an escape
  hatch. `EXEC_ORDER_FILLED` is the fill event (Principle VIII weight).
- **(ii)** `event_type` is **entirely ungoverned** — no `VALID_EVENT_TYPES`, no scan, no completeness check;
  the vocabulary test reads reason_code only. The ungoverned event_type namespace is what masked the §0
  problem (canonical codes read "producible" via their event_type literals).
- **(iii)** Governing it takes a declared event_type vocabulary + a keyword-arg (non-colon) scan that also
  closes the reason_code= hole + the four properties + reconciliation of current free event_types. **Its own
  WO — scope ruling requested.**
- **One-line fix (done):** the establishment tool's stale hardcoded `0.108886` comparison constant now reads
  the stored figure via `host_baseline.load_baseline()` — no orphan figure.

## Verification (`evidence/WO-013/verify_followup_ABC.txt`)
- Deterministic **210 passed** (245.23 s); randomized `--randomly-seed=20260727` **210 passed** (245.84 s);
  0 failed / xfailed / xpassed both orders. **No test count change** — A/B/C are declarations, tool changes,
  and docs; no src production code changed (the only code touched is the establishment *tool*).
- `lint-imports` **6/6**; contract **6/6**; `ruff` clean. **Secret scan:** 0 hits. **No new reason code.**
- **Venue connection? NO. HTTPS fetch? NO. Prose standing in for output? NO** (noise floor derived from
  captured run values; widened figure from 4 captured runs; both pasted).
- **Changed but not asked?** Only what A/B/C require: `config/mean_cycle_baselines.json` (scope +
  annotations + widened assessment), `tools/establish_mean_cycle_baseline.py` (widened instrument, noise
  floor + report form, stale-constant fix), `progress.md` (rule = instrument boundary; noise-floor rule),
  `evidence/WO-013/*`, this report. `instructions.md` carries the lead's text (uncommitted, never by me).

---
**STOP for review.** Next by sequence: CI capture + version ruling → CI green → 008c → 24-h corpus.
Also awaiting a scope ruling on the **event_type governance WO** (item C).
