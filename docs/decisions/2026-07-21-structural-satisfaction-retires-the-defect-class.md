# Decision Log: Structural satisfaction retires the defect class (FR-018a(f) literal closure)

**Date:** 2026-07-21
**WO:** WO-017 — FR-018a(f) literal closure (wire-string retention) + first pre-declared re-baseline
**Baseline:** `0463e77` → this WO

---

> FR-018a(f) — checksum input from the venue's transmitted representation, never re-rendered —
> was closed LITERALLY. A3 closed the parse edge and preserved precision; the render edge stayed
> open and produced 234 checksum failures four work orders later. The interim fix made
> re-rendering correct; this makes rendering NON-EXISTENT. The distinction matters: a correct
> renderer is correct for the inputs it was validated against, while a retained wire string is
> correct by construction for every input the venue can send. Where a rule can be satisfied
> structurally rather than behaviorally, structural satisfaction retires the defect class instead
> of patching its instances. The strings were arriving and being discarded at parse the entire
> time; the cost of closure was plumbing, and the cost of NOT closing it was a live 60-minute
> capture's worth of undiagnosed failures.

---

**Mechanism.** `json.loads(parse_float=WireDecimal, parse_int=WireDecimal)` retains each number's
transmitted token text on `WireDecimal.wire`; ladder levels carry the WireDecimal unchanged (the
book never does arithmetic on a level — apply replaces, delete filters, sort reorders, truncate
slices — so the subclass survives from parse to checksum); `_current_ladder_strings` returns `.wire`
exclusively. The no-fallback guard (`CHECKSUM_WIRE_STRING_MISSING`) raises rather than re-render, at
both the parse origin (`_retain_wire`) and the consumption point (`_wire_pair`); the `'E'`-sentinel
(WO-016 D27) stays, now guarding the invariant "no synthesized notation reaches the CRC" rather than
the interim implementation.

**Synthesis proof (§1.5).** Denominator: **2 writers** (`apply_snapshot`, `apply_incremental_update`),
**1 origin** (`_parse_levels` → `_retain_wire`), **0 residual synthesis paths** after the change.
Delete/sort/truncate/reset operate on existing tuples and never create a level's value.

**Cost, measured (§5).** The first pre-declared, legitimate re-baseline, executed inside the WO that
caused the pipeline change: 108.886 ms → **107.923 ms**, delta **−0.963 ms (−0.9%)**, attributed to
wire-string retention replacing the per-level `format(x,'f')` render. The "at what cost" clause is
answered in milliseconds under identical replayed load: **the cost is negative** — a `.wire` read is
cheaper than a fixed-point render. Not material to any gate; real, reproducible, favorable. The old
baseline is retained (never overwritten), end-dated in the ledger; `save_baseline` now accretes
history structurally so the ledger cannot silently drift.

**Related:** [[baselines-attract-scope-errors]] (the LOAD-WORK scope dimension this WO added was that
line's predicted next instance), the WO-008b-A3 parse-edge closure, WO-016's interim render fix.
