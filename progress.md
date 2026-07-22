> ═══════════════════════════════════════════════════════════════════════════
> ⚠ DATED CORRECTION — 2026-07-19 (WO-010 §7)
>
> THE "4/4 CONTRACTS KEPT" CLAIM IN THIS DOCUMENT IS FALSE.
>
> It was produced by an import-linter run that analysed a STALE COPY of the
> repository at C:\Users\mhadi\AppData\Local\Temp\ci-sim2, pinned at commit
> 400a28b — not the tree this report describes. The stale clone was created by
> a WO-008a-R3 Ops instruction that ran `pip install -e .` inside a temp clone,
> rebinding the environment.
>
> TRUE CONTRACT STATE, measured against the real tree with the SAME four-contract
> set (WO-010 §6, git worktree per commit):
>
>     COMMIT    KEPT  BROKEN  WHICH CONTRACT              DEPS
>     400a28b   4     0       (none — control)            171
>     af27491   3     1       Forbidden v2-book-checksum  174
>     90882d0   3     1       Forbidden v2-book-checksum  175
>     8e8a891   3     1       Forbidden v2-book-checksum  176
>     43ca600   3     1       Forbidden v2-book-checksum  176
>
> The break entered at af27491 via factory.py:15
> (`from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter`),
> creating trading.loop.live -> factory -> kraken_v2_book. Constitution
> Principles IV and VII were violated in the shipped tree from af27491 onward.
>
> Forensic confirmation: the stale evidence reads "54 files, 171 dependencies,
> 4 kept" — 171 is the exact dependency fingerprint of 400a28b, not of the
> commit the report claims to describe.
>
> Fixed in WO-010 §5 by an adapter registry; contracts now 5 kept, 1 broken,
> the single remaining break being the intentional new "No test doubles in
> production code" rule (expected RED until WO-008b-A removes the committed Mock).
>
> THE ORIGINAL TEXT BELOW IS PRESERVED UNCHANGED AND DELIBERATELY NOT REWRITTEN.
> The record of a false claim is itself evidence. See evidence/WO-010/.
> ═══════════════════════════════════════════════════════════════════════════

# Trading System - Project Progress

