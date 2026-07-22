# WO-017 FOLLOW-UP — items A & B (post-acceptance)

**Baseline:** `5c4eab6` (WO-017 accepted). **NO VENUE CONNECTION.** Two non-reopening items from the
acceptance note. Then STOP.

---

## A. The 200/200 fixture guards CHECKSUM MATH, not the wire path — stated, labelled, and made non-recurring

**Stated explicitly (report + fixture + test).** The 200-capture fixture is a **REGRESSION GUARD ON THE
CHECKSUM MATH**. It cannot witness `.wire` retention because its artifacts contain no wire text to retain —
the wire text was discarded at capture time (retention did not exist yet), so `local_book_bids/asks` store
`str(Decimal)` and the replay reconstructs the wire form via `WireDecimal(format(x,'f'))`. **The wire path is
certified ELSEWHERE:** `tests/integration/test_wire_string_retention.py` bite proofs **(a)** (checksum input ==
transmitted text) and **(c)** (a scientific-notation frame round-trips and validates) exercise the production
wire path against real frames, including the scientific-notation case that occasioned the line. This is the
**fixture-coverage doctrine, third instance**: a fixture is sovereign for what it CONTAINS and cannot certify a
path its data does not reach (A3's frames could not witness the Decimal→str path; these cannot witness the wire
path).

Labelled in `tests/fixtures/kraken_v2_checksum_captures_wo016.json` `_meta.evidentiary_bounds`:
- `certifies`: *"CHECKSUM MATH — … REGRESSION GUARD ON THE CHECKSUM MATH."*
- `does_not_witness`: *"WIRE RETENTION. … certified ELSEWHERE: … test_wire_string_retention.py bite proofs (a)
  and (c) …"*
Asserted by `test_fixture_present_and_labelled` (CHECKSUM MATH / WIRE RETENTION / the certifying test file).

**Forward action — DONE. The failure-capture machinery (WO-014c-2 §3) now persists `.wire`.**
It previously stored `str(p), str(q)` (line ~1572) — which for a `WireDecimal` still renders scientific
notation via `Decimal.__str__`, so **every future capture would have inherited the same blindness.** Added two
fields to the capture artifact in `_capture_checksum_failure`:

```
"local_book_bids_wire": [(getattr(p, "wire", None), getattr(q, "wire", None)) for p, q in bids[:depth]]
"local_book_asks_wire": [ … asks … ]
```

- The **transmitted text** per level is persisted, so a future live run's captures can witness the wire path
  **end-to-end**: a replay seeds `WireDecimal(wire)` and validates through production with **no reconstruction**.
- A level lacking a wire string is recorded as **`None`** — honest, the blindness stays VISIBLE — **never
  re-rendered** (a silent render here would recreate the exact defect class WO-017 closed).
- The existing `str()` fields are **kept** (the 200-capture regression replays the checksum-math form) and are
  now commented as the rendered/checksum-math view.
- **Guarded:** `test_checksum_failure_capture_has_every_ruled_field` now asserts `local_book_*_wire` is present,
  every level non-`None`, and the top bid equals the frame verbatim `("45283.5", "0.10000000")` — proving it is
  the transmitted text, not `str()`'s render.

## B. The stale constant is no longer a bare authoritative-looking figure

`MEAN_CYCLE_BASELINE_SECONDS = 0.108886` — **annotated** (not removed; your call, annotation is fine):

> test/default seed only; the LIVE gate is HOST-SCOPED and reads the per-host store
> (`config/mean_cycle_baselines.json`), which is authoritative (D28); the runner overrides
> `self._mean_cycle_baseline_s` from it at preflight. **SUPERSEDED as a live figure on 2026-07-21 by WO-017's
> re-baseline (0.107923s, −0.9%, attributed to wire-string retention)** — see the store's `rebaseline`/
> `superseded` ledger. Do NOT read this as the live baseline.

No orphan figure: a future reader hitting `0.108886` in code now sees it is a seed and where the live figure
lives.

## Verification (`evidence/WO-017/verify_followup.txt`)
- Deterministic (`-p no:randomly`): **207 passed** (245.58s). Randomized (`--randomly-seed=20260725`): **207
  passed** (246.54s). 0 failed / 0 xfailed / 0 xpassed both orders.
- **Delta vs the accepted 207:** none in count — assertions were **strengthened** in `test_failure_capture.py`
  (wire fields) and `test_checksum_capture_replay.py` (coverage labels); no tests added or removed.
- `lint-imports` **6/6**; contract **6/6**; `ruff` clean. **No new reason code** (A adds forensic fields, not a
  reason code; B is a comment).
- **Secret scan:** 0 hits. **Venue connection? NO. HTTPS fetch? NO. Prose standing in for output? NO.**
- **Changed but not asked?** Only the four files A+B require: `src/…/kraken_v2_book.py` (wire capture fields +
  constant annotation), `tests/fixtures/kraken_v2_checksum_captures_wo016.json` (`_meta` labels; captures array
  untouched — 200 intact), `tests/integration/test_failure_capture.py` (wire assertion),
  `tests/integration/test_checksum_capture_replay.py` (label assertions + docstring). `instructions.md` carries
  the lead's text (uncommitted, never by me).

---
**STOP for review.** Next by ruling: WO-013 (reason-code emission) → CI capture + version ruling → CI green →
008c → corpus. Did NOT proceed.