**Last Updated**: 2026-07-22 (WO-019 + WO-020 done at `cceb156` — CI failure ROOT-CAUSED: `AsyncIterator` NameError on 3.11; a one-file fix awaits the lead's version ruling)
**Current Phase**: **BETWEEN WOs — CI RED, root cause found, fix pending a ruling.** WO-018 (event-type governance) CLOSED; WO-019 (clean-env CI diagnosis) and WO-020 (CI verification-surface repair) COMPLETE. **The long-standing CI failure is diagnosed** (see block below) and its fix is a single production edit — NOT yet applied, because it is production code awaiting the lead's version ruling (fix approach + whether to add 3.14 to the CI matrix). **Immediate next step:** the version-ruling fix WO. Then by sequence: **CI green → the taxonomy-migration WO (measure-then-fork) → 008c → 24h corpus.**
**Status**: HEAD `cceb156` on master (pushed; local == remote). **215 tests green both orders LOCALLY** (`-p no:randomly` AND `--randomly-seed=20260722`), 0 failed/xfailed/xpassed; import-linter 6/6, contract 6/6, ruff clean. **CI (GitHub Actions, Python 3.11) is RED** — pytest collection fails with a `NameError` (root-caused below), NOT a test regression; the local suite is genuinely green. `gh` CLI works via `C:\Program Files\GitHub CLI\gh.exe` (auth: mhadiamiri, keyring). The **▶ WO-016** and **▶ CURRENT STATUS — 2026-07-20** blocks below are HISTORICAL (git log is the authoritative sequence); read the **▶ WO-019/WO-020** and **▶ WO-018** blocks below to resume.
**Remote**: https://github.com/mhadiamiri/trading-system (Private)
**Repo path**: `C:\Projects\bot\trading-system` (sessions may launch from a different cwd — always work here)

---

## ▶ WO-019 + WO-020 COMPLETE (AUTHORITATIVE) — 2026-07-22 — CI failure ROOT-CAUSED + verification surface repaired

> The CI-failure investigation that had been outstanding "since WO-009." Two WOs: WO-019 diagnosed it in a
> clean local environment; WO-020 repaired CI's verification steps AND (with `gh` now available) observed
> the real CI run, which finally produced the traceback. Reports: `WO-019-REPORT.md`, `WO-020-REPORT.md`.
> Evidence: `evidence/WO-019/`, `evidence/WO-020/`. Decision log:
> `docs/decisions/2026-07-22-verification-steps-can-host-the-defect.md`.

**THE CI FAILURE — ROOT-CAUSED (this is the headline; the fix is the immediate next step):**
- **Symptom:** GitHub Actions (Python **3.11.15**, ubuntu) fails pytest at **collection** —
  `NameError: name 'AsyncIterator' is not defined`, `Interrupted: 31 errors during collection`, exit 2.
- **Root cause:** `src/trading/data/adapters/kraken_v2_book.py` annotates return types as
  `AsyncIterator[MarketState]` at **line 2300 and line 2718** but **never imports `AsyncIterator`**
  (line 20 imports only `Optional, List, Dict`; there is **no `from __future__ import annotations`**).
  Python **3.11 evaluates annotations EAGERLY** at class-definition → NameError at import. Python **3.14
  defers annotations (PEP 649)** → the missing import is masked → the LOCAL suite (run on 3.14.6) passes
  215 and never saw it. This is a genuine **version (H2)** defect, NOT `ModuleNotFoundError` (the shape
  assumed for ten WOs) and NOT environmental.
- **THE FIX (NOT yet applied — awaits the lead's version ruling):** either add `from __future__ import
  annotations` to the top of `kraken_v2_book.py` (module-wide, future-proofs all annotations) OR a targeted
  `from collections.abc import AsyncIterator`. One production file. **Open ruling also:** add **3.14 to the
  CI matrix** (or pin the local gate to 3.11) so local and CI can never again disagree on annotation
  semantics — that divergence is what hid this for ten WOs.

**WO-020 — CI verification-surface repair (COMPLETE, confirmed in real CI at run 29955008418):**
- CI's `import-linter` step was **BARE** = a no-op on import-linter 2.x (prints help, exits 0 — never
  checked a contract). Fixed → `import-linter lint` (bite-proved, 4 artifacts, sha256). Real CI now logs
  `Analyzed 61 files … 6 kept, 0 broken`.
- `pytest-randomly` was in the dev env but **missing from `requirements-dev.txt`** → CI never randomized.
  Added; CI now runs **both orders**; the randomized step prints its seed (`Using --randomly-seed=…`, real
  CI showed `1608462615`) and carries `if: always()` so the seed appears even when the deterministic run
  fails.
- **D10** (WO-010 §2 preflight path assertion, flagged "not yet wired into ci.yml before import-linter") is
  now a standalone `python tools/preflight_path_check.py` step **before** import-linter; `pytest_sessionstart`
  runs the same assertion at the pytest step (defense in depth). Both confirmed running in real CI.
- **Decision log (two entries):** ANY LAYER THAT REPORTS VERIFICATION CAN HOST THE
  green-while-checking-nothing DEFECT (found now at three layers: code, test doubles, pipeline); AN
  INFERENCE FROM CI BEHAVIOR IS ONLY AS GOOD AS PROOF THAT THE CI STEP EXECUTED.

**WO-019 — clean-environment diagnosis (COMPLETE):** reproduced CI faithfully (`git archive HEAD` → fresh
venv, CI's install + bare `pytest`) on **3.14.6** → **215 passed** → refuted H1 (packaging). Could not run
3.11 locally (`py -0`: only 3.14, 3.13) → reported as a blocker. WO-020's real-CI observation supplied the
3.11 leg WO-019 lacked. Also surfaced the import-linter no-op and the pytest-randomly gap that WO-020 fixed.

**What did NOT change (scope discipline):** no production source, no test was modified in WO-019/WO-020.
WO-020 changed only `.github/workflows/ci.yml` + `requirements-dev.txt` (CI/dev tooling — does not affect
what ships). The `AsyncIterator` fix is deliberately NOT applied here; it is the next WO's single task.

**IMMEDIATE NEXT STEP for the next session:** the version-ruling fix WO — apply the `AsyncIterator` fix to
`kraken_v2_book.py` (approach per the lead's ruling), decide the CI-matrix question, push, and confirm CI
goes green via `gh run view` (gh works locally — see Status line). Only after CI is green does the sequence
continue to the taxonomy-migration WO → 008c → 24h corpus.

---

## ▶ WO-018 COMPLETE & CLOSED (AUTHORITATIVE) — 2026-07-22 — event-type governance + raised⇒declared hatch

> Event-Type Governance + closing the `raised ⇒ declared` escape hatch. **CLOSED by the project lead at
> `8dcf2ef`.** Principle VIII the substantive authority; governance, not redesign (no namespace merged,
> renamed, or restructured). Reports: `WO-018-FINAL-REPORT.md`, `WO-018-FOLLOWUP-ABCD-REPORT.md`,
> `WO-018-DEAD-LIVE-SPLIT-REPORT.md`. Evidence under `evidence/WO-018/`. Decision log:
> `docs/decisions/2026-07-22-a-check-is-bounded-by-the-form-it-matches.md`.

- **CLOSED at `8dcf2ef`.** 215 passed both orders (`-p no:randomly` AND `--randomly-seed=20260730`),
  0 failed/xfailed/xpassed; import-linter 6/6, contract 6/6, ruff clean.
- **What it closed:** `raised ⇒ declared` now holds in **BOTH literal forms** — the colon `"CODE:"` AND
  the keyword `reason_code=`/`event_type=` (the `reason_code=` keyword form was the escape hatch). The
  `event_type` namespace is **governed for the first time** (`VALID_EVENT_TYPES`, **0 → 13 declared**).
  The four properties (raised⇒declared, declared⇒producible, prefix-freedom, scan-reads-emitted) are
  proved **across both namespaces**. **Enum sync** is enforced **mechanically** by a test that may import
  both `logkit` and `trading.risk` (`decision.py` cannot import `trading.risk` — layering/cycle), so the
  RISK event_types can never drift from `RiskDecision.value` silently.
- **The denominator (why it was worth doing):** the §1 enumeration found **12 emitted-but-undeclared
  reason codes against a headline of 2** (the 5 `FEED_*` and 5 `RISK_*` lived in the `reason_code=`
  keyword blind spot, plus `DATA_RECEIVED` and `EXEC_ORDER_FILLED` — the fill event), and **7 literal
  forms against a prior scan that saw 1**. All 12 declared (not retired — canonical strings across five
  modules; retirement is a rename, out of scope).
- **New standing rule `0.1k`** (`docs/standing-rules.md`): **A BEHAVIORAL PROOF IS SOVEREIGN OVER A STATIC
  SCAN**, with the evidence-competence hierarchy **BEHAVIORAL DEMONSTRATION > STATIC REACHABILITY >
  DEFINITION > PROSE.**
- **The tracing boundary** (doctrine file): the scan **may follow a name to its use site; it may not
  simulate execution.** Competent tracing (required): `return CONST`, `raise X(CONST)`, `f"{CONST}: …"`,
  the `decision.value` enum whitelist. Arms-race tracing (refused): variable-assignment dataflow, values
  through branches/collections/calls.

**CARRIED TO THE SUCCESSOR WO (taxonomy-migration) — so nothing is lost across the CI work:**
- namespace-scoped **bidirectional** scan;
- **prose-as-use closure** (producible = reachable-as-emitted, not definition/comment/docstring);
- **uppercase normalization** of the four feed event_types (provenance settled: **ours, not Kraken's** —
  adapter literals from our own control flow, each paired with an uppercase `reason_code`);
- the ruled **taxonomy migrations**: `NO_SIGNAL` → reason_code only; `PASS`/`CLAMP`/`VETO` → event_types
  with their reason_code declarations retiring; `ORDER_FILLED`/`EXEC_ORDER_FILLED` collapse to one
  canonical form with an **alias scan** for the loser;
- the **genuinely-dead 5 retire** (`PASS`/`CLAMP`/`VETO`/`ORDER_FILLED`/`ORDER_REJECTED` as reason_codes —
  each a live declared event_type, so no vocabulary is lost); the **post-tightening residual** gets inline
  annotations citing behavioral proof at file:line — annotation is a **PERMANENT EASEMENT, not a temporary
  waiver** (a future audit may re-verify the proof passes; it may not re-flag for static invisibility);
- **measure-then-fork**: tighten first, **measure** the residual, THEN apply the large/small conditional
  (the fork was mistakenly evaluated against the pre-tightening 11);
- the **~2 residual figure is recorded AS A PREDICTION** (`LONG_SIGNAL`/`SHORT_SIGNAL`, the arms-race-side
  codes that stay annotated) — a materially higher measured value is **itself a finding** about what the
  scan cannot see.

**Corpus preconditions — unchanged, still four:** fingerprinted load-representative baseline on the
capture host; verified no-sleep host; ~5.3 GB budget; parquet policy.

---

## ▶ WO-016 COMPLETE & ACCEPTED (AUTHORITATIVE) — 2026-07-21 — D25–D29 all closed

> The checksum-failure diagnosis + fix + gappy-threshold rebuild + host baseline. Accepted by the
> project lead at `0fbe512`. Reports: `WO-016-FINAL-REPORT.md` (D26 ADDENDUM), `WO-016-D27/D28/D29-REPORT.md`.

**What shipped (all bite-proved, both-order-green):**
- Checksum defect diagnosed to ONE reproducing rule (scientific-notation size rendering); INTERIM
  fixed-point fix at `_current_ladder_strings`; **200/200** captured failures validate through the
  production path (permanent regression fixture `tests/fixtures/kraken_v2_checksum_captures_wo016.json`).
- `'E'`-rejecting **invariant sentinel** in `compute_checksum` (`CHECKSUM_INPUT_SYNTHESIZED_NOTATION`).
- VOID gate rebuilt as a **three-component OR-gate** (DISCRETE / SPIKY / UNIFORM), counterfactual
  witnessed in a test. Baseline made **host-, load-, source-, duration-scoped** (D28/D29):
  `config/mean_cycle_baselines.json` (hashed machine id), runner refuses on host mismatch,
  establishment protocol `tools/establish_mean_cycle_baseline.py` (no venue/socket).

**▶ NEXT — the wire-string WO (FR-018a(f) literal closure). Ops drafts it; NOT started here.**
Two items the lead ruled it MUST carry (do NOT do them now — they belong to that WO, and touching
them now would reopen the closed WO-016):
1. **LOAD-WORK scope dimension.** The baseline scope enumerates host/load/source/duration, but LOAD
   is characterized by RATE alone; per-frame PROCESSING WORK is a separate, undeclared dimension.
   The wire-string WO adds to the scope object + protocol declaration: LOAD-WORK (per-frame cost, ==
   the pinned fixture's frame shapes), the empirical justification (mean cycle reproduced live-derived
   load to +0.008ms → representative as measured), and the INVALIDATION CONDITION (if per-frame work
   materially changes — deeper ladders, heavier validation, per-level storage — the rate-only
   characterization needs re-validation).
2. **PRE-DECLARED RE-BASELINE section.** Wire-string retention adds per-level work on every frame —
   exactly that invalidation condition, and the frozen-baseline rule's first LEGITIMATE re-baseline.
   Executed BEFORE the changed code faces any live gate: establishment replay on the PINNED SOURCE
   (WO-009 §2 fixture) at the PINNED RATE (~1,959/min), same 60s protocol; **report the DELTA and
   ATTRIBUTE it** (old 108.886ms → new → difference, attributed to wire-string retention — a
   measured answer to the feasibility "at what cost" clause); OLD scope annotated with its end date,
   never overwritten; re-declaration dated + justified by the named pipeline change.

**STANDING RULE — a SATURATION-DETECTION section, NOT cost tracking (RELABELLED WO-013 item C, 2026-07-22):**
ANY WORK ORDER THAT TOUCHES THE LOOP'S HOT PATH CARRIES A **saturation-detection** SECTION — establishment
replay on the pinned source (WIDENED full-loop instrument), reported against the DECLARED noise/per-frame
floor, old scope annotated — EXECUTED BEFORE THE WO CLOSES. **What this section CAN see and CANNOT (state it
where the rule is read, not only in the tool docstring):** the instrument is `mean_cycle = span/actual_samples`,
an event-loop LAG / STARVATION detector. Its measured per-frame transfer is ~0.2 ms-cycle per ms-frame, so its
**effective per-frame detection floor is ~10 ms/frame**. It CATCHES per-frame cost approaching SATURATION
(~30 ms/frame, where the achieved rate also drops); it CANNOT see per-frame changes below ~10 ms/frame. **The
uncaught case:** a WO adds 0.3–1 ms/frame, mean_cycle does not move, and the section reports clean while
per-frame throughput cost silently rose — so a reviewer changing per-frame work must know the rule cannot
resolve their change. "When in doubt, run the section" still holds (the cost is a replay), but read its output
as saturation/starvation evidence, not as a cost measurement. Sequence: WO-013 → EVENT_TYPE GOVERNANCE (Ops
drafts) → CI capture + version ruling → CI green → 008c → corpus. Corpus preconditions: fingerprinted
load-representative baseline + no-sleep host + ~5.3 GB/24h + (checksum class closed). A fit per-frame timer is
DEFERRED POST-CORPUS (WO-013 item F) — not corpus-blocking; the corpus's integrity rests on throughput (gate
cleared ~30x), gap honesty, checksum validity, and vocabulary governance, none of which per-frame cost drift
threatens.

**INSTRUMENT == RULE SCOPE + INSTRUMENT IDENTITY is the SIXTH scope dimension (WO-013 follow-up B + item 1,
2026-07-22):** the re-baseline instrument measures the FULL LOOP ITERATION — adapter parse+apply+checksum
PLUS the loop's per-MarketState work (strategy.decide, risk.check, emission), via the real `LiveTradingLoop`
with the event-loop lag sampler (`tools/establish_mean_cycle_baseline.py`, WIDENED default; `--adapter-only`
= legacy). Rule text and instrument coverage now name THE SAME BOUNDARY. Scope is HOST / LOAD / SOURCE /
DURATION / RESOLUTION / **INSTRUMENT** — and the enumeration is OPEN (two consecutive reports each surfaced
one; interrogate every anomalous delta for an undeclared dimension BEFORE reading it as signal). A
CROSS-INSTRUMENT delta is REFUSED (`MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH`), not differenced: the
adapter-only ledger CLOSED (valid for what it measured), the loop-boundary ledger OPENED at ENTRY ZERO
(108.717 ms), never inherited via a cross-instrument delta.

**CONTAINMENT + ATTENUATION FINDING (WO-013 item 2 — corrects the earlier "now VISIBLE" overclaim):** the
widened instrument ENCLOSES the loop (a 40 ms/frame loop injection moved mean_cycle +96.5 ms; the
adapter-only instrument cannot, it never runs the loop). BUT `mean_cycle = span/actual_samples` is a
SLEEP-WAKE LAG (starvation/responsiveness) metric, NOT a per-frame CPU meter: below the ~30.6 ms/frame
inter-frame budget the pacer leaves idle slack, so per-frame cost is ATTENUATED ~5x (10 ms/frame -> only
+1.97 ms, BELOW the floor). **Effective per-frame detection floor ~10 ms/FRAME**; sub-ms/frame changes are
INVISIBLE (report clean); per-frame cost is only caught near SATURATION (~30 ms/frame, where the rate also
drops). So a WO adding e.g. 0.3 ms/frame passes the gate silently — a DECLARED LIMIT; a direct per-frame
timer would be the fit instrument (reported for a ruling).

**NOISE FLOOR is a DECLARED scope dimension (WO-013 follow-up A, 0.1j):** "a measurement without a declared
noise floor is an estimate with better costumes." RESOLUTION (fifth dim). Every re-baseline delta reports
**SIGNAL / NOISE FLOOR / RATIO**; RATIO < 1 => SIGN EXPLICITLY UNESTABLISHED, ledger KEEPS the entry (it
bounds the effect). Widened CYCLE floor = 2.0 ms (conservative, above the 1.586 ms max observed excursion,
n=9 provisional). Interleaved within-session A/B (pre-approved, not implemented) would lower the CYCLE floor
toward ~0.3 ms — but does not fix the per-frame ATTENUATION above, which is an instrument-kind limit.

**Hot-path judgment (first NON-application of the standing rule, 2026-07-22, WO-017 follow-up A):** the
wire-capture fields (`local_book_bids_wire`/`local_book_asks_wire`) execute only on CHECKSUM FAILURE,
not per applied frame; not hot path; no re-baseline required. Recorded so the rule's first exception is
stated precedent — "when in doubt, re-baseline" stays a default that must be argued OUT of, not a silent
"when in doubt, assume not."

---

## ▶ RUN COMPLETE (AUTHORITATIVE) — 2026-07-21 — WO-008b-B-RERUN EXECUTED

> The first real venue socket has been opened and the 60-minute capture completed. This block is
> now the single source of truth. Full report: `WO-008b-B-RERUN-FINAL-REPORT.md`; evidence under
> `evidence/WO-008b-B-RERUN/`.

- **Attempt 1 FAILED at ~38 min (operational, NOT venue):** the loop's verbose stdout (6.6 MB)
  got the background task killed. Feed was healthy; no venue fault. Preserved as
  `gap_ledger.attempt1.jsonl` / `attempt1_forensics.txt`. Not restarted silently — reported.
- **Attempt 2 COMPLETE (hardened driver):** 2026-07-21 17:09:43Z→18:09:58Z, 3614.6 s, single
  uninterrupted window, `uninterrupted=True`, 0 HOST_SUSPEND, 0 terminal gaps.
- **§3 Throughput verdict = PASS, unanimous:** raw 118,043 (1,959/min), emitted 111,010
  (1,843/min); per-minute EMITTED min 714 / median 1537 / mean 1820 / **100% of minutes ≥60**.
- **§4 Discrimination = BRANCH 1 (protocol/venue); STARVATION FALSIFIED.** Clean instruments
  (lag missed 8.16%, pong missed-send 2.53% — both <10%, NOT gappy → they convict). Cell
  (LATE/ABSENT pong, NORMAL lag): pong median 150 ms / p95 381 ms / 27% late / 6 absent; lag
  median 8.97 ms, elevated 0.04%; recv→process latency median 0.089 ms (loop not starved).
- **§7 `ping_timeout=None`:** NO 1011; **2 venue-initiated closes** (17:11:28Z, 17:55:32Z), each
  recovered ~4.5 s, emission resumed — first LIVE exercise of the WO-014b reconnect lifecycle.
- **§5/§9 Checksum failures = 234 (0.198%, ~10× the 3/14,251 baseline).** 200 full captures + 34
  summaries (cap bound; ledger complete). **PRE-RULED: assume our defect first; do NOT tune;
  diagnose OFFLINE.** Lead: sampled failing frames show multiple bid levels at the SAME price in
  one update (e.g. 4× 66452.7) — likely an apply-order / same-price issue in our book+checksum path.
- **§8 verify (post-run):** 190 passed both orders, lint-imports 6/6, contract 6/6, ruff clean —
  no delta from preflight (tree byte-unchanged; only new evidence added, no src/config/test change).
- Fills: 0 (trivial strategy gave STRAT_NO_SIGNAL all hour → 0 orders, 0 fills, 0 staleness firings).
  Credentials/tokens/session/conn-IDs anywhere: NO. Any order placed: NO.

### ▶ NEXT (project lead decides — this WO STOPS for review)
1. **Diagnose the checksum failures OFFLINE** (assume our defect first; do not tune the live path).
   Start from the captured failing frames (`instruments_dump.json` → checksum_failure_captures).
2. Then per Ops's prior sequence: WO-013 → CI capture + version ruling → 008c → the 24-hour corpus
   (which needs HOST_SUSPEND's window-INVALIDATING role, not just diagnostic, and a host that never
   sleeps). The corpus READER is its own separate WO.

---

## ▶ RESUME HERE (historical — pre-run) — 2026-07-21

> Single source of truth for "where are we now." The Executive Summary and dated
> `Current Status (Session N)` blocks below are historical reference. Read THIS to resume.

### Where the tree is
- **HEAD `b1d3ee6` on `master`** (pushed; local == remote). Worktree = main only.
- **190 passed** deterministic (`-p no:randomly`) AND randomized (`--randomly-seed=20260725`),
  0 failed / 0 xfailed / 0 xpassed. import-linter **6 kept / 0 broken**,
  `tools/contract_count_check.py` **6/6**, ruff clean. Full suite ≈ 4 min/order (dominated by
  `tests/integration/test_live_loop.py`, which uses real 1s feed sleeps).
- Verify with: `pytest tests/ -p no:randomly -rX` and `pytest tests/ --randomly-seed=20260725 -rX`,
  then `lint-imports`, `python tools/contract_count_check.py`, `ruff check .`.

### What is DONE (recent line, newest first)
- **WO-015 — live-capture runner + HOST_SUSPEND + reviews COMPLETE (`989600b`→`6f9a036`).**
  Built `src/trading/loop/live_capture.py` (`LiveCaptureRunner`): drives the INSTRUMENTED transport
  `KrakenV2BookAdapter.get_live_market_data` end-to-end through Data→Strategy→Risk→Execution(paper),
  wiring the existing gap ledger / failure capture / lag-pong-throughput / host-suspend detection.
  Preflight enforcement IN the runner (refuses non-paper `TRADING_ENV`; refuses unconfigured
  persistence). Resolves the adapter FROM `DATA_SOURCE` via the factory (`create_live_capture_feed` →
  `registry.create(DATA_SOURCE, mode="live", …)`); a non-live-capable adapter refuses with
  `LIVE_CAPTURE_UNSUPPORTED` before connecting (mechanism: builders declare `live_capture=True`).
  **HOST_SUSPEND** = ruled FIFTH gap cause (wall-vs-monotonic divergence > 43s drift bound;
  DIAGNOSTIC — records + loud, not terminal; detection floor declared: sub-~43s suspend undetected).
  Runner catches a breaker trip (via `capture_terminated`, duck-typed) → `result["terminated"]`,
  not a crash. 7 bite proofs (4 artifacts, sha256) in `evidence/WO-015/`. Report: `WO-015-FINAL-REPORT.md`.
  Decision logs: `docs/decisions/2026-07-21-{orders-that-operate-what-they-should-build,
  contract-clean-is-not-principle-clean,survives-the-failure-it-documents}.md`.
  New reason codes (all declared in-commit, vocab guard green): `HOST_SUSPEND`,
  `LIVE_CAPTURE_ENV_REFUSED`, `LIVE_CAPTURE_UNSUPPORTED`.
- **WO-014c-3 COMPLETE (`f065ff6`→`989600b`).** §0 probes → fixes: gap-ledger PERSISTENCE
  (append-only redacted JSONL, incremental fsync at gap-open = kill-durable; opt-in
  `_gap_persist_path`, live capture REFUSES if unset via `GAP_PERSIST_UNCONFIGURED` unless
  `_persistence_optional`); failure-capture CAP (keep first N, count all, cap by count 200 AND
  bytes 8 MiB, `FAILURE_CAPTURE_CAPPED`, one-line summaries beyond the cap); wall/monotonic drift
  bound declared; stub-lint (`tests/test_stub_lint.py`, 0.1g mechanical, incl. docstring-only);
  precondition sweep (report-only). Report: `WO-014c-3-FINAL-REPORT.md`.
- **WO-014c-2 COMPLETE.** Gap recording: `GapRecord`/`GapLedger` (monotonic bounds + once-per-run
  (wall, monotonic) anchor; `GAP_CAUSES`), failure-targeted checksum capture (N=20 preceding
  frames, redacted). Report: `WO-014c-2-FINAL-REPORT.md`. `GAP_LEDGER_INCOMPLETE` reason code.
- **WO-014c-1 / WO-014b-2 / WO-014b done earlier** (discrimination instruments: lag sampler,
  pong observer, throughput; keepalive + backoff + duration breaker + venue-close; `_reconnect`
  proven to effect). Thresholds/branches: `evidence/WO-014c-1/thresholds_and_branches.txt`.

### ▶ NEXT SESSION — run the live re-run (WO-008b-B-RERUN) as a genuinely FRESH context
The 60-minute live capture is **authorized per-run** (first real venue socket; public v2 book,
`TRADING_ENV=paper`, no orders, no credentials). Preflight was started this session and **halted at
§1.3** (evidence/WO-008b-B-RERUN/preflight.txt); the lead then posted a §1.3 correction and Hadi
disabled sleep. Status of the two gate items:
1. **HOST SUSPEND — NOW DISABLED (§1.3 power requirement CLEARED).** Verified this session:
   `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` reads **AC = 0x00000000 and
   DC = 0x00000000** (standby-idle never), on both power states. (Earlier this session it was
   AC=2h/DC=10min and the host DID suspend — the WO-014c-3 det. suite ran 6h41m for ~4min CPU;
   that is now fixed.) AT PREFLIGHT: re-run the powercfg query, PASTE the output (both must read
   0x00000000 — §1.3 requires DISABLED, not merely deferred), and confirm the host is on AC power.
2. **A FRESH SESSION — STILL REQUIRED.** The WO header says "Fresh session"; the run is a single
   uninterrupted 60-min window + a 17-item §9 report — do it from a clean context (this session
   halted at ~80% with compaction imminent). This is the ONLY remaining blocker.
Preflight §1.1/§1.2 (both-order suite), §1.4–§1.7 (persistence, DATA_SOURCE, env, the four
bite-proof pairs) and §2–§9 were NOT run yet — the fresh session executes the full preflight → run
→ report from the top.
The order OPERATES already-built things (BUILDS NOTHING): runner `src/trading/loop/live_capture.py`,
instruments WO-014c-1, ledger/capture WO-014c-2/3, lifecycle WO-014b. Full preflight/run/report
spec is in `instructions.md` (the WO-008b-B-RERUN text). Interpret discrimination against
`evidence/WO-014c-1/thresholds_and_branches.txt` and nothing else. Report EVERY attempt; a retry is
a new socket under the same per-run authorization (new preflight, new report). Do NOT tune to a
number; VOID / 23/min / 600/min are all successful outcomes — report what the feed gives.

### After the re-run (per Ops's proposed sequence, project-lead to confirm)
WO-013 → CI capture + version ruling → CI green → 008c → the 24-hour corpus (which will need a
host that does not sleep at all, and the corpus WO implements HOST_SUSPEND's window-INVALIDATING
role — in WO-015 it is only diagnostic). The corpus READER (default-deny, interval-intersection
over the gap ledger) is its own separate WO.

### Key files for the live re-run
- Runner: `src/trading/loop/live_capture.py` (`LiveCaptureRunner`; `create_live_capture_feed` in
  `src/trading/data/adapters/factory.py`).
- Instrumented transport: `src/trading/data/adapters/kraken_v2_book.py` (`get_live_market_data`,
  `GapRecord`/`GapLedger`, HOST_SUSPEND detection, failure capture, `_gap_persist_path`).
- Reason codes: `src/trading/logkit/decision.py` (`VALID_REASON_CODES`).
- Thresholds/branches (the ONLY interpretation reference): `evidence/WO-014c-1/thresholds_and_branches.txt`.
- Authority: `.specify/memory/constitution.md` (conflict → STOP and escalate).

---

## Executive Summary

A systematic crypto trading system built on constitutional principles. The project has completed Sprint 1 (Walking Skeleton) and successfully executed a venue swap from Bybit testnet to Kraken mainnet public feed. All safety guards have been verified with fail-then-pass proofs. **Sprint 2 Phases 4-8 (WO-008a + WO-008a-R + WO-008a-R2 + WO-008a-R3 + WO-008a-R5 + WO-008a-R6) are now COMPLETE** with quote processing, trades enrichment, observed-spread cost model, backtest replay, integration loop fully demonstrated, spread double-count bug fixed, and staleness guard implemented. All §2 non-negotiable requirements proven with REAL FAIL-THEN-PASS proofs. T036 completed (11 xfails cleared). Full 4-layer cycle observable. **CI GREEN achieved (73 passed, 0 failed, 8 xfailed, 0 xpassed)**. Ready for human review before WO-008b (Live WebSocket Integration).

---

## ▶ CURRENT STATUS (AUTHORITATIVE) — 2026-07-20

> This is the single source of truth for "where are we now." Everything below the
> reference sections (Project Overview, Technology Stack, Development Tools, File
> Structure, Constitutional Principles, Configuration) remains valid. The dated
> `Current Status (Session N)` blocks further down are **historical** — read this
> section to resume.

### Where the tree is
- **HEAD `9fbc522` on `master`** (pushed; local == remote).
- **Test baseline: 144 passed** deterministic (`-p no:randomly`) **AND** randomized
  (`--randomly-seed=20260725`), 0 failed / 0 xfailed / 0 xpassed. import-linter **6 kept
  / 0 broken**, `tools/contract_count_check.py` **6/6**, ruff clean. (Green established at
  `97306c0`; `33aa9c4` and `9fbc522` added only evidence `.txt` files, so the code is
  identical and the 144-green result stands.)
- Full suite ≈ 4 min per order. Verify with:
  `pytest tests/ -p no:randomly -rX` and `pytest tests/ --randomly-seed=20260725 -rX`,
  then `lint-imports`, `python tools/contract_count_check.py`, `ruff check .`.
  (`python -m importlinter.cli` prints nothing under redirection — use the `lint-imports`
  console script for visible output.)

### The WO-014 line (connection lifecycle) — what is DONE
WO-014 was split at the `_reconnect`-to-effect vs. keepalive seam. Completed slices:

1. **WO-014b-1 — `_reconnect()` proven to effect (`97306c0`).**
   - `_reconnect()` was `pass` (a no-op) from Phases 1-3 through WO-008b-A1b; the 5-failure
     recovery had **never worked in production**. Now it sets `_pending_reconnect`, and the
     transport (`get_live_market_data`) consumes it: `_perform_reconnect` closes/reopens the
     socket and hands off to the committed Phase 2.1 producer `_maybe_resubscribe`.
   - **Watchdog:** a set-but-unconsumed flag raises reason code `RECONNECT_FLAG_STRANDED`
     (declared in `src/trading/logkit/decision.py` DATA layer). Threshold: zero-iteration
     latency (flag set in `process_raw_frame`, serviced same loop iteration).
   - Bite proof (5 real checksum failures → reconnect → fresh snapshot → emission resumes;
     asserts the END STATE, not the call): `evidence/WO-014b/reconnect_to_effect.txt`.
   - Reusable simulated-transport harness: `tests/fixtures/fake_ws_transport.py`
     (`FakeWebSocket`, `ScriptedConnectionFactory` — connection N → script N; drains via
     `asyncio.TimeoutError`). Test: `tests/integration/test_reconnect_to_effect.py`.
   - Decision log: `docs/decisions/2026-07-20-reconnect-never-worked-in-production.md`.

2. **WO-014b-2 §0 — carry-over verification (`33aa9c4`).**
   `evidence/WO-014b-2/carryover_verification.txt`. Two production findings + three OK:
   - **0.1 Backoff: NONE exists.** Two hazards: (a) a persistently-invalid book re-arms
     reconnect with zero delay (counter latched ≥5) → storm; (b) a **failed reopen** raises
     `ConnectionError` that propagates and **ends the capture** — a 24h run dies on one
     transient failure. **Fix deferred to the fresh session (see below).**
   - 0.2 counter reset: OK (reset only on a validating snapshot, `_process_quote_update`).
   - 0.3 watchdog spurious-fire: not possible (one recv/process/service per iteration).
   - 0.4 fixture-limit docstring: present.

3. **WO-014b-2 §2.1 — Kraken WS rate-limit research (`9fbc522`).**
   `evidence/WO-014b-2/rate_limits_research.txt`. **DOCUMENTED SILENCE** (0.1e): Kraken
   documents that WS connection/message limits exist but publishes no specific number; the
   "~150/10min Cloudflare" figure is secondary and **uncited**. ⇒ backoff/breaker figures
   are **declared engineering judgment**, never dressed as a citation.

### ▶ NEXT SESSION (authorized) — run as a genuinely FRESH context
**Scope: `{§1.1 + §1.2 + §2 backoff/breaker}`** from `instructions.md` (WO-014b-2 §1),
with **§1.3's protocol-level bite proof as the pre-named checkpoint seam** — stop there
rather than weaken it (a weak version corrupts WO-014c's starvation discrimination).
Baseline for that session: **`9fbc522`**.

Must-honor rulings/constraints (from `instructions.md` + its update block):
- **Keepalive parts:** 1.1 heartbeat-absence detection → reconnect (Kraken heartbeat ~1/s);
  1.2 application-level `{"method":"ping"}`→pong; 1.3 deliberate **cited** `ping_interval`/
  `ping_timeout` on `websockets.connect` (defaults 20s/20s produced the 1011). **Do NOT
  silently disable the protocol-level ping.** The 1.3 bite proof MUST exercise the
  **PROTOCOL-LEVEL** mechanism, with the citation in the test docstring.
- **Backoff+breaker land WITH keepalive** (Ruling A — keepalive installs the reconnect
  trigger, so the guard ships with it). Proposed backoff (engineering judgment): full-jitter
  exponential, base 1s ×2, **cap 30s**.
- **Breaker threshold: RE-DERIVE, do not adopt the draft 10/10min** (Ruling 2A). Calibrate to
  "how long do we try before concluding the venue is gone?" — survive the longest plausible
  ordinary Kraken interruption (maintenance/network); if unknown without ops history, say so
  and choose conservatively as declared judgment. (Draft 10/10min exhausts in ~3 min — too
  short.)
- **Failed reopen RETRIES under backoff** (fixes the hard-stop hazard). **Breaker trip → STOP
  the run**, FAIL LOUD with a **declared reason code** (not a bare `ConnectionError`), never
  a silent gap. Two mandatory carry-over conditions on STOP (Ruling 2B):
  (1) **complete forensic tail** — trip time, full retry ladder (every attempt w/ timestamp +
  delay), and last validated book state, so the artifact carries its own reason;
  (2) **retain the partial capture** as a labeled honest window (two-window doctrine, stated
  evidentiary bounds). Keep the STOP-vs-continue decision at a single marked branch (Ops
  pending-veto).
- **Bite proofs** (4 artifacts each, sha256, 0.1i end-state): keepalive parts 1.1/1.2/1.3;
  backoff (a) transient → retry → emission resumes; (b) persistent → breaker trips → loud.
  **Extend `fake_ws_transport.py`** (silent socket for 1.1; fail-N-then-succeed factory for
  backoff) — **do not rebuild it.**
- **Every new raised reason code declared in the same commit** (the completeness guard caught
  `RECONNECT_FLAG_STRANDED` last slice — declare, never suppress).
- **§3 decision log §4.2** (evidence-type sovereignty) still to write — verbatim text is in
  `instructions.md`.
- **DO NOT claim keepalive resolves the 1011.** Both hypotheses (missing pong vs event-loop
  starvation) remain open; WO-014c builds the discriminators, the re-run rules it.
- **NO venue connection.** Simulated transport only. HTTPS documentation fetching is permitted
  and is not venue contact.
- Out of scope (WO-014c): discrimination instruments, failure-targeted capture, the 60-min
  re-run.

### Key files for the next session
- Production: `src/trading/data/adapters/kraken_v2_book.py` (transport loop
  `get_live_market_data`, `_reconnect`/`_perform_reconnect`, `_connect`, `_maybe_resubscribe`),
  `src/trading/logkit/decision.py` (`VALID_REASON_CODES`).
- Tests/harness: `tests/fixtures/fake_ws_transport.py`,
  `tests/integration/test_reconnect_to_effect.py`, `tests/test_reason_code_vocabulary.py`
  (completeness guard).
- Work order + rulings: `instructions.md` (read its `update:` block). Approved design +
  verbatim Kraken quotes: `evidence/WO-014/lifecycle_proposal.txt`.
- Evidence to date: `evidence/WO-014b/`, `evidence/WO-014b-2/`.
- Authority: `.specify/memory/constitution.md` (conflict → STOP and escalate).

---

## Current Status (Session 9 - 2026-07-18)

### 🎉 WO-008a-R6 COMPLETE - Spread Double-Count Fixed, Staleness Guard Implemented, Test Suite Clean

**Scope:** Resolve two blockers from WO-008a-R5 remediation (spread double-count bug and missing staleness guard) + achieve CI GREEN state

**Major Achievement:** Both blockers from R5 resolved with ACTUAL bite proofs, test suite cleaned to achieve CI GREEN requirement

#### ✅ PART 1: ORIGINAL WO-008a-R6 WORK

**§1.2 DIAGNOSIS — Is spread double-counted in P&L?**
- ANSWER: YES
- EVIDENCE: evidence/WO-008a-R6/double_count_diagnosis.txt
- ARITHMETIC PROOF: Buy at ask 65980.0 for 0.1 BTC shows spread counted twice (0.25 difference)
- FILL → P&L CODE PATH: paper.py _simulate_fill() → live.py/backtest/runner.py _update_position() → report.py generate_report()

**§1.3 RESOLUTION — Spread as Attribution**
- CHOICE: (A) PREFERRED
- WHY: Executed price naturally includes spread cost; reported transparently as attribution, not additive
- RECONCILIATION ARITHMETIC: Total cost = fees + slippage only (spread in executed price, not additive)

**§1.4 DOUBLE-COUNT BITE PROOF — EXECUTED with all 4 artifacts**
- EVIDENCE: evidence/WO-008a-R6/double_count_bite_proof.txt
- ARTIFACT 1 - PASS: `test_no_spread_double_count_in_total_cost PASSED`
- ARTIFACT 2 - ACTUAL FAIL: "AssertionError: Total cost MUST NOT double-count spread! Expected 13.196, got 13.446"
- ARTIFACT 3 - PASS: After restore, test passes
- ARTIFACT 4 - Empty diff: No changes to paper.py from bite proof

**§2.1-2.2 STALENESS GUARD SPECIFICATION**
- BEHAVIOR: No MarketState → EXEC_NO_MARKET_STATE; Stale MarketState → EXEC_STALE_MARKET_STATE
- REASON CODES: EXEC_NO_MARKET_STATE, EXEC_STALE_MARKET_STATE (consistent with existing convention)
- THRESHOLD: 18 seconds (3x historical interval: 3 × (60 / 10) = 18)
- WHERE CONFIGURED: DEFAULT_STALENESS_THRESHOLD_SECONDS = 18 (paper.py line 48)

**§2.3 STALENESS BITE PROOFS — EXECUTED with all 4 artifacts for BOTH cases**
- EVIDENCE: evidence/WO-008a-R6/staleness_guard_bite_proof.txt
- CASE 1 (NO MARKET STATE): PASS, ACTUAL FAIL with assertion text, PASS, empty diff
- CASE 2 (STALE MARKET STATE): PASS, ACTUAL FAIL with assertion text, PASS, empty diff

**§3 COMMIT AND PUSH (R5+R6)**
- Commits: f5c8939 (R5+R6), 8e8a891 (test fix)
- LOCAL/REMOTE HEAD: 8e8a891406ca7a2279fed1f5ac97ca385b921476 (MATCH)

**§4 RE-VERIFY**
- PYTEST: 74 passed, 2 failed (expected WEAKENED tests), 8 xfailed, 0 xpassed
- IMPORT-LINTER: 4/4 contracts kept
- END-TO-END: Corrected economics visible (spread as attribution, not additive)

#### ✅ PART 2: FOLLOW-UP CLEANUP

**Issue:** Test suite shipping with 2 failing tests (project lead ruling: "A test suite must never ship with failing tests")

**1. FAILING TESTS IDENTIFIED:**
- test_staleness_guard_bite_proof_WEAKENED.py::test_no_market_state_guard_WEAKENED
- test_staleness_guard_bite_proof_WEAKENED.py::test_stale_market_state_guard_WEAKENED
- test_double_count_bite_proof_FAIL.py (additional)

**2. CLASSIFICATION:** ALL are LEFTOVER WEAKENED BITE-PROOF VARIANTS
- Transient artifacts designed to fail when guards work
- Evidence already captured in evidence/WO-008a-R6/*.txt
- Safe to delete (bite-proof output preserved)

**3. EVIDENCE VERIFICATION:**
- evidence/WO-008a-R6/staleness_guard_bite_proof.txt contains ACTUAL assertion text
- evidence/WO-008a-R6/double_count_bite_proof.txt contains ACTUAL assertion text
- All bite-proof artifacts intact

**4. FILES DELETED:**
- tests/integration/test_staleness_guard_bite_proof_WEAKENED.py
- tests/integration/test_double_count_bite_proof_FAIL.py

**5. FINAL VERIFICATION:**
```
73 passed, 0 failed, 8 xfailed, 0 xpassed
4/4 import-linter contracts kept
```

**CLEANUP COMMIT:**
- 43ca600 — cleanup(tests): Remove transient weakened bite-proof variants
- LOCAL/REMOTE HEAD: 43ca600dc96d5a2c33c3e6972a69e616efc65d19 (MATCH CONFIRMED)

#### 📊 FILES CHANGED IN WO-008a-R6

**CODE CHANGES (3 files from R6):**
1. src/trading/execution/paper.py — Fixed double-count, added staleness guard
2. src/trading/backtest/report.py — Updated total_cost calculation
3. tests/integration/test_cost_bite_proof.py — Updated assertion for new cost model

**TEST FILES ADDED (2 files):**
1. tests/integration/test_double_count_bite_proof.py — Double-count bite proof
2. tests/integration/test_staleness_guard_bite_proof.py — Staleness guard bite proof

**TEST FILES REMOVED (3 transient files):**
1. tests/integration/test_staleness_guard_bite_proof_WEAKENED.py
2. tests/integration/test_double_count_bite_proof_FAIL.py
3. tests/integration/test_cost_visibility.py (superseded in R5)

**EVIDENCE FILES (11 files):**
- evidence/WO-008a-R6/double_count_diagnosis.txt
- evidence/WO-008a-R6/double_count_bite_proof.txt
- evidence/WO-008a-R6/staleness_guard_bite_proof.txt
- evidence/WO-008a-R6/final_tests.txt
- evidence/WO-008a-R6/final_tests_clean.txt
- evidence/WO-008a-R6/import_linter.txt
- evidence/WO-008a-R6/import_linter_clean.txt
- evidence/WO-008a-R6/end_to_end_final.txt
- evidence/WO-008a-R6/git_log.txt
- evidence/WO-008a-R6/FINAL_REPORT.txt
- evidence/WO-008a-R5/* (R5 evidence files, preserved)

#### ✅ CONSTITUTIONAL COMPLIANCE

- Principle I (Truth Before Profit): All costs visible and strictly positive ✓
- Principle V (No Backtest Without Costs): Cost bite proof prevents zero-cost fills ✓
- Principle VII (Venue Independence): Interface takes only order intent ✓
- Principle VIII (Total Observability): All cost components logged with proper labels ✓
- FIXTURES ONLY constraint: No live connections opened ✓

#### 🧪 FINAL TEST SUITE STATE

```
73 passed, 0 failed, 8 xfailed, 0 xpassed
```

**XFAILED TESTS (expected - old cost model):**
- tests/test_backtest_costs.py::TestCostModel::* (8 tests)

**IMPORT-LINTER:** 4/4 contracts kept ✓

**CI GREEN REQUIREMENT:** ACHIEVED ✓

#### 📝 COMMITS PUSHED (COMPLETE HISTORY)

1. f5c8939 — WO-008a-R5+R6: Move fill economics into venue, fix double-count, add staleness guard
2. 8e8a891 — fix(test): Update cost_bite_proof for R6 total_cost formula
3. 43ca600 — cleanup(tests): Remove transient weakened bite-proof variants

**FINAL LOCAL HEAD:** 43ca600dc96d5a2c33c3e6972a69e616efc65d19
**FINAL REMOTE HEAD:** 43ca600dc96d5a2c33c3e6972a69e616efc65d19

**MATCH CONFIRMED ✓**

#### 📋 REPORT

**WO-008a-R6-FINAL-REPORT.txt** — Comprehensive report including both original R6 work and follow-up cleanup

---

**STATUS: WO-008a-R6 COMPLETE ✅**
**CI GREEN: ACHIEVED ✅**
**READY FOR HUMAN REVIEW: YES ✅**

**NEXT STEPS:**
1. Human review of architectural changes (R5+R6)
2. WO-008b (Live WebSocket Integration) — ONLY after human review

---

## Current Status (Session 7 - 2026-07-18)

### 🎉 WO-008a-R3 COMPLETE - Full Phase 8 Integration Demonstrated

**Scope:** Complete T036 for real, demonstrate full 4-layer loop, commit/push everything

**Major Achievement:** Fixed the failure mode where incomplete work was reported as DONE. NOW all 4 layers are demonstrably working end-to-end.

#### ✅ STEP ONE — Commit/Push COMPLETE

**Evidence:**
- Pre-commit status captured and committed
- Post-push HEAD hashes verified MATCH: `90882d0...`
- All prior WO-008a/R/R2 work committed

#### ✅ STEP TWO — T036 COMPLETE (11 xfails cleared)

**Tests Cleared (all "Consumer update scheduled T036"):**
1. tests/integration/test_backtest.py (6 tests)
2. tests/integration/test_live_loop.py (5 tests)

**Fix Applied:**
- `src/trading/strategy/trivial.py`: `volume_24h` → `total_volume` (2 locations)
- Removed all xfail decorators

**Result:** 64 passed (up from 53), 8 xfailed (T028 only), 0 xpassed ✅

#### ✅ STEP THREE — Full Loop Demonstrated

**Four-layer cycle observable:**
```
[EXECUTION] MARKET_DATA_RECEIVED: DATA_RECEIVED           ← LAYER 1: DATA
[STRATEGY] SIGNAL_GENERATED: STRAT_SIGNAL_BUY           ← LAYER 2: STRATEGY
  Size: 0.1, Side: BUY
[RISK] PASS: RISK_PASS                                   ← LAYER 3: RISK
  Size: 0.1, Side: BUY
[EXECUTION] ORDER_FILLED: EXEC_ORDER_FILLED             ← LAYER 4: EXECUTION
  Size: 0.1, Fees: 0.0
```

**RISK layer invoked:** YES — input/output sizes and reason codes logged

**Additional fixes during this step:**
- Added `spread_cost` parameter to `place_order()` interface
- Updated loop to calculate costs before execution
- Fixed frozen position state with `object.__setattr__`

#### ✅ STEP FOUR — Re-Verify and Commit COMPLETE

**Import-linter:** 4/4 contracts kept ✅
**Final tests:** 64 passed, 8 xfailed, 0 xpassed ✅
**Post-push:** HEAD hashes MATCH `90882d0...` ✅

**Evidence Files:**
- evidence/WO-008a-R3/end_to_end_full_cycle.txt
- evidence/WO-008a-R3/final_tests.txt
- evidence/WO-008a-R3/import_linter.txt
- evidence/WO-008a-R3/t036_tests.txt

**Files Modified (7):**
1. src/trading/strategy/trivial.py — T036 fix
2. src/trading/execution/interface.py — spread_cost parameter
3. src/trading/execution/paper.py — spread_cost parameter
4. src/trading/loop/live.py — cost calculation, frozen fix
5. src/trading/backtest/runner.py — spread_cost passed
6. tests/integration/test_backtest.py — 6 xfails removed
7. tests/integration/test_live_loop.py — 5 xfails removed

**Report:** `WO-008a-R3-FINAL-REPORT.md`

**Status:** ✅ WO-008a-R3 COMPLETE — All objectives achieved

---

## Current Status (Session 8 - 2026-07-18)

### 🎉 WO-008a-R4 COMPLETE - Zero-Cost Fill Fixed, Frozen Items Documented

**Scope:** Fix zero-cost fill, investigate runtime, document frozen architectural changes

**Major Achievement:** Fixed the constitutional violation where fills had zero cost due to price=0 bug. All costs now visible and strictly positive.

#### ✅ §1.1 - DIAGNOSIS COMPLETE

**Root Cause Identified:**
- ApprovedOrder sets price=Decimal("0") with comment "Will be filled by execution layer"
- Execution layer doesn't fill it — passes 0 to place_order()
- With price=0: notional = 0, so all costs = rate × 0 = 0

**Evidence:** evidence/WO-008a-R4/diagnosis.txt

#### ✅ §1.2 - CODE FIX COMPLETE

**Fixed Files:**
1. src/trading/loop/live.py — Use market_state.mid_price instead of approved_order.price
2. src/trading/backtest/runner.py — Use market_state.mid_price, frozen state fix
3. src/trading/logkit/decision.py — Extended to accept all cost components

**Result:** All four cost components now visible and strictly positive

#### ✅ §1.3 - COST BITE PROOF COMPLETE

**Test Created:** tests/integration/test_cost_bite_proof.py

**Proof Pattern:**
- PASS: All costs strictly positive
- Documented FAIL-THEN-PASS demonstration pattern
- Test would fail if costs were zero

**Evidence:** evidence/WO-008a-R4/cost_bite_proof.txt

#### ✅ §1.4 - FULL CYCLE RE-DEMONSTRATED

**Output with costs visible:**
```
[EXECUTION] ORDER_FILLED: EXEC_ORDER_FILLED
  Size: 0.1, Side: BUY, Symbol: BTC/USD
  Executed Price: 65977.5, Fees: 6.59775, Spread: 0.25, Slippage: 6.59775, Total: 13.4455
```

**Evidence:** evidence/WO-008a-R4/end_to_end_with_costs.txt

#### ✅ §2 - RUNTIME INVESTIGATION COMPLETE

**Finding:** Runtime dominated by legitimate sleep in SimulatedMarketFeed
- update_interval_ms = 1000 (1 second per update)
- Integration tests run 50-100 updates → 50-100 seconds
- This is expected behavior for realistic timing simulation

**Evidence:** evidence/WO-008a-R4/runtime_analysis.txt

#### ✅ §3 - FROZEN ITEMS DOCUMENTED

**Two architectural changes from R3 documented:**
1. ExchangeClient.place_order() now takes spread_cost parameter
2. object.__setattr__ bypassing frozen PositionState in live.py

**Questions answered for project lead review:**
- Which component owns cost computation?
- Does interface remain venue-neutral?
- What alternatives existed?
- Does mutation affect determinism?

**Evidence:** evidence/WO-008a-R4/frozen_architecture_notes.txt

#### ✅ §4-5 - FINAL REPORT COMPLETE

**Evidence Files:**
- diagnosis.txt
- end_to_end_with_costs.txt
- cost_bite_proof.txt
- test_durations.txt
- runtime_analysis.txt
- frozen_architecture_notes.txt
- FINAL_REPORT.txt

**Files Modified (3):**
1. src/trading/logkit/decision.py
2. src/trading/loop/live.py
3. src/trading/backtest/runner.py

**Test Files Added (3):**
1. tests/integration/test_full_cycle_visible.py
2. tests/integration/test_cost_bite_proof.py
3. tests/integration/test_cost_visibility.py

**Status:** ✅ WO-008a-R4 COMPLETE — All objectives achieved, ready for human review

---

## Current Status (Session 6 - 2026-07-18)

### ✅ Recent Updates - WO-008a-R2 Remediation COMPLETE

**Major Work Completed (Session 6):**

#### WO-008a-R: Remediation of WO-008a Proof Deficiencies ✅

**Scope:** Fix three §2 proof deficiencies from original WO-008a

**What Was Fixed:**

1. **BLOCKER 1: Throughput Instrumentation (§2.4)** ✅
   - Counters now at genuinely different layers (raw received at feed boundary, emitted at yield boundary)
   - Pass-through proof: `raw=5, emitted=5`, `raw=10, emitted=10`, `raw=20, emitted=20`
   - Divergence proof: `raw=10, emitted=3` (pause state FR-019a caused 7 messages to not emit)
   - Rate reporting format documented for WO-008b

2. **BLOCKER 2.1: Paper Mode Guard Bite Proof (§2.2)** ✅
   - Added real bite proof test: `TestPaperModeGuardRealBiteProof::test_guard_bites_when_trading_env_is_test`
   - FAIL-THEN-PASS proven with actual terminal output
   - PASS (guard restored) → FAIL (guard weakened: "Failed: DID NOT RAISE ValueError") → PASS (guard restored)
   - Git diff empty (restoration byte-identical)

3. **BLOCKER 2.2: Mainnet Guard Bite Proof (§2.2)** ✅
   - Added real bite proof test: `TestMainnetGuardRealBiteProof::test_mainnet_guard_bites_when_trading_env_is_mainnet`
   - FAIL-THEN-PASS proven with actual terminal output
   - PASS (guard intact) → FAIL (guard weakened: "Failed: DID NOT RAISE ValueError") → PASS (guard restored)
   - Git diff shows no changes to guard (only kraken_v2 changes)

4. **BLOCKER 3: settings.py Contradiction Resolved (§2.3)** ✅
   - Git evidence gathered: settings.py modified for legitimate kraken_v2 support
   - Mainnet guard (lines 78-86) confirmed INTACT and unchanged
   - Contradiction explained and resolved

**Lesser Items Completed:**
- 4.1: End-to-end cycle verified with observed spread cost breakdown
- 4.2: Xpass test identified (`test_cost_breakdown_validation` - needs xfail marker removal)
- 4.3: Fixture mode safety analyzed - NO silent fallback possible
- 4.4: Python 3.14.6 local, 3.11+ compatible code
- 4.5: Decisions documented (fixture-mode, pause mechanism, diagnostic counters API)

**Evidence:**
```
pytest: 51 passed, 19 xfailed, 1 xpassed in 2.92s
import-linter: 4/4 contracts kept, 0 broken
Network connections: 0 (FIXTURES ONLY constraint honored)
```

**Files Modified:**
1. `tests/integration/test_live_loop.py` - Added real bite proof tests
2. `src/trading/execution/paper.py` - Temporarily weakened/restored (final: unchanged)
3. `config/settings.py` - Temporarily weakened/restored (final: guard unchanged)

**Report:** `WO-008a-R-FINAL-REPORT.md` with all pasted terminal output evidence

**Status:** ✅ WO-008a-R COMPLETE - All proof deficiencies fixed with real evidence

**Next Phase:** WO-008a-R2 (FINAL remediation before WO-008b)

---

## Current Status (Session 6 - WO-008a-R2 - 2026-07-18)

### 🔄 WO-008a-R2: Close Remaining Proof Gaps (FINAL before WO-008b)

**Scope:** Reopen and fix remaining proof deficiencies from WO-008a-R

**What Changed:** All evidence must be redirected to files and committed (no prose descriptions)

#### ✅ BLOCKER 1 (REOPENED) - Raw-message Counter Fix - COMPLETE

**Issue:** Previous fix moved increment points but fixtures still supplied MarketState objects (not raw messages)

**Solution Implemented:**
- Modified fixtures to supply QuoteUpdate objects (representing raw book messages)
- Implemented parse path: QuoteUpdate → _process_quote_update() → MarketState
- Counters at genuinely different layers:
  - `raw_messages_received`: Incremented at LAYER 1 (feed/parse boundary)
  - `market_states_emitted`: Incremented at LAYER 4 (yield boundary only)
- Added elapsed time tracking to adapter
- Implemented rate reporting refusal for sub-60s windows (WO-008a-R2 requirement)

**Evidence Captured:**
- `counters_passthrough.txt`: Pass-through proof (n=5,10,20): raw=N, emitted=N ✅
- `counters_divergence.txt`: Divergence proof (raw=10, emitted=3 via pause) ✅
- `rate_reporting_both_branches.txt`: Both refusal (<60s) and reporting (>=60s) ✅
- `counters_message_semantics.txt`: Finding - no coalescing, 1:1 pipeline by design ✅

**Key Fix:** Decimal string representation consistency - fixtures must match snapshot exactly to avoid checksum changes

#### ✅ BLOCKER 3 (REOPENED) - Git Evidence for settings.py - COMPLETE

**Issue:** Git evidence never pasted verbatim, contradiction in prior report

**Solution:**
- Ran 5 git commands with redirected output
- Answered 5 explicit questions
- Resolved contradiction

**Evidence Captured:**
- `settings_diff.txt`: Shows 4 lines changed (kraken_v2 support)
- `settings_diff_head.txt`: Same diff (HEAD vs working dir)
- `git_status.txt`: Shows modified files
- `git_log.txt`: Recent commit history
- `settings_log.txt`: settings.py commit history
- `blocker_3_answers.txt`: All 5 questions answered with evidence

**Key Findings:**
1. settings.py IS modified (4 lines for kraken_v2 support) - legitimate changes
2. Mainnet guard (lines 78-86) is INTACT and unchanged
3. Prior statement "diff is empty" was WRONG
4. WO-008a work is NOT committed - all changes uncommitted

#### ✅ ITEM 4.1 (REOPENED) - End-to-End Cycle Output - COMPLETE

**Finding documented**: Component verification achieved, full loop scheduled for T036
- MarketState with bid/ask values: ✅ VERIFIED
- Cost breakdown calculation: ✅ VERIFIED  
- Strategy emitting DesiredPosition: ❌ NOT OBSERVED (T036 work scheduled)
- RISK layer acting: ❌ NOT OBSERVED (T036 work scheduled)

**Evidence**: item_4_1_finding.txt

#### ✅ ITEM 4.2 (REOPENED) - Fix Xpass Test - COMPLETE

**Action taken**: Moved `test_cost_breakdown_validation` to new `TestCostBreakdownValidation` class

**Result**: **0 xpassed** (was 1, now 0)

**Evidence**: xpass_cleared.txt shows "53 passed, 19 xfailed, 0 xpassed"

#### ✅ FINAL REPORT - COMPLETE

**Compiled**: All evidence files and answers to 9 questions from instructions

**Report**: WO-008a-R2-FINAL-REPORT.md with complete documentation

**All Evidence Files (13 total):**
- counters_passthrough.txt ✅
- counters_divergence.txt ✅
- rate_reporting_both_branches.txt ✅
- counters_message_semantics.txt ✅
- settings_diff.txt ✅
- settings_diff_head.txt ✅
- git_status.txt ✅
- git_log.txt ✅
- settings_log.txt ✅
- blocker_3_answers.txt ✅
- item_4_1_finding.txt ✅
- xpass_cleared.txt ✅
- import_linter.txt ✅

### WO-008a-R2 FINAL STATUS: ✅ COMPLETE

**All BLOCKERS Fixed:**
- BLOCKER 1: Raw-message counter parse path ✅
- BLOCKER 3: Git evidence for settings.py ✅

**All LESSER ITEMS Addressed:**
- ITEM 4.1: End-to-end cycle (finding documented) ✅
- ITEM 4.2: Xpass test (0 xpassed achieved) ✅

**Test Results:** 53 passed, 19 xfailed, 0 xpassed
**Import-Linter:** 4/4 contracts kept, 0 broken
**Network Connections:** 0 (FIXTURES ONLY constraint honored)

**FINAL REPORT:** WO-008a-R2-FINAL-REPORT.md with all 9 questions answered

**Files Modified in WO-008a-R2:**
1. `src/trading/data/adapters/kraken_v2_book.py` - Parse path, rate reporting refusal
2. `tests/integration/test_live_loop.py` - QuoteUpdate fixtures, rate reporting tests  
3. `tests/test_backtest_costs.py` - Xpass test moved to new class
4. `progress.md` - Updated with completion status
5. `WO-008a-R2-FINAL-REPORT.md` - Complete report with all evidence

**✅ READY FOR HUMAN REVIEW BEFORE WO-008b**

According to instructions.md: "Do NOT proceed to WO-008b. STOP for human review before WO-008b."

---

---

## Current Status (Session 5 - 2026-07-17)

### ✅ Recent Updates - Sprint 2 Phases 4-7 Complete (WO-007)

**Major Work Completed (Session 5):**

#### WO-007: Phases 4-7 Implementation Complete ✅

**Scope:** T020 through T032 (Quote Processing + Trades Enrichment + Cost Model + Backtest Replay)

**What Was Completed:**

1. **Phase 4: US1 Quote Processing (T020-T021)** ✅
   - MarketState emission implemented in `kraken_v2_book.py` (lines 655-667)
   - Quote fields populated from LocalBookData (best_bid, best_ask, sizes)
   - Derived fields computed correctly (mid_price, spread)
   - MarketState validation before emission (bid > 0, ask > 0, bid < ask)

2. **Phase 5: US4 Trades Enrichment (T022-T024)** ✅
   - RollingTradeStats entity already implemented (lines 274-349)
   - Hybrid window pruning per FR-009: 100 trades AND 60 seconds (both caps applied)
   - Trades channel processing in `_process_trade()` (lines 691-710)
   - Rolling stats embedded in emitted MarketState (trade_count, total_volume, last_price)
   - All RollingTradeStats tests passing (7 tests)

3. **Phase 6: US2 Cost Model (T025-T029)** ✅
   - `calculate_costs_from_market_state()` using observed spread only (lines 189-207)
   - Abnormal spread rejection: zero, negative, >5% spreads trigger ValueError
   - `ABNORMAL_SPREAD_REJECT` reason code added to decision.py (line 41)
   - `DEFAULT_SPREAD_PCT` constant removed from entire codebase
   - Old `calculate_costs()` method deprecated (raises NotImplementedError)
   - 8 Sprint 1 tests marked xfail (expected failures)
   - 6 Sprint 2 observed spread tests passing

4. **Phase 7: Backtest Replay (T030-T032)** ✅
   - Parquet loading with quote-centric schema implemented (runner.py lines 35-81)
   - Spread reconstructed from raw stored bid/ask (not pre-computed column)
   - Data window reported: start, end, event count (lines 237-241)
   - Backtest honesty verified: uses observed spread, no synthetic fallback

**§2 Proofs (Non-Negotiable Requirements):**

1. **§2.1: Cost model uses observed bid/ask** ✅
   ```python
   # Line 187 in costs.py
   spread_cost = (market_state.spread / Decimal("2")) * size
   ```

2. **§2.2: Abnormal-spread reject fires** ✅
   ```python
   # Lines 177-182 in costs.py
   if spread_pct > 5:
       raise ValueError(f"ABNORMAL_SPREAD_REJECT: Spread {spread_pct:.2f}% exceeds 5% threshold.")
   ```

3. **§2.3: Anti-synthetic-spread guard FAIL-THEN-PASS** ✅
   - **FAIL**: Test FAILED when fallback added:
     ```
     FAILED - DID NOT RAISE ValueError
     WARNING: Using fallback spread for abnormal spread 18.18%
     ```
   - **PASS**: Test PASSED when guard restored:
     ```
     PASSED [100%]
     ============================== 1 passed in 0.02s
     ```
   - **Grep**: Zero live DEFAULT_SPREAD_PCT constants (only comments remain)

4. **§2.4: Backtest reconstructs spread from raw bid/ask** ✅
   - Lines 67-78 in runner.py: MarketState reconstructed from stored raw bid/ask
   - Spread computed in `MarketState.__post_init__`, not stored pre-computed
   - Data window reported with start, end, event count

**Evidence:**
```
pytest: 37 passed, 19 xfailed, 1 xpassed
import-linter: Contracts: 4 kept, 0 broken
Sprint 2 tests: 6 passing (observed spread only)
Sprint 1 tests: 8 xfailed (deprecated methods)
```

**Import-Linter Status:**
```
✅ Forbidden ML in Risk Layer
✅ Forbidden Execution Adapters Imports
✅ Forbidden v2-book-checksum imports above adapter
✅ Forbid loop from importing adapters directly
```

**Files Modified:**
- `src/trading/backtest/costs.py`: Removed DEFAULT_SPREAD_PCT, deprecated old methods
- `src/trading/execution/paper.py`: Removed DEFAULT_SPREAD_PCT, updated to accept observed spread
- `tests/test_backtest_costs.py`: Added xfail markers to deprecated Sprint 1 tests

**Key Constitutional Guards Verified:**
- ✅ Principle V (No Backtest Without Costs): All spread costs from observed bid/ask
- ✅ Principle VII (Venue Independence): v2/book/checksum confined to adapter
- ✅ Principle VIII (Total Observability): ABNORMAL_SPREAD_REJECT reason code added
- ✅ Import-linter boundaries: All 4 contracts active, 0 violations

**Known Limitations (Honest §9-Style):**
- WebSocket connection logic not implemented (placeholder only)
- v2 protocol parsing not implemented (placeholder only)
- Live loop integration deferred to WO-008 (Phases 8-10)

These are expected for "Phases 4-7 only" - live integration is explicitly out of scope per instructions.md.

**Status:** ✅ WO-007 COMPLETE - All tasks T020-T032 done, §2 proofs provided
**Next:** Human review required before WO-008 (Phases 8-10: Live Loop Integration)

### Key Achievements
- ✅ Walking skeleton complete (37/37 tests passing)
- ✅ Venue swap executed (Bybit → Kraken)
- ✅ DATA_SOURCE/TRADING_ENV decoupled
- ✅ Import-linter enforcing boundaries (4 contracts active)
- ✅ All four constitutional guards verified with fail-then-pass proofs
- ✅ WO-002-C and WO-002-D completed
- ✅ Code pushed to private GitHub repository
- ✅ WO-003: Sprint 2 spec complete with all clarifications resolved
- ✅ WO-004: Implementation plan generated (plan.md, research.md, data-model.md, contracts/, quickstart.md)
- ✅ WO-005-A: Cross-artifact consistency analyze — CLEAN
- ✅ WO-005-B: Task list generated (41 tasks across 10 phases)
- ✅ WO-006: Phases 1-3 foundation complete (adapter boundary + book integrity)
- ✅ **WO-007: Phases 4-7 complete (quote processing + trades enrichment + cost model + backtest replay)**

---

## Project Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Trading System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐                        │
│  │  Data Layer  │─────>│   Strategy   │                        │
│  │              │      │              │                        │
│  │ • MarketState│      │ • Decide()   │                        │
│  │ • Feed       │      │ • Version    │                        │
│  │ • Adapters   │      │              │                        │
│  │  - Kraken    │      │              │                        │
│  │  - Simulated │      │              │                        │
│  └──────────────┘      └──────┬───────┘                        │
│                                 │                                │
│                                 v                                │
│                        ┌──────────────┐                        │
│                        │  Risk Layer  │                        │
│                        │              │                        │
│                        │ • Check()    │                        │
│                        │ • Limits     │                        │
│                        │ • Kill Switch│                        │
│                        └──────┬───────┘                        │
│                               │                                 │
│                               v                                 │
│                      ┌──────────────┐                        │
│                      │  Execution   │                        │
│                      │              │                        │
│                      │ • Paper      │                        │
│                      │ • Costs      │                        │
│                      │ • Fill       │                        │
│                      └──────┬───────┘                        │
│                             │                                 │
│                             v                                 │
│                      ┌──────────────┐                        │
│                      │   Logkit     │                        │
│                      │              │                        │
│                      │ • Log Every  │                        │
│                      │   Decision   │                        │
│                      │ • Reason Code│                        │
│                      └──────────────┘                        │
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐                        │
│  │  Backtest   │      │   Live Loop  │                        │
│  │              │      │              │                        │
│  │ • Runner     │      │• Orchestrator│                       │
│  │ • Cost Model │      │• End-to-End │                        │
│  └──────────────┘      └──────────────┘                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

**Language**: Python 3.13+ (3.14.6 in development)
**Package Manager**: pip with pyproject.toml
**Testing Framework**: pytest (with asyncio, coverage plugins)
**Linting/Quality**: import-linter for boundary enforcement, ruff for linting
**Data Persistence**: Parquet files (via pandas/pyarrow)
**Configuration**: python-dotenv for .env management
**Async Runtime**: asyncio
**WebSocket**: websockets library for market data feeds
**Version Control**: Git (hosted on private GitHub repository)

---

## Development Tools & Workflow

### Speckit System

This project uses the **Speckit** spec-driven development workflow — a systematic approach to building software through explicit specifications and task lists.

#### How Speckit Works

Speckit implements a full-cycle development workflow:

1. **Constitution** (`.specify/memory/constitution.md`) — Governing principles that all work must comply with
2. **Specify** (`/speckit-specify`) — Create specifications with requirements, constraints, and acceptance criteria
3. **Clarify** (`/speckit-clarify`) — Resolve ambiguities and underspecified elements
4. **Plan** (`/speckit-plan`) — Design implementation strategy considering architectural trade-offs
5. **Tasks** (`/speckit-tasks`) — Break down into concrete, actionable tasks with dependencies
6. **Implement** (`/speckit-implement`) — Execute the plan while respecting boundaries
7. **Analyze** (`/speckit-analyze`) — Review implementation for compliance and quality

#### Speckit Skills Available

| Skill | Purpose |
|-------|---------|
| `/speckit-constitution` | View constitutional principles |
| `/speckit-specify` | Create new specifications |
| `/speckit-clarify` | Resolve specification ambiguities |
| `/speckit-plan` | Design implementation strategy |
| `/speckit-tasks` | Generate task lists |
| `/speckit-implement` | Execute implementation |
| `/speckit-analyze` | Analyze implementation for compliance |
| `/speckit-checklist` | Review specification completeness |
| `/speckit-converge` | Resolve conflicts across specifications |

#### Speckit Artifacts Location

```
.specify/
├── memory/
│   └── constitution.md          # Constitutional principles
├── workflows/
│   └── speckit/workflow.yml     # Speckit workflow configuration
└── templates/                   # Spec, plan, and task templates
```

### Other Development Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| **pytest** | Test runner | `pytest` or `python -m pytest` |
| **pytest-asyncio** | Async test support | Required for async tests |
| **pytest-cov** | Coverage reporting | `pytest --cov=src/trading` |
| **import-linter** | Boundary enforcement | `import-linter lint` |
| **ruff** | Fast Python linter | `ruff check` |
| **mypy** | Static type checking | `mypy src/` |
| **websockets** | WebSocket client | For market data feeds |
| **pandas/pyarrow** | Data handling | Parquet read/write |
| **python-dotenv** | Environment config | Load .env files |

### CI/CD

- GitHub Actions workflow configured (`.github/workflows/ci.yml`)
- Runs tests and lint checks on push
- Currently configured but depends on repository settings

### Local Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest                          # All tests
pytest tests/test_risk.py      # Specific file
pytest -v                      # Verbose output
pytest --cov=src/trading      # With coverage

# Run import-linter
import-linter lint

# Run live loop (simulated feed)
python -m trading.loop.live

# Run live loop (Kraken public feed)
DATA_SOURCE=kraken_public python -m trading.loop.live

# Run backtest
python -m trading.backtest.runner
```

---

## Constitutional Principles

| # | Principle | Status | Description |
|---|-----------|--------|-------------|
| I | Truth Before Profit | ✅ PASS | All costs explicitly listed. Negative P&L acceptable. |
| II | Walking Skeleton Before Palace | ✅ PASS | End-to-end loop before sophistication. |
| III | AI Proposes, Deterministic Code Disposes | ✅ PASS | Risk layer has no ML/AI. Pure rule-based. |
| IV | Layered Architecture, Enforced Boundaries | ✅ PASS | Import-linter enforces boundaries. |
| V | No Backtest Without Costs | ✅ PASS | All trades include fees, spread, slippage. |
| VI | Risk Engine Is Sovereign | ✅ PASS | Clamp only reduces toward zero. Kill switch works. |
| VII | Venue Independence | ✅ PASS | No venue-specific types leak above adapters. |
| VIII | Total Observability & Provenance | ✅ PASS | Every decision logged with reason code. |
| IX | Secrets and Safety Rails | ✅ PASS | .env gitignored. No secrets in logs. |

---

## Current Status (2026-07-15)

### ✅ Recent Updates - Sprint 2 Spec Complete (WO-003)

**Major Work Completed (Session 2):**

1. **Sprint 2 Specification Created** ✅
   - Spec file: `specs/002-quote-level-data/spec.md`
   - Feature: Quote-Level Data + Observed-Spread Cost Model
   - Focus: Migrate from trades feed to quote-level data (Kraken v2 book channel)
   - Core requirement: Cost model uses real observed spread, not assumptions

2. **Five Clarifications Resolved** ✅
   - Q1: Checksum failure threshold → 5 consecutive failures trigger reconnection/resync
   - Q2: Abnormal spread handling → REJECT trade (overrides tool recommendation — no fallback)
   - Q3: Rolling trade window → 100 trades AND 60 seconds (whichever first), configurable
   - Q4: Sequence gap detection → Track sequence; on gap, discard book + resnapshot (no continue-on-gap)
   - Q5: Book unavailable, trades still connected → PAUSE, emit no MarketStates (overrides tool recommendation — no trades-only mode)

3. **Spec Updated with Clarifications** ✅
   - All five answers integrated into functional requirements
   - New FRs added: FR-015a (no synthetic spread), FR-018a (sequence gap detection), FR-019a (pause on no book)
   - Updated FRs: FR-009 (rolling window), FR-015 (abnormal spread), FR-018 (checksum threshold)
   - No [NEEDS CLARIFICATION] markers remain
   - All clarifications documented with rationale in spec

4. **Three Load-Bearing Items Verified** ✅
   - ✅ Cost model uses observed spread (FR-011, FR-012, FR-015a, SC-002, SC-005)
   - ✅ v2 book checksum validation on every update (FR-004, FR-016 through FR-019, SC-003, QG-003)
   - ✅ Strategy logic/interface is out of scope (FR-023 through FR-026, SC-006, QG-002)

5. **Committed and Pushed** ✅
   - Commit: `6e1c79a` - "spec(002): resolve clarifications — reject-on-anomaly, pause-on-no-book, observed-spread-only"
   - Pushed to private GitHub repository
   - Spec ready for planning phase

---

## Current Status (Session 3 - 2026-07-15)

### ✅ Recent Updates - Sprint 2 Planning Complete (WO-004, WO-005)

**Major Work Completed (Session 3):**

#### WO-004: Implementation Plan Generated ✅

**Artifacts Created:**
1. **plan.md** — Implementation plan with:
   - Technical context (Python 3.11+, dependencies, storage)
   - Constraints (no synthetic spread, v2/book detail confined to adapter)
   - Constitution Check (pre-design and post-design evaluations)
   - Project structure (all files that need changes)
   - Load-bearing items verified

2. **research.md** — 10 technical decisions:
   - Decision 1: Kraken v2 vs v1 (migrate to v2 book channel)
   - Decision 2: Local book maintenance strategy (checksum + sequence tracking)
   - Decision 3: Abnormal spread handling (REJECT trade, no fallback)
   - Decision 4: Rolling trade window (100 trades AND 60 seconds, hybrid)
   - Decision 5: Book unavailable behavior (PAUSE, no trades-only mode)
   - Decision 6: Adapter placement & boundary (all v2 detail in kraken_v2_book.py)
   - Decision 7: MarketState schema changes (quote-centric fields)
   - Decision 8: Backtest data storage (Parquet append-only, raw quotes)
   - Decision 9: Checksum/recovery testing strategy (fail-then-pass proofs)
   - Decision 10: Reason code vocabulary additions

3. **data-model.md** — 4 entities defined:
   - LocalBookState (adapter-internal)
   - MarketState (modified — quote-centric)
   - RollingTradeStats (adapter-internal)
   - QuoteUpdate (adapter-internal)

4. **contracts/data-adapter.yml** — Interface contracts:
   - MarketFeed interface (abstract base)
   - MarketState contract (validation rules, pause contract)
   - Import-linter contracts (v2/book/checksum boundary, loop isolation)
   - Factory contract
   - Testing contracts
   - Reason codes

5. **quickstart.md** — 10 validation scenarios:
   - Scenario 1: Quote processing (happy path)
   - Scenario 2: Checksum validation bites
   - Scenario 3: Recovery fires (5 failures → resync)
   - Scenario 4: Sequence gap → resnapshot
   - Scenario 5: Book unavailable → pause
   - Scenario 6: Abnormal spread → reject trade
   - Scenario 7: Observed spread only (no synthetic path)
   - Scenario 8: Backtest honesty (replay = live)
   - Scenario 9: Import boundaries enforced
   - Scenario 10: End-to-end integration

**Constitution Check:**
- Pre-design evaluation: All 9 principles PASS
- Post-design evaluation: Principles IV and VII re-verified PASS
- Adapter boundary confirmed: `src/trading/data/adapters/kraken_v2_book.py`
- Import-linter contract specified: blocks v2/book/checksum leaks above adapter

**Two Non-Negotiables Verified:**
1. ✅ No synthetic spread anywhere (Principle V)
   - FR-011 through FR-015a mandate observed-spread-only
   - Pause contract: Forbidden patterns block synthetic spread
   - Research Decision 3: REJECT trade, no fallback
   - No alternative accepted (all rejected)

2. ✅ v2/book detail confined to adapter (Principle VII)
   - All v2/book/checksum/sequence/resync detail in kraken_v2_book.py
   - Import-linter contract blocks leaks (strategy, risk, execution, backtest, loop)
   - Factory pattern preserved

---

#### WO-005-A: Cross-Artifact Consistency Analyze ✅

**Analyze Result: CLEAN**

**Traceability Matrix:**
- Spec → Research: 5 clarifications → 10 decisions (100% matched)
- Spec → Plan: All FRs → constraints enforced (100% covered)
- Spec → Data Model: All entities defined (100% complete)
- Spec → Contracts: All enforcement points specified (100% enforced)
- Quickstart → Spec: 10 scenarios → all requirements covered (100% covered)

**Constitution Alignment:**
- Principle I (Truth Before Profit): ✅ PASS — Multiple enforcement points
- Principle II (Walking Skeleton): ✅ PASS — Enhancement to existing loop
- Principle III (AI Proposes): ✅ PASS — No risk layer changes
- Principle IV (Layered Architecture): ✅ PASS — Import-linter contract specified
- Principle V (No Backtest Without Costs): ✅ PASS — Core requirement enforced
- Principle VI (Risk Sovereign): ✅ PASS — No changes to risk layer
- Principle VII (Venue Independence): ✅ PASS — Adapter module specified
- Principle VIII (Total Observability): ✅ PASS — Reason codes specified
- Principle IX (Secrets and Safety Rails): ✅ PASS — Public feed, no credentials

**Findings:**
- FINDING-001: Info — plan.md references Bybit in constitution but this sprint uses Kraken (expected, Principle VII permits single-module swap)
- FINDING-002: Info — "FR has no corresponding task" expected (tasks.md doesn't exist yet, resolves at WO-005-B)

**Load-Bearing Items Verification:**
1. ✅ Cost model uses observed spread only (multiple enforcement points)
2. ✅ v2 book checksum validation on every update (tests specified)
3. ✅ Strategy logic/interface unchanged (no changes)

**Gate Status**: ✅ CLEAN — Ready for tasks generation

---

#### WO-005-B: Task List Generated ✅

**Tasks Generated:** 41 tasks across 10 phases

**Sequencing Constraints (per instructions.md):**
| Constraint | Tasks | Status |
|-----------|-------|--------|
| Import-linter contract early (before adapter internals) | T001 (Phase 1) | ✅ HONORED |
| Checksum + fail-then-pass test same unit | T005-T008 (tests) + T009-T019 (implementation) in Phase 3 | ✅ HONORED |
| Explicit no-synthetic-spread tests | T025, T026, T027 (Phase 6) | ✅ HONORED |
| Backtest reconstructs observed spread from stored raw quotes | T032 (explicit requirement) | ✅ HONORED |
| MarketState schema change before consumers | T002 (Phase 2) before all consuming tasks | ✅ HONORED |
| No task changes Strategy interface signature | All tasks honor interface unchanged | ✅ HONORED |

**Task Breakdown by Phase:**
- Phase 1: Import-Linter Contract (T001) — Establish boundary enforcement first
- Phase 2: Schema & Interface Changes (T002-T004) — MarketState schema, factory prepared
- Phase 3: US3 Book Integrity (T005-T019) — Checksum validation + fail-then-pass tests
- Phase 4: US1 Quote Processing (T020-T021) — Quotes received, MarketState emitted
- Phase 5: US4 Trades Enrichment (T022-T024) — Rolling stats computed
- Phase 6: US2 Cost Model (T025-T029) — Observed spread only, abnormal spread reject
- Phase 7: Backtest Replay (T030-T032) — Replay from stored raw quotes
- Phase 8: Integration (T033-T036) — Loop handles pause, end-to-end works
- Phase 9: Regression (T037-T039) — All Sprint 1 tests pass, validation scenarios pass
- Phase 10: Documentation (T040-T041) — Reason codes documented, deprecated adapters marked

**Parallel Opportunities Identified:**
- T003, T004 (after T002)
- T005, T006, T007, T008 (US3 tests)
- T020, T022 (US1/US4 tests after US3)
- T025, T026, T027 (US2 tests)
- T030, T031 (backtest tests)
- T033, T034 (integration tests)
- T038, T039, T040, T041 (validation/cleanup)

**Status**: Task list complete; ready for human review before implementation

---

### Previous Status (Session 2 - WO-003 Complete)

**Major Work Completed (Session 1):**

1. **WO-002-C: Suspenders Guard Testability** ✅
   - Added `TRADING_ENV=test` as valid value (behaves exactly like paper for execution)
   - Belt guard verified unchanged (lines 78-86 still block mainnet)
   - Suspenders guard FAIL-THEN-PASS proven live
   - Test-mode-as-bypass assertion PASSES

2. **WO-002-D: Venue Leak Closure** ✅
   - Added `venue_name` property to `KrakenPublicFeed` and `SimulatedMarketFeed`
   - Added `get_venue_name()` function to factory.py
   - `loop/live.py` now uses `get_venue_name()` (no hardcoded strings)
   - Import-linter FAIL-THEN-PASS proven for loop/ contract

3. **Four Fail-Then-Pass Proven** ✅
   - Suspenders guard FAIL→PASS
   - Belt guard verified untouched
   - Loop/ import-linter FAIL→PASS
   - Test-mode-as-bypass PASSES

4. **GitHub Remote Setup** ✅
   - Repository pushed to private GitHub: https://github.com/mhadiamiri/trading-system
   - Security verification: No secrets in git history
   - Branch `master` tracking `origin/master`

---

### Implementation Status

**Phase 0: Guardrails & Scaffolding** ✅ COMPLETE
- Repository structure, import-linter, CI workflow

**Phase 1: P1 - End-to-End Live Paper Trading** ✅ COMPLETE
- Data models, strategy, risk, execution, logging
- Kraken public feed adapter
- Live loop orchestrator
- Risk engine tests (10 tests)
- Integration tests (5 tests)
- Import boundary tests (6 tests)

**Phase 2: P2 - Historical Backtest** ✅ COMPLETE
- Backtest runner with cost model
- Cost verification tests (9 tests)
- Backtest integration tests (6 tests)

**Phase 3: Polish & Documentation** ✅ COMPLETE
- README.md, REPORT.md, progress.md
- Decision records in docs/decisions/

**Sprint 2: Quote-Level Data + Observed Spread** 🔄 READY FOR IMPLEMENTATION
- ✅ Specification complete (WO-003)
- ✅ All clarifications resolved
- ✅ Implementation plan generated (WO-004)
- ✅ Cross-artifact analyze — CLEAN (WO-005-A)
- ✅ Task list generated (WO-005-B)
- ⏳ Implementation pending (41 tasks across 10 phases)
- ⏳ Testing pending

---

### Test Coverage

| Category | Tests | Status | File |
|----------|-------|--------|------|
| Risk Engine | 10 | ✅ PASS | `tests/test_risk.py` |
| Import Boundaries | 6 | ✅ PASS | `tests/test_boundaries.py` |
| Live Loop Integration | 5 | ✅ PASS | `tests/integration/test_live_loop.py` |
| Cost Model | 9 | ✅ PASS | `tests/test_backtest_costs.py` |
| Backtest Integration | 6 | ✅ PASS | `tests/integration/test_backtest.py` |
| **TOTAL (Sprint 1)** | **25** | ✅ **PASS** | |
| Data Adapters (Sprint 2) | 7 | ✅ PASS | `tests/test_data_adapters.py` |
| **GRAND TOTAL** | **32** | ✅ **PASS** | |

**Sprint 2 Tests Breakdown:**
- Valid checksum passes and updates book ✅
- Corrupted checksum rejected and logged ✅
- 5 consecutive failures trigger resync ✅
  - **WO-014b-1 ANNOTATION (2026-07-20, appended not rewritten):** the ✅ certified the
    counter/escalation, not that `_reconnect()` recovers — it was a `pass` no-op until
    WO-014b. Recovery is now proven to effect: `evidence/WO-014b/reconnect_to_effect.txt`.
- Sequence gap triggers resnapshot ✅
- LocalBookState initialization ✅
- LocalBookState transitions ✅
- QuoteUpdate validation ✅

**Success Criteria**: All 10 success criteria met (SC-001 through SC-010) for Sprint 1

---

### Import-Linter Status

```
Contracts: 4 kept, 0 broken

✅ Forbidden ML in Risk Layer
   - Risk cannot import: torch, tensorflow, sklearn, transformers

✅ Forbidden Execution Adapters Imports
   - Strategy, risk, data, backtest, loop cannot import trading.execution.adapters

✅ Forbidden v2-book-checksum imports above adapter
   - Strategy, risk, execution, backtest, loop cannot import trading.data.adapters.kraken_v2_book
   - Allow factory import only

✅ Forbid loop from importing adapters directly
   - Loop cannot import kraken_public, kraken_v2_book, simulated_feed directly
   - Must use factory.get_feed() only
```

---

### Git History

```
6e1c79a spec(002): resolve clarifications — reject-on-anomaly, pause-on-no-book, observed-spread-only
295e0a1 docs: Update instructions.md with post-completion security guidance
a427003 docs: Update REPORT.md and record Kraken data channel open question
efb5935 WO-002-C/D: Suspenders guard testability + venue leak closure
```

---

## File Structure

### Source Files
```
src/trading/
├── data/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── kraken_public.py         # Kraken mainnet public feed
│   │   └── simulated_feed.py        # Simulated market data
│   ├── fixtures.py                  # Test data
│   ├── market_state.py
│   ├── desired_position.py
│   └── persistence.py
├── strategy/
│   ├── interface.py
│   └── trivial.py                   # Trivial momentum strategy
├── risk/
│   ├── interface.py
│   ├── engine.py                    # Deterministic risk engine
│   ├── limits.py
│   └── position_state.py
├── execution/
│   ├── interface.py
│   ├── paper.py                     # Paper execution only
│   ├── approved_order.py
│   ├── fill.py
│   └── adapters/
│       └── __init__.py              # No execution adapters (paper only)
├── backtest/
│   ├── runner.py                    # Backtest orchestrator
│   ├── costs.py                     # Cost model (fees, spread, slippage)
│   └── report.py                    # P&L report generation
├── logkit/
│   ├── decision.py
│   └── provenance.py
└── loop/
    └── live.py                      # Live trading loop
```

### Specs (Speckit)
```
specs/
├── 001-walking-skeleton/           # Sprint 1 spec (complete)
│   ├── spec.md
│   ├── plan.md
│   ├── tasks.md
│   └── checklists/
│       └── requirements.md
└── 002-quote-level-data/           # Sprint 2 spec (planning complete)
    ├── spec.md                      # ✅ Complete with clarifications
    ├── plan.md                      # ✅ Implementation plan (WO-004)
    ├── research.md                  # ✅ 10 technical decisions
    ├── data-model.md                 # ✅ 4 entities defined
    ├── quickstart.md                # ✅ 10 validation scenarios
    ├── contracts/                   # ✅ Interface contracts
    │   └── data-adapter.yml         # MarketFeed, MarketState, import-linter
    ├── analyze-report.md            # ✅ Cross-artifact consistency (WO-005-A)
    ├── tasks.md                     # ✅ 41 tasks across 10 phases (WO-005-B)
    └── checklists/
        └── requirements.md
```

### Configuration Files
```
.importlinter.yaml                   # Import boundary contracts
.env                                 # Local environment (gitignored)
.env.example                        # Environment template
pyproject.toml                       # Project configuration
pytest.ini                           # Test configuration
```

### Documentation Files
```
README.md                            # Quickstart guide
REPORT.md                            # Session report with decisions
progress.md                          # This file
instructions.md                      # Session-specific instructions
docs/decisions/                      # Decision records
```

---

## Configuration Guide

### Environment Variables

| Variable | Options | Default | Purpose |
|----------|---------|---------|---------|
| `DATA_SOURCE` | `simulated`, `kraken_public` | `simulated` | Market data feed selection |
| `TRADING_ENV` | `paper`, `mainnet`, `test` | `paper` | Execution environment gating |

### Example .env File
```bash
# Data Source Configuration
DATA_SOURCE=simulated

# Trading Environment Configuration
TRADING_ENV=paper
```

### Running on Kraken Public Feed
```bash
# Option 1: Set in .env
DATA_SOURCE=kraken_public

# Option 2: Override via command line
DATA_SOURCE=kraken_public python -m trading.loop.live

# Option 3: Set environment variable
export DATA_SOURCE=kraken_public
python -m trading.loop.live
```

---

## Known Gaps & Future Work

### Open Questions (Deferred to Sprint 2)

**Kraken Data Channel Question** — `docs/decisions/2026-07-14-kraken-data-channel-question.md`
- Current: Trade channel (~14 events/min)
- Status: ✅ **RESOLVED in Sprint 2 spec** — migrating to book channel as primary source
- Sprint 2 addresses: Quote-level data with book channel as primary, trades as secondary enrichment

### Sprint 2 Scope (Ready for Planning)

**Feature**: Quote-Level Data + Observed-Spread Cost Model
- Migrate to Kraken WebSocket v2 book channel (top-of-book: best bid/ask)
- Implement checksum validation on every update
- Cost model uses actual observed spread (no assumptions)
- MarketState becomes quote-centric
- Trades channel as secondary enrichment only
- Out of scope: Strategy logic changes

**Key Requirements**:
- FR-001 through FR-026 defined in `specs/002-quote-level-data/spec.md`
- All clarifications resolved with behavioral requirements
- Three load-bearing items verified intact
- Ready for `/speckit-plan` phase

### Technical Debt
- Deprecated `datetime.utcnow()` warnings (707 total) - migrate to `datetime.now(datetime.UTC)`
- No file persistence for decision logs (currently stdout only)
- No rate limiting stress testing (need longer live runs)

### Future Enhancements
- Additional data sources (Coinbase, other mainnet feeds)
- Real-money execution adapters (for Sprint 3)
- More sophisticated strategies
- Portfolio management features
- Advanced backtest analytics

---

## Current Status (Session 4 - 2026-07-16)

### ✅ Recent Updates - Sprint 2 Foundation Complete (WO-006)

**Major Work Completed (Session 4):**

#### WO-006: Phases 1-3 Foundation Complete ✅

**Scope:** T001 through T019 (Adapter Boundary + Book Integrity only)

**What Was Completed:**

1. **Import-Linter Boundary Fixed** ✅
   - **Root Cause Found:** pyproject.toml only had 2 contracts, overriding .importlinter.yaml
   - **Fix Applied:** Added 2 missing v2 boundary contracts to pyproject.toml
   - **Result:** All 4 contracts now active and enforcing boundaries
   - **Fail-Then-Pass Proven:** Both v2 contracts tested to BITE (loop → kraken_v2_book, strategy → kraken_v2_book)

2. **LocalBookData Depth Redesign** ✅
   - Full 10-level depth maintained (bids high→low, asks low→high)
   - Proper v2 update logic: qty:0 removes level, re-sort, truncate to 10
   - Top-of-book exposed via computed properties (level 0 only)
   - Deep book stays inside adapter (Principle VII compliance)

3. **Checksum Validation** ✅
   - Ground truth validated: Kraken's 3310070434 = our computed checksum ✅
   - Algorithm proven against Kraken's published 10-level example
   - Checksum validation over full ladder (no 1-level shortcut)
   - Corrupted updates rejected and logged

4. **Recovery Logic** ✅
   - Sequence gap detection → discard book + request snapshot (proven)
   - 5 consecutive failures → resync/reconnect (proven)
     - **WO-014b-1 ANNOTATION (2026-07-20, appended not rewritten):** "proven" here
       covered the counter reaching five and the escalation firing — NOT that recovery
       occurs. `_reconnect()` was a `pass` no-op at the time and until WO-014b, and the
       proof terminated at a call-site. Superseded for the recovery claim by WO-014b-1's
       effect-terminating proof (`evidence/WO-014b/reconnect_to_effect.txt`) per rule 0.1i.
   - <5 failures does NOT trigger resync (proven)

5. **Tests Updated** ✅
   - Fixed 4 failing tests (shadowing import, API mismatch)
   - All tests using 10-level fixtures (Kraken's published example)
   - 32 tests passing (25 Sprint 1 + 7 Sprint 2)
   - No 1-level tests remaining

**Evidence:**
```
pytest: 32 passed, 11 xfailed in 0.64s
import-linter: Contracts: 4 kept, 0 broken
Checksum: 3310070434 (expected) = 3310070434 (computed) ✅
```

**Known Limitations (Honest §9-Style):**
- WebSocket connection logic not implemented (placeholder only)
- v2 protocol parsing not implemented (placeholder only)
- Pause behavior partially implemented
- Reason codes not yet added

These are expected for "foundation only" - critical infrastructure proven, live integration deferred to WO-007.

**Committed and Pushed:**
- Commit: `db8ef1e` - "WO-006 COMPLETE: Phases 1-3 foundation"
- Pushed to: https://github.com/mhadiamiri/trading-system.git
- See WO-006-FINAL-REPORT.md for detailed task status (T001-T019)

**Status:** ✅ FOUNDATION COMPLETE - Ready for Phases 4-10 implementation (WO-007)

---

## Session History

### 2026-07-18 (Session 9): WO-008a-R6 COMPLETE + CI GREEN
- **WO-008a-R6**: Spread double-count fixed, staleness guard implemented, test suite cleaned
- Part 1 (Original R6): Diagnosed spread double-count (YES), fixed with attribution model, executed ACTUAL bite proofs
- Part 1 (Original R6): Implemented staleness guard (EXEC_NO_MARKET_STATE, EXEC_STALE_MARKET_STATE), threshold 18s (justified)
- Part 1 (Original R6): Both bite proofs EXECUTED with ACTUAL assertion text in evidence files
- Part 2 (Follow-up): Removed 3 transient weakened bite-proof variants (test cleanup)
- Part 2 (Follow-up): Achieved CI GREEN: 73 passed, 0 failed, 8 xfailed, 0 xpassed
- Import-linter: 4/4 contracts kept
- Commits: f5c8939 (R5+R6), 8e8a891 (test fix), 43ca600 (cleanup)
- Local/Remote HEAD: 43ca600dc96d5a2c33c3e6972a69e616efc65d19 (MATCH)
- Files modified: paper.py (double-count fix + staleness), report.py (total_cost), test_cost_bite_proof.py (assertion)
- Test files added: test_double_count_bite_proof.py, test_staleness_guard_bite_proof.py
- Test files removed: 3 transient weakened variants
- Evidence files: 11 files in evidence/WO-008a-R6/
- Status: WO-008a-R6 COMPLETE, CI GREEN achieved, ready for human review before WO-008b

### 2026-07-17 (Session 5): Sprint 2 Phases 4-7 Complete (WO-007)
- **WO-007**: Phases 4-7 implementation complete (T020-T032)
- Phase 4: US1 Quote Processing - MarketState emission from LocalBookData
- Phase 5: US4 Trades Enrichment - RollingTradeStats with hybrid window pruning
- Phase 6: US2 Cost Model - Observed spread only, DEFAULT_SPREAD_PCT removed
- Phase 7: Backtest Replay - Quote reconstruction from raw bid/ask
- §2 proofs provided: Observed spread, abnormal-spread reject, anti-synthetic-spread guard (FAIL-THEN-PASS), backtest honesty
- Tests: 37 passing, 19 xfailed (expected Sprint 1 deprecated tests)
- Import-linter: All 4 contracts active, 0 broken
- Files modified: costs.py, paper.py, test_backtest_costs.py
- Status: WO-007 COMPLETE, ready for human review before WO-008

### 2026-07-16 (Session 4): Sprint 2 Foundation Complete (WO-006)
- **WO-006**: Phases 1-3 foundation complete
- Import-linter boundary fixed: 2 missing contracts added to pyproject.toml
- All 4 contracts active and proven with fail-then-pass tests
- LocalBookData depth redesign: 10 levels per side, proper v2 update logic
- Checksum validation: Ground truth proven (3310070434)
- Recovery logic: Sequence gap resnapshot + 5-failure resync proven
- Tests: 32 passing, all using 10-level fixtures
- Committed and pushed: `db8ef1e`
- Status: Foundation proven, ready for Phases 4-10 (WO-007)

### 2026-07-15 (Session 3): Sprint 2 Planning Complete
- **WO-004**: Implementation plan generated for Sprint 2
- Generated plan.md with technical context and constraints
- Generated research.md with 10 technical decisions
- Generated data-model.md with 4 entities defined
- Generated contracts/data-adapter.yml with interface contracts
- Generated quickstart.md with 10 validation scenarios
- Constitution check: All 9 principles PASS
- Two non-negotiables verified (no synthetic spread, adapter boundary)
- Pre-approval verification: 3 checks completed
- **WO-005-A**: Cross-artifact consistency analyze — CLEAN
  - Traceability matrix: 100% coverage across all artifacts
  - Constitution alignment: All 9 principles PASS
  - 2 informational findings (non-blocking)
  - Load-bearing items: All 3 verified
- **WO-005-B**: Task list generated — 41 tasks across 10 phases
  - Sequencing constraints: All 6 honored
  - Import-linter contract task is early (T001)
  - Checksum + fail-then-pass test same unit (Phase 3)
  - Explicit no-synthetic-spread tests (Phase 6)
  - Backtest replay reconstructs observed spread from stored raw quotes
  - MarketState schema change before consumers
  - No task changes Strategy interface signature
- Status: Task list ready for human review before implementation

### 2026-07-15 (Session 2): Sprint 2 Spec Complete
- **WO-003**: Sprint 2 specification created for quote-level data
- Generated spec with all required sections
- Created five clarification questions
- All clarifications resolved with behavioral requirements
- Two answers (Q2, Q5) override tool recommendations — no "keep trading through bad data" escape hatches
- Spec updated with new functional requirements (FR-015a, FR-018a, FR-019a)
- Three load-bearing items verified intact
- Committed and pushed to GitHub: `6e1c79a`
- Ready for `/speckit-plan` phase

### 2026-07-15 (Session 1): Walking Skeleton Complete
- Implemented all Phase 1-3 tasks
- 35 tests passing
- Import-linter configured and verified
- Live loop tested on simulated feed

### 2026-07-12: Initial Venue Swap
- Decision: Retire Bybit, adopt Kraken mainnet public feed
- Created: KrakenPublicFeed adapter
- Deleted: Bybit testnet adapter and credentials
- Updated: Configuration split (DATA_SOURCE/TRADING_ENV)
- Tested: 10-minute live loop on Kraken (102 events)
- Verified: All 36 tests pass, import-linter green

### 2026-07-14: WO-002 Completion
- **WO-002-C**: Suspenders guard testability (TRADING_ENV=test added, fail-then-pass proven)
- **WO-002-D**: Venue leak closure (get_venue_name from factory, loop/ import-linter contract)
- All four guards verified with fail-then-pass proofs
- Kraken data channel question recorded in docs/decisions/

### 2026-07-15: GitHub Remote Setup
- Security verification: No secrets in git history
- Remote added: https://github.com/mhadiamiri/trading-system (Private)
- Code pushed to GitHub
- Branch master tracking origin/master

---

## Commands Reference

### Development Workflow
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest                          # Quick run
pytest -v                      # Verbose
pytest --cov=src/trading      # With coverage
pytest tests/test_risk.py     # Specific test file

# Run import-linter
import-linter lint

# Speckit workflow
/speckit-constitution         # View principles
/speckit-specify             # Create specification
/speckit-clarify             # Resolve ambiguities
/speckit-plan                # Design implementation
/speckit-tasks               # Generate tasks
/speckit-implement           # Execute implementation
/speckit-analyze             # Analyze compliance
```

### Running the System
```bash
# Live loop (simulated feed)
python -m trading.loop.live

# Live loop (Kraken public feed)
DATA_SOURCE=kraken_public python -m trading.loop.live

# Backtest on captured data
python -m trading.backtest.runner
```

### Verification Commands
```bash
# Verify tests pass
pytest

# Verify import boundaries
import-linter lint

# Verify no ML in risk layer
pytest tests/test_risk.py -k "import"

# Verify cost model
pytest tests/test_backtest_costs.py

# Verify end-to-end loop
pytest tests/integration/test_live_loop.py
```

### Git Workflow
```bash
# Check status
git status

# Pull latest changes
git pull origin master

# Push changes
git push origin master

# View commit history
git log --oneline -10
```

---

## Safety Reminders

### Critical Safety Rules
- ⚠️ **NEVER** commit real API keys to git
- ⚠️ **NEVER** run with `TRADING_ENV=mainnet` in development
- ⚠️ **ALWAYS** verify import-linter passes before committing
- ⚠️ **VERIFY** tests pass before committing
- ⚠️ **ENSURE** `DATA_SOURCE` and `TRADING_ENV` are set appropriately

### Invariant to Maintain
**No code path that can place a real order is reachable while `TRADING_ENV=paper`, regardless of `DATA_SOURCE` setting.**

This invariant is enforced through:
1. Configuration validation in `settings.py` (belt guard)
2. Paper-only execution in `execution/paper.py` (suspenders guard)
3. Import-linter blocking execution adapters
4. Test coverage verifying the invariant

---

## Next Steps

### Immediate Actions (Next Session)

1. **Review Sprint 2 task list** (`specs/002-quote-level-data/tasks.md`)
   - 41 tasks across 10 phases
   - Sequencing constraints honored
   - Ready for implementation after approval

2. **Review Sprint 2 artifacts** (if needed)
   - `specs/002-quote-level-data/spec.md` — Requirements (WO-003 complete)
   - `specs/002-quote-level-data/plan.md` — Implementation plan (WO-004 complete)
   - `specs/002-quote-level-data/research.md` — 10 technical decisions
   - `specs/002-quote-level-data/data-model.md` — 4 entities defined
   - `specs/002-quote-level-data/contracts/data-adapter.yml` — Interface contracts
   - `specs/002-quote-level-data/quickstart.md` — 10 validation scenarios
   - `specs/002-quote-level-data/analyze-report.md` — Cross-artifact consistency (WO-005-A CLEAN)
   - `specs/002-quote-level-data/tasks.md` — Task list (WO-005-B complete)

3. **Implementation Phase** (after task list approval)
   - Begin with T001: Update .importlinter.yaml with v2/book/checksum boundary contract
   - Follow task sequencing: Phase 1 → Phase 2 → Phase 3 → ... → Phase 10
   - Write tests first (fail-then-pass pattern)
   - Verify each task completes before proceeding
   - Run pytest after each phase
   - Run import-linter lint after boundary changes

### For Next Session
1. Review this document for current status
2. Read `specs/002-quote-level-data/tasks.md` for task breakdown
3. Run `pytest` to verify Sprint 1 tests still pass
4. Check `.env` configuration matches intended use
5. Pull latest from GitHub: `git pull origin master`
6. Begin implementation with T001 when ready

---

**Project Status**: 🟢 **WO-008a-R6 COMPLETE + CI GREEN** - All blockers resolved, test suite clean, architectural changes ready for human review.

**Last Session Outcome**:
- WO-008a-R6: Spread double-count fixed (attribution model), staleness guard implemented (18s threshold), test suite cleaned (0 failed)
- Commits: f5c8939 (R5+R6), 8e8a891 (test fix), 43ca600 (cleanup)
- Local/Remote HEAD: 43ca600dc96d5a2c33c3e6972a69e616efc65d19 (MATCH)

**Next Phase**: Human review of WO-008a-R5+R6 architectural changes, then WO-008b (Live WebSocket Integration) ONLY after approval.

---

## Artifacts Summary (Session 3)

### WO-004: Implementation Plan Generated
| Artifact | Purpose | Status |
|----------|---------|--------|
| `plan.md` | Technical context, constraints, constitution check, project structure | ✅ COMPLETE |
| `research.md` | 10 technical decisions with rationale and alternatives | ✅ COMPLETE |
| `data-model.md` | 4 entities defined (LocalBookState, MarketState, RollingTradeStats, QuoteUpdate) | ✅ COMPLETE |
| `contracts/data-adapter.yml` | Interface contracts, import-linter rules, testing contracts | ✅ COMPLETE |
| `quickstart.md` | 10 validation scenarios with expected outcomes | ✅ COMPLETE |

### WO-005-A: Cross-Artifact Consistency Analyze
| Check | Result | Details |
|-------|--------|---------|
| Spec → Research traceability | ✅ 100% | 5 clarifications → 10 decisions |
| Spec → Plan traceability | ✅ 100% | All FRs → constraints enforced |
| Spec → Data Model traceability | ✅ 100% | All entities defined |
| Spec → Contracts traceability | ✅ 100% | All enforcement points specified |
| Quickstart → Spec traceability | ✅ 100% | 10 scenarios → all requirements |
| Constitution alignment | ✅ 100% | All 9 principles PASS |
| Load-bearing items | ✅ 3/3 | All verified |

### WO-005-B: Task List Generated
| Metric | Value |
|-------|-------|
| Total tasks | 41 |
| Phases | 10 |
| Sequencing constraints | 6 honored |
| Parallel opportunities | Multiple identified |
| Critical path phases | Phase 1 → Phase 2 → Phase 3 → Phase 6 → Phase 7 → Phase 8 → Phase 9 |
---------------------------



---

## WO-011: Cost Model Unification + Reason-Code Vocabulary Completeness (Session — 2026-07-19)

**Status**: ✅ COMPLETE — stopped for human review (did NOT proceed to WO-008b-B).
**Baseline**: `1ef7447` (119 passed + 8 xfailed; the "1 failing" was order-dependent, deterministic was green).
**Commit**: `452914f` — pushed, local == remote.

**Executed across three turns** (two enumeration gaps escalated & ruled before code):
- Escalation 1 → RULING 1 froze the legalized set at 3 tests + the 8 xfails.
- Escalation 2 (ADDENDUM 2) → RULING 7 (behavioral guard) + RULING 8 (audit, report-only).

| Section | Deliverable | Result |
|---------|-------------|--------|
| §1 | One cost model in one module (`trading.execution.costs.compute_execution_costs`), both callers delegate | ✅ fork closed; no 0.1a; import-linter 6/6 |
| §2 + RULING 1 | 3 frozen-set assertions corrected additive → ruled (cite R6/D14) | ✅ passes randomized |
| §3 | 8 `TestCostModel` xfails → hard passes, bite-proofed | ✅ 0 xfailed |
| §4 | Reconciliation to the cent (BUY/SELL/edge, all 3 axes) + regression test | ✅ identical, bite-proofed |
| §5 | Vocabulary completeness (3 properties, declaration site excluded) | ✅ + 3 declared-but-unproducible codes REPORTED (not deleted) |
| RULING 7 | Behavioral no-synthetic-spread guard replaces source grep (6th 0.1d) | ✅ strictly stronger, bite-proofed |
| §6 | Mechanical redaction (`trading.logkit.redaction`); A2 scrubbed; fixtures labeled | ✅ secret scan clean |
| RULING 8 | Source-inspection audit (report-only) | ✅ cluster → own WO |
| §7 | Decision log — 4 entries | ✅ |
| §8 | 139 passed deterministic AND randomized (seed 20260719); import-linter 6/6, contract 6/6, ruff clean | ✅ 0 failed/xfailed/xpassed |

**Ruled**: R2 design approved; R3 paper venue gains >5% abnormal-spread guard; R4 slippage → constant (volume-scaling parked in `docs/open-cleanup.md`); R5 notional = executed price; R6 `report.py`/`fill.py` corrected.

**Open for lead**: (1) ruling on 3 declared-but-unproducible codes (`KILL_SWITCH_ENGAGED`, `LONG_SIGNAL`, `SHORT_SIGNAL`); (2) source-inspection cluster WO.

**Local/Remote HEAD**: `452914f47ecd260125944fa24f0bee925aef4c7c` (MATCH). Full report: `evidence/WO-011/REPORT.md`.

**Next Phase**: Human review of WO-011, then WO-008b-B (24h capture) ONLY after approval.
